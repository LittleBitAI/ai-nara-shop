"""C5 후보 둘의 계약 — **올리기만 하고, 다른 항목을 안 건드린다.**

보고서(`reports/team-c/c5-v11-paths/CANDIDATE.md`)가 낸 수를 여기에 고정한다.
재생은 기준 커밋 `788c7df` 의 `script.py` 로만 한다 — 작업 트리 판을 쓰면 오늘 blob 이
같아도 내일 갈린다(#124 의 [P2] 가 그 자리였다).

  후보 A (scope 만)      v11 2/3/4 → 5/17/1   F1 내려간다 — 폐기
  후보 B (부재 신호)     v11 2/3/4 → 5/6/1    F1 0.363636 → 0.588235 — 합격
  둘 다 v10·v12·v13 0셀 · 대상 밖 0셀

모델을 부르지 않는다.
"""

from __future__ import annotations

import csv
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CASE = ROOT / "reports/runs/colab-1789902969401579900/dev-debug"
BASE_REV = "788c7df"
ITEMS = ("v10", "v11", "v12", "v13")
EXPECTED = {
    "head": {"v10": (4, 8, 3), "v11": (2, 3, 4), "v12": (4, 0, 2), "v13": (3, 8, 3)},
    "experiments/c5_v11_scope_gate_candidate.py":
        {"v10": (4, 8, 3), "v11": (5, 17, 1), "v12": (4, 0, 2), "v13": (3, 8, 3)},
    "experiments/c5_v11_absence_signal_candidate.py":
        {"v10": (4, 8, 3), "v11": (5, 6, 1), "v12": (4, 0, 2), "v13": (3, 8, 3)},
}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class CandidateReplays(unittest.TestCase):
    """기준 커밋 위에서 두 후보가 보고서의 수를 내는가."""

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
        with (ROOT / "open/dev_labels.csv").open(encoding="utf-8", newline="") as stream:
            cls.truth = {r["id"]: r for r in csv.DictReader(stream)}
        cls.scores = {}
        for key in EXPECTED:
            cls.scores[key] = cls.replay(root, key)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "tmp"):
            cls.tmp.cleanup()

    @classmethod
    def replay(cls, root, key):
        out = root / key.replace("/", "_").replace(".", "_")
        command = [sys.executable, "-X", "utf8", str(ROOT / "tools/replay_run.py"),
                   "--case", str(CASE), "--script", str(cls.pinned),
                   "--output-dir", str(out)]
        if key != "head":
            command += ["--candidate", str(ROOT / key)]
        done = subprocess.run(command, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", cwd=ROOT)
        if done.returncode != 0:
            raise AssertionError(f"재생 실패 {key}\n{done.stdout}\n{done.stderr}")
        with (out / "submission.csv").open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        tally = {}
        for item in ITEMS:
            tp = fp = fn = 0
            for row in rows:
                label, hit = cls.truth[row["id"]][item], row[item]
                tp += label == hit == "1"
                fp += label == "0" and hit == "1"
                fn += label == "1" and hit == "0"
            tally[item] = (tp, fp, fn)
        return tally

    def test_the_pinned_baseline_matches_the_report(self):
        self.assertEqual(self.scores["head"], EXPECTED["head"])

    def test_the_scope_only_candidate_is_wider(self):
        """후보 A 는 FN 을 줄이지만 FP 를 열넷 늘린다 — 폐기한 이유를 고정한다."""
        key = "experiments/c5_v11_scope_gate_candidate.py"
        self.assertEqual(self.scores[key], EXPECTED[key])

    def test_the_absence_signal_candidate_matches_the_report(self):
        key = "experiments/c5_v11_absence_signal_candidate.py"
        self.assertEqual(self.scores[key], EXPECTED[key])

    def test_no_candidate_loses_a_true_positive(self):
        """어느 항목이든 TP 가 줄면 폐기 조건이다."""
        for key, tally in self.scores.items():
            if key == "head":
                continue
            for item in ITEMS:
                self.assertGreaterEqual(tally[item][0], EXPECTED["head"][item][0],
                                        (key, item))

    def test_the_other_three_items_never_move(self):
        for key, tally in self.scores.items():
            for item in ("v10", "v12", "v13"):
                self.assertEqual(tally[item], EXPECTED["head"][item], (key, item))


class CandidateShape(unittest.TestCase):
    """후보가 규칙을 어떻게 쓰는가 — 정규식에 공고 문구를 더하지 않았는가."""

    def setUp(self):
        self.sources = {
            name: (ROOT / f"experiments/{name}").read_text(encoding="utf-8")
            for name in ("c5_v11_scope_gate_candidate.py",
                         "c5_v11_absence_signal_candidate.py")}

    def test_no_candidate_defines_its_own_pattern(self):
        """정규식을 새로 만들거나 어휘를 더하지 않는다 — 폐기 조건이다."""
        for name, source in self.sources.items():
            self.assertNotIn("re.compile", source, name)

    def test_the_absence_candidate_borrows_the_operational_decision(self):
        """조건을 다시 만들지 않고 운영 코드의 판단을 그대로 읽는다."""
        source = self.sources["c5_v11_absence_signal_candidate.py"]
        self.assertIn("verify_document_requirements", source)

    def test_no_candidate_ever_lowers_the_item(self):
        """**올리기만 한다.** 보고서의 무라벨 검증이 "1→0 해당 없음" 이라고 적는 근거다.

        이미 1 인 셀을 건드리지 않고, 쓰는 값은 1 하나뿐이다.
        """
        for name, source in self.sources.items():
            self.assertIn('already != 1', source, name)
            self.assertNotIn('"위반여부": 0', source, name)


if __name__ == "__main__":
    unittest.main()
