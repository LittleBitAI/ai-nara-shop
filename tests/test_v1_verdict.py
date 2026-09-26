import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
import a_v1_verdict as v1_verdict  # noqa: E402


def notice(text, law="국가계약법", method="제한경쟁"):
    return {"docs": [{"text": text}], "meta": {"적용계약법": law, "계약방법": method}}


def limit(quote, kind="facility_equipment_staff", **extra):
    return {"v1_limits": [{"quote": quote, "kind": kind, "private_firms_allowed": True, "statute_quote": None,
                           "need_quote": None, "use_quote": None, **extra}], "정보부족": False}


def test_scale_without_basis_is_v1_and_a_stated_need_clears_it():
    quote = "50명 이상의 보안인력을 보유한 업체"
    assert v1_verdict.v1(limit(quote), notice(quote)) == 1
    task = quote + " 과업: 경비 인력 50명 배치표"
    assert v1_verdict.v1(limit(quote, need_quote="경비 인력 50명 배치표"), notice(task)) == 0


def test_use_clears_only_a_local_small_value_quote():
    quote = "15톤 이상 암롤차량 보유한 업체"
    text = quote + " 과업지시서: 암롤차량으로 폐기물 운반"
    facts = limit(quote, use_quote="암롤차량으로 폐기물 운반")
    assert v1_verdict.v1(facts, notice(text, law="지방계약법", method="수의계약")) == 0
    assert v1_verdict.v1(facts, notice(text)) == 1          # 제한경쟁: relevance alone does not clear (S7-12)


def test_institution_only_and_its_exceptions():
    only = "본 입찰은 4년제 대학교만 참여 가능"
    assert v1_verdict.v1(limit(only, kind="institution_type", private_firms_allowed=False), notice(only)) == 1
    women = "「여성기업지원에 관한 법률」 제2조 제1호에 따른 여성기업"
    facts = limit(women, kind="institution_type", private_firms_allowed=False)
    assert v1_verdict.v1(facts, notice(women, method="수의계약")) == 0     # 영 제26조①5호가목5)
    assert v1_verdict.v1(facts, notice(women)) == 1


def test_a_list_line_and_an_unscaled_leasable_holding_are_not_limits():
    line = "- 차량용 소화기 1대"
    assert v1_verdict.v1(limit(line), notice(line)) == 0
    leasable = "냉동·냉장 차량을 보유 또는 임차하고 있으며, 차량보험(1인당 1천만원 이상)에 가입한 업체"
    assert v1_verdict.v1(limit(leasable), notice(leasable)) == 0
    fleet = "대형버스 5대 이상을 소유 또는 임차한 업체"
    assert v1_verdict.v1(limit(fleet), notice(fleet)) == 1


def test_stated_purpose_without_scale_is_the_contracts_own_means():
    purpose = "급식품 운반에 필요한 냉동·냉장 차량을 소유 또는 임차하고 있는 업체"
    assert v1_verdict.v1(limit(purpose), notice(purpose)) == 0
    scaled = "급식품 운반에 필요한 냉동 차량 3대 이상을 소유한 업체"
    assert v1_verdict.v1(limit(scaled), notice(scaled)) == 1
