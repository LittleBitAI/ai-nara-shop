"""Run a bounded A5 H3 control/candidate GPU pilot; never submit or resume H2 shards."""
import argparse
from collections import Counter
from contextlib import nullcontext
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import script
from experiments import a5_collect_facts as collector
from experiments import a5_scope_observation as candidate
from experiments.a5_v11_absence_candidate import verify_company_size
from tools import compare_runs, replay_run, score

CASE = ROOT / 'reports/runs/colab-1789902969401579900/dev-debug'
DIAGNOSTIC_IDS = ('PPS-D-000732', 'PPS-D-001333', 'PPS-D-002069', 'PPS-D-002106', 'PPS-D-002151')
FACTOR = 1853 / 200 * 0.96
STAGE_LIMIT = 246.985 + (7200 - 6380) / FACTOR


def hybrid_replay(payload, output):
    """Replace only company_size responses; retain actual new per-record document budgets."""
    texts = replay_run.saved_responses(CASE)
    texts['company_size'] = {r['id']: r['response_text'] for r in payload['rows']}
    records = list(script.iter_records(str(ROOT/'open/dev.jsonl')))
    assert list(texts['company_size']) == [r['id'] for r in records]
    events = [dict(event='response', status='valid', phase=phase, id=identifier, response_text=text)
              for phase, values in texts.items() for identifier, text in values.items()]
    events.extend(dict(event='company_size_input', id=r['id'], max_chars=r['max_chars']) for r in payload['rows'])
    truth = score.load_csv(ROOT/'open/dev_labels.csv')[0]
    results, predictions = {}, {}
    with tempfile.TemporaryDirectory(prefix='a5-hybrid-') as directory:
        case = Path(directory)
        (case/'run_report.json').write_bytes((CASE/'run_report.json').read_bytes())
        (case/'diagnostics.jsonl').write_text(''.join(json.dumps(e, ensure_ascii=False)+'\n' for e in events),
                                             encoding='utf-8', newline='\n')
        for name, verifier in (('head', None), ('h2', verify_company_size)):
            replay = replay_run.replay(script, case, input_path=str(ROOT/'open/dev.jsonl'),
                                      data_dir=str(ROOT/'open/data'), verify_company_size=verifier)
            (output/f'{name}-hybrid.csv').write_bytes(replay_run.to_csv_bytes(script, replay['rows']))
            predictions[name] = {r['id']: tuple(int(r[v]) for v in script.ITEMS) for r in replay['rows']}
            results[name] = score.calculate(truth, predictions[name])[0]
    return results, predictions


def changes(before, after):
    return [dict(id=identifier, item=item, before=a, after=b)
            for identifier in before for item, a, b in zip(script.ITEMS, before[identifier], after[identifier]) if a != b]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--model-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--episode', type=int, choices=(1, 2), required=True)
    args = parser.parse_args()
    if args.model_dir.name != script.MODEL_REVISION or not args.model_dir.is_dir():
        parser.error('Use the fixed Hugging Face snapshot directory')
    if collector.file_hash(args.input) != collector.UNLABELED_SHA256:
        parser.error('Wrong train_unlabeled SHA256')
    dev = list(script.iter_records(str(ROOT/'open/dev.jsonl')))
    diagnostics = [r for r in script.iter_records(str(args.input), limit=2000) if r['id'] in DIAGNOSTIC_IDS]
    assert len(dev) == 200 and tuple(r['id'] for r in diagnostics) == DIAGNOSTIC_IDS
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=False)
    _, products = script.load_sme_reference(str(ROOT/'open/data'))
    order = ['control', 'h3'] if args.episode == 1 else ['h3', 'control']
    sources = [ROOT/'script.py', Path(__file__), ROOT/'experiments/a5_scope_observation.py',
               ROOT/'experiments/a5_collect_facts.py', ROOT/'experiments/a5_v11_absence_candidate.py',
               ROOT/'tools/replay_run.py', ROOT/'tools/score.py', ROOT/'tools/compare_runs.py', ROOT/'requirements.txt',
               ROOT/'open/dev.jsonl', ROOT/'open/dev_labels.csv', CASE/'diagnostics.jsonl', CASE/'run_report.json',
               *sorted(p for p in (ROOT/'open/data').rglob('*') if p.is_file())]
    contract = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    files={p.relative_to(ROOT).as_posix(): collector.file_hash(p) for p in sources},
                    input_sha256=collector.UNLABELED_SHA256, model_id=script.MODEL_ID,
                    model_revision=script.MODEL_REVISION, episode=args.episode, order=order,
                    dev_ids=[r['id'] for r in dev], diagnostic_ids=list(DIAGNOSTIC_IDS),
                    chunk=collector.CHUNK, max_chars=collector.MAX_CHARS, seed=script.SEED,
                    max_tokens=script.MAX_TOKENS, quant=script.QUANT,
                    stage_limit_seconds=STAGE_LIMIT, arms={})
    for name in order:
        with candidate.activate() if name == 'h3' else nullcontext():
            contract['arms'][name] = dict(prompt=script.COMPANY_SIZE_PROMPT, schema=script.company_size_schema())
    collector.save(output/'contract.json', contract)
    runner = script.VLLMRunner(script.decode_schema(str(ROOT/'open/data')), model_dir=str(args.model_dir))
    collector.save(output/'environment.json', dict(environment=runner.environment, model_load_seconds=runner.load_seconds))
    summary = dict(mode='live_company_size_pilot_with_hybrid_cpu_replay', episode=args.episode,
                   complete=False, arms={}, diagnostic_is_independent_evaluation=False)
    collector.save(output/'summary.json', summary)
    predictions = {}
    for name in order:
        arm = output/name
        arm.mkdir()
        payloads = {}
        with candidate.activate() if name == 'h3' else nullcontext():
            for group, records in (('dev', dev), ('diagnostic', diagnostics)):
                with (arm/f'{group}.events.jsonl').open('x', encoding='utf-8', newline='\n') as log:
                    def emit(event, **fields):
                        log.write(json.dumps(dict(event=event, **fields), ensure_ascii=False)+'\n')
                        log.flush()
                    payload = collector.collect(records, runner, products, emit)
                if name == 'h3':
                    for row, rec in zip(payload['rows'], records):
                        facts = script.parse_judgment(row['response_text'], expected_items=script.COMPANY_SIZE_KEYS)[0]['company_size']
                        row['scope_trace'] = candidate.trace(facts, rec, row['max_chars'], products)
                payloads[group] = payload
                collector.save(arm/f'{group}.json', dict(contract_sha256=collector.digest(contract),
                               payload_sha256=collector.digest(payload), payload=payload))
        # Restored base parser consumes the original facts and ignores the diagnostic extension.
        metrics, predictions[name] = hybrid_replay(payloads['dev'], arm)
        stage = payloads['dev']['stage_seconds']
        projected = 6380 + (stage - 246.985) * FACTOR
        within = changes(predictions[name]['head'], predictions[name]['h2'])
        assert all(c['item'] == 'v11' for c in within)
        summary['arms'][name] = dict(metrics=metrics, head_to_h2_changes=within,
                                     dev_stage_seconds=stage, dev_inference_seconds=payloads['dev']['inference_seconds'],
                                     projected_server_seconds_conditional=projected,
                                     within_stage_planning_limit=stage <= STAGE_LIMIT,
                                     dev_h2_fired=sum(r['h2_fired'] for r in payloads['dev']['rows']))
        if name == 'h3':
            summary['arms'][name]['condition_states'] = dict(Counter(r['scope_trace']['state'] for r in payloads['dev']['rows']))
            summary['arms'][name]['competitive_without_condition_support'] = [r['id'] for r in payloads['dev']['rows']
                if r['scope_trace']['competitive_without_condition_support']]
        collector.save(output/'summary.json', summary)
    summary['control_to_h3_changes'] = {name: changes(predictions['control'][name], predictions['h3'][name])
                                        for name in ('head', 'h2')}
    for name in ('head', 'h2'):
        comparison = compare_runs.compare(score, ROOT/'open/dev_labels.csv',
            output/'control'/f'{name}-hybrid.csv', output/'h3'/f'{name}-hybrid.csv', focus=('v11', 'v13'))
        comparison['interpretation'] = 'Different prompts; historical drift_reference is not a pass/fail threshold.'
        collector.save(output/f'{name}-comparison.json', comparison)
    summary['complete'] = True
    summary['note'] = '410 company_size observations only. Hybrid replay is not a new full-pipeline GPU score or adoption.'
    collector.save(output/'summary.json', summary)
    print(json.dumps({name: dict(v11=arm['metrics']['h2']['items']['v11'],
                     stage_seconds=arm['dev_stage_seconds'], within_limit=arm['within_stage_planning_limit'])
                     for name, arm in summary['arms'].items()}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
