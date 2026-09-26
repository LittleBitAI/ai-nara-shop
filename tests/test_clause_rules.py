import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("script_clause_rules", ROOT / "script.py")
script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script)


def notice(text, **meta):
    base = {"적용계약법": "국가계약법", "계약방법": "제한경쟁", "업무구분": "일반용역", "입찰추정가격": 80_000_000}
    return {"id": "T", "docs": [{"doc_id": "D0", "type": "공고문", "text": text}], "meta": {**base, **meta}}


def cells(**values):
    out = {f"v{i}": {"위반여부": 0, "근거문구": ""} for i in range(1, 25)}
    for item, value in values.items():
        out[item] = {"위반여부": value, "근거문구": ""}
    return out


class SizeLimitTests(unittest.TestCase):
    def test_a_size_limit_on_the_bidder_lowers_v11(self):
        rec = notice("1. 입찰참가자격\n가. 「중소기업기본법」 제2조에 따른 소기업 또는 소상공인으로서 확인서를 소지한 업체")
        # The quote is "", not None: write_csv writes None as the text "None" and the CSV check rejects it.
        self.assertEqual(script.apply_clause_rules(cells(v11=1), rec)["v11"], {"위반여부": 0, "근거문구": ""})

    def test_limits_written_with_a_quote_mark_or_a_copula_count(self):
        # Off-dev batch 2: "확인서’를 소지한 업체" and "소상공인인 업체" are bidder conditions too.
        for text in ("가. 소기업 또는 소상공인으로‘소기업, 소상공인 확인서’를 소지한 업체",
                     "가. 「소상공인 보호 및 지원에 관한 법률」 제2조에 따른 소기업자 및 소상공인인 업체"):
            with self.subTest(text=text):
                self.assertTrue(script.size_limited(notice(text)))

    def test_a_website_name_or_a_document_line_is_not_a_limit(self):
        for text in ("중소기업공공구매 종합정보망에서 확인되지 않을 경우, 입찰 참가 자격이 없습니다.",
                     "제출서류\n⑤ 소기업·소상공인 확인서 1부"):
            with self.subTest(text=text):
                self.assertFalse(script.size_limited(notice(text)))


class ReviewRoundOneTests(unittest.TestCase):
    """PR #153 round 1 findings, each on the reviewer's own input."""

    def test_a_raised_quote_with_a_formula_prefix_is_not_written(self):
        plain = notice("공동수급 안내: 구성원별 최소 지분율은 3% 이상입니다.", 공동도급구성방식="공동이행")
        self.assertEqual(script.apply_clause_rules(cells(), plain)["v21"]["위반여부"], 1)   # the rule fires
        rec = notice("= 공동수급 안내: 구성원별 최소 지분율은 3% 이상입니다.", 공동도급구성방식="공동이행")
        out = script.apply_clause_rules(cells(), rec)
        self.assertFalse(out["v21"]["근거문구"].startswith(("=", "+", "@")))

    def test_the_size_clause_does_not_reach_the_next_list_item(self):
        text = "입찰참가자격\n가. 소기업 확인서는 제출 선택 사항입니다.\n나. 입찰은 대기업으로 제한합니다."
        self.assertFalse(script.size_limited(notice(text)))
        # Round 2: flattened text keeps its list markers inline.
        self.assertFalse(script.size_limited(notice("입찰참가자격 가. 소기업 확인서는 선택사항, 나. 입찰은 대기업으로 제한합니다.")))
        # Round 3: a marker glued to punctuation is still a boundary.
        self.assertFalse(script.size_limited(notice("입찰참가자격 가. 소기업 확인서는 선택사항,나.입찰은 대기업으로 제한합니다.")))
        # A limit that wraps within its own clause still counts.
        self.assertTrue(script.size_limited(notice("입찰참가자격\n가. 「중소기업기본법」 제2조에 따른 소기업 또는\n소상공인으로서 확인서를 소지한 업체")))

    def test_a_body_mention_of_negotiation_is_not_the_contract_method(self):
        text = "협상 관련 안내는 별첨을 참고하세요. 제안설명회에 참석하지 않은 업체는 입찰에 참가할 수 없습니다."
        self.assertEqual(script.apply_clause_rules(cells(), notice(text, 낙찰방법="적격심사제"))["v22"]["위반여부"], 0)

    def test_a_catalogue_name_in_the_registered_clause_keeps_the_product(self):
        script.load_sme_reference(str(ROOT / "open/data"))
        name = script._PRODUCTS[0]["세부품명"]
        rec = notice("품명: 기타 물품", 세부품명번호목록="[9999999999]", 조항호내용=name)
        self.assertFalse(script.catalogue_miss(rec))


class OffDevBatchTwoTests(unittest.TestCase):
    def test_v8_is_not_raised_on_a_local_small_quote(self):
        text = "1. 견적제출 자격\n가. 경상북도에 소재하고 최근 3년간 유사 용역 실적이 있는 업체"
        local = notice(text, 적용계약법="지방계약법", 계약방법="수의계약")
        self.assertTrue(script.local_small_quote(local))
        self.assertEqual(script.apply_qualification_rules(cells(), local)["v8"]["위반여부"], 0)

    def test_a_pledge_list_heading_past_notes_and_sub_bullets(self):
        lines = ["다. 입찰 시 제출서류 [나라장터를 통한 온라인 제출]", "③ 법인등기부등본 1부",
                 "- 증빙자료 : 카탈로그 등 규격 사항 증빙자료", "⑦ 제조자 정품 공급 및 기술지원 확약서"]
        self.assertTrue(script.list_heading(lines, 3).startswith("- 증빙자료"))       # the old lookup stops here
        self.assertTrue(script.enumerated_heading(lines, 3).startswith("다. 입찰 시"))
        self.assertTrue(script.v19_demanded_at_bid_stage(notice("\n".join(lines))))


class Pr154RoundOneTests(unittest.TestCase):
    """PR #154 round 1 findings, each on the reviewer's own input."""

    def test_an_unmarked_section_heading_ends_the_walk(self):
        lines = ["다. 입찰 시 제출서류", "③ 사업자등록증", "계약 체결 후 제출서류", "① 물품공급 확약서 1부"]
        self.assertEqual(script.enumerated_heading(lines, 3), "계약 체결 후 제출서류")
        self.assertFalse(script.v19_demanded_at_bid_stage(notice("\n".join(lines))))

    def test_a_large_local_negotiated_contract_is_not_a_small_quote(self):
        self.assertFalse(script.local_small_quote(notice("x", 적용계약법="지방계약법", 계약방법="수의계약",
                                                         입찰추정가격=300_000_000)))

    def test_a_bare_bid_time_on_the_pledge_line_is_another_requirement(self):
        text = "계약 시 제출서류: 물품공급 확약서 1부. 입찰 시 평가표는 별첨."
        self.assertFalse(script.v19_demanded_at_bid_stage(notice(text)))

    def test_round_two_bid_time_in_the_pledge_sentence_counts(self):
        # PR #154 round 2: the timing on the pledge's own sentence governs it.
        for text in ("① 입찰 시 물품공급 확약서 1부 제출", "물품공급 확약서는 입찰 시 제출하여야 합니다."):
            with self.subTest(text=text):
                self.assertTrue(script.v19_demanded_at_bid_stage(notice(text)))

    def test_round_three_a_contract_time_in_the_sentence_binds_to_the_comma_clause(self):
        # PR #154 round 3: "… 확약서 1부, 입찰 시 평가표는 별첨" — the pledge is due at contract time.
        self.assertFalse(script.v19_demanded_at_bid_stage(notice("계약 시 제출서류: 물품공급 확약서 1부, 입찰 시 평가표는 별첨")))
        # Round 6: a bare bid time counts only in the pledge's own clause, so a section named by its recipient
        # ("낙찰자 제출서류") cannot borrow another clause's time either.
        for text in ("낙찰자 제출서류: 물품공급 확약서 1부, 입찰 시 평가표는 별첨",
                     "계약상대자 제출서류: 물품공급 확약서 1부, 입찰 시 평가표는 별첨"):
            with self.subTest(text=text):
                self.assertFalse(script.v19_demanded_at_bid_stage(notice(text)))

    def test_round_five_post_award_phrases_bind_the_bid_time_too(self):
        for text in ("낙찰 후 제출서류: 물품공급 확약서 1부, 입찰 시 평가표는 별첨",
                     "계약 후 제출서류: 물품공급 확약서 1부, 입찰 시 평가표는 별첨"):
            with self.subTest(text=text):
                self.assertFalse(script.v19_demanded_at_bid_stage(notice(text)))

    def test_round_seven_the_bid_time_must_modify_the_pledge_submission(self):
        self.assertFalse(script.v19_demanded_at_bid_stage(notice("물품공급 확약서는 낙찰자가 제출하며 입찰 시 가격평가를 진행합니다.")))
        # Round 9: a negated demand is no demand.
        for text in ("물품공급 확약서는 입찰 시 제출하지 않습니다.", "입찰 시 물품공급 확약서 제출은 요구하지 않습니다.",
                     "물품공급 확약서는 입찰 시 제출 대상이 아닙니다.", "입찰 시 물품공급 확약서 제출은 필수가 아닙니다.",
                     "입찰 시 물품공급 확약서 제출 의무 없음", "입찰 시 물품공급 확약서 제출 불요",
                     "입찰 시 물품공급 확약서 제출은 선택사항",
                     "입찰 시 물품공급 확약서는 제출하지 말 것", "입찰 시 물품공급 확약서 제출 금지",
                     # Round 13: optional, deferred or incentive wording states no demand.
                     "입찰 시 물품공급 확약서 제출은 권장사항입니다.", "입찰 시 물품공급 확약서 제출은 자율입니다.",
                     "입찰 시 물품공급 확약서 제출은 선택입니다.", "입찰 시 물품공급 확약서 제출 시 가점을 부여합니다.",
                     "입찰 시 물품공급 확약서는 제출할 수 있습니다.", "입찰 시 물품공급 확약서 제출 가능합니다.",
                     "입찰 시 물품공급 확약서 제출은 보류합니다.", "입찰 시 물품공급 확약서 제출은 유예합니다.",
                     "입찰 시 물품공급 확약서 제출은 추후 안내합니다.", "입찰 시 물품공급 확약서 제출 안 함"):
            with self.subTest(text=text):
                self.assertFalse(script.v19_demanded_at_bid_stage(notice(text)))
        # Round 8: "입찰 시 제출한 가격표" is another item's bid-stage submission.
        self.assertFalse(script.v19_demanded_at_bid_stage(notice("물품공급 확약서는 낙찰자가 제출하며 입찰 시 제출한 가격표를 평가합니다.")))

    def test_a_flattened_list_item_is_its_own_sentence(self):
        text = "① 입찰 시 제안서 6부 제출 ② 증빙서류 각 1부 ㉰ “확약서” 1부 [별지 7]"
        self.assertFalse(script.v19_demanded_at_bid_stage(notice(text)))

    def test_round_two_prose_is_not_a_heading_but_a_named_section_is(self):
        prose = ["다. 입찰 시 제출서류", "제출서류는 다음과 같습니다.", "① 물품공급 확약서 1부"]
        self.assertTrue(script.v19_demanded_at_bid_stage(notice("\n".join(prose))))
        after = ["다. 입찰 시 제출서류", "③ 사업자등록증", "계약 체결 후 제출자료", "① 물품공급 확약서 1부"]
        self.assertFalse(script.v19_demanded_at_bid_stage(notice("\n".join(after))))

    def test_the_copula_close_attaches_to_the_size_word(self):
        self.assertFalse(script.size_limited(notice("입찰참가자격\n가. 소기업 확인서는 필요 없으며 참여 가능한 법인 업체")))


class RaiseTests(unittest.TestCase):
    def test_v2_rises_below_the_notice_amount_but_not_for_a_local_small_quote(self):
        text = "1. 입찰참가자격\n가. 최근 3년 이내 유사 용역 실적이 있는 업체이어야 합니다."
        self.assertEqual(script.apply_clause_rules(cells(), notice(text))["v2"]["위반여부"], 1)
        local = notice(text, 적용계약법="지방계약법", 계약방법="수의계약")
        self.assertEqual(script.apply_clause_rules(cells(), local)["v2"]["위반여부"], 0)
        above = notice(text, 입찰추정가격=300_000_000)
        self.assertEqual(script.apply_clause_rules(cells(), above)["v2"]["위반여부"], 0)

    def test_v22_rises_only_on_a_negotiated_contract(self):
        text = "제안설명회에 참석하지 않은 업체는 입찰에 참가할 수 없습니다."
        rec = notice(text, 낙찰방법="협상에의한계약")
        self.assertEqual(script.apply_clause_rules(cells(), rec)["v22"]["위반여부"], 1)
        self.assertEqual(script.apply_clause_rules(cells(), notice(text, 낙찰방법="적격심사제"))["v22"]["위반여부"], 0)


if __name__ == "__main__":
    unittest.main()
