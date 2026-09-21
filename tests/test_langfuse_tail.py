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


def ops_for(events, *, include_prompts=True):
    """`include_prompts` 는 수출 검사 통과 상태다. 기본값을 참으로 두는 검사는
    **본문 계약**을 보고, 거짓으로 두는 검사는 **수출 경계**를 본다."""
    state = tail.State(include_prompts=include_prompts)
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


def captured(arm, *, ids=("A", "B"), chunk_start=0, seq=1, fail=None):
    """capture_protocol 1 판형의 한 군을 흉내낸 이벤트 묶음."""
    out = [dict(event="arm_started", time_unix=1.0, arm=arm, sample="dev", selected_count=len(ids),
                system_prompt_sha256=f"prompt-{arm}", schema_sha256="schema",
                output_reserved=1024, prompt_budget=15296),
           dict(event="phase_started", time_unix=1.1, arm=arm, sample="dev", phase="company_size")]
    for index, identifier in enumerate(ids):
        out.append(dict(event="company_size_input", time_unix=1.2, arm=arm, sample="dev",
                        id=identifier, max_chars=16000, requested_max_chars=16000, truncated=False,
                        prompt_tokens=100, token_count_kind="actual", prompt_sha256=f"p-{identifier}",
                        visible_sha256=f"v-{identifier}", phase="company_size"))
    out.append(dict(event="chunk_started", time_unix=2.0, arm=arm, sample="dev",
                    phase="company_size", chunk_start=chunk_start, count=len(ids), ids=list(ids)))
    for index, identifier in enumerate(ids):
        common = dict(arm=arm, sample="dev", phase="company_size", chunk_start=chunk_start,
                      call_seq=seq, call_index=index, id=identifier, identity_status="initial",
                      call_kind="initial")
        out.append(dict(event="model_call_started", time_unix=2.1, prompt_text=[
            {"role": "system", "content": f"SYS-{arm}"}, {"role": "user", "content": identifier}],
            prompt_sha256=f"p-{identifier}", schema_sha256="schema", max_tokens=1024, **common))
        if fail == identifier:
            out.append(dict(event="model_call_failed", time_unix=2.5, error_type="RuntimeError",
                            transport_status="failed", **common))
            continue
        out.append(dict(event="model_call_finished", time_unix=2.5, response_text="{}",
                        prompt_tokens=100, output_tokens=7, finish_reason="stop",
                        transport_status="returned", **common))
        out.append(dict(event="response", time_unix=2.6, arm=arm, sample="dev",
                        phase="company_size", chunk_start=chunk_start, id=identifier,
                        global_index=index, attempt=1, status="valid", response_chars=2))
    out.append(dict(event="chunk_finished", time_unix=3.0, arm=arm, sample="dev",
                    phase="company_size", chunk_start=chunk_start, count=len(ids)))
    out.append(dict(event="arm_finished", time_unix=3.1, arm=arm, sample="dev", status="complete",
                    stage_seconds=1.0, valid_response_count=len(ids), failed_response_count=0))
    return out


ROOT_EVENT = dict(event="run_started", time_unix=0.5, mode="pending", experiment="a8",
                  dataset="dev", capture_protocol=1, code_sha256="abc1234def",
                  expected_model={"id": "google/gemma-4-26B-A4B-it", "revision": "rev"})


class CapturedRunProjection(unittest.TestCase):
    """새 판형은 군을 가르고 물리 호출을 generation 으로 만든다."""

    def test_arms_and_calls_get_distinct_keys_and_close_in_order(self):
        events = [ROOT_EVENT] + captured("control") + captured("a8") + \
                 [dict(event="run_succeeded", time_unix=9.0, seconds=8.5)]
        ops, state = ops_for(events)
        opens = [o.key for o in ops if o.action == "open"]
        closes = [o.key for o in ops if o.action == "close"]
        self.assertEqual(sorted(set(opens)), sorted(set(closes)))
        self.assertEqual(len(opens), len(closes))
        self.assertEqual(opens.count("run"), 1)
        # 군·청크·호출 key 에 군 이름이 들어간다 — 안 들어가면 두 군이 겹친다.
        self.assertIn("arm:control:dev", opens)
        self.assertIn("arm:a8:dev", opens)
        self.assertIn("chunk:control:dev:company_size:0", opens)
        self.assertIn("chunk:a8:dev:company_size:0", opens)
        generations = [o for o in ops if o.kind == "generation"]
        self.assertEqual(len(generations), 4)
        self.assertEqual(len({o.key for o in generations if o.action == "open"}), 4)
        # 청크가 군별 부모다.
        self.assertEqual({o.parent for o in generations if o.action == "open"},
                         {"chunk:control:dev:company_size:0", "chunk:a8:dev:company_size:0"})
        self.assertEqual({o.parent for o in ops if o.key.startswith("chunk:")},
                         {"arm:control:dev", "arm:a8:dev", None})
        self.assertIsNone(state.arm)
        self.assertEqual(state.calls, {})

    def test_same_notice_in_two_arms_does_not_share_a_key(self):
        ops, _ = ops_for([ROOT_EVENT] + captured("control") + captured("a8") +
                         [dict(event="run_succeeded", time_unix=9.0)])
        for identifier in ("A", "B"):
            keys = {o.key for o in ops if o.kind == "generation" and o.name == identifier}
            self.assertEqual(len(keys), 2, identifier)     # 군마다 하나
        prompts = {json.loads(o.attrs["langfuse.observation.input"])[0]["content"]
                   for o in ops if o.kind == "generation" and o.action == "open"}
        self.assertEqual(prompts, {"SYS-control", "SYS-a8"})

    def test_response_is_a_parse_event_not_a_second_generation(self):
        ops, _ = ops_for([ROOT_EVENT] + captured("control") +
                         [dict(event="run_succeeded", time_unix=9.0)])
        self.assertEqual(len([o for o in ops if o.kind == "generation" and o.action == "open"]), 2)
        self.assertEqual(len([o for o in ops if o.key.startswith("parse:")]), 2)
        self.assertFalse(any(o.key.startswith("gen:") for o in ops))   # 옛 투영이 겹치지 않는다

    def test_failed_call_closes_with_an_error_and_no_invented_usage(self):
        ops, _ = ops_for([ROOT_EVENT] + captured("control", fail="B") +
                         [dict(event="run_succeeded", time_unix=9.0)])
        closed = [o for o in ops if o.action == "close" and o.key.startswith("call:")]
        self.assertEqual(len(closed), 2)
        failed = next(o for o in closed if o.level == "ERROR")
        self.assertNotIn("langfuse.observation.usage_details", failed.attrs)
        self.assertEqual(failed.status, "RuntimeError")

    def test_one_sided_usage_does_not_become_a_total(self):
        events = [ROOT_EVENT] + captured("control", ids=("A",))
        finished = next(e for e in events if e["event"] == "model_call_finished")
        finished["output_tokens"] = None
        ops, _ = ops_for(events + [dict(event="run_succeeded", time_unix=9.0)])
        closed = next(o for o in ops if o.action == "close" and o.key.startswith("call:"))
        self.assertNotIn("langfuse.observation.usage_details", closed.attrs)
        self.assertIn("langfuse.observation.metadata.usage_note", closed.attrs)

    def test_unclosed_call_and_arm_are_closed_by_the_run_end(self):
        events = [ROOT_EVENT] + captured("control", ids=("A",))
        events = [e for e in events
                  if e["event"] not in ("model_call_finished", "chunk_finished", "arm_finished")]
        ops, state = ops_for(events + [dict(event="run_failed", time_unix=9.0,
                                            error_type="KeyboardInterrupt")])
        closes = [o for o in ops if o.action == "close"]
        self.assertIn("no model_call_finished", [o.status for o in closes])
        self.assertEqual({o.key for o in ops if o.action == "open"},
                         {o.key for o in closes})
        self.assertEqual(state.calls, {})

    def test_old_logs_without_capture_protocol_keep_the_legacy_projection(self):
        legacy = [dict(event="run_started", time_unix=0.5, mode="live", code_sha256="abc1234"),
                  dict(event="chunk_started", time_unix=1.0, phase="baseline", chunk_start=0, count=1),
                  dict(event="response", time_unix=2.0, phase="baseline", global_index=0,
                       id="A", attempt=1, status="valid", response_chars=2,
                       prompt_tokens=12, output_tokens=3),
                  dict(event="run_succeeded", time_unix=3.0)]
        ops, state = ops_for(legacy)
        self.assertIsNone(state.capture_protocol)
        self.assertTrue(any(o.key == "gen:baseline:0:1" for o in ops))   # 옛 경로 유지
        self.assertFalse(any(o.key.startswith("parse:") for o in ops))

    def test_the_real_mode_reaches_the_root_so_live_and_double_are_distinguishable(self):
        """루트는 생성 전에 `pending` 으로 열린다. 실제 mode 가 루트까지 오지 않으면
        Langfuse 에서 실제 모델 회차와 대역 실행이 같은 이름으로 끝난다."""
        events = [dict(event="run_started", time_unix=0.5, mode="pending", code_sha256="abc1234def",
                       capture_protocol=1, dataset="dev"),
                  dict(event="model_loading", time_unix=0.6),
                  dict(event="model_loaded", time_unix=0.9, mode="live", load_seconds=12.0,
                       token_count_kind="actual"),
                  dict(event="run_succeeded", time_unix=3.0)]
        ops, state = ops_for(events)
        self.assertEqual(state.actual_mode, "live")
        self.assertEqual(state.trace_name, "nara live abc1234")
        update = next(o for o in ops if o.action == "update")
        self.assertEqual((update.key, update.name), ("run", "nara live abc1234"))
        self.assertEqual(update.attrs["langfuse.trace.name"], "nara live abc1234")
        self.assertEqual(update.attrs["langfuse.observation.metadata.mode"], "live")
        self.assertEqual(update.attrs["langfuse.observation.metadata.mode_at_start"], "pending")
        # 루트를 닫을 때도 실제 mode 로 끝난다 — `pending` 으로 남지 않는다.
        end = next(o for o in ops if o.action == "close" and o.key == "run")
        self.assertEqual(end.attrs["langfuse.observation.metadata.mode"], "live")
        self.assertEqual(end.attrs["langfuse.observation.metadata.model_loaded"], "yes")

    def test_a_run_that_never_loaded_a_model_does_not_claim_a_mode(self):
        ops, state = ops_for([dict(event="run_started", time_unix=0.5, mode="pending",
                                   code_sha256="abc1234def", capture_protocol=1),
                              dict(event="run_failed", time_unix=1.0, error_type="ValueError",
                                   error_message="budget")])
        self.assertIsNone(state.actual_mode)
        self.assertFalse(any(o.action == "update" for o in ops))
        end = next(o for o in ops if o.action == "close" and o.key == "run")
        self.assertEqual(end.attrs["langfuse.observation.metadata.mode"], "pending")
        self.assertEqual(end.attrs["langfuse.observation.metadata.model_loaded"], "no")


class PromptExportBoundary(unittest.TestCase):
    """프롬프트 전문은 로컬 Langfuse + 고정 공개 dev 회차에서만 나간다."""

    def _dev_ids(self):
        dev = ROOT / "open/dev.jsonl"
        return dev, [json.loads(line)["id"]
                     for line in dev.read_text(encoding="utf-8").splitlines() if line.strip()]

    def _events(self, tmp, *, notices=("A", "B"), **overrides):
        event = dict(event="run_started", time_unix=0.5, mode="pending", capture_protocol=1,
                     dataset="dev", code_sha256="abc1234def")
        event.update(overrides)
        path = Path(tmp) / "diagnostics.jsonl"
        lines = [event] + captured("control", ids=tuple(notices)) + \
            [dict(event="run_succeeded", time_unix=9.0)]
        path.write_text("".join(json.dumps(line, ensure_ascii=False) + "\n" for line in lines),
                        encoding="utf-8", newline="\n")
        return path

    def test_bodies_are_withheld_by_default_and_the_withholding_is_visible(self):
        ops, _ = ops_for([ROOT_EVENT] + captured("control") +
                         [dict(event="run_succeeded", time_unix=9.0)], include_prompts=False)
        bodies = {o.key for o in ops if "langfuse.observation.input" in o.attrs
                  or "langfuse.observation.output" in o.attrs}
        # 루트의 settings·회차 요약은 본문이 아니다. 프롬프트·응답 전문은 하나도 없어야 한다.
        self.assertEqual(bodies, {"run"})
        marked = [o for o in ops if o.attrs.get("langfuse.observation.metadata.prompt_capture")
                  == "withheld"]
        self.assertTrue(marked, "막았다는 사실을 남겨야 '본문 없는 회차' 와 갈린다")
        with_prompts, _ = ops_for([ROOT_EVENT] + captured("control") +
                                  [dict(event="run_succeeded", time_unix=9.0)])
        self.assertTrue(any("langfuse.observation.input" in o.attrs
                            for o in with_prompts if o.kind == "generation"))

    def test_non_local_host_is_refused(self):
        dev, ids = self._dev_ids()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._events(tmp, notices=ids[:2], dataset_sha256=tail._sha256(dev),
                                dev_ids=ids)
            for host in ("https://cloud.langfuse.com", "http://localhost:3002/../x",
                         "http://user:pw@localhost:3002", "http://localhost:3003",
                         "http://localhost:3002?to=evil", "http://127.0.0.1:3002#x"):
                verdict = tail.validate_dev_export(path, dev, host=host)
                self.assertFalse(verdict["allowed"], host)
                self.assertIn(f"host_not_local:{host}", verdict["reasons"])

    def test_a_pinned_dev_run_on_the_local_host_is_allowed(self):
        dev, ids = self._dev_ids()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._events(tmp, notices=ids[:2], dataset_sha256=tail._sha256(dev),
                                dev_ids=ids)
            verdict = tail.validate_dev_export(path, dev, host="http://localhost:3002")
        self.assertTrue(verdict["allowed"], verdict["reasons"])
        self.assertEqual(verdict["dev_records"], len(ids))
        self.assertEqual(verdict["observed_records"], 2)

    def test_a_notice_outside_the_pinned_dev_is_refused(self):
        """고정 dev 로 이름만 붙이고 다른 공고를 돌린 로그. 접두사만 보면 통과한다."""
        dev, ids = self._dev_ids()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._events(tmp, notices=(ids[0], "PPS-DEV-9999"),
                                dataset_sha256=tail._sha256(dev), dev_ids=ids)
            verdict = tail.validate_dev_export(path, dev, host="http://localhost:3002")
        self.assertFalse(verdict["allowed"])
        self.assertIn("unknown_ids:PPS-DEV-9999", verdict["reasons"])

    def test_a_log_that_declares_a_different_id_set_is_refused(self):
        dev, ids = self._dev_ids()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._events(tmp, notices=ids[:2], dataset_sha256=tail._sha256(dev),
                                dev_ids=ids[:2])      # 200건 파일을 2건이라고 적은 로그
            verdict = tail.validate_dev_export(path, dev, host="http://localhost:3002")
        self.assertFalse(verdict["allowed"])
        self.assertIn("dev_ids_mismatch", verdict["reasons"])

    def test_an_unidentified_prompt_body_is_never_exported(self):
        dev, ids = self._dev_ids()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._events(tmp, notices=ids[:2], dataset_sha256=tail._sha256(dev),
                                dev_ids=ids)
            lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            for line in lines:
                if line["event"] == "model_call_started":
                    line["identity_status"] = "ambiguous"
            path.write_text("".join(json.dumps(line, ensure_ascii=False) + "\n" for line in lines),
                            encoding="utf-8", newline="\n")
            verdict = tail.validate_dev_export(path, dev, host="http://localhost:3002")
        self.assertFalse(verdict["allowed"])
        self.assertTrue(any(r.startswith("unknown_ids:") for r in verdict["reasons"]))

    def test_a_dev_file_that_is_not_the_pinned_one_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            other = Path(tmp) / "dev.jsonl"
            other.write_text('{"id": "A", "docs": []}\n', encoding="utf-8", newline="\n")
            path = self._events(tmp, dataset_sha256=tail._sha256(other), dev_ids=["A"])
            verdict = tail.validate_dev_export(path, other, host="http://localhost:3002")
        self.assertFalse(verdict["allowed"])
        self.assertIn("dev_input_not_pinned", verdict["reasons"])


if __name__ == "__main__":
    unittest.main()
