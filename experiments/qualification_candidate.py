"""참가자격 제한 4항목(v8·v7·v4·v3) 후보. 모델 뒤에 붙는 후처리 단계다.

왜 후처리인가. 등록된 회차 4개에서 세 항목이 모두 TP=0이고 v8·v7은 FP도 0이다.
FP가 0이라는 것은 모델이 dev 200건 어디에서도 1을 낸 적이 없다는 뜻이다.
정밀도 문제가 아니라 항목이 아예 발화하지 않으므로, 모델 출력을 깎는 대신
공고 원문에서 요건을 직접 찾아 올린다. 규칙은 0을 1로 올리기만 하고 내리지 않는다.

무엇을 보는가.

- v8 중복제한(실적+지역): 같은 문서에서 실적 요건과 지역 요건이 한 참가자격 묶음에 함께 온다.
  메타 `지역제한여부`로 거르지 않는다. 양성 6건 중 3건이 `N`이다.
- v7 지역제한 인접 확대: 지역 제한 조항이 서로 다른 광역 지자체를 둘 이상 열거한다.
  익명 지역을 복원하거나 외부 지도를 쓰지 않는다. 열거 형태만 본다.
- v4 특정기관·특정실적: 실적을 특정 기관이 발주·시행·납품한 것으로 한정한다.
  금액 기준을 걸지 않는다. 양성 6건의 추정가격이 2,269만~7.48억으로 흩어져 있다.
  민간까지 열어 둔 실적은 특정기관 제한이 아니다(`PPS-DEV-054`가 v4=0인 이유).
- v3 실적제한 1배수 이상: **이 항목만 1을 0으로 내린다.** 항목표 비고가 `사업예산 기준`이고
  모델은 실적제한을 보면 배수를 따지지 않고 1을 낸다. 요구 실적금액을 읽어
  사업예산의 1배에 못 미치면 내린다. 금액이나 예산을 못 읽으면 건드리지 않는다.
  모르는 것을 근거로 내리면 정답 양성을 잃는다.

공통으로 제안서 평가 배점표와 제출 서식은 참가 제한이 아니므로 제외한다.

인터페이스는 공고 1건과 그 공고의 모델 출력뿐이다. 정답·다른 공고 통계는 받지 않는다.
"""

import importlib.util
import os
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ("v8", "v7", "v4")
_script = None

# 참가자격을 실적으로 거는 문구. 조문의 낱말은 `실적`·`준공금액`이고
# 어미(`보유`·`있는`·`갖춘`·`충족`·`우수한`)는 dev 공고에서 관측한 표기다.
# 제출서류 목록의 `실적증명서 1부`나 평가 배점표의 `실적`은 참가 제한이 아니므로 잡지 않는다.
PERFORMANCE = re.compile(
    r"실적(?:을|이)?\s*(?:보유|있는|갖춘|충족|우수한)"
    r"|(?:이상|초과)(?:인|의)?\s*실적"
    r"|실적(?:증명서?)?\s*(?:보유|소지)"
    r"|수행(?:한|실적)\s*실적"
    r"|준공(?:금)?액(?:이)?\s*[^\n]{0,40}이상"
)

# 참가자격을 지역으로 거는 문구. `본점소재지`·`주된 영업소`·`관할구역`은 조문 표현이다.
# `관내에`·`~에 소재한`은 dev 공고에서만 본 표기이며, 후자는
# `경북에 소재한 실적이 우수한 업체`처럼 사이에 말이 끼는 공고를 위해 둔다.
REGION = re.compile(
    r"본점\s*소재지"
    r"|주된\s*영업소"
    r"|소재지를\s*[^\n]{0,60}(?:에)?\s*(?:두고|둔)"
    r"|관내에\s*(?:있는|소재)"
    r"|에\s*소재한\s*(?:업체|자|업체로)"
    r"|지역\s*제한"
    r"|(?:에|내에)\s*소재(?:한|하고|하는)"
)

# 두 요건이 같은 참가자격 묶음에 속한다고 볼 글자 거리.
# dev에서 가장 먼 양성은 `PPS-DEV-054`의 705자이고, 1400자까지 늘려도 FP는 늘지 않았다.
WINDOW = 800

# 제출 근거문구 셀 상한(script.EVIDENCE_MAX)보다 짧게 잘라 후처리에서 깎이지 않게 한다.
QUOTE_MAX = 480


def _pairs(text):
    """같은 문서에서 창 안에 함께 있는 (실적, 지역) 위치 쌍.

    한 인용에 두 절을 **함께 담을 수 있는 쌍을 먼저** 돌려준다. 그다음이 가까운 순이다.
    거리만으로 고르면 더 가깝지만 인용 상한을 넘는 쌍을 집어, 근거문구가 항목의
    절반만 입증하게 된다.
    """
    perf = [(m.start(), m.end()) for m in PERFORMANCE.finditer(text)]
    region = [(m.start(), m.end()) for m in REGION.finditer(text)]
    found = [(abs(p[0] - r[0]), p, r)
             for p in perf for r in region if abs(p[0] - r[0]) <= WINDOW]

    def order(item):
        distance, p, r = item
        span = max(p[1], r[1]) - min(p[0], r[0])
        return (span > QUOTE_MAX, distance)

    return sorted(found, key=order)


def _quote(text, perf, region):
    """두 요건을 덮는 원문 조각. 상한을 넘으면 실적 요건 쪽을 남긴다.

    지역 제한만 있는 공고는 v5·v6·v7이 따로 다룬다. v8을 가르는 것은 실적 쪽이므로
    둘을 한 인용에 못 담으면 실적 문구를 남긴다.

    이 폴백은 근거문구가 항목의 절반만 입증한다는 뜻이다. 근거문구 셀은 한 개의
    연속 인용이고 500자가 상한이라, 두 절이 그보다 멀면 한쪽을 버리는 수밖에 없다.
    dev에서는 `PPS-DEV-054` 한 건이 여기 해당한다(두 절이 703자 떨어져 있다).
    로컬 채점기는 근거를 보지 않으므로 이 손실은 점수에 안 나타난다. 서버만 본다.
    """
    lo, hi = min(perf[0], region[0]), max(perf[1], region[1])
    if hi - lo > QUOTE_MAX:
        lo, hi = perf[0], perf[1]
    lo = max(0, lo - 40)
    hi = min(len(text), hi + 60)
    quote = text[lo:hi]
    if len(quote) > QUOTE_MAX:
        quote = quote[:QUOTE_MAX]
    return quote.strip()


def detect(rec):
    """공고 1건에서 중복제한 근거를 찾는다. 없으면 None.

    배점표·서식 문맥은 v4와 같은 가드로 뺀다. 지역업체 참여 가점과 유사실적 배점이
    한 표에 나란히 있는 제안요청서가 흔해서, 가드가 없으면 그 표에서 발화한다.
    dev 음성 194건에는 창 안에 두 요건이 들어오는 공고가 없어 이 경로가 한 번도
    실행되지 않았다. 통과가 안전을 뜻하지 않는다.
    """
    for doc in rec.get("docs", []):
        text = doc.get("text") or ""
        for _, perf, region in _pairs(text):
            if not _is_qualification_context(text, perf[0], region[0]):
                continue
            quote = _quote(text, perf, region)
            if quote and unicodedata.normalize("NFC", quote) in unicodedata.normalize("NFC", text):
                return {"doc_id": doc.get("doc_id"), "doc_type": doc.get("type"),
                        "performance": text[perf[0]:perf[1]],
                        "region": text[region[0]:region[1]],
                        "distance": abs(perf[0] - region[0]),
                        "근거문구": quote}
    return None


# ===== v7 지역제한 인접 확대 =====
# 지역 제한을 여는 참가자격 문구.
REGION_ANCHOR = re.compile(
    r"본점\s*소재지|본점소재지|주된\s*영업소|소재지를\s*[^\n]{0,80}(?:두고|둔)"
    r"|관할구역\s*안에|지역제한|소재지가|주된\s*영업소를\s*둔"
)
# 광역 지자체 이름. 제공 공고의 표기 그대로이며 외부 지도·좌표를 쓰지 않는다.
# 시·군·구 단위는 v6이 다루므로 여기서는 광역만 센다.
WIDE_REGION = (r"[가-힣]{2}특별자치도|[가-힣]{2}특별자치시|[가-힣]{2,3}광역시|서울특별시"
               r"|경기도|강원도|충청북도|충청남도|전라북도|전라남도|경상북도|경상남도|제주도")
# 두 지역 사이에 따옴표가 끼는 공고가 있다(`"대구광역시"또는"경상북도"`).
_Q = r"[\s\"'“”‘’]*"
REGION_PAIR = re.compile(
    r"(" + WIDE_REGION + r")" + _Q + r"[^\n]{0,60}?(?:또는|,|·|및)" + _Q + r"(" + WIDE_REGION + r")")

# 지역 제한 조항이 이어지는 범위. 120~300자에서 결과가 같아 가운데를 쓴다.
REGION_WINDOW = 200

# 지역제한을 걸 수 있는 추정가격 상한. 항목명의 `고시금액 미만`이 이것이다.
# 이 금액 이상인데 지역을 제한하면 v7이 아니라 v5(고시금액 이상 지역제한)다.
#
# 용역·물품
#   국가: 시행령 제21조제1항제6호 → 시행규칙 제24조제2항제2호 `고시금액`
#         → 재정경제부 고시 `물품 및 용역: 2억 3천만 원`
#   지방: 시행령 제20조제1항제6호 → 시행규칙 제24조제2호 나목
#
# 이 후보는 지방 용역·물품을 5억원 하나로 둔다. 지방 금액은 발주기관에 따라 둘이다 —
# 시·도(세종 제외) 3억 5천만원, 그 밖 5억원(docs/rules.md 지역제한 금액과 고시금액).
# 운영 코드는 `script.py`의 `region_price_limit()`이 그 둘을 가른다. 이 파일은 후보 기록이다.
#
# 공사
#   국가: 시행규칙 제24조제2항제1호 — 건설공사(전문 제외)는 고시금액(공사 88억원),
#         전문공사·그 밖의 공사는 10억원.
#   지방: 시행규칙 제24조제1호 — 종합공사 150억원, 전문공사·그 밖의 공사 10억원.
# **메타로는 종합공사와 전문공사를 가를 수 없다.** 낮은 쪽(10억원)을 쓰면 종합공사에서
# 정답 양성을 막고, 높은 쪽을 쓰면 전문공사를 못 막는다. 막는 쪽이 틀리면 양성을
# 잃으므로 넓은 쪽을 쓴다. 이 선택의 결과는 10억~150억 구간의 전문공사에서
# 이 게이트가 막지 못한다는 것이다. dev에 공사 건이 없어 관측되지 않았다.
REGION_PRICE_LIMIT = {
    ("국가계약법", "용역물품"): 230_000_000,
    ("지방계약법", "용역물품"): 500_000_000,
    ("국가계약법", "공사"): 8_800_000_000,
    ("지방계약법", "공사"): 15_000_000_000,
}
GOODS_AND_SERVICE_SCOPE = ("일반용역", "물품(내자)")


def _price_scope(work_type):
    """업무구분을 조문이 금액을 나누는 갈래로 옮긴다. 모르면 None."""
    if work_type in GOODS_AND_SERVICE_SCOPE:
        return "용역물품"
    if work_type and "공사" in work_type:
        return "공사"
    return None


def region_restriction_allowed(rec):
    """추정가격이 지역제한 허용 상한 미만인지. 판단할 수 없으면 True를 돌려준다.

    모르는 것을 근거로 막지 않는다. 막는 쪽이 틀리면 정답 양성을 잃는다.
    """
    meta = rec.get("meta") or {}
    scope = _price_scope(meta.get("업무구분"))
    limit = REGION_PRICE_LIMIT.get((meta.get("적용계약법"), scope))
    price = meta.get("입찰추정가격")
    if limit is None or not price:
        return True
    return price < limit


# ===== v4 특정기관·특정실적 =====
# 아래 표현은 두 갈래다. `조문`은 제공 법령 원문에 있는 낱말이고,
# `dev 관측`은 공개 dev 200건의 공고에서만 본 낱말이다. 후자는 비공개 test에서
# 다른 표기를 만날 수 있으므로 늘리거나 줄일 때 이 구분을 유지한다.
INSTITUTION_IN_LAW = (r"국가기관|공공기관|정부투자기관|지방자치단체|지자체|공기업"
                      r"|준정부기관|정부기관|교육청|고등학교|대학교")
INSTITUTION_FROM_DEV = r"대학병원|종합병원|국공립|중고등학교|초등학교|중학교|중앙정부"
INSTITUTION = INSTITUTION_IN_LAW + "|" + INSTITUTION_FROM_DEV

# 실적을 그 기관에 묶는 동사. 전부 제공 법령에 있는 낱말이다.
ORDERED = r"발주|시행|납품|공급|체결|수주"

# 민간까지 인정하면 특정기관 제한이 아니다. `민간`은 조문 표현이고 나머지는 dev 관측이다.
OPEN_TO_PRIVATE = re.compile(r"민간|일반\s*기업|기업체\s*포함|개인\s*포함")

# 참가자격이 아닌 문맥. 배점표·서식의 실적은 참가를 제한하지 않는다.
# 전부 공고 서식에서 온 표현이라 조문 근거가 없다. dev에서 오탐 5건을 걷어낸 근거다.
NOT_QUALIFICATION = re.compile(
    r"배점|평가\s*항목|평가표|정량평가|정성평가|가점|심사\s*기준|점\s*배점"
    r"|평가\s*기준|평가대상\s*기준|제안서\s*평가|서식|별지|제출서류|증빙서류")

# 참가자격 조항의 끝맺음. 공고 문체라 조문 근거가 없다.
QUALIFYING_TAIL = re.compile(
    r"업체이어야|업체여야|업체만|자격이\s*있|있는\s*업체|보유한\s*업체|있어야\s*합니다"
    r"|자로\s*제한|하여야\s*합니다|참가\s*자격")

# 기관이 발주한 실적임을 동사로 밝힌 형태.
INSTITUTION_ORDERED = re.compile(
    r"(?:" + INSTITUTION + r")[^\n]{0,12}?(?:이|가|에서|에게|에|,)?\s*(?:" + ORDERED
    + r")(?:한|된|하는|하여)[^\n]{0,80}?실적")
# 동사 없이 기관만 한정한 형태. 참가자격 어미를 함께 요구한다.
INSTITUTION_NEAR = re.compile(r"(?:" + INSTITUTION + r")[^\n]{0,60}?실적")

CONTEXT = 300    # 민간 포함 여부를 볼 앞뒤 범위. 그 문구는 실적 조항 안팎에 걸쳐 온다
TAIL_REACH = 60  # 참가자격 어미를 찾을 범위


# 참가자격 절을 여는 머리글. 이것을 만나면 위로 더 거슬러 올라가지 않는다.
QUALIFICATION_HEADING = re.compile(r"참가\s*자격|자격요건|참가자격")
HEADING_LOOKBACK = 40   # 위로 훑을 줄 수 상한. 문서 전체를 훑지 않는다


def _line(text, pos):
    """`pos`가 놓인 줄. 공고는 조항마다 줄을 바꾸므로 이것이 절 경계다."""
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    return text[start:] if end < 0 else text[start:end]


def _is_qualification_context(text, *positions):
    """그 조항이 참가자격 절 안에 있는지. 배점표·서식 절 안이면 아니다.

    앞뒤를 같은 글자 반경으로 재면 안 된다. 두 방향이 비대칭이기 때문이다.
    - **뒤**에는 참가자격 바로 다음에 제출서류·심사기준 목록이 붙는다.
      `PPS-DEV-048`의 참가자격 `다.` 항목은 300자 뒤의 `6. 제출서류` 때문에 실제로 죽었다.
      그래서 뒤는 보지 않는다.
    - **앞**에는 배점표·서식의 머리글이 온다. `배점 | 1점` 같은 표 머리가 한 줄 위에,
      `【서식 11】`이 여러 줄 위에 있다. 그래서 앞으로는 걸어 올라간다.

    올라가다 참가자격 머리글을 만나면 거기서 멈춘다. 그 아래는 참가자격 절이다.
    """
    for pos in positions:
        line_start = text.rfind("\n", 0, pos) + 1
        if NOT_QUALIFICATION.search(_line(text, pos)):
            return False
        for line in reversed(text[:line_start].split("\n")[-HEADING_LOOKBACK:]):
            if QUALIFICATION_HEADING.search(line):
                break
            if NOT_QUALIFICATION.search(line):
                return False
    return True


def _span_quote(text, start, end):
    """원문 그대로의 인용 조각. 상한을 넘기지 않는다."""
    lo = max(0, start - 40)
    hi = min(len(text), end + 60)
    quote = text[lo:hi]
    if len(quote) > QUOTE_MAX:
        quote = quote[:QUOTE_MAX]
    return quote.strip()


def _contains(text, quote):
    return bool(quote) and unicodedata.normalize("NFC", quote) in unicodedata.normalize("NFC", text)


def detect_region_expansion(rec):
    """v7. 고시금액 미만 계약의 지역 제한이 서로 다른 광역 지자체 둘 이상으로 확대됐는지.

    없으면 None. 고시금액 이상이면 v5의 몫이므로 여기서 발화하지 않는다.
    """
    if not region_restriction_allowed(rec):
        return None
    for doc in rec.get("docs", []):
        text = doc.get("text") or ""
        for anchor in REGION_ANCHOR.finditer(text):
            segment_start = max(0, anchor.start() - 150)
            segment = text[segment_start:anchor.end() + REGION_WINDOW]
            for pair in REGION_PAIR.finditer(segment):
                if pair.group(1) == pair.group(2):
                    continue
                start = segment_start + pair.start()
                quote = _span_quote(text, start, segment_start + pair.end())
                if _contains(text, quote):
                    return {"doc_id": doc.get("doc_id"), "doc_type": doc.get("type"),
                            "regions": [pair.group(1), pair.group(2)],
                            "근거문구": quote}
    return None


def detect_institution_performance(rec):
    """v4. 실적을 특정 기관이 발주·시행·납품한 것으로 한정했는지. 없으면 None."""
    for doc in rec.get("docs", []):
        text = doc.get("text") or ""
        for pattern, needs_tail in ((INSTITUTION_ORDERED, False), (INSTITUTION_NEAR, True)):
            for match in pattern.finditer(text):
                around = text[max(0, match.start() - CONTEXT):match.end() + CONTEXT]
                if OPEN_TO_PRIVATE.search(around):
                    continue
                if not _is_qualification_context(text, match.start()):
                    continue
                if needs_tail and not QUALIFYING_TAIL.search(
                        text[match.end():match.end() + TAIL_REACH]):
                    continue
                quote = _span_quote(text, match.start(), match.end())
                if _contains(text, quote):
                    return {"doc_id": doc.get("doc_id"), "doc_type": doc.get("type"),
                            "clause": match.group(0), "근거문구": quote}
    return None


# ===== v3 실적제한 1배수 이상 =====
# 항목표 비고가 `사업예산 기준`이다. 요구 실적금액이 사업예산의 1배 미만이면 1배수 제한이 아니다.
# 이 규칙만 1을 0으로 내린다. 금액을 못 읽으면 모델 판정을 그대로 둔다.
# 금액은 자리수 단위를 이어 붙여 적는다 — `1억 5천만원`은 1억이 아니라 1억 5천만원이다.
# 단위마다 따로 읽고 최댓값을 고르면 그 표기를 33% 낮게 읽어 정답 양성을 내려 버린다.
# 그래서 한 번의 일치로 억·천만·만·원 자리를 모두 먹고 더한다.
MONEY = re.compile(
    r"(?=\d)"
    r"(?:(\d+(?:\.\d+)?)\s*억)?"
    r"\s*(?:(\d+(?:\.\d+)?)\s*천만)?"
    r"\s*(?:([\d,]+)\s*만)?"
    r"\s*(?:([\d,]+))?"
    r"\s*(원)?"
)
PERF_WORD = re.compile(r"실적")
MONEY_REACH = 180      # 실적 문구 앞뒤에서 금액을 찾을 범위
MONEY_MIN = 1_000_000            # 사람 수·건수를 금액으로 읽지 않기 위한 하한
MONEY_MAX = 100_000_000_000      # 오독한 큰 수를 버리는 상한


def parse_money(match):
    """한 일치의 억·천만·만·원 자리를 더해 원 단위로 돌려준다. 금액이 아니면 None.

    자리 표시가 하나도 없는 맨 숫자는 `원`이 붙었을 때만 금액으로 본다.
    그렇지 않으면 세부품명번호 10자리나 날짜를 금액으로 읽는다.
    """
    eok, cheonman, man, plain, won = match.groups()
    total = 0
    if eok:
        total += int(float(eok) * 100_000_000)
    if cheonman:
        total += int(float(cheonman) * 10_000_000)
    if man:
        total += int(man.replace(",", "")) * 10_000
    if plain:
        if not (eok or cheonman or man) and not won:
            return None
        total += int(plain.replace(",", ""))
    if not (eok or cheonman or man or plain):
        return None
    return total


def _money_near(text, pos):
    """실적 문구 근처의 원 단위 금액. 억·천만·만원 표기를 모두 원으로 바꾼다."""
    segment = text[max(0, pos - MONEY_REACH):pos + MONEY_REACH]
    values = []
    for match in MONEY.finditer(segment):
        value = parse_money(match)
        if value is not None:
            values.append(value)
    return values


def required_performance(rec):
    """참가자격이 요구하는 실적 금액의 최댓값. 읽지 못하면 None."""
    best = None
    for doc in rec.get("docs", []):
        text = doc.get("text") or ""
        for match in PERF_WORD.finditer(text):
            if not _is_qualification_context(text, match.start()):
                continue
            for value in _money_near(text, match.start()):
                if MONEY_MIN <= value <= MONEY_MAX and (best is None or value > best):
                    best = value
    return best


def performance_below_budget(rec):
    """v3. 요구 실적금액이 계약목적물 추정가격의 1배 미만이면 그 배수를 돌려준다. 아니면 None.

    기준은 조문대로 추정가격이다(국가·지방 시행규칙 제25조제2항제1호 나목).
    추정가격이 없으면 배정예산금액으로 물러선다. dev에서는 두 기준의 1배 경계 판정이 같다.
    금액이나 기준액을 읽지 못하면 None을 돌려준다. 모르는 것을 근거로 내리지 않는다.
    """
    meta = rec.get("meta") or {}
    basis = meta.get("입찰추정가격") or meta.get("배정예산금액")
    if not basis:
        return None
    required = required_performance(rec)
    if required is None:
        return None
    ratio = required / basis
    return ratio if ratio < 1.0 else None


RULES = {"v8": detect, "v7": detect_region_expansion, "v4": detect_institution_performance}


def apply(judgment, rec):
    """모델 판정에 v8·v7·v4를 올리고 v3만 내린다. 다른 20항목은 그대로 돌려준다.

    v8·v7·v4는 이미 1이면 모델 근거를 유지하고, 0일 때만 올린다.
    v3는 요구 실적금액이 예산 1배 미만인 것을 읽었을 때만 내린다.
    """
    out = dict(judgment)
    for item in ITEMS:
        cell = dict(out.get(item) or {"위반여부": 0, "근거문구": None})
        if cell.get("위반여부") == 1:
            continue
        hit = RULES[item](rec)
        if hit:
            out[item] = {"위반여부": 1, "근거문구": hit["근거문구"]}
    v3 = dict(out.get("v3") or {"위반여부": 0, "근거문구": None})
    if v3.get("위반여부") == 1 and performance_below_budget(rec) is not None:
        out["v3"] = {"위반여부": 0, "근거문구": None}
    return out


def _submission():
    """제출 코드를 한 번만 읽는다. 후보는 script.py를 고치지 않고 뒤에 붙는다.

    **재생 도구가 이미 적재한 것이 있으면 그것을 쓴다.** `tools/replay_run.py` 는 제출 코드를
    `sys.modules["submission"]` 에 등록하고 "후보가 저장소 루트의 script.py 를 따로 읽지 않게"
    한다고 적어 두었는데, 이 함수가 그것을 무시하고 사본을 하나 더 읽고 있었다.
    사본은 재생이 `load_sme_reference()` 로 채운 참조표를 모른다 — 규칙을 하나도 켜지 않은
    재생이 main 과 v11 4셀·v12 1셀 어긋났고, Macro 가 0.020707070707 내려갔다(실측).
    """
    global _script
    loaded = sys.modules.get("submission")
    if loaded is not None and hasattr(loaded, "postprocess"):
        return loaded
    if _script is None:
        spec = importlib.util.spec_from_file_location("submission", ROOT / "script.py")
        _script = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_script)
    return _script


# ===== v6 시·군·구 지역제한 (D9) =====
# 운영진이 S7-15 에서 `단위=기초` 를 시·군·구 지명 표시라고 공인했다. 지역제한은 광역까지이고
# 시·군·구 제한은 위반이다. 규칙은 넷이고 **따로 켜고 따로 잰다** — 어느 것을 채택할지는 A가 정한다.
#
#   U        올림. 모델이 0인데 참가자격의 지역 제한 문장에 기초 신호가 있다
#   L1       내림. 모델이 1인데 어느 지역 제한 문장에도 기초 신호가 없다 (v6 정의 밖)
#   L2C      내림. 지방 소액수의 견적의 관할 제한 예외 — (a)(b)(c) 를 전부 확인했을 때만(보수)
#   L2E      내림. 같은 예외 — (a)(b) 만 확인하고 (c) 는 관할로 추정한다(추정)
#
# 기본값은 **아무것도 켜지 않음**이다. 켜지 않으면 이 절은 v6 을 건드리지 않아서
# 먼저 있던 v8·v7·v4·v3 재생이 그대로 재현된다.
# 환경변수 `D9_V6_RULES` 로 켠다: `D9_V6_RULES=U`, `D9_V6_RULES=U,L1`, `D9_V6_RULES=L2E` …
V6_RULE_NAMES = ("U", "L1", "L2C", "L2E")
V6_RULES_ENV = "D9_V6_RULES"
# 이 후보에는 v8·v7·v4·v3 이 먼저 들어 있다. v6 규칙 하나만의 변경 셀을 세려면 그 넷을 꺼야 한다.
# `D9_V6_ONLY=1` 이면 앞의 넷을 건너뛰고 제출 코드 그대로에 v6 만 얹는다.
V6_ONLY_ENV = "D9_V6_ONLY"


def v6_only():
    return os.environ.get(V6_ONLY_ENV, "").strip() not in ("", "0", "false", "False")


def enabled_v6_rules():
    """켜져 있는 v6 규칙 이름 집합. 환경변수가 비어 있으면 빈 집합이다."""
    raw = os.environ.get(V6_RULES_ENV, "")
    names = {part.strip().upper() for part in raw.replace(";", ",").split(",") if part.strip()}
    unknown = names - set(V6_RULE_NAMES)
    if unknown:
        raise ValueError(f"{V6_RULES_ENV} 에 모르는 규칙 이름: {sorted(unknown)}")
    return names


# 참가 업체의 소재 지역을 한정하는 문장을 여는 표현. 낱말 목록이 아니라 역할로 정했고,
# 맞았는지는 검사의 보호 사례 표가 정한다. `지역 업체`(`PPS-DEV-061`)처럼 `소재지` 류 낱말이
# 하나도 없는 꼴이 실제로 있어서, 소재지 계열만으로는 정탐을 놓친다.
REGION_LIMIT_ANCHOR = re.compile(
    r"본점\s*소재지|주된\s*영업소|영업소(?:가|를|의|는)|사업장의?\s*소재지"
    r"|소재지를|소재지\)?\s*가|소재지가"
    r"|관내\s*(?:에\s*)?(?:있는|소재|업체)"
    r"|지역\s*제한|지역제한|지역\s*업체|관할\s*구역")

# 지역 이름이 나와도 참가 업체의 소재 지역을 한정하지 않는 문장. 역할로 가른다.
# 무라벨 2,000건에서 U 가 올린 11건 중 4건이 전부 여기였다(실측) — dev 2건으로는 안 보였다.
#   · 소송 관할 법원  `소송의 관할 법원은 [지역:r1…]의 소재지를 관할하는 각급 법원으로 한다`
#   · 지역업체 보호·지원 조항  `제19조([수요기관(기초자치단체)…] 지역업체 보호 및 지원)`
#   · 동점자 우선순위·우대  `… 소재지가 [지역:r1…] 내에 있는 업체를 우선으로 한다`
# 앞의 둘은 계약 이행·분쟁 조항이고 셋째는 순위를 매길 뿐 참가를 막지 않는다.
NOT_REGION_LIMIT = re.compile(
    r"관할\s*법원|소송|재판"
    r"|지역\s*업체\s*보호|지역업체\s*보호|보호\s*및\s*지원|지원지침"
    r"|우선으로\s*한다|우선한다|우선순위|선순위|우대|가점")

# 발주기관 토큰으로 기초를 적은 공고가 있다(`PPS-DEV-071`: `[수요기관(기초자치단체)]내에 소재`).
# data.md D3 이 기관 유형을 판단에 쓸 수 있다고 한다. 지명을 복원하지는 않는다(R10).
# **그 토큰이 제한의 대상일 때만** 기초 신호다. `[수요기관(기초자치단체)]이 제시하는 시방서에
# 따라` 처럼 발주기관을 가리키기만 하는 문장은 제한이 `충청북도`(광역)인데도 기초로 읽힌다.
BASIC_AGENCY_TOKEN = "[수요기관(기초자치단체)"
BASIC_AGENCY_TARGET = re.compile(
    r"\[수요기관\(기초자치단체\)[^\]]*\]\s*(?:내|안|관내)?\s*(?:에|에서)?\s*(?:소재|있는|위치|둔|두고)"
    r"|\[수요기관\(기초자치단체\)[^\]]*\]\s*(?:내에|관내에|안에)")

def has_confirmed_basic_signal(text):
    """**올리는 쪽**이 쓰는 기초 신호. 익명화 토큰과 발주기관 토큰만 센다.

    dev 입력은 200건 전부 `anon_applied=True` 라 시·군·구 지명이 `[지역:…단위=기초…]` 로
    바뀌어 있다. 그러므로 익명화를 뚫고 남은 `○○시` 꼴 낱말은 기초 지명이라는 증거가 아니다 —
    운영진이 공인한 것은 `단위=기초` 토큰이지 이름이 아니고, 이름으로 적은 공고(`066`)는
    지명 목록이 없어 이번 범위 밖이다.

    실제로 이름으로 읽으면 무너진다. `script.BASIC_REGION_NAME` 은 `[가-힣]{2,4}(?:시|군|구)`
    라서 **`체결시`·`반드시`** 같은 보통 낱말을 기초 지명으로 읽는다. 그 둘이 dev 에서
    `PPS-DEV-32`·`PPS-DEV-076` 을 올려 오탐 2건을 만들었다(실측). U 는 모를 때 올리지 않는다.
    """
    text = text or ""
    if BASIC_AGENCY_TARGET.search(text):
        return True
    return any(unit == "기초" for unit in _submission().ANON_REGION.findall(text))


def has_basic_signal(text):
    """**내리는 쪽**이 쓰는 기초 신호. 위의 토큰에 더해 이름으로 적은 꼴까지 센다.

    방향이 다르면 기본값도 달라야 한다. 내리는 규칙에서 이 함수가 참이면 **내리지 않는다**.
    그래서 여기서는 의심스러운 것을 기초로 세는 쪽이 안전하다 — `경기도 광주시` 처럼 광역
    축약명과 기초 지명이 겹치는 이름을 광역으로 단정하면 정탐을 내린다.
    이름 읽기는 운영 게이트의 `script._has_basic_unit()` 을 그대로 쓴다.
    """
    text = text or ""
    if has_confirmed_basic_signal(text) or BASIC_AGENCY_TOKEN in text:
        return True
    return _submission()._has_basic_unit(text)


def _doc_lines(text):
    """(시작위치, 줄) 쌍. 공고는 조항마다 줄을 바꾸므로 이것이 절 경계다."""
    pos = 0
    for line in (text or "").split("\n"):
        yield pos, line
        pos += len(line) + 1


def region_limit_sentences(rec):
    """참가자격 문맥에서 참가 업체의 소재 지역을 한정하는 문장 전부.

    판정 단위는 모델 인용이 아니라 레코드의 `docs` 전부다(작업서 "공통 정의").
    """
    found = []
    for doc in rec.get("docs", []):
        text = doc.get("text") or ""
        for start, line in _doc_lines(text):
            if not line.strip() or not REGION_LIMIT_ANCHOR.search(line):
                continue
            if NOT_REGION_LIMIT.search(line) or not _is_qualification_context(text, start):
                continue
            found.append({"doc_id": doc.get("doc_id"), "doc_type": doc.get("type"),
                          "text": text, "start": start, "sentence": line})
    return found


def basic_region_sentences(rec):
    """위 문장 중 기초 신호가 있는 것. 내리는 쪽 기준이다(넓게 센다).

    내리는 쪽은 줄 단위로 넓게 본다 — 기초일 수 있으면 내리지 않는 것이 안전하다.
    """
    return [hit for hit in region_limit_sentences(rec) if has_basic_signal(hit["sentence"])]


# 절 경계. 쉼표·세미콜론으로 자르되 **괄호 안에서는 자르지 않는다** —
# `본점소재지(개인사업자인 경우에는 … 허가ㆍ인가ㆍ면허ㆍ등록ㆍ신고 …)가 [수요기관(기초자치단체)]내에`
# 처럼 제한 대상과 토큰 사이에 괄호가 통째로 끼는 문장이 흔하다.
CLAUSE_BREAK = ",，;；"
CLAUSE_OPEN = "([{（［｛【〔「『"
CLAUSE_CLOSE = ")]}）］｝】〕」』"
# **쉼표만으로는 모자란다.** 접속 어미로 이어 붙인 문장이 흔하고, 그 앞뒤는 역할이 다르다 —
# `본점소재지가 경기도 […광역…]에 있는 업체이며 납품장소는 […기초…]` 에 쉼표가 없다.
# 어미에서도 끊어야 제한 대상과 납품 장소가 한 도막에 들어오지 않는다(PR #114 재리뷰 P1).
CLAUSE_CONNECTIVE = re.compile(r"(?:이며|하며|되며|으며|이고|하고|되고|고서|한\s*뒤|한\s*후)(?=\s)")


def _clauses(line):
    """(줄 안 시작위치, 절). 쉼표·세미콜론에서 자른다. 괄호 깊이를 센다."""
    depth = start = 0
    for index, char in enumerate(line):
        if char in CLAUSE_OPEN:
            depth += 1
        elif char in CLAUSE_CLOSE:
            depth = max(0, depth - 1)
        elif depth == 0 and char in CLAUSE_BREAK:
            yield start, line[start:index]
            start = index + 1
    yield start, line[start:]


def _segments(line):
    """(줄 안 시작위치, 도막). 절을 다시 접속 어미에서 자른 것 — 역할을 가르는 단위다."""
    for clause_start, clause in _clauses(line):
        depth = start = 0
        for index, char in enumerate(clause):
            if char in CLAUSE_OPEN:
                depth += 1
            elif char in CLAUSE_CLOSE:
                depth = max(0, depth - 1)
        depth = 0
        cut = 0
        for match in CLAUSE_CONNECTIVE.finditer(clause):
            if _bracket_depth(clause, match.start()):
                continue
            yield clause_start + cut, clause[cut:match.end()]
            cut = match.end()
        yield clause_start + cut, clause[cut:]


def _bracket_depth(text, position):
    """`position` 이 괄호 안인가."""
    depth = 0
    for char in text[:position]:
        if char in CLAUSE_OPEN:
            depth += 1
        elif char in CLAUSE_CLOSE:
            depth = max(0, depth - 1)
    return depth > 0


# 지역 토큰의 역할을 참가 제한이 아닌 것으로 바꾸는 말. 제한 대상과 토큰 사이에 이것이
# 끼면 그 토큰은 제한 대상이 아니다 — 납품 장소·현장·개찰 장소다.
ROLE_SWITCH = re.compile(
    r"납품\s*장소|납품장소|납품\s*소재지|배송|인도\s*장소|설치\s*장소"
    r"|사업\s*장소|사업장소|사업\s*위치|과업\s*(?:위치|장소|구역)|이행\s*장소"
    r"|공사\s*위치|현장\s*위치|용역\s*위치|대상\s*위치|위\s*치\s*[:：]"
    r"|개찰|설명회|접수\s*장소|제출\s*장소")

# ===== 올림의 긍정 근거 =====
# 네 라운드 연속 같은 자리에서 오탐이 났다. 원인은 하나다 — **관계를 "반증이 없음" 으로
# 증명하려 했다.** 앵커가 있고 토큰이 있고 사이에 금지어가 없으면 묶었으니, 금지 목록에
# 없는 표현이 나올 때마다 뚫렸다. 그래서 기준을 뒤집는다: **무엇이 있으면 묶는가**를 적는다.
#
# 지역 제한 문장은 한국어 공고에서 두 꼴 중 하나다.
#   ① 주어-서술  `<참가 업체의 소재지> ... <지역> ... <두다/소재하다/있다>`
#   ② 융합       `지역제한(<지역>)` · `<지역> 지역 업체` — 주어와 서술이 한 낱말에 붙었다
# ①은 **주어가 참가 업체의 것**이어야 한다. `납품장소의 소재지가 […기초…]` 는 `소재지` 가
# 있어도 그 주어가 납품 장소다. 그래서 `소재지` 를 홀로 앵커로 쓰지 않고, 머리 낱말까지
# 묶어서 본다.
PARTICIPANT_SUBJECT = re.compile(
    r"(?:법인\s*등기(?:부|사항증명서)?\s*상\s*)?"
    r"(?:본점|본사|주된\s*영업소|주\s*사무소|주사무소|사업장|영업소)"
    r"\s*(?:의\s*)?(?:소재지|소재\s*지)?(?:가|는|를|을|은|에)?")
# ②. 주어와 서술이 붙어 있어 토큰이 앞에 와도 된다.
FUSED_LIMIT = re.compile(r"지역\s*제한|지역제한|지역\s*업체|관내\s*업체|관할\s*구역")
# ①의 서술. 토큰이 이 서술의 자리에 놓여야 제한이 성립한다.
LOCATED_PREDICATE = re.compile(r"둔|두고|두어|둘|소재|있는|있어야|위치|한정|제한")
PREDICATE_REACH = 40   # 토큰 뒤에서 서술을 찾을 범위(괄호를 뺀 뒤)


def confirmed_basic_region_sentences(rec):
    """**절 단위로** 제한 대상과 기초 토큰이 이어진 자리. 올리는 쪽 기준이다(좁게 센다).

    줄 단위로 보면 안 된다. 한 줄에 참가자격 제한과 납품 장소가 같이 오는 공고가 있어서,
    `본점소재지가 경기도 [지역:r1|단위=광역|…]에 있는 업체, 납품장소는 [지역:r2|단위=기초|…]`
    를 "참가자격이 시·군·구로 제한됐다"로 읽는다. 제한은 광역인데 기초 토큰의 역할은 납품
    장소다 — 올림은 **같은 절에서** 둘이 이어질 때만 허용한다(PR #114 리뷰 P1).
    """
    found = []
    for doc in rec.get("docs", []):
        text = doc.get("text") or ""
        for line_start, line in _doc_lines(text):
            if not line.strip() or not REGION_LIMIT_ANCHOR.search(line):
                continue
            if NOT_REGION_LIMIT.search(line) or not _is_qualification_context(text, line_start):
                continue
            for offset, segment in _segments(line):
                if NOT_REGION_LIMIT.search(segment) or not _binds_limit_to_token(segment):
                    continue
                found.append({"doc_id": doc.get("doc_id"), "doc_type": doc.get("type"),
                              "text": text, "start": line_start + offset,
                              "sentence": segment, "line": line})
    return found


def _binds_limit_to_token(segment):
    """이 도막에서 **제한 대상과 기초 토큰이 실제로 묶이는가.**

    한 도막에 둘이 있다는 것으로는 부족하다. `본점소재지가 경기도 […광역…]에 있는 업체
    납품장소는 […기초…]` 처럼 역할이 바뀌는 말이 사이에 끼면 그 토큰은 제한 대상이 아니다.
    그래서 둘 사이를 실제로 읽고, 역할을 바꾸는 말이 끼면 묶지 않는다.

    괄호 안은 정의를 덧붙이는 자리라 사이 거리에서 빼고 본다 — `본점소재지(개인사업자인
    경우에는 … 사업장의 소재지)가 [수요기관(기초자치단체)]내에` 의 괄호가 90자쯤 된다.
    """
    tokens = [(m.start(), m.end()) for m in _submission().ANON_REGION.finditer(segment)
              if "단위=기초" in m.group(0)]
    tokens += [(m.start(), m.end()) for m in BASIC_AGENCY_TARGET.finditer(segment)]
    if not tokens:
        return False
    subjects = [(m.start(), m.end()) for m in PARTICIPANT_SUBJECT.finditer(segment)]
    fused = [(m.start(), m.end()) for m in FUSED_LIMIT.finditer(segment)]
    roles = [(m.start(), m.end()) for m in ROLE_SWITCH.finditer(segment)]
    for token in tokens:
        if _bound_to_subject(segment, token, subjects, roles):
            return True
        if _bound_to_fused_limit(segment, token, fused, roles):
            return True
    return False


def _strip_parentheses(text):
    """괄호 안은 정의를 덧붙이는 자리라 거리에서 뺀다 — `본점소재지(개인사업자인 경우에는
    … 사업장의 소재지)가` 의 괄호가 90자쯤 된다."""
    return re.sub(r"\([^)]*\)|（[^）]*）|【[^】]*】", " ", text)


def _bound_to_subject(segment, token, subjects, roles):
    """꼴 ① — 참가 업체의 소재지 주어가 토큰 **앞**에 있고, 토큰 뒤에 소재 서술이 온다."""
    subject = max((x for x in subjects if x[1] <= token[0]), default=None)
    if subject is None:
        return False
    # 주어와 토큰 사이에 역할이 바뀌면 그 토큰은 이 주어의 것이 아니다.
    between = _strip_parentheses(segment[subject[1]:token[0]])
    if ROLE_SWITCH.search(between) or len(between.strip()) > LIMIT_TOKEN_REACH:
        return False
    # 서술을 찾는 창에 **토큰 자신을 포함한다.** 발주기관 토큰은 `[수요기관(기초자치단체)]내에
    # 소재` 까지를 한 덩어리로 물기 때문에, 토큰 뒤만 보면 서술이 이미 소비돼 남지 않는다.
    after = _strip_parentheses(segment[token[0]:token[1] + PREDICATE_REACH])
    return bool(LOCATED_PREDICATE.search(after))


def _bound_to_fused_limit(segment, token, fused, roles):
    """꼴 ② — `지역제한(<지역>)` · `<지역> 지역 업체`. 주어와 서술이 붙어 있다."""
    for limit in fused:
        lo, hi = (limit[1], token[0]) if limit[0] <= token[0] else (token[1], limit[0])
        if lo > hi:
            continue
        between = _strip_parentheses(segment[lo:hi])
        if ROLE_SWITCH.search(between) or len(between.strip()) > LIMIT_TOKEN_REACH:
            continue
        # 토큰 앞에 다른 역할이 더 가까이 있으면 그 역할의 것이다.
        role = max((r for r in roles if r[1] <= token[0]), default=None)
        if role and role[0] > limit[0]:
            continue
        return True
    return False


# 제한 대상과 토큰이 떨어져 있어도 되는 거리. 괄호를 뺀 뒤의 글자 수다.
# dev 양성 다섯 중 가장 먼 것이 `PPS-DEV-072` 의 `를 계속 경기도 `(11자)다.
LIMIT_TOKEN_REACH = 60


def price_below_region_limit(rec):
    """추정가격이 그 공고의 지역제한 상한 미만인가. 둘 중 하나라도 모르면 False.

    상한은 운영 `script.region_price_limit()` 을 쓴다. 같은 파일의
    `region_restriction_allowed()` 는 쓰지 않는다 — 그 True 는 "허용 구간이다"가 아니라
    "못 막는다"여서, 올리는 쪽에 쓰면 금액 미상 공고까지 올린다(작업서 선행 작업 절).
    """
    script = _submission()
    limit = script.region_price_limit(rec)
    price = script.estimated_price(rec)
    return limit is not None and price is not None and price < limit


def is_small_negotiated(rec):
    """지방 소액수의 견적인가."""
    meta = rec.get("meta") or {}
    return meta.get("적용계약법") == "지방계약법" and meta.get("낙찰방법") == "소액수의견적"


def _docs_dropped(rec):
    """첨부가 잘려 들어왔는가. 잘렸으면 내리지 않는다 — 못 본 문서에 근거가 있을 수 있다."""
    return any((rec.get("dropped_doc_counts") or {}).values())


# --- L2 예외 평가기 ---
# 「지방자치단체 입찰 및 계약 집행기준」 제5장 제3절 1 이 정한 예외다. 금액기준 이하의
# 2인 이상 견적을 지정정보처리장치로 받을 때 "공사현장·납품소재지를 관할하는 시·군" 또는
# "그 시·군과 인접 시·군" 으로 제한할 수 있다. 같은 장 제6절 2 는 지정정보처리장치를
# 쓰지 않는 견적의 지역 제한을 금지한다.
#
# 평가기는 (a)(b)(c) 를 각각 판정하고 **근거 문장을 전부** 돌려준다. 판정 기대값을 사람이
# 원문과 대조할 수 있어야 해서다(작업서 "L2 사례의 기대값" 절 1~4).

# (a) 이 계약의 견적서·입찰서를 지정정보처리장치로 제출한다고 말하는 문장.
#     낱말이 어딘가 있는 것으로는 부족하다 — 시스템과 제출이 한 문장 안에서 **이어져야** 한다.
#     그래서 `제출` 하나하나를 보고 한 도막 안에서 셋을 맞춘다.
#       · 그 앞에서 지정정보처리장치가 제출의 수단으로 표시됐다(`_system_is_the_means()`)
#       · 그 앞의 제출물이 견적서·입찰서다
#       · 바로 뒤가 `제출 확인`·`제출 여부`처럼 제출 사실의 조회가 아니다
#     `견적서 제출 여부는 나라장터 …에서 확인하여야 합니다` 는 시스템이 `제출` 뒤에 있어 떨어지고,
#     `공동수급협정서는 … 제출하여야 합니다` 는 제출물이 견적서·입찰서가 아니라 떨어진다.
QUOTE_SYSTEM = re.compile(r"지정정보처리장치|국가종합전자조달|나라장터|G2B|전자조달시스템")
# 제출 대상이 될 수 있는 서류. **무엇을 내는 문장인지**를 이 목록으로 가른다.
QUOTE_DOCUMENT = re.compile(
    r"전자견적서|견적서|입찰서|공동수급협정서|협정서|서약서|제안서|산출내역서"
    r"|증명서|확인서|등록증|신청서|제출서류|첨부서류")
# 그중 이 계약의 견적·입찰 그 자체인 것.
QUOTE_TARGET = re.compile(r"전자견적서|견적서|입찰서")
QUOTE_SUBMIT_WORD = re.compile(r"제출")
QUOTE_LOOKUP_ONLY = re.compile(r"^\s*(?:여부|확인|사실|결과|내역|현황)")


# 전자 제출이 아닌 제출 방식. 이것이 대상과 `제출` 사이에 있으면 전자 제출이 아니다.
QUOTE_OFFLINE = re.compile(r"우편|등기|방문|직접\s*제출|지참|팩스|FAX|이메일|전자우편|인편|우송")


# 시스템이 **제출의 수단**으로 표시된 꼴. 이것이 (a) 의 긍정 근거다.
# `나라장터에서 공고문 열람 후 …` 의 `에서` 는 행위가 일어난 자리일 뿐이고, 실제로 그
# 자리에서 한 일은 열람이다. 그래서 수단·방향 표지를 요구한다.
QUOTE_MEANS_MARK = re.compile(r"(?:을|를)\s*(?:이용|통하|통해|경유)|(?:으)?로\s*(?:제출|송신)"
                              r"|에\s*제출|을\s*통한")
# 표지가 붙은 것 — `이용`·`통하` 의 목적어 머리 낱말 — 이 **제출 경로 자체**여야 한다.
# 시스템 이름 바로 뒤(`국가종합전자조달시스템(G2B)을`)거나, 시스템 안에서 제출을 맡는 기능
# (`안전 입찰서비스를`·`전자입찰시스템을`·`입찰서 제출기능을`)일 때만이다. `나라장터의 서식을
# 이용하여` 는 머리가 서식이라 시스템 안의 자료를 쓴 것이고, 그 이용과 시스템을 통한 제출은
# 뒤따르는 동사로도 갈리지 않는다(`…서식을 이용하여 현장으로 제출`, PR #114 6라운드 P1).
# 머리가 제출 경로가 아니면 (a) 를 세우지 않는다 — 내리는 쪽의 보류다. 메뉴 이름
# `시스템의 "입찰정보"를 이용하여 제출`(`PPS-D-015016`)도 제출 경로라 말하지 않아 보류된다.
QUOTE_MEANS_GAP = 40
QUOTE_CHANNEL_HEAD = re.compile(
    r"(?:^|(?:시스템|입찰\s*서비스|제출\s*기능))[\s\"'“”‘’]*(?:\([^()]{0,40}\))?[\s\"'“”‘’]*$")
# 표지가 시스템에 붙었어도 그 `이용` 이 시키는 첫 행위가 제출이어야 한다.
# 첫 행위가 작성·등록·열람이면 시스템은 그 일에 쓰인 것이고 제출 수단이 아니다.
QUOTE_ACTION = re.compile(r"제출|송신|작성|열람|조회|확인|게시|공고|출력|등록|접수|발급|교부|내려받|다운로드")
QUOTE_SUBMIT_ACTION = re.compile(r"제출|송신")


def _system_is_the_means(text):
    """이 앞말에서 **지정정보처리장치가 제출의 수단으로 쓰였다**고 말하는가."""
    for system in QUOTE_SYSTEM.finditer(text):
        mark = QUOTE_MEANS_MARK.search(text, system.end(), system.end() + QUOTE_MEANS_GAP)
        if mark is None or not QUOTE_CHANNEL_HEAD.search(text[system.end():mark.start()]):
            continue             # 표지가 없거나 제출 경로가 아닌 것에 붙었다
        if QUOTE_SUBMIT_ACTION.search(mark.group(0)):
            return True          # `…로 제출`·`…에 제출` — 표지 자체가 제출이다
        after = text[mark.end():]
        action = QUOTE_ACTION.search(after)
        if action is None or not QUOTE_SUBMIT_ACTION.match(action.group(0)):
            continue             # 첫 행위가 제출이 아니면 시스템은 그 일에 쓰인 것이다
        return True
    return False


def _says_electronic_quote(line):
    """이 줄이 **견적서·입찰서를** 지정정보처리장치로 제출한다고 말하는가.

    셋이 한 줄에 있는 것으로는 부족하고, `제출` 의 대상만 봐도 부족하다.
    `견적서는 나라장터에서 열람하고 입찰서는 우편으로 제출한다` 는 대상이 입찰서인데도
    전자 제출이 아니다 — `나라장터` 는 열람에, `우편` 은 제출에 붙었다(PR #114 재리뷰 P1).

    그래서 **도막 단위로** 본다. 접속 어미에서 끊으면 위 문장은
    `견적서는 나라장터에서 열람하고` / `입찰서는 우편으로 제출한다` 로 갈리고, 제출이 있는
    도막에 시스템이 없다. 한 도막 안에서 셋이 다 서야 인정한다 —
    시스템 · 견적서·입찰서인 제출 대상 · 그 사이에 다른 제출 방식이 없을 것.

    대상이 생략된 도막(`국가종합전자조달시스템을 이용하여 제출하여야 하며`)은 그 도막의
    서류가 전부 견적서·입찰서일 때만 인정한다.
    """
    for _, segment in _segments(line):
        for submit in QUOTE_SUBMIT_WORD.finditer(segment):
            if not _system_is_the_means(segment[:submit.end()]):
                continue
            if QUOTE_LOOKUP_ONLY.match(segment[submit.end():submit.end() + 8]):
                continue
            # 제출 방식은 문서명 **앞에도** 온다 — `우편으로 입찰서를 제출한다`.
            # 그래서 대상과 `제출` 사이가 아니라 그 도막에서 `제출` 앞 전체를 본다.
            if QUOTE_OFFLINE.search(segment[:submit.start()]):
                continue
            preceding = list(QUOTE_DOCUMENT.finditer(segment[:submit.start()]))
            if preceding:
                if not QUOTE_TARGET.fullmatch(preceding[-1].group(0)):
                    continue
                return True
            # 대상이 생략된 도막은 줄 전체를 본다. 그 줄의 서류가 전부 견적서·입찰서이고
            # 줄 어디에도 다른 제출 방식이 없을 때만 인정한다 — 모르면 인정하지 않는다.
            documents = QUOTE_DOCUMENT.findall(line)
            if not documents or not all(QUOTE_TARGET.fullmatch(n) for n in documents):
                continue
            if QUOTE_OFFLINE.search(line):
                continue
            return True
    return False

# (b) 금액기준. 용역·물품은 추정가격 1억원 이하다.
#     공사는 종류별로 갈리는데 meta 로 종합공사와 전문공사를 가를 수 없다 — 확인 못 한 것으로 둔다.
SMALL_QUOTE_LIMIT = {"용역물품": 100_000_000}

# (c) 관할. 제한 문장의 지역 토큰이 같은 문서의 납품·현장·과업 장소 문장에도 있는가.
PLACE_LABEL = re.compile(
    r"납품\s*장소|납품장소|납품\s*소재지|사업\s*장소|사업장소|사업\s*위치"
    r"|과업\s*(?:위치|장소|구역|수행\s*장소)|이행\s*장소|공사\s*위치|현장\s*위치|위\s*치")
# 개찰·설명회·접수 장소는 납품·과업 장소가 아니다. `PPS-D-009156` 에서 같은 `r2` 가
# 개찰 장소와 과업 위치에 둘 다 있고, 근거는 과업 위치여야 한다.
# 홈페이지 메뉴 경로의 `위치` 도 장소가 아니다(`PPS-D-017898` 의 부패신고 안내).
PLACE_NOT = re.compile(r"개찰|설명회|접수\s*장소|입찰집행|제출\s*장소|등록\s*장소|교부\s*장소"
                       r"|홈페이지|메뉴|접속\s*경로")
# 장소 이름표는 조항의 머리에 온다. 줄 한가운데의 `… - 위치 : 홈페이지 / …` 는 이름표가 아니다.
PLACE_LABEL_HEAD = 30
# 표에서 이름표와 값이 다른 줄에 온다(`위 치` / 빈 줄 / 토큰 줄). 그래서 위로 훑되
# **바로 윗 줄 하나**까지다. 셋까지 훑었더니 `라. 납품장소 : 농업기술센터 지정장소` 아래
# 세 줄 뒤의 부패행위 신고 안내문이 관할 근거로 나왔다(`PPS-D-017898`).
PLACE_LABEL_LOOKBACK = 1

# 같은 문서의 같은 `rN` 은 같은 지역이다(data.md D3). 그 id 는 지역 토큰뿐 아니라
# **기관 토큰에도 붙는다** — `[수요기관(기초자치단체)|지역=r1] [지역:r2|단위=읍면동] 일원`.
# 앞 꼴만 읽으면 제한과 장소가 같은 `r1` 인데도 관할을 못 본다. 표본 20건 중 4건이 그랬다
# (`PPS-D-013602`·`014480`·`015016`·`017875`). 지명은 복원하지 않는다(R10).
REGION_TOKEN = re.compile(r"\[(?:등록)?지역:(r\d+)\||\|지역=(r\d+)\]")


def _region_ids(text):
    return {a or b for a, b in REGION_TOKEN.findall(text or "")}
# 제한 문장이 관할을 직접 말하는 꼴. 이때는 장소 문장을 따로 찾지 않아도 (c) 가 선다.
SELF_JURISDICTION = re.compile(r"납품\s*소재지|공사\s*현장[^\n]{0,20}관할|현장[^\n]{0,10}관할"
                               r"|관할하는\s*시\s*[·․]?\s*군|인접\s*시\s*[·․]?\s*군")


def _place_sentences(text):
    """그 문서에서 납품·현장·과업 장소를 말하는 줄. 개찰·설명회 장소는 뺀다."""
    lines = list(_doc_lines(text))
    out = []
    for index, (start, line) in enumerate(lines):
        if not line.strip() or PLACE_NOT.search(line):
            continue
        # 제한 문장 자신은 장소 문장이 아니다. `입찰 및 계약방식 지역제한([지역:r1…])` 이
        # 바로 위의 `장소` 이름표에 걸려 제 자신을 관할 근거로 내놓았다(`PPS-D-013602`).
        if REGION_LIMIT_ANCHOR.search(line):
            continue
        if PLACE_LABEL.search(line[:PLACE_LABEL_HEAD]):
            out.append((start, line))
            continue
        # 표에서는 이름표와 값이 다른 줄에 온다. 위로 몇 줄만 훑는다.
        seen = 0
        for prev_start, prev in reversed(lines[:index]):
            if not prev.strip():
                continue
            seen += 1
            if seen > PLACE_LABEL_LOOKBACK:
                break
            if PLACE_NOT.search(prev):
                break
            if PLACE_LABEL.search(prev[:PLACE_LABEL_HEAD]):
                out.append((start, line))
                break
    return out


def evaluate_small_quote_exception(rec, sentences=None):
    """L2 의 (a)(b)(c) 를 각각 판정하고 근거 문장을 전부 돌려준다.

    이 함수는 내리지 않는다. 판정은 `apply_v6` 이 두 판본의 조건으로 한다.
    """
    sentences = basic_region_sentences(rec) if sentences is None else sentences
    script = _submission()
    result = {"a": False, "a_evidence": [], "b": False, "b_note": "",
              "c": False, "c_evidence": [], "limit_sentences": [
                  {"doc_id": hit["doc_id"], "sentence": hit["sentence"].strip()}
                  for hit in sentences]}

    for doc in rec.get("docs", []):
        text = doc.get("text") or ""
        for _, line in _doc_lines(text):
            if not line.strip() or not _says_electronic_quote(line):
                continue
            result["a_evidence"].append({"doc_id": doc.get("doc_id"), "sentence": line.strip()})
    result["a"] = bool(result["a_evidence"])

    meta = rec.get("meta") or {}
    scope = script._price_scope(meta.get("업무구분"))
    price = script.estimated_price(rec)
    limit = SMALL_QUOTE_LIMIT.get(scope)
    if limit is None:
        result["b_note"] = f"금액표 갈래를 모른다(업무구분={meta.get('업무구분')!r})"
    elif price is None:
        result["b_note"] = "추정가격이 없다"
    else:
        result["b"] = price <= limit
        result["b_note"] = f"추정가격 {price:,}원 대 상한 {limit:,}원"

    by_doc = {}
    for hit in sentences:
        by_doc.setdefault(hit["doc_id"], []).append(hit)
    for doc in rec.get("docs", []):
        hits = by_doc.get(doc.get("doc_id"))
        if not hits:
            continue
        text = doc.get("text") or ""
        places = _place_sentences(text)
        for hit in hits:
            if SELF_JURISDICTION.search(hit["sentence"]):
                result["c_evidence"].append({"doc_id": hit["doc_id"], "역할": "제한 문장이 관할을 직접 말한다",
                                             "sentence": hit["sentence"].strip()})
                continue
            tokens = _region_ids(hit["sentence"])
            for _, place in places:
                if tokens & _region_ids(place):
                    result["c_evidence"].append({"doc_id": hit["doc_id"], "역할": "같은 문서의 장소 문장",
                                                 "sentence": place.strip()})
    # 제한 문장이 둘이면 같은 장소 문장이 두 번 들어온다. 사람이 읽는 표라 한 번만 남긴다.
    seen, unique = set(), []
    for item in result["c_evidence"]:
        key = (item["doc_id"], item["역할"], item["sentence"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    result["c_evidence"] = unique
    result["c"] = bool(result["c_evidence"])
    return result


def _v6_quote(hit):
    """올림 근거문구. **기초 토큰을 반드시 담은** 연속 원문 구간이다.

    앞에서 480자로 자르면 안 된다. 긴 참가자격 조항의 앞부분만 잘려 나가 `단위=기초` 가
    빠진 인용이 되고, 그러면 근거가 항목을 입증하지 못한 채 양성만 남는다(PR #114 리뷰 P1).
    그래서 절 안에서 **토큰 자리를 중심으로** 상한만큼 떼어 낸다.
    """
    script = _submission()
    clause = hit["sentence"]
    if len(clause.strip()) <= QUOTE_MAX:
        return script.clean_evidence(clause.strip(), hit["text"])
    anchors = [m.start() for m in script.ANON_REGION.finditer(clause)]
    anchors += [m.start() for m in BASIC_AGENCY_TARGET.finditer(clause)]
    if not anchors:
        return ""
    center = min(anchors)
    lo = max(0, center - QUOTE_MAX // 3)
    quote = clause[lo:lo + QUOTE_MAX].strip()
    return script.clean_evidence(quote, hit["text"])


def v6_evidence_contract(quote, rec):
    """이 근거로 v6 양성을 써도 되는가. (통과여부, 사유) 를 돌려준다.

    운영 `script.postprocess()` 가 v6 에 거는 계약을 후보가 **스스로 다시 건다.** 이 후보는
    v6 을 그 후처리 뒤에 얹으므로, 다시 걸지 않으면 검사받지 않은 양성이 남는다.

    한 자리에서 운영 게이트와 갈린다. `v6_not_a_basic_region_limit()` 은
    `[수요기관(기초자치단체)]내에 소재` 를 기초 신호로 읽지 못해 조건 ②로 내린다(`PPS-DEV-071`).
    그 한 경우만 사유를 남기고 통과시킨다 — 운영에 옮길 때 그 함수가 이 토큰을 배워야 한다는
    뜻이고, 보고서 §"B에게 넘기는 것" ①이 그것이다. 다른 이유로 게이트가 내리면 올리지 않는다.
    """
    if not (quote or "").strip():
        return False, "근거가 비었다"
    if not has_confirmed_basic_signal(quote):
        return False, "인용 안에 기초 토큰이 없다"
    script = _submission()
    if not script.v6_not_a_basic_region_limit(quote, rec):
        return True, ""
    if BASIC_AGENCY_TARGET.search(quote):
        return True, "운영 게이트가 발주기관 토큰을 못 읽는다 — 운영 반영 시 수리 필요"
    return False, "운영 v6 근거 게이트가 내린다"


def v6_decision(model_v6, rec, rules):
    """켜진 규칙이 v6 을 바꾸는가. 바꾸면 (값, 근거문구, 규칙이름), 아니면 None.

    한 셀을 여럿이 내릴 수 있으면 L1 을 먼저 보고 그다음 L2 다(작업서 "모든 규칙에 공통").
    """
    sentences = basic_region_sentences(rec)
    if "U" in rules and model_v6 != 1:
        confirmed = confirmed_basic_region_sentences(rec)
        if confirmed and price_below_region_limit(rec) and not is_small_negotiated(rec):
            for hit in confirmed:
                quote = _v6_quote(hit)
                passed, _why = v6_evidence_contract(quote, rec)
                if passed:
                    return 1, quote, "U"
    if model_v6 == 1 and not _docs_dropped(rec):
        if "L1" in rules and not sentences:
            return 0, None, "L1"
        if sentences and is_small_negotiated(rec) and ({"L2C", "L2E"} & rules):
            checked = evaluate_small_quote_exception(rec, sentences)
            if "L2C" in rules and checked["a"] and checked["b"] and checked["c"]:
                return 0, None, "L2C"
            if "L2E" in rules and checked["a"] and checked["b"]:
                return 0, None, "L2E"
    return None


def apply_v6(out, judgment, rec, rules=None):
    """제출 후처리 결과에 v6 규칙을 얹는다. 켜진 규칙이 없으면 그대로 돌려준다."""
    rules = enabled_v6_rules() if rules is None else set(rules)
    if not rules:
        return out
    model_v6 = (judgment.get("v6") or {}).get("위반여부")
    decided = v6_decision(model_v6, rec, rules)
    if decided is None:
        return out
    value, quote, _rule = decided
    out = dict(out)
    out["v6"] = {"위반여부": value, "근거문구": quote if value == 1 else ""}
    return out


def postprocess(judgment, rec):
    """`tools/replay_run.py --candidate`의 진입점. 제출 후처리 앞에 세 규칙만 끼운다.

    근거문구의 원문 대조·부재탐지 빈칸 고정은 제출 코드가 그대로 맡는다.
    v6 만 제출 후처리 **뒤**에 얹는다 — `script.postprocess()` 안의 #96 게이트가
    `[수요기관(기초자치단체)]` 를 기초 신호로 읽지 못해, 앞에 끼우면 U 가 올린 `071` 을
    그 게이트가 도로 내린다(실측). 조건 판단에는 게이트를 타기 전의 모델 판정을 쓴다.
    """
    staged = judgment if v6_only() else apply(judgment, rec)
    out = _submission().postprocess(staged, rec)
    return apply_v6(out, judgment, rec)
