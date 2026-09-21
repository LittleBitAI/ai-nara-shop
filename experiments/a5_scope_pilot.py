"""Run a bounded A5 control/candidate GPU pilot; never submit or resume H2 shards."""
import argparse
from collections import Counter
from contextlib import nullcontext
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import script
from experiments import a5_collect_facts as collector
from experiments import a5_scope_observation as candidate
from experiments import a5_v18_scope_review as v18_candidate
from experiments import a8_v20_annex as a8_candidate
from experiments.a5_v11_absence_candidate import verify_company_size
from tools import compare_runs, replay_run, score

CASE = ROOT / 'reports/runs/colab-1789902969401579900/dev-debug'
DIAGNOSTIC_IDS = ('PPS-D-000732', 'PPS-D-001333', 'PPS-D-002069', 'PPS-D-002106', 'PPS-D-002151')
FACTOR = 1853 / 200 * 0.96
STAGE_LIMIT = 246.985 + (7200 - 6380) / FACTOR
INPUT_MANIFEST = ROOT/'reports/team-c/a5-v18-scope-review/inputs.json'
A8_INPUT_MANIFEST = ROOT/'reports/team-c/a8-v20-annex/inputs.json'
# 회차 기록·비교·churn 이 보는 항목. 실험마다 하나다.
FOCUS = {'h3': 'v11', 'v18': 'v18', 'a8': 'v20'}
# dev 입력 명세를 쓰는 실험. h3 만 무라벨 진단 입력을 받는다.
DEV_ONLY = ('v18', 'a8')


def manifest_for(experiment):
    return A8_INPUT_MANIFEST if experiment == 'a8' else INPUT_MANIFEST


def activate_arm(name):
    return (candidate.activate() if name == 'h3' else v18_candidate.activate() if name == 'v18'
            else a8_candidate.activate() if name == 'a8' else nullcontext())


def validate_inputs(experiment='v18'):
    expected = json.loads(manifest_for(experiment).read_text(encoding='utf-8'))
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
    return first


def hybrid_replay(payload, output, *, experiment='h3', review_fields=False):
    """Replace only company_size responses; retain actual new per-record document budgets."""
    texts = replay_run.saved_responses(CASE)
    texts['company_size'] = {r['id']: r['response_text'] for r in payload['rows']}
    records = list(script.iter_records(str(ROOT/'open/dev.jsonl')))
    assert list(texts['company_size']) == [r['id'] for r in records]
    events = [dict(event='response', status='valid', phase=phase, id=identifier, response_text=text)
              for phase, values in texts.items() for identifier, text in values.items()]
    events.extend(dict(event='company_size_input', id=r['id'], max_chars=r['max_chars']) for r in payload['rows'])
    results, predictions = {}, {}
    with tempfile.TemporaryDirectory(prefix='a5-hybrid-') as directory:
        case = Path(directory)
        (case/'run_report.json').write_bytes((CASE/'run_report.json').read_bytes())
        (case/'diagnostics.jsonl').write_text(''.join(json.dumps(e, ensure_ascii=False)+'\n' for e in events),
                                             encoding='utf-8', newline='\n')
        # A8은 소비자를 바꾸지 않는다. 후보 문맥만 켜고 끄며 같은 저장 응답을 재생해,
        # 참조 블록이 라벨·항목 규칙으로 새지 않았음을 24항목 CSV 바이트로 확인한다.
        variants = (('off', None), ('on', v18_candidate.verify_company_size)) if experiment == 'v18' else (
            ('off', None), ('on', None)) if experiment == 'a8' else (('head', None), ('h2', verify_company_size))
        for name, verifier in variants:
            with (v18_candidate.activate() if review_fields else
                  a8_candidate.activate() if experiment == 'a8' and name == 'on' else nullcontext()):
                replay = replay_run.replay(script, case, input_path=str(ROOT/'open/dev.jsonl'),
                                          data_dir=str(ROOT/'open/data'), verify_company_size=verifier)
            (output/f'{name}-hybrid.csv').write_bytes(replay_run.to_csv_bytes(script, replay['rows']))
            predictions[name] = {r['id']: tuple(int(r[v]) for v in script.ITEMS) for r in replay['rows']}
            score_args = argparse.Namespace(truth=ROOT/'open/dev_labels.csv', pred=output/f'{name}-hybrid.csv',
                                            output_dir=output/f'{name}-score')
            results[name] = score.run(score_args, ['python', 'tools/score.py', '--truth', str(score_args.truth),
                '--pred', str(score_args.pred), '--output-dir', str(score_args.output_dir)])
    return results, predictions


def changes(before, after):
    return [dict(id=identifier, item=item, before=a, after=b)
            for identifier in before for item, a, b in zip(script.ITEMS, before[identifier], after[identifier]) if a != b]


def record_run(output, contract, started_at, seconds, status, error_type=None):
    """Self-contained episode record, including partial/failure runs; never invent missing F1."""
    def read(name):
        path = output/name
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    summary, environment = read('summary.json'), read('environment.json')
    counts = {}
    for path in sorted(output.glob('*/*.events.jsonl')):
        events = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
        responses = [e for e in events if e['event'] == 'response']
        counts[path.relative_to(output).as_posix()] = dict(
            valid_json=sum(e.get('status') == 'valid' for e in responses),
            invalid_json=sum(e.get('status') == 'invalid' for e in responses),
            retry_responses=sum(e.get('attempt', 1) > 1 for e in responses),
            batch_failures=sum(e['event'] == 'batch_failed' for e in events),
            retry_failures=sum(e['event'] == 'retry_failed' for e in events),
            output_tokens=sum(e['output_tokens'] for e in responses if isinstance(e.get('output_tokens'), int)),
            responses_with_token_counts=sum(isinstance(e.get('output_tokens'), int) for e in responses))
    mode = environment.get('runner_mode', 'pending')
    report = dict(run_id=f"a5-scope-{started_at}", started_at_utc=started_at,
                  ended_at_utc=datetime.now(timezone.utc).isoformat() if status != 'running' else None,
                  status=status, error_type=error_type, pilot_seconds_after_input_validation=seconds,
                  episode=contract['episode'], execution_order=contract['order'],
                  code_commit=contract['source_commit'], contract=contract, environment=environment,
                  execution_mode=mode,
                  score_kind='hybrid_cpu_replay_with_live_company_size_only' if mode == 'live' else 'not_live',
                  full_pipeline_gpu_macro_f1=None,
                  model_success_count=sum(c['valid_json'] for c in counts.values()) if mode == 'live' else 0,
                  counts=counts, results=summary, raw_responses_included=True,
                  planned_responses=2 * (len(contract['dev_ids']) + len(contract['diagnostic_ids'])),
                  independent_diagnostic_sample=False)
    collector.save(output/'run_report.json', report)
    focus = FOCUS.get(contract.get('experiment'), 'v11')
    lines = [f"# {contract.get('experiment', 'h3')} 회차 기록 (A5 파일럿 실행기)", '',
             f"- 회차 ID: {report['run_id']}", f"- 상태: {status}",
             f"- 코드: {contract['source_commit']}", f"- 순서: {' → '.join(contract['order'])}",
             f"- 시작 UTC: {started_at}", f"- 입력 검사 이후 경과: {seconds:.3f}초",
             f"- 모델 적재: {environment.get('model_load_seconds', '미측정')}초",
             f'- 실행 모드: {mode}. live 외의 실행을 실제 모델 성공으로 세지 않는다.',
             '- F1 종류: company_size + 보관된 기본/SME 응답의 혼합 CPU 재생. 전체 GPU F1은 미측정.',
             f"- 별도 진단 {len(contract['diagnostic_ids'])}건. 무라벨 발화율은 미측정.", '',
             f'| 군 | 소비자 | Macro F1 | {focus} TP/FP/FN | company 단계초 | 서버 조건부 환산초 |',
             '| --- | --- | ---: | --- | ---: | ---: |']
    for name, arm in summary.get('arms', {}).items():
        for variant, metrics in arm['metrics'].items():
            v = metrics['items'][focus]
            lines.append(f"| {name} | {variant} | {metrics['macro_f1']:.12f} | {v['tp']}/{v['fp']}/{v['fn']} | "
                         f"{arm['dev_stage_seconds']:.3f} | {arm['projected_server_seconds_conditional']:.3f} |")
    lines += ['', '## 24항목 지표', '', '| 군/소비자 | 항목 | F1 | precision | recall | TP | FP | FN |',
              '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for name, arm in summary.get('arms', {}).items():
        for variant, metrics in arm['metrics'].items():
            for item, m in metrics['items'].items():
                lines.append(f"| {name}/{variant} | {item} | {m['f1']:.6f} | {m['precision']:.6f} | "
                             f"{m['recall']:.6f} | {m['tp']} | {m['fp']} | {m['fn']} |")
    lines += ['', '입력/코드/스키마 해시·원응답·파싱/재시도 건수·변경 셀은 run_report.json과 군별 JSON,',
              'CSV·오답은 군별 *-score/에 있다. 반복 비교는 회차 2의 repeat-*/comparison.json에 있다.',
              f"실패 종류: {error_type or '없음'}. 미완료 단계의 F1은 0으로 채우지 않는다.", '']
    (output/'run-record.md').write_text('\n'.join(lines), encoding='utf-8', newline='\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, help='H3 diagnostic unlabeled input; unused for v18 dev-only pilot')
    parser.add_argument('--experiment', choices=('h3', 'v18', 'a8'), default='h3')
    parser.add_argument('--model-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--episode', type=int, choices=(1, 2), required=True)
    args = parser.parse_args()
    if args.model_dir.name != script.MODEL_REVISION or not args.model_dir.is_dir():
        parser.error('Use the fixed Hugging Face snapshot directory')
    if args.experiment in DEV_ONLY:
        validate_inputs(args.experiment)
    elif args.input is None or collector.file_hash(args.input) != collector.UNLABELED_SHA256:
        parser.error('Wrong train_unlabeled SHA256')
    dev = list(script.iter_records(str(ROOT/'open/dev.jsonl')))
    diagnostics = ([r for r in script.iter_records(str(args.input), limit=2000) if r['id'] in DIAGNOSTIC_IDS]
                   if args.experiment == 'h3' else [])
    assert len(dev) == 200 and (args.experiment != 'h3' or tuple(r['id'] for r in diagnostics) == DIAGNOSTIC_IDS)
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=False)
    _, products = script.load_sme_reference(str(ROOT/'open/data'))
    order = ['control', args.experiment] if args.episode == 1 else [args.experiment, 'control']
    sources = [ROOT/'script.py', Path(__file__), ROOT/'experiments/a5_scope_observation.py',
               ROOT/'experiments/a5_collect_facts.py', ROOT/'experiments/a5_v11_absence_candidate.py',
               ROOT/'tools/replay_run.py', ROOT/'tools/score.py', ROOT/'tools/compare_runs.py', ROOT/'requirements.txt',
               ROOT/'open/dev.jsonl', ROOT/'open/dev_labels.csv', CASE/'diagnostics.jsonl', CASE/'run_report.json',
               *sorted(p for p in (ROOT/'open/data').rglob('*') if p.is_file())]
    if args.experiment in DEV_ONLY:
        manifest = manifest_for(args.experiment)
        sources = [p for p in sources if not p.is_relative_to(ROOT/'open/data')]
        sources += [ROOT/name for name in json.loads(manifest.read_text(encoding='utf-8'))
                    if name.startswith('open/data/')]
        sources += [ROOT/'experiments/a5_v18_scope_review.py', manifest]
        if args.experiment == 'a8':
            sources += [ROOT/'experiments/a8_v20_annex.py', ROOT/'experiments/law_index.py']
    contract = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    files={p.relative_to(ROOT).as_posix(): collector.file_hash(p) for p in sources},
                    input_sha256=collector.UNLABELED_SHA256 if args.experiment == 'h3' else collector.file_hash(ROOT/'open/dev.jsonl'),
                    experiment=args.experiment, model_id=script.MODEL_ID,
                    model_revision=script.MODEL_REVISION, episode=args.episode, order=order,
                    dev_ids=[r['id'] for r in dev], diagnostic_ids=[r['id'] for r in diagnostics],
                    chunk=collector.CHUNK, max_chars=collector.MAX_CHARS, seed=script.SEED,
                    max_tokens=script.MAX_TOKENS, quant=script.QUANT,
                    prompt_budget=script.PROMPT_BUDGET, max_model_len=script.MAX_MODEL_LEN,
                    stage_limit_seconds=STAGE_LIMIT, arms={})
    for name in order:
        with activate_arm(name):
            contract['arms'][name] = dict(prompt=script.COMPANY_SIZE_PROMPT, schema=script.company_size_schema(),
                prompt_sha256=collector.digest(script.COMPANY_SIZE_PROMPT), schema_sha256=collector.digest(script.company_size_schema()))
    collector.save(output/'contract.json', contract)
    started_at = datetime.now(timezone.utc).isoformat()
    started = time.perf_counter()
    record_run(output, contract, started_at, 0, 'running')
    status, error_type = 'failed', None
    try:
        if args.experiment in DEV_ONLY and args.episode == 2:
            validate_previous(output, contract)
        execute(args, output, contract, dev, diagnostics, products, order)
        status = 'complete'
    except BaseException as error:
        error_type = type(error).__name__
        raise
    finally:
        record_run(output, contract, started_at, time.perf_counter()-started, status, error_type)


def execute(args, output, contract, dev, diagnostics, products, order):
    runner = script.VLLMRunner(script.decode_schema(str(ROOT/'open/data')), model_dir=str(args.model_dir))
    collector.save(output/'environment.json', dict(environment=runner.environment, model_load_seconds=runner.load_seconds,
                                                   runner_mode=getattr(runner, 'MODE', 'test_double')))
    if args.experiment in DEV_ONLY and args.episode == 2:
        first = output.parent/'episode-1'
        previous = json.loads((first/'environment.json').read_text(encoding='utf-8'))
        if previous['environment'] != runner.environment or previous['runner_mode'] != getattr(runner, 'MODE', 'test_double'):
            raise ValueError('Episode GPU/runtime mismatch')
    if args.experiment == 'a8':
        # 생성 호출 전에 이 러너의 실제 토크나이저로 두 군을 센다. 기록은 실패해도 남긴다.
        budget = a8_candidate.budget_report(dev, runner, products, max_chars=collector.MAX_CHARS)
        collector.save(output/'budget.json', budget)
        if not budget['conditions_pass']:
            raise RuntimeError('Injected block shrinks documents or changes notice text; stopping before generation')
    summary = dict(mode=getattr(runner, 'MODE', 'test_double') + '_company_size_pilot_with_hybrid_cpu_replay', episode=args.episode,
                   complete=False, arms={}, diagnostic_is_independent_evaluation=False)
    collector.save(output/'summary.json', summary)
    predictions = {}
    for name in order:
        arm = output/name
        arm.mkdir()
        payloads = {}
        with activate_arm(name):
            for group, records in (('dev', dev), ('diagnostic', diagnostics)):
                if not records:
                    continue
                with (arm/f'{group}.events.jsonl').open('x', encoding='utf-8', newline='\n') as log:
                    def emit(event, **fields):
                        log.write(json.dumps(dict(event=event, **fields), ensure_ascii=False)+'\n')
                        log.flush()
                    payload = collector.collect(records, runner, products, emit)
                if name == 'h3':
                    for row, rec in zip(payload['rows'], records):
                        facts = script.parse_judgment(row['response_text'], expected_items=script.COMPANY_SIZE_KEYS)[0]['company_size']
                        row['scope_trace'] = candidate.trace(facts, rec, row['max_chars'], products)
                elif name == 'v18':
                    for row, rec in zip(payload['rows'], records):
                        facts = script.parse_judgment(row['response_text'], expected_items=script.COMPANY_SIZE_KEYS)[0]['company_size']
                        row['scope_trace'] = v18_candidate.trace(facts, rec, row['max_chars'])
                payloads[group] = payload
                collector.save(arm/f'{group}.json', dict(contract_sha256=collector.digest(contract),
                               payload_sha256=collector.digest(payload), payload=payload))
        # H3 diagnostics are ignored; v18 explicitly retains review fields for OFF/ON replay.
        metrics, predictions[name] = hybrid_replay(payloads['dev'], arm, experiment=args.experiment,
                                                  review_fields=name == 'v18')
        stage = payloads['dev']['stage_seconds']
        projected = 6380 + (stage - 246.985) * FACTOR
        variants = ('off', 'on') if args.experiment in ('v18', 'a8') else ('head', 'h2')
        within = changes(predictions[name][variants[0]], predictions[name][variants[1]])
        if args.experiment == 'a8':
            assert not within, 'Prompt-only injection must not change any consumed cell'
        else:
            assert all(c['item'] == FOCUS[args.experiment] for c in within)
        change_key = 'off_to_on_changes' if args.experiment in ('v18', 'a8') else 'head_to_h2_changes'
        summary['arms'][name] = dict(metrics=metrics, **{change_key: within},
                                     dev_stage_seconds=stage, dev_inference_seconds=payloads['dev']['inference_seconds'],
                                     projected_server_seconds_conditional=projected,
                                     within_stage_planning_limit=stage <= STAGE_LIMIT,
                                     dev_h2_fired=sum(r['h2_fired'] for r in payloads['dev']['rows']))
        if name == 'h3':
            summary['arms'][name]['condition_states'] = dict(Counter(r['scope_trace']['state'] for r in payloads['dev']['rows']))
            summary['arms'][name]['competitive_without_condition_support'] = [r['id'] for r in payloads['dev']['rows']
                if r['scope_trace']['competitive_without_condition_support']]
        collector.save(output/'summary.json', summary)
        if args.experiment in DEV_ONLY and stage > STAGE_LIMIT:
            raise RuntimeError('Company stage exceeds planning limit; partial results preserved')
    summary[f'control_to_{args.experiment}_changes'] = {
        name: changes(predictions['control'][name], predictions[args.experiment][name]) for name in variants}
    for name in variants:
        comparison = compare_runs.compare(score, ROOT/'open/dev_labels.csv',
            output/'control'/f'{name}-hybrid.csv', output/args.experiment/f'{name}-hybrid.csv',
            focus=(FOCUS[args.experiment],) if args.experiment in DEV_ONLY else ('v11', 'v13'))
        comparison['interpretation'] = 'Different prompts; historical drift_reference is not a pass/fail threshold.'
        collector.save(output/f'{name}-comparison.json', comparison)
    if args.experiment in DEV_ONLY:
        focus = (FOCUS[args.experiment],)
        collector.save(output/'consumer-comparison.json', compare_runs.compare(score, ROOT/'open/dev_labels.csv',
            output/args.experiment/'off-hybrid.csv', output/args.experiment/'on-hybrid.csv', focus=focus))
        if args.episode == 2:
            for arm in order:
                for variant in variants:
                    comparison = compare_runs.compare(score, ROOT/'open/dev_labels.csv',
                        output.parent/'episode-1'/arm/f'{variant}-hybrid.csv', output/arm/f'{variant}-hybrid.csv', focus=focus)
                    comparison['interpretation'] = 'Same arm, independent runtime; measured churn, not a universal threshold.'
                    collector.save(output/f'repeat-{arm}-{variant}.json', comparison)
    summary['complete'] = True
    summary['note'] = 'Company_size observations only. Hybrid replay is not a new full-pipeline GPU score or adoption.'
    collector.save(output/'summary.json', summary)
    print(json.dumps({name: dict(macro_f1=arm['metrics'][variants[-1]]['macro_f1'],
                     focus=arm['metrics'][variants[-1]]['items'][FOCUS[args.experiment]],
                     stage_seconds=arm['dev_stage_seconds'], within_limit=arm['within_stage_planning_limit'])
                     for name, arm in summary['arms'].items()}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
