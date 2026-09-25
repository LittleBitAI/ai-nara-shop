"""C dev Macro — 보류돼 있던 후보 둘을 **순서를 고정해** 함께 얹는다.

방침이 바뀌었다(2026-09-25). 무라벨 배율이 "미정"이라는 것만으로 후보를 보류하지 않는다.
그래서 배율 때문에 멈춰 있던 둘을 현재 기준에서 다시 재고, 겹쳤을 때를 본다.

  1단계 `c_v13_merge_candidate`  — company 가 scope 를 `general` 로 확정했는데 앞 단계
     v13 양성이 남아 있으면 유지하지 않는다. **0 을 쓴다.**
  2단계 `c5_v11_absence_signal_candidate` — v10 부재 확인이 서 있고 중소 허용 문구가
     없으면 v11 을 올린다. **1 을 쓴다.**

**순서는 1 → 2 로 고정한다.** 둘은 같은 후처리 경로(`verify_company_size` 의 반환 dict)를
건드리지만 **쓰는 키가 다르다**(v13 · v11). 그래서 이 기준에서는 교환해도 같은 값이 나온다 —
그럼에도 순서를 적는 이유는, 둘 중 하나가 나중에 상대 항목을 건드리도록 넓어지면 그때
결과가 갈리기 때문이다. 순서를 안 적으면 그 변화를 못 본다.

**dev 라벨 기반이 아니다.** 두 규칙 모두 판별축이 항목 정의와 운영 코드의 기존 판단이며,
dev 라벨을 조건으로 읽지 않는다. (방침 변경으로 dev 라벨 기반 규칙도 허용되지만, 이 후보는
그것을 쓰지 않는다 — 방침이 되돌아가도 이 후보는 그대로 선다.)

모델을 부르지 않는다. 추가 호출 0 · 추가 시간 0초.

재생:
    python -X utf8 tools/replay_run.py \
      --case reports/runs/colab-1790235508743452453/dev-debug \
      --script <기준 커밋의 script.py> \
      --candidate experiments/c_dev_macro_stack_candidate.py --output-dir <새 경로>
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


STEP1 = _load("c_v13_merge_candidate", ROOT / "experiments/c_v13_merge_candidate.py")
STEP2 = _load("c5_v11_absence_signal_candidate",
              ROOT / "experiments/c5_v11_absence_signal_candidate.py")
# 적은 순서가 곧 적용 순서다. 읽는 사람이 파일 위치를 따라가지 않아도 되게 여기 둔다.
ORDER = (STEP1.__name__, STEP2.__name__)


def baseline():
    """재생기가 읽은 제출 코드를 집는다. 단독 import 면 저장소 루트의 것을 읽는다."""
    submitted = sys.modules.get("submission")
    if submitted is not None:
        return submitted
    return _load("baseline_script", ROOT / "script.py")


def verify_company_size(facts: dict[str, Any], rec: dict[str, Any], max_chars: int):
    """1단계의 반환 위에 2단계를 얹는다. 운영 판정을 지우지 않고 키만 더한다."""
    # 1단계. 안에서 운영 `verify_company_size` 를 부르고 v13 모순만 닫는다.
    out, reason = STEP1.verify_company_size(facts, rec, max_chars)
    if reason == UNVERIFIED:
        return out, reason
    # 2단계. 1단계가 낸 dict 를 받아 v11 만 올린다. 이미 1 인 셀은 건드리지 않는다.
    script = baseline()
    visible = script.build_context(rec, max_chars)
    already = (out.get(STEP2.ITEM) or {}).get("위반여부")
    if (already != 1
            and STEP2.absence_confirmed(script, facts, rec, visible)
            and not STEP2.sme_allowed(script, rec)):
        out = dict(out)
        out[STEP2.ITEM] = {"위반여부": 1, "근거문구": None}
    return out, reason
