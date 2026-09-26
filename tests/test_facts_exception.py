import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
import a_facts_verdict as fv  # noqa: E402


def test_competition_exception_is_the_sales_support_decree_article_7_only():
    match = fv.COMPETITION_EXCEPTION.search
    assert match("「중소기업제품 구매촉진 및 판로지원에 관한 법률 시행령」 제7조제1항제4호에 따라")
    assert match("중소기업자간 경쟁입찰의 예외")
    # a different clause of another decree
    assert not match("이 입찰은 국가계약법 시행령 제7조의2제2항에 따라 예정가격을 작성하지 않으며")
    # 제2조의3 excepts general products from 우선조달, not a 경쟁제품 from 중소기업자간 경쟁
    assert not match("판로지원에 관한 법률 시행령 제2조의3제2호에 따라 비영리법인은")
