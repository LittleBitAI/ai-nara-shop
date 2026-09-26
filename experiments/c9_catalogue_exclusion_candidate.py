"""C9 — 품목번호가 있는데 경쟁제품 고시에 없으면 중기간 경쟁제품 항목이 아니다.

v10·v11·v13 은 항목명이 전부 "**중기간 경쟁제품** …" 이다(`docs/items.md`).
경쟁제품이 아니면 그 항목이 애초에 안 선다.

공고 메타의 `세부품명번호목록` 과 제공 고시(`open/data`, 616개)를 대조하면 dev 200건이
셋으로 갈린다.

| | 건수 | v10 양성 | v11 양성 | v13 양성 | v12 양성 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 품번이 아예 없다 | 122 | **7** | **6** | **6** | 4 |
| 품번이 있고 고시에 **있다** | 0 | — | — | — | — |
| 품번이 있고 고시에 **없다** | **78** | **0** | **0** | **0** | **2** |

**v10·v11·v13 의 양성은 전부 "품번이 없는" 122건 안에 있다.** 품번이 찍혀 있는데 그것이
경쟁제품 고시에 하나도 안 걸리는 78건에서는 셋 다 양성이 0 이다.

그래서 이 후보는 **그 78건에서만** v10·v11·v13 을 올리지 않는다.

## `script.py:102` 의 경고를 어떻게 피하나

그 주석이 적는다 — "경쟁제품 코드 일치를 적용 게이트로 쓰면 dev 의 v10 양성 7건 중
6건이 사라진다(양성 공고가 전부 일반용역이라 물품 코드가 안 맞는다)".

**그 게이트와 이 게이트는 방향이 반대다.**

| | 조건 | 품번 없는 공고는 |
| --- | --- | --- |
| 주석이 기각한 게이트 | 코드가 고시에 **일치해야** 올린다 | 못 올린다 → 양성 7건 중 6건이 죽는다 |
| **이 후보** | 코드가 있는데 고시에 **없으면** 안 올린다 | **안 건드린다** → 양성 7건이 그대로 산다 |

품번이 아예 없는 공고(일반용역 등)는 이 후보의 대상이 아니다. 대상은 "물품 코드가
찍혀 있는데 그 코드가 경쟁제품이 아닌" 공고뿐이다.

## v12 는 뺀다

같은 78건에 v12 양성이 **2건** 있다. v12 까지 닫으면 TP 를 지운다 — 금지선이다.
v12 는 "중기간 경쟁제품 소기업·소상공인 제한"이 아니라 다른 축이라 같은 논리가 안 선다.

모델을 부르지 않는다. 대회 제공 고시와 공고 메타만 쓴다. 추가 호출 0 · 추가 시간 0초.

재생:
    python -X utf8 tools/replay_run.py \
      --case reports/runs/colab-1790396310565903096/dev-debug \
      --script <기준 커밋의 script.py> \
      --candidate experiments/c9_catalogue_exclusion_candidate.py --output-dir <새 경로>
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 닫는 항목. v12 는 같은 자리에 양성 2건이 있어 뺀다.
ITEMS = ("v10", "v11", "v13")
# 세부품명번호는 10자리다. 운영 `sme_product_lookup()` 이 쓰는 패턴과 같게 둔다.
CODE = re.compile(r"(?<!\d)\d{10}(?!\d)")


def baseline():
    """재생기가 읽은 제출 코드를 집는다. 단독 import 면 저장소 루트의 것을 읽는다."""
    submitted = sys.modules.get("submission")
    if submitted is not None:
        return submitted
    spec = importlib.util.spec_from_file_location("baseline_script", ROOT / "script.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def outside_catalogue(script, rec: dict[str, Any]) -> bool:
    """품번이 찍혀 있는데 그중 어느 것도 경쟁제품이 아닌가.

    품번이 아예 없으면 False 다 — 그 공고는 이 후보의 대상이 아니다.

    판정은 운영 `competitive_product()` 에 그대로 맡긴다. 고시 대조와 `특이사항` 의
    금액 상한까지 그 함수가 이미 본다 — 규칙을 여기 옮겨 적으면 둘이 따로 논다.
    `True`(경쟁제품)와 `None`(판단 불가)은 안 건드리고 `False` 만 대상으로 삼는다.
    """
    listed = CODE.findall(str((rec.get("meta") or {}).get("세부품명번호목록") or ""))
    if not listed:
        return False
    return script.competitive_product(rec, set(listed)) is False


def postprocess(parsed: dict[str, Any], rec: dict[str, Any]):
    """운영 후처리를 낸 뒤, 대상 공고의 세 항목만 0 으로 닫는다.

    후처리 마지막에 둔다 — 앞 단계가 무엇을 올렸든 이 조건이 참이면 경쟁제품 항목이
    아니다. 근거문구는 비운다(판정 0 셀에 근거를 남기지 않는다).
    """
    script = baseline()
    out = script.postprocess(parsed, rec)
    if not outside_catalogue(script, rec):
        return out
    for item in ITEMS:
        cell = out.get(item)
        if cell and cell.get("위반여부") == 1:
            out[item] = {"위반여부": 0, "근거문구": None}
    return out
