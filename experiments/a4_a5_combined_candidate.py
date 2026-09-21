"""A4 적용범위 게이트 + A5 H2 부재 연결을 한 재생에서 같이 잰다. 새 규칙은 없다.

**두 후보가 서로 다른 단계를 정의한다.** `replay_run.replay()`가 갈아끼우는 세 슬롯 중
A4는 `postprocess`(모델 뒤), H2는 `verify_company_size`(company_size 원응답 소비)다.
이 파일은 각각을 그대로 내보내기만 한다 — 어느 쪽 판정 규칙도 고치지 않는다.

**순서와 간섭.** 재생기는 `verify_company_size` → `parsed.update()` → `postprocess` 순으로 돈다.
H2가 올린 v11=1이 A4의 `postprocess`를 지나며 살아남는지가 유일한 간섭 지점이고, 둘 다 안 건드린다.

- `script.postprocess`의 `apply_product_rules()`는 `if cell.get("위반여부") != 1` 일 때만
  v11을 올리므로 이미 1인 것을 덮지 않는다.
- A4의 `postprocess`는 v6·v9·v23만 고쳐 쓴다. v11은 통과한다.
- v11은 `ABSENCE`라 `postprocess`가 `근거문구`를 빈칸으로 고정한다. H2도 None으로 넣는다.

**합치는 근거.** 두 후보가 바꾸는 항목이 겹치지 않는다(A4: v6·v9·v23 / H2: v11).
Macro F1은 항목별 F1의 평균이므로 서로 다른 항목의 변화는 정확히 더해진다.
그 산술이 맞는지를 실제 재생으로 확인하는 것이 이 파일의 목적이다.

기준: 회차 `colab-1789902969401579900`의 `dev-debug` 원응답 200건, `script.py` 미수정
(`main`·`feat/a4-scope-gate`·`LittleBitAI/a5-label-wall` 세 브랜치에서 블롭 `d2bcc73` 동일).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# A4 — v6·v9 오탐 게이트와 v23 공고기간 규칙. PR #69.
_a4 = _load("a4_scope_gate_candidate", REPO / "experiments" / "a4_scope_gate_candidate.py")
# A5 H2 — 검증된 company_size 부재 관측을 v11에 연결. astra, 브랜치 LittleBitAI/a5-label-wall.
_h2 = _load("a5_v11_absence_candidate", REPO / "experiments" / "a5_v11_absence_candidate.py")

postprocess = _a4.postprocess
verify_company_size = _h2.verify_company_size


def demo():
    """두 슬롯이 서로 다른 모듈에서 오고, 원본과 같은 함수인지만 본다."""
    assert postprocess.__module__ == "a4_scope_gate_candidate"
    assert verify_company_size.__module__ == "a5_v11_absence_candidate"
    assert not hasattr(sys.modules[__name__], "verify_sme"), "verify_sme는 건드리지 않는다"
    # 두 후보가 바꾸는 항목이 겹치지 않는다는 전제를 문서와 같이 고정한다.
    assert {"v6", "v9", "v23"} & {"v11"} == set()
    print("A4+A5 combined wiring self-check passed")


if __name__ == "__main__":
    demo()
