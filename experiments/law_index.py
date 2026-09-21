"""제공 법령을 **구조 그대로** 잘라 항목표의 인용으로 주소지정한다. 모델을 부르지 않는다.

`항목표.json` 은 항목마다 근거 조문을 이미 지정해 준다. 검색할 것이 없다 — 필요한 것은
**그 표기를 원문 조각으로 바꾸는 조회**다. 규칙 A6 이 "항목→조문 직접 조회" 를 BM25·bge-m3 와
**나란히, 별개로** 허용 목록에 올려 둔 이유가 이것이다.

## 왜 단순 분할이면 안 되나

제공 23개 파일에 체계가 **세 가지** 섞여 있다. 베이스라인 RAG 노트북의 `^제\\s?\\d+조\\(` 한 줄은
그중 하나만 안다.

| 체계 | 쓰는 파일 | `^제N조(` 로 자르면 |
| --- | --- | --- |
| 조-항-호-목 | 법률·시행령·시행규칙 18개 | 정상 |
| 장-절-번호-가나다 | 예규·집행기준·결정기준 | 「지방자치단체 입찰시 낙찰자 결정기준」(420,768자)은 **제N조가 0개**라 통째로 한 조각이 된다 |
| 별표 | 지침·예규 | 부칙 뒤 꼬리라 **주소지정 자체가 안 된다** |

그리고 dev 에서 가장 약한 두 항목이 정확히 뒤의 둘을 가리킨다.

- **v20 (F1 0.200)** — 판정 규칙 전체가 「중소 소프트웨어사업자의 사업 참여 지원에 관한 지침」의
  `[별표 1] 대기업인 소프트웨어사업자가 참여할 수 있는 사업금액의 하한` **685자 표 하나**다.
- **v23 (F1 0.286)** — 근거가 「지방자치단체 입찰시 낙찰자 결정기준」 `제7장 제3절`(5,126자)이다.

## 이 모듈이 지키는 것

**항목표의 인용 31개가 전부 비어 있지 않은 원문으로 풀린다 — 31/31.** 그것이 통과 조건이고
`tests/test_law_index.py` 의 14개 검사가 전수로 고정한다. 새 조문을 발명하지 않는다 —
제공 스냅샷의 원문 부분문자열만 돌려준다(검사가 부분문자열임을 확인한다).

## 항목별 조문 크기 — 주입이 가능한가

`baseline` 프롬프트 토큰 중앙값 **9,356**, 예산 14,272 → **중앙값 여유 4,916 토큰**
(회차 `colab-1789902969401579900` 의 실측 `prompt_tokens`).

**그러나 중앙값으로 판단하면 안 된다.** 200건의 실제 분포로 세면 조각 크기마다 예산을
넘기는 공고 수가 다르고, 넘기면 `fit_to_budget` 이 **공고**를 줄인다.

| 항목 | dev F1 | 조각 | 글자 | ≈토큰 | 예산 초과 공고 |
| --- | ---: | ---: | ---: | ---: | ---: |
| **v20** | **0.200** | 2 | **934** | **623** | **0 / 200** |
| v24 | 0.204 | 0 | 0 | 0 | — (조문 없는 대조형) |
| v10 | 0.400 | 2 | 3,312 | 2,208 | 6 / 200 |
| v13 | 0.400 | 3 | 5,507 | 3,671 | 48 / 200 |
| v23 | 0.286 | 2 | 6,445 | 4,297 | **94 / 200** |
| v9 | 0.435 | 2 | 6,495 | 4,330 | **94 / 200** |
| v11 | 0.364 | 4 | 7,378 | 4,919 | 안 들어감 |
| v6 | 0.462 | 3 | 7,595 | 5,063 | 안 들어감 |
| v18 | 0.200 | 4 | 7,752 | 5,168 | 안 들어감 |
| v21 · v4 | 0.667 · 0.800 | 2 | 44,509 · 72,582 | 29,673 · 48,388 | 안 들어감 |

**v20 만이 200건 전부에서 예산을 안 넘긴다.** 623토큰이고 그 표가 없으면 사업금액 하한을
알 방법이 없다 — 비용 대비 가장 유리하다.

서로 다른 조각 32개 · union 163,072자라 전부는 못 넣는다.

초판은 주소를 평탄하게 소비해 부모·자식을 둘 다 돌려줬고 v9 를 13,516자로 부풀렸다.
계층 소비로 고친 뒤 6,495자다. 수치와 근거는
[보고서](../reports/team-c/law-index/README.md)가 소유한다.

## 알려진 한계

- 항목표가 **장까지만** 지목한 인용은 조각이 크다 — 지방 집행기준 제1장 70,290자,
  제6장 25,268자, 공동계약운용요령 19,241자. 절·번호까지 내려가려면 인용에 그 주소가 있어야 한다.
  `chapter(law, 장, 절, 번호)` 로 직접 부르면 내려간다.
- 호(`1.`)·목(`가.`) 층은 예규 경로에서만 쓴다. 법률 조문 안의 각 호는 조 전문에 포함해 돌려준다.
- 같은 장 제목이 속표지와 본문에 반복되면 **가장 긴 블록**을 고른다. 휴리스틱이다.

## 조각내기 규칙

1. **별표를 먼저 떼어낸다.** `[별표 N]` 블록은 본문 계층 밖이다.
2. **목차·부칙의 가짜 헤더를 거른다.** 예규는 같은 `제5장 …` 을 목차(점선+쪽번호)·본문·부칙 인용에서
   반복한다. 줄머리 헤더이면서 점선이 없는 것만 헤더로 본다.
3. 본문은 `제N장 > 제N절 > 제N조 > 항(①) > 호(1.) > 목(가.)` 순으로 잡되 **있는 층만** 쓴다.
   예규는 조가 없고 `번호. > 가.` 로 내려간다.

## 안 하는 것

- **검색을 안 붙인다.** 인용이 주소를 주므로 BM25·임베딩이 할 일이 없다.
  한국 법령에서 BM25 는 Recall@10 23% 이고(arXiv:2604.06173), 이 저장소에서
  공고명↔고시 617행 BM25 는 분리도가 0이었다.
- **프롬프트에 무엇을 넣을지 정하지 않는다.** 이 모듈은 조회만 한다. 주입 설계는 별도 후보다.
- 조문을 요약·정규화하지 않는다. 원문 부분문자열 그대로여야 인용 검증과 어긋나지 않는다.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple

REPO = Path(__file__).resolve().parents[1]
LAW_DIR = Path("open/data/법령패키지/법령")

# 항목표의 약칭·붙여쓰기 → 제공 파일명. 실제로 쓰이는 표기만 둔다.
ALIASES = {
    "국가계약법": "국가를 당사자로 하는 계약에 관한 법률",
    "국가를당사자로하는계약에관한법률등의재정경제부장관이정하는고시금액":
        "국가를 당사자로 하는 계약에 관한 법률 등의 재정경제부장관이 정하는 고시금액",
    "지방계약법": "지방자치단체를 당사자로 하는 계약에 관한 법률",
    "소프트웨어진흥법": "소프트웨어 진흥법",
    "정부입찰계약집행기준": "(계약예규) 정부 입찰·계약 집행기준",
    "정부입찰·계약집행기준": "(계약예규) 정부 입찰·계약 집행기준",
    "공동계약운용요령": "(계약예규) 공동계약운용요령",
}
# 약칭 뒤에 붙는 꼬리. `지방계약법시행규칙` 처럼 붙여 쓰거나 `법시행규칙` 처럼 겹쳐 쓴다.
SUFFIXES = ("시행규칙", "법시행규칙", "시행령", "법시행령")
# 인용 앞에 붙는 발령기관 표시. 법령명이 아니다.
ISSUER = re.compile(r"\((?:계약예규|행안부예규)\)\s*")

ANNEX = re.compile(r"\[별표\s*(\d+)\]")
# 별표 구역의 시작. 번호 없는 단독 줄이라 본문 안 `[별표1]` 참조와 갈린다.
ANNEX_SECTION = re.compile(r"^[ 	]*\[별표\][ 	]*$", re.M)
# 번호가 아니라 **라벨 전체**를 잡는다. 숫자만 비교하면 `제3장의2` 가 `제3장` 으로 풀린다 —
# 다른 장의 원문을 조용히 돌려주는 자리였다.
CHAPTER = re.compile(r"^(제\s?\d+장(?:의\s?\d+)?)\s*(\S[^\n]*)?$", re.M)
SECTION = re.compile(r"^(제\s?\d+절(?:의\s?\d+)?)\s*(\S[^\n]*)?$", re.M)
ARTICLE = re.compile(r"^제\s?(\d+)조(?:의\s?(\d+))?\s*[(（]", re.M)
PARAGRAPH = re.compile(r"^\s*([①-⑳])", re.M)
NUMBERED = re.compile(r"^\s*(\d+)\.\s*\S", re.M)
LETTERED = re.compile(r"^\s*([가-힣])\.\s*\S", re.M)
# 목차 줄. 점선 채움과 쪽번호로 끝난다.
TOC_LEADER = re.compile(r"[·．.]{3,}|…{2,}")


class Segment(NamedTuple):
    law: str
    path: Tuple[str, ...]
    text: str

    @property
    def address(self) -> str:
        return f"{self.law} " + " ".join(self.path)


@lru_cache(maxsize=1)
def laws(data_dir: str = "open/data") -> Dict[str, str]:
    """파일명 → NFC 정규화한 원문."""
    base = Path(data_dir).parent / LAW_DIR if not Path(data_dir).is_absolute() else Path(data_dir)
    root = Path(data_dir) / "법령패키지" / "법령"
    if not root.is_dir():
        root = REPO / LAW_DIR
    out = {}
    for path in sorted(root.glob("*.txt")):
        name = unicodedata.normalize("NFC", path.stem)
        out[name] = unicodedata.normalize("NFC", path.read_text(encoding="utf-8"))
    return out


def _flat(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def resolve_law(name: str, data_dir: str = "open/data") -> Optional[str]:
    """항목표의 법령 표기를 제공 파일명으로 바꾼다. 못 찾으면 None."""
    available = laws(data_dir)
    raw = ISSUER.sub("", name or "").strip()
    flat = _flat(raw)
    if not flat:
        return None
    for key in available:                       # 정식 명칭이 그대로 온 경우
        if _flat(key) == flat:
            return key
    for short, full in ALIASES.items():         # 약칭 + 시행령/시행규칙 꼬리
        if not flat.startswith(_flat(short)):
            continue
        tail = flat[len(_flat(short)):]
        for suffix in SUFFIXES:
            if tail == _flat(suffix):
                candidate = f"{full} {suffix.removeprefix('법')}"
                if candidate in available:
                    return candidate
        if not tail and full in available:
            return full
    for key in available:                       # 붙여쓴 정식 명칭의 접두 일치
        if flat.startswith(_flat(key)) or _flat(key).startswith(flat):
            return key
    return None


def _strip_annexes(text: str) -> Tuple[str, Dict[str, str]]:
    """별표 구역을 본문에서 떼어낸다. 계층 밖이라 따로 주소지정한다.

    **앵커는 단독 `[별표]` 줄이다.** `[별표1]` 은 본문 안 참조로도 쓰여서 그것을 경계로
    삼으면 본문이 잘린다 — 「지방자치단체 입찰시 낙찰자 결정기준」은 그 표기가 본문에
    120회 나오고, 첫 등장에서 자르면 420,768자가 11,267자가 된다.
    단독 마커가 없는 파일은 별표 구역이 없다.
    """
    anchor = ANNEX_SECTION.search(text)
    if anchor is None:
        return text, {}
    tail = text[anchor.end():]
    out: Dict[str, str] = {}
    marks = list(ANNEX.finditer(tail))
    for index, mark in enumerate(marks):
        end = marks[index + 1].start() if index + 1 < len(marks) else len(tail)
        block = tail[mark.start():end].strip()
        number = mark.group(1)
        # 같은 별표가 머리글과 본문으로 두 번 나온다. 긴 쪽이 본문이다.
        if len(block) > len(out.get(number, "")):
            out[number] = block
    return text[:anchor.start()], out


def _headers(text: str, pattern: re.Pattern) -> List[Tuple[int, str, str]]:
    """(시작, 라벨, 제목). 목차 줄(점선+쪽번호)은 뺀다."""
    found = []
    for match in pattern.finditer(text):
        if TOC_LEADER.search(match.group(0)):
            continue                            # 목차
        found.append((match.start(), _flat(match.group(1)), (match.group(2) or "").strip()))
    return found


def _block(text: str, headers, label: str) -> Optional[Tuple[int, int]]:
    """그 번호의 헤더가 여는 블록 (시작, 끝). 같은 헤더가 여러 번이면 **가장 긴 블록**을 쓴다.

    예규는 같은 `제5장 …` 을 속표지와 본문에서 반복하고, 부칙은 문장 안에서 인용한다.
    줄머리 헤더만 남겨도 속표지가 남으므로 길이로 고른다.
    """
    best = None
    wanted = _flat(label)
    for index, (start, value, _) in enumerate(headers):
        if value != wanted:
            continue
        end = headers[index + 1][0] if index + 1 < len(headers) else len(text)
        if best is None or end - start > best[1] - best[0]:
            best = (start, end)
    return best


def annex(law: str, number, data_dir: str = "open/data") -> Optional[Segment]:
    name = resolve_law(law, data_dir)
    if name is None:
        return None
    _, blocks = _strip_annexes(laws(data_dir)[name])
    block = blocks.get(str(number))
    return Segment(name, (f"별표 {number}",), block) if block else None


def _article_in(body: str, number: str) -> Optional[str]:
    head = re.escape(number.replace(" ", ""))
    found = re.search(r"^" + head + r"\s*[(（].*?(?=^제\s?\d+조|\Z)", body, re.M | re.S)
    return found.group(0).rstrip() if found else None


def article(law: str, number: str, paragraph: Optional[str] = None,
            data_dir: str = "open/data", within: Optional["Segment"] = None) -> Optional[Segment]:
    """`제21조` · `제2조의2` 를 조 전문으로. `paragraph` 를 주면 그 항만.

    `within` 을 주면 그 조각 안에서만 찾는다 — 예규의 `제2장 … 제5조` 처럼 장이 조를 품는다.
    """
    name = resolve_law(law, data_dir)
    if name is None:
        return None
    if within is not None:
        body, prefix = within.text, within.path
    else:
        body, _ = _strip_annexes(laws(data_dir)[name])
        prefix = ()
    text = _article_in(body, number)
    if text is None:
        return None
    path: Tuple[str, ...] = prefix + (number,)
    if paragraph:
        marks = list(PARAGRAPH.finditer(text))
        for index, mark in enumerate(marks):
            if mark.group(1) != paragraph:
                continue
            end = marks[index + 1].start() if index + 1 < len(marks) else len(text)
            return Segment(name, path + (paragraph,), text[mark.start():end].strip())
        return None
    return Segment(name, path, text)


def chapter(law: str, label: str, section: Optional[str] = None,
            items: Tuple[str, ...] = (), data_dir: str = "open/data") -> Optional[Segment]:
    """예규의 `제N장 > 제N절 > N. > 가.` 경로를 **요청한 깊이까지** 내려간다.

    `label` 은 `"제5장"` · `"제3장의2"` 처럼 라벨 문자열이다. 숫자만 받으면
    `제3장의2` 가 `제3장` 으로 풀린다 — 다른 장의 원문을 조용히 돌려주는 자리였다.
    """
    name = resolve_law(law, data_dir)
    if name is None:
        return None
    body, _ = _strip_annexes(laws(data_dir)[name])
    span = _block(body, _headers(body, CHAPTER), label)
    if span is None:
        return None
    text = body[span[0]:span[1]]
    path: Tuple[str, ...] = (label,)
    if section is not None:
        inner = _block(text, _headers(text, SECTION), section)
        if inner is None:
            return None
        text = text[inner[0]:inner[1]]
        path += (section,)
    for item in items:                          # `1.` 다음 `가.` 처럼 여러 층을 내려간다
        key = item.rstrip(".")
        pattern = NUMBERED if key.isdigit() else LETTERED
        marks = [m for m in pattern.finditer(text) if m.group(1) == key]
        if not marks:
            return None
        mark = marks[0]
        rest = pattern.search(text, mark.end())
        text = text[mark.start():rest.start() if rest else len(text)]
        path += (f"{key}.",)
    return Segment(name, path, text.strip())


# ----- 항목표 인용 문자열 파싱 -----
# 인용은 구분자 없이 이어 붙는다 — `국가계약법 시행령 제21조 중소기업제품 … 법률 제7조 제1항`.
# 그래서 법령 이름을 **긴 것부터** 찾아 자르고, 그 뒤에 붙은 주소 토큰을 그 법령에 준다.
ADDRESS = re.compile(
    r"제\s?\d+조(?:의\s?\d+)?"           # 제21조 · 제2조의2
    r"|제\s?\d+장(?:의\s?\d+)?"
    r"|제\s?\d+절(?:의\s?\d+)?"
    r"|제\s?\d+항|\d+항"
    r"|별표\s*\d+"
    r"|(?<![\d가-힣])\d+\.(?=\s)"         # 예규의 `7.`
    r"|(?<![가-힣])[가-힣]\.(?=\s)"       # 예규의 `나.`
)
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
# `제2조의2` 는 **'조'로 끝나지 않는다.** 끝글자로 갈랐다가 판로지원법 시행령 제2조의2·제2조의3이
# 통째로 빠졌다. 종류는 머리로 가른다.
IS_ARTICLE = re.compile(r"^제\d+조")
IS_CHAPTER = re.compile(r"^제\d+장")
IS_SECTION = re.compile(r"^제\d+절")


def _law_spans(citation: str, data_dir: str) -> List[Tuple[int, int, str]]:
    """인용 문자열 안에서 법령 이름이 차지한 구간. 긴 이름부터 잡아 겹침을 막는다."""
    names = list(laws(data_dir)) + list(ALIASES)
    spans: List[Tuple[int, int, str]] = []
    for name in sorted(names, key=len, reverse=True):
        pattern = r"\s*".join(map(re.escape, _flat(name)))
        for found in re.finditer(pattern, citation):
            if any(found.start() < end and start < found.end() for start, end, _ in spans):
                continue
            end = found.end()
            # `국가계약법 시행령` 은 약칭 다섯 자만 잡히고 ` 시행령` 이 주소 쪽에 남는다.
            # 그대로 두면 **시행령 제21조가 법률 제21조로 풀린다** — 조용히 틀린 원문이다.
            tail = re.match(r"\s*(법\s*)?시행(령|규칙)", citation[end:])
            if tail and resolve_law(citation[found.start():end + tail.end()], data_dir):
                end += tail.end()
            spans.append((found.start(), end, name if end == found.end()
                          else citation[found.start():end]))
    return sorted(spans)


def resolve(citation: str, data_dir: str = "open/data", *, strict: bool = True) -> List[Segment]:
    """항목표의 인용 문자열 하나 → 원문 조각들.

    `strict` 면 **주소를 못 푼 토큰이 하나라도 있을 때 예외**다. 조용히 빼면
    `제5장 제3절 1. 나.` 의 `나.` 가 사라진 것을 아무도 모른다.
    """
    spans = _law_spans(citation or "", data_dir)
    out: List[Segment] = []
    unconsumed: List[str] = []
    if not spans and ADDRESS.search(citation or ""):
        # 주소 토큰은 있는데 법령 이름을 하나도 못 찾았다. 빈 결과로 성공하면
        # 오타나 스냅샷 불일치가 **근거 없는 판정**으로 그대로 흘러간다.
        unconsumed.append(f"법령 미상: {citation.strip()[:60]}")
    for index, (_, end, raw) in enumerate(spans):
        stop = spans[index + 1][0] if index + 1 < len(spans) else len(citation)
        tokens = [t.replace(" ", "") for t in ADDRESS.findall(citation[end:stop])]
        law = resolve_law(raw, data_dir)
        if law is None:
            continue
        if not tokens:
            # 주소가 안 붙은 법령이 **뒤에 다른 법령을 달고 있으면** 그것은 상위 법령 표시다 —
            # `소프트웨어진흥법 … 지침 제2조 별표1` 에서 진흥법 37,234자가 통째로 딸려 왔다.
            # 마지막 이름이면 그 법령 전체를 가리킨 것이다(`… 제21조 … 고시금액`).
            if index == len(spans) - 1:
                out.append(Segment(law, (), laws(data_dir)[law]))
            continue
        found, unused = _segments_for(law, tokens, data_dir)
        out.extend(found)
        unconsumed.extend(f"{law} {token}" for token in unused)
    if unconsumed and strict:
        raise ValueError("주소를 못 푼 토큰: " + " · ".join(unconsumed))
    return [s for s in out if s and s.text]


def _segments_for(law: str, tokens: List[str], data_dir: str) -> Tuple[List[Segment], List[str]]:
    """한 법령에 붙은 주소 토큰을 **계층 경로**로 소비한다. (조각들, 소비 못 한 토큰).

    인용의 주소는 평탄한 목록이 아니라 경로다. `제2장 제한경쟁입찰의 운용 제5조` 는
    **제2장 안의 제5조** 한 곳을 가리키지, 제2장 전체와 제5조 둘을 가리키지 않는다.
    평탄하게 소비하면 부모(7,021자)와 자식(2,292자)을 둘 다 돌려줘 같은 원문이 두 번 들어가고,
    `제5장 제3절 1. 나.` 의 `나.` 처럼 **더 깊은 주소가 조용히 버려진다.**

    소비 못 한 토큰은 돌려준다 — 호출자가 조용히 넘기지 않게 하려는 것이다.
    """
    out: List[Segment] = []
    unused: List[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if token.startswith("별표"):
            found = annex(law, re.sub(r"\D", "", token), data_dir)
        elif IS_CHAPTER.match(token):
            section = None
            if index < len(tokens) and IS_SECTION.match(tokens[index]):
                section = tokens[index]; index += 1
            if index < len(tokens) and IS_ARTICLE.match(tokens[index]):
                # 예규는 장이 조를 품는다. 장 전체가 아니라 그 안의 조가 인용의 대상이다.
                inner = chapter(law, token, section, (), data_dir)
                article_token = tokens[index]; index += 1
                paragraph, asked, index = _paragraph(tokens, index)
                found = (inner and article(law, article_token, paragraph, data_dir, within=inner))
                if found is None and asked is not None:
                    unused.append(asked)
            else:
                run: List[str] = []
                while index < len(tokens) and tokens[index].endswith("."):
                    run.append(tokens[index]); index += 1
                # 같은 종류가 이어지면 **형제**다. 종류가 바뀔 때만 한 층 내려간다 —
                # `1. 2.` 는 제3절의 형제 둘이고 `1. 나.` 는 `1.` 안의 `나.` 하나다.
                for path in _item_paths(run):
                    piece = chapter(law, token, section, path, data_dir)
                    if piece:
                        out.append(piece)
                    else:
                        unused.append(token)
                continue
        elif IS_ARTICLE.match(token):
            paragraph, asked, index = _paragraph(tokens, index)
            found = article(law, token, paragraph, data_dir)
            if found is None and asked is not None:
                # **항을 지목했는데 못 찾았으면 조 전체로 넓히지 않는다.**
                # 넓히면 요청하지 않은 조 전문이 근거가 되고, 토큰이 소비돼 strict 도 침묵한다.
                unused.append(asked)
            elif found is None:
                found = article(law, token, None, data_dir)
        elif token.endswith("."):
            # 장·절 문맥 없는 `22.` 은 주소가 아니라 날짜다 —
            # `제43조 7항 삭제 (’22. 9. 20. …)`. 주소로 세면 영원히 못 푼다.
            continue
        else:
            found = None
        if found:
            out.append(found)
        else:
            unused.append(token)
    return out, unused


def _paragraph(tokens: List[str], index: int) -> Tuple[Optional[str], Optional[str], int]:
    """`제1항` · `6항` 을 동그라미 숫자로. (표시, 요청한 토큰, 다음 위치).

    **요청한 토큰을 함께 돌려준다.** 항을 못 찾았을 때 조 전체로 넓히는 대신
    그 토큰을 미소비로 남기려면 호출자가 "항을 물었다" 는 사실을 알아야 한다.
    `⑳` 을 넘는 번호처럼 표시가 없는 경우도 요청은 있었던 것이다.
    """
    if index >= len(tokens) or not tokens[index].endswith("항"):
        return None, None, index
    asked = tokens[index]
    number = int(re.sub(r"\D", "", asked))
    mark = CIRCLED[number - 1] if 1 <= number <= len(CIRCLED) else None
    return mark, asked, index + 1


def _item_kind(token: str) -> str:
    return "number" if token.rstrip(".").isdigit() else "letter"


def _item_paths(run: List[str]) -> List[Tuple[str, ...]]:
    """`1. 2.` → 형제 둘, `1. 나.` → 한 층 내려간 경로 하나.

    같은 종류가 이어지면 같은 부모의 형제다. 하나의 중첩 경로로 읽으면
    `1.` 안에서 `2.` 를 찾다가 유효한 인용이 실패한다.
    """
    if not run:
        return [()]
    paths: List[Tuple[str, ...]] = []
    current: List[str] = []
    for token in run:
        if current and _item_kind(current[-1]) == _item_kind(token):
            paths.append(tuple(current))
            current = current[:-1] + [token]
        else:
            current = current + [token]
    paths.append(tuple(current))
    return paths
