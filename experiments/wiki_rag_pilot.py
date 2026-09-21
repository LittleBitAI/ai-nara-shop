"""Wiki RAG pilot: does a v20 판정 페이지 beat the raw law spans, or the current prompt?

Three arms share one company_size call, one schema and one document budget. Only the data
block appended to the user message changes. Nothing here is adopted, submitted or merged.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import script
from experiments import a5_collect_facts as collector
from experiments import a5_scope_pilot as pilot
from tools import compare_runs, replay_run, score

ASSETS = ROOT/'experiments/wiki-rag'
INPUT_MANIFEST = ROOT/'reports/wiki-rag-pilot/inputs.json'
ARMS = ('control', 'raw', 'wiki')
PLACEHOLDER = re.compile(r'\{\{span:([a-z0-9-]+)\}\}')
FRONT_MATTER = re.compile(r'\A---\n.*?\n---\n', re.S)
BLOCK_HEAD = ("\n[Provided 법령·고시 excerpts for the software participation fields; "
              "not notice evidence]\n"
              "Do not copy any text below into a quotation field and do not treat it as a "
              "sentence of the notice. Quotations are verbatim from the supplied 법령패키지.\n\n")
BLOCK_TAIL = "\n\n[End of provided 법령·고시 excerpts]\n"


def load_sources():
    """Fail before inference on a damaged asset: bad hash, bad offset or edited quotation."""
    manifest = json.loads((ASSETS/'sources.json').read_text(encoding='utf-8'))
    texts = {}
    for source in manifest['sources']:
        raw = (ROOT/source['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != source['sha256']:
            raise ValueError('Source SHA256 mismatch: ' + source['path'])
        texts[source['path']] = raw.decode('utf-8')
    seen = set()
    for span in manifest['spans']:
        if span['span_id'] in seen:
            raise ValueError('Duplicate span id: ' + span['span_id'])
        seen.add(span['span_id'])
        text = texts[span['source_path']]
        if text[span['start']:span['end']] != span['quote'] or len(span['quote']) != span['chars']:
            raise ValueError('Span offset does not reproduce the quotation: ' + span['span_id'])
    return manifest


def render(span):
    return '[' + span['address'] + ']\n' + span['quote']


def raw_block(manifest):
    """Arm B: the same spans, in source order, with no page structure."""
    order = [source['path'] for source in manifest['sources']]
    spans = sorted(manifest['spans'], key=lambda s: (order.index(s['source_path']), s['start']))
    return BLOCK_HEAD + '\n\n'.join(render(span) for span in spans) + BLOCK_TAIL


def wiki_block(manifest):
    """Arm C: the same spans placed in the 7칸 page. Same quotations, different arrangement."""
    page = FRONT_MATTER.sub('', (ASSETS/'v20.md').read_text(encoding='utf-8'))
    by_id = {span['span_id']: span for span in manifest['spans']}
    if sorted(PLACEHOLDER.findall(page)) != sorted(by_id):
        raise ValueError('Page and sources.json do not use the same span set exactly once')
    return BLOCK_HEAD + PLACEHOLDER.sub(lambda m: render(by_id[m.group(1)]), page).strip() + BLOCK_TAIL


def blocks(manifest):
    return {'control': '', 'raw': raw_block(manifest), 'wiki': wiki_block(manifest)}


@contextmanager
def activate(arm, arm_blocks):
    """Append one data block to the existing user message. Prompt and schema are untouched."""
    if not arm_blocks[arm]:
        yield
        return
    original = script.build_user_prompt

    def build_user_prompt(rec, max_chars, products=()):
        return original(rec, max_chars, products) + arm_blocks[arm]

    with patch.object(script, 'build_user_prompt', build_user_prompt):
        yield


def budget_plan(records, runner, products, arm_blocks):
    """One document budget every arm passes, so only the knowledge block differs.

    `fit_to_budget` shrinks each arm on its own, so calling it three times is not a plan.
    Start from the smallest arm, then re-measure every arm on the shared value until none
    shrinks. Over budget at the 128-char floor raises before any inference call.
    """
    plan, notes = {}, {}
    for rec in records:
        company = {**rec, 'meta': {k: v for k, v in rec.get('meta', {}).items() if k != '조항호내용'}}
        chars, usual, usual_tokens = collector.MAX_CHARS, None, None
        while True:
            fitted = {}
            for arm in arm_blocks:
                with activate(arm, arm_blocks):
                    _, tokens, arm_chars = script.fit_to_budget(
                        company, script.COMPANY_SIZE_PROMPT, runner, chars,
                        budget=script.PROMPT_BUDGET, products=products)
                fitted[arm] = dict(prompt_tokens=tokens, max_chars=arm_chars)
            if usual is None:
                # The first pass starts at the production budget, so control's own fit is the
                # usual A input. Measuring it again would only repeat the same call.
                usual, usual_tokens = fitted['control']['max_chars'], fitted['control']['prompt_tokens']
            smallest = min(value['max_chars'] for value in fitted.values())
            if smallest == chars:
                break
            chars = smallest
        plan[rec['id']] = chars
        visible, usual_visible = script.build_context(rec, chars), script.build_context(rec, usual)
        notes[rec['id']] = dict(
            common_max_chars=chars, usual_control_max_chars=usual,
            usual_control_prompt_tokens=usual_tokens,
            additional_truncation_chars=usual - chars, arms=fitted,
            context_sha256=hashlib.sha256(visible.encode('utf-8')).hexdigest(),
            usual_context_sha256=hashlib.sha256(usual_visible.encode('utf-8')).hexdigest(),
            truncated='[Truncated documents; unseen remainder]' in visible,
            usual_truncated='[Truncated documents; unseen remainder]' in usual_visible)
    return plan, notes


def replay_arm(payload, output, name):
    """Replace only company_size; keep the archived baseline/SME responses and default verifier."""
    texts = replay_run.saved_responses(pilot.CASE)
    texts['company_size'] = {row['id']: row['response_text'] for row in payload['rows']}
    records = list(script.iter_records(str(ROOT/'open/dev.jsonl')))
    if list(texts['company_size']) != [rec['id'] for rec in records]:
        raise ValueError('Replay needs one company response per dev record, in input order')
    events = [dict(event='response', status='valid', phase=phase, id=identifier, response_text=text)
              for phase, values in texts.items() for identifier, text in values.items()]
    events.extend(dict(event='company_size_input', id=row['id'], max_chars=row['max_chars'])
                  for row in payload['rows'])
    with tempfile.TemporaryDirectory(prefix='wiki-rag-') as directory:
        case = Path(directory)
        (case/'run_report.json').write_bytes((pilot.CASE/'run_report.json').read_bytes())
        (case/'diagnostics.jsonl').write_text(
            ''.join(json.dumps(event, ensure_ascii=False)+'\n' for event in events),
            encoding='utf-8', newline='\n')
        replay = replay_run.replay(script, case, input_path=str(ROOT/'open/dev.jsonl'),
                                   data_dir=str(ROOT/'open/data'))
    path = output/(name + '-hybrid.csv')
    path.write_bytes(replay_run.to_csv_bytes(script, replay['rows']))
    arguments = argparse.Namespace(truth=ROOT/'open/dev_labels.csv', pred=path, output_dir=output/'score')
    metrics = score.run(arguments, ['python', 'tools/score.py', '--truth', str(arguments.truth),
                                    '--pred', str(path), '--output-dir', str(arguments.output_dir)])
    predictions = {row['id']: tuple(int(row[item]) for item in script.ITEMS) for row in replay['rows']}
    collector.save(output/'verification.json', dict(
        rejected_conditions=replay['rejected_conditions'],
        facts=[dict(id=row['id'], max_chars=row['max_chars'],
                    company_size=script.parse_judgment(
                        row['response_text'], expected_items=script.COMPANY_SIZE_KEYS)[0]['company_size'])
               for row in payload['rows']]))
    return metrics, predictions


def validate_inputs():
    expected = json.loads(INPUT_MANIFEST.read_text(encoding='utf-8'))
    for name, digest in expected.items():
        if collector.file_hash(ROOT/name) != digest:
            raise ValueError('Input SHA256 mismatch: ' + name)


def validate_previous(output, contract):
    first = output.parent/'episode-1'
    summary = json.loads((first/'summary.json').read_text(encoding='utf-8'))
    report = json.loads((first/'run_report.json').read_text(encoding='utf-8'))
    if not summary['complete'] or report['status'] != 'complete':
        raise ValueError('Episode 1 incomplete')
    if not all(arm['within_stage_planning_limit'] for arm in summary['arms'].values()):
        raise ValueError('Episode 1 stage time limit exceeded')
    previous = json.loads((first/'contract.json').read_text(encoding='utf-8'))
    for key in (contract.keys() | previous.keys()) - {'episode', 'order'}:
        if previous.get(key) != contract.get(key):
            raise ValueError('Episode contract mismatch: ' + key)


def record_run(output, contract, started_at, seconds, status, error_type=None):
    """Self-contained episode record. A missing stage keeps a null, never a zero F1."""
    def read(name):
        path = output/name
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    summary, environment = read('summary.json'), read('environment.json')
    counts = {}
    for path in sorted(output.glob('*/*.events.jsonl')):
        events = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
        responses = [event for event in events if event['event'] == 'response']
        counts[path.relative_to(output).as_posix()] = dict(
            valid_json=sum(event.get('status') == 'valid' for event in responses),
            invalid_json=sum(event.get('status') == 'invalid' for event in responses),
            retry_responses=sum(event.get('attempt', 1) > 1 for event in responses),
            batch_failures=sum(event['event'] == 'batch_failed' for event in events),
            retry_failures=sum(event['event'] == 'retry_failed' for event in events),
            output_tokens=sum(event['output_tokens'] for event in responses
                              if isinstance(event.get('output_tokens'), int)))
    mode = environment.get('runner_mode', 'pending')
    report = dict(run_id='wiki-rag-' + started_at, started_at_utc=started_at,
                  ended_at_utc=datetime.now(timezone.utc).isoformat() if status != 'running' else None,
                  status=status, error_type=error_type, pilot_seconds_after_input_validation=seconds,
                  episode=contract['episode'], execution_order=contract['order'],
                  code_commit=contract['source_commit'], contract=contract, environment=environment,
                  execution_mode=mode,
                  score_kind='hybrid_cpu_replay_with_live_company_size_only' if mode == 'live' else 'not_live',
                  full_pipeline_gpu_macro_f1=None, server_macro_f1=None,
                  model_success_count=sum(c['valid_json'] for c in counts.values()) if mode == 'live' else 0,
                  counts=counts, results=summary, raw_responses_included=True,
                  planned_responses=len(ARMS)*len(contract['dev_ids']),
                  unlabeled_firing_rate_measured=False, independent_review=False)
    collector.save(output/'run_report.json', report)
    lines = ['# Wiki RAG v20 회차 기록', '', '- 회차 ID: ' + report['run_id'], '- 상태: ' + status,
             '- 코드: ' + contract['source_commit'], '- 순서: ' + ' → '.join(contract['order']),
             '- 시작 UTC: ' + started_at, f'- 입력 검사 이후 경과: {seconds:.3f}초',
             f"- 모델 적재: {environment.get('model_load_seconds', '미측정')}초",
             f'- 실행 모드: {mode}. live 외의 실행을 실제 모델 성공으로 세지 않는다.',
             '- F1 종류: company 응답만 이번 실행이고 기본/SME는 보관 응답인 혼합 CPU 재생이다.',
             '  전체 파이프라인 GPU·무라벨 발화율·서버 점수는 미측정이다.', '',
             '| 군 | Macro F1 | v20 TP/FP/FN | company 단계초 | 서버 조건부 환산초 | 상한 이내 |',
             '| --- | ---: | --- | ---: | ---: | --- |']
    for name, arm in summary.get('arms', {}).items():
        v20 = arm['metrics']['items']['v20']
        lines.append(f"| {name} | {arm['metrics']['macro_f1']:.12f} | {v20['tp']}/{v20['fp']}/{v20['fn']} | "
                     f"{arm['dev_stage_seconds']:.3f} | {arm['projected_server_seconds_conditional']:.3f} | "
                     f"{'예' if arm['within_stage_planning_limit'] else '아니오'} |")
    lines += ['', '## 24항목 지표', '', '| 군 | 항목 | F1 | precision | recall | TP | FP | FN |',
              '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for name, arm in summary.get('arms', {}).items():
        for item, value in arm['metrics']['items'].items():
            lines.append(f"| {name} | {item} | {value['f1']:.6f} | {value['precision']:.6f} | "
                         f"{value['recall']:.6f} | {value['tp']} | {value['fp']} | {value['fn']} |")
    budget = summary.get('budget', {})
    lines += ['', '## 공통 입력 예산', '',
              f"- 세 군 공통 max_chars 중앙값 {budget.get('median_common_max_chars', '미측정')}, "
              f"최소 {budget.get('min_common_max_chars', '미측정')}.",
              f"- 통상 A보다 더 잘린 공고 {budget.get('further_truncated_notices', '미측정')}건, "
              f"추가 절단 글자 합계 {budget.get('additional_truncation_chars_total', '미측정')}.",
              f"- 공통 예산에서 새로 절단 표시가 생긴 공고 {budget.get('newly_truncated_notices', '미측정')}건.",
              '- 공고별 값과 본문 hash는 budget.json에 있다. 세 군의 본문 hash는 같다.', '',
              '입력/코드/자산 해시·원응답·재시도·변경 셀은 run_report.json과 군별 JSON에,',
              'CSV·오답은 군별 score/에 있다. 군 간·회차 간 비교는 *-comparison.json에 있다.',
              f"실패 종류: {error_type or '없음'}. 미완료 단계의 F1은 0으로 채우지 않는다.", '']
    (output/'run-record.md').write_text('\n'.join(lines), encoding='utf-8', newline='\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--episode', type=int, choices=(1, 2), required=True)
    args = parser.parse_args()
    if args.model_dir.name != script.MODEL_REVISION or not args.model_dir.is_dir():
        parser.error('Use the fixed Hugging Face snapshot directory')
    validate_inputs()
    manifest = load_sources()
    arm_blocks = blocks(manifest)
    dev = list(script.iter_records(str(ROOT/'open/dev.jsonl')))
    if len(dev) != 200:
        parser.error('Expected dev 200 records')
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=False)
    order = list(ARMS) if args.episode == 1 else list(reversed(ARMS))
    sources = [ROOT/'script.py', Path(__file__), ROOT/'experiments/a5_collect_facts.py',
               ROOT/'experiments/a5_scope_pilot.py', ROOT/'tools/replay_run.py', ROOT/'tools/score.py',
               ROOT/'tools/compare_runs.py', ROOT/'requirements.txt', ASSETS/'v20.md',
               ASSETS/'sources.json', INPUT_MANIFEST,
               *(ROOT/name for name in json.loads(INPUT_MANIFEST.read_text(encoding='utf-8')))]
    contract = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    files={path.relative_to(ROOT).as_posix(): collector.file_hash(path)
                           for path in dict.fromkeys(sources)},
                    experiment='wiki-rag-v20', item='v20', model_id=script.MODEL_ID,
                    model_revision=script.MODEL_REVISION, episode=args.episode, order=order,
                    dev_ids=[rec['id'] for rec in dev], chunk=collector.CHUNK,
                    starting_max_chars=collector.MAX_CHARS, seed=script.SEED,
                    max_tokens=script.MAX_TOKENS, quant=script.QUANT,
                    prompt_budget=script.PROMPT_BUDGET, max_model_len=script.MAX_MODEL_LEN,
                    stage_limit_seconds=pilot.STAGE_LIMIT,
                    prompt_sha256=collector.digest(script.COMPANY_SIZE_PROMPT),
                    schema_sha256=collector.digest(script.company_size_schema()),
                    span_ids=sorted(span['span_id'] for span in manifest['spans']),
                    quote_sha256=collector.digest(sorted(span['quote'] for span in manifest['spans'])),
                    blocks={arm: dict(chars=len(text),
                                      sha256=hashlib.sha256(text.encode('utf-8')).hexdigest())
                            for arm, text in arm_blocks.items()})
    collector.save(output/'contract.json', contract)
    started_at = datetime.now(timezone.utc).isoformat()
    started = time.perf_counter()
    record_run(output, contract, started_at, 0, 'running')
    status, error_type = 'failed', None
    try:
        if args.episode == 2:
            validate_previous(output, contract)
        execute(args, output, contract, dev, arm_blocks, order)
        status = 'complete'
    except BaseException as error:
        error_type = type(error).__name__
        raise
    finally:
        record_run(output, contract, started_at, time.perf_counter()-started, status, error_type)


def execute(args, output, contract, dev, arm_blocks, order):
    _, products = script.load_sme_reference(str(ROOT/'open/data'))
    runner = script.VLLMRunner(script.decode_schema(str(ROOT/'open/data')), model_dir=str(args.model_dir))
    mode = getattr(runner, 'MODE', 'test_double')
    collector.save(output/'environment.json', dict(environment=runner.environment,
                   model_load_seconds=runner.load_seconds, runner_mode=mode,
                   token_count=getattr(runner, 'TOKEN_COUNT', 'unknown')))
    if args.episode == 2:
        previous = json.loads((output.parent/'episode-1/environment.json').read_text(encoding='utf-8'))
        if previous['environment'] != runner.environment or previous['runner_mode'] != mode:
            raise ValueError('Episode GPU/runtime mismatch')
    # The shared budget is fixed before any inference call; an over-budget notice raises here.
    plan, notes = budget_plan(dev, runner, products, arm_blocks)
    collector.save(output/'budget.json', dict(plan=plan, notices=notes))
    if args.episode == 2:
        if json.loads((output.parent/'episode-1/budget.json').read_text(encoding='utf-8'))['plan'] != plan:
            raise ValueError('Episode document budget mismatch')
    summary = dict(mode=mode + '_company_size_pilot_with_hybrid_cpu_replay', episode=args.episode,
                   complete=False, arms={}, budget=dict(
                       median_common_max_chars=sorted(plan.values())[len(plan)//2],
                       min_common_max_chars=min(plan.values()),
                       further_truncated_notices=sum(n['additional_truncation_chars'] > 0 for n in notes.values()),
                       additional_truncation_chars_total=sum(n['additional_truncation_chars'] for n in notes.values()),
                       newly_truncated_notices=sum(n['truncated'] and not n['usual_truncated'] for n in notes.values()),
                       note='Common budget, not the production A input. Extra truncation is recorded, not hidden.'))
    collector.save(output/'summary.json', summary)
    predictions = {}
    for name in order:
        arm = output/name
        arm.mkdir()
        with activate(name, arm_blocks), (arm/'dev.events.jsonl').open('x', encoding='utf-8', newline='\n') as log:
            def emit(event, **fields):
                log.write(json.dumps(dict(event=event, **fields), ensure_ascii=False)+'\n')
                log.flush()
            payload = collector.collect(dev, runner, products, emit, plan=plan)
        collector.save(arm/'dev.json', dict(contract_sha256=collector.digest(contract),
                       payload_sha256=collector.digest(payload), payload=payload))
        metrics, predictions[name] = replay_arm(payload, arm, name)
        stage = payload['stage_seconds']
        summary['arms'][name] = dict(metrics=metrics, dev_stage_seconds=stage,
                                     dev_inference_seconds=payload['inference_seconds'],
                                     projected_server_seconds_conditional=6380 + (stage-246.985)*pilot.FACTOR,
                                     within_stage_planning_limit=stage <= pilot.STAGE_LIMIT,
                                     prompt_tokens_total=sum(row['prompt_tokens'] for row in payload['rows']))
        collector.save(output/'summary.json', summary)
        if stage > pilot.STAGE_LIMIT:
            raise RuntimeError('Company stage exceeds planning limit; partial results preserved')
    for before, after in (('control', 'raw'), ('control', 'wiki'), ('raw', 'wiki')):
        comparison = compare_runs.compare(score, ROOT/'open/dev_labels.csv',
            output/before/(before + '-hybrid.csv'), output/after/(after + '-hybrid.csv'), focus=('v20',))
        comparison['changes'] = pilot.changes(predictions[before], predictions[after])
        comparison['interpretation'] = ('Different user messages; the historical drift_reference is a '
                                        'churn observation, not a pass/fail threshold.')
        collector.save(output/(before + '-to-' + after + '-comparison.json'), comparison)
    if args.episode == 2:
        for name in ARMS:
            comparison = compare_runs.compare(score, ROOT/'open/dev_labels.csv',
                output.parent/'episode-1'/name/(name + '-hybrid.csv'), output/name/(name + '-hybrid.csv'),
                focus=('v20',))
            comparison['interpretation'] = 'Same arm, independent runtime; measured churn only.'
            collector.save(output/('repeat-' + name + '.json'), comparison)
    summary['complete'] = True
    summary['note'] = ('Company_size observations only. Hybrid replay is neither a full-pipeline GPU '
                       'score nor an adoption decision.')
    collector.save(output/'summary.json', summary)
    print(json.dumps({name: dict(macro_f1=arm['metrics']['macro_f1'], v20=arm['metrics']['items']['v20'],
                                 stage_seconds=arm['dev_stage_seconds'],
                                 within_limit=arm['within_stage_planning_limit'])
                      for name, arm in summary['arms'].items()}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
