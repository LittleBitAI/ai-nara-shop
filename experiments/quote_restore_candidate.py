"""후처리 후보 — 모델 인용의 공백·줄바꿈 차이만 원문 위치로 되돌린다 (가설 B).

모델 뒤 단계만 바꾼다. `tools/replay_run.py --candidate` 로 갈아 끼운다. GPU 를 쓰지 않는다.

왜. `verify_company_size` 는 인용이 공고 원문에 **그대로** 있어야 사실을 받아들인다
([data D4-4](../docs/data.md) 가 `e` 를 원문의 연속된 부분문자열로 규정하므로 그 계약이 맞다).
그런데 모델이 그 계약을 **내용이 아니라 표기에서** 놓친다.
[A1 후속 진단](../reports/team-c/a1-company-size/followup-analysis.md)이 v18 미탐 7건의
차단 사유를 세었는데 다섯이 순전히 공백·줄바꿈이었다 — 원문은 `입 찰 방 법`인데
모델은 `입찰 방법`이라 적었고, 인용이 가리키는 자리는 맞는데 문자열이 안 맞아 떨어졌다.

무엇을 한다. 인용에서 **공백만 지운 문자열**이 개별 문서에서 연속으로 일치하면
그 문서의 원래 시작·끝 위치로 되돌린다. 복원한 문자열이 그 공고의 실제
`build_context(rec, max_chars)` 안에도 있어야 승인한다 — 모델이 못 본 자리는 되살리지 않는다.

무엇을 안 한다. **문장부호·낱말·법령 제목은 바꾸지 않는다.** 진단이 `PPS-DEV-040`에서
법령 제목의 `」` 위치까지 달라진 사례를 찾았고 그것은 공백 문제가 아니므로 승인하지 않는다.
후보가 여럿이면 가장 짧은 것 하나만 쓴다 — 긴 것을 고르면 인용이 원래 가리키지 않던
문맥까지 끌고 들어온다.

이 후보는 **판정 로직을 하나도 안 바꾼다.** 복원한 사실을 그대로
`verify_company_size` 에 넘기고 그다음은 제출 코드가 한다.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

REPO = Path(__file__).resolve().parents[1]

# 복원 대상 인용. company_size 사실이 원문 대조를 거는 두 자리다.
QUOTE_KEYS = ("scope_quote", "qualification_quote")

_SPACE = re.compile(r"\s+")


def _load_script():
    spec = importlib.util.spec_from_file_location("baseline_script", REPO / "script.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_SCRIPT = None


def baseline():
    """제출 코드를 한 번만 읽어 돌려준다. replay_run 이 넘긴 것이 있으면 그것을 쓴다."""
    global _SCRIPT
    if _SCRIPT is None:
        _SCRIPT = sys.modules.get("run_submission") or sys.modules.get("submission") or _load_script()
    return _SCRIPT


def restore(quote: str, rec: Dict[str, Any], visible: str) -> Optional[str]:
    """공백만 다른 원문 구간을 찾아 돌려준다. 못 찾거나 이미 맞으면 None.

    공백을 지운 인용이 공백을 지운 문서에서 연속으로 일치할 때만 승인한다. 그 일치
    구간을 원문 좌표로 되돌리려고 문서의 비공백 문자마다 원래 위치를 들고 있는다.
    """
    flat_quote = _SPACE.sub("", quote or "")
    if len(flat_quote) < 8:
        return None                              # 너무 짧으면 아무 데나 걸린다
    best = None
    for doc in rec["docs"]:
        text = doc["text"]
        if quote in text:
            return None                          # 이미 원문 그대로다. 손대지 않는다
        flat, where = [], []
        for i, ch in enumerate(text):
            if not ch.isspace():
                flat.append(ch)
                where.append(i)
        flat = "".join(flat)
        start = flat.find(flat_quote)
        while start != -1:
            candidate = text[where[start]:where[start + len(flat_quote) - 1] + 1]
            # 모델이 실제로 본 문맥 안에 있어야 한다. 잘린 뒤쪽은 되살리지 않는다.
            if candidate in visible and (best is None or len(candidate) < len(best)):
                best = candidate
            start = flat.find(flat_quote, start + 1)
    return best


def verify_company_size(facts: Dict[str, Any], rec: Dict[str, Any], max_chars: int):
    script = baseline()
    visible = script.build_context(rec, max_chars)
    repaired = dict(facts)
    for key in QUOTE_KEYS:
        fixed = restore(repaired.get(key), rec, visible)
        if fixed is not None:
            repaired[key] = fixed
    return script.verify_company_size(repaired, rec, max_chars)


def demo():
    """공백 복원이 되는 자리와 안 되는 자리를 한 번씩 확인한다."""
    rec = {"docs": [{"type": "공고서", "doc_id": "d1",
                     "text": "가. 입 찰 방 법: 제한경쟁입찰\n나. 「중소기업제품 구매촉진법」 제9조"}]}
    visible = rec["docs"][0]["text"]
    assert restore("입찰 방법: 제한경쟁입찰", rec, visible) == "입 찰 방 법: 제한경쟁입찰", "공백 차이는 되돌린다"
    assert restore("제한경쟁입찰로 집행한다", rec, visible) is None, "낱말이 다르면 안 건드린다"
    assert restore("「중소기업제품 구매촉진법」 제9조", rec, visible) is None, "이미 원문 그대로면 안 건드린다"
    assert restore("입찰 방법", rec, visible) is None, "너무 짧으면 안 건드린다"
    far = {"docs": [{"type": "공고서", "doc_id": "d1", "text": "머리말\n" + "가 나 다 라 마 바 사 아 자 차"}]}
    assert restore("가나다라마바사아자차", far, "머리말") is None, "모델이 못 본 자리는 안 되살린다"
    print("demo 통과")


if __name__ == "__main__":
    demo()
