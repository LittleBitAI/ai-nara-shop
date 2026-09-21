"""CPU evidence inventory for all 83 predicate-positive observations; no new labels."""
from collections import Counter
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import script

OUT = Path(__file__).resolve().parent
TERMS = re.compile(r'중\s*소\s*기\s*업|중\s*기\s*업|대\s*기\s*업|소\s*기\s*업|소\s*상\s*공\s*인|비영리|우선\s*조달|유찰|직접\s*생산|\d+\s*[kK][wW]')


def snippets(rec):
    hits = []
    for doc in rec['docs']:
        spans = []
        for found in TERMS.finditer(doc['text']):
            start, end = max(0, found.start()-90), min(len(doc['text']), found.end()+170)
            if spans and start <= spans[-1][1]:
                spans[-1][1] = max(spans[-1][1], end)
            else:
                spans.append([start, end])
        for start, end in spans:
            hits.append(dict(doc_id=doc['doc_id'], start=start, end=end, text=doc['text'][start:end]))
    return hits


def main():
    audit = json.loads((OUT/'round2-audit.json').read_text(encoding='utf-8'))
    selected = {r['id']: (group, r) for group, info in audit['groups'].items() for r in info['selected']}
    _, products = script.load_sme_reference(str(ROOT/'open/data'))
    zip_path = ROOT/'artifacts/inbox'/audit['zip_name']
    with zipfile.ZipFile(zip_path) as z:
        facts = {r['id']: script.parse_judgment(r['response_text'], expected_items=script.COMPANY_SIZE_KEYS)[0]['company_size']
                 for name in audit['groups'] for r in json.loads(z.read(f'facts/{name}.json'))['payload']['rows']}
    distributions = {group: Counter() for group in ('dev', 'first_2000', 'remaining_18000')}
    observations = []
    audit_records = {}
    for source in ('dev', 'train_unlabeled'):
        for index, rec in enumerate(script.iter_records(str(ROOT/f'open/{source}.jsonl'))):
            population = 'dev' if source == 'dev' else ('first_2000' if index < 2000 else 'remaining_18000')
            counts = distributions[population]
            counts['count'] += 1
            chars = sum(len(d['text']) for d in rec['docs'])
            band = '<=8000' if chars <= 8000 else ('8001..16000' if chars <= 16000 else ('16001..32000' if chars <= 32000 else '>32000'))
            counts[f'doc_chars:{band}'] += 1
            for key in ('업무구분', '적용계약법', '계약방법', '소관구분'):
                counts[f'{key}:{rec["meta"].get(key)}'] += 1
            visible = script.build_context(rec, 16000)
            counts['truncated_at_16000'] += '[Truncated documents; unseen remainder]' in visible
            counts['input_complete'] += rec.get('input_completeness', {}).get('완전관측') is True
            if rec['id'] not in selected:
                continue
            group, entry = selected[rec['id']]
            audit_records[rec['id']] = rec
            text = '\n'.join(d['text'] for d in rec['docs'])
            flat = re.sub(r'\s+', '', text)
            body_codes = set(script.CODE10.findall(text))
            meta_codes = set(script.CODE10.findall(str(rec['meta'].get('세부품명번호목록') or '')))
            matches = []
            for row in products:
                name = re.sub(r'\s+', '', row['세부품명'])
                sources = []
                if row['세부품명번호'] in body_codes:
                    sources.append('body_code')
                if row['세부품명번호'] in meta_codes:
                    sources.append('meta_code')
                if len(name) >= 4 and name in flat:
                    sources.append('body_name')
                if sources:
                    matches.append(dict(code=row['세부품명번호'], name=row['세부품명'], conditions=row['특이사항'], sources=sources))
            observations.append(dict(group=group, **entry, facts=facts[rec['id']], meta=rec['meta'],
                                     documents=[dict(doc_id=d['doc_id'], type=d['type'], chars=len(d['text'])) for d in rec['docs']],
                                     catalog_mentions_not_applicability=matches, qualification_and_exception_snippets=snippets(rec)))
    assert len(observations) == 83
    for row in observations:
        docs = {d['doc_id']: d['text'] for d in audit_records[row['id']]['docs']}
        for hit in row['qualification_and_exception_snippets']:
            assert docs[hit['doc_id']][hit['start']:hit['end']] == hit['text']
    def locate(identifier, quote):
        result = []
        for doc in audit_records[identifier]['docs']:
            start = doc['text'].find(quote)
            if start >= 0:
                result.append(dict(id=identifier, doc_id=doc['doc_id'], start=start,
                                   end=start+len(quote), text=quote))
        assert result, (identifier, quote)
        return result
    charger = next(p for p in products if p['세부품명번호'] == '2611170403')
    assert charger['특이사항'] == '50kW 이하에 한함'
    assert selected['PPS-D-002151'][1]['fired']
    assert not selected['PPS-D-000860'][1]['fired']
    rec = audit_records['PPS-D-002151']
    rec = {**rec, 'meta': {k: v for k, v in rec['meta'].items() if k != '조항호내용'}}
    prompt = script.build_messages(rec, script.COMPANY_SIZE_PROMPT,
                                   selected['PPS-D-002151'][1]['max_chars'], products)[1]['content']
    assert '50kW 이하에 한함' in prompt and '240kW 급속충전기2기' in prompt
    counterexamples = dict(
        charger=dict(catalog=charger, evidence=locate('PPS-D-002151', '240kW 급속충전기2기'),
                     both_condition_and_spec_in_reconstructed_input=True,
                     conclusion='scope=competitive conflicts with the supplied catalogue capacity condition'),
        pump=dict(evidence=locate('PPS-D-000860', '중소기업자간 경쟁제품(완제품) 구매 사업이 아닙니다.'),
                  conclusion='scope=competitive conflicts with the notice; current truncation guard prevents H2 firing'))
    coverage = Counter()
    for row in observations:
        row['audit_disposition'] = ('rejected_by_observation_guard' if not row['fired'] else
                                    'scope_semantics_unresolved')
        if row['id'] == 'PPS-D-002151':
            row['audit_disposition'] = 'scope_condition_contradicted'
        if row['id'] == 'PPS-D-000860':
            row['audit_disposition'] = 'guard_rejected_and_scope_refuted_in_notice'
        if row['id'] == 'PPS-DEV-040':
            row['audit_disposition'] = 'known_dev_false_positive'
        if row['id'] in ('PPS-DEV-061', 'PPS-DEV-062'):
            row['audit_disposition'] = 'known_dev_true_positive'
        coverage['fired' if row['fired'] else 'rejected'] += 1
        if row['fired']:
            matches = row['catalog_mentions_not_applicability']
            kind = 'no_literal_catalog_mention' if not matches else (
                'has_body_catalog_mention' if any('body_code' in m['sources'] or 'body_name' in m['sources'] for m in matches)
                else 'only_meta_catalog_mention')
            coverage[kind] += 1
    result = dict(source_zip_sha256=audit['zip_sha256'], model_called=False, count=83,
                  note='Catalogue mentions and keyword windows are evidence locations, not legal decisions or labels.',
                  coverage=dict(coverage), counterexamples=counterexamples,
                  distributions={k: dict(v) for k, v in distributions.items()}, observations=observations)
    result['shortcut_checks'] = dict(
        existing_helper_with_charger_code=script.competitive_product(audit_records['PPS-D-002151'], {'2611170403'}),
        existing_helper_with_direct_production_codes={identifier: script.competitive_product(
            audit_records[identifier], script.direct_production_demand(audit_records[identifier])[1])
            for identifier in ('PPS-DEV-040', 'PPS-DEV-061', 'PPS-DEV-062')})
    assert result['shortcut_checks']['existing_helper_with_charger_code'] is True
    assert all(value is None for value in result['shortcut_checks']['existing_helper_with_direct_production_codes'].values())
    (OUT/'observation-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(result['distributions'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
