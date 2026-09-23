"""B6 후보 — v9 `V9_EQUIVALENT` 를 운영진 답(S7-4·14)에 맞춰 다시 잰다.

모델 뒤 단계만 바꾼다. `tools/replay_run.py --candidate` 로 갈아 끼운다. GPU 를 쓰지 않는다.
가설은 환경변수 `B6_MODE` 로 고른다 — 한 회차에 하나씩 잰다.

- `off` : `V9_EQUIVALENT` 만 끈다. 기준 비교용(착수서의 "끔" 행).
- `h2`  : 동등품 문구를 근거 앞뒤 300자가 아니라 **근거가 든 문장** 안에서만 찾는다.
- `h1`  : `V9_EQUIVALENT` 를 빼고 판정 단위를 인용에서 문서로 바꾼다. 모델이 v9=1 을 낸 공고의
          `docs` 전부에서 모델 지정 줄을 찾아, 있으면 v9=1 을 두고(인용이 지정 줄이 아니면 e9 를
          그 줄로 바꾼다) 어디에도 없을 때만 내린다. 첨부가 입력에서 빠진 공고는 내리지 않는다.

지정 줄의 꼴은 `reports/team-b/b6-v9-equivalent/README.md` 의 표가 소유한다. 표에 없는 꼴을 넣지 않는다.

재생:
    B6_MODE=h1 python -X utf8 tools/replay_run.py --case reports/runs/colab-1789902969401579900/dev-debug \\
      --candidate experiments/b6_v9_candidate.py --output-dir <새 경로>
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MODES = ("off", "h1", "h2")

# 머리말 꼴 — 제조사·모델·형식·품번 뒤의 값. 글자 사이 공백을 허용한다(`모 델 :`).
_SP = r"\s*"
HEADER = re.compile(
    r"(?P<pre>제안|입찰자|응찰)?" + _SP
    + r"(?:제" + _SP + r"조" + _SP + r"(?:사|회" + _SP + r"사)"
    + r"(?:" + _SP + r"[·ㆍ/및]" + _SP + r"모" + _SP + r"델(?:" + _SP + r"명)?)?"
    + r"|모" + _SP + r"델(?:" + _SP + r"명)?"
    + r"|형" + _SP + r"식(?:" + _SP + r"명)?"
    + r"|품" + _SP + r"번)"
    + _SP + r"[:：]" + _SP + r"(?P<value>.*)")
PLACEHOLDER = re.compile(r"^[\s_.\-·()]*$|^\(?\s*(?:기재|작성|제안|별도|참조|해당\s*없음)\s*\)?$")
# 브랜드 + 제품 식별자 — 라틴+숫자 한 토큰, 또는 라틴 낱말 뒤 숫자 토큰.
# 숫자로 시작하는 토큰(`128GB`·`40mm`)은 단위라 세지 않는다. 라틴 낱말 뒤 숫자가 한글에 붙으면
# (`Maxwell 7칩`) 개수이지 식별자가 아니다.
# ponytail: 문맥(구매 대상인가)을 안 본다 — `Windows 11`·`DDR5` 도 식별자로 센다. H1 은 그만큼 덜 내린다.
IDENT = re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z][A-Za-z\-]*\d[A-Za-z0-9\-]*"
                   r"|[A-Za-z][A-Za-z\-]+\s+\d[A-Za-z0-9\-.]*(?![0-9가-힣]))")
# 인증·등급·규격 표기는 식별자로 세지 않는다.
NOT_IDENT = re.compile(r"^(?:EAL\d|Tier-?\d|IP\d\d)", re.IGNORECASE)
NOT_IDENT_BEFORE = re.compile(r"(?:인증|등급|규격|표준|KS|ISO)\s*\S{0,3}$")
SPEC_FLOOR = re.compile(r"이상\s*$")
# 운영 `script.py` 에서 뺀 동등품 정규식의 사본. H2 측정을 재현하려고만 둔다.
# 측정은 그것이 운영에 있던 `4dbe0ce` 기준이다 — 지금 HEAD 에서 `off` 는 HEAD 와 같다.
V9_EQUIVALENT = re.compile(r"동등|이상의?\s*(?:제품|성능|사양)|또는\s*그\s*이상")
SENTENCE_END = re.compile(r"\n|(?<=[.。])\s")


def baseline():
    """재생기가 읽은 제출 코드를 집는다. 단독 import 면 저장소 루트의 것을 읽는다."""
    submitted = sys.modules.get("submission")
    if submitted is not None:
        return submitted
    import importlib.util
    spec = importlib.util.spec_from_file_location("baseline_script", ROOT / "script.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mode() -> str:
    value = os.environ.get("B6_MODE", "")
    if value not in MODES:
        raise ValueError(f"B6_MODE 는 {MODES} 중 하나여야 한다: {value!r}")
    return value


# 익명화 토큰(`[지역:r1|…]` 의 `r1`)과 주소(`g2b.go.kr`)는 제품 식별자가 아니다. 지우고 본다.
MASKED = re.compile(r"\[[^\]]*\]|https?://\S+|\b[\w.-]+\.(?:go|or|co)\.kr\S*")


def _has_ident(line: str) -> bool:
    line = MASKED.sub(" ", line)
    for m in IDENT.finditer(line):
        if NOT_IDENT.match(m.group(0)):
            continue
        if NOT_IDENT_BEFORE.search(line[max(0, m.start() - 10):m.start()]):
            continue
        return True
    return False


def designation_kind(line: str) -> Optional[str]:
    """줄이 모델 지정이면 꼴 이름(`header`·`ident`), 아니면 None. 판정 표를 그대로 옮긴다."""
    line = line.strip()
    if not line or SPEC_FLOOR.search(line):
        return None
    header = HEADER.search(line)
    if header and not header.group("pre"):
        value = header.group("value").strip()
        if value and not PLACEHOLDER.match(value):
            return "header"
    if _has_ident(line):
        return "ident"
    return None


def find_designation(rec: Dict[str, Any]) -> Optional[str]:
    """문서 전체에서 첫 머리말 지정 줄. 문서 종류로 좁히지 않는다.

    식별자 꼴은 문서 탐색에 쓰지 않는다. 라벨 없이 dev 200건을 세면 식별자 꼴은 171건,
    머리말 꼴은 17건에서 선다(`G2B`·공고번호·규격 토큰). 기저율 3% 항목에서 171/200 은
    아무것도 가르지 않는다. 식별자 꼴은 모델 인용 — 이미 구매 대상 줄을 가리킨 것 — 을 볼 때만 쓴다."""
    for doc in rec["docs"]:
        for line in doc["text"].split("\n"):
            if designation_kind(line) == "header":
                return line.strip()
    return None


def sentence_around(text: str, at: int, length: int) -> str:
    starts = [m.end() for m in SENTENCE_END.finditer(text, 0, at)]
    start = starts[-1] if starts else 0
    end_match = SENTENCE_END.search(text, at + length)
    return text[start:end_match.start() if end_match else len(text)]


def _h2_refutes(base, evidence: str, rec: Dict[str, Any]) -> bool:
    if base.V9_SPEC_FLOOR.search(evidence):
        return True
    for doc in rec["docs"]:
        at = doc["text"].find(evidence)
        if at >= 0:
            return bool(V9_EQUIVALENT.search(sentence_around(doc["text"], at, len(evidence))))
    return False


def _verified(base, quote, rec) -> str:
    for doc in rec["docs"]:
        ev = base.clean_evidence(quote, doc["text"])
        if ev:
            return ev
    return ""


def postprocess(judgment: Dict[str, Dict[str, Any]], rec: Dict[str, Any]):
    base = baseline()
    chosen = mode()
    original_refutes = base.evidence_refutes

    def refutes(item, evidence, record):
        if item != "v9":
            return original_refutes(item, evidence, record)
        if chosen == "off":
            return bool(evidence) and bool(base.V9_SPEC_FLOOR.search(evidence))
        if chosen == "h2":
            return bool(evidence) and _h2_refutes(base, evidence, record)
        return False                                    # h1 은 아래에서 문서 단위로 판정한다

    base.evidence_refutes = refutes
    try:
        out = base.postprocess(judgment, rec)
    finally:
        base.evidence_refutes = original_refutes
    if chosen != "h1" or (judgment.get("v9") or {}).get("위반여부") != 1:
        return out
    quote = _verified(base, (judgment.get("v9") or {}).get("근거문구"), rec)
    if quote and designation_kind(quote):
        out["v9"] = {"위반여부": 1, "근거문구": quote}
        return out
    found = find_designation(rec)
    if found:
        ev = _verified(base, found, rec)
        out["v9"] = {"위반여부": 1, "근거문구": ev or quote}
        if not out["v9"]["근거문구"]:
            out["v9"] = {"위반여부": 0, "근거문구": ""}   # 근거 계약: 인용 없는 위반은 서지 않는다
        return out
    if rec.get("dropped_doc_counts"):
        return out                                      # 없는 것은 반증이 아니다 — 기존 판정을 둔다
    out["v9"] = {"위반여부": 0, "근거문구": ""}
    return out
