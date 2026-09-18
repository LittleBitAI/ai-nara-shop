"""v8 중복제한(실적+지역) 후보. 모델 뒤에 붙는 후처리 단계다.

왜 후처리인가. 등록된 회차 4개에서 v8은 모두 TP=0 FP=0 FN=6이다.
FP가 0이라는 것은 모델이 dev 200건 어디에서도 v8에 1을 낸 적이 없다는 뜻이다.
정밀도 문제가 아니라 항목이 아예 발화하지 않으므로, 모델 출력을 깎는 대신
공고 원문에서 두 요건을 직접 찾아 올린다.

무엇을 보는가. 같은 문서 안에서 실적 요건과 지역 요건이 한 참가자격 묶음에
함께 나오는지만 본다. 메타 `지역제한여부` 하나로 거르지 않는다.
dev 양성 6건 중 3건(`PPS-DEV-11`·`048`·`071`)이 `지역제한여부=N`이다.

인터페이스는 공고 1건과 그 공고의 모델 출력뿐이다. 정답·다른 공고 통계는 받지 않는다.
"""

import importlib.util
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
ITEM = "v8"
_script = None

# 참가자격을 실적으로 거는 문구. 제출서류 목록의 `실적증명서 1부`나
# 제안서 평가 배점표의 `실적` 항목은 참가 제한이 아니므로 잡지 않는다.
PERFORMANCE = re.compile(
    r"실적(?:을|이)?\s*(?:보유|있는|갖춘|충족|우수한)"
    r"|(?:이상|초과)(?:인|의)?\s*실적"
    r"|실적(?:증명서?)?\s*(?:보유|소지)"
    r"|수행(?:한|실적)\s*실적"
    r"|준공(?:금)?액(?:이)?\s*[^\n]{0,40}이상"
)

# 참가자격을 지역으로 거는 문구. `주된 영업소`·`본점 소재지`는 조문 표현이고
# `~에 소재한`은 `경북에 소재한 실적이 우수한 업체`처럼 사이에 말이 끼는 공고를 위해 둔다.
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
    """같은 문서에서 창 안에 함께 있는 (실적, 지역) 위치 쌍을 가까운 순으로 돌려준다."""
    perf = [(m.start(), m.end()) for m in PERFORMANCE.finditer(text)]
    region = [(m.start(), m.end()) for m in REGION.finditer(text)]
    found = [(abs(p[0] - r[0]), p, r)
             for p in perf for r in region if abs(p[0] - r[0]) <= WINDOW]
    return sorted(found, key=lambda item: item[0])


def _quote(text, perf, region):
    """두 요건을 덮는 원문 조각. 상한을 넘으면 실적 요건 쪽을 남긴다.

    지역 제한만 있는 공고는 v5·v6·v7이 따로 다룬다. v8을 가르는 것은 실적 쪽이므로
    둘을 한 인용에 못 담으면 실적 문구를 남긴다.
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
    """공고 1건에서 중복제한 근거를 찾는다. 없으면 None."""
    for doc in rec.get("docs", []):
        text = doc.get("text") or ""
        for _, perf, region in _pairs(text):
            quote = _quote(text, perf, region)
            if quote and unicodedata.normalize("NFC", quote) in unicodedata.normalize("NFC", text):
                return {"doc_id": doc.get("doc_id"), "doc_type": doc.get("type"),
                        "performance": text[perf[0]:perf[1]],
                        "region": text[region[0]:region[1]],
                        "distance": abs(perf[0] - region[0]),
                        "근거문구": quote}
    return None


def apply(judgment, rec):
    """모델 판정에 v8만 덧쓴다. 다른 23항목은 그대로 돌려준다.

    이미 1이면 모델 근거를 유지한다. 규칙은 0을 1로 올리기만 하고 내리지 않는다.
    """
    out = dict(judgment)
    cell = dict(out.get(ITEM) or {"위반여부": 0, "근거문구": None})
    if cell.get("위반여부") == 1:
        return out
    hit = detect(rec)
    if hit:
        out[ITEM] = {"위반여부": 1, "근거문구": hit["근거문구"]}
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
    """`tools/replay_run.py --candidate`의 진입점. 제출 후처리 앞에 v8 규칙만 끼운다.

    근거문구의 원문 대조·부재탐지 빈칸 고정은 제출 코드가 그대로 맡는다.
    """
    return _submission().postprocess(apply(judgment, rec), rec)
