"""무라벨 표본 추첨의 계약: 본 공고와 그 복제는 빠지고, 순서는 seed 로만 정해진다."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.unlabeled_sample import draw  # noqa: E402


def rec(identifier, text):
    return {"id": identifier, "docs": [{"type": "공고문", "text": text}]}


class Draw(unittest.TestCase):

    def records(self):
        return [rec("A", "본문1"), rec("B", "본문2"), rec("C", "본문1"), rec("D", "본문3"),
                rec("E", "본문4"), rec("F", "본문5")]

    def test_seen_and_its_byte_duplicates_are_excluded(self):
        order, info = draw(self.records(), {"A"})
        self.assertEqual(info["excluded"], {"A": "seen", "C": "duplicate_of_seen"})
        self.assertEqual(sorted(order), ["B", "D", "E", "F"])

    def test_order_depends_only_on_seed_not_on_input_order(self):
        first, _ = draw(self.records(), {"A"}, seed=7)
        second, _ = draw(list(reversed(self.records())), {"A"}, seed=7)
        self.assertEqual(first, second)
        self.assertNotEqual(first, draw(self.records(), {"A"}, seed=8)[0])

    def test_prefix_is_stable_when_keeping_more(self):
        """2,000건에서 6,000건으로 늘려도 앞 2,000건은 같아야 한다."""
        short, _ = draw(self.records(), set(), keep=2)
        long, _ = draw(self.records(), set(), keep=5)
        self.assertEqual(long[:2], short)

    def test_rejects_duplicate_ids_and_unknown_seen(self):
        with self.assertRaises(ValueError):
            draw(self.records() + [rec("B", "x")], set())
        with self.assertRaises(ValueError):
            draw(self.records(), {"Z"})


if __name__ == "__main__":
    unittest.main()
