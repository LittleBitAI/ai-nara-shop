"""후처리 후보 — v24 양성은 **코드가 찾을 수 있는 불일치**를 하나는 가져야 한다.

모델 뒤 단계만 바꾼다. `tools/replay_run.py --candidate` 로 갈아 끼운다. GPU 를 쓰지 않는다.

**실측: `18f07e5` 회차 `colab-1789902969401579900` 재생 0.593846165415 → 0.599231652943,
`+0.005385`. v24 5/36/3 → 4/12/4 (F1 0.204 → 0.333).** 바뀐 셀 24개가 전부 v24 이고
대상 밖 23항목 0셀이다. 무라벨 6,000건 발화 24.9% 대 dev 22.5% — 배율 1.107.
근거·한계·못 살린 한 건은 [보고서](../reports/team-c/a7-v24-meta-diff/README.md)가 소유한다.
**채택 전이며 새 GPU·서버 점수가 아니다.**

## 왜 v24 인가

`18f07e5` 회차 재생에서 v24 는 **5/36/3 · F1 0.204** 다. **오탐 36건은 전체 오탐 111건의 32%**
이고, 단일 항목의 `FP→0` 이득으로는 24항목 중 최대다(+0.0235). 그리고 v24 는
[A5 독립 분석](../reports/team-c/a5-label-definition/five-stuck-analysis.md)이 확인한 대로
**company 소비 대상이 아니다** — baseline 판정과 기존 후처리만 쓴다.
그래서 `scope`·기업등급·부재 관측과 독립이고, 보관 원응답 재생으로 churn 0 에서 잴 수 있다.

## 지금 무엇이 비어 있나

`v24_consistent_with_meta()` 는 **모델이 준 근거 문구**의 금액·지역·제목태그를 메타와 대조해
전부 일치하면 그 양성을 내린다(`evidence_refutes`). 문제는 반환값이 `checked` 라는 것이다 —
**대조할 것이 근거에 없으면 아무 말도 못 하고 양성이 그대로 남는다.**

회차 2 control 의 v24 양성 41건을 세면 **근거 빈칸이 24건(TP 2 · FP 22)** 이다.
즉 현재 검증기는 **오탐 질량의 61% 에 닿지 못한다.**

## 무엇을 바꾸나

**대조 대상을 모델의 근거가 아니라 공고 원문으로 바꾼다.** 항목표 `비고` 가 지정한 네 축
(`예산, 계약방법, 지역제한, 업종`)을 코드가 직접 공고↔메타로 대조하고,
**어느 축에서도 불일치를 못 찾으면 그 양성을 내린다.** 근거가 있든 없든 같은 검사를 받는다.

v24 는 조문 없는 대조형 항목이라(`항목표.json`: "조문 없는 대조형 항목") 네 축이 전부
구조화된 메타 필드에 있다. [규칙 A10](../docs/rules.md) 이 이 용도를 명시로 허용한다 —
"기관 유형·지역 계층·금액·품목·문서를 함께 읽고 v24 불일치 대조".

축별 판정은 기존 자산을 그대로 쓴다. `V24_TITLE_TAG`·`V24_UNIT`(제목의 계약방법·금액구간),
`V24_AMOUNT`(금액), `V24_REGION`·`REGION`·`WIDE_REGION`(지역제한), `CODE10`(업종·품명 코드).
새 정규식은 업종코드 표기 하나뿐이다.

## 네 축을 다 넣고 한 번 잰다

`a4_scope_gate_candidate` 가 적어 둔 그대로다 — 축을 하나씩 넣고 이긴 것만 남기면
양성 8건 위에서 네 번 고르는 dev 과적합이다. **항목표가 지정한 네 축을 그대로 넣는다.**
[A5](../reports/team-c/a5-label-definition/five-stuck-analysis.md)가 업종 축 단독으로는
7건 중 1건밖에 못 가른다고 측정했으나, 그것은 업종을 **빼는** 근거가 아니라 단독으로 쓰지
말라는 근거다.

## 안 하는 것

- **"빈 근거면 0"** 을 다시 제안하지 않는다. A5 가 이미 기각했고 TP 2건을 잃는다.
  이 후보는 빈 근거를 **따로 취급하지 않는다** — 근거 유무와 무관하게 같은 원문 대조를 건다.
- 새 양성을 만들지 않는다. 이 후보는 **내리기만** 한다. FN 3건(29·049·055)은 그대로 남는다.
- 메타에 없는 축(예: 낙찰하한율)은 보지 않는다. 항목표가 지정한 넷만 본다.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[1]

# 본문이 업종을 참가자격으로 거는 표기. `업종코드 1169`·`(업종코드: 5210)` 꼴이다.
DOC_INDUSTRY = re.compile(r"업\s*종\s*(?:코드|번호)?\s*[:：(]?\s*(\d{4})(?!\d)")
# 메타 `면허업종제한목록` 이 괄호로 코드를 적는다. 목록 문자열에서 코드만 뽑는다.
META_INDUSTRY = re.compile(r"(?<!\d)(\d{4})(?!\d)")

_SCRIPT = None


def baseline():
    """제출 코드를 한 번만 읽어 돌려준다. replay_run 이 넘긴 것이 있으면 그것을 쓴다.

    `run_submission` 은 보지 않는다. 그 이름은 `replay_run.run_script()` 가 **회차 커밋의**
    `script.py` 를 꽂는 자리이고(`--verify` 전용), `--verify` 는 후보를 아예 거부한다.
    그래서 후보가 그것을 집으면 항상 틀린 코드다 — 옛 커밋에는 이 후보가 쓰는
    `V24_TITLE_TAG` 같은 뒤에 생긴 이름이 없다.
    `tests/test_replay_run.py` 가 모듈 적재 시점에 그 이름을 등록한 채 남기므로,
    같은 프로세스에서 뒤에 도는 후보가 실제로 그것을 줍는다.
    """
    global _SCRIPT
    if _SCRIPT is None:
        _SCRIPT = sys.modules.get("submission")
    if _SCRIPT is None:
        spec = importlib.util.spec_from_file_location("baseline_script", REPO / "script.py")
        _SCRIPT = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_SCRIPT)
    return _SCRIPT


def _body(rec: Dict[str, Any]) -> str:
    return "\n".join(doc.get("text") or "" for doc in rec.get("docs") or [])


def _int(value) -> Optional[int]:
    try:
        return int(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def title_tag_diff(rec: Dict[str, Any], body: str, meta: Dict[str, Any]) -> Optional[str]:
    """제목 태그 `(계약방법·N억원 미만)` 가 등록 계약방법·추정가격과 어긋나는가."""
    script = baseline()
    price = _int(meta.get("입찰추정가격"))
    for tag in script.V24_TITLE_TAG.finditer(body):
        cap = int(tag.group(2)) * script.V24_UNIT[tag.group(3)]
        if tag.group(1) != str(meta.get("계약방법") or ""):
            return tag.group(0)                     # 계약방법 축
        if price is not None and price >= cap:
            return tag.group(0)                     # 예산 축 — 적힌 구간을 넘는다
    return None


# 부가세를 역산한 추정가격은 등록값과 1원까지 어긋난다 — 반올림 잔차이지 불일치가 아니다.
ROUNDING_WON = 1
# 지역제한 문구에서 광역 이름을 찾을 범위. 제한 문구와 지역명 사이에 조건이 끼는 공고가 있다.
REGION_CLAUSE_WINDOW = 120


def region_diff(rec: Dict[str, Any], body: str, meta: Dict[str, Any]) -> Optional[str]:
    """공고가 지역을 거는데 등록이 제한 없음이거나, 걸린 지역 집합이 등록과 다른가."""
    script = baseline()
    listed = meta.get("제한지역코드목록")
    restricted = meta.get("지역제한여부") == "Y"
    tagged = script.V24_REGION.search(body)
    if tagged:
        if not restricted or not listed or "[" in str(listed):
            return tagged.group(0)
        if script._region_names(tagged.group(1)) != script._region_names(str(listed)):
            return tagged.group(0)
        return None                                 # 표기가 등록과 같다 — 이 축은 일치
    found = script.REGION.search(body)
    if found and not restricted:
        return found.group(0)                       # 본문은 거는데 등록은 제한 없음
    if not restricted or not listed or "[" in str(listed):
        return None
    # 등록이 제한인 경우에도 **어느 지역인지**를 대조한다. 기존 `v24_consistent_with_meta` 가
    # 모델 근거에 대해 하는 그 집합 비교를, 근거가 없을 때를 위해 원문에 대해 한다.
    # `PPS-DEV-072`: 등록은 `경기도` 하나인데 본문은 "경기도 … 또는 제주도"다.
    registered = script._region_names(str(listed))
    for clause in script.REGION.finditer(body):
        window = body[max(0, clause.start() - REGION_CLAUSE_WINDOW):
                      clause.end() + REGION_CLAUSE_WINDOW]
        extra = set(re.findall(script.WIDE_REGION, window)) - registered
        if extra:
            return f"{clause.group(0)} … {'·'.join(sorted(extra))} (등록: {listed})"
    return None


def amount_diff(rec: Dict[str, Any], body: str, meta: Dict[str, Any]) -> Optional[str]:
    """**현재 `AXES` 에서 빠져 있다.** 아래 「왜 껐나」 참조. 코드는 재활성화 기준과 함께 남긴다.

    공고 본문이 배정예산·추정가격 어느 쪽과도 다른 사업 금액을 적는가.

    금액은 본문 어디에나 나오므로(단가·보증금) `사업/배정/추정` 근처 표기만 본다.
    그 창 안에서도 **라벨에 바로 붙은 금액 하나만** 본다. 창 안의 모든 금액을 비교하면
    같은 줄의 부가세를 불일치로 읽는다 — `PPS-DEV-19` 의
    `추정가격: 168,410,000원, 부가세: 16,841,000원` 이 그랬다. 등록 추정가격과
    정확히 같은데도 예산 축이 발화했고, dev 의 예산 축 발화 19건은 **전부 이 축 단독**이라
    그 오염이 다른 축에 가려지지도 않았다.
    """
    known = {_int(meta.get("배정예산금액")), _int(meta.get("입찰추정가격"))} - {None}
    if not known:
        return None
    script = baseline()
    for label in re.finditer(r"(?:사업|배정|추정|기초)\s*(?:예산|금액|가격)[^\n]{0,40}", body):
        amounts = [v for v in (_int(m.group(1)) for m in script.V24_AMOUNT.finditer(label.group(0)))
                   if v is not None and v >= 1_000_000]
        if not amounts:
            continue
        # **그 식에 등록 금액이 어디든 있으면 일치로 본다.** 첫 금액만 보면 산식의
        # 구성값을 총액과 비교한다 — 무라벨 `PPS-D-004155` 의
        # `사업예산: 1,750,000원 × 18명 = 31,500,000원` 이 등록 31,500,000 과 같은데도 발화했다.
        # ±1원은 부가세 역산의 반올림 잔차다 — `PPS-DEV-067` 138,045,454 대 등록 138,045,455.
        if any(any(abs(value - base) <= ROUNDING_WON for base in known) for value in amounts):
            continue
        return label.group(0).strip()
    return None


# ----- 왜 예산 축을 껐나 -----
#
# 이 축 하나가 **세 라운드 연속으로 P1 을 냈고, 매번 직전 수정의 반대 방향**이었다.
#
#   라운드 6  창 안의 모든 금액 비교 → 같은 줄 부가세를 불일치로 읽음
#             `PPS-DEV-19`  추정가격: 168,410,000원, 부가세: 16,841,000원  (등록과 정확히 일치)
#   라운드 7  "첫 금액 하나만" → 산식의 구성값을 총액과 비교
#             `PPS-D-004155`  사업예산: 1,750,000원 × 18명 = 31,500,000원  (등록 31,500,000)
#   라운드 8  "식 어디에든 있으면 일치" → **한 필드의 일치가 다른 필드의 불일치를 지움**
#             `PPS-D-001198`  기초금액 26,600,000 대 등록 배정 2,660,000 (10배!)
#                             인데 추정가격 24,181,819 ≈ 등록 24,181,818 라 침묵
#             `PPS-D-006193`  기초금액 122,881,920 대 등록 배정 122,991,920 (11만원) — 같은 모양
#   라운드 8  `ROUNDING_WON = 1` 이 너무 좁음 → 10원 단위 표시를 불일치로
#             `PPS-D-000043`  기초금액 74,460,960 대 등록 배정 74,460,958 (2원)
#             무라벨 앞 6,000건에서 최근접 차이가 2~1,000원인 사례 14건
#
# **그리고 이 축은 dev 에서 무력하다.** 남은 발화 3건이 전부 baseline 예측 v24=0 이라
# 필터 결과를 한 셀도 바꾸지 않는다 — 축을 빼도 v24 는 `4/12/4` 그대로다.
# 정밀도는 1/3(TP `29`, FP `097`·`117`)이다. **dev 이득 0, 위험은 비공개에만 있다.**
#
# 항목표 `비고` 가 예산 대조를 명시하므로 **영구 삭제하지 않는다.** 다시 켜려면 둘이 필요하다.
#
#   1. **필드별 대응** — `기초금액`·`배정예산` 은 등록 `배정예산금액` 에, `추정가격` 은
#      `입찰추정가격` 에 각각 맞춘다. 한 필드의 일치가 다른 필드의 불일치를 지우면 안 된다.
#   2. **표시 반올림 동등성** — 고정 ±1원이 아니라 본문의 표시 정밀도(10원·100원 단위)와
#      VAT 역산 관계로 판단한다.
#
# 그 둘을 갖춘 뒤에는 **무라벨 카나리를 다시 산출해야 한다** — 지금 배율은 이 축의
# 오발화를 포함한 값이 아니다(껐으므로).
DISABLED_AXES = ("예산",)


def industry_diff(rec: Dict[str, Any], body: str, meta: Dict[str, Any]) -> Optional[str]:
    """공고가 업종을 거는데 등록이 제한 없음이거나, 요구 코드가 등록 목록에 없는가.

    **제한 플래그를 코드 집합보다 먼저 본다.** `region_diff` 가 하는 순서와 같다.
    본문이 `업종코드 1169` 를 참가자격으로 걸고 메타가 `업종제한여부=N` 인데
    `면허업종제한목록` 에 1169 가 남아 있으면 집합 차이가 비어 침묵했다 —
    공고의 제한과 등록 플래그가 **정면으로 다른** v24 사례를 음성으로 내리는 경로다.
    """
    demanded = {m.group(1) for m in DOC_INDUSTRY.finditer(body)}
    if not demanded:
        return None
    restricted = meta.get("업종제한여부") == "Y"
    registered = set(META_INDUSTRY.findall(str(meta.get("면허업종제한목록") or "")))
    if not restricted:
        return next(DOC_INDUSTRY.finditer(body)).group(0)    # 본문은 거는데 등록은 제한 없음
    if not registered:
        return None                                 # 등록은 제한이라는데 코드를 못 읽었다 — 단정하지 않는다
    missing = demanded - registered
    if not missing:
        return None
    for found in DOC_INDUSTRY.finditer(body):
        if found.group(1) in missing:
            return found.group(0)
    return None


# `("예산", amount_diff)` 는 **의도적으로 빠져 있다** — 위 「왜 예산 축을 껐나」.
# `계약방법·예산` 은 제목 태그의 금액**구간**이라 다른 기계다. 그쪽은 남긴다.
AXES = (("계약방법·예산", title_tag_diff), ("지역제한", region_diff),
        ("업종", industry_diff))


def meta_discrepancies(rec: Dict[str, Any]) -> List[str]:
    """네 축에서 코드가 찾은 공고↔등록 불일치. 비어 있으면 대조로 설명되는 위반이 없다."""
    body, meta = _body(rec), rec.get("meta") or {}
    out = []
    for name, axis in AXES:
        found = axis(rec, body, meta)
        if found:
            out.append(f"{name}: {found[:120]}")
    return out


def postprocess(judgment: Dict[str, Dict[str, Any]], rec: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out = dict(baseline().postprocess(judgment, rec))
    cell = out.get("v24") or {"위반여부": 0, "근거문구": ""}
    if cell.get("위반여부") == 1 and not meta_discrepancies(rec):
        out["v24"] = {"위반여부": 0, "근거문구": ""}
    return out
