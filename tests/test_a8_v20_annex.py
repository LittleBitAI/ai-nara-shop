"""A8 주입 계약. 프롬프트만 바뀌고 소비 경로는 그대로임을 CPU에서 확인한다.

여기서 통과해도 실제 토큰 수·GPU 성능·v20 TP 회복은 미측정이다.
"""
import csv
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import script
from experiments import a5_scope_pilot as pilot
from experiments import a8_v20_annex as candidate
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

    def test_replayed_h4_bytes_are_identical_with_the_block_on_and_off(self):
        payload = h4_payload()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            metrics, predictions = pilot.hybrid_replay(payload, output, experiment='a8')
            baseline = BASELINE_CSV.read_bytes()
            for variant in ('off', 'on'):
                self.assertEqual((output/f'{variant}-hybrid.csv').read_bytes(), baseline)
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


class LawQuotationTests(unittest.TestCase):
    """주입한 조문을 모델이 공고 인용 자리에 넣어도 v20을 움직이지 못해야 한다."""

    def facts_for(self, identifier):
        texts = pilot.replay_run.saved_responses(pilot.CASE)['company_size']
        rec = {r['id']: r for r in script.iter_records(str(pilot.ROOT/'open/dev.jsonl'))}[identifier]
        facts = script.parse_judgment(texts[identifier], expected_items=script.COMPANY_SIZE_KEYS)[0]['company_size']
        return facts, rec, script.build_context(rec, 16000)

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
