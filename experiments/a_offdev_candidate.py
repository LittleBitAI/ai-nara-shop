"""Two post-processing fixes found by scoring the current code outside dev (docs/tasks/labels-600.md, off-dev audit).

v11 — 판로지원법 제7조①: a 경쟁제품 is bought from 중소기업자, and v11 is a 경쟁제품 bid NOT limited to them. The
product rule raises v11 when `SME_ALLOWED` misses the limit sentence, and that regex wants "중소기업" within 60
characters on one line: "소기업 또는 소상공인으로서 … 확인서를 소지한 업체" (small firms are 중소기업자 too) and limits
wrapped over lines slip past. On the diagnostic 200 the product and company-size stages set 31 v11 false positives.
The fix lowers v11 when a participation sentence limits bidders by company size.

v2 — the raising rule dropped on 9/25 (13938fe) after dev review rounds traded precision for recall. Outside dev
the model misses 19 of 22 labeled v2 positives; the dropped rule (202d197) recovers 5 with no new false positive.
Brought back as it was.

    python -X utf8 tools/replay_run.py --case <run>/output --candidate experiments/a_offdev_candidate.py ...
    OFFDEV_FIXES=v11 or v2 limits the candidate to one fix.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
FIXES = set((os.environ.get("OFFDEV_FIXES") or "v11,v2").split(","))

# A company-size limit on who may bid: the size class, then within one clause a qualifying close.
SIZE = r"(?:중\s*[·ㆍ・‧]?\s*소\s*기업자?|소\s*기업자?|소\s*상\s*공\s*인)"
# The close must make the size class a condition on the bidder — a bare 확인서 mention, a document list line or
# "확인 가능하여야" about a website is not one.
SIZE_LIMIT = re.compile(SIZE + r"[^。]{0,120}?(?:으로\s*[서써]|로\s*[서써]|에\s*한(?:정|하여|함|해|합니다)|한정"
                        r"|으로\s*제한|로\s*제한|에\s*해당하는\s*(?:업체|자)|확인서를?\s*(?:소지|보유|발급받은)[^。\n]{0,10}?(?:업체|자))"
                        r"|제한\s*경쟁\s*(?:입찰)?\s*\(\s*" + SIZE, re.S)
# Titles and site names that carry the words without limiting anyone.
TITLES = re.compile(r"[「｢『《][^」｣』》]{0,60}[」｣』》]|중소기업\s*기본법|중소기업\s*범위\s*및\s*확인에\s*관한\s*규정"
                    r"|중소기업제품[^,.\n]{0,30}?(?:법률|시행령)|중소벤처기업부|중소기업자\s*간\s*경쟁\s*제품"
                    r"|중소기업\s*공공\s*구매\s*(?:종합)?\s*정보망")


def baseline():
    """The submission code the replayer loaded; standalone, the repository's script.py."""
    submitted = sys.modules.get("submission")
    if submitted is not None:
        return submitted
    import importlib.util
    spec = importlib.util.spec_from_file_location("baseline_script", ROOT / "script.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def size_limited(base, rec: Dict[str, Any]) -> bool:
    for doc in rec.get("docs") or ():
        text = TITLES.sub(" ", doc.get("text") or "")
        for m in SIZE_LIMIT.finditer(text):
            if base._is_qualification_context(text, m.start()):
                return True
    return False


# ----- v2, verbatim from 202d197 -----
V2_ELIGIBILITY = re.compile(r"(?<!신용과 )실적(?:이|을)\s*(?:있는|보유한|갖춘)\s*(?:업체|자)"
                            r"(?=[ \t]*(?:$|이어야|여야|만(?![가-힣])|로서|[(.,]))", re.M)


def v2_performance_clause(base, rec: Dict[str, Any]) -> Optional[str]:
    meta = rec.get("meta") or {}
    price = base.estimated_price(rec)
    if price is None or price >= base.NOTICE_AMOUNT_WON:
        return None
    if ("지방" in str(meta.get("적용계약법") or "") and meta.get("계약방법") == "수의계약"
            and price < 100_000_000):
        return None
    for doc in rec.get("docs") or ():
        if doc.get("type") != "공고문":
            continue
        text = doc.get("text") or ""
        for m in V2_ELIGIBILITY.finditer(text):
            if base._is_qualification_context(text, m.start()):
                start = text.rfind("\n", 0, m.start()) + 1
                return text[start:m.end()].strip()[-base.QUOTE_MAX:]
    return None


def postprocess(judgment: Dict[str, Dict[str, Any]], rec: Dict[str, Any]):
    base = baseline()
    out = base.postprocess(judgment, rec)
    if "v11" in FIXES and (out.get("v11") or {}).get("위반여부") == 1 and size_limited(base, rec):
        out["v11"] = {"위반여부": 0, "근거문구": None}
    if "v2" in FIXES and (out.get("v2") or {}).get("위반여부") == 0:
        quote = v2_performance_clause(base, rec)
        for doc in rec["docs"] if quote else ():
            cleaned = base.clean_evidence(quote, doc["text"])
            if cleaned:
                out["v2"] = {"위반여부": 1, "근거문구": cleaned}
                break
    return out
