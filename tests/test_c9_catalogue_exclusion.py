"""C7+C9 의 계약 — **대가 없이 올린다.** 내려가는 항목이 하나도 없어야 한다.

이 묶음의 값은 크기가 아니라 성질이다. TP 를 안 지우는 것에 더해 **어느 항목의 F1 도
안 내린다.** 그것이 무너지면 이 후보를 다시 볼 이유가 사라지므로 검사로 박는다.

고정하는 것 다섯.
  1. 기준선이 보고서의 Macro 를 그대로 낸다
  2. C7 · C9 · 통합이 각각 보고서의 수를 낸다
  3. 통합이 **개별 합과 정확히 같다** — 두 후보가 다른 단계·다른 항목을 건드린다
  4. **F1 이 내려가는 항목이 없다** (C8 을 안 넣은 이유이기도 하다)
  5. C9 의 게이트가 `script.py:102` 가 기각한 게이트와 **방향이 반대**다 —
     품번이 없는 공고를 안 건드려야 양성 7건이 산다

모델을 부르지 않는다.
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "reports/runs/colab-1790396310565903096/dev-debug"
BASE_REV = "772ca12"
ITEMS = [f"v{i}" for i in range(1, 25)]
C_ITEMS = ("v10", "v11", "v12", "v13", "v14", "v15", "v16", "v17", "v18", "v20")
OFF_TARGET = [i for i in ITEMS if i not in C_ITEMS]

CANDIDATES = {
    "c7": "experiments/c7_role_over_value_candidate.py",
    "c9": "experiments/c9_catalogue_exclusion_candidate.py",
    "integrated": "experiments/c9_integrated_candidate.py",
}
BASE_MACRO = "0.825021628698"
EXPECTED_MACRO = {
    "c7": "0.829829321006",
    "c9": "0.826608930285",
    "integrated": "0.831416622593",
}
EXPECTED_CHANGED = {"c7": 1, "c9": 1, "integrated": 2}
# 통합에서 움직이는 항목과 그 TP/FP/FN.
EXPECTED_ITEMS = {"v10": (4, 3, 3), "v18": (4, 2, 3)}


class Replay(unittest.TestCase):
    """기준 커밋 위에서 보고서의 수가 나오는가."""

    @classmethod
    def setUpClass(cls):
        if shutil.which("git") is None:
            raise unittest.SkipTest("git 이 없다")
        if not (CASE / "diagnostics.jsonl").is_file():
            raise unittest.SkipTest(f"{CASE} 가 없다")
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.pinned = root / "script.py"
        cls.pinned.write_bytes(subprocess.run(
            ["git", "-C", str(ROOT), "show", f"{BASE_REV}:script.py"],
            capture_output=True, check=True).stdout)
        cls.rows, cls.macro, cls.metrics = {}, {}, {}
        cls.rows["head"], cls.macro["head"], cls.metrics["head"] = cls.replay(
            root, "head", None)
        for name, path in CANDIDATES.items():
            cls.rows[name], cls.macro[name], cls.metrics[name] = cls.replay(
                root, name, str(ROOT / path))

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "tmp"):
            cls.tmp.cleanup()

    @classmethod
    def replay(cls, root, name, candidate):
        out = root / name
        command = [sys.executable, "-X", "utf8", str(ROOT / "tools/replay_run.py"),
                   "--case", str(CASE), "--script", str(cls.pinned),
                   "--output-dir", str(out)]
        if candidate:
            command += ["--candidate", candidate]
        done = subprocess.run(command, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", cwd=ROOT)
        if done.returncode != 0:
            raise AssertionError(f"재생 실패 {name}\n{done.stdout}\n{done.stderr}")
        scored = subprocess.run(
            [sys.executable, "-X", "utf8", str(ROOT / "tools/score.py"),
             "--truth", str(ROOT / "open/dev_labels.csv"),
             "--pred", str(out / "submission.csv"),
             "--output-dir", str(root / f"{name}-score")],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
        if scored.returncode != 0:
            raise AssertionError(f"채점 실패 {name}\n{scored.stdout}\n{scored.stderr}")
        metrics = json.loads((root / f"{name}-score/metrics.json").read_text(encoding="utf-8"))
        with (out / "submission.csv").open(encoding="utf-8", newline="") as stream:
            rows = {r["id"]: r for r in csv.DictReader(stream)}
        return rows, f"{metrics['macro_f1']:.12f}", metrics

    def changed(self, name):
        head = self.rows["head"]
        return [(i, item) for i in head for item in ITEMS
                if head[i][item] != self.rows[name][i][item]]

    def test_the_pinned_baseline_matches_the_report(self):
        self.assertEqual(self.macro["head"], BASE_MACRO)

    def test_each_candidate_matches_the_report(self):
        for name in CANDIDATES:
            with self.subTest(name):
                self.assertEqual(self.macro[name], EXPECTED_MACRO[name])
                self.assertEqual(len(self.changed(name)), EXPECTED_CHANGED[name])

    def test_the_integration_is_exactly_the_sum(self):
        """두 후보가 다른 단계·다른 항목을 건드리므로 합이 그대로여야 한다."""
        base = float(self.macro["head"])
        total = base + sum(float(self.macro[n]) - base for n in ("c7", "c9"))
        self.assertAlmostEqual(total, float(self.macro["integrated"]), delta=5e-12)

    def test_the_integration_moves_the_documented_items(self):
        for item, expected in EXPECTED_ITEMS.items():
            got = self.metrics["integrated"]["items"][item]
            with self.subTest(item):
                self.assertEqual((got["tp"], got["fp"], got["fn"]), expected)

    def test_nothing_goes_down(self):
        """이 묶음의 값은 크기가 아니라 성질이다 — 내려가는 항목이 없어야 한다."""
        head = self.metrics["head"]["items"]
        for name in CANDIDATES:
            for item in ITEMS:
                with self.subTest(name=name, item=item):
                    self.assertGreaterEqual(
                        self.metrics[name]["items"][item]["tp"], head[item]["tp"],
                        "TP 를 지웠다 — 방침과 무관한 금지선")
        done = self.metrics["integrated"]["items"]
        fell = [i for i in ITEMS if done[i]["f1"] < head[i]["f1"]]
        self.assertEqual(fell, [], f"F1 이 내려간 항목이 있다: {fell}")

    def test_no_candidate_touches_another_part(self):
        for name in CANDIDATES:
            off = [c for c in self.changed(name) if c[1] in OFF_TARGET]
            self.assertEqual(off, [], (name, off))


class Shape(unittest.TestCase):
    """C9 의 게이트가 과거에 기각된 게이트와 방향이 반대인가."""

    def setUp(self):
        self.source = (ROOT / CANDIDATES["c9"]).read_text(encoding="utf-8")

    def test_it_leaves_notices_without_a_code_alone(self):
        """품번이 없으면 대상이 아니다.

        `script.py:102` 가 기각한 게이트는 "코드가 고시에 일치해야 올린다" 였고, 그러면
        품번이 없는 공고에서 v10 양성 7건 중 6건이 죽는다. 이 후보는 품번이 **있는**
        공고만 본다 — 그 조건이 사라지면 같은 사고가 난다.
        """
        self.assertIn("if not listed:", self.source)
        self.assertIn("return False", self.source)

    def test_it_borrows_the_operational_catalogue_check(self):
        """고시 대조와 금액 상한을 다시 만들지 않고 운영 함수를 쓴다."""
        self.assertIn("script.competitive_product(", self.source)
        self.assertIn("is False", self.source)

    def test_v12_is_excluded_and_says_why(self):
        """같은 78건에 v12 양성이 2건 있다. 넣으면 TP 를 지운다."""
        order = re.search(r"ITEMS = \((.+?)\)", self.source, re.S)
        self.assertIsNotNone(order)
        self.assertNotIn("v12", order[1])
        self.assertIn("v12", self.source, "왜 뺐는지가 안 적혔다")

    def test_it_never_raises_a_cell(self):
        """닫기만 한다. 0 을 1 로 만들지 않는다."""
        self.assertIn('"위반여부": 0', self.source)
        self.assertNotIn('"위반여부": 1', self.source)


if __name__ == "__main__":
    unittest.main()
