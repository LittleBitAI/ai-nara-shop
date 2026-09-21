"""A8 주입 계약. 프롬프트만 바뀌고 소비 경로는 그대로임을 CPU에서 확인한다.

여기서 통과해도 실제 토큰 수·GPU 성능·v20 TP 회복은 미측정이다.
"""
import csv
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unicodedata
import unittest
from unittest.mock import patch

import script
from experiments import a5_scope_pilot as pilot
from experiments import a8_v20_annex as candidate
from experiments import a8_v20_audit as audit
from experiments import law_index
from tests.test_a5_collect_facts import FakeRunner, records

BASELINE_CSV = pilot.ROOT/'reports/team-c/a5-label-definition/head-replay/submission.csv'
# H4 재생의 v20. 새 control 결과와 구분한다.
H4_V20 = dict(tp=['PPS-DEV-133'], fp=['PPS-DEV-056', 'PPS-DEV-064', 'PPS-DEV-068', 'PPS-DEV-144'],
              fn=['PPS-DEV-24', 'PPS-DEV-131', 'PPS-DEV-132', 'PPS-DEV-134'])


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as source:
        return {row['id']: row for row in csv.DictReader(source)}


def h4_payload():
    events = [json.loads(line) for line in (pilot.CASE/'diagnostics.jsonl').read_text(encoding='utf-8').splitlines()]
    chars = {e['id']: e['max_chars'] for e in events if e['event'] == 'company_size_input'}
    texts = pilot.replay_run.saved_responses(pilot.CASE)['company_size']
    return dict(rows=[dict(id=r['id'], response_text=texts[r['id']], max_chars=chars[r['id']])
                      for r in script.iter_records(str(pilot.ROOT/'open/dev.jsonl'))])


class CountingRunner:
    """글자 수로 세는 가짜 토크나이저. 실제 토큰 근거가 아니며 그렇게 보고한다."""
    MODE = 'test_double'
    environment = {'chat_template_sha256': 'test-double'}

    def count_tokens(self, messages):
        return sum(len(m['content']) for m in messages)


class AnnexBlockTests(unittest.TestCase):
    def test_block_is_the_provided_text_and_keeps_the_20억원_row(self):
        article, annex = candidate.segments()
        raw = law_index.laws(candidate.DATA_DIR)[law_index.resolve_law(candidate.LAW, candidate.DATA_DIR)]
        self.assertEqual((len(article.text), len(annex.text)), (305, 629))
        for segment in (article, annex):
            self.assertIn(segment.text, raw)
            self.assertIn(segment.text, candidate.block())
        for floor in ('80억원', '40억원', '20억원'):
            self.assertIn(floor, annex.text)
        self.assertIn('법 제48조제2항', article.text)

    def test_activate_changes_only_the_prompt_and_restores_on_failure(self):
        prompt, schema = script.COMPANY_SIZE_PROMPT, script.company_size_schema()
        empty = json.dumps({'company_size': script.empty_company_size()})
        with self.assertRaisesRegex(RuntimeError, 'restore'):
            with candidate.activate():
                self.assertTrue(script.COMPANY_SIZE_PROMPT.startswith(prompt))
                self.assertTrue(script.COMPANY_SIZE_PROMPT.endswith(candidate.block()))
                self.assertEqual(script.company_size_schema(), schema)
                self.assertEqual(list(script.COMPANY_SIZE_KEYS), ['company_size'])
                # 새 필드를 요구하지 않는다. 기존 응답이 그대로 통과해야 한다.
                script.parse_judgment(empty, expected_items=script.COMPANY_SIZE_KEYS)
                raise RuntimeError('restore')
        self.assertEqual(script.COMPANY_SIZE_PROMPT, prompt)

    def test_missing_mangled_or_shortened_segments_stop_before_injection(self):
        article, annex = candidate.segments()
        cases = [
            (dict(resolve_law=lambda *a, **k: None), '찾지 못했다'),
            (dict(article=lambda *a, **k: None), '빈 조각'),
            (dict(annex=lambda *a, **k: annex._replace(text='  ')), '빈 조각'),
            (dict(article=lambda *a, **k: article._replace(text='제2조(사업금액의 하한) 임의로 지어낸 조문')), '부분문자열'),
            # 20억원 행 앞에서 잘린 조각. 원문의 부분문자열이라 길이 검사만으로는 통과한다.
            (dict(annex=lambda *a, **k: annex._replace(text=annex.text[:annex.text.index('20억원')])), '하한 행'),
        ]
        for attributes, message in cases:
            with self.subTest(message=message):
                with patch.multiple(candidate.law_index, **attributes):
                    with self.assertRaisesRegex(ValueError, message):
                        candidate.segments()

    def test_activate_touches_nothing_the_replay_reads(self):
        """정적 불변만 잰다 — 소비자를 안 바꿨으니 바이트는 같을 수밖에 없다.

        법령 유출은 이 재생이 아니라 `LawQuotationTests`의 결정적 스윕이 잡는다.
        """
        payload = h4_payload()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            metrics, predictions = pilot.hybrid_replay(payload, output, experiment='a8')
            baseline = BASELINE_CSV.read_bytes()
            for variant in ('off', 'on'):
                # v13 근거 수리로 보관 CSV와 세 셀이 일부러 갈렸다. v20 은 그대로다.
                self.assertEqual(pilot.replay_run.csv_cell_diff((output/f'{variant}-hybrid.csv').read_bytes(), baseline),
                                 [('PPS-DEV-148', 'e13'), ('PPS-DEV-16', 'v13'), ('PPS-DEV-198', 'v13')])
                item = metrics[variant]['items']['v20']
                self.assertEqual((item['tp'], item['fp'], item['fn']), (1, 4, 4))
            self.assertEqual(pilot.changes(predictions['off'], predictions['on']), [])

    def test_reachable_v20_tp_ceiling_on_the_fixed_case_is_two(self):
        truth, predicted = read_csv(pilot.ROOT/'open/dev_labels.csv'), read_csv(BASELINE_CSV)
        cells = {kind: sorted(i for i in truth if truth[i]['v20'] == positive and predicted[i]['v20'] == prediction)
                 for kind, positive, prediction in (('tp', '1', '1'), ('fp', '0', '1'), ('fn', '1', '0'))}
        self.assertEqual({k: sorted(v) for k, v in H4_V20.items()}, cells)
        texts = pilot.replay_run.saved_responses(pilot.CASE)['company_size']
        by_id = {r['id']: r for r in script.iter_records(str(pilot.ROOT/'open/dev.jsonl'))}
        blocked_by_input, reachable = [], []
        for identifier in cells['fn']:
            rec = by_id[identifier]
            facts = script.parse_judgment(texts[identifier], expected_items=script.COMPANY_SIZE_KEYS)[0]['company_size']
            # 프롬프트가 못 바꾸는 입력 사실이면 주입으로 양성이 될 수 없다.
            if rec['input_completeness']['완전관측'] is not True or any((rec['dropped_doc_counts'] or {}).values()):
                blocked_by_input.append(identifier)
            else:
                reachable.append((identifier, facts['software_business']))
        self.assertEqual(blocked_by_input, sorted(['PPS-DEV-24', 'PPS-DEV-131', 'PPS-DEV-134']))
        self.assertEqual(reachable, [('PPS-DEV-132', 'no')])
        self.assertEqual(len(cells['tp']) + len(reachable), 2)


class ReservationTests(unittest.TestCase):
    """줄인 출력 예약이 두 군 공통이고, 관측 출력과 재시도를 살려 두는지 본다."""

    def h4(self):
        events = [json.loads(line) for line in (pilot.CASE/'diagnostics.jsonl').read_text(encoding='utf-8').splitlines()]
        prompts = [e['prompt_tokens'] for e in events if e['event'] == 'company_size_input']
        outputs = [e['output_tokens'] for e in events if e['event'] == 'response'
                   and e.get('phase') == 'company_size' and isinstance(e.get('output_tokens'), int)]
        stops = {e.get('finish_reason') for e in events if e['event'] == 'response'
                 and e.get('phase') == 'company_size'}
        return prompts, outputs, stops

    def test_reservation_keeps_twice_the_observed_output_and_frees_prompt_budget(self):
        prompts, outputs, stops = self.h4()
        self.assertEqual((len(prompts), len(outputs)), (200, 200))
        self.assertEqual(stops, {'stop'})  # 관측 출력이 상한에 걸린 응답이 없어야 예약을 줄일 수 있다.
        self.assertGreaterEqual(candidate.OUTPUT_RESERVED, 2 * max(outputs))
        self.assertEqual(candidate.PROMPT_BUDGET, script.MAX_MODEL_LEN - candidate.OUTPUT_RESERVED - 64)
        self.assertGreater(candidate.PROMPT_BUDGET, script.PROMPT_BUDGET)
        # 운영 예산에서는 최악 공고에 22토큰만 남아 어떤 블록도 들어가지 못한다.
        self.assertLess(script.PROMPT_BUDGET - max(prompts), 100)
        self.assertGreaterEqual(candidate.PROMPT_BUDGET - max(prompts), 1000)

    def test_split_retry_still_has_room_for_the_observed_output(self):
        prompts, outputs, _ = self.h4()
        block_ceiling = candidate.PROMPT_BUDGET - max(prompts)
        # 분할 재시도는 system 메시지에 출력범위 문장을 덧붙인 뒤 출력 예산을 다시 계산한다.
        suffix = ('\n[Output scope for this call] Evaluate only these keys, overriding the earlier key list: '
                  + ', '.join(script.COMPANY_SIZE_KEYS)
                  + '. Return no other keys. Keep evidence quotations under 100 characters.')
        suffix_ceiling = len(suffix)  # 영어 1자=1토큰보다 나쁠 수 없다. 보수적 상한이다.
        left = script.MAX_MODEL_LEN - (max(prompts) + block_ceiling + suffix_ceiling) - 64
        self.assertGreater(left, max(outputs))

    def test_both_arms_get_the_same_reduced_budget(self):
        self.assertEqual(pilot.output_reserved('a8'), candidate.OUTPUT_RESERVED)
        self.assertEqual(pilot.prompt_budget('a8'), candidate.PROMPT_BUDGET)
        for experiment in ('h3', 'v18'):
            self.assertEqual(pilot.output_reserved(experiment), script.MAX_TOKENS)
            self.assertEqual(pilot.prompt_budget(experiment), script.PROMPT_BUDGET)


class MeasuredBudgetTests(unittest.TestCase):
    """기록된 CPU 실측이 지금 코드의 블록·예산과 같은 것을 재고 있는지 본다."""

    def test_recorded_measurement_matches_this_block_and_passes(self):
        measured = json.loads((pilot.ROOT/'reports/team-c/a8-v20-annex/budget-cpu.json')
                              .read_text(encoding='utf-8'))
        # 블록 글자가 바뀌면 이 검사가 먼저 깨진다. 낡은 실측으로 GPU 를 돌리지 않는다.
        self.assertEqual(measured['reference_sha256'],
                         hashlib.sha256(candidate.block().encode('utf-8')).hexdigest())
        self.assertEqual(measured['reference_chars'], len(candidate.block()))
        self.assertEqual(measured['prompt_budget'], candidate.PROMPT_BUDGET)
        self.assertEqual(measured['output_reserved'], candidate.OUTPUT_RESERVED)
        self.assertEqual(measured['token_count_kind'], 'actual')
        self.assertEqual(measured['model_revision'], script.MODEL_REVISION)
        self.assertEqual(measured['records'], 200)
        # 블록은 공고마다 같은 값이어야 한다. 다르면 문서가 깎인 것이다.
        block_tokens = measured['block_tokens']
        self.assertEqual((measured['added_tokens_min'], measured['added_tokens_max']),
                         (block_tokens, block_tokens))
        self.assertEqual(measured['additional_shrink'], [])
        self.assertEqual(measured['visible_differs'], [])
        self.assertEqual(measured['candidate_truncated'], [])
        self.assertTrue(measured['conditions_pass'])
        self.assertTrue(measured['budget_safety_evidence'])
        worst = max(row['candidate']['prompt_tokens'] for row in measured['rows'])
        self.assertLessEqual(worst, candidate.PROMPT_BUDGET)
        # 분할 재시도까지 포함한 여유. 관측 최대 출력 494 보다 커야 한다.
        self.assertGreater(script.MAX_MODEL_LEN - worst - 64, 494)


class LawQuotationTests(unittest.TestCase):
    """주입한 조문을 모델이 공고 인용 자리에 넣어도 v20을 움직이지 못해야 한다."""

    # 인용을 담을 수 있는 company_size 필드 전부. 하나라도 빠지면 스윕이 표면을 덜 잰다.
    QUOTE_FIELDS = ('scope_quote', 'qualification_quote', 'priority_exception_quote',
                    'size_exception_quote', 'direct_production_quote',
                    'software_business_quote', 'software_participation_quote')
    # 별표 1의 실제 부분문자열. 모델이 복사하기 가장 쉬운 꼴이다.
    LAW_SPAN = '「중소기업기본법」제2조의 중소기업'

    def facts_for(self, identifier):
        texts = pilot.replay_run.saved_responses(pilot.CASE)['company_size']
        rec = {r['id']: r for r in script.iter_records(str(pilot.ROOT/'open/dev.jsonl'))}[identifier]
        facts = script.parse_judgment(texts[identifier], expected_items=script.COMPANY_SIZE_KEYS)[0]['company_size']
        return facts, rec, script.build_context(rec, 16000)

    def sweep(self):
        """공고 200건 × 인용 필드 7개. 법령 문자열이 근거로 박히는 셀을 항목별로 센다.

        카탈로그 전역(`_PRODUCTS`)을 실제 파이프라인처럼 채운 뒤 잰다 — 안 채우면
        `competitive_product()`가 None 이라 v13 경로가 닫히고 스윕이 0을 돌려준다.
        """
        _, products = script.load_sme_reference(str(pilot.ROOT/'open/data'))
        events = [json.loads(line) for line in (pilot.CASE/'diagnostics.jsonl').read_text(encoding='utf-8').splitlines()]
        chars = {e['id']: e['max_chars'] for e in events if e['event'] == 'company_size_input'}
        texts = pilot.replay_run.saved_responses(pilot.CASE)['company_size']
        planted = {}
        for rec in script.iter_records(str(pilot.ROOT/'open/dev.jsonl')):
            facts = script.parse_judgment(texts[rec['id']], expected_items=script.COMPANY_SIZE_KEYS)[0]['company_size']
            for field in self.QUOTE_FIELDS:
                out, _ = script.verify_company_size(dict(facts, **{field: self.LAW_SPAN}), rec, chars[rec['id']])
                for item, cell in out.items():
                    if cell['위반여부'] == 1 and cell['근거문구'] and self.LAW_SPAN in str(cell['근거문구']):
                        planted.setdefault(field, {}).setdefault(item, []).append(rec['id'])
        return planted

    def test_no_quote_field_accepts_the_law_as_evidence(self):
        """인용 필드 일곱 중 어디에 법령을 넣어도 24항목의 근거로 서지 못한다.

        `company_size_products()`가 검증된 인용을 요구하게 된 뒤의 계약이다. 그 전에는
        `qualification_quote` → v13 9셀이 열려 있었다.
        """
        self.assertIn(self.LAW_SPAN, candidate.segments()[1].text)
        self.assertIn(self.LAW_SPAN, candidate.block())
        self.assertEqual(self.sweep(), {})

    def facts_and_records(self):
        """카탈로그 전역을 채운 뒤 H4 사실·공고·실제 max_chars 를 함께 돌려준다."""
        script.load_sme_reference(str(pilot.ROOT/'open/data'))
        events = [json.loads(line) for line in (pilot.CASE/'diagnostics.jsonl').read_text(encoding='utf-8').splitlines()]
        chars = {e['id']: e['max_chars'] for e in events if e['event'] == 'company_size_input'}
        texts = pilot.replay_run.saved_responses(pilot.CASE)['company_size']
        for rec in script.iter_records(str(pilot.ROOT/'open/dev.jsonl')):
            facts = script.parse_judgment(texts[rec['id']], expected_items=script.COMPANY_SIZE_KEYS)[0]['company_size']
            yield facts, rec, chars[rec['id']]

    def test_role_and_quote_together_no_longer_open_new_v13_positives(self):
        """실제 모델은 분류·역할·인용을 한 응답에서 함께 낸다. 그 결합 경로가 닫혔는지 본다.

        라운드 2 리뷰의 P1이다. 수리 전에는 `qualification_role=eligibility` +
        `qualification=small_only` + 법령 인용을 함께 넣으면 v13 이 9 → 33셀로 열리고
        신규 24셀(정답 23×0 / 1×1)이 전부 법령을 근거로 썼다. scope 는 건드리지 않는다 —
        H4 의 `competitive` 78건이 그대로 후보군이다.
        """
        base, combined = {}, {}
        for facts, rec, max_chars in self.facts_and_records():
            before, _ = script.verify_company_size(facts, rec, max_chars)
            after, _ = script.verify_company_size(
                dict(facts, qualification_role='eligibility', qualification='small_only',
                     qualification_quote=self.LAW_SPAN), rec, max_chars)
            if 'v13' in before:
                base[rec['id']] = before['v13']
            if 'v13' in after:
                combined[rec['id']] = after['v13']
        # 수리 뒤 기준선은 검증된 인용을 가진 6셀이고, 법령으로 바꾸면 그 6셀마저 선다는 근거를 잃는다.
        self.assertEqual(len(base), 6)
        self.assertEqual(combined, {})
        self.assertEqual([i for i in combined if i not in base], [])

    def test_no_evidence_column_of_the_final_csv_ever_holds_the_law(self):
        """소비자 하나가 아니라 **최종 CSV** 로 잰다 — `근거문구` 를 쓰는 자리가 여럿이다.

        `verify_company_size` 만 보는 스윕은 `_company_size_bands`(script.py:815)나
        추가 호출 소비자(script.py:1278)처럼 모델 인용을 근거로 쓰는 다른 자리를 못 본다.
        저장 company 응답의 인용 필드를 하나씩 법령으로 바꿔 전체 파이프라인을 재생하고,
        24개 `e` 열 어디에도 법령이 남지 않는지 본다.
        """
        texts = pilot.replay_run.saved_responses(pilot.CASE)['company_size']
        for field in self.QUOTE_FIELDS:
            patched = {}
            for identifier, text in texts.items():
                obj = json.loads(text)
                obj['company_size'][field] = self.LAW_SPAN
                patched[identifier] = json.dumps(obj, ensure_ascii=False)
            original = pilot.replay_run.saved_responses

            def saved(case, *args, **kwargs):
                return dict(original(case, *args, **kwargs), company_size=patched)

            with patch.object(pilot.replay_run, 'saved_responses', side_effect=saved):
                rows = pilot.replay_run.replay(script, pilot.CASE, input_path=str(pilot.ROOT/'open/dev.jsonl'),
                                               data_dir=str(pilot.ROOT/'open/data'))['rows']
            data = pilot.replay_run.to_csv_bytes(script, rows)
            planted = [(row['id'], column)
                       for row in csv.DictReader(io.StringIO(data.decode('utf-8-sig')))
                       for column, value in row.items()
                       if column.startswith('e') and value and self.LAW_SPAN in value]
            self.assertEqual(planted, [], f'{field} 가 법령을 최종 근거열에 남겼다')

    def test_the_three_rejected_quotes_are_not_contiguous_notice_spans(self):
        """잃은 셀이 정말 잃어야 할 셀인지 — 세 인용이 공고와 어디서 갈리는지 센다.

        복원기(`restore_spacing`)의 결함이 아니다. 공백을 다 지워도 세 인용 모두 공고에 없고,
        갈리는 지점이 다르다 — `16`은 23자 뒤부터 다른 대목을 이어 붙였고(실질 위조),
        `148`·`198`은 끝에 모델이 붙인 마침표 한 글자뿐이다(그래도 축자 인용은 아니다).
        프롬프트가 요구하는 것은 "하나의 연속된 정확한 구간"이므로 셋 다 기각이 맞다.
        """
        events = [json.loads(line) for line in (pilot.CASE/'diagnostics.jsonl').read_text(encoding='utf-8').splitlines()]
        chars = {e['id']: e['max_chars'] for e in events if e['event'] == 'company_size_input'}
        texts = pilot.replay_run.saved_responses(pilot.CASE)['company_size']
        records = {r['id']: r for r in script.iter_records(str(pilot.ROOT/'open/dev.jsonl'))}

        def flat(value):
            return ''.join(unicodedata.normalize('NFC', value).split())

        for identifier, matched, total in [('PPS-DEV-16', 23, 78), ('PPS-DEV-148', 87, 88),
                                           ('PPS-DEV-198', 141, 142)]:
            rec = records[identifier]
            facts = script.parse_judgment(texts[identifier], expected_items=script.COMPANY_SIZE_KEYS)[0]['company_size']
            quote = flat(facts['qualification_quote'])
            visible = flat(script.build_context(rec, chars[identifier]))
            self.assertEqual(len(quote), total)
            self.assertNotIn(quote, visible)  # 공백 차이가 아니다
            longest = max(n for n in range(len(quote) + 1) if quote[:n] in visible)
            self.assertEqual(longest, matched, identifier)

    def test_every_v13_cell_now_carries_a_verified_notice_quote(self):
        """수리 전에는 이 구멍이 후보 없이도 3셀에서 발화했다 — A8 이 만든 회귀가 아니었다.

        수리 뒤에는 company 경로가 쓰는 v13 이 전부 공고 원문으로 검증된 인용을 갖는다.
        """
        _, products = script.load_sme_reference(str(pilot.ROOT/'open/data'))
        events = [json.loads(line) for line in (pilot.CASE/'diagnostics.jsonl').read_text(encoding='utf-8').splitlines()]
        chars = {e['id']: e['max_chars'] for e in events if e['event'] == 'company_size_input'}
        texts = pilot.replay_run.saved_responses(pilot.CASE)['company_size']
        written, ungrounded = [], []
        for rec in script.iter_records(str(pilot.ROOT/'open/dev.jsonl')):
            facts = script.parse_judgment(texts[rec['id']], expected_items=script.COMPANY_SIZE_KEYS)[0]['company_size']
            out, _ = script.verify_company_size(facts, rec, chars[rec['id']])
            cell = out.get('v13')
            if not cell:
                continue
            written.append(rec['id'])
            visible = script.build_context(rec, chars[rec['id']])
            quote = cell['근거문구']
            if not (quote and quote in visible and any(quote in d['text'] for d in rec['docs'])):
                ungrounded.append(rec['id'])
        self.assertEqual(len(written), 6)
        self.assertEqual(ungrounded, [])

    def test_injected_law_span_is_not_accepted_as_a_notice_clause(self):
        article, annex = candidate.segments()
        facts, rec, visible = self.facts_for('PPS-DEV-133')
        self.assertEqual(script.verify_document_requirements(facts, rec, visible)['v20']['위반여부'], 1)
        for span in (article.text.strip().splitlines()[0], '80억원 이상', annex.text.strip().splitlines()[0]):
            self.assertNotIn(span, visible)  # 법령은 공고 본문이 아니다.
            with self.subTest(span=span[:20]):
                # 참여제한 인용 자리에 법령을 넣으면 present도 absent도 아니라 기본 판정이 보존된다.
                out = script.verify_document_requirements(dict(facts, software_participation_quote=span), rec, visible)
                self.assertNotIn('v20', out)
                # SW 사업 인용 자리에 법령을 넣으면 적용 자체가 서지 않는다.
                out = script.verify_document_requirements(dict(facts, software_business_quote=span), rec, visible)
                self.assertNotIn('v20', out)


class BudgetTests(unittest.TestCase):
    def long_record(self, chars=2000):
        """글자를 토큰으로 세는 러너에서도 control이 예산 안에 들어가는 길이."""
        rec = records('a8', 1)[0]
        rec['docs'][0]['text'] = '물품 구매 공고 ' + '가' * chars
        return rec

    def test_report_counts_both_arms_and_keeps_the_notice_text_identical(self):
        report = candidate.budget_report([self.long_record()], CountingRunner(), max_chars=16000)
        row = report['rows'][0]
        self.assertEqual(row['added_tokens'], len(candidate.block()))
        self.assertFalse(row['additional_shrink'])
        self.assertTrue(row['same_visible'])
        self.assertEqual(row['control']['max_chars'], row['candidate']['max_chars'])
        self.assertTrue(report['conditions_pass'])
        # 글자 환산 러너는 조건을 채워도 예산 안전 근거가 아니다.
        self.assertEqual(report['token_count_kind'], 'test_double')
        self.assertFalse(report['budget_safety_evidence'])
        self.assertEqual(report['reference_chars'], len(candidate.block()))
        self.assertEqual(report['control_truncated'], [])

    def test_extra_shrink_is_reported_instead_of_quietly_trimming(self):
        record = self.long_record()
        runner = CountingRunner()
        control = script.fit_to_budget({**record, 'meta': {}}, script.COMPANY_SIZE_PROMPT, runner, 16000,
                                       budget=10**9)[1]
        # 후보만 넘치는 예산. control은 16,000자 그대로 들어간다.
        report = candidate.budget_report([record], runner, max_chars=16000,
                                         budget=control + len(candidate.block()) // 2)
        row = report['rows'][0]
        self.assertTrue(row['additional_shrink'])
        self.assertFalse(row['same_visible'])
        self.assertLess(row['candidate']['max_chars'], row['control']['max_chars'])
        self.assertEqual(report['additional_shrink'], [record['id']])
        self.assertEqual(report['visible_differs'], [record['id']])
        self.assertFalse(report['conditions_pass'])

    def test_control_budget_is_never_measured_inside_the_candidate_context(self):
        with candidate.activate():
            with self.assertRaisesRegex(ValueError, 'control'):
                candidate.budget_report([self.long_record()], CountingRunner(), max_chars=16000)


class BudgetFakeRunner(FakeRunner):
    """예산 검사는 activate() 밖에서 후보 프롬프트도 센다. 그 둘 외에는 받지 않는다."""

    def count_tokens(self, messages):
        assert 'DO_NOT_COPY_REGISTERED_VALUE' not in str(messages)
        assert messages[0]['content'] in (script.COMPANY_SIZE_PROMPT,
                                          script.COMPANY_SIZE_PROMPT + candidate.block())
        return 100


class PilotWiringTests(unittest.TestCase):
    def run_pilot(self, output, episode, runner):
        argv = ['pilot', '--experiment', 'a8', '--model-dir', str(output.parent/script.MODEL_REVISION),
                '--output-dir', str(output), '--episode', str(episode)]
        with patch.object(sys, 'argv', argv), patch.object(script, 'VLLMRunner', return_value=runner):
            pilot.main()

    def test_two_mock_episodes_record_v20_budget_and_no_consumer_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/script.MODEL_REVISION).mkdir()
            runner = BudgetFakeRunner()
            self.run_pilot(root/'episode-1', 1, runner)
            budget = json.loads((root/'episode-1/budget.json').read_text(encoding='utf-8'))
            self.assertEqual(budget['records'], 200)
            self.assertTrue(budget['conditions_pass'])
            self.assertFalse(budget['budget_safety_evidence'])
            contract = json.loads((root/'episode-1/contract.json').read_text(encoding='utf-8'))
            self.assertTrue(contract['arms']['a8']['prompt'].endswith(candidate.block()))
            self.assertEqual(contract['arms']['control']['schema'], contract['arms']['a8']['schema'])
            self.assertIn('experiments/a8_v20_annex.py', contract['files'])
            self.assertIn('experiments/law_index.py', contract['files'])
            self.run_pilot(root/'episode-2', 2, runner)
            report = json.loads((root/'episode-2/run_report.json').read_text(encoding='utf-8'))
            self.assertEqual(report['status'], 'complete')
            self.assertEqual(report['execution_order'], ['a8', 'control'])
            self.assertEqual(report['planned_responses'], 400)
            self.assertIsNone(report['full_pipeline_gpu_macro_f1'])
            self.assertEqual(report['results']['arms']['a8']['off_to_on_changes'], [])
            self.assertEqual(report['results']['control_to_a8_changes'], {'off': [], 'on': []})
            self.assertIn('| 군 | 소비자 | Macro F1 | v20 TP/FP/FN |',
                          (root/'episode-2/run-record.md').read_text(encoding='utf-8'))
            for arm in ('control', 'a8'):
                for variant in ('off', 'on'):
                    self.assertTrue((root/f'episode-2/repeat-{arm}-{variant}.json').is_file())

    def events_of(self, output):
        return [json.loads(line) for line in
                (output/'diagnostics.jsonl').read_text(encoding='utf-8').splitlines()]

    def test_unified_log_carries_one_root_and_two_distinguishable_arms(self):
        """사이드카는 `run_started` 가 없으면 **모든 이벤트를 버린다**(`langfuse_tail.py:91`).

        그래서 루트·군·청크·실제 호출이 한 파일에 순서대로 있어야 관측이 존재한다.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/script.MODEL_REVISION).mkdir()
            self.run_pilot(root/'episode-1', 1, BudgetFakeRunner())
            events = self.events_of(root/'episode-1')
            kinds = [e['event'] for e in events]
            self.assertEqual(kinds.count('run_started'), 1)
            self.assertEqual(kinds.count('run_succeeded'), 1)
            self.assertEqual(kinds[0], 'run_started')
            self.assertEqual(kinds[-1], 'run_succeeded')
            self.assertEqual(kinds.count('arm_started'), 2)
            self.assertEqual(kinds.count('arm_finished'), 2)
            # 군이 갈린다 — 같은 공고가 두 군에 각각 있다.
            for kind in ('company_size_input', 'model_call_started', 'model_call_finished', 'response'):
                arms = {e['arm'] for e in events if e['event'] == kind}
                self.assertEqual(arms, {'control', 'a8'}, kind)
                self.assertEqual(sum(1 for e in events if e['event'] == kind), 400, kind)
            root_event = events[0]
            self.assertEqual(root_event['capture_protocol'], pilot.CAPTURE_PROTOCOL)
            self.assertEqual(root_event['dataset'], 'dev')
            self.assertEqual(len(root_event['dev_ids']), 200)
            self.assertEqual(root_event['expected_model']['revision'], script.MODEL_REVISION)
            self.assertEqual(root_event['mode'], 'pending')     # 시작 줄은 live 를 주장하지 않는다
            loaded = next(e for e in events if e['event'] == 'model_loaded')
            self.assertEqual(loaded['mode'], 'test_double')     # 실제 mode 는 적재 뒤에 적는다
            # 같은 공고·같은 군의 입력과 호출이 이어진다.
            started = [e for e in events if e['event'] == 'model_call_started']
            self.assertEqual({e['call_kind'] for e in started}, {'initial'})
            self.assertTrue(all(e['prompt_text'][0]['content'].startswith('Extract facts') for e in started))
            a8_prompts = {e['prompt_text'][0]['content'] for e in started if e['arm'] == 'a8'}
            control_prompts = {e['prompt_text'][0]['content'] for e in started if e['arm'] == 'control'}
            self.assertTrue(all(p.endswith(candidate.block()) for p in a8_prompts))
            self.assertFalse(any(p.endswith(candidate.block()) for p in control_prompts))
            # 군별 로그도 그대로 남는다 — 기존 감사 경로가 계속 읽는다.
            for arm in ('control', 'a8'):
                self.assertTrue((root/'episode-1'/arm/'dev.events.jsonl').is_file())
            # 성공을 두 번 세지 않는다.
            report = json.loads((root/'episode-1/run_report.json').read_text(encoding='utf-8'))
            self.assertEqual(report['model_success_count'], 0)
            self.assertEqual(sum(c['valid_json'] for c in report['counts'].values()), 400)

    def test_the_unified_log_actually_projects_into_distinct_spans(self):
        """로그를 만든 것과 사이드카가 그것을 쓸 수 있는 것은 다른 일이다.

        커밋 1 직후 이 파일을 `plan()`에 넣으면 generation 400개가 **서로 다른 key 200개**로
        겹쳤다(군이 key 에 없었다). 그 회귀를 여기서 막는다.
        """
        from tools import langfuse_tail
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/script.MODEL_REVISION).mkdir()
            self.run_pilot(root/'episode-1', 1, BudgetFakeRunner())
            state, ops = langfuse_tail.State(), []
            for event in self.events_of(root/'episode-1'):
                ops += langfuse_tail.plan(event, state)
            generations = [o for o in ops if o.kind == 'generation' and o.action == 'open']
            self.assertEqual(len(generations), 400)
            self.assertEqual(len({o.key for o in generations}), 400)   # 겹치지 않는다
            opens = {o.key for o in ops if o.action == 'open'}
            closes = {o.key for o in ops if o.action == 'close'}
            self.assertEqual(opens, closes)                            # 짝이 맞는다
            self.assertEqual(state.calls, {})
            self.assertIn('arm:control:dev', opens)
            self.assertIn('arm:a8:dev', opens)
            self.assertEqual(len([o for o in ops if o.key.startswith('parse:')]), 400)
            self.assertFalse(any(o.key.startswith('gen:') for o in ops))
            # 두 군의 system 프롬프트가 span 입력에서 갈린다.
            systems = [json.loads(o.attrs['langfuse.observation.input'])[0]['content']
                       for o in generations]
            self.assertEqual(len({o.attrs['langfuse.observation.input'] for o in generations}), 400)
            self.assertEqual(sum(1 for s in systems if s.endswith(candidate.block())), 200)
            self.assertEqual(sum(1 for s in systems if s == script.COMPANY_SIZE_PROMPT), 200)

    def test_reserved_event_keys_cannot_be_overwritten(self):
        rows = []
        emit = pilot.make_emit(SimpleNamespace(write=rows.append, flush=lambda: None),
                              run_id='r', episode=1, arm='a8', sample='dev')
        emit('company_size_input', id='X')
        self.assertEqual(json.loads(rows[0])['arm'], 'a8')
        for key in ('arm', 'run_id', 'episode', 'time_unix', 'event', 'sample'):
            with self.assertRaisesRegex(ValueError, '예약된 이벤트 키'):
                emit('company_size_input', **{key: 'spoofed'})

    def test_failed_run_leaves_the_root_and_the_reason(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/script.MODEL_REVISION).mkdir()
            failing = dict(records=200, conditions_pass=False, additional_shrink=['PPS-DEV-01'])
            with patch.object(candidate, 'budget_report', return_value=failing), \
                    self.assertRaises(RuntimeError):
                self.run_pilot(root/'stopped', 1, BudgetFakeRunner())
            events = self.events_of(root/'stopped')
            kinds = [e['event'] for e in events]
            self.assertEqual(kinds.count('run_started'), 1)
            self.assertEqual(kinds.count('run_failed'), 1)
            self.assertEqual(kinds.count('run_succeeded'), 0)
            self.assertEqual(kinds.count('model_call_started'), 0)   # 생성 전에 멈췄다
            self.assertEqual(next(e for e in events if e['event'] == 'run_failed')['error_type'],
                             'RuntimeError')

    def test_failed_budget_stops_before_any_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/script.MODEL_REVISION).mkdir()
            failing = dict(records=200, conditions_pass=False, additional_shrink=['PPS-DEV-01'])
            with patch.object(candidate, 'budget_report', return_value=failing), \
                    self.assertRaisesRegex(RuntimeError, 'stopping before generation'):
                self.run_pilot(root/'stopped', 1, BudgetFakeRunner())
            output = root/'stopped'
            self.assertEqual(json.loads((output/'budget.json').read_text(encoding='utf-8')), failing)
            self.assertFalse((output/'control').exists())
            self.assertEqual(json.loads((output/'run_report.json').read_text(encoding='utf-8'))['status'], 'failed')


class AuditTests(unittest.TestCase):
    """감사는 문자열 검증과 판정을 가르고, 실제 소비자와 어긋나면 안 된다."""

    def h4_rows(self):
        script.load_sme_reference(str(pilot.ROOT/'open/data'))
        events = [json.loads(line) for line in (pilot.CASE/'diagnostics.jsonl').read_text(encoding='utf-8').splitlines()]
        chars = {e['id']: e['max_chars'] for e in events if e['event'] == 'company_size_input'}
        texts = pilot.replay_run.saved_responses(pilot.CASE)['company_size']
        out = []
        for rec in script.iter_records(str(pilot.ROOT/'open/dev.jsonl')):
            facts = script.parse_judgment(texts[rec['id']], expected_items=script.COMPANY_SIZE_KEYS)[0]['company_size']
            out.append((rec, facts, chars[rec['id']], audit.audit_row(rec, facts, max_chars=chars[rec['id']])))
        return out

    def test_audit_matches_the_real_consumer_on_all_200_records(self):
        rows = self.h4_rows()
        for rec, facts, max_chars, row in rows:
            writes, reason = script.verify_company_size(facts, rec, max_chars)
            cell = writes.get('v20')
            self.assertEqual(row['v20_write'], None if cell is None else cell['위반여부'], rec['id'])
            self.assertEqual(row['company_reason'], reason, rec['id'])
        counts = audit._counts([row for *_, row in rows])
        # H4 의 v20 양성 다섯 건과 정확히 같다 — 감사가 판정을 새로 만들지 않는다.
        self.assertEqual(counts['v20_write_1'], 5)
        self.assertEqual([row['id'] for *_, row in rows if row['v20_action'] == 'write_1'],
                         ['PPS-DEV-056', 'PPS-DEV-064', 'PPS-DEV-068', 'PPS-DEV-133', 'PPS-DEV-144'])
        # **실패 분모**: 참여 조항 인용이 200건 전부 null 이다. 개선할 양성 인용이 없었다.
        self.assertEqual(counts['participation_nonnull'], 0)
        self.assertEqual(counts['software_yes'], 11)

    def test_the_catalogue_global_must_be_filled_or_the_audit_refuses(self):
        """`_PRODUCTS` 가 빈 상태의 0 은 안전의 증거가 아니다 — 라운드 2에서 내가 틀린 자리다."""
        with tempfile.TemporaryDirectory() as directory:
            episode = Path(directory)
            (episode/'contract.json').write_text('{}', encoding='utf-8')
            with patch.object(script, '_PRODUCTS', []), \
                    patch.object(script, 'load_sme_reference', return_value=((), [])), \
                    self.assertRaisesRegex(ValueError, '카탈로그 전역이 비었다'):
                audit.audit_episode(episode)

    def test_invalid_quote_is_preserve_not_a_verified_negative(self):
        rec = {r['id']: r for r in script.iter_records(str(pilot.ROOT/'open/dev.jsonl'))}['PPS-DEV-133']
        texts = pilot.replay_run.saved_responses(pilot.CASE)['company_size']
        facts = script.parse_judgment(texts['PPS-DEV-133'], expected_items=script.COMPANY_SIZE_KEYS)[0]['company_size']
        visible = script.build_context(rec, 16000)
        real = facts['software_business_quote']
        self.assertEqual(audit.quote_check(real, rec, visible)['state'], 'exact')
        for quote, state in [(None, 'null'), ('   ', 'empty'), ('공고에 없는 문장', 'invalid'),
                             ('「중소기업기본법」제2조의 중소기업', 'invalid')]:
            self.assertEqual(audit.quote_check(quote, rec, visible)['state'], state, quote)
        # 참여 인용이 원문 밖이면 판정을 보류한다 — 검증된 비위반(write_0)이 아니다.
        row = audit.audit_row(rec, dict(facts, software_participation_quote='공고에 없는 문장'),
                              max_chars=16000)
        self.assertEqual(row['v20_action'], 'preserve')
        self.assertEqual(row['software_participation_quote_check']['state'], 'invalid')
        # null 이고 완전관측이면 부재로 1 을 쓴다.
        self.assertEqual(audit.audit_row(rec, facts, max_chars=16000)['v20_action'], 'write_1')

    def test_quote_matches_point_at_real_document_spans(self):
        rec = {r['id']: r for r in script.iter_records(str(pilot.ROOT/'open/dev.jsonl'))}['PPS-DEV-133']
        texts = pilot.replay_run.saved_responses(pilot.CASE)['company_size']
        facts = script.parse_judgment(texts['PPS-DEV-133'], expected_items=script.COMPANY_SIZE_KEYS)[0]['company_size']
        checked = audit.quote_check(facts['software_business_quote'], rec, script.build_context(rec, 16000))
        self.assertTrue(checked['matches'])
        for match in checked['matches']:
            doc = rec['docs'][match['doc_index']]
            self.assertEqual(doc['text'][match['start']:match['end']], checked['effective_quote'])
            self.assertEqual(match['doc_id'], doc.get('doc_id'))

    def test_fallback_only_change_is_marked_and_not_a_mechanism(self):
        base = dict(id='X', v20_action='write_1', software_business='yes',
                    software_business_quote_check=dict(state='exact'),
                    software_participation_quote_check=dict(state='null'))
        worse = dict(base, v20_action='preserve',
                     software_participation_quote_check=dict(state='invalid'))
        verified = dict(base, v20_action='write_0',
                        software_participation_quote_check=dict(state='exact'))
        self.assertEqual(audit.paired_changes([base], [worse])[0]['gain_kind'], 'fallback_only')
        self.assertEqual(audit.paired_changes([base], [verified])[0]['gain_kind'], 'verified_quote')
        self.assertEqual(audit.paired_changes([base], [base]), [])

    def test_audit_episode_reads_a_real_pilot_output_and_writes_the_ledger(self):
        """회차 폴더 전체를 감사한다 — 계약 hash·공고 집합·군을 함께 검사한다."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/script.MODEL_REVISION).mkdir()
            argv = ['pilot', '--experiment', 'a8', '--model-dir', str(root/script.MODEL_REVISION),
                    '--output-dir', str(root/'episode-1'), '--episode', '1']
            with patch.object(sys, 'argv', argv), \
                    patch.object(script, 'VLLMRunner', return_value=BudgetFakeRunner()):
                pilot.main()
            result = audit.audit_episode(root/'episode-1')
            self.assertEqual(sorted(result['arms']), ['a8', 'control'])
            self.assertTrue(result['complete'])
            self.assertFalse(result['semantic_review_complete'])
            for arm in result['arms'].values():
                self.assertEqual(arm['counts']['records'], 200)
                self.assertIsNone(arm['counts']['participation_semantically_applicable'])
            self.assertEqual(result['execution_mode'], 'cpu_audit')
            self.assertEqual(audit.main(['--episode-dir', str(root/'episode-1')]), 0)
            self.assertTrue((root/'episode-1/v20-audit.json').is_file())
            # 계약 hash 가 어긋나면 감사를 거부한다.
            payload = json.loads((root/'episode-1/a8/dev.json').read_text(encoding='utf-8'))
            payload['contract_sha256'] = '0' * 64
            (root/'episode-1/a8/dev.json').write_text(json.dumps(payload, ensure_ascii=False),
                                                      encoding='utf-8', newline='\n')
            with self.assertRaisesRegex(ValueError, '계약 hash'):
                audit.audit_episode(root/'episode-1')

    def test_sample_takes_the_union_of_runs_plus_label_positives(self):
        """`software_business=yes` 는 회차 산출물이라 한 회차로 고정하면 표본이 편향된다."""
        manifest = json.loads((pilot.ROOT/'reports/team-c/a8-v20-annex/api-sample.json')
                              .read_text(encoding='utf-8'))
        self.assertEqual(len(manifest['mandatory_ids']), 15)
        self.assertEqual(len(manifest['random_ids']), 30)
        self.assertEqual(len(manifest['selected_ids']), 45)
        self.assertEqual(len(set(manifest['selected_ids'])), 45)
        self.assertIn('PPS-DEV-132', manifest['mandatory_ids'])        # 라벨 양성 중 yes 밖
        sources = manifest['sources']
        self.assertEqual(sources['union_count'], 14)
        self.assertEqual(sources['intersection_count'], 9)             # 회차마다 흔들린다
        self.assertEqual(len(sources['per_run']), 3)
        self.assertFalse(set(manifest['mandatory_ids']) & set(manifest['random_ids']))
        # 같은 seed 는 같은 표본을 준다.
        again = audit.select_sample([r['id'] for r in script.iter_records(str(pilot.ROOT/'open/dev.jsonl'))],
                                   sources['union'], {'PPS-DEV-132'},
                                   random_n=manifest['random_n'], seed=manifest['seed'])
        self.assertEqual(sorted(again['random_ids']), sorted(manifest['random_ids']))
        with self.assertRaisesRegex(ValueError, '입력 밖의 공고'):
            audit.select_sample(['A', 'B'], {'ZZZ'}, set(), random_n=1)


class NotebookTests(unittest.TestCase):
    def cells(self):
        return json.loads((pilot.ROOT/'notebooks/colab-a8-v20-annex.ipynb').read_text(encoding='utf-8'))['cells']

    def test_notebook_compiles_and_pins_the_run_request_commit(self):
        for index, cell in enumerate(self.cells()):
            if cell['cell_type'] == 'code':
                compile(''.join(cell['source']), f'cell-{index}', 'exec')
        code = ''.join(self.cells()[3]['source'])
        for ref in ('PASTE_40_HEX_COMMIT', 'z'*40, '44f5e4b'):
            with self.assertRaisesRegex(ValueError, 'REPO_REF'):
                exec(code, dict(REPO_REF=ref, WORK=Path('.')))

    def test_notebook_preserves_partial_results_when_the_run_failed(self):
        import shutil
        import time
        import zipfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results, output = root/'results', root/'pilot'
            results.mkdir()
            output.mkdir()
            (results/'a8-v20-annex.log').write_text('failure', encoding='utf-8')
            (output/'budget.json').write_text('{}', encoding='utf-8')
            downloads = []
            fake_colab = SimpleNamespace(files=SimpleNamespace(download=downloads.append))
            with patch.dict(sys.modules, {'google.colab': fake_colab}):
                exec(''.join(self.cells()[15]['source']),
                     dict(WORK=root, RESULTS=results, PILOT_ROOT=output, time=time, zipfile=zipfile, shutil=shutil))
            with zipfile.ZipFile(downloads[0]) as archive:
                self.assertIn('logs/a8-v20-annex.log', archive.namelist())
                self.assertIn('pilot/budget.json', archive.namelist())


if __name__ == '__main__':
    unittest.main()
