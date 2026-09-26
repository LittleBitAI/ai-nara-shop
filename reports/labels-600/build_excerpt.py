"""Build the labeler's cached context from the provided snapshot: clause fragments, item guide, rulings.

The clause part is copied verbatim from `open/data/법령패키지/법령/`, cut to the paragraph (항) or
subparagraph (호) each item needs. Every fragment carries an ID (L01 ...) that `item-guide.txt` cites,
so a clause shared by several items appears once. Which fragment serves which item, and why the
`항목표.json` citations were widened or narrowed, is in `citation-audit.md`. Run from the repository root:

  python -X utf8 reports/labels-600/build_excerpt.py
"""

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAWS = ROOT / "open/data/법령패키지/법령"
HERE = Path(__file__).parent
OUT = HERE / "law-excerpt.txt"

NAT_DECREE = "국가를 당사자로 하는 계약에 관한 법률 시행령.txt"
NAT_RULE = "국가를 당사자로 하는 계약에 관한 법률 시행규칙.txt"
LOC_DECREE = "지방자치단체를 당사자로 하는 계약에 관한 법률 시행령.txt"
LOC_RULE = "지방자치단체를 당사자로 하는 계약에 관한 법률 시행규칙.txt"
NOTICE = "국가를 당사자로 하는 계약에 관한 법률 등의 재정경제부장관이 정하는 고시금액.txt"
SME_ACT = "중소기업제품 구매촉진 및 판로지원에 관한 법률.txt"
SME_DECREE = "중소기업제품 구매촉진 및 판로지원에 관한 법률 시행령.txt"
DESIGNATED = "중소기업자간 경쟁제품 및 공사용자재 직접구매 대상 품목 지정 내역.txt"
SMB_ACT = "중소기업기본법.txt"
NAT_STD = "(계약예규) 정부 입찰·계약 집행기준.txt"
LOC_STD = "지방자치단체 입찰 및 계약 집행기준.txt"
JOINT = "(계약예규) 공동계약운용요령.txt"
AWARD = "지방자치단체 입찰시 낙찰자 결정기준.txt"
SW_ACT = "소프트웨어 진흥법.txt"
SW = "중소 소프트웨어사업자의 사업 참여 지원에 관한 지침.txt"

ARTICLE_HEAD = r"^제\d+조(?:의\d+)?\("
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"


def read(name):
    return (LAWS / name).read_text(encoding="utf-8-sig")


def article(name, number):
    body = re.split(r"^부칙", read(name), maxsplit=1, flags=re.M)[0]
    match = re.search("^" + re.escape(number) + r"\(.*?(?=" + ARTICLE_HEAD + r"|\Z)", body, re.M | re.S)
    if not match:
        raise ValueError(f"article not found: {name} {number}")
    return match.group(0).strip()


def paragraphs(name, number, marks):
    """The article heading line plus the listed paragraphs (항), in order."""
    lines = article(name, number).split("\n")
    starts = [i for i, line in enumerate(lines) if line.strip()[:1] in CIRCLED]
    out = [lines[0]]
    for mark in marks:
        hit = [i for i in starts if lines[i].strip().startswith(mark)]
        if not hit:
            raise ValueError(f"paragraph not found: {name} {number} {mark}")
        end = next((j for j in starts if j > hit[0]), len(lines))
        out += lines[hit[0]:end]
    return "\n".join(out).strip()


def subparagraphs(name, number, mark, numbers):
    """The paragraph's lead sentence plus the listed subparagraphs (호) with their items (목)."""
    lines = paragraphs(name, number, [mark]).split("\n")
    head, body = lines[:2], lines[2:]                 # article heading + paragraph lead
    ho = re.compile(r"^\s{4}(\d+(?:의\d+)?)\.\s")
    starts = [i for i, line in enumerate(body) if ho.match(line)]
    out = list(head)
    for number_ in numbers:
        hit = [i for i in starts if ho.match(body[i]).group(1) == number_]
        if not hit:
            raise ValueError(f"subparagraph not found: {name} {number} {mark} {number_}")
        end = next((j for j in starts if j > hit[0]), len(body))
        out += body[hit[0]:end]
    return "\n".join(out).strip()


def section(name, start, end):
    lines = read(name).split("\n")
    try:
        first = next(i for i, line in enumerate(lines) if line.strip().startswith(start))
        last = next(i for i in range(first + 1, len(lines)) if lines[i].strip().startswith(end))
    except StopIteration:
        raise ValueError(f"section not found: {name} {start!r} .. {end!r}") from None
    return "\n".join(lines[first:last]).strip()


def whole(name):
    body = re.split(r"^\[?부칙", read(name), maxsplit=1, flags=re.M)[0]
    # Lines that only say an image had no text carry nothing for the labeler.
    return "\n".join(line for line in body.split("\n") if not line.startswith("[원문 그림")).strip()


def tail(text):
    """Drop the article heading line; used when a second paragraph joins a fragment that has one."""
    return text.split("\n", 1)[1]


# (ID, source label, fragment). Grouped by subject; item-guide.txt says which item uses which.
FRAGMENTS = [
    ("L01", "국가계약법 시행령 제12조①", lambda: paragraphs(NAT_DECREE, "제12조", ["①"])),
    ("L02", "국가계약법 시행규칙 제17조", lambda: article(NAT_RULE, "제17조")),
    ("L03", "지방계약법 시행령 제13조①", lambda: paragraphs(LOC_DECREE, "제13조", ["①"])),
    ("L04", "지방계약법 시행규칙 제17조", lambda: article(LOC_RULE, "제17조")),
    ("L05", "국가계약법 시행령 제21조①(3·5·6·8·8의2·10호)·②",
     lambda: subparagraphs(NAT_DECREE, "제21조", "①", ["3", "5", "6", "8", "8의2", "10"])
     + "\n" + tail(paragraphs(NAT_DECREE, "제21조", ["②"]))),
    ("L06", "지방계약법 시행령 제20조①(3·5·6·8·11·12호)·②",
     lambda: subparagraphs(LOC_DECREE, "제20조", "①", ["3", "5", "6", "8", "11", "12"])
     + "\n" + tail(paragraphs(LOC_DECREE, "제20조", ["②"]))),
    ("L07", "재정경제부장관 고시금액", lambda: whole(NOTICE)),
    ("L08", "국가계약법 시행규칙 제24조", lambda: article(NAT_RULE, "제24조")),
    ("L09", "지방계약법 시행규칙 제24조", lambda: article(LOC_RULE, "제24조")),
    ("L10", "국가계약법 시행규칙 제25조②③⑤", lambda: paragraphs(NAT_RULE, "제25조", ["②", "③", "⑤"])),
    ("L11", "지방계약법 시행규칙 제25조②③⑦", lambda: paragraphs(LOC_RULE, "제25조", ["②", "③", "⑦"])),
    ("L12", "(계약예규) 정부 입찰·계약 집행기준 제5조", lambda: article(NAT_STD, "제5조")),
    ("L13", "지방자치단체 입찰 및 계약 집행기준 제1장 제1절 7. 계약담당자 주의사항",
     lambda: section(LOC_STD, "7. 계약담당자 주의사항", "8. 계약정보의 공개")),
    ("L14", "지방자치단체 입찰 및 계약 집행기준 제5장 제3절 1. 2인 이상 견적 수의계약",
     lambda: section(LOC_STD, "1. 금액기준에 따른 2인 이상 견적서 제출 수의계약",
                     "2. 금액기준에 따른 1인 견적서 제출 가능 수의계약")),
    ("L15", "판로지원법 제7조·제7조의2",
     lambda: article(SME_ACT, "제7조") + "\n" + article(SME_ACT, "제7조의2")),
    ("L16", "판로지원법 제9조①④", lambda: paragraphs(SME_ACT, "제9조", ["①", "④"])),
    ("L17", "판로지원법 시행령 제7조①②", lambda: paragraphs(SME_DECREE, "제7조", ["①", "②"])),
    ("L29", "판로지원법 시행령 제10조①②", lambda: paragraphs(SME_DECREE, "제10조", ["①", "②"])),
    ("L18", "중소기업자간 경쟁제품 품목 지정 내역", lambda: whole(DESIGNATED)),
    ("L19", "판로지원법 시행령 제2조의2①·제2조의3",
     lambda: paragraphs(SME_DECREE, "제2조의2", ["①"]) + "\n" + article(SME_DECREE, "제2조의3")),
    ("L20", "중소기업기본법 제2조", lambda: article(SMB_ACT, "제2조")),
    ("L21", "(계약예규) 정부 입찰·계약 집행기준 제5조의3", lambda: article(NAT_STD, "제5조의3")),
    ("L22", "(계약예규) 공동계약운용요령 제9조⑤", lambda: paragraphs(JOINT, "제9조", ["⑤"])),
    ("L23", "지방자치단체 입찰 및 계약 집행기준 제6장 제2절 1. 나. 구성원 수 등",
     lambda: section(LOC_STD, "나. 구성원 수 등", "다. 공동수급체 구성의 제한")),
    ("L24", "소프트웨어 진흥법 제48조", lambda: article(SW_ACT, "제48조")),
    ("L25", "중소 소프트웨어사업자의 사업 참여 지원에 관한 지침 제2조·제3조·별표 1",
     lambda: article(SW, "제2조") + "\n" + article(SW, "제3조") + "\n"
     + section(SW, "[별표 1] 대기업인 소프트웨어사업자가 참여할 수 있는 사업금액의 하한", "[별표 2]")),
    ("L26", "국가계약법 시행령 제43조⑤⑥ · 지방계약법 시행령 제43조",
     lambda: paragraphs(NAT_DECREE, "제43조", ["⑤", "⑥"]) + "\n" + article(LOC_DECREE, "제43조")),
    ("L27", "지방계약법 시행령 제35조①", lambda: paragraphs(LOC_DECREE, "제35조", ["①"])),
    ("L28", "지방자치단체 입찰시 낙찰자 결정기준 제7장 제3절 1.~2.",
     lambda: section(AWARD, "제3절 입찰과 계약상대자 결정절차", "3. ")),
]


def build():
    parts = ["Statute excerpt — the provided snapshot, verbatim. The item guide below cites these IDs."]
    parts += [f"[{fid}] {label}\n{make()}" for fid, label, make in FRAGMENTS]
    parts.append((HERE / "item-guide.txt").read_text(encoding="utf-8").strip())
    # The rulings restate docs/qna.md without any dev notice ID, so dev calibration sees no answers.
    parts.append((HERE / "rulings.txt").read_text(encoding="utf-8").strip())
    return "\n\n".join(parts) + "\n"


def main():
    for fid, label, make in FRAGMENTS:
        print(f"  {fid} {len(make()):>6} {label}")
    text = build()
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"{OUT.relative_to(ROOT).as_posix()} chars={len(text)} "
          f"sha256={hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
