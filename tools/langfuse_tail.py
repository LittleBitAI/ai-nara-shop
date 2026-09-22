"""`diagnostics.jsonl` 을 따라 읽어 로컬 Langfuse 로 보내는 사이드카.

**`script.py` 를 고치지 않는다.** 제출물은 바이트 하나도 안 바뀌어야 하고
(R7 제출 추론의 외부 호출 금지, R17 평가 데이터 외부 송신 금지, 그리고
"검증한 ZIP 을 그대로 제출한다"는 Colab 규율), `script.py` 는 이미 이벤트마다
`flush()` 하며 진단을 쓴다. 그래서 옆에서 따라 읽는 것으로 실시간이 된다.

    python tools/langfuse_tail.py --diagnostics out/diagnostics.jsonl --follow

키가 스위치다. `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY`/`LANGFUSE_HOST` 가
없으면 보낼 곳이 없다는 뜻이므로 아무것도 안 하고 끝난다.

**공개 dev 자료만 보낸다.** 비공개 평가 입력을 넣는 순간 R17 즉시 실격이다.

`capture_protocol=1` 로그에는 **모델에 실제로 보낸 프롬프트 전문과 응답 전문**이 들어 있다.
그래서 그 본문은 기본적으로 **보내지 않는다** — `--include-prompts` 와
`--dev-input` 을 함께 주고 `validate_dev_export()` 가 통과할 때만 실린다.
그 검사는 보낼 곳이 **로컬 Langfuse 인지**와 로그가 **고정 공개 dev 회차인지**를
provider 를 만들기 전에 본다. 플래그는 안전의 근거가 아니다 — 데이터 대조가 근거다.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
from urllib.parse import urlparse
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Optional

MODEL_FALLBACK = "google/gemma-4-26B-A4B-it"
ROOT = Path(__file__).resolve().parents[1]
# 프롬프트 전문 수출이 허용되는 곳. 대회 전용 로컬 Langfuse 하나뿐이다.
LOCAL_HOSTS = ("http://localhost:3002", "http://127.0.0.1:3002", "http://[::1]:3002")
# 프로젝트가 고정한 공개 dev 파일. 이 hash 가 아니면 프롬프트를 수출하지 않는다.
DEV_MANIFEST = ROOT/"reports/team-c/a8-v20-annex/inputs.json"
DEV_NAME = "open/dev.jsonl"


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _retry_suffixes() -> set:
    """분할 재시도가 system 뒤에 붙이는 **정확한 문자열들**(`script.py` 의 `retry_chat`).

    정규식으로 key 목록을 `[\\w, ]+` 로 열어 두면 안 된다 — 그 자리에 임의 문자열을
    넣은 system 이 통과한다(라운드 3 P0). 실제로 가능한 key 조합에서 문자열을 만든다.
    """
    sys.path.insert(0, str(ROOT))
    import script
    out = set()
    for keys in ([[key] for key in script.COMPANY_SIZE_KEYS] + [list(script.COMPANY_SIZE_KEYS)]):
        out.add("\n[Output scope for this call] Evaluate only these keys, overriding the "
                "earlier key list: " + ", ".join(keys) + ". Return no other keys. "
                "Keep evidence quotations under 100 characters.")
    return out


def _rebuild_dev_prompts(dev_path, wanted: dict, data_dir) -> dict:
    """공고별 user 프롬프트를 **실제 dev 파일에서 다시 만든다.**

    로그가 뭐라고 적었든 이것이 기준이다. id 가 고정 dev 에 있다는 것만으로는
    그 자리에 실린 본문이 dev 에서 왔다는 근거가 되지 않는다 —
    유효한 id 에 임의 문자열을 붙인 로그가 그 검사를 통과한다(라운드 2 P0).
    """
    sys.path.insert(0, str(ROOT))
    import script                                   # 수출 검사에서만 쓴다
    _, products = script.load_sme_reference(str(data_dir))
    out = {}
    for rec in script.iter_records(str(dev_path)):
        chars = wanted.get(rec["id"])
        if chars is None:
            continue
        # 수집기와 같은 변형이다 — meta 의 `조항호내용` 은 프롬프트에 안 들어간다.
        company = {**rec, "meta": {k: v for k, v in rec.get("meta", {}).items()
                                   if k != "조항호내용"}}
        messages = script.build_messages(company, script.COMPANY_SIZE_PROMPT, chars, products)
        out[rec["id"]] = (messages[-1]["content"],
                          hashlib.sha256(script.build_context(company, chars).encode()).hexdigest())
    return out


def _known_systems(data_dir) -> set:
    """내보내도 되는 system 프롬프트. 제품 프롬프트와 이 저장소의 후보 블록뿐이다."""
    sys.path.insert(0, str(ROOT))
    import script
    systems = {script.COMPANY_SIZE_PROMPT}
    try:
        from experiments import a8_v20_annex
        systems.add(script.COMPANY_SIZE_PROMPT + a8_v20_annex.block(str(data_dir)))
    except Exception:                                # 후보가 없는 저장소 상태면 제품 것만 허용한다
        pass
    return systems


def _body_is_bound(event, prompts: dict, systems: set, suffixes: set) -> Optional[str]:
    """이 호출의 프롬프트가 **재구성한 본문과 같은지** 본다. 다르면 이유를 돌려준다.

    형태를 느슨하게 보면 안 된다. 첫 메시지가 system·끝이 user 인 것만 보면
    그 사이에 `{"role":"assistant","content":"..."}` 를 끼운 배열이 통과하고,
    배열 전체가 span input 으로 나간다(라운드 3 P0). 실제 호출은 **정확히 두 메시지**이고
    각 메시지는 `role`·`content` 두 칸뿐이다.
    """
    text = event.get("prompt_text")
    if text is None:
        return None
    if (not isinstance(text, list) or len(text) != 2
            or not all(isinstance(m, dict) and set(m) == {"role", "content"}
                       and isinstance(m.get("content"), str) for m in text)
            or [m["role"] for m in text] != ["system", "user"]):
        return "prompt_shape"
    system = text[0]["content"]
    # 후보 system 은 제품 프롬프트로도 시작한다 — **가장 긴 것**을 골라야 블록이
    # 모르는 꼬리로 떨어지지 않는다. set 순서에 맡기면 회차가 seed 마다 거부된다(라운드 3 P1).
    base = max((known for known in systems if system.startswith(known)), key=len, default=None)
    if base is None:
        return "unknown_system"
    tail = system[len(base):]
    if tail and tail not in suffixes:
        return "unknown_system_tail"
    expected = prompts.get(event.get("id"))
    if expected is None:
        return "no_rebuilt_prompt"
    if text[-1].get("content") != expected[0]:
        return "prompt_body_mismatch"
    return None


def validate_dev_export(events_path, dev_path, *, host: str, data_dir=None) -> dict:
    """프롬프트 전문을 수출해도 되는지 **provider 를 만들기 전에** 판단한다.

    순수 함수다 — 파일을 읽고 판단만 돌려주며 네트워크를 모른다. 거짓이면
    호출자가 metadata 만 보낸다. 통과 조건은 넷이고 하나라도 빠지면 거짓이다.

    1. 보낼 곳이 대회 전용 로컬 Langfuse 주소 그대로다. userinfo·query·fragment·
       다른 경로·다른 포트는 전부 거부한다 — 로컬처럼 생긴 주소가 밖으로 리다이렉트할 수 있다.
    2. 로그의 첫 `run_started` 가 `dataset="dev"` 이고 그 `dataset_sha256` 이
       넘긴 dev 파일의 실측 hash 와 같고, **프로젝트가 고정한 공개 dev hash** 와도 같다.
    3. `dev_ids` 가 그 파일의 고유 공고 id 집합과 정확히 같다.
    4. 로그의 모든 공고 이벤트 id 가 그 집합 안에 있다. `null`·`ambiguous` 신원이
       하나라도 있으면 거짓이다 — 어느 공고의 프롬프트인지 모르는 본문은 내보내지 않는다.
    5. **실린 본문이 그 공고에서 나왔다.** 공고별 user 프롬프트와 문서 본문 hash 를
       실제 dev 파일에서 다시 만들어 한 글자까지 대조하고, system 은 제품 프롬프트나
       이 저장소의 후보 블록으로 시작하며 꼬리는 분할 재시도 문장뿐이어야 한다.
       1~4 만으로는 **유효한 id 에 임의 본문을 붙인 로그가 통과한다**(라운드 2 P0).
    """
    reasons = []
    if host not in LOCAL_HOSTS:
        reasons.append(f"host_not_local:{host}")
    events_path, dev_path = Path(events_path), Path(dev_path)
    if not events_path.is_file():
        reasons.append("no_diagnostics")
    if not dev_path.is_file():
        reasons.append("no_dev_input")
    if reasons:
        return dict(allowed=False, reasons=reasons)

    pinned = json.loads(DEV_MANIFEST.read_text(encoding="utf-8")).get(DEV_NAME)
    actual = _sha256(dev_path)
    if pinned != actual:
        reasons.append("dev_input_not_pinned")
    dev_ids = []
    for line in dev_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            dev_ids.append(json.loads(line)["id"])
    if len(dev_ids) != len(set(dev_ids)):
        reasons.append("dev_input_duplicate_ids")
    known, started = set(dev_ids), None
    seen, unknown = set(), set()
    inputs, calls = {}, []              # 공고별 문서 예산과, 본문이 실린 호출들
    with events_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("event") == "company_size_input" and event.get("id") in known:
                inputs[event["id"]] = event
            # 본문이 실린 것뿐 아니라 **모든 물리 호출 시작**을 모은다. 본문 없는 시작을
            # 빼고 보면 그 호출의 응답만 위조한 로그가 통과한다(라운드 4 P0).
            if (event.get("event") == "model_call_started"
                    or event.get("prompt_text") is not None
                    or event.get("response_text") is not None):
                calls.append(event)
            if event.get("event") == "run_started":
                if started is not None:
                    reasons.append("multiple_runs")
                    break
                started = event
                if event.get("dataset") != "dev":
                    reasons.append(f"dataset_not_dev:{event.get('dataset')}")
                if event.get("dataset_sha256") != actual:
                    reasons.append("dataset_sha256_mismatch")
                if sorted(event.get("dev_ids") or []) != sorted(known):
                    reasons.append("dev_ids_mismatch")
                continue
            if event.get("event") in ("model_call_started", "model_call_finished",
                                      "model_call_failed", "company_size_input", "response"):
                identifier = event.get("id")
                if identifier is None or event.get("identity_status") in ("ambiguous", "unmatched"):
                    unknown.add(event.get("identity_status") or "no_id")
                elif identifier not in known:
                    unknown.add(identifier)
                else:
                    seen.add(identifier)
    if started is None:
        reasons.append("no_run_started")
    if unknown:
        reasons.append("unknown_ids:" + ",".join(sorted(unknown)[:5]))

    bound = 0
    if not reasons and calls:
        prompts = _rebuild_dev_prompts(dev_path, {i: e["max_chars"] for i, e in inputs.items()},
                                       data_dir or ROOT/"open/data")
        systems, suffixes = _known_systems(data_dir or ROOT/"open/data"), _retry_suffixes()
        # 로그가 주장한 문서 본문 hash 도 재구성한 것과 맞아야 한다.
        for identifier, event in inputs.items():
            claimed, rebuilt = event.get("visible_sha256"), prompts.get(identifier)
            if rebuilt is None:
                reasons.append(f"no_rebuilt_prompt:{identifier}")
            elif claimed is not None and claimed != rebuilt[1]:
                reasons.append(f"visible_sha256_mismatch:{identifier}")
        problems, started_keys = set(), set()
        for event in calls:
            why = _body_is_bound(event, prompts, systems, suffixes)
            if why:
                problems.add(why)
                continue
            if event.get("event") == "model_call_started":
                # **본문 없는 시작은 결속을 건너뛴다.** 그러면 같은 호출의 응답만
                # 위조해도 통과한다(라운드 4 P0). 모든 물리 호출이 결속된 프롬프트를 갖는다.
                if event.get("prompt_text") is None:
                    problems.add("call_without_prompt")
                    continue
                started_keys.add(_call_key(event))
                bound += 1
            elif event.get("response_text") is not None:
                # 응답은 **결속된 시작과 짝이 맞을 때만** 내보낸다.
                if _call_key(event) not in started_keys:
                    problems.add("unpaired_output")
        if problems:
            reasons.append("unbound_body:" + ",".join(sorted(problems)))
    return dict(allowed=not reasons, reasons=sorted(set(reasons)), dev_records=len(known),
                observed_records=len(seen), bound_prompts=bound, dev_sha256=actual)


@dataclass
class Op:
    """span 하나에 대한 지시. 네트워크를 모른다."""
    action: str                      # open | close | point | update
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
    # 프롬프트·응답 **전문**을 실을지. `run()` 이 `validate_dev_export()` 통과 후에만 켠다.
    include_prompts: bool = False
    actual_mode: Optional[str] = None              # model_loaded 가 적은 실제 실행 방식
    code: str = ""                                 # trace 이름에 쓰는 코드 hash 앞자리
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


# 수출해도 되는 값의 모양. **"구조화 필드라서 안전하다" 는 근거가 아니다** —
# `settings.note` 나 `items` 에 임의 문자열을 넣은 로그가 그대로 실렸다(라운드 4 P0).
HEX = re.compile(r"^[0-9a-f]{7,64}$")
# id·군·단계 같은 짧은 식별자. **`/` 와 `:` 를 뺐다** — 그것이 있으면 경로가 통과한다.
TOKEN = re.compile(r"^[A-Za-z0-9_\-.+]{1,48}$")
# 값 집합이 정해진 enum. 타입만이 아니라 **값까지** 고정한다.
_ENUMS = {
    "identity_status": frozenset(("initial", "matched", "ambiguous", "unmatched")),
    "call_kind": frozenset(("initial", "retry")),
    "transport_status": frozenset(("returned", "failed", "response_count_mismatch")),
    "mode": frozenset(("live", "test_double", "pending", "?")),
    "mode_at_start": frozenset(("pending",)),
    "model_loaded": frozenset(("yes", "no")),
    "detail_capture": frozenset(("withheld",)),
    "prompt_capture": frozenset(("withheld", "unavailable")),
    "token_count_kind": frozenset(("actual", "estimate", "test_double")),
    "dataset": frozenset(("dev", "unlabeled")),
    "experiment": frozenset(("h3", "v18", "a8")),
    "status": frozenset(("valid", "invalid", "complete", "incomplete", "failed", "ok")),
    # `retry_chat` 의 단계와 전략, `sme_fallback` 의 출처. 값은 전부 `script.py` 가 만든다.
    "stage": frozenset(("call", "parse", "response_count")),
    "retry_strategy": frozenset(("split_items",)),
    "source": frozenset(("validated_baseline",)),
    # vLLM 이 만든다. 모르는 값이면 안 싣는다 — 그 자리는 자유 텍스트가 아니다.
    "finish_reason": frozenset(("stop", "length", "abort", "tool_calls")),
}
# `error_type` 은 예외 **클래스 이름**이라 값 집합을 못 고정한다. 임의 문자열이 올 수 있지만
# 좁힌 `TOKEN`(공백·`/`·`:` 없음, 48자)이 경로와 본문 조각을 막는다. 메시지는 `_detail()` 이 건다.
_NUMERIC = frozenset((
    "attempt", "call_index", "call_seq", "chunk_start", "count", "episode",
    "failed_response_count", "global_index", "load_seconds", "max_chars", "max_tokens",
    "output_reserved", "output_tokens", "prompt_budget", "prompt_tokens",
    "requested_max_chars", "response_chars", "sample_count", "seconds", "selected_count",
    "skipped_count", "stage_seconds", "valid_response_count"))
_TOKENS = frozenset((
    "arm", "call_kind", "dataset", "error_type", "experiment", "finish_reason", "id",
    "identity_status", "mode", "mode_at_start", "phase", "retry_strategy", "sample",
    "source", "stage", "status", "stop_reason", "token_count_kind", "transport_status",
    "platform", "python", "model_loaded", "detail_capture", "prompt_capture",
    "truncated", "quant", "seed", "chunk"))
_TOKEN_LISTS = frozenset(("ids", "indices", "dev_ids", "order", "arms"))
# 항목 이름은 **고정 목록**이다. 토큰 패턴만 보면 그 자리에 임의 문자열이 들어간다.
_ITEM_LISTS = frozenset(("items", "groups"))
# `argv` 는 명령줄이라 경로가 들어간다. `packages` 는 `이름==버전` 뿐이다.
PACKAGE = re.compile(r"^[A-Za-z0-9_.\-\[\]]+==[\w.+\-]+$")
# `verify_sme` 가 만드는 기각 사유 전부(`script.py:1258`). 그 밖의 문자열은 안 내보낸다.
REJECTION_REASONS = frozenset(("unverified_product", "unconfirmed_scope_or_exception",
                               "unverified_small_only_clause",
                               "clause_includes_medium_enterprises"))
# 자유 텍스트라 본문 게이트를 지난 것만 나간다. `_detail()` 이 이미 걸렀다.
_FREE = frozenset(("error_message", "traceback"))


def _known_items() -> frozenset:
    """제품이 쓰는 항목 이름 전부. 그 밖의 값은 `items`·`groups` 에 올 수 없다."""
    sys.path.insert(0, str(ROOT))
    import script
    return frozenset(script.ITEMS) | frozenset(script.COMPANY_SIZE_KEYS) | frozenset(script.SME_ITEMS)


def _clean(name: str, value: Any, *, _depth: int = 0) -> Any:
    """이 값이 생산자가 만드는 모양인지 본다. 아니면 버린다(None).

    이름으로 규칙을 찾는다 — 모르는 이름은 안 내보낸다. 수치는 수치여야 하고,
    hash 는 16진수여야 하고, 식별자·enum 은 짧은 토큰이어야 하고, 목록은 그 토큰의
    목록이어야 한다. 중첩 dict 는 키마다 같은 규칙을 다시 건다.
    """
    if value is None or _depth > 3:
        return None
    if name.endswith("_sha256"):
        return value if isinstance(value, str) and HEX.match(value) else None
    if name in _FREE:
        return value if isinstance(value, str) else None
    if name in _NUMERIC:
        return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None
    if name in _ENUMS:
        return value if value in _ENUMS[name] else None
    if name in _TOKENS:
        if isinstance(value, bool) or isinstance(value, (int, float)):
            return value
        return value if isinstance(value, str) and TOKEN.match(value) else None
    if name in _TOKEN_LISTS or name in _ITEM_LISTS or name == "packages":
        if not isinstance(value, list):
            return None
        flat = [item for entry in value for item in (entry if isinstance(entry, list) else [entry])]
        if name in _ITEM_LISTS:
            ok = flat and set(flat) <= _known_items()
        elif name == "packages":
            ok = all(isinstance(item, str) and PACKAGE.match(item) for item in flat)
        else:
            ok = all(isinstance(item, str) and TOKEN.match(item) for item in flat)
        return value if ok else None
    if isinstance(value, dict):        # settings·environment·expected_model·flags·rejected_conditions
        items, kept = _known_items(), {}
        for key, inner in value.items():
            if key in items:           # 항목별 판정·기각 사유. 값도 생산자가 만드는 것만.
                if isinstance(inner, bool) or isinstance(inner, int):
                    kept[key] = inner
                elif isinstance(inner, list) and set(inner) <= REJECTION_REASONS:
                    kept[key] = inner
                continue
            clean = _clean(key, inner, _depth=_depth + 1)
            if clean is not None:
                kept[key] = clean
        return kept or None
    return None                                      # 모르는 이름은 안 내보낸다


def _meta(**fields: Any) -> dict:
    """이벤트에서 온 값을 메타데이터로 만든다. **위생을 지난 것만 나간다.**

    코드에 박아 넣은 고정 문구는 이 함수를 쓰지 않는다 — `_fixed()` 가 따로 넣는다.
    그래야 "이름을 모르면 버린다" 가 규칙으로 성립한다.
    """
    out = {}
    for key, value in fields.items():
        clean = _clean(key, value)
        if clean is None:
            continue
        out[f"langfuse.observation.metadata.{key}"] = (
            clean if isinstance(clean, (str, int, float, bool))
            else json.dumps(clean, ensure_ascii=False))
    return out


def _fixed(**fields: str) -> dict:
    """이 파일이 만든 고정 문구. 이벤트에서 오지 않으므로 위생 대상이 아니다."""
    return {f"langfuse.observation.metadata.{k}": v for k, v in fields.items() if v is not None}


def _io(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


# 회차 종료 이벤트에서 span output 으로 내보내도 되는 필드. 나머지는 자유 텍스트다.
RUN_END_FIELDS = ("count", "seconds", "model_success_count", "status", "error_type",
                  "arms", "episode", "experiment", "stage")


def _detail(state: "State", value: Any) -> Any:
    """예외 메시지·traceback 은 **본문이다.** 개인 절대경로와 입력 조각이 그대로 들어간다.

    클래스 이름(`error_type`)은 안전하지만 메시지는 아니다. metadata 전용 모드에서
    `run_failed` 의 나머지 필드를 통째로 output 에 실어 경로가 나갔다(라운드 2 P0).
    """
    return value if state.include_prompts else None


def _status(state: "State", event: dict) -> str:
    kind = event.get("error_type") or "error"
    message = _detail(state, event.get("error_message"))
    return f"{kind}: {message}" if message else str(kind)


def _body(state: "State", attrs: dict, slot: str, value: Any) -> dict:
    """프롬프트·응답 **전문**은 수출 검사를 통과했을 때만 싣는다.

    막았을 때 조용히 비우지 않는다 — `prompt_capture="withheld"` 로 남겨
    Langfuse 에서 "본문이 없는 회차" 와 "본문을 안 보낸 회차" 가 갈린다.
    """
    if value is None:
        return attrs
    if state.include_prompts:
        attrs[f"langfuse.observation.{slot}"] = _io(value)
    else:
        attrs["langfuse.observation.metadata.prompt_capture"] = "withheld"
    return attrs


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
        state.code = (event.get("code_sha256") or "")[:7]
        state.trace_name = f"nara {mode} {state.code}".strip()
        # settings 도 통째로 싣지 않는다 — 임의 키를 넣은 로그가 루트 input 으로 나갔다.
        settings = _clean("settings", event.get("settings")) or {}
        return [Op("open", "run", state.trace_name, "span", None, now,
                   attrs={"langfuse.observation.input": _io(settings),
                          **_meta(mode=mode, code_sha256=event.get("code_sha256"),
                                  # argv 는 안 싣는다 — 명령줄에 개인 경로가 들어간다.
                                  platform=event.get("platform"),
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
        # 루트는 생성 전에 나므로 `mode="pending"` 으로 열렸다. 실제 mode 는 여기서 처음 알 수 있다.
        # 그것을 루트에 얹지 않으면 Langfuse 에서 **실제 모델 회차와 대역 실행이 안 갈린다.**
        ops = [Op("close", "model", end=now,
                  attrs=_meta(load_seconds=event.get("load_seconds"),
                              environment=event.get("environment")))]
        mode = event.get("mode")
        if mode:
            state.actual_mode = mode
            state.trace_name = f"nara {mode} {state.code}".strip()
            ops.append(Op("update", "run", state.trace_name,
                          attrs={"langfuse.trace.name": state.trace_name,
                                 **_meta(mode=mode, mode_at_start="pending",
                                         token_count_kind=event.get("token_count_kind"))},
                          # 루트가 없으면 실제 mode 를 잃는다. 그것을 투영 성공처럼 끝내지 않는다.
                          status="루트 span 이 없어 실제 mode 를 못 적었다"))
        return ops

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
                   attrs={**_meta(arm=arm, sample=sample, id=event.get("id"),
                                  max_chars=event.get("max_chars"),
                                  requested_max_chars=event.get("requested_max_chars"),
                                  truncated=event.get("truncated"),
                                  prompt_tokens=event.get("prompt_tokens"),
                                  token_count_kind=event.get("token_count_kind"),
                                  prompt_sha256=event.get("prompt_sha256"),
                                  visible_sha256=event.get("visible_sha256")),
                          **_fixed(note="입력 예산 관측. 군 간 추가 절단 판정은 "
                                        "budget.json 이 소유한다")})]

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
                         max_tokens=event.get("max_tokens"), items=event.get("items")),
                 # 같은 batch 의 호출들은 시작·종료를 공유한다. 한 건의 지연이 아니다.
                 **_fixed(duration_note="shared batch latency")}
        source = state.inputs.get((event.get("arm"), event.get("sample"), event.get("id")))
        if source is not None:
            attrs.update(_meta(max_chars=source.get("max_chars"),
                               token_count_kind=source.get("token_count_kind")))
        _body(state, attrs, "input", event.get("prompt_text"))
        return [Op("open", key, str(event.get("id") or event.get("call_index")), "generation",
                   state.chunk or state.arm or "run", now, attrs=attrs)]

    if kind in ("model_call_finished", "model_call_failed"):
        key = _call_key(event)
        if key not in state.calls:             # 시작 없는 종료는 관측 계약 실패다. 꾸며 넣지 않는다.
            return [Op("point", f"orphan:{key}:{now}", "orphan model call", "event",
                       state.arm or "run", now, now, level="ERROR",
                       attrs={**_fixed(call_key=key),
                              **_meta(transport_status=event.get("transport_status"))})]
        state.calls.pop(key, None)
        failed = kind == "model_call_failed"
        prompt_tokens, output_tokens = event.get("prompt_tokens"), event.get("output_tokens")
        attrs = {**_meta(transport_status=event.get("transport_status"),
                         finish_reason=event.get("finish_reason"),
                         stop_reason=event.get("stop_reason"),
                         error_type=event.get("error_type")),
                 **_fixed(note="반환 여부다. JSON 유효 판정은 parse-result 가 소유한다")}
        if prompt_tokens is not None and output_tokens is not None:
            # 둘 다 알 때만 total 을 만든다. 모르는 토큰을 0 으로 쓰지 않는다.
            attrs["langfuse.observation.usage_details"] = json.dumps(
                {"input": prompt_tokens, "output": output_tokens,
                 "total": prompt_tokens + output_tokens})
        elif prompt_tokens is not None or output_tokens is not None:
            attrs.update(_meta(prompt_tokens=prompt_tokens, output_tokens=output_tokens))
            attrs.update(_fixed(usage_note="한쪽만 보고돼 total 을 만들지 않았다"))
        _body(state, attrs, "output", event.get("response_text"))
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
                               error_message=_detail(state, event.get("error_message"))),
                   level=None if ok else "ERROR",
                   status="" if ok else _status(state, event))]

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
                    retry_strategy=event.get("retry_strategy"), groups=event.get("groups")),
            # 배치 호출이라 시작 시각은 청크와 같다. 한 건의 순수 지연이 아니다.
            **_fixed(duration_note="batch call; span starts at the chunk start"),
        }
        if prompt_tokens is not None or output_tokens is not None:
            attrs["langfuse.observation.usage_details"] = json.dumps(
                {"input": prompt_tokens or 0, "output": output_tokens or 0,
                 "total": (prompt_tokens or 0) + (output_tokens or 0)})
        _body(state, attrs, "input", event.get("prompt_text"))
        _body(state, attrs, "output", event.get("response_text"))
        return [Op("point", f"gen:{phase}:{event.get('global_index')}:{attempt}",
                   str(event.get("id") or event.get("global_index")), "generation",
                   state.chunk or "run", state.chunk_start or now, now, attrs=attrs,
                   level=None if ok else "ERROR",
                   status="" if ok else _status(state, event))]

    if kind in ("batch_failed", "retry_failed", "sme_fallback"):
        label = event.get("id") or event.get("chunk_start")
        return [Op("point",
                   f"{kind}:{phase}:{event.get('global_index')}:{event.get('attempt')}:{now}",
                   f"{kind} {label}", "event", state.chunk or "run", now, now,
                   attrs=_meta(phase=phase, stage=event.get("stage"), attempt=event.get("attempt"),
                               source=event.get("source"), global_index=event.get("global_index")),
                   level="WARNING" if kind == "sme_fallback" else "ERROR",
                   status=_status(state, event))]

    if kind == "sme_verified":
        return [Op("point", f"verify:{event.get('id')}", f"verify {event.get('id')}", "event",
                   "run", now, now,
                   attrs={"langfuse.observation.output": _io(_clean("flags", event.get("flags"))
                                                             or {}),
                          **_meta(rejected_conditions=event.get("rejected_conditions"))})]

    if kind in ("run_succeeded", "run_failed"):
        # 남은 것을 안쪽부터 닫는다 — 호출 → 청크 → 군 → run.
        for key in list(state.calls):
            ops.append(Op("close", key, end=now, level="ERROR", status="no model_call_finished",
                          attrs=_fixed(note="종료 이벤트 없이 회차가 끝났다")))
        state.calls.clear()
        if state.chunk:
            ops.append(Op("close", state.chunk, end=now))
            state.chunk = None
        for key in list(state.arms.values()):
            ops.append(Op("close", key, end=now,
                          attrs=_fixed(status="incomplete",
                                       note="arm_finished 없이 회차가 끝났다")))
        state.arms.clear()
        state.arm = None
        failed = kind == "run_failed"
        # 이벤트를 통째로 싣지 않는다 — `run_failed` 에는 error_message 와 traceback 이 있고
        # 거기에 개인 절대경로가 들어간다. 허용 목록만 내보낸다.
        # 허용 목록의 **값도** 위생을 지난다 — 이름만 맞추고 임의 값을 넣을 수 있다.
        summary = {k: _clean(k, event[k]) for k in RUN_END_FIELDS if k in event}
        summary = {k: v for k, v in summary.items() if v is not None}
        ops.append(Op("close", "run", end=now,
                      attrs={"langfuse.observation.output": _io(summary),
                             # 루트가 `pending` 으로 끝나지 않게 실제 mode 를 마지막에 한 번 더 적는다.
                             **_meta(mode=state.actual_mode or "pending",
                                     model_loaded="yes" if state.actual_mode else "no",
                                     error_type=event.get("error_type"),
                                     detail_capture=None if state.include_prompts else "withheld",
                                     traceback=_detail(state, event.get("traceback")))},
                      level="ERROR" if failed else None,
                      status=_status(state, event) if failed else ""))
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


def _session_name(path) -> str:
    """경로를 span 에 안 싣는 안정 ID. 같은 파일이면 같은 이름이라 trace 가 이어진다."""
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        digest = hashlib.sha256(str(resolved).encode()).hexdigest()[:12]
        return f"{resolved.name}:{digest}"


def _same_host(url: str, host: str) -> bool:
    """scheme·hostname·port 가 같은지 본다. 문자열 `startswith` 로는 부족하다 —
    `http://localhost:3002@evil.example/x` 가 그것을 통과한다(라운드 3 P0)."""
    left, right = urlparse(str(url)), urlparse(host)
    return (left.scheme == right.scheme and left.hostname == right.hostname
            and left.port == right.port and not left.username and not left.password)


def pin_to_host(exporter, host: str) -> None:
    """수출이 **그 호스트를 떠나지 못하게** 한다. 셋을 막는다.

    1. **redirect.** `OTLPSpanExporter` 는 `requests.Session.post` 를 `allow_redirects`
       없이 부르고 requests 의 기본값은 따라가기다. 로컬 엔드포인트가 307/308 로 외부
       `Location` 을 돌려주면 검사를 통과한 본문이 밖으로 다시 POST 된다(라운드 2 P0).
    2. **환경 프록시.** 세션의 `trust_env` 가 참이면 `HTTP_PROXY` 가 있는 환경에서
       `merge_environment_settings()` 가 **로컬 주소에도** 외부 프록시를 고른다.
       그러면 본문과 인증 헤더가 그 프록시로 간다(라운드 3 P0).
    3. **호스트 위장.** url 을 파싱해 scheme·hostname·port 를 비교하고 userinfo 를 거부한다.

    세션을 못 잡으면 **조용히 넘어가지 않고 세운다.** 막았다고 믿는 것이
    안 막힌 것보다 나쁘다.
    """
    session = getattr(exporter, "_session", None)
    if session is None or not hasattr(session, "request"):
        raise RuntimeError("OTLP 세션을 못 잡았다. redirect 를 막을 수 없으므로 수출하지 않는다.")
    session.trust_env = False                       # 환경 프록시를 안 본다
    session.proxies = {}
    original = session.request

    def request(method, url, **kwargs):
        if not _same_host(url, host):
            raise RuntimeError(f"허용된 호스트 밖으로 보내려 했다: {url}")
        kwargs["allow_redirects"] = False           # setdefault 가 아니다 — post() 가 이미 True 를 넣는다
        kwargs["proxies"] = {}
        return original(method, url, **kwargs)

    session.request = request


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
    exporter = OTLPSpanExporter(
        endpoint=f"{host.rstrip('/')}/api/public/otel/v1/traces",
        headers={"Authorization": f"Basic {auth}", "x-langfuse-ingestion-version": "4"})
    pin_to_host(exporter, host)
    provider.add_span_processor(BatchSpanProcessor(exporter))
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
    # 기본 실행 이름에 절대경로를 쓰지 않는다 — `C:/Users/<이름>/...` 이 span 에 실린다
    # (라운드 3 P0). 저장소 안이면 상대경로, 밖이면 파일명 + 경로 hash 앞자리다.
    session = args.session or _session_name(path)
    trace_id = int.from_bytes(hashlib.sha256(session.encode()).digest()[:16], "big")

    # 프롬프트·응답 전문 수출은 **provider 를 만들기 전에** 판단한다.
    include_prompts = False
    if args.include_prompts:
        if args.follow or args.from_line:
            print("[tail] --include-prompts 는 완성 파일만 본다. --follow/--from-line 과 같이 못 쓴다.")
            return 2
        if not args.dev_input:
            print("[tail] --include-prompts 에는 --dev-input 이 필요하다. 대조할 것이 없으면 안 보낸다.")
            return 2
        verdict = validate_dev_export(path, args.dev_input, host=host)
        if not verdict["allowed"]:
            print("[tail] 프롬프트 수출 거부: " + ", ".join(verdict["reasons"]))
            return 2
        include_prompts = True
        print(f"[tail] 프롬프트 수출 허용 — 로컬 {host}, 공고 {verdict['observed_records']}"
              f"/{verdict['dev_records']}건")

    provider = build_provider(host, public, secret, trace_id, args.service)
    tracer = provider.get_tracer("nara-langfuse-tail")

    state = State(include_prompts=include_prompts)
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
                if op.action == "update":       # 열린 span 을 닫지 않고 고친다
                    span = live.get(op.key)
                    if span is None:
                        # 조용히 버리면 실제 mode 를 잃고도 투영이 성공처럼 끝난다.
                        print(f"[tail] 관측 계약 실패: {op.status or op.key}")
                        continue
                    for key, value in op.attrs.items():
                        span.set_attribute(key, value)
                    if op.name:
                        span.update_name(op.name)
                    continue
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
    parser.add_argument("--dev-input", default="",
                        help="대조할 고정 공개 dev 파일. --include-prompts 에 필수다")
    parser.add_argument("--include-prompts", action="store_true",
                        help="프롬프트·응답 **전문**을 싣는다. 로컬 Langfuse + 고정 dev 회차만 허용된다")
    parser.add_argument("--environment", default="colab")
    parser.add_argument("--session", default="", help="실행 이름. 비우면 파일 경로로 정한다")
    parser.add_argument("--service", default="ai-nara-shop")
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
