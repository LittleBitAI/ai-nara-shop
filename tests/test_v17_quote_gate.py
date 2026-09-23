"""v17 production gate: a positive whose quote names only a narrow qualification is refuted.

Adopted from experiments/quoted_deletion_candidate.py after the unlabeled 6,000 audit
(reports/label-compare/unlabeled-d/README.md): 32 drawn deletions, 0 labeller losses,
98.75% upper 0.163 < gate 0.166.
"""

import csv
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import replay_run  # noqa: E402

script = replay_run.load_module(ROOT / "script.py", "submission")
CASE = ROOT / "reports/runs/colab-1789902969401579900/dev-debug"


def refutes(quote):
    return script.evidence_refutes("v17", quote, {"docs": [], "meta": {}})


class NarrowQualification(unittest.TestCase):

    def test_narrow_only_is_refuted(self):
        for quote in ("거. 소기업 또는 소상공인확인서 1부",
                      "소기업(소상공인) 확인서를(응찰(개찰)일 까지 발급된 것) 소지한 업체",
                      "「중소기업기본법」 제2조제2항에 따른 소기업 또는 「소상공인기본법」 제2조에 따른 "
                      "소상공인으로서 「중소기업 범위 및 확인에 관한 규정」에 따라 발급된 "
                      "소기업·소상공인 확인서를 소지한 자",
                      "중소기업기본법 제2조에 따른 소기업자",
                      "「중소기업진흥에 관한 법률」에 따른 소기업",
                      "「중소기업기본법」 제2조의 규정에 의한 소기업 또는 소상공인",
                      "「여성기업지원에 관한 법률」 제2조 제1호에 따른 여성기업"):
            with self.subTest(quote=quote):
                self.assertTrue(refutes(quote))

    def test_mid_size_entity_is_kept(self):
        for quote in ("「중소기업기본법」제2조에 따른 중소기업 또는 소상공인으로서 확인서를 소지한 자",
                      "「중소기업제품 구매촉진 및 판로지원에 관한 법률」 제8조의 요건을 갖춘 중소기업자",
                      "중소기업기본법 제2조 제2항에 따른 중·소기업 또는 소상공인",
                      "｢중소기업기본법｣ 제2조에 따른 중・소기업자",
                      "중,소기업제한", "중기업 및 소기업",
                      "참가자격은 「중소기업」 또는 「소상공인」으로 제한한다",
                      "중소기업 범위에 해당하는 업체", "중소기업제품을 생산하는 업체"):
            with self.subTest(quote=quote):
                self.assertFalse(refutes(quote))

    def test_article_designation_of_sme_is_kept(self):
        """Article 2 of the SME Framework Act defines SMEs, mid-size included."""
        for quote in ("「중소기업기본법」 제2조에 따른 업체",
                      "「중소기업기본법」 제2조에 따른 업체 또는 소상공인",
                      "「중소기업기본법」 제2조의 규정에 따른 업체 또는 소상공인",
                      "「중소기업기본법」 제2조에 의한 업체 또는 소상공인",
                      "「중소기업기본법」 제2조 및 「소상공인 보호 및 지원에 관한 법률」 제2조에 따른 업체 또는 소상공인",
                      "중소기업기본법 제2조에 따른 기업,소상공인기본법 제2조상 소상공인",
                      "「중소기업기본법」 제2조 해당 여부는 입찰 공고일 현재를 기준으로 판단하며 소상공인 확인서를 제출"):
            with self.subTest(quote=quote):
                self.assertFalse(refutes(quote))

    def test_quote_without_narrow_entity_is_kept(self):
        self.assertFalse(refutes("입찰참가자격을 갖춘 업체"))
        self.assertFalse(refutes(""))


class DevReplay(unittest.TestCase):
    """Pin the v17 effect on the stored baseline run (HEAD replay, no model call)."""

    @classmethod
    def setUpClass(cls):
        if not (CASE / "diagnostics.jsonl").is_file():
            raise unittest.SkipTest(f"{CASE} missing")
        cls.rows = replay_run.replay(script, CASE, input_path=ROOT / "open/dev.jsonl",
                                     data_dir=ROOT / "open/data")["rows"]
        with (ROOT / "open/dev_labels.csv").open(encoding="utf-8", newline="") as stream:
            cls.truth = {r["id"]: r["v17"] == "1" for r in csv.DictReader(stream)}

    def test_v17_counts(self):
        tp = sum(1 for r in self.rows if r["v17"] == 1 and self.truth[r["id"]])
        fp = sum(1 for r in self.rows if r["v17"] == 1 and not self.truth[r["id"]])
        fn = sum(1 for r in self.rows if r["v17"] == 0 and self.truth[r["id"]])
        self.assertEqual((tp, fp, fn), (5, 2, 1))   # was 5/6/1; 038, 102, 120, 172 refuted


if __name__ == "__main__":
    unittest.main()
