"""구조 인지 법령 조회 검사. 모델을 부르지 않는다. 성능 검사가 아니다.

여기서 지키는 것은 **주소지정**이다. 항목표의 인용 31개가 전부 비어 있지 않은 원문으로 풀리고,
돌려준 조각이 제공 파일의 부분문자열인지 본다. 조문을 발명하면 여기서 걸린다.

만들면서 실제로 걸린 오류 넷을 회귀로 고정한다.

1. `국가계약법 시행령 제21조` 가 **시행령이 아니라 법률** 제21조로 풀렸다.
   약칭 다섯 자만 법령 이름으로 잡히고 ` 시행령` 이 주소 쪽에 남았다.
   못 푸는 것보다 나쁘다 — 조용히 틀린 원문을 돌려준다.
2. `[별표1]` 은 본문 안 참조로도 쓰인다. 첫 등장에서 별표 구역을 자르면
   「지방자치단체 입찰시 낙찰자 결정기준」이 420,768자 → 11,267자가 된다.
3. `제2조의2` 는 **'조'로 끝나지 않는다.** 끝글자로 종류를 가르면 통째로 빠진다.
4. 주소가 안 붙은 법령을 파일 전체로 펴면 `소프트웨어진흥법 … 지침 제2조 별표1` 에서
   진흥법 37,234자가 딸려 온다.
"""

import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


law_index = _load("law_index", ROOT / "experiments" / "law_index.py")
DATA = str(ROOT / "open/data")


def citations():
    table = json.loads((ROOT / "open/data/항목표.json").read_text(encoding="utf-8"))["항목"]
    found = set()
    for row in table.values():
        for column in ("국가계약법", "지방계약법"):
            value = (row.get(column) or "").strip()
            if value and "해당 없음" not in value:
                found.add(value)
    return sorted(found)


class LawIndex(unittest.TestCase):
    def test_every_item_table_citation_resolves(self):
        unresolved = [c for c in citations() if not law_index.resolve(c, DATA)]
        self.assertEqual(unresolved, [], "항목표 인용은 전부 원문으로 풀려야 한다")

    def test_segments_are_verbatim_substrings_of_the_supplied_files(self):
        laws = law_index.laws(DATA)
        for citation in citations():
            for segment in law_index.resolve(citation, DATA):
                self.assertIn(segment.law, laws, citation)
                self.assertIn(segment.text, laws[segment.law],
                              f"{segment.address} 가 원문 부분문자열이 아니다")

    def test_enforcement_decree_is_not_confused_with_the_act(self):
        """`국가계약법 시행령 제21조` 는 법률 제21조가 아니다 — 조용히 틀리던 자리."""
        decree = law_index.article("국가계약법 시행령", "제21조", data_dir=DATA)
        act = law_index.article("국가계약법", "제21조", data_dir=DATA)
        self.assertIsNotNone(decree)
        self.assertTrue(decree.law.endswith("시행령"), decree.law)
        self.assertNotEqual(decree.text, act and act.text)
        self.assertEqual(law_index.resolve("국가계약법 시행령 제21조", DATA)[0].law, decree.law)

    def test_in_text_annex_references_do_not_truncate_the_body(self):
        """`[별표1]` 본문 참조 120회짜리 파일이 통째로 살아 있어야 한다."""
        name = "지방자치단체 입찰시 낙찰자 결정기준"
        body, annexes = law_index._strip_annexes(law_index.laws(DATA)[name])
        self.assertEqual(annexes, {}, "단독 [별표] 마커가 없으면 별표 구역이 없다")
        self.assertEqual(len(body), len(law_index.laws(DATA)[name]))

    def test_chapter_and_section_of_a_file_with_no_articles(self):
        """제N조가 0개인 420,768자 파일에서 제7장 제3절을 집어낸다 — v23 의 근거."""
        segment = law_index.chapter("지방자치단체 입찰시 낙찰자 결정기준", "제7장", "제3절",
                                    data_dir=DATA)
        self.assertIsNotNone(segment)
        self.assertIn("제안요청서 설명일의 전일부터 기산하여 7일전에 공고", segment.text)
        self.assertIn("추정가격 10억원 이상인 경우 40일", segment.text)
        self.assertLess(len(segment.text), 20000, "절 하나가 장 전체로 부풀면 안 된다")

    def test_annex_table_behind_the_addendum(self):
        """v20 의 판정 규칙 전체가 들어 있는 685자 표. 부칙 뒤라 조 단위로는 못 닿는다."""
        segment = law_index.annex("중소 소프트웨어사업자의 사업 참여 지원에 관한 지침", 1, data_dir=DATA)
        self.assertIsNotNone(segment)
        self.assertIn("사업금액의 하한", segment.text)
        self.assertLess(len(segment.text), 2000)

    def test_article_with_a_sub_number_is_not_dropped(self):
        """`제2조의2` 는 '조'로 끝나지 않는다 — 끝글자로 가르면 빠지던 자리."""
        found = law_index.resolve(
            "중소기업제품 구매촉진 및 판로지원에 관한 법률 시행령 제2조의2 제1항,제2조의3", DATA)
        self.assertEqual([s.path for s in found], [("제2조의2", "①"), ("제2조의3",)])

    def test_a_parent_law_without_an_address_is_not_expanded(self):
        """`소프트웨어진흥법 … 지침 제2조 별표1` 에서 진흥법 전체가 딸려 오면 안 된다."""
        found = law_index.resolve(
            "소프트웨어진흥법 중소 소프트웨어사업자의 사업 참여 지원에 관한 지침 제2조 별표1", DATA)
        self.assertEqual([s.law for s in found],
                         ["중소 소프트웨어사업자의 사업 참여 지원에 관한 지침"] * 2)

    def test_address_tokens_are_consumed_as_a_path_not_a_flat_list(self):
        """`제2장 … 제5조` 는 **제2장 안의 제5조** 한 곳이다.

        평탄하게 소비하면 부모(7,021자)와 자식(2,292자)을 둘 다 돌려줘 같은 원문이 두 번
        들어간다. v3·v4·v9 에서 실제로 그랬고 보고서의 v9 크기를 부풀렸다.
        """
        found = law_index.resolve(
            "(계약예규) 정부 입찰·계약 집행기준 제2장 제한경쟁입찰의 운용 제5조", DATA)
        self.assertEqual([s.path for s in found], [("제2장", "제5조")])
        for citation in citations():
            segments = law_index.resolve(citation, DATA)
            nested = [(a.path, b.path) for a in segments for b in segments
                      if a is not b and a.text in b.text]
            self.assertEqual(nested, [], f"{citation}: 부모·자식을 둘 다 돌려준다")

    def test_the_deepest_requested_level_is_not_dropped(self):
        """`제5장 제3절 1. 나.` 의 `나.` 가 조용히 버려지던 자리."""
        found = law_index.resolve(
            "지방자치단체 입찰 및 계약집행기준 제5장 수의계약 운영요령 제3절 수의계약 대상과 "
            "운영요령 1. 금액기준에 따른 2인 이상 견적서 제출 수의계약 나. 수의계약 요령", DATA)
        self.assertEqual([s.path for s in found], [("제5장", "제3절", "1.", "나.")])

    def test_a_sub_numbered_chapter_is_not_collapsed_into_its_parent(self):
        """`제3장의2` 가 `제3장` 으로 풀리면 **다른 장의 원문**을 조용히 돌려준다."""
        found = law_index.resolve("중소기업제품 구매촉진 및 판로지원에 관한 법률 제3장의2", DATA)
        self.assertEqual([s.path for s in found], [("제3장의2",)])
        self.assertIn("공공조달 상생협력", found[0].text.splitlines()[0])

    def test_an_unresolved_address_token_raises_instead_of_disappearing(self):
        """주소를 못 풀면 예외다. 조용히 빼면 무엇이 사라졌는지 아무도 모른다."""
        with self.assertRaises(ValueError):
            law_index.resolve("국가계약법 시행령 제9999조", DATA)
        self.assertEqual(law_index.resolve("국가계약법 시행령 제9999조", DATA, strict=False), [])

    def test_a_date_is_not_an_address(self):
        """`(’22. 9. 20. …)` 의 `22.` 은 번호가 아니다 — 장 문맥 없는 `N.` 은 주소가 아니다."""
        found = law_index.resolve("지방계약법 시행령 제43조 7항 삭제 (’22. 9. 20. 시행령 개정으로 삭제)", DATA)
        self.assertEqual([s.path for s in found], [("제43조", "⑦")])

    def test_a_trailing_law_without_an_address_means_the_whole_file(self):
        """마지막에 주소 없이 놓인 이름은 그 법령 전체를 가리킨다 — 고시금액이 그렇다."""
        found = law_index.resolve(
            "국가계약법 시행령 제21조 국가를 당사자로하는 계약에 관한 법률 등의 "
            "재정경제부장관이 정하는 고시금액", DATA)
        self.assertEqual(found[-1].path, ())
        self.assertIn("고시금액", found[-1].law)


if __name__ == "__main__":
    unittest.main()
