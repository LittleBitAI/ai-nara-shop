"""C7 + C9 — 대가 없이 세 항목을 올린다. GPU 회차가 필요 없다.

둘은 서로 다른 단계에서 서로 다른 항목을 건드린다.

| 순서 | 후보 | 단계 | 항목 | 방향 |
| --- | --- | --- | --- | --- |
| 1 | `c7_role_over_value` | `verify_company_size` | `v18` | 올림 |
| 2 | `c9_catalogue_exclusion` | `postprocess` | `v10` · `v11` · `v13` | 내림 |

**순서가 갈릴 여지가 없다.** 1번은 기업규모 단계에서 사실을 고쳐 판정을 받고, 2번은
후처리 맨 끝에서 셀을 닫는다. 파이프라인이 순서를 정하므로 이 파일이 고를 것이 없다.
실제로 합이 개별 합과 **정확히 같다**(`+0.004807692308 + 0.005937791783
= +0.010745484091`).

`c8_scope_skeleton` 은 **넣지 않았다.** 단독으로는 합격이지만 v18 하나를 얻는 대신
같은 공고(`041`)에서 v10·v11 오탐을 만든다. 이 묶음의 값은 "내려가는 항목이 없다"는
것이라 그 후보를 섞으면 성질이 달라진다.

모델을 부르지 않는다. 추가 호출 0 · 추가 시간 0초 — 서버 시간이 그대로다.

재생:
    python -X utf8 tools/replay_run.py \
      --case reports/runs/colab-1790396310565903096/dev-debug \
      --script <기준 커밋의 script.py> \
      --candidate experiments/c9_integrated_candidate.py --output-dir <새 경로>
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


STEP1 = _load("c7_role_over_value_candidate",
              ROOT / "experiments/c7_role_over_value_candidate.py")
STEP2 = _load("c9_catalogue_exclusion_candidate",
              ROOT / "experiments/c9_catalogue_exclusion_candidate.py")
# 적은 순서가 파이프라인 순서와 같다. 읽는 사람이 파일을 따라가지 않아도 되게 여기 둔다.
ORDER = (STEP1.__name__, STEP2.__name__)


def verify_company_size(facts: dict[str, Any], rec: dict[str, Any], max_chars: int):
    """1단계 — 역할이 제한 아님을 말하면 값을 그쪽으로 맞춘다."""
    return STEP1.verify_company_size(facts, rec, max_chars)


def postprocess(parsed: dict[str, Any], rec: dict[str, Any]):
    """2단계 — 품번이 경쟁제품이 아니면 v10·v11·v13 을 닫는다."""
    return STEP2.postprocess(parsed, rec)
