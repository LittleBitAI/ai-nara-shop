"""C3 후보 — 부재탐지 금액 게이트.

모델 뒤 단계만 바꾼다. `tools/replay_run.py --candidate` 로 갈아 끼우거나
`tests/test_sme_candidate.py` 가 직접 부른다. GPU 를 쓰지 않는다.

하는 일은 하나뿐이다. 기본 `postprocess` 결과에서 v16·v18 의 위반=1 을
`meta.입찰추정가격` 이 그 항목의 조문 금액 구간 밖이면 0 으로 되돌린다.
근거문구는 건드리지 않는다 — 부재탐지 항목은 원래 빈칸이다.

금액 구간의 근거는 제공 법령 스냅샷이며 `reports/team-c/c3-amount-gate/README.md`
가 조문 위치를 적는다. 분포에 맞춘 값이 아니다.

v20 은 게이트를 넣지 않는다. SW 지침 별표1 의 사업금액 하한은 20억·40억·80억뿐이고
dev 양성 5건 중 3건이 20억 미만이라 하한만으로 라벨이 설명되지 않는다. C7 에서 다룬다.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]

# 「국가를 당사자로 하는 계약에 관한 법률」 제4조제1항 고시금액 (물품 및 용역, WTO 정부조달협정).
NOTICE_AMOUNT_WON = 230_000_000
# 국가 시행령 제21조①10호 가목/나목, 지방 시행령 제20조①12호 가목/나목의 경계.
SME_BAND_FLOOR_WON = 100_000_000

# 항목 → (하한 포함, 상한 미포함). None 은 경계 없음.
AMOUNT_BANDS: dict[str, tuple] = {
    # v16: 1억 이상 - 고시금액미만 중소기업 제한 없음
    "v16": (SME_BAND_FLOOR_WON, NOTICE_AMOUNT_WON),
    # v18: 1억원 미만 일반물품 소기업 제한 없음
    "v18": (None, SME_BAND_FLOOR_WON),
}


def _load_script():
    spec = importlib.util.spec_from_file_location("baseline_script", REPO / "script.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_SCRIPT = None


def baseline():
    """제출 코드를 한 번만 읽어 돌려준다.

    replay_run 이 `--script` 로 다른 제출 코드를 넘겼으면 그것을 쓴다. 저장소 루트를
    고집하면 파싱은 넘긴 코드로, postprocess 는 워킹트리 코드로 갈라지고 manifest 에
    그 불일치가 남지 않는다. 단독으로 import 될 때만 루트의 script.py 를 읽는다.
    """
    submitted = sys.modules.get("submission")
    if submitted is not None:
        return submitted  # 캐시하지 않는다 — main() 이 다시 돌면 새 모듈로 바뀐다
    global _SCRIPT
    if _SCRIPT is None:
        _SCRIPT = _load_script()
    return _SCRIPT


def estimated_price(rec: dict[str, Any]) -> int | None:
    """meta.입찰추정가격 을 정수 원 단위로 읽는다. 읽히지 않으면 None."""
    raw = (rec.get("meta") or {}).get("입찰추정가격")
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    text = str(raw).strip().replace(",", "")
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def in_band(item: str, price: int | None) -> bool:
    """항목의 금액 구간 안인가. 금액을 못 읽으면 거르지 않는다(참으로 본다)."""
    band = AMOUNT_BANDS.get(item)
    if band is None or price is None:
        return True
    low, high = band
    above_floor = low is None or price >= low
    below_ceiling = high is None or price < high
    return above_floor and below_ceiling


def apply_amount_gate(judgment: dict[str, dict[str, Any]],
                      rec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """후처리된 판정에 금액 게이트를 씌운다. 입력을 바꾸지 않고 새 사전을 돌려준다."""
    price = estimated_price(rec)
    out: dict[str, dict[str, Any]] = {}
    for item, cell in judgment.items():
        cell = dict(cell)
        if item in AMOUNT_BANDS and cell.get("위반여부") == 1 and not in_band(item, price):
            cell["위반여부"] = 0
            cell["근거문구"] = ""
        out[item] = cell
    return out


def postprocess(judgment: dict[str, dict[str, Any]],
                rec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """기본 후처리 그대로 한 뒤 금액 게이트만 덧씌운다."""
    return apply_amount_gate(baseline().postprocess(judgment, rec), rec)
