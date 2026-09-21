"""Independent CPU-only stage audit for brief 4. Does not load the other analysis branch."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import script
from tools import replay_run, score
from experiments import a4_a5_combined_candidate as combined
from experiments.a5_v11_absence_candidate import verify_company_size as h2

OUT = Path(__file__).resolve().parent
CASE = ROOT/'reports/runs/colab-1789902969401579900/dev-debug'
PILOT = ROOT/'reports/runs/a5-scope-1789959906563639676/pilot/episode-1'
ITEMS = ('v10', 'v13', 'v18', 'v20', 'v24')


def main():
    started = time.perf_counter()
    combined._a4._SCRIPT = script
    records = {r['id']: r for r in script.iter_records(str(ROOT/'open/dev.jsonl'))}
    truth = score.load_csv(ROOT/'open/dev_labels.csv')[0]
    texts = replay_run.saved_responses(CASE)
    events = [json.loads(line) for line in (CASE/'diagnostics.jsonl').read_text(encoding='utf-8').splitlines()]
    budgets = {e['id']: e['max_chars'] for e in events if e['event'] == 'company_size_input'}
    _, products = script.load_sme_reference(str(ROOT/'open/data'))
    traced = {}

    def capture(facts, rec, chars):
        stages = {}
        def profile(frame, event, result):
            if event != 'return' or frame.f_globals.get('__name__') != 'script':
                return
            if frame.f_code.co_name == 'verify_document_requirements':
                local = frame.f_locals
                stages['document_checks'] = dict(complete=local['complete'], software_complete=local['software_complete'],
                                                 checks=local['checks'], writes=deepcopy(result))
            elif frame.f_code.co_name == 'verify_company_size':
                stages['normalized_facts'] = deepcopy(frame.f_locals['facts'])
        previous = sys.getprofile()
        try:
            sys.setprofile(profile)
            writes, reason = script.verify_company_size(facts, rec, chars)
        finally:
            sys.setprofile(previous)
        visible = script.build_context(rec, chars)
        def quotation(quote):
            fixed = script.restore_spacing(quote, rec, visible) or quote
            return dict(raw=quote, restored=fixed, in_visible=bool(fixed and fixed in visible),
                        in_document=bool(fixed and any(fixed in d['text'] for d in rec['docs'])))
        stages.update(raw_facts=deepcopy(facts), company_writes=deepcopy(writes), band_reason=reason,
                      chars=chars, truncated='[Truncated documents; unseen remainder]' in visible,
                      missing='[Missing documents]' in visible, input_completeness=rec.get('input_completeness'),
                      dropped=rec.get('dropped_doc_counts'),
                      quotes={k: quotation(v) for k, v in facts.items() if k.endswith('_quote')})
        traced[rec['id']] = stages
        return writes, reason

    runs, predictions = {}, {}
    def replay(name, **kwargs):
        rows = replay_run.replay(script, CASE, input_path=str(ROOT/'open/dev.jsonl'),
                                 data_dir=str(ROOT/'open/data'), **kwargs)['rows']
        pred = {r['id']: tuple(int(r[v]) for v in script.ITEMS) for r in rows}
        runs[name] = score.calculate(truth, pred)[0]
        predictions[name] = pred
        return replay_run.to_csv_bytes(script, rows)
    assert replay('head', verify_company_size=capture) == (OUT/'head-replay/submission.csv').read_bytes()
    replay('a4', postprocess=combined.postprocess)
    replay('h2', verify_company_size=h2)
    assert replay('combined', postprocess=combined.postprocess, verify_company_size=combined.verify_company_size) == (
        ROOT/'reports/team-c/a4-a5-combined/combined-replay/submission.csv').read_bytes()
    errors, rows = {}, []
    for item in ITEMS:
        index = script.ITEMS.index(item)
        assert all(predictions['head'][i][index] == predictions['combined'][i][index] for i in truth)
        errors[item] = {kind: sorted(i for i in truth if (truth[i][index], predictions['head'][i][index]) == pair)
                        for kind, pair in [('tp', (1, 1)), ('fp', (0, 1)), ('fn', (1, 0))]}
    for identifier, rec in records.items():
        raw = script.parse_judgment(texts['baseline'][identifier])[0]
        after_sme = deepcopy(raw)
        sme = None
        if identifier in texts['sme']:
            parsed = script.parse_judgment(texts['sme'][identifier], expected_items=script.SME_ITEMS, sme=True)[0]
            verified, why = script.verify_sme(parsed, rec, products, 16000)
            sme = dict(raw=parsed, writes=verified, reasons=why)
            after_sme.update(verified)
        after_company = {**after_sme, **traced[identifier]['company_writes']}
        final = script.postprocess(deepcopy(after_company), rec)
        assert tuple(final[v]['위반여부'] for v in script.ITEMS) == predictions['head'][identifier]
        demand, codes = script.direct_production_demand(rec)
        industry_spans = []
        for doc in rec['docs']:
            for found in re.finditer(r'업종\s*코드\s*[:：]?\s*(\d{4})(?!\d)', doc['text']):
                start, end = max(0, found.start()-70), min(len(doc['text']), found.end()+100)
                industry_spans.append(dict(code=found[1], doc_id=doc['doc_id'], start=start, end=end, text=doc['text'][start:end]))
        rows.append(dict(id=identifier, truth={v: truth[identifier][script.ITEMS.index(v)] for v in ITEMS},
                         baseline={v: raw[v] for v in ITEMS}, sme=sme,
                         after_sme={v: after_sme[v] for v in ITEMS}, company=traced[identifier],
                         before_postprocess={v: after_company[v] for v in ITEMS}, final={v: final[v] for v in ITEMS},
                         meta=rec['meta'], direct_demand=demand, demand_codes=sorted(codes),
                         catalog_gate=script.competitive_product(rec, codes), industry_spans=industry_spans,
                         documents=[dict(doc_id=d['doc_id'], type=d['type'], chars=len(d['text'])) for d in rec['docs']]))
    error_sets = {v: set(errors[v]['fp']+errors[v]['fn']) for v in ITEMS}
    overlaps = {v: {w: len(error_sets[v] & error_sets[w]) for w in ITEMS} for v in ITEMS}
    pilot_rows = {name: json.loads((PILOT/name/'dev.json').read_text(encoding='utf-8'))['payload']['rows'] for name in ('control', 'h3')}
    pilot_facts = {name: {r['id']: (script.parse_judgment(r['response_text'], expected_items=script.COMPANY_SIZE_KEYS)[0]['company_size'], r['max_chars'])
                          for r in values} for name, values in pilot_rows.items()}
    field_groups = {'scope_only': ('scope', 'scope_quote'),
                    'qualification_only': ('qualification', 'qualification_role', 'qualification_quote', 'qualification_complete'),
                    'requirements_only': ('requirements_complete', 'direct_production_quote'),
                    'priority_only': ('priority_exception', 'priority_exception_quote'),
                    'software_only': ('software_business', 'software_business_quote', 'software_participation_quote')}
    for name in ('control', 'h3', *field_groups):
        def verifier(_, rec, __):
            facts, chars = pilot_facts['h3' if name == 'h3' else 'control'][rec['id']]
            if name in field_groups:
                facts = {**facts, **{k: pilot_facts['h3'][rec['id']][0][k] for k in field_groups[name]}}
            return script.verify_company_size(facts, rec, chars)
        csv = replay('pilot_'+name, verify_company_size=verifier)
        if name in ('control', 'h3'):
            assert csv == (PILOT/name/'head-hybrid.csv').read_bytes()
    delta_cells = {name: [dict(id=i, item=v, before=predictions['head'][i][j], after=pred[i][j])
                         for i in truth for j, v in enumerate(script.ITEMS) if pred[i][j] != predictions['head'][i][j]]
                   for name, pred in predictions.items() if name in ('a4', 'h2', 'combined')}
    industry = []
    for row in rows:
        registered = sorted(set(re.findall(r'\((\d{4})\)', row['meta'].get('면허업종제한목록') or '')))
        explicit = sorted({span['code'] for span in row['industry_spans']})
        if explicit and registered != explicit:
            industry.append(dict(id=row['id'], registered=registered, explicit_body_codes=explicit,
                                 registration_flag=row['meta'].get('업종제한여부'), truth=row['truth']['v24'],
                                 prediction=row['final']['v24']['위반여부']))
    pilot_changes = {name: [dict(id=i, item=v, truth=truth[i][j], before=predictions['pilot_control'][i][j], after=pred[i][j])
                           for i in truth for j, v in enumerate(script.ITEMS) if pred[i][j] != predictions['pilot_control'][i][j]]
                     for name, pred in predictions.items() if name.startswith('pilot_')}
    result = dict(round_id='a5-brief4-independent-cpu', status='completed',
                  recorded_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.perf_counter()-started,
                  environment=dict(python=platform.python_version(), system=platform.system(), machine=platform.machine()),
                  command='python -X utf8 reports/team-c/a5-label-definition/five_stuck_audit.py',
                  basis_commit='434f5182ca8e921218d40cbd103fa2c361b7bbeb', model_called=False,
                  other_analysis_branch_read=False, runs=runs, errors=errors, error_overlap=overlaps,
                  error_union=len(set.union(*error_sets.values())), delta_cells=delta_cells,
                  unchanged_target_cells=1000, observations=rows,
                  pilot_field_swap_note='CPU counterfactuals on different model outputs, not deployable rules, causal proof or new GPU performance.',
                  pilot_field_groups=field_groups,
                  pilot_changed_cells=pilot_changes, industry_lexical_candidates=industry,
                  industry_note='Lexical retrieval only: OR branches and omitted codes require source inspection; not a classifier.',
                  pilot_budget_changed=sum(pilot_facts['control'][i][1] != pilot_facts['h3'][i][1] for i in truth),
                  pilot_field_changes={key: sum(pilot_facts['control'][i][0][key] != pilot_facts['h3'][i][0][key] for i in truth)
                                       for key in next(iter(pilot_facts['control'].values()))[0]},
                  sources={p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                           [ROOT/'script.py', CASE/'diagnostics.jsonl', ROOT/'open/dev.jsonl', ROOT/'open/dev_labels.csv',
                            OUT/'head-replay/submission.csv', ROOT/'reports/team-c/a4-a5-combined/combined-replay/submission.csv',
                            PILOT/'control/dev.json', PILOT/'h3/dev.json', Path(__file__),
                            ROOT/'experiments/a4_scope_gate_candidate.py', ROOT/'experiments/a5_v11_absence_candidate.py',
                            ROOT/'experiments/a4_a5_combined_candidate.py']})
    (OUT/'five-stuck-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({v: {k: len(ids) for k, ids in by.items()} for v, by in errors.items()}, ensure_ascii=False))
    print('overlap', overlaps, 'union', result['error_union'])
    print('runs', {k: r['macro_f1'] for k, r in runs.items()})


if __name__ == '__main__':
    main()
