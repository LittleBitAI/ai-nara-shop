"""`diagnostics.jsonl` 을 따라 읽어 로컬 Langfuse 로 보내는 사이드카.

**`script.py` 를 고치지 않는다.** 제출물은 바이트 하나도 안 바뀌어야 하고
(R7 제출 추론의 외부 호출 금지, R17 평가 데이터 외부 송신 금지, 그리고
"검증한 ZIP 을 그대로 제출한다"는 Colab 규율), `script.py` 는 이미 이벤트마다
`flush()` 하며 진단을 쓴다. 그래서 옆에서 따라 읽는 것으로 실시간이 된다.

    python tools/langfuse_tail.py --diagnostics out/diagnostics.jsonl --follow

키가 스위치다. `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY`/`LANGFUSE_HOST` 가
없으면 보낼 곳이 없다는 뜻이므로 아무것도 안 하고 끝난다.

**공개 dev 자료만 보낸다.** 비공개 평가 입력을 넣는 순간 R17 즉시 실격이다.
원문·프롬프트는 `--debug-responses` 로 돌린 진단 실행에만 들어 있다.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Optional

MODEL_FALLBACK = "google/gemma-4-26B-A4B-it"


@dataclass
class Op:
    """span 하나에 대한 지시. 네트워크를 모른다."""
    action: str                      # open | close | point
    key: str
    name: str = ""
    kind: str = "span"               # Langfuse 의 observation type
    parent: Optional[str] = None
    start: float = 0.0
    end: float = 0.0
    attrs: dict = field(default_factory=dict)
    level: Optional[str] = None
    status: str = ""


@dataclass
class State:
    run: Optional[str] = None
    trace_name: str = "nara-run"
    model: str = MODEL_FALLBACK
    phase: str = "baseline"
    chunk: Optional[str] = None
    chunk_start: float = 0.0
    last: float = 0.0
    # 아래는 capture_protocol 1 로 기록한 회차에서만 채워진다.
    capture_protocol: Optional[int] = None
    arm: Optional[str] = None                      # 현재 열린 군 span 의 이름
    arms: dict = field(default_factory=dict)       # (arm, sample) → span key
    inputs: dict = field(default_factory=dict)     # (arm, sample, id) → company_size_input 이벤트
    calls: dict = field(default_factory=dict)      # call key → 시작 시각


def _scope(event: dict) -> tuple:
    """군·표본을 포함한 범위. 이 값이 span key 에 들어가야 두 군이 겹치지 않는다."""
    return event.get("arm"), event.get("sample")


def _arm_key(event: dict) -> Optional[str]:
    arm, sample = _scope(event)
    return None if arm is None else f"arm:{arm}:{sample}"


def _call_key(event: dict) -> str:
    """물리 모델 요청 하나의 전체 식별자."""
    arm, sample = _scope(event)
    return (f"call:{arm}:{sample}:{event.get('phase')}:{event.get('chunk_start')}"
            f":{event.get('call_seq')}:{event.get('call_index')}")


def _meta(**fields: Any) -> dict:
    """None 을 걸러 Langfuse 메타데이터 속성으로 만든다."""
    return {f"langfuse.observation.metadata.{k}":
            v if isinstance(v, (str, int, float, bool)) else json.dumps(v, ensure_ascii=False)
            for k, v in fields.items() if v is not None}


def _io(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def plan(event: dict, state: State) -> list:
    """이벤트 하나를 span 지시로 바꾼다. 여기까지가 순수 함수다."""
    kind = event.get("event")
    now = float(event.get("time_unix") or state.last or time.time())
    state.last = now
    phase = event.get("phase") or state.phase
    ops: list = []

    if kind == "run_started":
        state.run = "run"
        state.capture_protocol = event.get("capture_protocol")
        state.model = (event.get("expected_model") or {}).get("id") or MODEL_FALLBACK
        mode = event.get("mode", "?")
        code = (event.get("code_sha256") or "")[:7]
        state.trace_name = f"nara {mode} {code}".strip()
        return [Op("open", "run", state.trace_name, "span", None, now,
                   attrs={"langfuse.observation.input": _io(event.get("settings", {})),
                          **_meta(mode=mode, code_sha256=event.get("code_sha256"),
                                  argv=event.get("argv"), platform=event.get("platform"),
                                  python=event.get("python"),
                                  expected_model=event.get("expected_model"))})]

    if state.run is None:                      # run_started 앞의 줄은 버린다
        return []

    if kind == "assets":
        return [Op("point", f"assets:{now}", "assets", "event", "run", now, now,
                   attrs=_meta(packages=event.get("packages"), sha256=event.get("sha256")))]

    if kind == "model_loading":
        return [Op("open", "model", "model-load", "span", "run", now,
                   attrs=_meta(schema_sha256=event.get("schema_sha256"),
                               system_prompt_sha256=event.get("system_prompt_sha256")))]

    if kind == "model_loaded":
        return [Op("close", "model", end=now,
                   attrs=_meta(load_seconds=event.get("load_seconds"),
                               environment=event.get("environment")))]

    if kind == "arm_started":
        key = _arm_key(event)
        if key is None:
            return []
        arm, sample = _scope(event)
        state.arm, state.arms[(arm, sample)] = key, key
        return [Op("open", key, f"arm {arm} · {sample}", "span", "run", now,
                   attrs=_meta(arm=arm, sample=sample, selected_count=event.get("selected_count"),
                               system_prompt_sha256=event.get("system_prompt_sha256"),
                               schema_sha256=event.get("schema_sha256"),
                               output_reserved=event.get("output_reserved"),
                               prompt_budget=event.get("prompt_budget")))]

    if kind == "arm_finished":
        key = _arm_key(event)
        if key is None:
            return []
        if state.chunk:                        # 군이 끝나면 남은 청크를 먼저 닫는다.
            ops.append(Op("close", state.chunk, end=now))
            state.chunk = None
        ops.append(Op("close", key, end=now,
                      attrs=_meta(status=event.get("status"), stage_seconds=event.get("stage_seconds"),
                                  valid_response_count=event.get("valid_response_count"),
                                  failed_response_count=event.get("failed_response_count"))))
        state.arms.pop(_scope(event), None)
        state.arm = None
        return ops

    if kind == "phase_started":
        state.phase = event.get("phase", phase)
        return [Op("point", f"phase:{state.arm or 'run'}:{state.phase}", f"phase {state.phase}",
                   "event", state.arm or "run", now, now,
                   attrs=_meta(arm=event.get("arm"), sample=event.get("sample"),
                               items=event.get("items"),
                               selected_count=event.get("selected_count"),
                               skipped_count=event.get("skipped_count"),
                               system_prompt_sha256=event.get("system_prompt_sha256")))]

    if kind == "company_size_input" and state.capture_protocol:
        arm, sample = _scope(event)
        # 공고별 입력 예산을 군과 함께 기억한다. `chars < 요청값` 만으로 문서 누락을 단정하지 않는다.
        state.inputs[(arm, sample, event.get("id"))] = event
        return [Op("point", f"input:{arm}:{sample}:{event.get('id')}", str(event.get("id")),
                   "event", state.arm or "run", now, now,
                   attrs=_meta(arm=arm, sample=sample, id=event.get("id"),
                               max_chars=event.get("max_chars"),
                               requested_max_chars=event.get("requested_max_chars"),
                               truncated=event.get("truncated"),
                               prompt_tokens=event.get("prompt_tokens"),
                               token_count_kind=event.get("token_count_kind"),
                               prompt_sha256=event.get("prompt_sha256"),
                               visible_sha256=event.get("visible_sha256"),
                               note="입력 예산 관측. 군 간 추가 절단 판정은 budget.json 이 소유한다"))]

    if kind == "chunk_started":
        if state.chunk:                        # 청크는 순차적이다. 앞 청크를 닫는다.
            ops.append(Op("close", state.chunk, end=now))
        state.phase = phase
        arm, sample = _scope(event)
        # 군을 key 에 넣는다 — 안 넣으면 control 의 청크에 a8 의 호출이 이어 붙는다.
        state.chunk = (f"chunk:{arm}:{sample}:{phase}:{event.get('chunk_start')}" if arm
                       else f"chunk:{phase}:{event.get('chunk_start')}")
        state.chunk_start = now
        ops.append(Op("open", state.chunk, f"{phase} chunk {event.get('chunk_start')}",
                      "span", state.arm or "run", now,
                      attrs=_meta(arm=arm, sample=sample, count=event.get("count"),
                                  ids=event.get("ids"), indices=event.get("indices"))))
        return ops

    if kind == "chunk_finished":
        if state.chunk:
            ops.append(Op("close", state.chunk, end=now))
            state.chunk = None
        return ops

    if kind == "model_call_started":
        key = _call_key(event)
        state.calls[key] = now
        attrs = {"langfuse.observation.model.name": state.model,
                 **_meta(arm=event.get("arm"), sample=event.get("sample"), id=event.get("id"),
                         identity_status=event.get("identity_status"),
                         call_kind=event.get("call_kind"), call_seq=event.get("call_seq"),
                         call_index=event.get("call_index"),
                         prompt_sha256=event.get("prompt_sha256"),
                         schema_sha256=event.get("schema_sha256"),
                         max_tokens=event.get("max_tokens"), items=event.get("items"),
                         # 같은 batch 의 호출들은 시작·종료를 공유한다. 한 건의 지연이 아니다.
                         duration_note="shared batch latency")}
        source = state.inputs.get((event.get("arm"), event.get("sample"), event.get("id")))
        if source is not None:
            attrs.update(_meta(max_chars=source.get("max_chars"),
                               token_count_kind=source.get("token_count_kind")))
        if event.get("prompt_text") is not None:
            attrs["langfuse.observation.input"] = _io(event["prompt_text"])
        return [Op("open", key, str(event.get("id") or event.get("call_index")), "generation",
                   state.chunk or state.arm or "run", now, attrs=attrs)]

    if kind in ("model_call_finished", "model_call_failed"):
        key = _call_key(event)
        if key not in state.calls:             # 시작 없는 종료는 관측 계약 실패다. 꾸며 넣지 않는다.
            return [Op("point", f"orphan:{key}:{now}", "orphan model call", "event",
                       state.arm or "run", now, now, level="ERROR",
                       attrs=_meta(call_key=key, transport_status=event.get("transport_status")))]
        state.calls.pop(key, None)
        failed = kind == "model_call_failed"
        prompt_tokens, output_tokens = event.get("prompt_tokens"), event.get("output_tokens")
        attrs = _meta(transport_status=event.get("transport_status"),
                      finish_reason=event.get("finish_reason"), stop_reason=event.get("stop_reason"),
                      error_type=event.get("error_type"),
                      note="반환 여부다. JSON 유효 판정은 parse-result 가 소유한다")
        if prompt_tokens is not None and output_tokens is not None:
            # 둘 다 알 때만 total 을 만든다. 모르는 토큰을 0 으로 쓰지 않는다.
            attrs["langfuse.observation.usage_details"] = json.dumps(
                {"input": prompt_tokens, "output": output_tokens,
                 "total": prompt_tokens + output_tokens})
        elif prompt_tokens is not None or output_tokens is not None:
            attrs.update(_meta(prompt_tokens=prompt_tokens, output_tokens=output_tokens,
                               usage_note="한쪽만 보고돼 total 을 만들지 않았다"))
        if event.get("response_text") is not None:
            attrs["langfuse.observation.output"] = _io(event["response_text"])
        return [Op("close", key, end=now, attrs=attrs, level="ERROR" if failed else None,
                   status=f"{event.get('error_type')}" if failed else "")]

    if kind == "response" and state.capture_protocol:
        # 새 판형에서 물리 생성은 `model_call_*` 가 소유한다. 여기서 또 generation 을 만들면
        # 호출 하나가 둘로 세진다. 최초 invalid·최종 valid 는 그대로 남긴다.
        arm, sample = _scope(event)
        ok = event.get("status") == "valid"
        return [Op("point",
                   f"parse:{arm}:{sample}:{event.get('global_index')}:{event.get('attempt', 1)}",
                   f"parse {event.get('id') or event.get('global_index')}", "event",
                   state.chunk or state.arm or "run", now, now,
                   attrs=_meta(arm=arm, sample=sample, id=event.get("id"),
                               attempt=event.get("attempt", 1), status=event.get("status"),
                               response_chars=event.get("response_chars"),
                               error_type=event.get("error_type"),
                               error_message=event.get("error_message")),
                   level=None if ok else "ERROR",
                   status="" if ok else f"{event.get('error_type')}: {event.get('error_message')}")]

    if kind == "response":
        attempt = event.get("attempt", 1)
        ok = event.get("status") == "valid"
        prompt_tokens = event.get("prompt_tokens")
        output_tokens = event.get("output_tokens")
        attrs = {
            "langfuse.observation.model.name": state.model,
            **_meta(phase=phase, attempt=attempt, status=event.get("status"),
                    response_chars=event.get("response_chars"),
                    finish_reason=event.get("finish_reason"), stop_reason=event.get("stop_reason"),
                    max_tokens=event.get("max_tokens"), global_index=event.get("global_index"),
                    chunk_start=event.get("chunk_start"),
                    retry_strategy=event.get("retry_strategy"), groups=event.get("groups"),
                    # 배치 호출이라 시작 시각은 청크와 같다. 한 건의 순수 지연이 아니다.
                    duration_note="batch call; span starts at the chunk start"),
        }
        if prompt_tokens is not None or output_tokens is not None:
            attrs["langfuse.observation.usage_details"] = json.dumps(
                {"input": prompt_tokens or 0, "output": output_tokens or 0,
                 "total": (prompt_tokens or 0) + (output_tokens or 0)})
        if event.get("prompt_text") is not None:
            attrs["langfuse.observation.input"] = _io(event["prompt_text"])
        if event.get("response_text") is not None:
            attrs["langfuse.observation.output"] = _io(event["response_text"])
        return [Op("point", f"gen:{phase}:{event.get('global_index')}:{attempt}",
                   str(event.get("id") or event.get("global_index")), "generation",
                   state.chunk or "run", state.chunk_start or now, now, attrs=attrs,
                   level=None if ok else "ERROR",
                   status="" if ok else f"{event.get('error_type')}: {event.get('error_message')}")]

    if kind in ("batch_failed", "retry_failed", "sme_fallback"):
        label = event.get("id") or event.get("chunk_start")
        return [Op("point",
                   f"{kind}:{phase}:{event.get('global_index')}:{event.get('attempt')}:{now}",
                   f"{kind} {label}", "event", state.chunk or "run", now, now,
                   attrs=_meta(phase=phase, stage=event.get("stage"), attempt=event.get("attempt"),
                               source=event.get("source"), global_index=event.get("global_index")),
                   level="WARNING" if kind == "sme_fallback" else "ERROR",
                   status=f"{event.get('error_type')}: {event.get('error_message')}")]

    if kind == "sme_verified":
        return [Op("point", f"verify:{event.get('id')}", f"verify {event.get('id')}", "event",
                   "run", now, now,
                   attrs={"langfuse.observation.output": _io(event.get("flags", {})),
                          **_meta(rejected_conditions=event.get("rejected_conditions"))})]

    if kind in ("run_succeeded", "run_failed"):
        # 남은 것을 안쪽부터 닫는다 — 호출 → 청크 → 군 → run.
        for key in list(state.calls):
            ops.append(Op("close", key, end=now, level="ERROR", status="no model_call_finished",
                          attrs=_meta(note="종료 이벤트 없이 회차가 끝났다")))
        state.calls.clear()
        if state.chunk:
            ops.append(Op("close", state.chunk, end=now))
            state.chunk = None
        for key in list(state.arms.values()):
            ops.append(Op("close", key, end=now,
                          attrs=_meta(status="incomplete", note="arm_finished 없이 회차가 끝났다")))
        state.arms.clear()
        state.arm = None
        failed = kind == "run_failed"
        ops.append(Op("close", "run", end=now,
                      attrs={"langfuse.observation.output": _io(
                          {k: v for k, v in event.items() if k not in ("event", "time_unix")}),
                          **_meta(traceback=event.get("traceback"))},
                      level="ERROR" if failed else None,
                      status=(f"{event.get('error_type')}: {event.get('error_message')}"
                              if failed else "")))
        return ops

    return []


def follow(path: Path, from_line: int, keep_following: bool, idle: float) -> Iterator[dict]:
    """파일이 생길 때까지 기다렸다가 줄 단위로 읽는다. 끝나면 잠깐 자고 다시 본다."""
    waited = 0.0
    while not path.exists():
        if not keep_following or waited > idle:
            raise SystemExit(f"진단 파일이 없다: {path}")
        time.sleep(0.5)
        waited += 0.5
    seen, quiet = 0, 0.0
    with path.open("r", encoding="utf-8") as stream:
        while True:
            line = stream.readline()
            if line:
                quiet = 0.0
                seen += 1
                if seen <= from_line:
                    continue
                line = line.strip()
                if line:
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        print(f"[tail] 줄 {seen} 을 건너뛴다(JSON 아님)", file=sys.stderr)
                continue
            if not keep_following or quiet > idle:
                return
            time.sleep(0.5)
            quiet += 0.5


def build_provider(host: str, public: str, secret: str, trace_id: int, service: str):
    """Langfuse 의 OTel 수집 엔드포인트로 바로 내보낸다."""
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.trace.id_generator import IdGenerator

    class Fixed(IdGenerator):
        """한 실행은 한 trace 다. 중간에 죽어 다시 붙어도 같은 곳에 쌓인다."""

        def generate_span_id(self) -> int:
            return int.from_bytes(os.urandom(8), "big") or 1

        def generate_trace_id(self) -> int:
            return trace_id

    auth = base64.b64encode(f"{public}:{secret}".encode()).decode()
    provider = TracerProvider(resource=Resource.create({"service.name": service}),
                              id_generator=Fixed())
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(
        endpoint=f"{host.rstrip('/')}/api/public/otel/v1/traces",
        headers={"Authorization": f"Basic {auth}", "x-langfuse-ingestion-version": "4"})))
    return provider


def run(args: argparse.Namespace) -> int:
    host = os.environ.get("LANGFUSE_HOST", "")
    public = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    secret = os.environ.get("LANGFUSE_SECRET_KEY", "")
    if not (host and public and secret):
        print("[tail] LANGFUSE_HOST/PUBLIC_KEY/SECRET_KEY 가 없다. 보낼 곳이 없으므로 끝낸다.")
        return 0

    from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags, set_span_in_context

    path = Path(args.diagnostics)
    session = args.session or str(path.resolve())
    trace_id = int.from_bytes(hashlib.sha256(session.encode()).digest()[:16], "big")
    provider = build_provider(host, public, secret, trace_id, args.service)
    tracer = provider.get_tracer("nara-langfuse-tail")

    state = State()
    live: dict = {}
    sent = [0]

    def finish(span, op: Op) -> None:
        for key, value in op.attrs.items():
            span.set_attribute(key, value)
        if op.level:
            span.set_attribute("langfuse.observation.level", op.level)
        if op.status:
            span.set_attribute("langfuse.observation.status_message", op.status[:2000])
        span.end(end_time=int(op.end * 1_000_000_000))
        sent[0] += 1

    try:
        for event in follow(path, args.from_line, args.follow, args.idle_timeout):
            for op in plan(event, state):
                if op.action == "close":
                    span = live.pop(op.key, None)
                    if span is not None:
                        finish(span, op)
                    continue
                parent = live.get(op.parent) if op.parent else None
                context = None
                if parent is not None:
                    context = set_span_in_context(parent)
                elif op.parent:                 # 부모가 이미 닫혔어도 같은 trace 아래 둔다
                    context = set_span_in_context(NonRecordingSpan(SpanContext(
                        trace_id, 1, False, TraceFlags(TraceFlags.SAMPLED))))
                span = tracer.start_span(op.name or op.key, context=context,
                                         start_time=int(op.start * 1_000_000_000))
                span.set_attribute("langfuse.trace.name", state.trace_name)
                span.set_attribute("langfuse.session.id", session)
                span.set_attribute("langfuse.environment", args.environment)
                span.set_attribute("langfuse.observation.type", op.kind)
                if op.action == "point":
                    finish(span, op)
                else:
                    live[op.key] = span
    finally:
        now = time.time()
        for span in live.values():              # 실행이 죽어도 열린 span 을 남기지 않는다
            span.set_attribute("langfuse.observation.status_message", "unfinished: tail stopped")
            span.end(end_time=int(now * 1_000_000_000))
            sent[0] += 1
        provider.shutdown()                     # 남은 배치를 내보낸다
    print(f"[tail] span {sent[0]}건 전송. trace={trace_id:032x}")
    return 0


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--diagnostics", required=True, help="script.py 가 쓰는 diagnostics.jsonl")
    parser.add_argument("--follow", action="store_true", help="실행 중에 따라 읽는다")
    parser.add_argument("--from-line", type=int, default=0, help="이 줄까지는 건너뛴다(재개용)")
    parser.add_argument("--idle-timeout", type=float, default=900.0,
                        help="이 시간 동안 새 줄이 없으면 끝낸다")
    parser.add_argument("--environment", default="colab")
    parser.add_argument("--session", default="", help="실행 이름. 비우면 파일 경로로 정한다")
    parser.add_argument("--service", default="ai-nara-shop")
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
