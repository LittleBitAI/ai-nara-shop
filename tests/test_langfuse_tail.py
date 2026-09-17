"""사이드카가 실제 진단 이벤트를 span 으로 옳게 바꾸는지 본다. 네트워크 없음."""

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module      # dataclass 는 자기 모듈을 sys.modules 에서 찾는다
    spec.loader.exec_module(module)
    return module


baseline = _load("baseline", ROOT / "script.py")
tail = _load("langfuse_tail", ROOT / "tools" / "langfuse_tail.py")

DATA = str(ROOT / "open/data")
INPUT = str(ROOT / "open/data/test.jsonl.gz")


def ops_for(events):
    state = tail.State()
    out = []
    for event in events:
        out.extend(tail.plan(event, state))
    return out, state


def read_events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


class LangfuseTail(unittest.TestCase):
    def test_mock_run_becomes_one_closed_trace_with_a_generation_per_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "submission.csv"
            baseline.run(INPUT, str(out), baseline.MockRunner, limit=2, chunk=128,
                         max_chars=16000, data_dir=DATA)
            events = read_events(out.with_name("diagnostics.jsonl"))

        ops, state = ops_for(events)
        opened = [o for o in ops if o.action == "open"]
        closed = [o for o in ops if o.action == "close"]
        # 열린 span 은 전부 닫혀야 한다. 안 닫히면 UI 에 미완으로 남는다.
        self.assertEqual(sorted(o.key for o in opened), sorted(o.key for o in closed))
        self.assertEqual([o.key for o in opened].count("run"), 1)

        responses = [e for e in events if e["event"] == "response"]
        generations = [o for o in ops if o.kind == "generation"]
        self.assertEqual(len(generations), len(responses))
        self.assertTrue(responses, "mock 실행이 response 이벤트를 남겨야 한다")
        for op, event in zip(generations, responses):
            self.assertEqual(op.name, event["id"])
            self.assertTrue(op.parent.startswith("chunk:"))
            self.assertLessEqual(op.start, op.end)
            self.assertIsNone(op.level)
            # mock 러너는 토큰 정보를 안 만든다. 없는 값을 0으로 지어내지 않는다.
            self.assertNotIn("langfuse.observation.usage_details", op.attrs)
            # 원문은 --debug-responses 실행에만 있다. 기본 실행에서 새면 안 된다.
            self.assertNotIn("langfuse.observation.input", op.attrs)
            self.assertNotIn("langfuse.observation.output", op.attrs)
        self.assertTrue(state.trace_name.startswith("nara mock "))

    def test_failed_run_closes_the_trace_with_an_error_level(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "submission.csv"

            class Broken(baseline.MockRunner):
                def chat(self, batch, items=None):
                    raise ValueError("test runtime cause")

            with self.assertRaises(RuntimeError):
                baseline.run(INPUT, str(out), Broken, limit=1, chunk=128,
                             max_chars=16000, data_dir=DATA)
            events = read_events(out.with_name("diagnostics.jsonl"))

        ops, _ = ops_for(events)
        run_close = [o for o in ops if o.action == "close" and o.key == "run"]
        self.assertEqual(len(run_close), 1)
        self.assertEqual(run_close[0].level, "ERROR")
        self.assertIn("test runtime cause", run_close[0].status)
        failures = [o for o in ops if o.level == "ERROR" and o.kind == "event"]
        self.assertTrue(failures, "batch_failed/retry_failed 는 ERROR 로 남아야 한다")

    def test_debug_fields_carry_the_prompt_and_response_when_present(self):
        events = [
            {"event": "run_started", "time_unix": 10.0, "mode": "live",
             "code_sha256": "abc1234def", "expected_model": {"id": "google/gemma-4-26B-A4B-it"}},
            {"event": "chunk_started", "time_unix": 11.0, "chunk_start": 0, "count": 1},
            {"event": "response", "time_unix": 20.0, "chunk_start": 0, "global_index": 0,
             "id": "PPS-DEV-11", "attempt": 1, "status": "valid", "prompt_tokens": 12,
             "output_tokens": 3, "finish_reason": "stop",
             "prompt_text": "[Notice documents] 지역제한 …", "response_text": "{\"v8\": 1}"},
            {"event": "run_succeeded", "time_unix": 30.0, "count": 1, "model_success_count": 1},
        ]
        ops, state = ops_for(events)
        generation = next(o for o in ops if o.kind == "generation")
        self.assertEqual(generation.attrs["langfuse.observation.input"], "[Notice documents] 지역제한 …")
        self.assertEqual(generation.attrs["langfuse.observation.output"], "{\"v8\": 1}")
        self.assertEqual(generation.attrs["langfuse.observation.model.name"],
                         "google/gemma-4-26B-A4B-it")
        self.assertEqual(json.loads(generation.attrs["langfuse.observation.usage_details"]),
                         {"input": 12, "output": 3, "total": 15})
        self.assertEqual(state.trace_name, "nara live abc1234")
        # 배치 호출이므로 시작은 청크와 같다. 끝은 그 공고의 응답 시각이다.
        self.assertEqual((generation.start, generation.end), (11.0, 20.0))
        self.assertEqual([o.key for o in ops if o.action == "close"], ["chunk:baseline:0", "run"])


if __name__ == "__main__":
    unittest.main()
