"""구조 인지 법령 조회 검사. 모델을 부르지 않는다. 성능 검사가 아니다.

여기서 지키는 것은 **주소지정**이다. 항목표의 인용 31개가 전부 비어 있지 않은 원문으로 풀리고,
돌려준 조각이 제공 파일의 부분문자열인지 본다. 조문을 발명하면 여기서 걸린다.

만들면서와 리뷰 두 라운드에서 실제로 걸린 오류를 회귀로 고정한다.
앞의 넷은 만들면서, 뒤의 여섯은 리뷰가 잡았다. **전부 "조용히 틀린 값을 돌려주는" 쪽이다.**

1. `국가계약법 시행령 제21조` 가 **시행령이 아니라 법률** 제21조로 풀렸다.
   약칭 다섯 자만 법령 이름으로 잡히고 ` 시행령` 이 주소 쪽에 남았다.
   못 푸는 것보다 나쁘다 — 조용히 틀린 원문을 돌려준다.
2. `[별표1]` 은 본문 안 참조로도 쓰인다. 첫 등장에서 별표 구역을 자르면
   「지방자치단체 입찰시 낙찰자 결정기준」이 420,768자 → 11,267자가 된다.
3. `제2조의2` 는 **'조'로 끝나지 않는다.** 끝글자로 종류를 가르면 통째로 빠진다.
4. 주소가 안 붙은 법령을 파일 전체로 펴면 `소프트웨어진흥법 … 지침 제2조 별표1` 에서
   진흥법 37,234자가 딸려 온다.
5. 주소를 **평탄한 목록**으로 소비하면 `제2장 … 제5조` 가 부모(7,021자)와 자식(2,292자)을
   둘 다 돌려준다. v9 크기를 13,516자로 부풀려 "안 들어감" 으로 적게 했다. (라운드 1)
6. `제5장 제3절 1. 나.` 의 `나.` 가 조용히 버려졌다. (라운드 1)
7. `제3장의2` 가 `제3장` 으로 풀려 **다른 장의 원문**을 돌려줬다. (라운드 1)
8. 항을 지목했는데 없으면 **조 전체로 확대**됐고 토큰이 소비돼 strict 도 침묵했다. (라운드 2)
9. `1. 2.` 형제를 중첩 경로로 읽어 유효한 인용이 실패했다. (라운드 2)
10. 법령 이름을 못 찾으면 strict 에서도 **빈 결과로 성공**했다. (라운드 2)
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

    def test_a_missing_paragraph_does_not_widen_to_the_whole_article(self):
        """항을 지목했는데 없으면 **조 전체로 넓히지 않는다.**

        넓히면 요청하지 않은 조 전문 2,646자가 근거가 되고, 토큰이 소비돼 strict 도 침묵한다.
        """
        with self.assertRaises(ValueError):
            law_index.resolve("국가계약법 시행령 제21조 제20항", DATA)
        self.assertEqual(law_index.resolve("국가계약법 시행령 제21조 제20항", DATA, strict=False), [])
        kept = law_index.resolve("국가계약법 시행령 제21조 제1항", DATA)
        self.assertEqual([s.path for s in kept], [("제21조", "①")])

    def test_same_kind_items_are_siblings_not_a_nested_path(self):
        """`1. 2.` 는 제3절의 형제 둘이고 `1. 나.` 는 `1.` 안의 `나.` 하나다.

        하나의 중첩 경로로 읽으면 `1.` 안에서 `2.` 를 찾다가 유효한 인용이 실패한다.
        """
        siblings = law_index.resolve(
            "지방자치단체 입찰 및 계약 집행기준 제5장 제3절 1. 및 2. 항목", DATA)
        self.assertEqual([s.path for s in siblings],
                         [("제5장", "제3절", "1."), ("제5장", "제3절", "2.")])
        self.assertEqual(law_index._item_paths(["1.", "나.", "다."]),
                         [("1.", "나."), ("1.", "다.")])

    def test_an_unknown_law_name_is_not_a_silent_empty_success(self):
        """주소는 있는데 법령을 못 찾으면 빈 성공이 아니라 실패다.

        오타나 스냅샷 불일치가 **근거 없는 판정**으로 흘러가는 경로였다.
        """
        with self.assertRaises(ValueError):
            law_index.resolve("없는법 제1조", DATA)
        self.assertEqual(law_index.resolve("없는법 제1조", DATA, strict=False), [])
        self.assertEqual(law_index.resolve("법령 이름만 있고 주소가 없다", DATA), [])

    def test_a_paragraph_that_has_no_marker_does_not_widen_either(self):
        """`제0항` · `제21항` 은 동그라미 표시로 못 바꾼다 — 그래도 **요청은 있었다.**

        표시가 없다고 `article(..., None)` 을 부르면 존재하는 조의 전문이 돌아오고
        토큰이 소비돼 strict 가 또 침묵한다. 라운드 2 수정이 못 막은 자리다.
        """
        for citation in ("국가계약법 시행령 제21조 제0항", "국가계약법 시행령 제21조 제21항"):
            with self.assertRaises(ValueError, msg=citation):
                law_index.resolve(citation, DATA)

    def test_item_paths_return_to_an_ancestor_of_the_same_kind(self):
        """`1. 나. 2.` 는 `(1.,나.)` 와 최상위 형제 `(2.,)` 둘이다.

        마지막 토큰만 보면 `2.` 가 `나.` 아래로 들어가 세 층짜리 경로 하나가 된다.
        """
        self.assertEqual(law_index._item_paths(["1.", "나.", "2."]), [("1.", "나."), ("2.",)])
        self.assertEqual(law_index._item_paths(["가.", "1."]), [("가.", "1.")])
        found = law_index.resolve(
            "지방자치단체 입찰 및 계약 집행기준 제5장 제3절 1. 나. 및 2. 항목", DATA)
        self.assertEqual([s.path for s in found],
                         [("제5장", "제3절", "1.", "나."), ("제5장", "제3절", "2.")])

    def test_normal_article_titles_and_connectives_are_never_cut(self):
        """조문 제목과 `같은 법` 연결어가 **정상 인용을 자르면 안 된다.**

        미등록 법령을 이름 모양으로 찾으려던 두 번의 시도가 모두 여기서 깨졌다 —
        한글 덩어리 전부(라운드 4), 법령 접미사로 끝나는 덩어리(라운드 5).
        제공 법령의 **조문 제목 43종**이 `기준`·`요령`·`방법` 으로 끝난다.
        """
        cases = {
            "국가계약법 시행령 제12조 경쟁입찰의 참가자격 제21조 제한경쟁입찰에 의할 계약과 "
            "제한사항등": [("제12조",), ("제21조",)],
            "국가계약법 시행령 제21조 제1항 및 같은 법 제22조": [("제21조", "①"), ("제22조",)],
            "국가계약법 시행규칙 제25조 제한경쟁입찰의 제한기준 제27조 지명경쟁입찰의 지명기준":
                [("제25조",), ("제27조",)],
            "국가계약법 시행령 제21조 물품제조계약 제22조": [("제21조",), ("제22조",)],
        }
        for citation, paths in cases.items():
            self.assertEqual([s.path for s in law_index.resolve(citation, DATA)], paths, citation)

    def test_an_unknown_law_after_a_known_one_is_a_documented_hole(self):
        """**문자열만으로는 못 가른다.** 이 한계를 검사로 고정해 둔다.

        `제22조` 는 앞 법령에도 실제로 존재하므로 어느 쪽을 가리켰는지 텍스트가 말해
        주지 않는다. 두 번의 휴리스틱이 모두 정상 인용을 잘랐으므로 판별을 **안 한다.**
        경계는 계약으로 옮겼다 — 항목표 31개는 전수 검사, 그 밖에는 `article()` 직접 호출.
        """
        found = law_index.resolve("국가계약법 시행령 제21조 없는법 제22조", DATA)
        self.assertEqual([s.path for s in found], [("제21조",), ("제22조",)])
        self.assertTrue(all(s.law.endswith("시행령") for s in found))
        with self.assertRaises(ValueError):     # 아는 법령이 하나도 없으면 여전히 실패한다
            law_index.resolve("없는법 제1조", DATA)

    def test_malformed_paragraph_markers_are_not_silently_dropped(self):
        """`제항` 은 토큰이 안 되고 `제-1항` 은 `1항` 으로 잡혔다.

        둘 다 **조 전문 또는 엉뚱한 항**을 성공으로 돌려줬다. 주소를 흉내 낸 표기는
        토큰이 안 되더라도 미소비로 남아야 한다.
        """
        for citation in ("국가계약법 시행령 제21조 제항", "국가계약법 시행령 제21조 제-1항",
                         "국가계약법 시행령 제21조 제+1항", "국가계약법 시행령 제21조 제/1항"):
            with self.assertRaises(ValueError, msg=citation):
                law_index.resolve(citation, DATA)
        self.assertEqual([s.path for s in law_index.resolve("국가계약법 시행령 제21조 제1항", DATA)],
                         [("제21조", "①")])
        self.assertEqual([s.path for s in law_index.resolve("지방계약법 시행령 제43조 7항", DATA)],
                         [("제43조", "⑦")])

    def test_the_word_hangmok_is_not_a_paragraph_address(self):
        """`제3항목` 의 `제3항` 을 항으로 읽으면 **근거 범위를 조용히 좁힌다.**

        조 전문(2,646자) 대신 ③항(208자)이 돌아왔다. 조사 결합 `제1항의` 는 유지한다.
        """
        found = law_index.resolve("국가계약법 시행령 제21조 제3항목", DATA)
        self.assertEqual([s.path for s in found], [("제21조",)])
        self.assertEqual([s.path for s in law_index.resolve("국가계약법 시행령 제21조 제3항", DATA)],
                         [("제21조", "③")])
        self.assertEqual(law_index.ADDRESS.findall("제1항의 규정"), ["제1항"])

    def test_a_trailing_law_without_an_address_means_the_whole_file(self):
        """마지막에 주소 없이 놓인 이름은 그 법령 전체를 가리킨다 — 고시금액이 그렇다."""
        found = law_index.resolve(
            "국가계약법 시행령 제21조 국가를 당사자로하는 계약에 관한 법률 등의 "
            "재정경제부장관이 정하는 고시금액", DATA)
        self.assertEqual(found[-1].path, ())
        self.assertIn("고시금액", found[-1].law)


if __name__ == "__main__":
    unittest.main()
