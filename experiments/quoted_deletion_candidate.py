"""후처리 후보 — v3·v17 양성 중 근거 인용이 그 위반을 세우지 못하는 것을 내린다.

모델 뒤 단계만 바꾼다. `tools/replay_run.py --candidate` 로 갈아 끼운다. GPU 를 쓰지 않는다.
운영 `postprocess` 가 끝낸 판정의 `근거문구`(원문 대조를 통과한 인용)만 읽는다.

출처는 [인용 오탐 판정](../artifacts/review/quoted-fp-result.md)의 v3·v17 행이다.
그 판정이 의미 기준으로 오탐이라 한 셀이 dev 재생에서 바뀌는 셀의 전부다
(`tests/test_quoted_deletion_candidate.py`). 채택 여부는 dev 가 아니라 무라벨 삭제 집합의
정탐 혼입 `q < F/2` 로 정한다 — [설계 감사](../reports/label-compare/unlabeled-design-audit.md).

**내리기만 한다.** 0을 1로 올리는 경로가 없다. 두 규칙은 서로 다른 항목만 건드리므로
각자 단독 적용한 결과와 합친 결과가 같다.

**v3 실적제한 1배수 이상.** 항목표 비고가 `사업예산 기준` 이다. 두 경우만 내린다.
 ① 인용에서 실적 문구에 붙은 요구실적 금액이 추정가격·배정예산 **둘 다의** 1배 미만이다. 운영
   `performance_below_budget()` 은 문서 전체에서 실적 근처 금액의 최댓값을 읽어 다른 조항의
   금액을 집는다 — PPS-DEV-03 은 인용이 3천만원인데 1억을 읽었다. 여기서는 모델이 위반의
   근거로 댄 그 문장의 금액만 본다.
 ② 인용이 배점표의 구간 칸이다. 문서의 모든 등장 자리에서 바로 다음 행(칸 구분선·배점·행 번호만
   사이에 둔)이 같은 기준 문구의 더 낮은 비율이고 앞쪽에 배점·평가 표지가 있으면, 그것은 입찰을
   막는 참가자격이 아니라 점수 구간이다.

**v17 1억원 미만 일반물품 중소기업 제한.** v15 는 소기업 제한, v18 은 소기업 제한 없음이다.
v17 은 중기업까지 허용한 제한이라, 인용이 중소기업·중기업을 자격 주체로 적지 않으면 그
위반을 세우지 못한다. 법령·규정 이름(「중소기업기본법」, 「중소기업 범위 및 확인에 관한
규정」)에 든 `중소기업` 은 자격 주체가 아니므로 지우고 본다. 소기업·소상공인 확인서,
여성기업 자격이 여기서 내려간다. `experiments/evidence_gate_candidate.py` 의 ② 는 법령 이름을
안 지워 PPS-DEV-102 를 놓치고, `소기업` 이 없는 여성기업 인용도 놓친다.
"""

from __future__ import annotations

import re
import sys
from typing import Any, Dict, Optional

# ----- v3 -----
PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
# 1배 이상을 비율로 적은 표기. 이것이 있으면 금액 규칙은 쉰다.
RATIO = re.compile(r"(\d+(?:\.\d+)?)\s*(%|배)")
# 요구가 예산·추정가격 자체를 기준으로 적혔다(`사업예산 이상`). 금액 비교의 대상이 아니다.
BUDGET_FLOOR = re.compile(r"(?:사업\s*예산|예산\s*금액|배정\s*예산|추정\s*가격|기초\s*금액)\s*(?:의\s*)?이\s*상")
# 요구실적 금액은 실적 문구에 문법적으로 붙은 금액만 센다. 같은 문장·같은 절에 있다는 것으로는
# 부족했다(리뷰 라운드 3·4: 자본금이 `및`·`로서` 로 이어져 실적액으로 읽혔다).
#  앞에 붙음: `실적이 3천만원`, `준공금액이 5억원`
#  뒤에 붙음: `3억원(부가세 포함) 이상의 사업을 수행`, `1억원 이상 실적`
BOUND_BEFORE = re.compile(r"(?:실\s*적|(?:준\s*공|계\s*약|납\s*품|수\s*행)\s*금\s*액)\s*[이가은는의]?\s*$")
BOUND_AFTER = re.compile(r"\s*(?:\([^()]{0,20}\)\s*)?이\s*상\s*[의인]?\s*"
                         r"(?:[가-힣]{1,6}[을를의]\s+)?(?:[가-힣]*실\s*적|[가-힣]*수\s*행|납\s*품)")
# 배점표의 구간 칸: `<기준 문구> N% 이상`. 기준 문구는 한두 어절이다.
BAND_CELL = re.compile(r"([가-힣]+(?:\s[가-힣]+)?)\s*(\d+(?:\.\d+)?)\s*%\s*이상")
# 구간 칸과 다음 행 사이에 올 수 있는 것: 칸 구분선, 배점 숫자, `나.`·`2)` 같은 행 번호.
ROW_GAP = r"[\s|│\d점]*(?:[가-힣\d]\s*[.)]\s*)?"
CUE_REACH = 600      # 인용 앞에서 배점표 표지를 찾을 범위
SCORING_CUE = re.compile(r"배\s*점|평\s*가|점\s*수|\d+\s*점")

# ----- v17 -----
# 괄호로 묶인 법령 이름, 괄호 없이 쓴 중소기업 관련 법령·기관·서식 이름.
# 괄호는 법령 이름처럼 끝날 때만 지운다. 「중소기업」 처럼 자격 주체를 인용 부호로 묶은 것은 남긴다.
LAW_TITLE = re.compile(r"[「｢『][^」｣』]*(?:법|법률|령|규정|규칙|고시|지침|기준|요령)[」｣』]")
# 괄호 없는 쪽은 이름 전체가 맞을 때만 지운다. `중소기업 범위에 해당하는 업체` 의 중소기업은 자격 주체다.
BARE_TITLE = re.compile(r"중소\s*기업\s*(?:기본\s*법|범위\s*및\s*확인|현황\s*정보|제품\s*구매\s*촉진|청)"
                        r"|중소\s*벤처\s*기업\s*부")
MID_SIZE = re.compile(r"중\s*[·・ㆍ․,./]?\s*소\s*기업|중\s*기업")


def baseline():
    """replay_run 이 실은 제출 코드. 직접 부르면 저장소 루트의 script.py 를 쓴다.

    `run_submission` 은 보지 않는다 — `--verify` 전용인 회차 커밋의 옛 코드 자리다.
    이유는 `experiments/a7_v24_meta_diff.py` 의 `baseline()` 에 적혀 있다.
    """
    module = sys.modules.get("submission")
    if module is None:
        import script as module
    return module


def _performance_amounts(quote):
    """실적 문구에 앞이나 뒤로 붙은 금액. 붙은 것이 없으면 빈 목록이다."""
    script = baseline()
    values = []
    for match in script.MONEY.finditer(quote):
        value = script.parse_money(match)
        if value is None or not script.MONEY_MIN <= value <= script.MONEY_MAX:
            continue
        if (BOUND_BEFORE.search(quote[max(0, match.start() - 20):match.start()])
                or BOUND_AFTER.match(quote, match.end())):
            values.append(value)
    return values


def _below_budget(quote, rec):
    meta = rec.get("meta") or {}
    bases = [b for b in (meta.get("입찰추정가격"), meta.get("배정예산금액"))
             if isinstance(b, (int, float)) and not isinstance(b, bool) and b > 0]
    if any(float(n) >= (100 if unit == "%" else 1) for n, unit in RATIO.findall(quote)):
        return False   # 1배 이상 비율을 적었다. 금액과 어느 쪽이 요구인지 가리지 않는다
    if BUDGET_FLOOR.search(quote):
        return False
    amounts = _performance_amounts(quote)
    if not bases or not amounts:
        return False
    return max(amounts) < min(bases)   # 두 기준 모두의 1배 미만일 때만


def _scoring_band(quote, rec):
    """인용이 배점표 구간 칸이고, 문서의 모든 등장 자리에서 바로 다음 행이 같은 기준의 낮은 구간인가.

    참가자격을 적는 표기는 끝이 없어 그것이 없음을 보는 방식은 새 표기마다 뚫렸다(리뷰 라운드 1·2).
    그래서 표 구조가 있음을 요구한다. 같은 문구가 한 곳에서라도 표의 칸이 아니면 — 참가자격
    문장에도 나오면 — 모델이 어느 쪽을 근거로 댔는지 모르므로 내리지 않는다.
    """
    cell = BAND_CELL.search(quote)
    if not cell:
        return False
    base, top = cell.group(1), float(cell.group(2))
    next_row = re.compile(ROW_GAP + r"\s*".join(map(re.escape, base.replace(" ", "")))
                          + r"\s*(\d+(?:\.\d+)?)\s*%")
    seen = False
    for doc in rec.get("docs", []):
        text = doc.get("text") or ""
        start = text.find(quote)
        while start >= 0:
            seen = True
            row = next_row.match(text, start + len(quote))
            if not (row and float(row.group(1)) < top
                    and SCORING_CUE.search(text[max(0, start - CUE_REACH):start])):
                return False
            start = text.find(quote, start + 1)
    return seen


def v3_deletion(quote: str, rec: Dict[str, Any]) -> Optional[str]:
    """v3 양성을 내릴 이유. 내리지 않으면 None."""
    if not (quote or "").strip():
        return None
    if _below_budget(quote, rec):
        return "below_budget"
    if _scoring_band(quote, rec):
        return "scoring_band"
    return None


def v17_deletion(quote: str) -> Optional[str]:
    """v17 양성을 내릴 이유. 인용이 중기업을 자격 주체로 적지 않으면 내린다."""
    if not (quote or "").strip():
        return None
    body = BARE_TITLE.sub(" ", LAW_TITLE.sub(" ", quote))
    return None if MID_SIZE.search(body) else "no_mid_size_entity"


def postprocess(judgment: Dict[str, Dict[str, Any]], rec: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out = baseline().postprocess(judgment, rec)
    for item, reason in (("v3", lambda q: v3_deletion(q, rec)), ("v17", v17_deletion)):
        cell = out[item]
        if cell["위반여부"] == 1 and reason(cell["근거문구"]):
            out[item] = {"위반여부": 0, "근거문구": ""}
    return out
