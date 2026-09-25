"""C6 후보 D2 (넓음) — 직생 요구가 **하나도 없으면** `competitive` 를 밴드에 한해 안 믿는다.

v18 의 FN 6건을 결정표 관문별로 폈더니 **4건(039·040·041·044)이 `outside_general_scope`**
였다. 모델이 `scope=competitive` 라고 했고, 그러면 결정표는 v14~v18 을 전부 0 으로 닫는다.

**제공 고시 카탈로그로는 그 주장을 반박할 수 없다.** dev 에서 `scope=competitive` 로 확정된
79건 중 카탈로그가 `True`/`False` 를 낸 것은 **0건**이다(42건은 직생 요구 문장 자체가 없고
37건은 코드 대조가 미확인이다). 그래서 카탈로그 축은 여기서 닫힌다.

남는 것은 **직생 요구 문장의 부재**다. 운영 코드는 이미 그 반대 방향에 같은 논리를 쓴다 —
`_company_size_bands()` 는 모델이 `general` 이라 해도 *직생 요구가 있고 카탈로그가 경쟁제품이면*
`competitive_by_catalogue` 로 닫는다. 이 후보는 그 대칭이다.

    직생 요구 문장이 공고 어디에도 없으면, `competitive` 라는 모델의 주장을
    **금액·등급 밴드에 한해** 채택하지 않고 결정표를 `general` 로 다시 밟는다.

**scope 자체는 안 건드린다.** `verify_document_requirements()` 의 v10 과
`company_size_products()` 의 v12·v13 은 `scope == "competitive"` 를 소비하므로, scope 를
뒤집으면 그 셋이 함께 죽는다. 그래서 이 후보는 **운영 판정 위에 밴드 다섯 키만** 덮는다.

D1 과 한 줄만 다르다 — `ITEMS`. **왜 둘을 다 재나.** v18 만 여는 것은 "이 자리에서
결정표가 틀렸다"의 최소 판이고, 밴드 다섯을 다 여는 것이 논리적으로 일관된 판이다.
일관된 쪽이 dev 에서 손해라면 그 사실 자체가 기록할 값이다 — 어느 쪽이 맞는지 미리
고르지 않고 **둘 다 재서 적는다.**

**dev 라벨 기반이 아니다.** 판별축은 `direct_production_demand()` — 운영 코드가 이미 쓰는
공고문 관측이다. dev 라벨을 조건으로 읽지 않는다.

완전관측 게이트(`absence_not_observable`)는 **그대로 둔다.** 기각된 접근이고, 여기서
다시 열지 않는다 — `_company_size_bands()` 를 그대로 다시 부르므로 그 게이트도 그대로 선다.

모델을 부르지 않는다. 추가 호출 0 · 추가 시간 0초.

재생:
    python -X utf8 tools/replay_run.py \
      --case reports/runs/colab-1790235508743452453/dev-debug \
      --script <기준 커밋의 script.py> \
      --candidate experiments/c6_band_no_demand_wide_candidate.py --output-dir <새 경로>
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 이 후보가 덮는 키. 넓게 잡는다 — 밴드 다섯 전부다.
ITEMS = ("v14", "v15", "v16", "v17", "v18")
CONTESTED_SCOPE = "competitive"
ASSUMED_SCOPE = "general"
UNVERIFIED = "unverified_scope"


def baseline():
    """재생기가 읽은 제출 코드를 집는다. 단독 import 면 저장소 루트의 것을 읽는다."""
    submitted = sys.modules.get("submission")
    if submitted is not None:
        return submitted
    spec = importlib.util.spec_from_file_location("baseline_script", ROOT / "script.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def demand_absent(script, rec) -> bool:
    """직생 요구 문장이 공고 어디에도 없는가. 운영 코드의 관측을 그대로 읽는다."""
    quote, _codes = script.direct_production_demand(rec)
    return quote is None


def verify_company_size(facts: dict[str, Any], rec: dict[str, Any], max_chars: int):
    """운영 판정을 낸 뒤, 다투는 자리에서만 밴드 키를 `general` 판으로 갈아 끼운다."""
    script = baseline()
    out, reason = script.verify_company_size(facts, rec, max_chars)
    if (reason == UNVERIFIED
            or facts.get("scope") != CONTESTED_SCOPE
            or not demand_absent(script, rec)):
        return out, reason
    # 같은 함수를 scope 만 바꿔 다시 부른다. 규칙을 옮겨 적지 않으므로 운영 결정표가
    # 바뀌면 이 후보도 같이 바뀐다. 반환의 **밴드 키만** 꺼내 쓴다.
    assumed, _assumed_reason = script.verify_company_size(
        dict(facts, scope=ASSUMED_SCOPE), rec, max_chars)
    out = dict(out)
    for item in ITEMS:
        cell = assumed.get(item)
        # **올리기만 한다.** 이미 1 인 셀도, 내리는 방향도 건드리지 않는다.
        if cell and cell.get("위반여부") == 1 and (out.get(item) or {}).get("위반여부") != 1:
            # **셀을 그대로 가져온다 — 근거문구까지.** 여기서 `근거문구: None` 을 쓰면
            # 부재탐지가 아닌 v14·v15·v17 은 근거 계약(#91, 검증된 인용 없는 위반은
            # 내린다)에 걸려 후처리에서 도로 0 이 된다. 첫 판이 그래서 v16·v18 에서만
            # 효과가 보였다. 결정표가 쓰는 근거를 그대로 쓴다.
            out[item] = dict(cell)
    return out, reason
