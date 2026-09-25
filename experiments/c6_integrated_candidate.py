"""C6 통합 — dev Macro 를 올린 후보 **셋**을 순서를 고정해 얹는다.

2026-09-25 방침(과적합을 감수하고 dev Macro 를 올린다) 아래에서 잰 후보 중 합격한 셋이다.
각각의 실측과 왜 채택했는지는 `reports/team-c/c6-dev-macro/README.md` 가 소유한다.

| 순서 | 후보 | 축 | 쓰는 키 | 방향 | 단독 Macro |
| --- | --- | --- | --- | --- | ---: |
| 1 | `c6_band_no_demand_narrow` | 직생 요구 부재 | `v18` | 올림 | +0.010897435897 |
| 2 | `c6_v16_role_none` | 자격 문장 역할 미정 | `v16` | 내림 | +0.004662004662 |
| 3 | `c5_v11_absence_signal` | v10 부재 확인 | `v11` | 올림 | +0.007843137255 |

**순서를 1 → 2 → 3 으로 고정한다.** 셋이 같은 후처리 경로(`verify_company_size` 의 반환
dict)를 건드리지만 **쓰는 키가 서로 다르다**(v18 · v16 · v11). 그래서 이 기준에서는 교환해도
같은 값이 나오고, 그 사실을 `tests/test_c6_integrated.py` 가 역순 재생으로 박아 둔다.
그럼에도 순서를 적는 이유는, 어느 하나가 나중에 옆 항목까지 건드리도록 넓어지면 그때
결과가 갈리기 때문이다. 순서를 안 적으면 그 변화를 못 본다.

**2번은 dev 라벨 기반이다** (표본 2건). 방침이 되돌아가면 그것부터 뺀다 —
`ORDER` 에서 `STEP2` 를 지우면 나머지 둘은 그대로 선다.

`c_v13_merge_candidate` 는 **넣지 않았다.** 이 기준에서 0셀이라 채택 근거가 없다.
`c6_band_no_demand_wide` 와 `c5_v11_scope_gate` 는 dev 에서 손해라 기각이다.

모델을 부르지 않는다. **추가 호출 0 · 추가 시간 0초** — 서버 시간이 늘지 않는다.

재생:
    python -X utf8 tools/replay_run.py \
      --case reports/runs/colab-1790235508743452453/dev-debug \
      --script <기준 커밋의 script.py> \
      --candidate experiments/c6_integrated_candidate.py --output-dir <새 경로>
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

UNVERIFIED = "unverified_scope"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


STEP1 = _load("c6_band_no_demand_narrow_candidate",
              ROOT / "experiments/c6_band_no_demand_narrow_candidate.py")
STEP2 = _load("c6_v16_role_none_candidate",
              ROOT / "experiments/c6_v16_role_none_candidate.py")
STEP3 = _load("c5_v11_absence_signal_candidate",
              ROOT / "experiments/c5_v11_absence_signal_candidate.py")
# 적은 순서가 곧 적용 순서다. 읽는 사람이 파일 위치를 따라가지 않아도 되게 여기 둔다.
ORDER = (STEP1.__name__, STEP2.__name__, STEP3.__name__)


def baseline():
    """재생기가 읽은 제출 코드를 집는다. 단독 import 면 저장소 루트의 것을 읽는다."""
    submitted = sys.modules.get("submission")
    if submitted is not None:
        return submitted
    return _load("baseline_script", ROOT / "script.py")


def verify_company_size(facts: dict[str, Any], rec: dict[str, Any], max_chars: int):
    """세 후보를 차례로 얹는다. 각 단계는 앞 단계가 낸 dict 를 받는다.

    1번만 운영 `verify_company_size` 를 부른다. 2·3번은 **규칙을 여기 옮겨 적지 않고**
    각 모듈의 판단을 그대로 다시 밟는다 — 원본이 바뀌면 여기도 같이 바뀌어야 한다.
    """
    script = baseline()
    # 1. 직생 요구가 없으면 `competitive` 를 v18 에 한해 안 믿는다.
    out, reason = STEP1.verify_company_size(facts, rec, max_chars)

    # 2. 자격 문장의 역할이 미정이면 v16 을 올리지 않는다. **결정표가 올린 셀만** 되돌린다.
    if (facts.get("qualification_role") == STEP2.UNDECIDED_ROLE
            and (out.get(STEP2.ITEM) or {}).get("위반여부") == 1):
        out = dict(out)
        out[STEP2.ITEM] = {"위반여부": 0, "근거문구": None}

    if reason == UNVERIFIED:
        return out, reason

    # 3. v10 부재가 확인됐고 중소 허용 문구가 없으면 v11 을 올린다. 이미 1 이면 안 건드린다.
    visible = script.build_context(rec, max_chars)
    if ((out.get(STEP3.ITEM) or {}).get("위반여부") != 1
            and STEP3.absence_confirmed(script, facts, rec, visible)
            and not STEP3.sme_allowed(script, rec)):
        out = dict(out)
        out[STEP3.ITEM] = {"위반여부": 1, "근거문구": None}
    return out, reason
