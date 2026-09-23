"""무라벨 D 층 나누기의 계약: B=1 만 판정하고, D·R·Z 가 전 셀을 한 번씩 나눈다."""

import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.unlabeled_d import layers  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
