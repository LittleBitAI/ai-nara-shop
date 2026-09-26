"""C9 + C11 — v10 오탐 둘을 서로 다른 축으로 닫는다. GPU 회차가 필요 없다.

둘 다 후처리에서 v10 을 닫지만 **보는 것이 다르고 닿는 공고가 다르다.**

| 후보 | 축 | 보는 것 | dev 에서 닿는 공고 |
| --- | --- | --- | --- |
| `c9_catalogue_exclusion` | 품번이 경쟁제품 고시에 없다 | 메타 `세부품명번호목록` + 제공 고시 | `PPS-DEV-128` |
| `c11_competition_exception` | 발주처가 법정 예외를 적용했다 | 공고문의 시행령 제7조제1항 인용 | `PPS-DEV-23` |

`23` 의 품번 `2513189901` 은 고시에 **있다**(드론). 그래서 C9 는 못 잡는다.
`128` 의 품번 `2510190101` 은 고시에 **없다**. 그래서 C11 은 못 잡는다.
두 축은 겹치지 않는다.

**합은 개별 합보다 크다.** F1 이 비선형이라 같은 항목의 FP 를 둘 닫으면 각각 닫을 때의
이득을 더한 것보다 많이 오른다. 그 수는 검사(`tests/test_c11_competition_exception.py`)가
고정한다 — 여기 적지 않고 측정값을 그쪽이 소유한다.

순서가 갈릴 여지가 없다. 둘 다 `postprocess` 끝에서 **닫기만** 하고, 어느 쪽도 0 을 1 로
만들지 않으며, 한쪽이 닫은 셀을 다른 쪽이 다시 열지 않는다. 그러므로 적용 순서와
무관하게 결과가 같다.

모델을 부르지 않는다. 추가 호출 0 · 추가 시간 0초.

재생:
    python -X utf8 tools/replay_run.py \
      --case reports/runs/colab-1790445336782946136/var-01 \
      --script <기준 커밋의 script.py> \
      --candidate experiments/c11_integrated_candidate.py --output-dir <새 경로>
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CATALOGUE = _load("c9_catalogue_exclusion_candidate",
                  ROOT / "experiments/c9_catalogue_exclusion_candidate.py")
EXCEPTION = _load("c11_competition_exception_candidate",
                  ROOT / "experiments/c11_competition_exception_candidate.py")


def postprocess(parsed: dict[str, Any], rec: dict[str, Any]):
    """운영 후처리를 낸 뒤 두 축을 차례로 적용한다. 둘 다 닫기만 한다."""
    script = EXCEPTION.baseline()
    out = script.postprocess(parsed, rec)
    if CATALOGUE.outside_catalogue(script, rec):
        for item in CATALOGUE.ITEMS:
            cell = out.get(item)
            if cell and cell.get("위반여부") == 1:
                out[item] = {"위반여부": 0, "근거문구": None}
    if EXCEPTION.competition_exception(rec):
        for item in EXCEPTION.ITEMS:
            cell = out.get(item)
            if cell and cell.get("위반여부") == 1:
                out[item] = {"위반여부": 0, "근거문구": None}
    return out
