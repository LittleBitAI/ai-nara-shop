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
    notice_ids: frozenset = frozenset()            # 회차가 선언한 공고 id 집합
    arm: Optional[str] = None                      # 현재 열린 군 span 의 이름
    arms: dict = field(default_factory=dict)       # (arm, sample) → span key
    inputs: dict = field(default_factory=dict)     # (arm, sample, id) → company_size_input 이벤트
    calls: dict = field(default_factory=dict)      # call key → 시작 시각


def _label(name: str, value: Any, fallback: str = "?") -> str:
    """span 이름·trace 이름에 쓰는 값. **이름도 수출이다.**

    metadata 만 위생하면 `mode="NON_DEV_SECRET"` 이 span 이름과 `langfuse.trace.name`
    으로 그대로 나간다(라운드 5 P0). 같은 규칙을 이름에도 건다.
    """
    clean = _clean(name, value)
    return str(clean) if clean is not None else fallback


# span 이름·상태 문자열에 남아도 되는 모양. 공고 id 와 군·단계 이름을 붙여 만든다.
NAME = re.compile(r"^[A-Za-z0-9_\-.+·: ]{1,96}$")


def guard(op: "Op") -> "Op":
    """**모든 Op 가 여기를 지나 밖으로 나간다.** 출구가 하나다.

    왜 이 자리인가. 라운드 1~5 의 P0 열둘이 전부 같은 결함이었다 — 값이 span 으로
    나가는 경로가 여럿인데 지적된 출구마다 게이트를 달았다. `input`/`output` 두 슬롯 →
    `status` → `metadata` → **span 이름** → `usage_details` 로 면이 하나씩 나왔다.
    호출자를 막으면 막을 목록을 손으로 세게 되고 그 목록은 언제나 모자란다.

    그래서 `plan()` 의 어느 분기가 무엇을 넣든 직렬화 **직전에** 여기서 한 번 본다.
    새 필드가 생겨도 자동으로 이 통로를 지난다 — 열거할 목록이 없다.

    `attrs` 는 이미 `_meta()`·`_fixed()`·`_body()` 가 만든 최종 키다. 여기서는
    **이름·상태·usage 처럼 metadata 를 안 지나는 자리**를 같은 기준으로 막는다.
    """
    if not NAME.match(op.key):
        # key 도 이름이 된다(`run()` 이 name 이 없으면 key 로 span 을 만든다). 모양이
        # 아니면 **결정적 hash** 로 바꾼다 — 같은 입력이 같은 key 가 되므로 open/close 짝이
        # 유지된다. 정상 경로에서는 조립에 쓰는 값이 이미 위생을 지나 여기 안 걸린다.
        op.key = "op:" + hashlib.sha256(op.key.encode("utf-8")).hexdigest()[:16]
    if op.name and not NAME.match(op.name):
        op.name = op.key.split(":")[0]
    if op.status and not NAME.match(op.status) and not op.attrs.get(
            "langfuse.observation.metadata.traceback"):
        # 상태 문구는 `_status()` 가 만들고 본문은 이미 게이트를 지났다. 남은 것은
        # 게이트를 통과한 상세거나 이 파일의 고정 문구다. 그 밖의 모양은 자른다.
        if not any(op.status.startswith(fixed) for fixed in _FIXED_STATUS):
            op.status = op.status.split(":")[0][:96]
    name = op.attrs.get("langfuse.trace.name")
    if name is not None:                   # `_meta()` 를 안 지나는 키다. 여기서 본다.
        op.attrs["langfuse.trace.name"] = _label("trace_name", name, "nara")
    usage = op.attrs.get("langfuse.observation.usage_details")
    if usage is not None:
        numbers = json.loads(usage) if isinstance(usage, str) else usage
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool)
                   for v in numbers.values()):
            op.attrs.pop("langfuse.observation.usage_details")
    return op


_FIXED_STATUS = ("no model_call_finished", "unfinished: tail stopped",
                 "루트 span 이 없어")


def _scope(event: dict) -> tuple:
    """군·표본을 포함한 범위. 이 값이 span key 에 들어가야 두 군이 겹치지 않는다.

    **key 도 출구다** — `run()` 이 이름이 없으면 key 로 span 이름을 만들고, orphan 경로는
    key 를 metadata 에 적는다. 그래서 여기서 위생한다. 같은 함수를 쓰므로 `state.inputs`
    조회 키와 span key 가 어긋나지 않는다.
    """
    arm, sample = event.get("arm"), event.get("sample")
    return (_clean("arm", arm), _clean("sample", sample))


def _notice(event: dict) -> Optional[str]:
    """span key·이름에 쓰는 공고 id. 위생을 지나지 않은 id 는 key 로도 안 쓴다."""
    return _clean("id", event.get("id"))


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
    # 생산자가 실제로 내는 값 전부. `split` 은 분할 재시도가 일어났다는 **핵심 관측값**인데
    # 손으로 적어 빠뜨렸다(라운드 6 P1). 아래 검사가 `script.py` 를 훑어 드리프트를 잡는다.
    "status": frozenset(("valid", "invalid", "split", "complete", "incomplete", "failed",
                         "ok", "returned", "ambiguous", "response_count_mismatch")),
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
    "truncated", "quant", "seed", "chunk", "call_key"))
_TOKEN_LISTS = frozenset(("ids", "indices", "dev_ids", "order", "arms", "argv"))
# **순수 숫자 버전만** 평문으로 둔다. 각 묶음은 세 자리까지다 — 길이를 안 막으면
# `010.1234.5678` 같은 전화번호나 긴 숫자 비밀이 통과한다(라운드 7 P0).
# 어느 vLLM 으로 돌았는지는 회차 판정의 근거이므로 이 자리는 요약하지 않는다.
VERSION = re.compile(r"^\d{1,3}(\.\d{1,3}){0,3}([+\-][A-Za-z][A-Za-z0-9]{0,11})?$")
DEVICE = re.compile(r"^[A-Za-z0-9 _.\-]{1,64}$")     # "NVIDIA A100-SXM4-40GB"
_VERSIONS = frozenset(("vllm", "python", "cuda", "torch", "transformers", "xgrammar",
                       "tokenizers", "platform", "quant", "revision"))
_DEVICES = frozenset(("name",))
_DIGESTED = frozenset(("sampling_params",))          # 본문 대신 hash 로 요약한다
# `arm`·`sample`·`phase`·`error_type` 은 `_producer_enums()` 가 생산자에서 읽은 집합으로
# 대조한다. 모양만 보면 그 자리에 토큰형 비밀이 통과한다(라운드 7 P0).
# trace 이름은 `nara <mode> <code7>` 로 조립된다. 조각은 이미 위생을 지났다.
TRACE_NAME = re.compile(r"^nara [A-Za-z0-9_\-:]{1,64}( [0-9a-f]{0,7})?$")
# 공고 id 모양. 회차가 id 집합을 선언하지 않은 옛 판형에서만 쓰는 최후 관문이다.
NOTICE = re.compile(r"^PPS-[A-Za-z0-9\-]{1,24}$")
# `plan()` 이 세우는 회차 문맥. 진입점이 하나이므로 여기서 한 번 세운다.
_CONTEXT: dict = {}
_HASH_MAPS = frozenset(("sha256",))                  # {제공 자료 이름: hash}
# 제공 자료 이름. 경로 구분자는 허용하지만 드라이브 문자(`C:`)와 상대 상승(`..`)은 막는다.
ASSET_NAME = re.compile(r"^(?!.*\.\.)(?![A-Za-z]:)[\w가-힣 ._\-/]{1,96}$")
_VERSION_MAPS = frozenset(("packages",))             # {패키지: 버전}
# 생산자가 실제로 만드는 키. **실측이다** — H4 회차 로그에서 읽었고 검사가 드리프트를 잡는다.
# 경로 키(input·output·data_dir·model_dir)는 뺐다. 생산자가 `record_path` 로 치환하지만
# 사이드카가 다시 내보낼 이유가 없다.
_DICT_KEYS = {
    "settings": frozenset((
        "chunk", "limit", "max_chars", "max_model_len", "max_tokens", "temperature", "thinking",
        "debug_responses", "seed", "quant", "tp", "gpu_mem", "prompt_language", "sme_facts",
        "sme_items", "sme_selection", "extra_call_items", "company_size_items", "split_items",
        "product_items", "company_size_document_checks", "company_size_clause_quotes",
        "company_size_qualification_role", "prompt_budget", "output_reserved", "episode")),
    "environment": frozenset(("vllm", "python", "cuda", "gpus", "chat_template_sha256",
                              "sampling_params")),
    "expected_model": frozenset(("id", "revision")),
    "gpus": frozenset(("name", "total_memory")),
}
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


def _known_packages() -> frozenset:
    """`script.py` 가 버전을 세는 패키지 이름. 그 dict 의 키는 이것뿐이다."""
    source = (ROOT/"script.py").read_text(encoding="utf-8")
    found = re.search(r'for name in \(([^)]*)\):\s*\n\s*try:\s*\n\s*packages\[name\]', source)
    names = re.findall(r'"([A-Za-z0-9_.\-]+)"', found[1]) if found else []
    return frozenset(names) or frozenset(("vllm", "torch", "transformers", "xgrammar",
                                          "tokenizers"))


def _dev_ids() -> frozenset:
    """고정 공개 dev 의 공고 id 집합. 없으면 빈 집합이고, 그러면 id 는 요약으로 나간다."""
    path = ROOT/"open/dev.jsonl"
    if not path.is_file():
        return frozenset()
    return frozenset(json.loads(line)["id"]
                     for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _known_items() -> frozenset:
    """제품이 쓰는 항목 이름 전부. 그 밖의 값은 `items`·`groups` 에 올 수 없다."""
    sys.path.insert(0, str(ROOT))
    import script
    return frozenset(script.ITEMS) | frozenset(script.COMPANY_SIZE_KEYS) | frozenset(script.SME_ITEMS)


def _known_strings() -> frozenset:
    """생산자가 상수로 들고 있어 그대로 내보내도 되는 문자열.

    `QUANT` 처럼 평가 서버 설정을 그대로 적는 값은 읽혀야 한다 — 요약하면
    어느 설정으로 돌았는지 확인할 수 없다. 대신 **상수와 같을 때만** 평문이다.
    """
    sys.path.insert(0, str(ROOT))
    import script
    return frozenset((script.MODEL_ID, script.MODEL_REVISION, script.QUANT))


def _producer_enums() -> dict:
    """평문으로 나가는 값의 집합을 **생산자에서 읽는다.**

    집합을 손으로 적으면 안 된다 — `mock` 을 빼서 mock 회차의 trace 이름이 깨졌고
    (라운드 5), `split` 을 빼서 분할 재시도 관측이 사라졌다(라운드 6).
    그리고 **패턴으로 두면 그 자리에 비밀이 통과한다** — `phase="sk-live-secret123"` ·
    `error_type="SecretTokenABC123"` 이 평문으로 나갔다(라운드 7 P0).
    모양이 값을 증명한다고 볼 수 있는 것은 hash 뿐이다. 나머지는 대조한다.
    """
    sys.path.insert(0, str(ROOT))
    import script
    runners = [getattr(script, name) for name in dir(script)
               if isinstance(getattr(script, name, None), type)
               and hasattr(getattr(script, name), "MODE")]
    modes = {runner.MODE for runner in runners} | {"pending", "test_double", "?"}
    counts = {getattr(runner, "TOKEN_COUNT", None) for runner in runners}
    counts = {value for value in counts if value} | {"test_double", "estimate"}
    experiments = {"h3", "v18", "a8", "control"}
    try:                                   # 후보 실행기도 같은 두 상수를 들고 있다
        from experiments import a8_v20_annex, a5_scope_pilot
        modes.add(a8_v20_annex.TokenizerRunner.MODE)
        counts.add(a8_v20_annex.TokenizerRunner.TOKEN_COUNT)
        experiments |= set(a5_scope_pilot.DEV_ONLY) | {"h3", "control"}
    except Exception:
        pass
    # 예외 클래스 이름은 빌트인에서 읽는다. 모양(CamelCase)만 보면 비밀이 통과한다.
    import builtins
    errors = {name for name in dir(builtins)
              if isinstance(getattr(builtins, name, None), type)
              and issubclass(getattr(builtins, name), BaseException)}
    return {"mode": frozenset(modes), "token_count_kind": frozenset(counts),
            "arm": frozenset(experiments), "experiment": frozenset(experiments),
            "sample": frozenset(("dev", "unlabeled")),
            "phase": frozenset(("baseline", "company_size", "product", "sme", "split")),
            "error_type": frozenset(errors)}


def _summary(value: str) -> str:
    """평문 대신 나가는 요약. 동일성·변화는 남고 값은 안 나간다."""
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _clean_str(name: str, value: str, nested: bool) -> Optional[str]:
    """문자열은 **모양만으로 통과시키지 않는다.** 자유 텍스트가 올 수 있는 자리다.

    기본이 **요약**이다. 알려진 값(생산자에서 읽은 enum·생산자 상수·hash·항목명·
    좁은 식별자)만 평문으로 나가고, 그 밖의 문자열은 hash 로 줄인다.

    왜 패턴으로는 안 되나. 버전 자리에 `sk-live-secret123` 을 넣으면 **값만 보고
    그것이 버전인지 비밀인지 구분할 방법이 없다.** 라운드 5·6 에서 나는 그 구분
    불가능을 "그러니 평문으로 보낸다" 의 근거로 썼는데, 그것이 라운드 6 P0 였다 —
    구분할 수 없으면 **평문을 안 보내는 쪽**이 답이다.

    중첩 안에서는 최상위 규칙(`_FREE`·enum)을 다시 쓰지 않는다 —
    `settings={"error_message": "C:/..."}` 가 본문 게이트를 그렇게 우회했다(라운드 5 P0).
    """
    if name.endswith("_sha256"):
        return value if HEX.match(value) else None
    produced = _producer_enums()
    if name in produced:                             # 생산자에서 읽은 집합이 먼저다
        return value if value in produced[name] else _summary(value)
    if not nested:
        if name in _FREE:                            # `_detail()` 이 이미 게이트를 걸었다
            return value
        if name in _ENUMS:
            return value if value in _ENUMS[name] else _summary(value)
    if value in _known_strings():                    # 모델 id·리비전 같은 생산자 상수
        return value
    if name in _ENUMS:                               # 중첩이라도 값 집합은 통과시킨다
        return value if value in _ENUMS[name] else _summary(value)
    if name in _ITEM_LISTS:
        return value if value in _known_items() else _summary(value)
    if name == "id":
        # 공고 id 는 **그 회차가 선언한 집합**과 대조한다. 패턴만 보면 그 자리에
        # 임의 토큰이 통과한다(라운드 7 P0). 고정 dev 집합으로 대조하면 제출 입력으로
        # 돈 회차(`test.jsonl.gz`)의 id 가 전부 요약돼 관측이 못 쓰게 되므로,
        # `run_started.dev_ids` 를 기준으로 쓴다. 그 값이 실제 파일과 맞는지는 1층이 본다.
        # 그 선언이 없는 옛 판형 로그는 공고 id 모양으로 떨어진다.
        declared = _CONTEXT.get("ids") or frozenset()
        if declared:
            return value if value in declared else _summary(value)
        return value if NOTICE.match(value) else _summary(value)
    if name == "trace_name":
        return value if TRACE_NAME.match(value) else "nara " + _summary(value)
    if name in _VERSIONS:
        return value if VERSION.match(value) else _summary(value)
    if name in _TOKENS or name in _TOKEN_LISTS or name in _DEVICES:
        return _summary(value)                       # 장비명·그 밖의 알려진 이름
    if name in _DIGESTED:
        return _summary(value)
    return None                                      # 모르는 이름은 아예 안 내보낸다


def _clean(name: str, value: Any, *, nested: bool = False, _depth: int = 0) -> Any:
    """이 값이 생산자가 만드는 모양인지 본다. 아니면 버린다(None).

    타입이 먼저다 — 수치·bool 은 자유 텍스트가 아니므로 이름 규칙 없이 통과한다.
    그래서 `settings.max_model_len` 처럼 **생산자가 실제로 내는 숫자가 사라지지 않는다**
    (라운드 5 P1: 허용 목록 방식이 진짜 값을 다수 지웠다).
    문자열만 `_clean_str()` 로 제한하고, 컨테이너는 부모별 허용 키를 따라 내려간다.

    기준은 추측이 아니라 **실측**이다 — H4 실제 회차 로그와 mock A8 회차 로그의
    이벤트 형태로 검사가 고정한다.
    """
    if value is None or _depth > 4:
        return None
    if isinstance(value, bool) or isinstance(value, (int, float)):
        # 수치 자리에 문자열이 오면 위에서 str 분기로 떨어진다. 그 반대는 막지 않는다.
        return value
    if isinstance(value, str):
        if name in _NUMERIC:                         # 수치 자리의 문자열은 생산자가 안 만든다
            return None
        return _clean_str(name, value, nested)
    if isinstance(value, list):
        if name in _ITEM_LISTS:                      # 항목 목록은 고정 집합이다
            flat = [i for e in value for i in (e if isinstance(e, list) else [e])]
            known = _known_items()                   # set() 으로 안 묶는다 — 중첩에서 터진다
            if flat and all(isinstance(i, str) and i in known for i in flat):
                return value
            # `groups` 는 dict 목록으로도 온다(`script.py:1001`). 그 경로로 내려간다.
            if not all(isinstance(e, dict) for e in value):
                return None
        kept = [_clean(name, item, nested=True, _depth=_depth + 1) for item in value]
        kept = [item for item in kept if item is not None]
        return kept or None
    if isinstance(value, dict):
        allowed = _DICT_KEYS.get(name)
        items, kept = _known_items(), {}
        for key, inner in value.items():
            if allowed is not None and key not in allowed:
                continue                             # 부모가 만들지 않는 키는 안 내보낸다
            if key in items:                         # 항목별 판정·기각 사유
                if isinstance(inner, bool) or isinstance(inner, int):
                    kept[key] = inner
                elif isinstance(inner, list) and all(
                        isinstance(reason, str) and reason in REJECTION_REASONS
                        for reason in inner):
                    # `set(inner)` 로 쓰면 중첩 list·dict 에서 TypeError 로 사이드카가
                    # 멈춘다(라운드 6 P0). 게이트는 fail-closed 여야 한다 —
                    # 오염된 값은 버리고 회차는 계속 투영한다.
                    kept[key] = inner
                continue
            if name in _HASH_MAPS:                   # {파일명: hash}
                # **키도 이벤트에서 온다.** 값만 보면 키에 개인 경로가 남는다(라운드 7 P0).
                # 제공 자료 이름은 고정 목록이 아니므로 모양을 좁히고, 아니면 요약한다.
                if isinstance(inner, str) and HEX.match(inner):
                    kept[key if ASSET_NAME.match(key) else _summary(key)] = inner
                continue
            if name in _VERSION_MAPS:                # {패키지: 버전}
                # 패키지 이름은 `script.py` 가 세는 고정 목록이다 — 그것과 대조한다.
                if isinstance(inner, str) and VERSION.match(inner):
                    kept[key if key in _known_packages() else _summary(key)] = inner
                continue
            clean = _clean(key, inner, nested=True, _depth=_depth + 1)
            if clean is not None:
                kept[key] = clean
        return kept or None
    return None                                      # 모르는 모양은 안 내보낸다


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
    """이벤트 하나를 span 지시로 바꾼다. **나가는 모든 Op 가 `guard()` 를 지난다.**

    이 한 줄이 라운드 1~5 의 반복을 끝내는 자리다 — 어느 분기가 무엇을 넣어도
    출구는 하나다. 자세한 이유는 `guard()` 의 주석에 있다.
    """
    _CONTEXT["ids"] = state.notice_ids
    return [guard(op) for op in _plan(event, state)]


def _plan(event: dict, state: State) -> list:
    """이벤트 하나를 span 지시로 바꾼다. 여기까지가 순수 함수다."""
    kind = event.get("event")
    now = float(event.get("time_unix") or state.last or time.time())
    state.last = now
    # phase 도 key 조립에 들어간다. 위생을 지난 값만 쓴다.
    phase = _clean("phase", event.get("phase")) or state.phase
    ops: list = []

    if kind == "run_started":
        state.run = "run"
        state.capture_protocol = event.get("capture_protocol")
        declared = event.get("dev_ids")
        if isinstance(declared, list):
            state.notice_ids = frozenset(i for i in declared if isinstance(i, str))
        # 이름도 수출이다 — 위생을 지난 값으로만 만든다.
        state.model = _label("id", (event.get("expected_model") or {}).get("id"),
                             MODEL_FALLBACK)
        mode = _label("mode", event.get("mode", "?"))
        state.code = _label("code_sha256", event.get("code_sha256"), "")[:7]
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
        # `run_started` 쪽만 위생하고 여기를 잊었다 — 그래서 trace 이름이 오염됐다(라운드 6 P0).
        mode = _clean("mode", event.get("mode"))
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
        identifier = _notice(event)
        state.inputs[(arm, sample, identifier)] = event
        return [Op("point", f"input:{arm}:{sample}:{identifier}", str(identifier),
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
        source = state.inputs.get((*_scope(event), _notice(event)))
        if source is not None:
            attrs.update(_meta(max_chars=source.get("max_chars"),
                               token_count_kind=source.get("token_count_kind")))
        _body(state, attrs, "input", event.get("prompt_text"))
        return [Op("open", key, str(_notice(event) or event.get("call_index")), "generation",
                   state.chunk or state.arm or "run", now, attrs=attrs)]

    if kind in ("model_call_finished", "model_call_failed"):
        key = _call_key(event)
        if key not in state.calls:             # 시작 없는 종료는 관측 계약 실패다. 꾸며 넣지 않는다.
            return [Op("point", f"orphan:{key}:{now}", "orphan model call", "event",
                       state.arm or "run", now, now, level="ERROR",
                       # `_fixed()` 는 이 파일이 만든 문구 전용이다. key 는 이벤트에서
                       # 조립되므로 여기 넣으면 계약이 깨진다(라운드 6 P0).
                       attrs={**_meta(call_key=key),
                              **_meta(transport_status=event.get("transport_status"))})]
        state.calls.pop(key, None)
        failed = kind == "model_call_failed"
        # 덧셈 전에 위생한다 — 문자열이 오면 `total` 이 이어붙거나 크래시한다(라운드 5 P0).
        prompt_tokens = _clean("prompt_tokens", event.get("prompt_tokens"))
        output_tokens = _clean("output_tokens", event.get("output_tokens"))
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
                   f"parse {_notice(event) or event.get('global_index')}", "event",
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
        prompt_tokens = _clean("prompt_tokens", event.get("prompt_tokens"))
        output_tokens = _clean("output_tokens", event.get("output_tokens"))
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
        # `guard()` 가 usage 를 사후에 걷지만, 덧셈 자체가 크래시하면 늦다.
        _body(state, attrs, "output", event.get("response_text"))
        return [Op("point", f"gen:{phase}:{event.get('global_index')}:{attempt}",
                   str(_notice(event) or event.get("global_index")), "generation",
                   state.chunk or "run", state.chunk_start or now, now, attrs=attrs,
                   level=None if ok else "ERROR",
                   status="" if ok else _status(state, event))]

    if kind in ("batch_failed", "retry_failed", "sme_fallback"):
        label = _notice(event) or event.get("chunk_start")
        return [Op("point",
                   f"{kind}:{phase}:{event.get('global_index')}:{event.get('attempt')}:{now}",
                   f"{kind} {label}", "event", state.chunk or "run", now, now,
                   attrs=_meta(phase=phase, stage=event.get("stage"), attempt=event.get("attempt"),
                               source=event.get("source"), global_index=event.get("global_index")),
                   level="WARNING" if kind == "sme_fallback" else "ERROR",
                   status=_status(state, event))]

    if kind == "sme_verified":
        return [Op("point", f"verify:{_notice(event)}", f"verify {_notice(event)}", "event",
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
                # `plan()` 을 안 지나는 네 속성도 같은 통로를 지난다 — 여기가
                # `guard()` 밖의 출구였다(라운드 6 P0). trace 이름은 이벤트 유래다.
                span.set_attribute("langfuse.trace.name", _label("trace_name", state.trace_name))
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
