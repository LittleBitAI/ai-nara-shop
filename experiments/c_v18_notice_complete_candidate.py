"""A — v16·v18 완전관측 게이트를 "공고문 전문" 기준으로 좁힌다. **반려됨.**

    ⚠ 이 후보는 **반려됐다. 채택 후보가 아니다.** 지우지 않는 이유는 반려 근거를
    재현 가능하게 남기기 위해서다. 사유는
    `reports/team-c/a-v18-notice-complete/README.md` §0 에 셋으로 적혀 있고,
    첫째가 결정적이다 — `docs/data.md:48` 의 데이터 계약과 충돌한다.

        위반이 첨부에만 나타날 수 있으므로 공고문만으로 판단을 끝내지 않습니다.
        첨부 누락은 부재탐지 위반의 자동 근거가 아닙니다.

    아래 `notice_complete()` 는 공고문만 온전하면 부재 판정을 허용한다. 그 계약을
    정면으로 어긴다. **이 후보를 살리는 변형을 만들지 않는다.**

아래는 반려 전에 쓴 설계 설명이며 기록으로 남긴다.


`_company_size_bands()` 의 `qualification == "unrestricted"` 분기(script.py 796-804)는
**문서 전체**의 절단·누락 플래그를 본다. 하나라도 잘리면 `absence_not_observable` 로
v14~v18 다섯 칸을 통째로 보류한다.

그런데 제한사항을 적어야 하는 곳은 법이 한 곳으로 지정한다.

    국가 시행령 제21조② (제공 스냅샷 210행)
    ②각 중앙관서의 장 또는 계약담당공무원은 제1항의 규정에 의하여 경쟁참가자의 자격을
    제한하고자 할 때에는 **입찰공고에** 그 제한사항과 제한기준을 명시하여야 한다.

    지방 시행령 제20조② (제공 스냅샷 211행)
    ② 지방자치단체의 장 또는 계약담당자는 제1항에 따라 입찰 참가자격을 제한하려는
    경우에는 **입찰공고에** 그 제한사항과 제한기준을 명시하여야 한다.

따라서 **공고문이 통째로 보였다면** 제한 문구의 부재는 관측된 것이다. 과업지시서 꼬리가
잘린 것은 그 관측을 무효로 만들지 않는다.

**이 방식은 이미 운영 코드 안에 있다.** v20 의 `software_complete`(script.py 737-741)가
전역 플래그 대신 해당 문서의 전문이 `visible` 안에 그대로 있는지를 본다. 같은 배선을
v16·v18 분기에 쓴다 — 새 판별축이 아니라 **이미 채택된 방식을 한 자리에 더 적용**하는 것이다.

바꾸는 것은 게이트 조건 하나뿐이다. 통과한 뒤의 우선조달 예외·금액 구간 판정은 운영
코드의 순서를 그대로 따른다. 올리는 항목·금액 경계·예외 처리에 손대지 않는다.

**절단을 요건 부재로 단정하지 않는다.** 공고문 자체가 잘렸거나 없으면 종전대로 보류한다.

모델을 부르지 않는다. 추가 호출 0 · 추가 시간 0초.

재생:
    python -X utf8 tools/replay_run.py --case reports/runs/colab-1789902969401579900/dev-debug \
      --candidate experiments/c_v18_notice_complete_candidate.py --output-dir <새 경로>
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 운영 게이트가 막았다는 신호. 이 사유일 때만 다시 본다.
BLOCKED = "absence_not_observable"
# 게이트를 통과한 뒤 운영 코드가 쓰는 사유들. 그대로 돌려준다.
DECIDED = "decided"
UNVERIFIED_PRIORITY = "unverified_priority_exception"
# 제한사항을 명시해야 하는 문서. 국가 제21조② · 지방 제20조② 가 "입찰공고" 로 지정한다.
NOTICE_TYPE = "공고문"


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


def notice_complete(facts: dict[str, Any], rec: dict[str, Any], visible: str) -> bool:
    """공고문 전문이 보였고 모델도 자격 절을 다 봤다고 하는가.

    `software_complete`(script.py 737-741)와 같은 모양이다 — 전역 절단 플래그 대신
    **그 문서의 본문이 `visible` 안에 그대로 있는지**를 본다.

    공고문이 없거나 비었거나 한 조각이라도 잘리면 거짓이다. 절단을 부재로 읽지 않는다.
    """
    notices = [d for d in rec.get("docs") or [] if d.get("type") == NOTICE_TYPE]
    return bool(
        rec.get("input_completeness", {}).get("완전관측") is True
        and notices
        and all(d.get("text", "").strip() and d["text"] in visible for d in notices)
        and facts.get("qualification_complete") == "yes")


def verify_company_size(facts: dict[str, Any], rec: dict[str, Any], max_chars: int):
    """운영 판정을 그대로 낸 뒤, 게이트가 막은 자리만 다시 본다.

    운영이 `absence_not_observable` 이 아닌 사유를 냈으면 **손대지 않는다.**
    금액 구간·예외·우선조달 판정은 운영 코드의 순서를 그대로 옮긴다.
    """
    script = baseline()
    out, reason = script.verify_company_size(facts, rec, max_chars)
    if reason != BLOCKED:
        return out, reason

    visible = script.build_context(rec, max_chars)
    if not notice_complete(facts, rec, visible):
        return out, reason                  # 공고문도 온전하지 않다. 종전대로 보류한다

    def quoted(value):
        return bool(value and value.strip() and value in visible
                    and any(value in d["text"] for d in rec["docs"]))

    # 여기부터는 script.py 805-822 와 같은 순서다. 게이트만 달랐을 뿐이다.
    priority = facts["priority_exception"]
    if priority == "unknown" or (priority == "yes" and not quoted(facts["priority_exception_quote"])):
        return out, UNVERIFIED_PRIORITY

    price = script.estimated_price(rec)
    hit = None if priority == "yes" or price >= script.NOTICE_AMOUNT_WON else (
        "v18" if price < script.SME_BAND_FLOOR_WON else "v16")

    bands = {v: {"위반여부": 0, "근거문구": None} for v in script.BAND_ITEMS}
    if hit in bands:
        bands[hit] = {"위반여부": 1,
                      "근거문구": None if hit in script.ABSENCE else facts["qualification_quote"]}

    # 운영은 bands 를 먼저 깔고 그 위에 products·document_requirements 를 얹는다
    # (script.py 716-719). 키가 서로 겹치지 않으므로 여기서도 밑에 깐다.
    merged = dict(bands)
    merged.update(out)
    return merged, DECIDED


def reopens(facts: dict[str, Any], rec: dict[str, Any], reason: str, visible: str) -> bool:
    """**적용 대상**인가. 셀이 바뀐다는 뜻이 아니다 — 둘을 섞지 않는다.

    운영이 전역 절단 때문에 막았는데 공고문은 온전한 공고를 센다. 그중 실제로 판정이
    바뀌는 것은 우선조달 예외와 금액 구간까지 통과한 일부뿐이다.
    """
    return reason == BLOCKED and notice_complete(facts, rec, visible)
