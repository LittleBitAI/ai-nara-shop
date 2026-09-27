"""C11 과 C9+C11 의 계약 — **대가 없이 v10 오탐 둘을 닫는다.**

이 묶음의 값은 크기가 아니라 성질이다. 0.0034 는 회차 변동폭(0.007287,
`reports/team-c/c-variance/VERDICT.md`)보다 작아서 **회차 두 번으로는 못 가른다.**
그래서 같은 원응답 위 재생으로만 서고, 그 재생이 결정적이려면 계약이 단단해야 한다.

고정하는 것 일곱.
  1. 기준선이 보고서의 Macro 를 그대로 낸다
  2. C11 · 통합이 각각 보고서의 수를 낸다
  3. **여섯 통과 전부 같은 이득**을 낸다 — 이 후보의 값은 재현성이다
  4. **F1 이 내려가는 항목이 없고 TP 를 하나도 안 지운다**
  5. 닫기만 한다 — 0 을 1 로 만들지 않는다
  6. 정규식이 **법률명에 묶여 있다** — 안 묶으면 딴 법의 제7조가 걸린다
  7. C9 와 C11 이 **서로 다른 공고**에 닿는다 — 두 축이 겹치면 통합이 의미가 없다

모델을 부르지 않는다.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "reports/runs/colab-1790445336782946136"
PASSES = [f"var-{k:02d}" for k in range(1, 7)]
BASE_REV = "772ca12"
ITEMS = [f"v{i}" for i in range(1, 25)]
C_ITEMS = ("v10", "v11", "v12", "v13", "v14", "v15", "v16", "v17", "v18", "v20")
OFF_TARGET = [i for i in ITEMS if i not in C_ITEMS]

CANDIDATES = {
    "c9": "experiments/c9_catalogue_exclusion_candidate.py",
    "c11": "experiments/c11_competition_exception_candidate.py",
    "integrated": "experiments/c11_integrated_candidate.py",
}
# `var-01` 기준. 통과마다 기준선이 달라도 **이득**은 같다 — test_the_gain_is_the_same…
BASE_MACRO = "0.828051931728"
EXPECTED_MACRO = {
    "c9": "0.829639233316",
    "c11": "0.829639233316",
    "integrated": "0.831470735147",
}
EXPECTED_CELLS = {
    "c9": [("PPS-DEV-128", "v10")],
    "c11": [("PPS-DEV-23", "v10")],
    "integrated": [("PPS-DEV-128", "v10"), ("PPS-DEV-23", "v10")],
}
GAIN = "0.003418803419"          # 통합의 이득. 여섯 통과에서 같아야 한다
EXPECTED_V10 = (4, 2, 3)         # 통합 뒤 v10 의 TP/FP/FN


def replay(root, case, name, candidate, pinned):
    out = root / f"{case}-{name}"
    command = [sys.executable, "-X", "utf8", str(ROOT / "tools/replay_run.py"),
               "--case", str(RUN / case), "--script", str(pinned),
               "--output-dir", str(out)]
    if candidate:
        command += ["--candidate", str(ROOT / candidate)]
    done = subprocess.run(command, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=ROOT)
    if done.returncode != 0:
        raise AssertionError(f"재생 실패 {case}/{name}\n{done.stdout}\n{done.stderr}")
    scored = subprocess.run(
        [sys.executable, "-X", "utf8", str(ROOT / "tools/score.py"),
         "--truth", str(ROOT / "open/dev_labels.csv"),
         "--pred", str(out / "submission.csv"),
         "--output-dir", str(root / f"{case}-{name}-score")],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
    if scored.returncode != 0:
        raise AssertionError(f"채점 실패 {case}/{name}\n{scored.stdout}\n{scored.stderr}")
    metrics = json.loads((root / f"{case}-{name}-score/metrics.json").read_text(encoding="utf-8"))
    with (out / "submission.csv").open(encoding="utf-8", newline="") as stream:
        rows = {r["id"]: r for r in csv.DictReader(stream)}
    return rows, metrics


class Replay(unittest.TestCase):
    """`var-01` 위에서 보고서의 수가 나오는가."""

    @classmethod
    def setUpClass(cls):
        if shutil.which("git") is None:
            raise unittest.SkipTest("git 이 없다")
        if not (RUN / "var-01/diagnostics.jsonl").is_file():
            raise unittest.SkipTest(f"{RUN}/var-01 이 없다")
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.pinned = root / "script.py"
        cls.pinned.write_bytes(subprocess.run(
            ["git", "-C", str(ROOT), "show", f"{BASE_REV}:script.py"],
            capture_output=True, check=True).stdout)
        cls.rows, cls.metrics = {}, {}
        cls.rows["head"], cls.metrics["head"] = replay(root, "var-01", "head", None, cls.pinned)
        for name, path in CANDIDATES.items():
            cls.rows[name], cls.metrics[name] = replay(root, "var-01", name, path, cls.pinned)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "tmp"):
            cls.tmp.cleanup()

    def macro(self, name):
        return f"{self.metrics[name]['macro_f1']:.12f}"

    def changed(self, name):
        head = self.rows["head"]
        return sorted((i, item) for i in head for item in ITEMS
                      if head[i][item] != self.rows[name][i][item])

    def test_the_pinned_baseline_matches_the_report(self):
        self.assertEqual(self.macro("head"), BASE_MACRO)

    def test_each_candidate_matches_the_report(self):
        for name in CANDIDATES:
            with self.subTest(name):
                self.assertEqual(self.macro(name), EXPECTED_MACRO[name])
                self.assertEqual(self.changed(name), EXPECTED_CELLS[name])

    def test_the_two_axes_touch_different_notices(self):
        """겹치면 통합이 의미가 없다. `23` 은 고시에 있는 품번이라 C9 가 못 잡는다."""
        c9 = {cell[0] for cell in self.changed("c9")}
        c11 = {cell[0] for cell in self.changed("c11")}
        self.assertEqual(c9 & c11, set(), "두 축이 같은 공고를 건드린다")
        self.assertEqual(c9 | c11, {cell[0] for cell in self.changed("integrated")})

    def test_the_integration_moves_v10_only(self):
        got = self.metrics["integrated"]["items"]["v10"]
        self.assertEqual((got["tp"], got["fp"], got["fn"]), EXPECTED_V10)
        self.assertEqual({cell[1] for cell in self.changed("integrated")}, {"v10"})

    def test_nothing_goes_down(self):
        """방침과 무관한 금지선 — TP 를 지우지 않는다. 내려가는 항목도 없다."""
        head = self.metrics["head"]["items"]
        for name in CANDIDATES:
            for item in ITEMS:
                with self.subTest(name=name, item=item):
                    self.assertGreaterEqual(
                        self.metrics[name]["items"][item]["tp"], head[item]["tp"],
                        "TP 를 지웠다")
                    self.assertGreaterEqual(
                        self.metrics[name]["items"][item]["f1"], head[item]["f1"],
                        "F1 이 내려갔다")

    def test_no_candidate_touches_another_part(self):
        for name in CANDIDATES:
            off = [c for c in self.changed(name) if c[1] in OFF_TARGET]
            self.assertEqual(off, [], (name, off))


class Shape(unittest.TestCase):
    """후보가 무엇을 안 하기로 했는지. 모델도 재생기도 안 부른다."""

    def setUp(self):
        self.source = (ROOT / CANDIDATES["c11"]).read_text(encoding="utf-8")
        # `experiments` 는 패키지가 아니다. 경로로 집는다.
        spec = importlib.util.spec_from_file_location(
            "c11_under_test", ROOT / CANDIDATES["c11"])
        self.c11 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.c11)

    def test_it_never_raises_a_cell(self):
        """닫기만 한다. 0 을 1 로 만들지 않는다."""
        self.assertIn('"위반여부": 0', self.source)
        self.assertNotIn('"위반여부": 1', self.source)

    def test_the_pattern_is_anchored_to_the_statute_name(self):
        """법률명에 안 묶으면 딴 법의 제7조가 걸린다.

        `PPS-DEV-103` 은 「공공디자인의 진흥에 관한 법률」 시행령 제7조 제1항을 인용한다.
        조 번호만 보면 그 공고가 걸리고, 그 공고의 v10~v13 은 전부 라벨 0 이라 닫아도
        점수는 안 변하지만 **규칙이 딴 법을 읽는다**는 것이 문제다.
        """
        self.assertIn("중소기업제품", self.c11.EXCEPTION.pattern)
        self.assertIn("판로지원", self.c11.EXCEPTION.pattern)
        other_law = "「공공디자인의 진흥에 관한 법률」제20조 제1항, 같은 법 시행령 제7조 제1항"
        self.assertIsNone(self.c11.EXCEPTION.search(other_law), "딴 법의 제7조가 걸린다")
        ours = "｢중소기업제품 구매촉진 및 판로지원에 관한 법률 시행령｣ 제7조제1항제4호"
        self.assertIsNotNone(self.c11.EXCEPTION.search(ours), "우리 조문이 안 걸린다")
        short = "「판로지원법 시행령」 제7조제1항제4호"
        self.assertIsNotNone(self.c11.EXCEPTION.search(short), "줄여 쓴 법률명이 안 걸린다")

    def test_a_citation_alone_is_not_an_exception(self):
        """인용만 하거나 부정하면 예외 적용이 아니다 — #152 2차 리뷰 P1 의 탐침."""
        cite = "「판로지원법 시행령」 제7조제1항"
        cases = {
            f"{cite}의 예외에 해당하지 않아 중소기업자간 경쟁입찰로 진행합니다.": False,
            f"{cite}을 적용하지 아니한다.": False,
            f"{cite}의 예외는 적용하지 못합니다. 중소기업자간 경쟁입찰로 진행합니다.": False,
            f"{cite}의 예외 적용 불가.": False,
            f"{cite}의 예외 적용을 배제한다.": False,
            f"{cite}의 예외를 안 적용합니다. 중소기업자간 경쟁입찰로 진행합니다.": False,
            f"{cite}의 예외에 해당하는지 검토하였다.": False,
            f"{cite}의 예외 사유를 참고한다.": False,
            f"{cite}의 예외에 해당함에도 제4호를 안 적용한다.": False,
            f"{cite}의 예외에 해당함에도 제4호를 적용하지 못한다.": False,
            f"{cite}의 예외 적용 여부: 미해당.": False,
            f"{cite}의 예외 적용 X.": False,
            f"{cite}의 예외에 해당함에도 제4호 미적용.": False,
            f"{cite}에 따라 경쟁입찰의 예외를 적용 3. 낙찰자 결정방법": True,
            f"{cite}에 따라 중소기업자간 경쟁입찰 예외 적용 <예외사유>": True,
            f"{cite}제4호에 따라 경쟁입찰 외의 방법으로 추진함.": True,
            f"{cite} 제4호는 이 입찰과 무관하다.": False,
            f"{cite}제4호에 따라 중소기업자간 경쟁입찰의 예외에 해당합니다.": True,
            f"{cite}제4호를 적용합니다.": True,
            f"{cite}제3호에 따라 경쟁입찰의 예외를 적용합니다 ※ 공동수급을 허용하지 않습니다.": True,
        }
        for text, expected in cases.items():
            with self.subTest(text):
                rec = {"docs": [{"text": text}]}
                self.assertIs(self.c11.competition_exception(rec), expected)

    def test_it_closes_only_v10_and_v11(self):
        """v12 는 일반제품, v13 은 제7조의2 특례라 예외가 근거가 안 된다."""
        self.assertEqual(self.c11.ITEMS, ("v10", "v11"))

    def test_it_reads_the_documents_not_the_prompt_window(self):
        """제2항이 요구한 기재는 16,000자 예산 뒤쪽에 있을 수 있다."""
        self.assertIn('rec.get("docs")', self.source)
        self.assertNotIn("build_context", self.source)


class EverySixPasses(unittest.TestCase):
    """이 후보의 값은 재현성이다 — 여섯 통과에서 같은 이득이어야 한다."""

    @classmethod
    def setUpClass(cls):
        if shutil.which("git") is None:
            raise unittest.SkipTest("git 이 없다")
        missing = [p for p in PASSES if not (RUN / p / "diagnostics.jsonl").is_file()]
        if missing:
            raise unittest.SkipTest(f"통과가 없다: {missing}")
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.pinned = root / "script.py"
        cls.pinned.write_bytes(subprocess.run(
            ["git", "-C", str(ROOT), "show", f"{BASE_REV}:script.py"],
            capture_output=True, check=True).stdout)
        cls.gains, cls.cells = {}, {}
        for case in PASSES:
            before_rows, before = replay(root, case, "head", None, cls.pinned)
            after_rows, after = replay(root, case, "integrated",
                                       CANDIDATES["integrated"], cls.pinned)
            cls.gains[case] = after["macro_f1"] - before["macro_f1"]
            cls.cells[case] = sorted((i, item) for i in before_rows for item in ITEMS
                                     if before_rows[i][item] != after_rows[i][item])

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "tmp"):
            cls.tmp.cleanup()

    def test_the_gain_is_the_same_in_every_pass(self):
        for case in PASSES:
            with self.subTest(case):
                self.assertEqual(f"{self.gains[case]:.12f}", GAIN)

    def test_the_same_two_cells_move_in_every_pass(self):
        """이득이 같아도 다른 셀이 움직였다면 우연이다. 공고까지 같아야 한다."""
        for case in PASSES:
            with self.subTest(case):
                self.assertEqual(self.cells[case], EXPECTED_CELLS["integrated"])


if __name__ == "__main__":
    unittest.main()
