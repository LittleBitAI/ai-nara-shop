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
