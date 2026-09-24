"""C5 후보 B — v11 을 **v10 이 이미 쓰는 부재 신호** 그대로 연다. A 보다 좁다.

후보 A(`c5_v11_scope_gate_candidate.py`)는 "검증된 `scope` 가 경쟁제품" 하나로 열었고,
그러면 **너무 넓다** — 실측 v11 2/3/4 → 5/17/1, F1 0.363636 → 0.357143 로 **내려간다.**
FN 은 셋 줄지만 FP 가 열넷 는다. 버린 카탈로그 조건이 실제로 일을 하고 있었다는 뜻이다.

## 이 후보가 대신 쓰는 조건

`verify_document_requirements()` 가 **v10 에 1 을 쓰는 바로 그 조건**을 쓴다. 그것은
`scope == competitive`(인용 검증) 위에 둘을 더 얹는다.

  · 모델이 `direct_production` 조항의 **부재를 관측**했다 (`direct_production_quote` 가 `null`)
  · 문서가 **완전관측**이다 (절단·결손 표시 없음, `requirements_complete == yes`)

즉 **"경쟁제품 입찰인데 직생 조항이 실제로 없다"** 까지 확인된 자리만 연다. 거기에
기존 게이트의 셋째 조건(`SME_ALLOWED` 부재)을 그대로 곱한다.

**여전히 정규식에 어휘를 더하지 않는다.** `DP_DEMAND` 를 **부재 판정의 전제로 쓰지 않는
것**이 방향이고, 그 자리를 모델이 이미 낸 부재 관측으로 바꾼 것이다 — v10 이 같은 신호로
TP 를 내고 있다.

**올리기만 한다.** 이미 1 인 v11 을 내리지 않고 다른 23항목을 건드리지 않는다.

모델을 부르지 않는다. 추가 호출 0 · 추가 시간 0초.

재생:
    py -X utf8 tools/replay_run.py --case reports/runs/colab-1789902969401579900/dev-debug \
      --script <tmp>/script.py \
      --candidate experiments/c5_v11_absence_signal_candidate.py --output-dir <새 경로>
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ITEM = "v11"
SOURCE_ITEM = "v10"                 # 부재 신호를 빌려 오는 항목
UNVERIFIED = "unverified_scope"


def baseline():
    """재생기가 실은 제출 코드를 집는다. 단독 import 면 저장소 루트의 것을 읽는다."""
    submitted = sys.modules.get("submission")
    if submitted is not None:
        return submitted
    import importlib.util
    spec = importlib.util.spec_from_file_location("baseline_script", ROOT / "script.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def absence_confirmed(script, facts: dict[str, Any], rec: dict[str, Any], visible: str) -> bool:
    """운영 코드가 v10 에 1 을 쓰는가. **그 판단을 그대로 빌린다 — 다시 만들지 않는다.**"""
    cell = script.verify_document_requirements(facts, rec, visible).get(SOURCE_ITEM)
    return bool(cell and cell.get("위반여부") == 1)


def sme_allowed(script, rec: dict[str, Any]) -> bool:
    """참가자격이 중소기업자까지 허용하는가. 기존 게이트의 셋째 조건 그대로다."""
    return bool(script.SME_ALLOWED.search(script.build_context(rec, max_chars=script.PROMPT_BUDGET)))


def verify_company_size(facts: dict[str, Any], rec: dict[str, Any], max_chars: int):
    """운영 판정을 그대로 낸 뒤, 부재가 확인된 자리에서만 v11 을 연다."""
    script = baseline()
    out, reason = script.verify_company_size(facts, rec, max_chars)
    if reason == UNVERIFIED:
        return out, reason
    visible = script.build_context(rec, max_chars)
    already = (out.get(ITEM) or {}).get("위반여부")
    if already != 1 and absence_confirmed(script, facts, rec, visible) and not sme_allowed(script, rec):
        out = dict(out)
        # 부재탐지 — 근거는 항상 빈칸이다(`script.ABSENCE`).
        out[ITEM] = {"위반여부": 1, "근거문구": None}
    return out, reason


def fires(script, facts: dict[str, Any], rec: dict[str, Any], max_chars: int) -> bool:
    """**발화 조건**이 참인가. 셀이 바뀐다는 뜻이 아니다 — 둘을 섞지 않는다."""
    visible = script.build_context(rec, max_chars)
    return absence_confirmed(script, facts, rec, visible) and not sme_allowed(script, rec)
