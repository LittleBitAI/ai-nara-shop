"""후처리 후보 — 근거가 뒷받침하지 않는 양성을 내린다.

모델 뒤 단계만 바꾼다. `tools/replay_run.py --candidate` 로 갈아 끼운다. GPU 를 쓰지 않는다.

둘을 한다. 둘 다 제출 계약과 항목 정의에서 나오고 dev 문자열에서 나오지 않는다.

**① 근거 없는 양성은 0이다.** [data D4-4](../docs/data.md) 가 `e` 를 원문의 연속된
부분문자열로 규정한다. 위반이라면서 공고에서 한 구절도 못 집는 판정은 그 계약을 못 채운다.
부재탐지 5항목은 스키마가 `근거문구` 를 null 로 고정하므로 제외한다 — 그 항목에서
빈칸은 근거 없음이 아니라 규정된 모양이다.

**② v17 은 중소기업 제한이지 소기업 제한이 아니다.** [items](../docs/items.md) 가
v17 을 "1억원 미만 일반물품 **중소기업** 제한", v15 를 "소기업 제한", v18 을
"소기업 제한 **없음**" 으로 가른다. 1억 미만에서 소기업·소상공인으로 제한하는 것은
판로지원법이 예정한 모양이고 v17 위반이 아니다. 인용이 소기업·소상공인만 가리키면 내린다.

**v24 는 ① 에서 뺀다.** 양성 47건 중 26건의 `e24` 가 빈칸이고 그 안에 TP 가 있다
([점수 진단](../reports/team-score-audit/result.md)). v24 는 공고서와 나라장터 등록값의
대조형이라 근거가 한 구절로 안 잡히는 것이 정상이다. 조문 없는 항목에 조문형 계약을 씌우지 않는다.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any, Dict

REPO = Path(__file__).resolve().parents[1]

# 근거 계약을 적용하지 않는 항목.
#  - 부재탐지 5항목: 스키마가 근거문구를 null 로 고정한다 (D4-5).
#  - v24: 대조형이라 한 구절로 안 잡힌다. 빈 근거 양성 안에 TP 가 있다.
EVIDENCE_EXEMPT = ("v10", "v11", "v16", "v18", "v20", "v24")

# v17 인용이 가리키는 기업 등급. 공백·가운뎃점 표기가 제각각이라 지우고 본다.
_STRIP = re.compile(r"[\s·ㆍ・․/／]")


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


def names_only_small_business(quote: str) -> bool:
    """인용이 소기업·소상공인만 가리키는가. '중소기업' 이 있으면 아니다."""
    flat = _STRIP.sub("", quote or "")
    if not flat:
        return False
    return "중소기업" not in flat and ("소기업" in flat or "소상공인" in flat)


def postprocess(judgment: Dict[str, Dict[str, Any]], rec: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out = baseline().postprocess(judgment, rec)
    fixed = {}
    for item, cell in out.items():
        hit, quote = cell["위반여부"], cell["근거문구"]
        if hit == 1 and item not in EVIDENCE_EXEMPT:
            if not (quote or "").strip():
                hit, quote = 0, ""                      # ① 근거가 없다
            elif item == "v17" and names_only_small_business(quote):
                hit, quote = 0, ""                      # ② 소기업 제한은 v17 이 아니다
        fixed[item] = {"위반여부": hit, "근거문구": quote}
    return fixed
