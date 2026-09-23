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
from pathlib import Path
import re
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
    """제출 코드를 한 번만 읽는다. 후보는 script.py를 고치지 않고 뒤에 붙는다."""
    global _script
    if _script is None:
        spec = importlib.util.spec_from_file_location("submission", ROOT / "script.py")
        _script = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_script)
    return _script


def postprocess(judgment, rec):
    """`tools/replay_run.py --candidate`의 진입점. 제출 후처리 앞에 세 규칙만 끼운다.

    근거문구의 원문 대조·부재탐지 빈칸 고정은 제출 코드가 그대로 맡는다.
    """
    return _submission().postprocess(apply(judgment, rec), rec)
