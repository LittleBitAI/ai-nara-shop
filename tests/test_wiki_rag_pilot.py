"""CPU wiring contracts for the wiki RAG pilot. No GPU, no model success, no adoption."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import script
from experiments import a5_collect_facts as collector
from experiments import a5_scope_pilot as pilot
from experiments import wiki_rag_pilot as wiki
from tools import replay_run

HEAD_REPLAY = wiki.ROOT/'reports/team-c/a5-label-definition/head-replay/submission.csv'


def dev_records():
    return list(script.iter_records(str(wiki.ROOT/'open/dev.jsonl')))


def saved_payload():
    """The archived H4 company responses with the per-notice budgets that produced them."""
    texts = replay_run.saved_responses(pilot.CASE)['company_size']
    chars = {}
    for line in (pilot.CASE/'diagnostics.jsonl').read_text(encoding='utf-8').splitlines():
        event = json.loads(line)
        if event['event'] == 'company_size_input':
            chars[event['id']] = event['max_chars']
    return dict(rows=[dict(id=rec['id'], response_text=texts[rec['id']], max_chars=chars[rec['id']])
                      for rec in dev_records()])


class CountingRunner:
    """One token per character, so a fixed budget actually squeezes the document text."""
    MODE = 'test_double'
    environment = {'test_only': True}
    load_seconds = 0.0

    def __init__(self, *_, **__):
        self.calls = []

    def count_tokens(self, messages):
        assert messages[0]['content'] == script.COMPANY_SIZE_PROMPT
        return sum(len(message['content']) for message in messages)

    def chat(self, batch, items=None):
        self.calls.append(len(batch))
        return [json.dumps({'company_size': script.empty_company_size()})] * len(batch)


def synthetic(count, text_chars):
    return [dict(id=f'PPS-T-{i:03d}', meta={}, docs=[dict(doc_id='D0', type='공고문', text='가'*text_chars)],
                 input_completeness={'완전관측': True}, dropped_doc_counts={}) for i in range(count)]


class AssetTests(unittest.TestCase):
    def test_manifest_offsets_reproduce_every_quotation(self):
        manifest = wiki.load_sources()
        self.assertEqual(manifest['status'], 'draft')
        self.assertIsNone(manifest['reviewer'])
        self.assertIsNone(manifest['decision'])
        self.assertEqual(len(manifest['spans']), 12)
        self.assertEqual(manifest['total_quote_chars'], sum(s['chars'] for s in manifest['spans']))
        for span in manifest['spans']:
            text = (wiki.ROOT/span['source_path']).read_bytes().decode('utf-8')
            self.assertEqual(text[span['start']:span['end']], span['quote'])
            # The anchors in `locator` must re-derive the same offsets without the numbers.
            self.assertEqual(text.count(span['locator']['head']), 1)
            start = text.index(span['locator']['head'])
            self.assertEqual(start, span['start'])
            self.assertEqual(text.index(span['locator']['tail'], start) + len(span['locator']['tail']),
                             span['end'])

    def test_damaged_asset_or_missing_key_fails_before_any_run(self):
        manifest = wiki.load_sources()
        with tempfile.TemporaryDirectory() as directory:
            assets = Path(directory)/'wiki-rag'
            shutil.copytree(wiki.ASSETS, assets)
            with patch.object(wiki, 'ASSETS', assets):
                self.assertEqual(wiki.load_sources()['spans'], manifest['spans'])
                for mutate, message in (
                        (lambda m: m['sources'][0].update(sha256='0'*64), 'Source SHA256'),
                        (lambda m: m['spans'][0].update(start=m['spans'][0]['start']+1), 'Span offset'),
                        (lambda m: m['spans'][0].update(quote=m['spans'][0]['quote'][:-1]), 'Span offset'),
                        (lambda m: m['spans'].append(deepcopy(m['spans'][0])), 'Duplicate span id')):
                    damaged = deepcopy(manifest)
                    mutate(damaged)
                    collector.save(assets/'sources.json', damaged)
                    with self.assertRaisesRegex(ValueError, message):
                        wiki.load_sources()
                collector.save(assets/'sources.json', manifest)
                page = (assets/'v20.md').read_text(encoding='utf-8')
                (assets/'v20.md').write_text(page.replace('{{span:gd-3-2}}', '요약: 명시하여야 한다'),
                                             encoding='utf-8', newline='\n')
                with self.assertRaisesRegex(ValueError, 'same span set'):
                    wiki.wiki_block(wiki.load_sources())

    def test_both_arms_carry_the_same_quotations_in_a_different_arrangement(self):
        manifest = wiki.load_sources()
        blocks = wiki.blocks(manifest)
        self.assertEqual(blocks['control'], '')
        self.assertNotEqual(blocks['raw'], blocks['wiki'])
        for span in manifest['spans']:
            for arm in ('raw', 'wiki'):
                self.assertEqual(blocks[arm].count(span['quote']), 1, (arm, span['span_id']))
                self.assertEqual(blocks[arm].count('[' + span['address'] + ']'), 1)
        # The page adds headings and field links, never a summarized or trimmed quotation.
        self.assertIn('## 위반 조건', blocks['wiki'])
        self.assertIn('미사용', blocks['wiki'])
        self.assertNotIn('## 위반 조건', blocks['raw'])
        for arm in ('raw', 'wiki'):
            self.assertIn('not notice evidence', blocks[arm])
            self.assertNotIn('PPS-DEV', blocks[arm])


class ArmInputTests(unittest.TestCase):
    def test_arms_differ_only_by_the_appended_block(self):
        blocks = wiki.blocks(wiki.load_sources())
        _, products = script.load_sme_reference(str(wiki.ROOT/'open/data'))
        rec = dev_records()[0]
        messages = {}
        for arm in wiki.ARMS:
            with wiki.activate(arm, blocks):
                messages[arm] = script.build_messages(rec, script.COMPANY_SIZE_PROMPT, 9000, products)
        base = messages['control']
        self.assertEqual(base, script.build_messages(rec, script.COMPANY_SIZE_PROMPT, 9000, products))
        for arm in wiki.ARMS:
            self.assertEqual(messages[arm][0]['content'], base[0]['content'])
            self.assertEqual(messages[arm][1]['content'],
                             base[1]['content'] + blocks[arm])

    def test_activate_restores_the_prompt_builder_after_a_failure(self):
        blocks = wiki.blocks(wiki.load_sources())
        original = script.build_user_prompt
        prompt = script.COMPANY_SIZE_PROMPT
        schema = collector.digest(script.company_size_schema())
        with self.assertRaisesRegex(RuntimeError, 'restore'):
            with wiki.activate('wiki', blocks):
                self.assertIsNot(script.build_user_prompt, original)
                # The arm never touches the system prompt or the output schema.
                self.assertEqual(script.COMPANY_SIZE_PROMPT, prompt)
                self.assertEqual(collector.digest(script.company_size_schema()), schema)
                raise RuntimeError('restore')
        self.assertIs(script.build_user_prompt, original)
        self.assertEqual(script.COMPANY_SIZE_PROMPT, prompt)
        self.assertEqual(collector.digest(script.company_size_schema()), schema)

    def test_common_budget_is_shared_and_records_the_extra_truncation(self):
        blocks = wiki.blocks(wiki.load_sources())
        runner = CountingRunner()
        records = synthetic(2, 20000)
        overhead = len(script.build_messages(records[0], script.COMPANY_SIZE_PROMPT, 1)[0]['content'])
        with patch.object(script, 'PROMPT_BUDGET', overhead + 8000):
            plan, notes = wiki.budget_plan(records, runner, (), blocks)
        self.assertEqual(runner.calls, [])
        for rec in records:
            note = notes[rec['id']]
            self.assertEqual(plan[rec['id']], note['common_max_chars'])
            self.assertEqual({value['max_chars'] for value in note['arms'].values()},
                             {note['common_max_chars']})
            # The control arm alone would have fitted more of the notice; the loss is recorded.
            self.assertGreater(note['usual_control_max_chars'], note['common_max_chars'])
            self.assertEqual(note['additional_truncation_chars'],
                             note['usual_control_max_chars'] - note['common_max_chars'])
            self.assertNotEqual(note['context_sha256'], note['usual_context_sha256'])
            self.assertTrue(note['truncated'])

    def test_over_budget_raises_before_the_model_is_called(self):
        blocks = wiki.blocks(wiki.load_sources())
        runner = CountingRunner()
        with patch.object(script, 'PROMPT_BUDGET', 200):
            with self.assertRaisesRegex(ValueError, '토큰 초과'):
                wiki.budget_plan(synthetic(1, 20000), runner, (), blocks)
        self.assertEqual(runner.calls, [])

    def test_collector_plan_keeps_one_body_and_rejects_an_unfittable_plan(self):
        blocks = wiki.blocks(wiki.load_sources())
        runner = CountingRunner()
        records = synthetic(2, 20000)
        overhead = len(script.build_messages(records[0], script.COMPANY_SIZE_PROMPT, 1)[0]['content'])
        with patch.object(script, 'PROMPT_BUDGET', overhead + 8000):
            plan, _ = wiki.budget_plan(records, runner, (), blocks)
            expected = [plan[rec['id']] for rec in records]
            bodies, own = set(), {}
            for arm in wiki.ARMS:
                with wiki.activate(arm, blocks):
                    unplanned = collector.collect(records, runner, (), lambda e, **f: None)
                    planned = collector.collect(records, runner, (), lambda e, **f: None, plan=plan)
                own[arm] = [row['max_chars'] for row in unplanned['rows']]
                self.assertEqual([row['max_chars'] for row in planned['rows']], expected)
                bodies.add(tuple(script.build_context(rec, row['max_chars'])
                                 for rec, row in zip(records, planned['rows'])))
            self.assertEqual(len(bodies), 1)
            # Each arm shrinks on its own; the plan is the smallest of the three, for all of them.
            self.assertEqual(own['wiki'], expected)
            for arm in ('control', 'raw'):
                self.assertTrue(all(a > b for a, b in zip(own[arm], expected)), (arm, own[arm]))
            with wiki.activate('wiki', blocks), self.assertRaisesRegex(ValueError, '계획한 문서 예산'):
                collector.collect(records, runner, (), lambda e, **f: None,
                                  plan={rec['id']: 20000 for rec in records})

    def test_unchanged_collector_default_still_shrinks_one_dev_notice(self):
        """The plan argument must not change the existing H2/H3/v18 collector behaviour."""
        runner = CountingRunner()
        records = synthetic(1, 20000)
        payload = collector.collect(records, runner, (), lambda e, **f: None)
        self.assertLess(payload['rows'][0]['max_chars'], collector.MAX_CHARS)


class ConsumerTests(unittest.TestCase):
    def test_h4_replay_is_byte_identical_and_the_consumer_is_untouched(self):
        payload = saved_payload()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            for arm in wiki.ARMS:
                arm_dir = output/arm
                arm_dir.mkdir()
                metrics, predictions = wiki.replay_arm(payload, arm_dir, arm)
                # 세 군이 서로 같은지가 이 검사의 뜻이다. 보관 기준선과는 A8 PR 의 v13 근거 수리로
                # 세 셀이 일부러 다르다 — `company_size_products()` 가 검증된 공고 인용을 요구한다.
                # 보관 CSV 는 다시 쓰지 않고 움직인 셀을 고정한다.
                self.assertEqual(replay_run.csv_cell_diff((arm_dir/(arm + '-hybrid.csv')).read_bytes(),
                                                          HEAD_REPLAY.read_bytes()),
                                 replay_run.DELIBERATE_MOVES)
                self.assertEqual(len(metrics['items']), 24)
                self.assertEqual(len(predictions), 200)
                self.assertTrue((arm_dir/'verification.json').is_file())

    def test_an_observed_v20_change_reaches_the_verifier_and_the_final_csv(self):
        payload = deepcopy(saved_payload())
        records = {rec['id']: rec for rec in dev_records()}
        row = next(r for r in payload['rows'] if r['id'] == 'PPS-DEV-02')
        response = json.loads(row['response_text'])
        facts = response['company_size']
        self.assertNotEqual(facts['software_business'], 'yes')
        facts.update(software_business='yes', software_business_quote=facts['scope_quote'],
                     software_participation_quote=None, requirements_complete='yes')
        row['response_text'] = json.dumps(response, ensure_ascii=False)
        verified, _ = script.verify_company_size(facts, records['PPS-DEV-02'], row['max_chars'])
        self.assertEqual(verified['v20'], {'위반여부': 1, '근거문구': None})
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'wiki'
            output.mkdir()
            _, predictions = wiki.replay_arm(payload, output, 'wiki')
            changed = [line for line in (output/'wiki-hybrid.csv').read_text(encoding='utf-8').splitlines()
                       if line.startswith('PPS-DEV-02,')]
            self.assertEqual(len(changed), 1)
            self.assertEqual(changed[0].split(',')[script.ITEMS.index('v20') + 1], '1')
            self.assertNotEqual((output/'wiki-hybrid.csv').read_bytes(), HEAD_REPLAY.read_bytes())
            self.assertEqual(predictions['PPS-DEV-02'][script.ITEMS.index('v20')], 1)
            others = {i: v for i, v in predictions.items() if i != 'PPS-DEV-02'}
            _, untouched = wiki.replay_arm(saved_payload(), output.parent, 'control')
            self.assertEqual(others, {i: v for i, v in untouched.items() if i != 'PPS-DEV-02'})

    def test_a_forged_law_quotation_is_rejected_as_notice_evidence(self):
        manifest = wiki.load_sources()
        law_quote = next(s for s in manifest['spans'] if s['span_id'] == 'gd-3-2')['quote']
        rec = next(r for r in dev_records() if r['id'] == 'PPS-DEV-02')
        visible = script.build_context(rec, 16000)
        facts = dict(script.empty_company_size(), software_business='yes',
                     software_business_quote=law_quote, software_participation_quote=None,
                     requirements_complete='yes')
        self.assertEqual(script.verify_document_requirements(facts, rec, visible), {})


class EpisodeTests(unittest.TestCase):
    def episode(self, root, output, episode):
        argv = ['wiki', '--model-dir', str(root/script.MODEL_REVISION),
                '--output-dir', str(output), '--episode', str(episode)]
        runner = CountingRunner()
        with patch.object(sys, 'argv', argv), patch.object(script, 'VLLMRunner', return_value=runner), \
                patch.object(script, 'PROMPT_BUDGET', 26000):
            wiki.main()
        return runner

    def test_two_mock_episodes_record_budgets_comparisons_and_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/script.MODEL_REVISION).mkdir()
            runner = self.episode(root, root/'episode-1', 1)
            self.assertEqual(sum(runner.calls), 600)
            report = json.loads((root/'episode-1/run_report.json').read_text(encoding='utf-8'))
            self.assertEqual(report['status'], 'complete')
            self.assertEqual(report['model_success_count'], 0)
            self.assertEqual(report['planned_responses'], 600)
            self.assertIsNone(report['full_pipeline_gpu_macro_f1'])
            self.assertEqual(report['execution_order'], ['control', 'raw', 'wiki'])
            self.assertFalse(report['independent_review'])
            budget = json.loads((root/'episode-1/budget.json').read_text(encoding='utf-8'))
            self.assertEqual(len(budget['plan']), 200)
            contract = json.loads((root/'episode-1/contract.json').read_text(encoding='utf-8'))
            self.assertEqual(contract['blocks']['control']['chars'], 0)
            self.assertGreater(contract['blocks']['wiki']['chars'], contract['blocks']['raw']['chars'])
            second = self.episode(root, root/'episode-2', 2)
            self.assertEqual(sum(second.calls), 600)
            record = json.loads((root/'episode-2/run_report.json').read_text(encoding='utf-8'))
            self.assertEqual(record['execution_order'], ['wiki', 'raw', 'control'])
            for name in wiki.ARMS:
                self.assertTrue((root/f'episode-2/repeat-{name}.json').is_file())
                self.assertEqual(len(record['results']['arms'][name]['metrics']['items']), 24)
            for pair in ('control-to-raw', 'control-to-wiki', 'raw-to-wiki'):
                comparison = json.loads((root/f'episode-2/{pair}-comparison.json').read_text(encoding='utf-8'))
                self.assertEqual(comparison['focus'], ['v20'])
                self.assertEqual(comparison['changes'], [])
            self.assertIn('## 24항목 지표', (root/'episode-2/run-record.md').read_text(encoding='utf-8'))
            with self.assertRaises(FileExistsError):
                self.episode(root, root/'episode-2', 2)

    def test_failed_episode_preserves_partial_responses_and_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/script.MODEL_REVISION).mkdir()
            original = collector.collect
            calls = []

            def fail_second_arm(*args, **kwargs):
                calls.append(1)
                if len(calls) > 1:
                    raise RuntimeError('injected interruption')
                return original(*args, **kwargs)

            with patch.object(collector, 'collect', side_effect=fail_second_arm), \
                    self.assertRaises(RuntimeError):
                self.episode(root, root/'failed', 1)
            report = json.loads((root/'failed/run_report.json').read_text(encoding='utf-8'))
            self.assertEqual(report['status'], 'failed')
            self.assertEqual(report['error_type'], 'RuntimeError')
            self.assertEqual(report['model_success_count'], 0)
            self.assertTrue((root/'failed/budget.json').is_file())
            events = [json.loads(line) for line in
                      (root/'failed/control/dev.events.jsonl').read_text(encoding='utf-8').splitlines()]
            self.assertEqual(sum(e['event'] == 'response' and e['status'] == 'valid' for e in events), 200)
            self.assertTrue(any(e['event'] == 'company_size_input' for e in events))

    def test_over_time_arm_fails_but_keeps_the_scored_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/script.MODEL_REVISION).mkdir()
            original = collector.collect

            def slow(*args, **kwargs):
                return dict(original(*args, **kwargs), stage_seconds=pilot.STAGE_LIMIT + 1)

            with patch.object(collector, 'collect', side_effect=slow), \
                    self.assertRaisesRegex(RuntimeError, 'planning limit'):
                self.episode(root, root/'slow', 1)
            summary = json.loads((root/'slow/summary.json').read_text(encoding='utf-8'))
            self.assertFalse(summary['complete'])
            self.assertIn('control', summary['arms'])
            self.assertFalse(summary['arms']['control']['within_stage_planning_limit'])

    def test_preflight_rejects_bad_inputs_contracts_and_budgets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root/'inputs.json'
            source = root/'input.txt'
            manifest.write_text(json.dumps({'input.txt': 'wrong-hash'}), encoding='utf-8')
            with patch.object(wiki, 'ROOT', root), patch.object(wiki, 'INPUT_MANIFEST', manifest):
                with self.assertRaises(FileNotFoundError):
                    wiki.validate_inputs()
                source.write_text('present', encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'SHA256'):
                    wiki.validate_inputs()
            first = root/'episode-1'
            first.mkdir()
            contract = {'episode': 2, 'order': list(wiki.ARMS), 'files': {'code': 'new'}}
            collector.save(first/'run_report.json', {'status': 'complete'})
            collector.save(first/'summary.json', {'complete': False, 'arms': {}})
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                wiki.validate_previous(root/'episode-2', contract)
            collector.save(first/'summary.json',
                           {'complete': True, 'arms': {'wiki': {'within_stage_planning_limit': False}}})
            with self.assertRaisesRegex(ValueError, 'time limit'):
                wiki.validate_previous(root/'episode-2', contract)
            collector.save(first/'summary.json',
                           {'complete': True, 'arms': {'wiki': {'within_stage_planning_limit': True}}})
            collector.save(first/'contract.json', dict(contract, files={'code': 'old'}))
            with self.assertRaisesRegex(ValueError, 'contract mismatch'):
                wiki.validate_previous(root/'episode-2', contract)

    def test_second_episode_rejects_a_different_runtime_or_document_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/script.MODEL_REVISION).mkdir()
            self.episode(root, root/'episode-1', 1)
            environment = json.loads((root/'episode-1/environment.json').read_text(encoding='utf-8'))
            collector.save(root/'episode-1/environment.json',
                           dict(environment, environment={'test_only': 'other gpu'}))
            with self.assertRaisesRegex(ValueError, 'GPU/runtime mismatch'):
                self.episode(root, root/'episode-2', 2)
            collector.save(root/'episode-1/environment.json', environment)
            budget = json.loads((root/'episode-1/budget.json').read_text(encoding='utf-8'))
            identifier = next(iter(budget['plan']))
            budget['plan'][identifier] -= 1
            collector.save(root/'episode-1/budget.json', budget)
            with self.assertRaisesRegex(ValueError, 'document budget mismatch'):
                self.episode(root, root/'episode-3', 2)


class NotebookTests(unittest.TestCase):
    def notebook(self):
        return json.loads((wiki.ROOT/'notebooks/colab-wiki-rag-pilot.ipynb').read_text(encoding='utf-8'))

    def test_cells_compile_and_pin_the_pilot_entry_point(self):
        notebook = self.notebook()
        code = {}
        for index, cell in enumerate(notebook['cells']):
            if cell['cell_type'] == 'code':
                source = ''.join(cell['source'])
                compile(source, f'cell-{index}', 'exec')
                code[index] = source
        self.assertIn('experiments/wiki_rag_pilot.py', code[13])
        self.assertIn('--episode', code[13])
        self.assertIn('experiments/wiki-rag/sources.json', code[3])
        self.assertIn('reports/wiki-rag-pilot/inputs.json', code[5])
        # The notebook runs one pushed commit, and the report names the same one.
        pinned = json.loads((wiki.ROOT/'reports/wiki-rag-pilot/cpu-checks.json')
                            .read_text(encoding='utf-8'))['pinned_code_commit']
        self.assertRegex(pinned or '', r'^[0-9a-f]{40}$')
        self.assertIn('REPO_REF = "' + pinned + '"', code[1])

    def test_input_bundle_is_verified_and_results_survive_a_failure(self):
        notebook = self.notebook()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, results = root/'repo', root/'results'
            results.mkdir()
            manifest = repo/'reports/wiki-rag-pilot/inputs.json'
            manifest.parent.mkdir(parents=True)
            data = b'provided input'
            collector.save(manifest, {'open/dev.jsonl': hashlib.sha256(data).hexdigest()})

            def local_path(value):
                return root/str(value).removeprefix('/content/')

            namespace = dict(REPO=repo, RESULTS=results, SOURCE_COMMIT='0'*40, Path=local_path,
                             json=json, hashlib=hashlib, zipfile=__import__('zipfile'),
                             write_json=collector.save)
            fake_colab = SimpleNamespace(drive=SimpleNamespace(mount=lambda _: None))
            code = ''.join(notebook['cells'][5]['source'])
            bundle = root/'drive/MyDrive/wiki-rag/wiki-rag-inputs.zip'
            import zipfile
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
            output = root/'pilot'
            output.mkdir()
            (results/'failure.log').write_text('failure', encoding='utf-8')
            (output/'dev.json.partial').write_text('partial', encoding='utf-8')
            import time
            downloads = []
            with patch.dict(sys.modules, {'google.colab': SimpleNamespace(files=SimpleNamespace(download=downloads.append))}):
                exec(''.join(notebook['cells'][15]['source']),
                     dict(WORK=root, RESULTS=results, PILOT_ROOT=output, time=time,
                          zipfile=zipfile, shutil=shutil))
            with zipfile.ZipFile(downloads[0]) as archive:
                self.assertIn('logs/failure.log', archive.namelist())
                self.assertIn('pilot/dev.json.partial', archive.namelist())


if __name__ == '__main__':
    unittest.main()
