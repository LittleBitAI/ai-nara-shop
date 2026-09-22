"""A-1 — v13 두 검증 경로의 합성 규칙.

`baseline → 양성만 SME 재검증 → company → 후처리` 순서에서 company 는 v13 을 조건 만족 시
1 로만 쓰고 불충족을 확정 0 으로 쓰지 않는다. 그래서 company 가 침묵하면 앞 단계의 양성이
그대로 남는다. dev 최종 양성 13건 중 4건이 그 경로다(TP 069, FP 03·059·193).

**좁게 잡는다.** company 덮어쓰기를 통째로 없애면 TP 3(077·078·16)을 잃는다.
company 가 competitive 라고 해서 1 로 올리지도 않는다. 이 후보가 하는 일은 하나뿐이다 —
**company 가 검증된 인용으로 scope 를 `general` 이라고 확정했을 때, 그것과 모순되는
앞 단계 v13 양성을 유지하지 않는다.**

근거는 항목 정의다. v13 의 공식 항목명은 "**중기간 경쟁제품** 소기업, 소상공인 제한"이고
(`docs/items.md`), 운영 코드의 `company_size_products()` 도 같은 문장을 근거로 v13 을
`competitive` 에서만 올린다. 그 전제를 **보존 경로에도 같게 적용하는 것**이며 새 판별축이
아니다. 이미 기각된 여섯 축(금액구간·scope·qualification·role·직생언급·인용문장)으로
정탐과 오탐을 가르려는 규칙이 아니다 — 경쟁제품 scope 안에서는 아무것도 가르지 않는다.

검증 게이트는 운영 코드가 쓰는 것을 그대로 쓴다. `_company_size_bands()` 가
`scope == "unknown"` 이거나 `scope_quote` 가 원문에서 확인되지 않으면 `unverified_scope` 를
돌려주므로, 그 경우에는 이 후보도 아무것도 하지 않는다(기본 판정 보존).

모델을 부르지 않는다. 추가 호출 0 · 추가 시간 0초.

재생:
    python -X utf8 tools/replay_run.py --case reports/runs/colab-1789902969401579900/dev-debug \
      --candidate experiments/c_v13_merge_candidate.py --output-dir <새 경로>
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ITEM = "v13"
# v13 이 설 수 있는 scope. 항목명이 그대로 조건이다 — "중기간 경쟁제품".
APPLICABLE_SCOPE = "competitive"
# scope 가 이 값으로 확정되면 v13 은 적용 대상이 아니다.
CONTRADICTING_SCOPE = "general"
# 이 사유일 때는 scope 자체가 미확인이므로 아무것도 하지 않는다.
UNVERIFIED = "unverified_scope"


def baseline():
    """재생기가 읽은 제출 코드를 집는다. 단독 import 면 저장소 루트의 것을 읽는다."""
    submitted = sys.modules.get("submission")
    if submitted is not None:
        return submitted  # 캐시하지 않는다 — main() 이 다시 돌면 새 모듈이 된다
    import importlib.util
    spec = importlib.util.spec_from_file_location("baseline_script", ROOT / "script.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_company_size(facts: dict[str, Any], rec: dict[str, Any], max_chars: int):
    """운영 판정을 그대로 낸 뒤, 모순되는 보존 경로만 닫는다.

    운영 `verify_company_size` 의 반환을 바꾸지 않고 **키 하나를 더할 뿐**이다.
    company 가 이미 v13 을 썼으면(조건 충족) 건드리지 않는다.
    """
    script = baseline()
    out, reason = script.verify_company_size(facts, rec, max_chars)
    if (reason != UNVERIFIED
            and ITEM not in out
            and facts.get("scope") == CONTRADICTING_SCOPE):
        # 검증된 scope 가 general 이다. v13 은 competitive 에서만 서므로 앞 단계 양성을
        # 유지하지 않는다. 근거문구는 후처리가 비운다(판정 0 셀에 근거를 남기지 않는다).
        out = dict(out)
        out[ITEM] = {"위반여부": 0, "근거문구": None}
    return out, reason


def contradicts(facts: dict[str, Any], reason: str, company_wrote_item: bool) -> bool:
    """**적용 대상**인가. 셀이 바뀐다는 뜻이 아니다 — 둘을 섞지 않는다.

    dev 200건에서 이 술어는 **118건**에서 참이고 그중 **1건**(`PPS-DEV-03`)만 판정이 바뀐다.
    나머지 117건은 앞 단계도 이미 0 이라 명시적 0 을 써도 같은 값이다.

    **위험은 넓이가 아니라 겹침에 있다.** 다른 회차에서 이 118건 중 어느 하나에 앞 단계
    양성이 남으면 그것도 닫는다. 그 양성이 TP 일 수 있다. dev 에서는 겹친 1건이 FP 였다.
    """
    return (reason != UNVERIFIED
            and not company_wrote_item
            and facts.get("scope") == CONTRADICTING_SCOPE)
