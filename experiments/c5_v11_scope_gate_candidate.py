"""C5 후보 — v11 의 "경쟁제품 입찰인가" 를 **직생 요구 문장 대신 검증된 `scope`** 로 본다.

C5 조사(`reports/team-c/c5-v11-paths/`)가 찾은 것: v11 의 FN 4건이 전부 후처리
경쟁제품 게이트의 **첫 조건**에서 막힌다. 그 조건은 `DP_DEMAND` 정규식이 "직생 요구
문장" 을 찾는 것인데, **v11 은 부재탐지 항목이라 그 문장이 없는 것이 정상**이다.
셋(`061`·`062`·`064`)은 모델이 직생 조항의 부재를 이미 관측했고 **v10 이 그 신호로
TP 를 냈다.** 같은 공고에서 v11 만 쉰다.

## 정규식에 어휘를 더하지 않는다

고치는 방향은 "더 많은 문구를 잡게" 가 아니라 **"존재 게이트로 쓰지 않는 것"** 이다.
운영 코드에서 `direct_production_demand()` 는 세 자리에 쓰이는데 역할이 갈린다.

| 자리 | 무엇에 쓰나 | 역할 |
| --- | --- | --- |
| `company_size_products()` (`script.py:677`) | v12 의 **근거문구** 그 자체 | **존재 판정** — 정당하다 |
| `_company_size_bands()` (`script.py:789`) | 품명번호를 꺼내 카탈로그와 대조 | **존재 판정** — 정당하다 |
| `apply_competitive_rules()` (`script.py:2321`) | v11 을 **열지 말지의 전제** | **부재 판정의 전제** — 여기가 문제다 |

앞의 둘은 "직생을 요구했다" 는 사실 자체가 근거다. 세 번째만 다르다 — v11 의 근거문구는
부재탐지라 **항상 빈칸**이고, `DP_DEMAND` 는 오직 **"이 공고가 경쟁제품 입찰인가" 를
알아내는 대용**으로 쓰인다. 그 물음에는 **모델이 이미 `scope` 로 답하고 있다.**

## 이 후보가 하는 일

`verify_company_size` 안에서, **v10 부재 판정과 같은 축**으로 v11 을 연다.

    검증된 scope 가 competitive 이고
    참가자격이 중소기업자를 허용하는 문구가 원문에 없으면   →   v11 = 1

`scope` 검증은 운영 코드가 v10 에 쓰는 것과 같다(`scope == "competitive"` + 인용이 원문에서
확인됨). 중소 허용 조건은 기존 게이트의 셋째 조건(`SME_ALLOWED`)을 그대로 쓴다 —
C5 §4 가 그 조건이 31건을 막고 **놓친 양성 0** 임을 실측했다.

**올리기만 한다.** 이미 1 인 v11 을 내리지 않고, 다른 23항목을 건드리지 않는다.
카탈로그 조건은 품명번호가 직생 문장에서 오므로 이 경로에서는 쓸 수 없다 — 그것이
이 후보의 대가이고, 오탐이 늘면 거기서 온다.

모델을 부르지 않는다. 추가 호출 0 · 추가 시간 0초.

재생:
    py -X utf8 tools/replay_run.py --case reports/runs/colab-1789902969401579900/dev-debug \
      --script <tmp>/script.py \
      --candidate experiments/c5_v11_scope_gate_candidate.py --output-dir <새 경로>
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ITEM = "v11"
APPLICABLE_SCOPE = "competitive"
# scope 자체가 미확인이면 아무것도 하지 않는다(기본 판정 보존).
UNVERIFIED = "unverified_scope"


def baseline():
    """재생기가 실은 제출 코드를 집는다. 단독 import 면 저장소 루트의 것을 읽는다."""
    submitted = sys.modules.get("submission")
    if submitted is not None:
        return submitted            # 캐시하지 않는다 — main() 이 다시 돌면 새 모듈이다
    import importlib.util
    spec = importlib.util.spec_from_file_location("baseline_script", ROOT / "script.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def competitive_scope(script, facts: dict[str, Any], rec: dict[str, Any], visible: str) -> bool:
    """검증된 `scope` 가 경쟁제품인가. **운영 코드가 v10 에 쓰는 것과 같은 검사다.**"""
    quote = facts.get("scope_quote")
    quote = script.restore_spacing(quote, rec, visible) or quote
    verified = bool(quote and quote.strip() and quote in visible
                    and any(quote in d["text"] for d in rec["docs"]))
    return facts.get("scope") == APPLICABLE_SCOPE and verified


def sme_allowed(script, rec: dict[str, Any]) -> bool:
    """참가자격이 중소기업자까지 허용하는가. 기존 게이트의 셋째 조건 그대로다."""
    return bool(script.SME_ALLOWED.search(script.build_context(rec, max_chars=script.PROMPT_BUDGET)))


def verify_company_size(facts: dict[str, Any], rec: dict[str, Any], max_chars: int):
    """운영 판정을 그대로 낸 뒤, v11 을 **scope 축으로** 한 번 더 연다.

    운영 `verify_company_size` 의 반환을 바꾸지 않고 **키 하나를 더할 뿐**이다.
    """
    script = baseline()
    out, reason = script.verify_company_size(facts, rec, max_chars)
    if reason == UNVERIFIED:
        return out, reason                      # scope 미확인 — 아무 말도 하지 않는다
    visible = script.build_context(rec, max_chars)
    already = (out.get(ITEM) or {}).get("위반여부")
    if already != 1 and competitive_scope(script, facts, rec, visible) and not sme_allowed(script, rec):
        out = dict(out)
        # 부재탐지 — 근거는 항상 빈칸이다(`script.ABSENCE`).
        out[ITEM] = {"위반여부": 1, "근거문구": None}
    return out, reason


def fires(script, facts: dict[str, Any], rec: dict[str, Any], max_chars: int) -> bool:
    """**발화 조건**이 참인가. 셀이 바뀐다는 뜻이 아니다 — 둘을 섞지 않는다."""
    visible = script.build_context(rec, max_chars)
    return competitive_scope(script, facts, rec, visible) and not sme_allowed(script, rec)
