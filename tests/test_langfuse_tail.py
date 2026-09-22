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


def captured(arm, *, ids=("PPS-DEV-01", "PPS-DEV-02"), chunk_start=0, seq=1, fail=None):
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
        for identifier in ("PPS-DEV-01", "PPS-DEV-02"):
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
        ops, _ = ops_for([ROOT_EVENT] + captured("control", fail="PPS-DEV-02") +
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
        # 루트가 없는 잘린 로그에서 조용히 버려지지 않게 이유를 들고 다닌다.
        self.assertTrue(update.status)
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

    def _real_prompts(self, dev, wanted):
        """제품과 **같은 방식으로** 두 건의 실제 프롬프트를 만든다.
        가짜 본문으로 짠 로그는 결속 검사에서 늘 거부되므로, 거부 검사가
        무엇 때문에 거부됐는지 못 가린다 — 통과하는 바닥이 있어야 한다."""
        import hashlib
        _, products = baseline.load_sme_reference(str(ROOT / "open/data"))
        out = []
        for rec in baseline.iter_records(str(dev)):
            if rec["id"] not in wanted:
                continue
            company = {**rec, "meta": {k: v for k, v in rec.get("meta", {}).items()
                                       if k != "조항호내용"}}
            messages = baseline.build_messages(company, baseline.COMPANY_SIZE_PROMPT, 16000,
                                               products)
            visible = hashlib.sha256(
                baseline.build_context(company, 16000).encode()).hexdigest()
            out.append((rec["id"], messages, visible))
        return out

    def _events(self, tmp, *, notices=("PPS-DEV-01", "PPS-DEV-02"), real=True, **overrides):
        event = dict(event="run_started", time_unix=0.5, mode="pending", capture_protocol=1,
                     dataset="dev", code_sha256="abc1234def")
        event.update(overrides)
        lines = [event]
        if real:
            for index, (identifier, messages, visible) in enumerate(
                    self._real_prompts(ROOT / "open/dev.jsonl", set(notices))):
                lines.append(dict(event="company_size_input", time_unix=1.0 + index, arm="control",
                                  sample="dev", id=identifier, max_chars=16000,
                                  visible_sha256=visible))
                lines.append(dict(event="model_call_started", time_unix=1.5 + index, arm="control",
                                  sample="dev", id=identifier, identity_status="initial",
                                  call_seq=1, call_index=index, prompt_text=messages))
        else:
            lines += captured("control", ids=tuple(notices))
        lines.append(dict(event="run_succeeded", time_unix=9.0))
        path = Path(tmp) / "diagnostics.jsonl"
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

    def test_failure_details_do_not_leak_in_metadata_only_mode(self):
        """`run_failed` 에는 예외 메시지와 traceback 이 있고 거기에 개인 절대경로가 들어간다.
        본문 차단이 두 슬롯만 보면 그것이 임의 host 로 나간다(라운드 2 P0)."""
        secret = "C:/Users/dasdk/private/.env"
        events = [dict(event="run_started", time_unix=0.5, mode="pending", capture_protocol=1,
                       code_sha256="abc1234def"),
                  dict(event="run_failed", time_unix=2.0, error_type="ValueError", count=3,
                       error_message=f"{secret} 를 못 읽었다",
                       traceback=f'File "{secret}", line 3\n  boom')]
        ops, _ = ops_for(events, include_prompts=False)
        end = next(o for o in ops if o.key == "run" and o.action == "close")
        blob = json.dumps(end.attrs, ensure_ascii=False) + end.status
        self.assertNotIn(secret, blob)
        self.assertNotIn("못 읽었다", blob)
        self.assertEqual(end.status, "ValueError")            # 클래스 이름은 남는다
        self.assertEqual(json.loads(end.attrs["langfuse.observation.output"]),
                         {"count": 3, "error_type": "ValueError"})
        self.assertEqual(end.attrs["langfuse.observation.metadata.detail_capture"], "withheld")
        # 수출이 허용된 자리에서는 그대로 남는다 — 진단을 못 하게 만들지 않는다.
        allowed, _ = ops_for(events)
        end = next(o for o in allowed if o.key == "run" and o.action == "close")
        self.assertIn(secret, end.attrs["langfuse.observation.metadata.traceback"])
        self.assertIn(secret, end.status)

    def test_other_error_paths_also_withhold_the_message(self):
        """실패 경로의 `error_type` 도 **생산자 집합과 대조**한다 — 원본을 status 로 쓰면
        `SecretTokenABC123` 이 그대로 나갔다(라운드 8 P0). 실제 회차 로그에는 실패
        이벤트가 없어 오염 스윕이 이 경로를 못 덮는다."""
        notice = "PPS-DEV-01"
        for kind, leaks in (("ValueError", False), ("SecretTokenABC123", True)):
            events = [ROOT_EVENT,
                      dict(event="arm_started", time_unix=1.0, arm="control", sample="dev"),
                      dict(event="response", time_unix=2.0, arm="control", sample="dev",
                           id=notice, attempt=1, status="invalid", global_index=0,
                           error_type=kind, error_message="C:/Users/dasdk/private/x 실패"),
                      dict(event="retry_failed", time_unix=2.5, arm="control", sample="dev",
                           id=notice, error_type=kind,
                           error_message="C:/Users/dasdk/private/x 실패"),
                      dict(event="model_call_started", time_unix=2.6, arm="control",
                           sample="dev", id=notice, call_seq=1, call_index=0),
                      dict(event="model_call_failed", time_unix=2.7, arm="control",
                           sample="dev", id=notice, call_seq=1, call_index=0,
                           error_type=kind, transport_status="failed"),
                      dict(event="run_failed", time_unix=9.0, error_type=kind,
                           error_message="C:/Users/dasdk/private/x 실패")]
            ops, _ = ops_for(events, include_prompts=False)
            blob = json.dumps([[o.attrs, o.status] for o in ops], ensure_ascii=False)
            self.assertNotIn("C:/Users/dasdk/private", blob, kind)
            if leaks:
                self.assertNotIn("Secret", blob, "예외 클래스 이름도 생산자 집합과 대조한다")
            else:
                self.assertIn("ValueError", blob)   # 진짜 클래스 이름은 남는다

    def test_the_exporter_cannot_follow_a_redirect_off_the_pinned_host(self):
        """주소 문자열만 막으면 부족하다. requests 는 기본적으로 redirect 를 따라가므로
        로컬 엔드포인트가 307 로 외부를 가리키면 본문이 다시 밖으로 나간다(라운드 2 P0)."""
        class Session:
            def __init__(self):
                self.seen = []

            def request(self, method, url, **kwargs):
                self.seen.append((method, url, kwargs.get("allow_redirects"),
                                  kwargs.get("proxies")))
                return "ok"

            def post(self, url, **kwargs):
                kwargs.setdefault("allow_redirects", True)   # requests 의 기본값
                return self.request("POST", url, **kwargs)

        class Exporter:
            def __init__(self):
                self._session = Session()

        exporter = Exporter()
        exporter._session.trust_env = True
        tail.pin_to_host(exporter, "http://localhost:3002")
        exporter._session.post("http://localhost:3002/api/public/otel/v1/traces", data=b"x")
        self.assertEqual(exporter._session.seen[-1][2], False)
        # 환경 프록시를 안 본다 — trust_env 가 참이면 HTTP_PROXY 가 로컬 주소도 가로챈다.
        self.assertFalse(exporter._session.trust_env)
        self.assertEqual(exporter._session.proxies, {})
        self.assertEqual(exporter._session.seen[-1][3], {})
        for bad in ("https://evil.example.com/v1/traces",
                    "http://localhost:3002@evil.example/x",     # startswith 를 통과한다
                    "http://localhost:3003/x", "https://localhost:3002/x"):
            with self.assertRaisesRegex(RuntimeError, "허용된 호스트 밖", msg=bad):
                exporter._session.post(bad, data=b"x")
        # 세션을 못 잡으면 조용히 넘어가지 않는다 — 막았다고 믿는 것이 더 나쁘다.
        with self.assertRaisesRegex(RuntimeError, "redirect"):
            tail.pin_to_host(object(), "http://localhost:3002")

    def test_the_default_session_name_carries_no_absolute_path(self):
        """`--session` 을 생략하면 기본값이 span 에 실린다. 개인 절대경로가 나갔다(라운드 3 P0)."""
        inside = tail._session_name(ROOT / "output/diagnostics.jsonl")
        self.assertEqual(inside, "output/diagnostics.jsonl")
        with tempfile.TemporaryDirectory() as tmp:
            outside = tail._session_name(Path(tmp) / "diagnostics.jsonl")
        self.assertNotIn(tmp.replace("\\", "/"), outside.replace("\\", "/"))
        self.assertTrue(outside.startswith("diagnostics.jsonl:"))
        # 같은 파일이면 같은 이름이라 trace 가 이어진다.
        self.assertEqual(inside, tail._session_name(ROOT / "output/diagnostics.jsonl"))

    def test_the_run_actually_sends_that_name_not_the_resolved_path(self):
        """함수가 있는 것과 `run()` 이 그것을 쓰는 것은 다르다. 실제로 실린 값을 본다."""
        import argparse
        import unittest.mock as mock

        sent = []

        class Span:
            def set_attribute(self, key, value):
                sent.append((key, value))

            def update_name(self, name):
                pass

            def end(self, end_time=None):
                pass

        class Tracer:
            def start_span(self, name, context=None, start_time=None):
                return Span()

        class Provider:
            def get_tracer(self, name):
                return Tracer()

            def shutdown(self):
                pass

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "diagnostics.jsonl"
            path.write_text(json.dumps(ROOT_EVENT, ensure_ascii=False) + "\n" +
                            json.dumps({"event": "run_succeeded", "time_unix": 9.0}) + "\n",
                            encoding="utf-8", newline="\n")
            args = argparse.Namespace(diagnostics=str(path), follow=False, from_line=0,
                                      idle_timeout=1.0, environment="test", session="",
                                      service="t", dev_input="", include_prompts=False)
            with mock.patch.dict("os.environ", {"LANGFUSE_HOST": "http://localhost:3002",
                                                "LANGFUSE_PUBLIC_KEY": "pk",
                                                "LANGFUSE_SECRET_KEY": "sk"}), \
                    mock.patch.object(tail, "build_provider", return_value=Provider()):
                self.assertEqual(tail.run(args), 0)
            names = [value for key, value in sent if key == "langfuse.session.id"]
        self.assertTrue(names)
        for name in names:
            self.assertNotIn(tmp.replace("\\", "/"), str(name).replace("\\", "/"))
            self.assertTrue(str(name).startswith("diagnostics.jsonl:"), name)

    def test_a_call_without_a_prompt_and_an_unpaired_output_are_refused(self):
        """본문 검증이 `prompt_text` 가 있을 때만 돌면, 같은 호출의 응답만 위조해도
        통과한다 — 검증을 건너뛴 시작에 붙은 output 이 그대로 나갔다(라운드 4 P0)."""
        dev, ids = self._dev_ids()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._events(tmp, notices=ids[:2], dataset_sha256=tail._sha256(dev),
                                dev_ids=ids)
            lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            out = []
            for line in lines:
                if line["event"] == "model_call_started":
                    line.pop("prompt_text")              # 본문 없는 시작
                    out.append(line)
                    out.append(dict(line, event="model_call_finished",
                                    response_text="NON_DEV_SECRET"))
                    continue
                out.append(line)
            path.write_text("".join(json.dumps(line, ensure_ascii=False) + "\n" for line in out),
                            encoding="utf-8", newline="\n")
            verdict = tail.validate_dev_export(path, dev, host="http://localhost:3002")
        self.assertFalse(verdict["allowed"])
        self.assertIn("unbound_body:call_without_prompt,unpaired_output", verdict["reasons"])
        self.assertEqual(verdict["bound_prompts"], 0)

    def test_structured_fields_cannot_carry_free_text(self):
        """"구조화 필드라서 안전하다" 는 근거가 아니다. `settings.note`·`items`·`argv` 로
        임의 문자열과 개인 경로가 실렸다(라운드 4 P0). 두 모드 모두에서 본다."""
        secret = "NON_DEV_SECRET"
        path = "C:/Users/dasdk/private"
        probes = [
            dict(event="run_started", time_unix=0.5, mode="pending", capture_protocol=1,
                 code_sha256="abc1234", settings={"chunk": 128, "note": secret},
                 argv=["python", f"{path}/x.py"],
                 environment={"vllm": "0.26.0", "leak": secret},
                 expected_model={"id": "m", "note": secret}),
            dict(event="assets", time_unix=0.6, packages=["vllm==0.26.0", secret],
                 sha256="a" * 64),
            dict(event="arm_started", time_unix=1.0, arm="control", sample="dev",
                 system_prompt_sha256=secret),
            dict(event="company_size_input", time_unix=1.1, arm="control", sample="dev",
                 id="PPS-DEV-01", max_chars=secret, visible_sha256="b" * 64),
            dict(event="model_call_started", time_unix=1.5, arm="control", sample="dev",
                 id="PPS-DEV-01", call_seq=1, call_index=0,
                 items=["company_size", secret], groups=[[secret]], schema_sha256="c" * 64),
            dict(event="model_call_finished", time_unix=2.0, arm="control", sample="dev",
                 id="PPS-DEV-01", call_seq=1, call_index=0, finish_reason=secret,
                 transport_status="returned"),
            dict(event="response", time_unix=2.1, arm="control", sample="dev", id="PPS-DEV-01",
                 attempt=1, status="valid", global_index=0, retry_strategy=secret),
            dict(event="retry_failed", time_unix=2.2, arm="control", sample="dev",
                 id="PPS-DEV-01", stage=secret, source=secret),
            dict(event="sme_verified", time_unix=2.5, id="PPS-DEV-01",
                 flags={"v13": 1, "leak": secret},
                 rejected_conditions={"v13": ["unverified_product", secret]}),
            dict(event="run_failed", time_unix=9.0, count=200, stage=secret,
                 error_message=f"{path}/x", traceback=f"File {path}/x"),
        ]
        for include in (False, True):
            state, ops = tail.State(include_prompts=include), []
            for event in probes:
                ops += tail.plan(event, state)
            blob = json.dumps([[op.attrs, op.status] for op in ops], ensure_ascii=False)
            self.assertNotIn(secret, blob, f"include_prompts={include}")
            if not include:
                self.assertNotIn(path, blob)
    def test_the_sanitiser_does_not_empty_a_captured_run(self):
        """`capture_protocol=1` 판형의 보존 검사. **형태는 mock 회차가 실제로 내는 것**과
        같아야 한다 — 손으로 쓴 `packages` 목록이 실제로는 dict 라서 회귀를 못 잡았다
        (라운드 5 P1). 그래서 legacy 판형의 보존은 실제 H4 로그 검사가 소유하고,
        여기는 새 판형의 군·호출 필드만 본다."""
        clean = [
            dict(event="run_started", time_unix=0.5, mode="pending", capture_protocol=1,
                 code_sha256="abc1234", settings={"chunk": 128, "max_chars": 16000},
                 expected_model={"id": "google/gemma-4-26B-A4B-it"}),
            dict(event="assets", time_unix=0.6,
                 packages={"vllm": "0.26.0", "torch": "2.11.0+cu130"}, sha256={"input": "a" * 64}),
            dict(event="model_loading", time_unix=0.7),
            dict(event="model_loaded", time_unix=0.9, mode="live", load_seconds=12.0,
                 token_count_kind="actual", environment={"vllm": "0.26.0", "cuda": "13.0"}),
            dict(event="arm_started", time_unix=1.0, arm="control", sample="dev",
                 selected_count=200, system_prompt_sha256="d" * 64),
            dict(event="company_size_input", time_unix=1.1, arm="control", sample="dev",
                 id="PPS-DEV-01", max_chars=16000, truncated=False, prompt_tokens=9000,
                 token_count_kind="actual", visible_sha256="b" * 64),
            dict(event="model_call_started", time_unix=1.5, arm="control", sample="dev",
                 id="PPS-DEV-01", identity_status="initial", call_kind="initial",
                 call_seq=1, call_index=0, items=["company_size"], max_tokens=1024,
                 schema_sha256="c" * 64),
            dict(event="model_call_finished", time_unix=2.0, arm="control", sample="dev",
                 id="PPS-DEV-01", identity_status="initial", call_seq=1, call_index=0,
                 transport_status="returned", finish_reason="stop", prompt_tokens=9000,
                 output_tokens=400),
            dict(event="sme_verified", time_unix=2.5, id="PPS-DEV-01", flags={"v13": 1},
                 rejected_conditions={"v13": ["unverified_product"]}),
            dict(event="run_succeeded", time_unix=9.0, count=200, seconds=300.0,
                 model_success_count=200),
        ]
        state, ops = tail.State(), []
        for event in clean:
            ops += tail.plan(event, state)
        kept = json.dumps([op.attrs for op in ops], ensure_ascii=False)
        for good in ("PPS-DEV-01", "company_size", "unverified_product",
                     "returned", "stop", "16000", "0.26.0", "2.11.0+cu130"):
            self.assertIn(good, kept, good)
        self.assertEqual(state.trace_name, "nara live abc1234")
        self.assertIn("\\\"chunk\\\": 128", kept)

    def test_the_real_h4_run_projects_without_loss_or_crash(self):
        """**손으로 쓴 이벤트로는 이 결함군이 안 보인다.** 실제 회차 로그로 셋을 같이 본다 —
        크래시 없음 · 진짜 값 보존 · 오염 차단. 합성 검사가 초록인 채로 위생이 생산자의
        값을 다수 지우고 dict 목록에서 크래시했다(라운드 5 P1·P0)."""
        log = ROOT / "reports/runs/colab-1789902969401579900/dev-debug/diagnostics.jsonl"
        events = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
        self.assertGreater(len(events), 1000, "실제 회차 로그가 있어야 이 검사가 의미 있다")

        state, ops = tail.State(), []
        for event in events:                       # 크래시하면 여기서 터진다
            ops += tail.plan(event, state)
        self.assertGreater(len(ops), 600)
        opened = {op.key for op in ops if op.action == "open"}
        self.assertEqual(opened, {op.key for op in ops if op.action == "close"})

        # 진짜 값이 남는다. 지워지면 관측이 비어 쓸 수 없다.
        kept = json.dumps([[op.attrs, op.name] for op in ops], ensure_ascii=False)
        for good in ("0.26.0", "3.12.13", "13.0", "google/gemma-4-26B-A4B-it", "16384",
                     "nara live", "int8_per_channel_weight_only", "unverified_product"):
            self.assertIn(good, kept, good)
        # 장비명처럼 알려진 값 집합이 없는 문자열은 **요약으로** 나간다 — 평문이 아니다.
        # 어느 GPU 였는지는 `total_memory` 숫자가 들고 있다.
        self.assertNotIn("NVIDIA A100-SXM4-40GB", kept)
        self.assertIn("sha256:", kept)
        self.assertIn("42405855232", kept)
        self.assertEqual(state.trace_name[:10], "nara live ")
        self.assertIn("chat_template_sha256", kept)
        # 긴 자유 문자열은 본문 대신 hash 로 남는다.
        self.assertIn("sampling_params", kept)
        self.assertNotIn("SamplingParams(n=1", kept)

    def test_poisoning_the_real_log_leaks_nothing_in_either_mode(self):
        """오염도 실제 로그에 심는다. 합성 이벤트는 생산자가 쓰는 자리를 다 덮지 못한다.

        본문·경로뿐 아니라 **토큰형 비밀**도 심는다. 라운드 6 까지는 "짧은 토큰은
        1층이 막는다" 로 스윕을 좁혔는데 그것이 라운드 6·7·8 의 P0 였다 —
        1층이 안 도는 모드가 있고, 모양은 값의 출처를 증명하지 못한다.
        이제 2층이 알려진 값이 아닌 문자열을 전부 요약하므로 스윕도 토큰을 덮는다.
        """
        body = "제3조(중소기업자간 경쟁제품) 이 문장은 공고 본문이다 " * 4
        path = "C:/Users/dasdk/private/secret.env"
        token = "sk-live-secret123"
        log = ROOT / "reports/runs/colab-1789902969401579900/dev-debug/diagnostics.jsonl"
        events = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]

        def poison(value, pick):
            if isinstance(value, str):
                return body if len(value) > 40 else pick
            if isinstance(value, dict):
                return {**{k: poison(v, pick) for k, v in value.items()}, "leaked": pick}
            if isinstance(value, list):
                return [poison(v, pick) for v in value] + [pick]
            return value

        for pick, needle in ((path, "dasdk"), (token, "secret")):
            dirty = []
            for event in events:
                copy = dict(event)
                for key, value in event.items():
                    if key not in ("event", "time_unix"):
                        copy[key] = poison(value, pick)
                dirty.append(copy)
            for include in (False, True):
                state, ops = tail.State(include_prompts=include), []
                for event in dirty:
                    ops += tail.plan(event, state)
                if include:                # 본문 슬롯은 허용 상태에서 나갈 수 있다
                    for op in ops:
                        for slot in ("input", "output"):
                            op.attrs.pop(f"langfuse.observation.{slot}", None)
                blob = json.dumps([[op.attrs, op.name, op.status, op.key] for op in ops],
                                  ensure_ascii=False)
                where = f"{needle}/include_prompts={include}"
                self.assertNotIn(body[:30], blob, where)
                self.assertNotIn(needle, blob.lower(), where)

    def test_an_orphan_close_does_not_carry_its_raw_call_key(self):
        """`_fixed()` 는 이 파일이 만든 문구 전용이다. 이벤트에서 조립한 key 를 거기 넣어
        `guard()` 가 op.key 만 바꾸는 사이 metadata 로 경로가 나갔다(라운드 6 P0)."""
        path = "C:/Users/dasdk/private/secret.env"
        state = tail.State()
        tail.plan(dict(event="run_started", time_unix=0.5, mode="pending", capture_protocol=1,
                       code_sha256="abc1234def"), state)
        ops = tail.plan(dict(event="model_call_finished", time_unix=2.0, phase=path,
                             call_seq=1, call_index=0, transport_status="returned"), state)
        self.assertTrue(ops)
        blob = json.dumps([[op.attrs, op.name, op.key, op.status] for op in ops],
                          ensure_ascii=False)
        self.assertNotIn("dasdk", blob)
        # 그래도 orphan 이라는 사실과 어느 호출인지의 동일성은 남는다.
        self.assertIn("sha256:", blob)
        self.assertEqual([op.level for op in ops], ["ERROR"])

    def test_the_mode_from_model_loaded_cannot_poison_the_trace_name(self):
        """`run_started` 쪽만 위생하고 `model_loaded` 를 잊었다 — trace 이름이 오염됐고
        `run()` 이 그것을 직접 set_attribute 했다(라운드 6 P0). 출구가 하나여야 한다."""
        path = "C:/Users/dasdk/private/secret.env"
        events = [dict(event="run_started", time_unix=0.5, mode="pending", capture_protocol=1,
                       code_sha256="abc1234def"),
                  dict(event="model_loading", time_unix=0.6),
                  dict(event="model_loaded", time_unix=0.9, mode=path, load_seconds=1.0),
                  dict(event="run_succeeded", time_unix=3.0, count=1)]
        state, ops = tail.State(), []
        for event in events:
            ops += tail.plan(event, state)
        blob = json.dumps([[op.attrs, op.name, op.status] for op in ops], ensure_ascii=False)
        self.assertNotIn("dasdk", blob)
        self.assertNotIn("dasdk", state.trace_name)
        self.assertNotIn("dasdk", str(state.actual_mode))
        self.assertTrue(state.trace_name.startswith("nara sha256:"))
        # `run()` 이 span 에 직접 쓰는 trace 이름도 같은 통로를 지난다.
        self.assertNotIn("dasdk", tail._label("trace_name", "nara " + path + " abc"))

    def test_guard_is_the_last_line_even_if_a_branch_forgets(self):
        """출구가 하나라는 것은 **어느 분기가 잊어도 막힌다**는 뜻이다. 그것을 직접 건다 —
        위의 mode 위생이 이미 막고 있어 이 줄은 단독으로는 검사되지 않는다."""
        path = "C:/Users/dasdk/private/secret.env"
        dirty = tail.Op("update", "run", "nara " + path,
                        attrs={"langfuse.trace.name": "nara " + path,
                               "langfuse.observation.usage_details":
                                   json.dumps({"input": "x", "output": "y", "total": "xy"})},
                        status=path)
        clean = tail.guard(dirty)
        blob = json.dumps([clean.attrs, clean.name, clean.status, clean.key], ensure_ascii=False)
        self.assertNotIn("dasdk", blob)
        # 타입이 틀린 usage 는 걷어낸다 — 숫자가 아닌 토큰 수는 관측이 아니다.
        self.assertNotIn("langfuse.observation.usage_details", clean.attrs)

    def test_a_tampered_log_never_reaches_the_projection(self):
        """짧은 토큰 위조는 **1층**이 막는다 — 값만 보고 버전과 비밀을 가를 수 없으므로
        그 로그는 수출 자체가 거부돼야 한다."""
        dev, ids = self._dev_ids()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._events(tmp, notices=ids[:2], dataset_sha256=tail._sha256(dev),
                                dev_ids=ids)
            lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            for line in lines:
                if line["event"] == "run_started":
                    line["settings"] = {"chunk": 128, "quant": "NON_DEV_SECRET"}
            path.write_text("".join(json.dumps(line, ensure_ascii=False) + "\n" for line in lines),
                            encoding="utf-8", newline="\n")
            # 계약이 멀쩡하면 1층은 통과한다. **그래도 그 값은 평문으로 안 나간다** —
            # 2층이 알려진 값이 아닌 문자열을 요약한다(라운드 6 P0 의 수리).
            good = tail.validate_dev_export(path, dev, host="http://localhost:3002")
            self.assertTrue(good["allowed"], good["reasons"])
            state, ops = tail.State(), []
            for line in path.read_text(encoding="utf-8").splitlines():
                ops += tail.plan(json.loads(line), state)
            blob = json.dumps([op.attrs for op in ops], ensure_ascii=False)
            self.assertNotIn("NON_DEV_SECRET", blob)
            # 본문·경로를 건드리면 1층이 거부한다.
            for line in lines:
                if line["event"] == "model_call_started":
                    line["prompt_text"][-1]["content"] += "\n숨긴 평가자료"
            path.write_text("".join(json.dumps(line, ensure_ascii=False) + "\n" for line in lines),
                            encoding="utf-8", newline="\n")
            verdict = tail.validate_dev_export(path, dev, host="http://localhost:3002")
        self.assertFalse(verdict["allowed"])
        self.assertIn("unbound_body:prompt_body_mismatch", verdict["reasons"])

    def test_the_sanitiser_keeps_what_the_producer_makes(self):
        self.assertEqual(tail._clean("max_chars", 16000), 16000)
        self.assertIsNone(tail._clean("max_chars", "16000"))          # 수치 자리에 문자열
        self.assertIsNone(tail._clean("visible_sha256", "not-a-hash"))
        self.assertEqual(tail._clean("visible_sha256", "b" * 64), "b" * 64)
        self.assertEqual(tail._clean("identity_status", "matched"), "matched")
        self.assertEqual(tail._clean("items", ["v13"]), ["v13"])
        self.assertIsNone(tail._clean("nobody_knows_this", "x"))      # 모르는 이름은 버린다
        self.assertFalse(tail.TOKEN.match("C:/Users/dasdk/x"))        # 경로는 토큰이 아니다
        # **알려진 값이 아닌 문자열은 평문으로 안 나간다.** 값만 보고 버전과 비밀을
        # 구분할 수 없으므로, 구분 못 하는 쪽을 평문으로 보내지 않는다(라운드 6 P0).
        for name, value in (("identity_status", "made_up"), ("items", ["not_an_item"]),
                            ("quant", "sk-live-secret123"), ("vllm", "sk-live-secret123"),
                            ("name", "sk-live-secret123"), ("stage", "sk-live-secret123"),
                            ("status", "sk-live-secret123")):
                clean = tail._clean(name, value)
                self.assertNotIn("secret", json.dumps(clean, ensure_ascii=False), name)
                self.assertNotIn("made_up", json.dumps(clean, ensure_ascii=False), name)
                self.assertNotIn("not_an_item", json.dumps(clean, ensure_ascii=False), name)
        # 버전은 **계약이 고정한 값**과 같을 때만 평문이다. 모양으로 두면
        # `123.456.789.012` 같은 고엔트로피 숫자가 통과한다(라운드 8 P0).
        pinned = tail._pinned_versions()
        self.assertIn("0.26.0", pinned)
        self.assertEqual(tail._clean("vllm", "0.26.0"), "0.26.0")
        self.assertEqual(tail._clean("python", "3.12.13"), "3.12.13")
        self.assertEqual(tail._clean("torch", "2.11.0+cu130"), "2.11.0+cu130")
        for bad in ("sk-live-1", "123.456.789.012", "0.99.0", "1234567890123"):
            self.assertTrue(str(tail._clean("vllm", bad)).startswith("sha256:"), bad)
        # 분할 재시도의 `split` 은 생산자가 내는 핵심 관측값이다(라운드 6 P1).
        self.assertEqual(tail._clean("groups", [{"items": ["v1"], "status": "split",
                                                 "stage": "parse"}]),
                         [{"items": ["v1"], "status": "split", "stage": "parse"}])
        # 중첩 list·dict 에서 크래시하지 않는다 — 게이트는 fail-closed 여야 한다.
        self.assertIsNone(tail._clean("rejected_conditions", {"v13": [[1]]}))
        self.assertIsNone(tail._clean("items", [[{"x": 1}]]))
        # 중첩이라도 값이 항목명뿐이면 크래시 없이 그대로 둔다.
        self.assertEqual(tail._clean("groups", [{"items": [["v1"]]}]), [{"items": [["v1"]]}])

    def test_map_keys_are_checked_not_just_values(self):
        """`sha256`·`packages` map 은 값만 검사해 **키에 개인 경로가 남았다**(라운드 7 P0).
        오염 스윕이 기존 키를 바꾸지 않아 이 경로를 덮지 못했다."""
        # POSIX·UNC 절대경로와 토큰형 비밀도 **키 자리**에서 막혀야 한다(라운드 8 P0).
        for path in ("C:/Users/dasdk/private/secret.env", "/home/dasdk/private/secret.env",
                     "//host/share/secret.env", "sk-live-secret123"):
            for name, inner in (("sha256", "a" * 64), ("packages", "0.26.0")):
                blob = json.dumps(tail._clean(name, {path: inner}), ensure_ascii=False)
                self.assertNotIn("dasdk", blob, f"{name}:{path}")
                self.assertNotIn("secret", blob.lower(), f"{name}:{path}")
        # 진짜 키는 그대로다 — `script.py` 가 만드는 닫힌 집합이다.
        assets = tail._known_assets()
        self.assertEqual(len(assets), 6)
        for key in assets:
            self.assertEqual(tail._clean("sha256", {key: "a" * 64}), {key: "a" * 64})
        self.assertEqual(tail._clean("packages", {"vllm": "0.26.0"}), {"vllm": "0.26.0"})
        self.assertIn("vllm", tail._known_packages())

    def test_scope_and_class_names_are_matched_against_the_producer(self):
        """모양이 값을 증명한다고 볼 수 있는 것은 hash 뿐이다. `phase`·`error_type` 을
        패턴으로 두어 토큰형 비밀이 평문으로 나갔다(라운드 7 P0)."""
        for name in ("phase", "arm", "sample", "error_type", "experiment"):
            clean = tail._clean(name, "sk-live-secret123")
            self.assertTrue(str(clean).startswith("sha256:"), f"{name}={clean}")
        self.assertTrue(str(tail._clean("error_type", "SecretTokenABC123")).startswith("sha256:"))
        # 생산자 값은 평문이다 — 대조가 관측을 비우면 쓸 수 없다.
        produced = tail._producer_enums()
        self.assertIn("company_size", produced["phase"])
        self.assertIn("split", produced["phase"])
        self.assertIn("ValueError", produced["error_type"])
        self.assertIn("control", produced["arm"])
        for name, value in (("phase", "company_size"), ("arm", "control"), ("sample", "dev"),
                            ("error_type", "ValueError"), ("experiment", "a8")):
            self.assertEqual(tail._clean(name, value), value)

    def test_the_notice_id_comes_from_the_input_files_not_the_log(self):
        """회차가 **스스로 선언한** `dev_ids` 는 근거가 아니다 — 1층이 안 도는 모드에서
        공격자가 자기 allowlist 를 만든다(라운드 8 P0). 모양도 근거가 아니다.
        저장소의 dev 와 제출 입력을 **둘 다** 읽어 대조한다 — dev 만 보면 제출 입력으로
        돈 회차(H4)의 관측이 통째로 요약된다."""
        forged = [dict(event="run_started", time_unix=0.5, mode="pending", capture_protocol=1,
                       code_sha256="abc1234", dev_ids=["sk-live-secret123"]),
                  dict(event="arm_started", time_unix=1.0, arm="control", sample="dev"),
                  dict(event="company_size_input", time_unix=1.1, arm="control", sample="dev",
                       id="sk-live-secret123", max_chars=16000),
                  dict(event="company_size_input", time_unix=1.2, arm="control", sample="dev",
                       id="PPS-sk-live-secret123", max_chars=16000)]
        state, ops = tail.State(), []
        for event in forged:
            ops += tail.plan(event, state)
        blob = json.dumps([[op.attrs, op.name, op.key] for op in ops], ensure_ascii=False)
        self.assertNotIn("secret", blob.lower())
        # 두 입력 파일의 id 는 평문이다 — dev 와 제출용을 둘 다 읽는다.
        known = tail._known_notices()
        self.assertIn("PPS-DEV-01", known)
        self.assertGreater(len(known), 200)
        for identifier in ("PPS-DEV-01", sorted(known)[0]):
            self.assertEqual(tail._clean("id", identifier), identifier)

    def test_the_status_enum_matches_what_the_producer_writes(self):
        """손으로 적은 집합은 드리프트한다 — `split` 을 빼서 분할 재시도 관측이 사라졌다.
        생산자 소스를 훑어 새 값이 생기면 이 검사가 먼저 깨진다."""
        import re as _re
        sources = [ROOT / "script.py"] + sorted((ROOT / "experiments").glob("*.py"))
        found = set()
        for source in sources:
            text = source.read_text(encoding="utf-8")
            found |= set(_re.findall(r'"status"\]\s*=\s*"([a-z_]+)"', text))
            found |= set(_re.findall(r'"status":\s*"([a-z_]+)"', text))
            found |= set(_re.findall(r'status=["\']([a-z_]+)["\']', text))
        self.assertIn("split", found, "생산자에서 status 값을 못 읽었다")
        missing = found - tail._ENUMS["status"]
        self.assertEqual(missing, set(), f"_ENUMS['status'] 에 없는 생산자 값: {missing}")

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
        """실제 프롬프트로 짠 고정 dev 회차는 통과한다 — 대조가 회차를 막으면 쓸 수 없다."""
        dev, ids = self._dev_ids()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._events(tmp, notices=ids[:2], dataset_sha256=tail._sha256(dev),
                                dev_ids=ids)
            verdict = tail.validate_dev_export(path, dev, host="http://localhost:3002")
        self.assertTrue(verdict["allowed"], verdict["reasons"])
        self.assertEqual(verdict["dev_records"], len(ids))
        self.assertEqual(verdict["observed_records"], 2)
        self.assertEqual(verdict["bound_prompts"], 2)

    def test_a_notice_outside_the_pinned_dev_is_refused(self):
        """고정 dev 로 이름만 붙이고 다른 공고를 돌린 로그. 접두사만 보면 통과한다."""
        dev, ids = self._dev_ids()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._events(tmp, notices=(ids[0], "PPS-DEV-9999"), real=False,
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

    def test_a_valid_id_with_a_body_that_did_not_come_from_dev_is_refused(self):
        """id 가 고정 dev 에 있다는 것은 **본문이 dev 에서 왔다는 근거가 아니다.**
        유효한 id 에 임의 문자열을 붙인 로그가 그 검사만으로는 통과한다(라운드 2 P0)."""
        dev, ids = self._dev_ids()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._events(tmp, notices=ids[:2], dataset_sha256=tail._sha256(dev),
                                dev_ids=ids)
            lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            for line in lines:
                if line["event"] == "model_call_started":
                    line["prompt_text"] = [{"role": "system", "content": "SYS"},
                                           {"role": "user", "content": "NON_DEV_SECRET"}]
            path.write_text("".join(json.dumps(line, ensure_ascii=False) + "\n" for line in lines),
                            encoding="utf-8", newline="\n")
            verdict = tail.validate_dev_export(path, dev, host="http://localhost:3002")
        self.assertFalse(verdict["allowed"])
        self.assertTrue(any(r.startswith("unbound_body:") for r in verdict["reasons"]),
                        verdict["reasons"])

    def test_a_message_smuggled_between_system_and_user_is_refused(self):
        """첫 메시지가 system·끝이 user 인 것만 보면 그 사이에 끼운 것이 통과하고,
        배열 **전체**가 span input 으로 나간다(라운드 3 P0)."""
        dev, ids = self._dev_ids()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._events(tmp, notices=ids[:2], dataset_sha256=tail._sha256(dev),
                                dev_ids=ids)
            lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            for line in lines:
                if line["event"] == "model_call_started":
                    line["prompt_text"].insert(1, {"role": "assistant",
                                                   "content": "NON_DEV_SECRET"})
            path.write_text("".join(json.dumps(line, ensure_ascii=False) + "\n" for line in lines),
                            encoding="utf-8", newline="\n")
            verdict = tail.validate_dev_export(path, dev, host="http://localhost:3002")
        self.assertFalse(verdict["allowed"])
        self.assertIn("unbound_body:prompt_shape", verdict["reasons"])

    def test_an_extra_field_on_a_message_is_refused(self):
        dev, ids = self._dev_ids()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._events(tmp, notices=ids[:2], dataset_sha256=tail._sha256(dev),
                                dev_ids=ids)
            lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            for line in lines:
                if line["event"] == "model_call_started":
                    line["prompt_text"][-1]["note"] = "NON_DEV_SECRET"
            path.write_text("".join(json.dumps(line, ensure_ascii=False) + "\n" for line in lines),
                            encoding="utf-8", newline="\n")
            verdict = tail.validate_dev_export(path, dev, host="http://localhost:3002")
        self.assertFalse(verdict["allowed"])
        self.assertIn("unbound_body:prompt_shape", verdict["reasons"])

    def test_the_retry_suffix_key_list_is_not_a_free_string(self):
        """접미사를 정규식으로 열어 두면 key 목록 자리에 임의 문자열이 들어간다(라운드 3 P0)."""
        dev, ids = self._dev_ids()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._events(tmp, notices=ids[:2], dataset_sha256=tail._sha256(dev),
                                dev_ids=ids)
            lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            for line in lines:
                if line["event"] == "model_call_started":
                    line["prompt_text"][0]["content"] += (
                        "\n[Output scope for this call] Evaluate only these keys, overriding "
                        "the earlier key list: NON_DEV_SECRET. Return no other keys. "
                        "Keep evidence quotations under 100 characters.")
            path.write_text("".join(json.dumps(line, ensure_ascii=False) + "\n" for line in lines),
                            encoding="utf-8", newline="\n")
            verdict = tail.validate_dev_export(path, dev, host="http://localhost:3002")
        self.assertFalse(verdict["allowed"])
        self.assertIn("unbound_body:unknown_system_tail", verdict["reasons"])

    def test_the_candidate_system_is_matched_by_its_longest_prefix(self):
        """후보 system 은 제품 프롬프트로도 시작한다. 짧은 쪽을 고르면 블록 전체가
        모르는 꼬리가 되어 **진짜 A8 회차가 거부된다** — set 순서에 맡기면 seed 마다 갈린다."""
        systems = tail._known_systems(ROOT / "open/data")
        self.assertEqual(len(systems), 2)
        candidate = max(systems, key=len)
        self.assertTrue(candidate.startswith(min(systems, key=len)))
        self.assertIsNone(tail._body_is_bound(
            dict(id="X", prompt_text=[{"role": "system", "content": candidate},
                                      {"role": "user", "content": "U"}]),
            {"X": ("U", "v")}, systems, tail._retry_suffixes()))

    def test_a_real_system_with_a_forged_user_body_is_refused(self):
        """system 을 진짜로 두고 **공고 본문만** 바꾼 로그. system 검사만으로는 통과한다."""
        dev, ids = self._dev_ids()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._events(tmp, notices=ids[:2], dataset_sha256=tail._sha256(dev),
                                dev_ids=ids)
            lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            for line in lines:
                if line["event"] == "model_call_started":
                    line["prompt_text"][-1]["content"] += "\n[숨긴 평가자료]"
            path.write_text("".join(json.dumps(line, ensure_ascii=False) + "\n" for line in lines),
                            encoding="utf-8", newline="\n")
            verdict = tail.validate_dev_export(path, dev, host="http://localhost:3002")
        self.assertFalse(verdict["allowed"])
        self.assertIn("unbound_body:prompt_body_mismatch", verdict["reasons"])

    def test_an_unknown_system_prompt_is_refused(self):
        """user 본문만 맞추고 system 에 다른 것을 숨긴 로그."""
        dev, ids = self._dev_ids()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._events(tmp, notices=ids[:2], dataset_sha256=tail._sha256(dev),
                                dev_ids=ids)
            lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            for line in lines:
                if line["event"] == "model_call_started":
                    line["prompt_text"][0]["content"] += "\n평가자료 조각"
            path.write_text("".join(json.dumps(line, ensure_ascii=False) + "\n" for line in lines),
                            encoding="utf-8", newline="\n")
            verdict = tail.validate_dev_export(path, dev, host="http://localhost:3002")
        self.assertFalse(verdict["allowed"])
        self.assertIn("unbound_body:unknown_system_tail", verdict["reasons"])

    def test_the_retry_suffix_is_a_known_tail(self):
        """분할 재시도는 system 뒤에 정해진 문장을 붙인다. 그것까지 막으면 재시도를 못 본다."""
        dev, ids = self._dev_ids()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._events(tmp, notices=ids[:2], dataset_sha256=tail._sha256(dev),
                                dev_ids=ids)
            lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            for line in lines:
                if line["event"] == "model_call_started":
                    line["prompt_text"][0]["content"] += (
                        "\n[Output scope for this call] Evaluate only these keys, overriding "
                        "the earlier key list: company_size. Return no other keys. "
                        "Keep evidence quotations under 100 characters.")
            path.write_text("".join(json.dumps(line, ensure_ascii=False) + "\n" for line in lines),
                            encoding="utf-8", newline="\n")
            verdict = tail.validate_dev_export(path, dev, host="http://localhost:3002")
        self.assertTrue(verdict["allowed"], verdict["reasons"])

    def test_a_tampered_visible_hash_is_refused(self):
        dev, ids = self._dev_ids()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._events(tmp, notices=ids[:2], dataset_sha256=tail._sha256(dev),
                                dev_ids=ids)
            lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            for line in lines:
                if line["event"] == "company_size_input":
                    line["visible_sha256"] = "0" * 64
            path.write_text("".join(json.dumps(line, ensure_ascii=False) + "\n" for line in lines),
                            encoding="utf-8", newline="\n")
            verdict = tail.validate_dev_export(path, dev, host="http://localhost:3002")
        self.assertFalse(verdict["allowed"])
        self.assertTrue(any(r.startswith("visible_sha256_mismatch") for r in verdict["reasons"]))

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
