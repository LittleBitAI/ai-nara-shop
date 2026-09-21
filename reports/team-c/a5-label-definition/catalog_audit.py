"""Reproduce brief 3 counts and locate specification evidence; no model or labels."""
from collections import Counter
from itertools import islice
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import script

OUT = Path(__file__).resolve().parent
QUOTES = {
    'PPS-D-000732': ['CPU: Intel® Xeon® 6458Q * 2', 'Clk: 3.1GHz-4.0GHz'],
    'PPS-D-001333': ['나. 품목 및 예정량 : 별첨 입찰품목 및 사양서 참조',
                     '계약은 품목별 단가로 체결합니다.'],
    'PPS-D-002069': ['데스크탑\n\n스탠다드형\n\n41대',
                     'Intel Xeon 6507P 3.5GHz(8-core) * 1EA 이상 제공', '최대 2CPU 장착 가능'],
    'PPS-D-002106': ['56 kg (배터리 포함)', '14.7 ± 0.3 kg',
                     '최대설정가능 비행반경\n\n2km', '프로펠러 크기 및 수\n\n62인치 / 4'],
    'PPS-D-002151': ['240kW 급속충전기2기'],
}


def main():
    audit = json.loads((OUT/'observation-audit.json').read_text(encoding='utf-8'))
    rows = audit['observations']
    _, products = script.load_sme_reference(str(ROOT/'open/data'))
    table = {}
    for fired, name in ((True, 'fired'), (False, 'rejected')):
        subset = [r for r in rows if r['fired'] == fired]
        matches = {r['id']: [p for p in products if p['세부품명번호'] in
                            set(script.CODE10.findall(str(r['meta'].get('세부품명번호목록') or '')))]
                   for r in subset}
        conditional = [identifier for identifier, items in matches.items() if any(p['특이사항'] for p in items)]
        table[name] = dict(count=len(subset), meta_present=sum(bool(r['meta'].get('세부품명번호목록')) for r in subset),
                           code_matched=sum(bool(items) for items in matches.values()),
                           conditional_ids=conditional)
    assert [table['fired'][k] for k in ('count', 'meta_present', 'code_matched')] == [34, 17, 15]
    assert [table['rejected'][k] for k in ('count', 'meta_present', 'code_matched')] == [49, 12, 10]
    assert set(table['fired']['conditional_ids']) == set(QUOTES)
    assert len(table['rejected']['conditional_ids']) == 4
    clause = '중소벤처기업부장관이 지정 공고한 물품'
    clause_ids = {}
    records = {}
    for source, count in (('dev', 200), ('train_unlabeled', 2000)):
        population = list(islice(script.iter_records(str(ROOT/f'open/{source}.jsonl')), count))
        clause_ids[source] = [r['id'] for r in population if r['meta'].get('조항호내용') == clause]
        records.update({r['id']: r for r in population if r['id'] in QUOTES})
    fired_clause_ids = [r['id'] for r in rows if r['fired'] and r['meta'].get('조항호내용') == clause]
    assert fired_clause_ids == ['PPS-DEV-061']
    assert [len(v) for v in clause_ids.values()] == [4, 6]
    evidence = []
    for identifier, quotes in QUOTES.items():
        rec = records[identifier]
        row = next(r for r in rows if r['id'] == identifier)
        clean = {**rec, 'meta': {k: v for k, v in rec['meta'].items() if k != '조항호내용'}}
        prompt = script.build_messages(clean, script.COMPANY_SIZE_PROMPT, row['max_chars'], products)[1]['content']
        matches = [p for p in products if p['세부품명번호'] in
                   set(script.CODE10.findall(str(rec['meta'].get('세부품명번호목록') or '')))]
        spans = []
        for quote in quotes:
            hits = []
            for doc in rec['docs']:
                start = doc['text'].find(quote)
                if start >= 0:
                    assert doc['text'][start:start+len(quote)] == quote
                    hits.append(dict(doc_id=doc['doc_id'], start=start, end=start+len(quote), text=quote,
                                     in_reconstructed_input=quote in prompt))
            assert hits, (identifier, quote)
            spans.extend(hits)
        assert all(hit['in_reconstructed_input'] for hit in spans)
        condition_visible = all(p['특이사항'] in prompt for p in matches if p['특이사항'])
        assert condition_visible
        evidence.append(dict(id=identifier, documents=[d['doc_id'] for d in rec['docs']],
                             input_completeness=rec['input_completeness'], catalog=matches,
                             conditions_in_reconstructed_input=condition_visible, evidence=spans))
    result = dict(model_called=False, source_zip_sha256=audit['source_zip_sha256'],
                  catalogue_rows=len(products), coded_rows=sum(bool(p['세부품명번호']) for p in products),
                  conditional_rows=sum(bool(p['특이사항']) for p in products),
                  counts=table, clause_population_ids=clause_ids, fired_clause_ids=fired_clause_ids,
                  fired_clause_counts=dict(Counter(r['meta']['조항호내용'] for r in rows if r['fired'])),
                  cases=evidence)
    assert (result['catalogue_rows'], result['coded_rows'], result['conditional_rows']) == (616, 615, 185)
    (OUT/'catalog-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(table, ensure_ascii=False))


if __name__ == '__main__':
    main()
