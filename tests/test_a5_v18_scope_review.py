"""Scope review wiring contracts; saved substitutions are not new model results."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
import sys
from types import SimpleNamespace
from unittest.mock import patch

import script
from experiments import a5_scope_pilot as pilot
from experiments import a5_v18_scope_review as candidate
from tests.test_a5_collect_facts import FakeRunner


class ScopeReviewTests(unittest.TestCase):
    def test_schema_requires_new_fields_and_restores_after_failure(self):
        original, prompt = script.company_size_schema, script.COMPANY_SIZE_PROMPT
        old = script.empty_company_size()
        with self.assertRaisesRegex(RuntimeError, 'restore'):
            with candidate.activate():
                schema = script.company_size_schema()['properties']
                self.assertEqual(list(schema)[-2:], ['scope_review', 'scope_review_quote'])
                self.assertEqual(schema['scope_review'], schema['scope'])
                self.assertEqual(schema['scope_review_quote'], schema['scope_quote'])
                self.assertTrue(script.COMPANY_SIZE_PROMPT.startswith(prompt))
                with self.assertRaisesRegex(ValueError, '필드 결손'):
                    script.parse_judgment(json.dumps({'company_size': old}), expected_items=script.COMPANY_SIZE_KEYS)
                script.parse_judgment(json.dumps({'company_size': script.empty_company_size()}),
                                      expected_items=script.COMPANY_SIZE_KEYS)
                raise RuntimeError('restore')
        self.assertIs(script.company_size_schema, original)
        self.assertEqual(script.COMPANY_SIZE_PROMPT, prompt)

    def test_verifier_preserves_guards_zero_and_original_facts(self):
        records = {r['id']: r for r in script.iter_records(str(pilot.ROOT/'open/dev.jsonl'))}
        texts = pilot.replay_run.saved_responses(pilot.CASE)['company_size']
        rec = records['PPS-DEV-043']
        facts = script.parse_judgment(texts[rec['id']], expected_items=script.COMPANY_SIZE_KEYS)[0]['company_size']
        original = deepcopy(facts)
        baseline = script.verify_company_size(facts, rec, 16000)
        self.assertEqual(baseline[0]['v18']['위반여부'], 1)
        self.assertEqual(candidate.verify_company_size(facts, rec, 16000), baseline)
        for scope, quote in [('unknown', facts['scope_quote']), ('general', 'invented quotation'), ('general', None)]:
            reviewed = dict(facts, scope_review=scope, scope_review_quote=quote)
            self.assertEqual(candidate.verify_company_size(reviewed, rec, 16000), baseline)
        reviewed = dict(facts, scope_review='other', scope_review_quote=facts['scope_quote'])
        out, _ = candidate.verify_company_size(reviewed, rec, 16000)
        self.assertEqual(out['v18']['위반여부'], 0)
        self.assertEqual({k: v for k, v in out.items() if k != 'v18'},
                         {k: v for k, v in baseline[0].items() if k != 'v18'})
        for fields, record, chars, reason in [
            # C7 (#152) reads checklist × sme_allowed as unrestricted; a limiting role with no limit stays unverified.
            ({'qualification': 'unrestricted', 'qualification_role': 'eligibility'}, rec, 16000, 'unverified_qualification'),
            ({'priority_exception': 'unknown'}, rec, 16000, 'unverified_priority_exception'),
            ({}, dict(rec, input_completeness={'완전관측': False}), 16000, 'absence_not_observable'),
        ]:
            f = dict(facts, **fields, scope_review='general', scope_review_quote=facts['scope_quote'])
            trace = candidate.trace(f, record, chars)
            self.assertEqual(trace['review_reason'], reason)
            self.assertFalse(trace['v18_overwritten'])
        c7 = dict(facts, qualification='sme_allowed', qualification_role='checklist',
                  scope_review='general', scope_review_quote=facts['scope_quote'])
        self.assertNotEqual(candidate.trace(c7, rec, 16000)['review_reason'], 'unverified_qualification')
        self.assertEqual(facts, original)
        # Actual input truncation, while both quotations remain visible, still blocks absence.
        long_rec = deepcopy(rec)
        long_rec['docs'][0]['text'] += ' extended specification' * 2000
        f = dict(facts, scope_review='general', scope_review_quote=facts['scope_quote'])
        self.assertEqual(candidate.trace(f, long_rec, 16000)['review_reason'], 'absence_not_observable')

    def test_h4_bytes_and_h3_surrogate_cannot_leak_v10(self):
        events = [json.loads(line) for line in (pilot.CASE/'diagnostics.jsonl').read_text(encoding='utf-8').splitlines()]
        chars = {e['id']: e['max_chars'] for e in events if e['event'] == 'company_size_input'}
        texts = pilot.replay_run.saved_responses(pilot.CASE)['company_size']
        payload = dict(rows=[dict(id=r['id'], response_text=texts[r['id']], max_chars=chars[r['id']])
                            for r in script.iter_records(str(pilot.ROOT/'open/dev.jsonl'))])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            pilot.hybrid_replay(payload, output, experiment='v18')
            baseline = (pilot.ROOT/'reports/team-c/a5-label-definition/head-replay/submission.csv').read_bytes()
            # 일부러 갈린 셀은 `replay_run.DELIBERATE_MOVES` 한 벌이 소유한다.
            moved = pilot.replay_run.DELIBERATE_MOVES
            self.assertEqual(pilot.replay_run.csv_cell_diff((output/'off-hybrid.csv').read_bytes(), baseline), moved)
            self.assertEqual(pilot.replay_run.csv_cell_diff((output/'on-hybrid.csv').read_bytes(), baseline), moved)
            case = pilot.ROOT/'reports/runs/a5-scope-1789959906563639676/pilot/episode-1'
            control, h3 = [json.loads((case/arm/'dev.json').read_text(encoding='utf-8'))['payload']
                           for arm in ('control', 'h3')]
            surrogate = deepcopy(control)
            for row, review in zip(surrogate['rows'], h3['rows']):
                self.assertEqual(row['id'], review['id'])
                obj = json.loads(row['response_text'])
                f = json.loads(review['response_text'])['company_size']
                obj['company_size'].update(scope_review=f['scope'], scope_review_quote=f['scope_quote'])
                row['response_text'] = json.dumps(obj, ensure_ascii=False)
            output = output/'surrogate'
            output.mkdir()
            metrics, predictions = pilot.hybrid_replay(surrogate, output, experiment='v18', review_fields=True)
            changed = pilot.changes(predictions['off'], predictions['on'])
            # `PPS-DEV-22` joined with the bundle's complete-notice rule (C, #93/#97): its 공고문 is
            # fully visible, so the A5 scope arm can now decide v18 there too. Still v18 only.
            # `22` and `040` left with the ported #139 v18 rule (feat/a-dev-fit-stack): both arms raise them now.
            self.assertEqual([(c['id'], c['item']) for c in changed], [('PPS-DEV-041', 'v18')])
            # 9 before the facts dev-fit zeroed v10 on two no-bid contracts; 7 before the catalogue-miss
            # gate (feat/a-offdev-stack) lowered 126 and 146, whose registered codes are outside the catalogue.
            # C9 (feat/a-final-stack) keeps the other five: their notices name a catalogue product (S7-15).
            self.assertEqual(metrics['off']['items']['v10']['fp'], 5)
            self.assertEqual(metrics['on']['items']['v10']['fp'], 5)
            # 3 before the #139 v18 port, 4 before C7 (feat/a-final-stack) raised 044.
            self.assertEqual(metrics['on']['items']['v18']['tp'], 5)

    def test_two_mock_episodes_record_comparisons_and_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root/script.MODEL_REVISION
            model.mkdir()
            runner = FakeRunner()
            def run(output, episode):
                argv = ['pilot', '--experiment', 'v18', '--model-dir', str(model),
                        '--output-dir', str(output), '--episode', str(episode)]
                with patch.object(sys, 'argv', argv), patch.object(script, 'VLLMRunner', return_value=runner):
                    pilot.main()
            run(root/'episode-1', 1)
            report = json.loads((root/'episode-1/run_report.json').read_text(encoding='utf-8'))
            self.assertEqual(report['status'], 'complete')
            self.assertEqual(report['model_success_count'], 0)
            self.assertEqual(report['planned_responses'], 400)
            self.assertIsNone(report['full_pipeline_gpu_macro_f1'])
            self.assertEqual(report['execution_order'], ['control', 'v18'])
            run(root/'episode-2', 2)
            second = json.loads((root/'episode-2/run_report.json').read_text(encoding='utf-8'))
            self.assertEqual(second['execution_order'], ['v18', 'control'])
            self.assertEqual(sum(runner.calls), 800)
            for arm in ('control', 'v18'):
                for variant in ('off', 'on'):
                    self.assertTrue((root/f'episode-2/repeat-{arm}-{variant}.json').is_file())
                    metrics = second['results']['arms'][arm]['metrics'][variant]
                    self.assertEqual(len(metrics['items']), 24)
            self.assertEqual(second['results']['arms']['v18']['off_to_on_changes'], [])
            with self.assertRaises(FileExistsError):
                run(root/'episode-2', 2)
            # Fail after one real collector chunk; the completed raw responses and budgets survive.
            chat = runner.chat
            count = 0
            def fail_second_batch(batch, items):
                nonlocal count
                count += 1
                if count > 1:
                    raise RuntimeError('injected interruption')
                return chat(batch, items)
            with patch.object(runner, 'chat', side_effect=fail_second_batch), \
                    self.assertRaises(RuntimeError):
                run(root/'failed', 1)
            failed = json.loads((root/'failed/run_report.json').read_text(encoding='utf-8'))
            self.assertEqual(failed['status'], 'failed')
            self.assertEqual(failed['model_success_count'], 0)
            events = [json.loads(line) for line in (root/'failed/control/dev.events.jsonl').read_text(encoding='utf-8').splitlines()]
            self.assertTrue(any(e['event'] == 'company_size_input' and 'max_chars' in e for e in events))
            self.assertEqual(sum(e['event'] == 'response' and e.get('status') == 'valid' for e in events), 128)
            # Over-budget stage is failed, but scored results remain available.
            collect = pilot.collector.collect
            def slow(*args, **kwargs):     # 파일럿이 observe= 같은 키워드도 넘긴다
                return dict(collect(*args, **kwargs), stage_seconds=pilot.STAGE_LIMIT + 1)
            with patch.object(pilot.collector, 'collect', side_effect=slow), \
                    self.assertRaisesRegex(RuntimeError, 'planning limit'):
                run(root/'slow', 1)
            slow_report = json.loads((root/'slow/run_report.json').read_text(encoding='utf-8'))
            self.assertFalse(slow_report['results']['complete'])
            self.assertIn('control', slow_report['results']['arms'])

    def test_input_and_repeat_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root/'inputs.json'
            source = root/'input.txt'
            manifest.write_text(json.dumps({'input.txt': 'wrong-hash'}), encoding='utf-8')
            with patch.object(pilot, 'ROOT', root), patch.object(pilot, 'INPUT_MANIFEST', manifest):
                with self.assertRaises(FileNotFoundError):
                    pilot.validate_inputs()
                source.write_text('present', encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'SHA256'):
                    pilot.validate_inputs()
            first = root/'episode-1'
            first.mkdir()
            def save(name, obj):
                pilot.collector.save(first/name, obj)
            contract = {'episode': 2, 'order': ['v18', 'control'], 'files': {'code': 'new'}}
            save('run_report.json', {'status': 'complete'})
            save('summary.json', {'complete': False, 'arms': {}})
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                pilot.validate_previous(root/'episode-2', contract)
            save('summary.json', {'complete': True, 'arms': {'v18': {'within_stage_planning_limit': False}}})
            with self.assertRaisesRegex(ValueError, 'time limit'):
                pilot.validate_previous(root/'episode-2', contract)
            save('summary.json', {'complete': True, 'arms': {'v18': {'within_stage_planning_limit': True}}})
            save('contract.json', dict(contract, files={'code': 'old'}))
            with self.assertRaisesRegex(ValueError, 'contract mismatch'):
                pilot.validate_previous(root/'episode-2', contract)

    def test_notebook_compiles_and_preserves_failed_partial_zip(self):
        notebook = json.loads((pilot.ROOT/'notebooks/colab-a5-v18-scope-review.ipynb').read_text(encoding='utf-8'))
        for index, cell in enumerate(notebook['cells']):
            if cell['cell_type'] == 'code':
                compile(''.join(cell['source']), f'cell-{index}', 'exec')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results, output = root/'results', root/'pilot'
            results.mkdir()
            output.mkdir()
            (results/'failure.log').write_text('failure', encoding='utf-8')
            (output/'dev.json.partial').write_text('partial', encoding='utf-8')
            import shutil
            import time
            import zipfile
            downloads = []
            fake_colab = SimpleNamespace(files=SimpleNamespace(download=downloads.append))
            with patch.dict(sys.modules, {'google.colab': fake_colab}):
                exec(''.join(notebook['cells'][15]['source']),
                     dict(WORK=root, RESULTS=results, PILOT_ROOT=output, time=time, zipfile=zipfile, shutil=shutil))
            with zipfile.ZipFile(downloads[0]) as archive:
                self.assertIn('logs/failure.log', archive.namelist())
                self.assertIn('pilot/dev.json.partial', archive.namelist())
            self.assertTrue((output/Path(downloads[0]).name).is_file())

    def test_notebook_input_bundle_missing_corrupt_and_verified(self):
        import hashlib
        import zipfile
        notebook = json.loads((pilot.ROOT/'notebooks/colab-a5-v18-scope-review.ipynb').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, results = root/'repo', root/'results'
            results.mkdir()
            manifest = repo/'reports/team-c/a5-v18-scope-review/inputs.json'
            manifest.parent.mkdir(parents=True)
            data = b'provided input'
            pilot.collector.save(manifest, {'open/dev.jsonl': hashlib.sha256(data).hexdigest()})
            def local_path(value):
                return root/str(value).removeprefix('/content/')
            namespace = dict(REPO=repo, RESULTS=results, SOURCE_COMMIT='0'*40, Path=local_path,
                             json=json, hashlib=hashlib, zipfile=zipfile, write_json=pilot.collector.save)
            fake_colab = SimpleNamespace(drive=SimpleNamespace(mount=lambda _: None))
            code = ''.join(notebook['cells'][5]['source'])
            bundle = root/'drive/MyDrive/a5/a5-v18-inputs.zip'
            with patch.dict(sys.modules, {'google.colab': fake_colab}):
                with self.assertRaises(FileNotFoundError):
                    exec(code, namespace)
                bundle.parent.mkdir(parents=True)
                with zipfile.ZipFile(bundle, 'w') as archive:
                    archive.writestr('open/dev.jsonl', b'corrupt')
                with self.assertRaisesRegex(ValueError, 'SHA256'):
                    exec(code, namespace)
                with zipfile.ZipFile(bundle, 'w') as archive:
                    archive.writestr('open/dev.jsonl', data)
                exec(code, namespace)
                self.assertEqual((repo/'open/dev.jsonl').read_bytes(), data)
                (repo/'open/dev.jsonl').write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError, 'SHA256'):
                    exec(code, namespace)


if __name__ == '__main__':
    unittest.main()
