"""CPU contracts, not model-success or accuracy claims."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import script
from experiments import a5_scope_observation as candidate
from experiments import a5_scope_pilot as pilot


class FakeRunner:
    environment = {'mode': 'cpu-test'}
    load_seconds = 0

    def __init__(self):
        self.calls = []

    def count_tokens(self, messages):
        assert '조항호내용' not in messages[1]['content']
        return 100

    def chat(self, batch, items):
        assert items == script.COMPANY_SIZE_KEYS
        h3 = 'scope_condition_state' in script.company_size_schema()['properties']
        self.calls.append((h3, len(batch)))
        facts = script.empty_company_size()
        if h3:
            facts['scope_condition_state'] = 'unobserved'
        return [json.dumps({'company_size': facts})] * len(batch)


class ScopePilotTests(unittest.TestCase):
    def test_original_responses_reproduce_both_committed_csvs(self):
        texts = pilot.replay_run.saved_responses(pilot.CASE)['company_size']
        events = [json.loads(line) for line in (pilot.CASE/'diagnostics.jsonl').read_text(encoding='utf-8').splitlines()]
        chars = {e['id']: e['max_chars'] for e in events if e['event'] == 'company_size_input'}
        payload = dict(rows=[dict(id=r['id'], response_text=texts[r['id']], max_chars=chars[r['id']])
                            for r in script.iter_records(str(pilot.ROOT/'open/dev.jsonl'))])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            pilot.hybrid_replay(payload, output)
            # 일부러 갈린 셀의 목록은 `replay_run.DELIBERATE_MOVES` 한 벌이 소유한다.
            for name, baseline in [('head', 'head-replay'), ('h2', 'absence-replay')]:
                expected = pilot.ROOT/'reports/team-c/a5-label-definition'/baseline/'submission.csv'
                self.assertEqual(pilot.replay_run.csv_cell_diff((output/f'{name}-hybrid.csv').read_bytes(),
                                                                expected.read_bytes()),
                                 pilot.replay_run.DELIBERATE_MOVES)

    def test_schema_restoration_and_grounding_are_separate_from_semantics(self):
        original = script.company_size_schema
        prompt = script.COMPANY_SIZE_PROMPT
        base = script.empty_company_size()
        with self.assertRaisesRegex(RuntimeError, 'restore'):
            with candidate.activate():
                with self.assertRaisesRegex(ValueError, '필드 결손'):
                    script.parse_judgment(json.dumps({'company_size': base}), expected_items=script.COMPANY_SIZE_KEYS)
                facts = {**base, 'scope_product_code': '2611170403', 'scope_condition_quote': '출력 240kW',
                         'scope_condition_quote_2': None, 'scope_condition_state': 'contradicted'}
                script.parse_judgment(json.dumps({'company_size': facts}), expected_items=script.COMPANY_SIZE_KEYS)
                rec = dict(meta={'세부품명번호목록': '전기자동차용충전장치[2611170403]'},
                           docs=[dict(doc_id='D0', type='공고문', text='충전기 출력 240kW 구매')])
                _, products = script.load_sme_reference(str(pilot.ROOT/'open/data'))
                trace = candidate.trace({**facts, 'scope': 'competitive'}, rec, 1000, products)
                self.assertTrue(trace['code_in_supplied_candidates'])
                self.assertTrue(trace['quote_grounding']['scope_condition_quote'])
                self.assertTrue(trace['competitive_without_condition_support'])
                # Source matching is not semantic validation; an invented quote is identified.
                trace = candidate.trace({**facts, 'scope': 'competitive', 'scope_condition_state': 'met',
                                         'scope_condition_quote': '없는 문장'}, rec, 1000, products)
                self.assertFalse(trace['quote_grounding']['scope_condition_quote'])
                self.assertTrue(trace['competitive_without_condition_support'])
                raise RuntimeError('restore')
        self.assertIs(script.company_size_schema, original)
        self.assertEqual(script.COMPANY_SIZE_PROMPT, prompt)

    def test_full_pilot_replays_200_rows_and_preserves_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root/script.MODEL_REVISION
            model.mkdir()
            output = root/'episode-1'
            runner = FakeRunner()
            argv = ['pilot', '--input', str(pilot.ROOT/'open/train_unlabeled.jsonl'),
                    '--model-dir', str(model), '--output-dir', str(output), '--episode', '1']
            with patch.object(sys, 'argv', argv), patch.object(script, 'VLLMRunner', return_value=runner):
                pilot.main()
                result = json.loads((output/'summary.json').read_text(encoding='utf-8'))
                self.assertTrue(result['complete'])
                self.assertEqual(runner.calls, [(False, 128), (False, 72), (False, 5),
                                                (True, 128), (True, 72), (True, 5)])
                self.assertEqual(result['control_to_h3_changes'], {'head': [], 'h2': []})
                self.assertEqual(result['arms']['h3']['condition_states'], {'unobserved': 200})
                report = json.loads((output/'run_report.json').read_text(encoding='utf-8'))
                self.assertEqual(report['status'], 'complete')
                self.assertEqual(report['execution_mode'], 'test_double')
                self.assertEqual(report['model_success_count'], 0)
                self.assertEqual(sum(c['valid_json'] for c in report['counts'].values()), 410)
                self.assertIsNone(report['full_pipeline_gpu_macro_f1'])
                self.assertIn('Macro F1', (output/'run-record.md').read_text(encoding='utf-8'))
                for name in ('control', 'h3'):
                    for variant in ('head', 'h2'):
                        self.assertEqual(len(pilot.score.load_csv(output/name/f'{variant}-hybrid.csv')[0]), 200)
                        metrics = json.loads((output/name/f'{variant}-score/metrics.json').read_text(encoding='utf-8'))
                        self.assertEqual(len(metrics['items']), 24)
                        self.assertTrue((output/name/f'{variant}-score/errors.csv').is_file())
                with self.assertRaises(FileExistsError):
                    pilot.main()
                self.assertEqual(len(runner.calls), 6)
                failed = root/'failed-episode'
                argv[6] = str(failed)
                with patch.object(pilot.collector, 'collect', side_effect=RuntimeError('test failure')):
                    with self.assertRaisesRegex(RuntimeError, 'test failure'):
                        pilot.main()
                report = json.loads((failed/'run_report.json').read_text(encoding='utf-8'))
                self.assertEqual(report['status'], 'failed')
                self.assertEqual(report['error_type'], 'RuntimeError')
                self.assertIsNone(report['full_pipeline_gpu_macro_f1'])
                self.assertEqual(report['results']['arms'], {})


if __name__ == '__main__':
    unittest.main()
