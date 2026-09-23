"""무라벨 D 층 나누기의 계약: B=1 만 판정하고, D·R·Z 가 전 셀을 한 번씩 나눈다."""

import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.unlabeled_d import check_prefix, check_shards, layers  # noqa: E402


class SampleContract(unittest.TestCase):
    """Review round 2: the shards plus the failed set must be exactly a prefix of the order."""

    ORDER = ["A", "B", "C", "D", "E", "F"]

    def test_full_prefix_passes(self):
        check_prefix(["A", "B", "C", "D"], set(), self.ORDER, 4)
        check_prefix(["A", "C", "D"], {"B"}, self.ORDER, 4)

    def test_short_of_the_planned_sample_is_rejected(self):
        """Review round 3: without the run summary a failed tail looks like a smaller sample."""
        with self.assertRaises(ValueError):
            check_prefix(["A", "B"], set(), self.ORDER, 3)

    def test_missing_shard_or_gap_is_rejected(self):
        for ids, failed in ((["C", "D"], set()),          # first shard missing
                            (["A", "C"], set()),          # gap not in F
                            (["A", "B"], {"B"}),          # both succeeded and failed
                            (["A", "B", "B"], set())):    # duplicate
            with self.subTest(ids=ids, failed=failed):
                with self.assertRaises(ValueError):
                    check_prefix(ids, failed, self.ORDER, len(set(ids) | failed))


class ShardProvenance(unittest.TestCase):
    """Review round 3: every shard must come from one code and from the notices read now."""

    def meta(self, name, code="c1", commit="k1", records="h-" ):
        return {"name": name, "commit": commit, "code_sha256": code, "records_sha256": records + name}

    def test_consistent_shards_pass(self):
        check_shards([self.meta("u00"), self.meta("u01")], lambda m: "h-" + m["name"])

    def test_mixed_code_or_changed_content_is_rejected(self):
        for metas, recompute in (([self.meta("u00"), self.meta("u01", code="c2")], lambda m: "h-" + m["name"]),
                                 ([self.meta("u00"), self.meta("u01", commit="k2")], lambda m: "h-" + m["name"]),
                                 ([self.meta("u00")], lambda m: "other")):
            with self.subTest(metas=metas):
                with self.assertRaises(ValueError):
                    check_shards(metas, recompute)


class Layers(unittest.TestCase):

    def test_partitions_cells_and_judges_only_positives(self):
        seen = []

        def v3(quote, rec):
            seen.append(("v3", quote))
            return "below_budget" if quote == "지움" else None

        def v17(quote):
            seen.append(("v17", quote))
            return "no_mid_size_entity" if quote == "지움" else None

        candidate = types.SimpleNamespace(v3_deletion=v3, v17_deletion=v17)
        rows = [{"id": "A", "v3": "1", "e3": "지움", "v17": "0", "e17": ""},
                {"id": "B", "v3": "1", "e3": "남김", "v17": "1", "e17": "지움"},
                {"id": "C", "v3": "0", "e3": "", "v17": "0", "e17": ""}]
        out = layers(rows, {r["id"]: {} for r in rows}, candidate)
        self.assertEqual([c["id"] for c in out["v3"]["D"]], ["A"])
        self.assertEqual((out["v3"]["R"], out["v3"]["Z"]), (1, 1))
        self.assertEqual([c["id"] for c in out["v17"]["D"]], ["B"])
        self.assertEqual((out["v17"]["R"], out["v17"]["Z"]), (0, 2))
        self.assertNotIn(("v3", ""), seen, "B=0 셀은 판정하지 않는다")

    def test_rejects_values_outside_the_csv_contract(self):
        """Review round 1: a corrupted cell must not be counted as Z."""
        candidate = types.SimpleNamespace(v3_deletion=lambda q, r: None, v17_deletion=lambda q: None)
        for bad in ("2", "", " 1", "1.0"):
            for quote in ("q", ""):   # with and without evidence, so the value check stands alone
                with self.subTest(value=bad, quote=quote):
                    rows = [{"id": "X", "v3": bad, "e3": quote, "v17": "0", "e17": ""}]
                    with self.assertRaises(ValueError):
                        layers(rows, {"X": {}}, candidate)

    def test_rejects_evidence_that_breaks_the_postprocess_contract(self):
        """Review round 2: production writes evidence for every v3/v17 positive and none for a 0."""
        candidate = types.SimpleNamespace(v3_deletion=lambda q, r: None, v17_deletion=lambda q: None)
        for row in ({"id": "X", "v3": "0", "e3": "", "v17": "1", "e17": ""},
                    {"id": "X", "v3": "1", "e3": "  ", "v17": "0", "e17": ""},
                    {"id": "X", "v3": "0", "e3": "stray", "v17": "0", "e17": ""}):
            with self.subTest(row=row):
                with self.assertRaises(ValueError):
                    layers([row], {"X": {}}, candidate)


if __name__ == "__main__":
    unittest.main()
