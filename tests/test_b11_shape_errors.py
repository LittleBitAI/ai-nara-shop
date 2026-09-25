"""B11/B12 verdicts drop replies whose values, or list elements, are not the question's shapes."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools"), str(ROOT / "experiments")]
import b11_b_facts_v2_verdict as v2  # noqa: E402

SCHEMA = {"v19_documents": [v2.V19_DOCUMENT], "정보부족": bool}


class ShapeErrors(unittest.TestCase):
    def test_a_nested_timing_list_is_a_failed_reply_not_a_negative(self):
        doc = {"name": "기술지원확약서", "timing": ["입찰 시"], "timing_from": "same_sentence"}
        self.assertEqual(v2.v1.shape_errors({"v19_documents": [doc], "정보부족": False}, SCHEMA),
                         ["v19_documents"])

    def test_a_string_element_where_an_object_belongs_fails(self):
        self.assertEqual(v2.v1.shape_errors({"v19_documents": ["x"], "정보부족": False}, SCHEMA),
                         ["v19_documents"])

    def test_extra_element_keys_are_allowed(self):
        doc = {"name": "확약서", "timing": None, "timing_from": "list_heading", "list_heading": "가."}
        self.assertEqual(v2.v1.shape_errors({"v19_documents": [doc], "정보부족": False}, SCHEMA), [])

    def test_scalar_elements_are_checked_too(self):
        self.assertEqual(v2.v1.shape_errors({"v24_regions": ["경상남도", 3]}, {"v24_regions": [str]}),
                         ["v24_regions"])


if __name__ == "__main__":
    unittest.main()
