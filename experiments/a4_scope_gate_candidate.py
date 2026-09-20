"""후처리 후보 — 적용범위 밖에서 난 오탐을 내리고, 조문이 정한 기간 위반을 올린다.

모델 뒤 단계만 바꾼다. `tools/replay_run.py --candidate` 로 갈아 끼운다. GPU 를 쓰지 않는다.

**다섯을 한 묶음으로 잰다.** v6·v9·v10·v13·v23 은 전부 "재현율은 있는데 적용범위 게이트가
없다" 로 묶인 항목이다. 하나씩 넣고 이긴 것만 남기면 항목당 양성 5~8 건 위에서 다섯 번
고르는 것이고, 그것이 dev 과적합의 경로다. 한 번에 넣고 한 번 잰다.

측정 기준: `18f07e5` 회차 `colab-1789902969401579900`, dev Macro F1 0.599315859078.

## 넣은 것 셋

**v6 — 고시금액 미만 지역제한 시·군·구 (3/6/3 · F1 0.400).**
세 조건 전부 항목 정의와 제출 계약에서 나온다.
① v6 은 부재탐지가 아니다. [data D4-4](../docs/data.md) 가 `e` 를 원문의 연속된 부분문자열로
   규정하므로, 지역을 제한했다면 그 문장이 공고에 있다. 근거가 비면 내린다.
② 근거에 광역 지자체 이름도 익명화 지역 마커도 없으면 그 인용은 지역제한 문장이 아니다.
③ 근거가 광역 지자체 **둘 이상**을 가리키고 기초 단위 신호가 하나도 없으면 그것은 v6 이 아니라
   v7(고시금액 미만 지역제한 인접 확대)이다. 기초 신호가 있으면 내리지 않는다 —
   `PPS-DEV-072` 는 정답이 v6 과 v7 **둘 다** 1 이다.

**v9 — 과업지시서 특정 모델명 명시 (5/13/1 · F1 0.417).**
① 근거가 비면 내린다. v9 도 부재탐지가 아니다.
② 항목명이 **과업지시서**다. 근거가 공고문에서만 나왔으면 과업 명세가 아니라 공고 본문의
   품명·내역이다. 규격서·과업지시서·제안요청서 계열에서 나온 인용만 남긴다.
   `ponytail: 정답 4건의 인용이 전부 규격서다. 규격서만 인정하면 dev F1 0.533 이지만
   항목명이 "과업지시서"이므로 안 좁힌다 — 문서 종류 하나에 맞추는 것은 dev 적합이다.`

**v23 — 현장설명회 (공고기간) (1/3/4 · F1 0.222).**
이 항목만 내림과 올림을 같이 한다. 모델이 7건 중 1건만 맞히고, 조문이 날짜 산술 하나이기 때문이다.
- **적용범위 밖은 0이다.** [items v23](../docs/items.md) 이 "계약방법 협상 + 계약법 지방만 적용",
  "국가계약법: 해당 없음(위반 성립 불가)" 으로 못박았다. 지방계약법이 아니거나 낙찰방법이
  협상이 아니면 위반이 성립하지 않는다.
- **범위 안에서는 조문이 정한다.** 「지방자치단체 입찰시 낙찰자 결정기준」 제7장 제3절 2-다:
  "제안요청서 설명은 … 이 경우 **입찰공고는 제안요청서 설명일의 전일부터 기산하여 7일전에
  공고해야 한다**." 전일부터 기산해 7일이므로 적법한 최소 간격은 `설명일 - 공고게시일 >= 8` 이다.
  설명일을 못 찾으면 발화하지 않는다 — 설명회를 안 하면 이 조항이 적용되지 않는다.

## 안 넣은 것 둘 — 재 봤고 열 재료가 없다

**v10 (4/8/3).** 부재탐지라 근거가 없고, 기존 `direct_production_demand()` 가
v10 관련 15건(양성 7 · 오탐 8) **전부에서** 직생 요구 문장을 못 찾는다. 내릴 축이 없다.
같은 함수가 v11 에서는 4건을 찾는다.

**v13 (4/9/2).** 여섯 축이 전부 정탐과 오탐에서 같은 값이다 — 금액 구간(오탐 9건 전부
1억 미만인데 TP 도 88.1M·90.5M), `scope`(competitive 6/6 대 8/9), `qualification`(small_only
5/6 대 **9/9**), `qualification_role`(eligibility 6/6 대 9/9), 본문 직접생산 언급(6/6 대 7/9),
그리고 인용 문장 자체. `PPS-DEV-078`(TP·90,454,545원)과 `PPS-DEV-03`(FP·89,090,909원)의
참가자격 문장이 같은 조문을 같은 형식으로 인용한다.

둘 다 [A5](../docs/tasks/a5-label-definition-wall.md) 로 넘겼다.
"못 고친다"가 아니라 **"이 축들로는 못 가른다"**이다.
"""

from __future__ import annotations

import datetime
import importlib.util
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, Optional

REPO = Path(__file__).resolve().parents[1]


def _load_script():
    spec = importlib.util.spec_from_file_location("baseline_script", REPO / "script.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_SCRIPT = None


def baseline():
    """제출 코드를 한 번만 읽어 돌려준다. replay_run 이 넘긴 것이 있으면 그것을 쓴다."""
    global _SCRIPT
    if _SCRIPT is None:
        _SCRIPT = sys.modules.get("run_submission") or sys.modules.get("submission") or _load_script()
    return _SCRIPT


# ----- v6 -----
# 익명화된 지역 토큰. 입력이 200건 전부 `anon_applied=True` 라 기초 지자체 이름이
# 이 꼴로 바뀌어 있다(본문 123건). `단위=기초` 가 시·군·구 제한이라는 신호다.
ANON_REGION = re.compile(r"\[(?:등록)?지역:[^\]]*?단위=(기초|광역)[^\]]*\]")
# 기초 단위를 이름으로 적은 공고도 있다. 광역시·특별시·특별자치시는 광역이므로 뺀다.
BASIC_REGION_NAME = re.compile(r"(?<![가-힣])[가-힣]{2,4}(?:시|군|구)(?![가-힣])")

# ----- v9 -----
# 항목명이 "과업지시서"다. 공고문 본문의 품명·내역은 과업 명세가 아니다.
SPEC_DOC_TYPES = ("과업지시서", "규격서", "제안요청서")

# ----- v23 -----
# 제안요청서 설명·현장설명을 여는 말. 예규가 "제안요청서 설명"이고 공고는 여러 이름을 쓴다.
BRIEFING = re.compile(r"(?:현장|과업|제안요청서|제안|사업)\s*설명(?:회)?")
BRIEFING_WINDOW = 120                       # 그 말 뒤로 날짜를 찾는 범위
# 설명을 안 하면 이 조항이 적용되지 않는다. 예규 제3절 2-나가 교부·설명 생략을 예정한다.
# 생략을 적어 둔 공고는 그 뒤에 제안서 마감일이 붙어 있어 날짜 창에 걸린다 — `PPS-DEV-041`.
BRIEFING_SKIPPED = re.compile(r"생략|미실시|실시하지\s*(?:않|아니)|갈음|해당\s*없음|없음")
NOTICE_DATE = re.compile(r"(20\d{2})\s*[.년]\s*(\d{1,2})\s*[.월]\s*(\d{1,2})")
# 제7장 제3절 2-다: 설명일의 **전일부터 기산하여 7일 전**에 공고. 적법한 최소 간격이 8일이다.
BRIEFING_NOTICE_DAYS = 8
QUOTE_MAX = 300                             # 제출 계약의 e 열 상한 안에서 자른다


def _wide_region_names(text: str) -> set:
    script = baseline()
    return set(re.findall(script.WIDE_REGION, text or ""))


def _has_basic_unit(text: str) -> bool:
    """이 인용이 기초(시·군·구) 단위 제한을 가리키는가."""
    if any(unit == "기초" for unit in ANON_REGION.findall(text or "")):
        return True
    # 광역 이름을 먼저 지운다. "서울특별시"의 "특별시"를 기초로 세지 않기 위해서다.
    script = baseline()
    stripped = re.sub(script.WIDE_REGION, " ", text or "")
    return bool(BASIC_REGION_NAME.search(stripped))


def v6_not_a_basic_region_limit(evidence: str, rec: Dict[str, Any]) -> bool:
    """v6 의 근거가 '고시금액 미만 계약의 시·군·구 제한'을 가리키지 못하는가."""
    if not (evidence or "").strip():
        return True                                     # ① 근거 없는 양성
    wide = _wide_region_names(evidence)
    if not wide and not ANON_REGION.search(evidence):
        return True                                     # ② 지역제한 문장이 아니다
    if len(wide) >= 2 and not _has_basic_unit(evidence):
        return True                                     # ③ 광역 확대 — v7 의 몫이다
    return False


def v9_not_from_spec_document(evidence: str, rec: Dict[str, Any]) -> bool:
    """v9 의 근거가 과업 명세 문서에서 나오지 않았는가."""
    if not (evidence or "").strip():
        return True                                     # ① 근거 없는 양성
    script = baseline()
    for doc in rec.get("docs") or []:
        if doc.get("type") in SPEC_DOC_TYPES and script.clean_evidence(evidence, doc.get("text") or ""):
            return False
    return True                                         # ② 공고문에서만 나왔다


def _as_date(value) -> Optional[datetime.date]:
    text = str(value or "")
    if len(text) != 8 or not text.isdigit():
        return None
    try:
        return datetime.date(int(text[:4]), int(text[4:6]), int(text[6:8]))
    except ValueError:
        return None


def v23_applies(rec: Dict[str, Any]) -> bool:
    """항목명 주석 그대로 — 계약방법 협상 + 계약법 지방인 공고에만 v23 이 성립한다."""
    meta = rec.get("meta") or {}
    return ("지방" in str(meta.get("적용계약법") or "")
            and "협상" in str(meta.get("낙찰방법") or ""))


def v23_late_notice(rec: Dict[str, Any]) -> Optional[str]:
    """설명일까지의 공고기간이 예규 최소선에 못 미치면 그 설명 문장을 돌려준다. 아니면 None.

    설명일을 못 찾으면 None 이다 — 설명을 안 하면 이 조항이 적용되지 않는다.
    """
    posted = _as_date((rec.get("meta") or {}).get("공고게시일자"))
    if posted is None:
        return None
    best = None
    for doc in rec.get("docs") or []:
        text = doc.get("text") or ""
        for found in BRIEFING.finditer(text):
            window = text[found.start(): found.end() + BRIEFING_WINDOW]
            if BRIEFING_SKIPPED.search(window):
                continue                                # 설명을 안 한다 — 이 조항이 적용되지 않는다
            for stamp in NOTICE_DATE.finditer(window):
                try:
                    held = datetime.date(int(stamp[1]), int(stamp[2]), int(stamp[3]))
                except ValueError:
                    continue
                if held < posted:
                    continue                            # 지난 해 일정 등 — 이 공고의 설명일이 아니다
                gap = (held - posted).days
                if best is None or gap < best[0]:
                    best = (gap, text[found.start(): found.start() + QUOTE_MAX].strip())
    if best is None or best[0] >= BRIEFING_NOTICE_DAYS:
        return None
    return best[1]


def postprocess(judgment: Dict[str, Dict[str, Any]], rec: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out = dict(baseline().postprocess(judgment, rec))
    script = baseline()

    for item, refuted in (("v6", v6_not_a_basic_region_limit), ("v9", v9_not_from_spec_document)):
        cell = out.get(item) or {"위반여부": 0, "근거문구": ""}
        if cell.get("위반여부") == 1 and refuted(cell.get("근거문구") or "", rec):
            out[item] = {"위반여부": 0, "근거문구": ""}

    # v23 은 코드가 정한다. 범위 밖이면 0, 범위 안에서는 예규의 공고기간이 갈린다.
    if not v23_applies(rec):
        out["v23"] = {"위반여부": 0, "근거문구": ""}
    else:
        quote = v23_late_notice(rec)
        evidence = ""
        if quote:
            for doc in rec.get("docs") or []:
                evidence = script.clean_evidence(quote, doc.get("text") or "")
                if evidence:
                    break
        out["v23"] = ({"위반여부": 1, "근거문구": evidence} if evidence
                      else {"위반여부": 0, "근거문구": ""})
    return out
