"""Recalculate A5 round 2 from its ZIP and original inputs; no model calls."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys
import subprocess
from types import ModuleType
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import script
from experiments.a5_collect_facts import digest, file_hash, UNLABELED_SHA256
from experiments.a5_v11_absence_candidate import observed_absence, verify_company_size
from tools import replay_run, score


def combined_replay():
    ref = 'ae79d5006375ce154f52c57f6f437c8813b57ec7'
    def git_read(path):
        return subprocess.check_output(['git', 'show', f'{ref}:{path}'], cwd=ROOT)
    assert git_read('script.py') == (ROOT / 'script.py').read_bytes()
    assert git_read('experiments/a5_v11_absence_candidate.py') == (ROOT / 'experiments/a5_v11_absence_candidate.py').read_bytes()
    a4_source = git_read('experiments/a4_scope_gate_candidate.py')
    a4 = ModuleType('a4_readonly_audit')
    a4.__file__ = str(ROOT / 'experiments/a4_scope_gate_candidate.py')
    exec(compile(a4_source, f'{ref}:experiments/a4_scope_gate_candidate.py', 'exec'), a4.__dict__)
    a4._SCRIPT = script
    truth = score.load_csv(ROOT / 'open/dev_labels.csv')[0]
    runs, results = {}, {}
    for name, kwargs in [('head', {}), ('h2', {'verify_company_size': verify_company_size}),
                         ('a4', {'postprocess': a4.postprocess}),
                         ('combined', {'postprocess': a4.postprocess, 'verify_company_size': verify_company_size})]:
        rows = replay_run.replay(script, ROOT / 'reports/runs/colab-1789902969401579900/dev-debug',
                                 input_path=str(ROOT / 'open/dev.jsonl'), data_dir=str(ROOT / 'open/data'), **kwargs)['rows']
        runs[name] = {r['id']: tuple(int(r[v]) for v in script.ITEMS) for r in rows}
        results[name] = score.calculate(truth, runs[name])[0]
        if name == 'combined':
            assert replay_run.to_csv_bytes(script, rows) == git_read('reports/team-c/a4-a5-combined/combined-replay/submission.csv')
    changes = Counter()
    for identifier in truth:
        for i, item in enumerate(script.ITEMS):
            expected = runs['h2'][identifier][i] if item == 'v11' else runs['a4'][identifier][i]
            assert runs['combined'][identifier][i] == expected
            if expected != runs['head'][identifier][i]:
                changes[item] += 1
    return dict(source_ref=ref, a4_source_sha256=hashlib.sha256(a4_source).hexdigest(),
                runs=results, changes=dict(changes), combined_csv_bytes_identical=True,
                independent_item_composition_all_4800_cells=True,
                additivity_error=results['combined']['macro_f1']-(results['a4']['macro_f1']+results['h2']['macro_f1']-results['head']['macro_f1']))


def predicate(f):
    return (f['scope'] == 'competitive' and f['qualification'] == 'unrestricted'
            and f['qualification_role'] in ('none', 'checklist', 'legal_reference')
            and f['qualification_complete'] == f['requirements_complete'] == 'yes'
            and f['priority_exception'] == 'no' and f['size_exception'] == 'none')


def failures(facts, rec, chars):
    reasons = []
    if rec.get('input_completeness', {}).get('완전관측') is not True:
        reasons.append('incomplete_input')
    if any((rec.get('dropped_doc_counts') or {}).values()):
        reasons.append('dropped_docs')
    visible = script.build_context(rec, chars)
    if '[Truncated documents; unseen remainder]' in visible:
        reasons.append('truncated')
    if '[Missing documents]' in visible:
        reasons.append('missing_documents')
    for key in ('scope_quote', 'qualification_quote'):
        quote = facts.get(key)
        quote = script.restore_spacing(quote, rec, visible) or quote
        if not (quote and quote.strip() and quote in visible
                and any(quote in d['text'] for d in rec['docs'])):
            reasons.append(key)
    return reasons


def wilson(k, n):
    p, z = k / n, 1.959963984540054
    center = (p + z*z/(2*n)) / (1 + z*z/n)
    width = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1 + z*z/n)
    return [center-width, center+width]


def fisher(a, b, c, d):
    total, successes, n = a+b+c+d, a+c, a+b
    def prob(x):
        return math.comb(successes, x)*math.comb(total-successes, n-x)/math.comb(total, n)
    observed = prob(a)
    return sum(prob(x) for x in range(max(0, n-(total-successes)), min(n, successes)+1)
               if prob(x) <= observed + 1e-12)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert file_hash(ROOT / 'open/train_unlabeled.jsonl') == UNLABELED_SHA256
    dev = list(script.iter_records(str(ROOT / 'open/dev.jsonl')))
    unlabeled = list(script.iter_records(str(ROOT / 'open/train_unlabeled.jsonl'), limit=2000))
    groups = {'dev': dev, 'unlabeled-00': unlabeled[:1000], 'unlabeled-01': unlabeled[1000:]}
    output = dict(zip_name=args.zip.name, zip_sha256=file_hash(args.zip), groups={})
    with zipfile.ZipFile(args.zip) as z:
        contract = json.loads(z.read('facts/contract.json'))
        for path, expected in contract['files'].items():
            assert file_hash(ROOT / path) == expected, path
        output['contract_sha256'] = digest(contract)
        output['source'] = json.loads(z.read('logs/source.json'))
        command = json.loads(z.read('logs/a5-facts-command.json'))
        output['collector_exit_code'] = command['returncode']
        output['collector_wall_seconds'] = command['elapsed_seconds']
        output['runtime'] = json.loads(z.read('logs/runtime.json'))
        output['runtime']['ninja_path'] = '<runtime>/venv/bin/ninja'
        output['stages_seconds'] = {name: json.loads(z.read(name))['elapsed_seconds']
                                   for name in z.namelist() if name.endswith('-command.json')}
        for name, records in groups.items():
            shard = json.loads(z.read(f'facts/{name}.json'))
            payload = shard['payload']
            assert shard['contract_sha256'] == digest(contract)
            assert shard['payload_sha256'] == digest(payload)
            assert [r['id'] for r in records] == [r['id'] for r in payload['rows']]
            first, all_reasons, selected = Counter(), Counter(), []
            full_count = bare_count = 0
            for row, rec in zip(payload['rows'], records):
                facts = script.parse_judgment(row['response_text'], expected_items=script.COMPANY_SIZE_KEYS)[0]['company_size']
                bare, full = predicate(facts), observed_absence(facts, rec, row['max_chars'])
                assert full == row['h2_fired'] and (bare or not full), rec['id']
                bare_count += bare
                full_count += full
                if bare:
                    why = failures(facts, rec, row['max_chars'])
                    assert bool(why) != full
                    if why:
                        first[why[0]] += 1
                        all_reasons.update(why)
                    selected.append(dict(id=rec['id'], fired=full, failed_checks=why,
                                         scope_quote=facts['scope_quote'], qualification_quote=facts['qualification_quote'],
                                         max_chars=row['max_chars'], doc_chars=sum(len(d['text']) for d in rec['docs'])))
            output['groups'][name] = dict(count=len(records), predicate=bare_count, full=full_count,
                retention=full_count/bare_count, first_failure=dict(first), all_failures=dict(all_reasons),
                full_wilson95=wilson(full_count, len(records)), predicate_wilson95=wilson(bare_count, len(records)),
                retention_wilson95=wilson(full_count, bare_count), selected=selected,
                inference_seconds=payload['inference_seconds'], stage_seconds=payload['stage_seconds'],
                model_load_seconds=shard['model_load_seconds'])
        output['saved_summary'] = json.loads(z.read('facts/summary.json'))
    g = output['groups']
    u_full = g['unlabeled-00']['full'] + g['unlabeled-01']['full']
    u_bare = g['unlabeled-00']['predicate'] + g['unlabeled-01']['predicate']
    full_ratio = (u_full/2000)/(g['dev']['full']/200)
    bare_ratio = (u_bare/2000)/(g['dev']['predicate']/200)
    output['ratios'] = dict(full=full_ratio, predicate=bare_ratio,
                           retention=(u_full/u_bare)/(g['dev']['full']/g['dev']['predicate']))
    assert math.isclose(full_ratio, output['saved_summary']['unlabeled_over_dev_rate'])
    assert math.isclose(full_ratio, bare_ratio*output['ratios']['retention'])
    output['u_full_wilson95'] = wilson(u_full, 2000)
    output['u_predicate_wilson95'] = wilson(u_bare, 2000)
    output['retention_fisher_two_sided'] = fisher(14, 27, 17, 16)
    dev_var = (1-3/200)/3
    output['delta_approximation_iid'] = {str(n): dict(
        dev_rse=math.sqrt(dev_var), unlabeled_rse=math.sqrt((1-31/2000)/(n*31/2000)),
        ratio_rse=math.sqrt(dev_var+(1-31/2000)/(n*31/2000)),
        dev_variance_share=dev_var/(dev_var+(1-31/2000)/(n*31/2000))) for n in (2000, 10000, 20000)}
    output['combined_replay'] = combined_replay()
    # Minimal algebra checks for this calculation, independent of observed data.
    assert abs(wilson(0, 10)[0]) < 1e-12
    assert math.isclose(fisher(1, 1, 1, 1), 1)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in output.items() if k not in ('groups', 'combined_replay')}, ensure_ascii=False, indent=2))
    print('combined:', {k: v['macro_f1'] for k, v in output['combined_replay']['runs'].items()}, output['combined_replay']['changes'])
    for name, group in g.items():
        print(name, json.dumps({k: v for k, v in group.items() if k != 'selected'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
