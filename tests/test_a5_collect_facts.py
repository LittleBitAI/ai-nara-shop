"""CPU contract checks only; these do not claim successful GPU inference."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from experiments import a5_collect_facts as a5


class FakeRunner:
    environment = {"test_only": True}
    load_seconds = 0

    def __init__(self, *args, **kwargs):
        self.calls = []
        self.fail = False

    def count_tokens(self, messages):
        assert "DO_NOT_COPY_REGISTERED_VALUE" not in str(messages)
        assert messages[0]["content"] == a5.script.COMPANY_SIZE_PROMPT
        return 100

    def chat(self, batch, items):
        assert items == a5.script.COMPANY_SIZE_KEYS
        self.calls.append(len(batch))
        response = "invalid" if self.fail else json.dumps({"company_size": a5.script.empty_company_size()})
        return [response] * len(batch)


def records(prefix, count):
    return [dict(id=f"{prefix}-{i}", meta={"조항호내용": "DO_NOT_COPY_REGISTERED_VALUE"},
                 docs=[dict(doc_id="D0", type="공고문", text="물품 구매 공고")],
                 input_completeness={"완전관측": True}, dropped_doc_counts={}) for i in range(count)]


class A5FactsTests(unittest.TestCase):
    def test_resume_and_failed_shard_preserve_completed_observations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root / a5.script.MODEL_REVISION
            model.mkdir()
            source, output = root / "unlabeled.jsonl", root / "results"
            source.write_text("synthetic test data\n", encoding="utf-8")
            runner = FakeRunner()
            real_hash = a5.file_hash
            argv = ["a5", "--input", str(source), "--output-dir", str(output), "--model-dir", str(model)]
            with patch.object(sys, "argv", argv), \
                    patch.object(a5, "file_hash", side_effect=lambda p: a5.UNLABELED_SHA256 if Path(p) == source else real_hash(p)), \
                    patch.object(a5.script, "iter_records", side_effect=lambda p: iter(records("dev", 200) if Path(p).name == "dev.jsonl" else records("unlabeled", 20000))), \
                    patch.object(a5.script, "VLLMRunner", return_value=runner):
                a5.main()
                self.assertEqual(sum(runner.calls), 1200)
                first_bytes = (output / "unlabeled-00.json").read_bytes()
                a5.main()
                self.assertEqual(sum(runner.calls), 2200)
                self.assertEqual((output / "unlabeled-00.json").read_bytes(), first_bytes)
                summary = json.loads((output / "summary.json").read_text())
                self.assertEqual(summary["unlabeled"]["count"], 2000)
                self.assertIsNone(summary["unlabeled_over_dev_rate"])
                self.assertFalse(summary["complete"])
                runner.fail = True
                with self.assertRaises(RuntimeError):
                    a5.main()
                self.assertFalse((output / "unlabeled-02.json").exists())
                self.assertEqual((output / "unlabeled-00.json").read_bytes(), first_bytes)
                self.assertEqual(json.loads((output / "summary.json").read_text())["unlabeled"]["count"], 2000)
                damaged = json.loads(first_bytes)
                damaged["payload"]["rows"][0]["h2_fired"] = True
                a5.save(output / "unlabeled-00.json", damaged)
                with self.assertRaisesRegex(ValueError, "contract/content mismatch"):
                    a5.main()

    def collected(self, observe, runner=None, count=3):
        """같은 대역 응답으로 한 청크를 수집하고 (payload, 이벤트) 를 돌려준다."""
        events = []
        runner = runner or FakeRunner()
        payload = a5.collect(records("obs", count), runner, (),
                             lambda event, **fields: events.append(dict(event=event, **fields)),
                             observe=observe)
        return payload, events

    def test_observation_does_not_change_calls_or_payload(self):
        """관측 ON/OFF 가 메시지·호출·원응답을 바꾸면 그 관측은 실험을 오염시킨다."""
        off_runner, on_runner = FakeRunner(), FakeRunner()
        off, off_events = self.collected(False, off_runner)
        on, on_events = self.collected(True, on_runner)
        self.assertEqual(off_runner.calls, on_runner.calls)          # 호출 횟수·batch 크기 동일
        self.assertEqual([r["response_text"] for r in off["rows"]],
                         [r["response_text"] for r in on["rows"]])
        self.assertEqual([r["prompt_tokens"] for r in off["rows"]],
                         [r["prompt_tokens"] for r in on["rows"]])
        self.assertEqual([r["max_chars"] for r in off["rows"]], [r["max_chars"] for r in on["rows"]])
        kinds = lambda events: [e["event"] for e in events]
        self.assertEqual(kinds(off_events), ["company_size_input"] * 3 + ["response"] * 3)
        # 관측은 이벤트만 늘린다. 기존 이벤트의 순서와 키는 그대로다.
        self.assertEqual([e for e in kinds(on_events) if e in ("company_size_input", "response")],
                         kinds(off_events))
        for before, after in zip([e for e in off_events if e["event"] == "company_size_input"],
                                 [e for e in on_events if e["event"] == "company_size_input"]):
            self.assertEqual(before, {k: v for k, v in after.items() if k in before})
        started = [e for e in on_events if e["event"] == "model_call_started"]
        finished = [e for e in on_events if e["event"] == "model_call_finished"]
        self.assertEqual(len(started), 3)
        self.assertEqual(len(finished), 3)
        self.assertEqual([e["id"] for e in started], [r["id"] for r in on["rows"]])
        self.assertEqual([e["call_kind"] for e in started], ["initial"] * 3)
        self.assertEqual([e["prompt_sha256"] for e in started],
                         [e["prompt_sha256"] for e in
                          (x for x in on_events if x["event"] == "company_size_input")])
        self.assertEqual([e["event"] for e in on_events][:2], ["company_size_input", "company_size_input"])
        self.assertIn("chunk_started", kinds(on_events))
        self.assertIn("chunk_finished", kinds(on_events))

    def test_recorded_schema_is_the_one_the_runner_actually_restricts_to(self):
        """`items` 가 오면 제품은 `sp` 가 아니라 **제한한 스키마**로 부른다
        (`script.py:967`). `sp` 를 적으면 기록이 실제 요청을 증명하지 못한다."""
        class Restricting(FakeRunner):
            def __init__(self):
                super().__init__()
                self.sp = type("SP", (), {})()
                self.sp.max_tokens = 1024
                self.sp.structured_outputs = type("SO", (), {})()
                self.sp.structured_outputs.json = {"properties": {"a": 1, "b": 2}}
                self.used = []

            def parameters_for_items(self, items, *, sme=True):
                restricted = type("SP", (), {})()
                restricted.max_tokens = self.sp.max_tokens
                restricted.structured_outputs = type("SO", (), {})()
                restricted.structured_outputs.json = {"properties": {"a": 1}, "sme": sme}
                self.used.append(items)
                return restricted

        runner = Restricting()
        events = []
        with a5.observe_chat(runner, lambda name, **f: events.append(dict(event=name, **f)),
                             ids=["PPS-DEV-1"], phase="company_size"):
            runner.chat([[{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]],
                        items=a5.script.COMPANY_SIZE_KEYS)
        started = next(e for e in events if e["event"] == "model_call_started")
        full = a5.digest(runner.sp.structured_outputs.json)
        restricted = a5.digest(
            runner.parameters_for_items(a5.script.COMPANY_SIZE_KEYS,
                                        sme=False).structured_outputs.json)
        self.assertNotEqual(full, restricted)            # 두 스키마가 실제로 다르다
        self.assertEqual(started["schema_sha256"], restricted)
        self.assertNotEqual(started["schema_sha256"], full)

    def test_a_runner_without_restriction_falls_back_to_its_own_parameters(self):
        """대역·API 실행기는 `parameters_for_items` 가 없다. 그 경로가 죽으면 안 된다."""
        runner = FakeRunner()
        runner.sp = type("SP", (), {})()
        runner.sp.max_tokens = 512
        runner.sp.structured_outputs = None
        chosen = a5.effective_parameters(runner, None, a5.script.COMPANY_SIZE_KEYS)
        self.assertIs(chosen, runner.sp)
        self.assertIsNone(a5.effective_parameters(FakeRunner(), None, None))

    def test_observe_chat_restores_the_runner_even_when_it_raises(self):
        """감싼 메서드가 남으면 다음 군의 호출이 이전 군 로그로 흘러간다."""
        runner = FakeRunner()
        original = runner.chat
        self.assertNotIn("chat", vars(runner))       # 클래스 메서드다
        with self.assertRaisesRegex(RuntimeError, "boom"):
            with a5.observe_chat(runner, lambda *a, **k: None, ids=["x"], phase="company_size"):
                self.assertIn("chat", vars(runner))  # 인스턴스 속성으로만 감쌌다
                raise RuntimeError("boom")
        self.assertNotIn("chat", vars(runner))
        self.assertEqual(runner.chat.__func__, original.__func__)

    def test_retry_is_recorded_as_its_own_call_with_the_changed_prompt(self):
        """재시도는 system 에 출력범위 문장이 붙고 출력 예산이 줄어든 **다른 요청**이다."""
        events, calls = [], []

        class RetryingRunner(FakeRunner):
            def chat(self, batch, sampling_params=None, items=None):
                calls.append(batch[0][0]["content"])
                text = json.dumps({"company_size": a5.script.empty_company_size()})
                return ["invalid" if len(calls) == 1 else text] * len(batch)

            def retry_chat(self, batch, items=None):
                # 실제 `VLLMRunner.retry_chat` 과 같은 자리에서 system 을 늘리고 self.chat 을 부른다.
                messages = [dict(m) for m in batch[0]]
                messages[0]["content"] += "\n[Output scope for this call] Evaluate only these keys"
                return self.chat([messages], items=items)

        runner = RetryingRunner()
        a5.collect(records("retry", 1), runner, (),
                   lambda event, **fields: events.append(dict(event=event, **fields)), observe=True)
        started = [e for e in events if e["event"] == "model_call_started"]
        self.assertEqual([e["call_kind"] for e in started], ["initial", "retry"])
        self.assertNotEqual(started[0]["prompt_sha256"], started[1]["prompt_sha256"])
        self.assertIn("[Output scope for this call]", started[1]["prompt_text"][0]["content"])
        self.assertNotIn("[Output scope for this call]", started[0]["prompt_text"][0]["content"])
        # 재시도의 공고는 system 을 뺀 본문 digest 로 되짚는다.
        self.assertEqual(started[1]["id"], "retry-0")
        self.assertEqual(started[1]["identity_status"], "matched")
        # 최초 invalid 와 최종 valid 는 기존 `response` 이벤트가 소유한다. 물리 호출 수와 섞지 않는다.
        responses = [e for e in events if e["event"] == "response"]
        self.assertEqual([e["status"] for e in responses], ["invalid", "valid"])
        self.assertEqual(len([e for e in events if e["event"] == "model_call_finished"]), 2)

    def test_notice_id_is_in_the_prompt_so_the_retry_mapping_is_not_a_guess(self):
        """대응의 근거는 `build_user_prompt` 첫 줄의 `[Notice ID]` 다."""
        rec = records("ident", 1)[0]
        self.assertIn("[Notice ID] ident-0", a5.script.build_user_prompt(rec, a5.MAX_CHARS, ()))

    def test_ambiguous_identity_is_recorded_not_guessed(self):
        """그 줄을 잃어 본문이 같아지면 재시도가 어느 공고인지 알 수 없다 — 아무 id 나 붙이지 않는다.

        `collect()` 경로에서는 위 검사대로 본문이 유일하므로, 그 보호가 실제로 도는지
        `observe_chat` 에 같은 본문 둘을 직접 넣어 확인한다.
        """
        events = []
        emit = lambda event, **fields: events.append(dict(event=event, **fields))
        same = [{"role": "system", "content": "S"}, {"role": "user", "content": "같은 본문"}]
        runner = FakeRunner()
        with a5.observe_chat(runner, emit, ids=["A", "B"], phase="company_size"):
            runner.chat([list(same), list(same)], items=a5.script.COMPANY_SIZE_KEYS)
            runner.chat([list(same)], items=a5.script.COMPANY_SIZE_KEYS)   # 재시도 모양
        started = [e for e in events if e["event"] == "model_call_started"]
        self.assertEqual([e["id"] for e in started[:2]], ["A", "B"])        # 첫 호출은 순서로 잇는다
        self.assertEqual(started[2]["identity_status"], "ambiguous")
        self.assertIsNone(started[2]["id"])

    def test_unmatched_retry_body_is_not_attached_to_any_notice(self):
        events = []
        emit = lambda event, **fields: events.append(dict(event=event, **fields))
        runner = FakeRunner()
        with a5.observe_chat(runner, emit, ids=["A"], phase="company_size"):
            runner.chat([[{"role": "user", "content": "첫 본문"}]], items=a5.script.COMPANY_SIZE_KEYS)
            runner.chat([[{"role": "user", "content": "전혀 다른 본문"}]], items=a5.script.COMPANY_SIZE_KEYS)
        started = [e for e in events if e["event"] == "model_call_started"]
        self.assertEqual(started[1]["identity_status"], "unmatched")
        self.assertIsNone(started[1]["id"])

    def test_rate_uses_covered_rows_and_does_not_call_partial_data_complete(self):
        completed = {"dev": {"payload": {"rows": [{"h2_fired": i < 3} for i in range(200)]}},
                     "unlabeled-00": {"payload": {"rows": [{"h2_fired": i < 12} for i in range(1000)]}}}
        result = a5.summarize(completed)
        self.assertAlmostEqual(result["unlabeled_over_dev_rate"], 0.8)
        self.assertFalse(result["complete"])


if __name__ == "__main__":
    unittest.main()
