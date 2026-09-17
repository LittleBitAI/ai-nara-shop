"""모델 없이 검증하는 제출 계약·실패 회귀 검사. live 성능 검사가 아니다."""

import copy
import csv
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("baseline", ROOT / "script.py")
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)


def record():
    return {"id": "sample", "docs": [{"doc_id": "a", "type": "공고문", "text": "공고 본문입니다."}],
            "meta": {"적용계약법": "국가", "지역제한여부": None},
            "input_completeness": {"완전관측": False}, "dropped_doc_counts": {"규격서": 1}}


def valid():
    return {v: {"위반여부": 0, "근거문구": None} for v in baseline.ITEMS}


class BaselineTests(unittest.TestCase):
    def test_split_retry_validates_every_group_without_changing_defaults(self):
        runner = object.__new__(baseline.VLLMRunner)
        runner.sp = SimpleNamespace(max_tokens=2048, structured_outputs=SimpleNamespace(
            json=baseline.decode_schema(str(ROOT / "open/data"))))
        runner.count_tokens = lambda messages: 14000
        good = valid()
        good["v10"]["위반여부"] = 1
        calls = []
        def chat(batch, sampling_params, **kwargs):
            keys = sampling_params.structured_outputs.json["required"]
            if len(keys) <= 6:
                for k in keys:
                    if k not in baseline.ABSENCE:
                        self.assertEqual(sampling_params.structured_outputs.json["properties"][k]
                                         ["properties"]["근거문구"]["maxLength"], 100)
            calls.append(list(keys))
            # A deterministic all-item completion always truncates; smaller schemas succeed.
            text = json.dumps({k: good[k] for k in keys}) if len(keys) <= 6 else '{"v1":'
            return [SimpleNamespace(outputs=[SimpleNamespace(text=text, token_ids=[1],
                    finish_reason="stop" if len(keys) <= 6 else "length", stop_reason=None)],
                    prompt_token_ids=[1])]
        runner.llm = SimpleNamespace(chat=chat)
        messages = [{"role": "system", "content": "판정 지시"}, {"role": "user", "content": "공고 원문"}]
        original = copy.deepcopy(messages)
        result = baseline.run_chunk(runner, [messages])
        self.assertEqual(baseline.parse_judgment(result[0])[0], good)
        self.assertEqual([len(keys) for keys in calls], [24, 6, 6, 6, 6])
        self.assertEqual(sum(calls[1:], []), baseline.ITEMS)
        self.assertEqual(messages, original)
        self.assertEqual(runner.sp.max_tokens, 2048)
        self.assertEqual(runner.sp.structured_outputs.json["required"], baseline.ITEMS)
        self.assertEqual(runner.sp.structured_outputs.json["properties"]["v1"]
                         ["properties"]["근거문구"]["maxLength"], 500)
        runner.llm.chat = lambda *a, **kw: [SimpleNamespace(outputs=[], prompt_token_ids=[1])]
        with self.assertRaises(RuntimeError):
            baseline.run_chunk(runner, [messages])
        def bad_second_group(batch, sampling_params, **kwargs):
            outputs = chat(batch, sampling_params, **kwargs)
            if sampling_params.structured_outputs.json["required"][0] == "v7":
                outputs[0].outputs[0].text = "{}"
            return outputs
        runner.llm.chat = bad_second_group
        calls.clear()
        with self.assertRaisesRegex(RuntimeError, "정상 6항목"):
            baseline.run_chunk(runner, [messages])
        self.assertEqual([len(keys) for keys in calls], [24, 6, 6])
        self.assertEqual([g["status"] for g in runner.last_response_info[0]["groups"]], ["valid", "failed"])
        runner.count_tokens = lambda messages: baseline.MAX_MODEL_LEN - 64
        with self.assertRaisesRegex(RuntimeError, "토큰 예산 없음"):
            baseline.run_chunk(runner, [messages])

    def test_provided_law_and_product_context(self):
        laws, products = baseline.load_sme_reference(str(ROOT / "open/data"))
        self.assertIn("제7조(중소기업자간 경쟁입찰의 예외 등)", laws)
        self.assertIn("제9조(직접생산의 확인 등)", laws)
        rec = record()
        rec["meta"]["세부품명번호목록"] = None
        rec["docs"][0]["text"] = "세부품명번호 1110152201 활성탄 구매"
        before = copy.deepcopy(rec)
        prompt = baseline.build_user_prompt(rec, 16000, products=products)
        self.assertIn("석탄계 입상활성탄 및 석유화학계 활성탄 제외", prompt)
        self.assertIn("1110152201", prompt)
        self.assertEqual(rec, before)
        # A different notice must not inherit a preceding notice's product lookup.
        other = baseline.build_user_prompt(record(), 16000, products=products)
        self.assertNotIn("1110152201", other)
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(FileNotFoundError):
            baseline.load_sme_reference(tmp)

    def test_diagnostics_preserve_initial_and_retry_metadata(self):
        good = json.dumps(valid())
        runner = object.__new__(baseline.VLLMRunner)
        runner.sp = SimpleNamespace(max_tokens=2048)
        # Exercise logging independently of the split-retry strategy tested above.
        runner.retry_chat = runner.chat
        calls = []
        def chat(batch, **kwargs):
            calls.append(len(batch))
            texts = [good, good[:-2]] if len(calls) == 1 else [""]
            return [SimpleNamespace(outputs=[SimpleNamespace(
                text=text, token_ids=[1] * (2048 if text else 0),
                finish_reason="length" if text else "stop", stop_reason=None)],
                prompt_token_ids=[1, 2, 3]) for text in texts]
        runner.llm = SimpleNamespace(chat=chat)
        events = []
        with self.assertRaisesRegex(RuntimeError, "global_index=129"):
            baseline.run_chunk(runner, [[], []], start=128, ids=["first", "failed"],
                               emit=lambda event, **fields: events.append({"event": event, **fields}))
        responses = [e for e in events if e["event"] == "response"]
        self.assertEqual(calls, [2, 1])
        self.assertEqual([(e["global_index"], e["attempt"]) for e in responses],
                         [(128, 1), (129, 1), (129, 2)])
        self.assertEqual(responses[1]["finish_reason"], "length")
        self.assertEqual(responses[1]["output_tokens"], 2048)
        self.assertEqual(responses[2]["finish_reason"], "stop")
        self.assertEqual(responses[2]["output_tokens"], 0)
        self.assertEqual(responses[2]["id"], "failed")
        self.assertNotIn("response_text", json.dumps(events))
        self.assertNotIn(good, json.dumps(events))
        events.clear()
        runner.llm.chat = lambda batch, **kw: [SimpleNamespace(outputs=[SimpleNamespace(
            text=good, token_ids=[1], finish_reason="stop", stop_reason=None)], prompt_token_ids=[1])]
        baseline.run_chunk(runner, [[]], debug_responses=True,
                           emit=lambda event, **kw: events.append(kw))
        self.assertEqual(events[0]["response_text"], good)
        # A call exception must not inherit completion metadata from the previous call.
        def broken(*args, **kwargs):
            raise ValueError("runtime failure")
        runner.llm.chat = broken
        events.clear()
        with self.assertRaisesRegex(RuntimeError, "runtime failure"):
            baseline.run_chunk(runner, [[]], emit=lambda event, **kw: events.append(kw))
        self.assertTrue(all("finish_reason" not in e for e in events))

    def test_failed_run_leaves_diagnostics_and_no_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "submission.csv"
            class Broken(baseline.MockRunner):
                def chat(self, batch):
                    raise ValueError("test runtime cause")
            with self.assertRaisesRegex(RuntimeError, "test runtime cause"):
                baseline.run(str(ROOT / "open/data/test.jsonl.gz"), str(out), Broken,
                             limit=1, chunk=128, max_chars=16000, data_dir=str(ROOT / "open/data"))
            path = out.with_name("diagnostics.jsonl")
            events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(events[0]["event"], "run_started")
            self.assertEqual(events[-1]["event"], "run_failed")
            self.assertIn("test runtime cause", events[-1]["traceback"])
            self.assertFalse(out.exists())
            self.assertFalse(out.with_name("run_report.json").exists())
            raw = path.read_bytes()
            with self.assertRaises(ValueError):
                baseline.run(str(ROOT / "open/data/test.jsonl.gz"), str(out), Broken,
                             limit=1, chunk=128, max_chars=16000, data_dir=str(ROOT / "open/data"))
            self.assertEqual(path.read_bytes(), raw)
            command = [sys.executable, "-X", "utf8", str(ROOT / "script.py"),
                       "--data-dir", str(ROOT / "open/data"), "--model-dir", str(Path(tmp) / "missing-model"),
                       "--output-dir", str(Path(tmp) / "load-failed")]
            failed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(failed.returncode, 1)
            self.assertIn("Traceback", failed.stderr)
            load_events = [json.loads(line) for line in
                           (Path(tmp) / "load-failed/diagnostics.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(load_events[-1]["event"], "run_failed")
            self.assertIn("로컬 디렉터리", load_events[-1]["error_message"])
            self.assertIn("items", load_events[1]["sha256"])

    def test_strict_output(self):
        obj = valid()
        for value in (True, "1", 0.5, 1.0, None):
            with self.subTest(value=value):
                bad = copy.deepcopy(obj)
                bad["v1"]["위반여부"] = value
                with self.assertRaises(ValueError):
                    baseline.parse_judgment(json.dumps(bad))
        for text in ("", "{}", "[]", '{"v1":', json.dumps({**obj, "v25": {}})):
            with self.subTest(text=text[:30]), self.assertRaises(ValueError):
                baseline.parse_judgment(text)
        self.assertEqual(baseline.parse_judgment(json.dumps(obj))[0], obj)
        # Gemma thought text must never supply an answer when the final JSON is absent.
        thought = '<|channel>thought\n' + json.dumps(obj) + '<channel|>'
        with self.assertRaises(ValueError):
            baseline.parse_judgment(thought)
        self.assertEqual(baseline.parse_judgment(thought + json.dumps(obj))[0], obj)

    def test_budget_is_hard_limit(self):
        class TooLarge:
            def count_tokens(self, messages):
                return 20000
        with self.assertRaises(ValueError):
            baseline.fit_to_budget(record(), "system", TooLarge(), 2000, budget=100)
        class Counter:
            def count_tokens(self, messages):
                return sum(len(m["content"]) for m in messages)
        rec = record()
        rec["docs"][0]["text"] = "가" * 5000
        _, count, _ = baseline.fit_to_budget(rec, "system", Counter(), 4000, budget=1500)
        self.assertLessEqual(count, 1500)

    def test_failed_model_never_becomes_zero_success(self):
        class Broken:
            def chat(self, batch):
                raise RuntimeError("simulated model failure")
        with self.assertRaises(RuntimeError):
            baseline.run_chunk(Broken(), [[{"role": "user", "content": "공고"}]])
        class Retry:
            calls = []
            def chat(self, batch):
                self.calls.append(len(batch))
                return [json.dumps(valid()), ""] if len(batch) == 2 else [json.dumps(valid())]
        runner = Retry()
        self.assertEqual(len(baseline.run_chunk(runner, [[], []])), 2)
        self.assertEqual(runner.calls, [2, 1])

    def test_attachment_and_observability(self):
        rec = record()
        rec["docs"].append({"doc_id": "b", "type": "과업지시서", "text": "첨부의중요조건" * 1000})
        context = baseline.build_context(rec, 1000)
        self.assertIn("첨부의중요조건", context)
        self.assertIn("절단", context)
        prompt = baseline.build_user_prompt(rec, 1000)
        self.assertIn("완전관측", prompt)
        self.assertIn("false", prompt)
        self.assertIn("null", prompt)
        self.assertEqual(rec["docs"][1]["text"], "첨부의중요조건" * 1000)

    def test_evidence_does_not_cross_documents(self):
        rec = record()
        rec["docs"][0]["text"] = '첫째문서'
        rec["docs"].append({"doc_id": "b", "type": "규격서", "text": '둘째문서, "인용"'})
        obj = valid()
        obj["v1"] = {"위반여부": 1, "근거문구": "첫째문서\n둘째문서"}
        self.assertEqual(baseline.postprocess(obj, rec)["v1"]["근거문구"], "")
        obj["v1"]["근거문구"] = '둘째문서, "인용"'
        self.assertEqual(baseline.postprocess(obj, rec)["v1"]["근거문구"], '둘째문서, "인용"')
        schema = baseline.decode_schema(str(ROOT / "open/data"))
        self.assertEqual(schema["properties"]["v1"]["properties"]["근거문구"]["maxLength"], 500)

    def test_mock_cli_and_invalid_inputs(self):
        with tempfile.TemporaryDirectory(prefix="t1 한글 ") as tmp:
            tmp = Path(tmp)
            env = {**os.environ, "PPS_DATA_DIR": str(ROOT / "open/data"),
                   "PPS_OUTPUT_DIR": str(tmp / "output")}
            command = [sys.executable, "-X", "utf8", str(ROOT / "script.py"), "--mock"]
            success = subprocess.run(command, env=env, cwd=tmp, capture_output=True, timeout=30)
            self.assertEqual(success.returncode, 0, success.stderr.decode("utf-8"))
            output = tmp / "output/submission.csv"
            raw = output.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertNotIn(b"\r", raw)
            with output.open(encoding="utf-8", newline="") as f:
                rows = list(csv.reader(f))
            self.assertEqual(rows[0], baseline.COLUMNS)
            self.assertEqual(len(rows), 11)
            report = json.loads((tmp / "output/run_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["mode"], "mock")
            self.assertEqual(report["model_success_count"], 0)
            self.assertIsNone(report["model"])
            # Reject reusing old success, including after a failing run.
            repeated = subprocess.run(command, env=env, cwd=tmp, capture_output=True, timeout=30)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertEqual(output.read_bytes(), raw)
            source = tmp / "input.jsonl"
            for name, text in [("empty", ""), ("duplicate", (json.dumps(record()) + "\n") * 2)]:
                source.write_text(text, encoding="utf-8")
                env["PPS_OUTPUT_DIR"] = str(tmp / name)
                failed = subprocess.run(command + ["--input", str(source)], env=env, cwd=tmp,
                                        capture_output=True, timeout=30)
                self.assertNotEqual(failed.returncode, 0)
                self.assertFalse((tmp / name / "submission.csv").exists())

    def test_csv_and_template_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "submission.csv"
            path.write_text(",".join(baseline.COLUMNS) + "\n\n", encoding="utf-8")
            self.assertTrue(baseline.validate_csv(str(path), ["sample"]))
            row = baseline.to_row("sample", baseline.postprocess(valid(), record()))
            row["e1"] = "비위반근거"
            baseline.write_csv([row], str(path))
            self.assertTrue(baseline.validate_csv(str(path), ["sample"]))
            row["v1"] = 1
            row["e1"] = '원문, "인용"\n다음 줄'
            baseline.write_csv([row], str(path))
            self.assertEqual(baseline.validate_csv(str(path), ["sample"]), [])
            with path.open(encoding="utf-8", newline="") as f:
                self.assertEqual(list(csv.DictReader(f))[0]["e1"], row["e1"])
        class Tokenizer:
            def apply_chat_template(self, messages, **kwargs):
                assert kwargs.get("enable_thinking") is False
                return {"input_ids": [1, 2, 3]}
        runner = object.__new__(baseline.VLLMRunner)
        runner.tok = Tokenizer()
        self.assertEqual(runner.count_tokens([]), 3)


if __name__ == "__main__":
    unittest.main()
