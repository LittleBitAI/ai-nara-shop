import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
import a_facts_verdict as fv  # noqa: E402


def test_a_catalogue_name_counts_only_as_the_head_of_the_object_name():
    # PR #153 round 2: "매트리스 동적 롤링시스템" is a test system, not the catalogue item 매트리스.
    assert fv.object_heads("매트리스 동적 롤링시스템", None) == ["매트리스동적롤링시스템"]
    assert not any(h.endswith("매트리스") for h in fv.object_heads("매트리스 동적 롤링시스템", None))
    assert any(h.endswith("책상") for h in fv.object_heads("사무용 책상 구매", None))
    assert fv.object_heads(None, "피로시험기[4111460801]") == ["피로시험기"]
    # Round 3: only separate words are cut — "등" ends catalogue names like 태양광가로등.
    assert fv.object_heads("태양광가로등", None) == ["태양광가로등"]
    assert fv.object_heads("태양광가로등 설치 및 교체", None) == ["태양광가로등"]
    assert fv.object_heads("사무용 책상 1식 (별첨 규격)", None) == ["사무용책상"]


def test_every_catalogue_name_matches_itself_as_an_object_name():
    # Round 3: cutting procurement words must never cut a designated item's own name (태양광가로등, 원격단말장치(RTU)).
    fv.products()
    for row in fv.script._PRODUCTS:
        item = fv.squash(fv.NOTES.sub("", row["세부품명"]))
        assert any(head.endswith(item) for head in fv.object_heads(row["세부품명"], None)), row["세부품명"]


def test_competition_exception_is_the_sales_support_decree_article_7_only():
    match = fv.COMPETITION_EXCEPTION.search
    assert match("「중소기업제품 구매촉진 및 판로지원에 관한 법률 시행령」 제7조제1항제4호에 따라")
    assert match("중소기업자간 경쟁입찰의 예외")
    # a different clause of another decree
    assert not match("이 입찰은 국가계약법 시행령 제7조의2제2항에 따라 예정가격을 작성하지 않으며")
    # 제2조의3 excepts general products from 우선조달, not a 경쟁제품 from 중소기업자간 경쟁
    assert not match("판로지원에 관한 법률 시행령 제2조의3제2호에 따라 비영리법인은")
