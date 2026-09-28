"""C6 스택 후보의 계약 — **올리기만 하고, 순서에 안 흔들리고, 남의 항목을 안 건드린다.**

보고서(`reports/team-c/c6-dev-macro/README.md`)가 낸 수를 여기에 고정한다.
재생은 기준 커밋 `c68eb00` 의 `script.py` 로만 한다 — 작업 트리 판을 쓰면 `main` 이 움직일 때
같은 보관 응답에서 다른 수가 나오고 보고서만 낡는다(#124 의 [P2] 가 그 자리였다).

이 검사가 고정하는 것 넷.
  1. 기준선이 보고서 §1 의 Macro·C 합계를 **그대로** 낸다
  2. 스택이 **v11 단독과 셀 단위로 같다** — §3 의 "상호작용 없음"
  3. **순서를 뒤집어도 같다** — §3 의 "순서 의존성 없음". 지금 같다는 사실을 박아 두면
     둘 중 하나가 상대 항목까지 건드리도록 넓어질 때 이 검사가 먼저 운다
  4. 어떤 후보도 **TP 를 안 줄이고 C 항목 밖 14개를 안 건드린다** — 방침과 무관한 금지선

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
CASE = ROOT / "reports/runs/colab-1790235508743452453/dev-debug"
BASE_REV = "c68eb00"

ITEMS = [f"v{i}" for i in range(1, 25)]
C_ITEMS = ("v10", "v11", "v12", "v13", "v14", "v15", "v16", "v17", "v18", "v20")
OFF_TARGET = [i for i in ITEMS if i not in C_ITEMS]

CANDIDATES = {
    "v13": "experiments/c_v13_merge_candidate.py",
    "v11": "experiments/c5_v11_absence_signal_candidate.py",
    "stack": "experiments/c_dev_macro_stack_candidate.py",
}
# 보고서 §1·§2·§3 의 실측. 하나라도 어긋나면 문서와 코드 중 하나가 낡은 것이다.
BASE_MACRO = "0.735764126941"
BASE_C_TOTALS = (42, 25, 21)          # TP · FP · FN
EXPECTED_MACRO = {"v13": "0.735764126941", "v11": "0.736464407053",
                  "stack": "0.736464407053"}
EXPECTED_CHANGED = {"v13": 0, "v11": 3, "stack": 3}
EXPECTED_V11 = {"v13": (4, 4, 2), "v11": (5, 6, 1), "stack": (5, 6, 1)}

# §3 의 역순 판. 저장소에 남기지 않는다 — 이 검사만 쓰는 대조용이다.
REVERSED_SOURCE = '''
import importlib.util
import sys
from pathlib import Path

ROOT = Path(r"{root}")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
UNVERIFIED = "unverified_scope"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


STEP1 = _load("c_v13_merge_candidate", ROOT / "experiments/c_v13_merge_candidate.py")
STEP2 = _load("c5_v11_absence_signal_candidate",
              ROOT / "experiments/c5_v11_absence_signal_candidate.py")


def verify_company_size(facts, rec, max_chars):
    out, reason = STEP2.verify_company_size(facts, rec, max_chars)
    if (reason != UNVERIFIED and STEP1.ITEM not in out
            and facts.get("scope") == STEP1.CONTRADICTING_SCOPE):
        out = dict(out)
        out[STEP1.ITEM] = {{"위반여부": 0, "근거문구": None}}
    return out, reason
'''


class StackReplay(unittest.TestCase):
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

        reverse = root / "reversed_stack.py"
        reverse.write_text(REVERSED_SOURCE.format(root=str(ROOT)),
                           encoding="utf-8", newline="\n")

        cls.rows, cls.macro, cls.metrics = {}, {}, {}
        cls.rows["head"], cls.macro["head"], cls.metrics["head"] = cls.replay(
            root, "head", None)
        for name, path in CANDIDATES.items():
            cls.rows[name], cls.macro[name], cls.metrics[name] = cls.replay(
                root, name, str(ROOT / path))
        cls.rows["reversed"], cls.macro["reversed"], cls.metrics["reversed"] = cls.replay(
            root, "reversed", str(reverse))

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
        totals = tuple(sum(self.metrics["head"]["items"][i][k] for i in C_ITEMS)
                       for k in ("tp", "fp", "fn"))
        self.assertEqual(totals, BASE_C_TOTALS)

    def test_each_candidate_matches_the_report(self):
        for name in CANDIDATES:
            with self.subTest(name):
                self.assertEqual(self.macro[name], EXPECTED_MACRO[name])
                self.assertEqual(len(self.changed(name)), EXPECTED_CHANGED[name])
                item = self.metrics[name]["items"]["v11"]
                self.assertEqual((item["tp"], item["fp"], item["fn"]), EXPECTED_V11[name])

    def test_the_stack_equals_the_v11_candidate_alone(self):
        """§3 "상호작용 없음" — v13 후보가 이 기준에서 0셀이라 합이 그대로다."""
        self.assertEqual(self.rows["stack"], self.rows["v11"])

    def test_the_order_does_not_change_the_result(self):
        """§3 "순서 의존성 없음" — 쓰는 키가 달라서 지금은 같다.

        둘 중 하나가 상대 항목까지 건드리도록 넓어지면 여기서 먼저 갈린다.
        """
        self.assertEqual(self.rows["stack"], self.rows["reversed"])

    def test_no_candidate_loses_a_true_positive(self):
        """방침과 무관한 금지선. **어느 한 항목에서도** TP 가 줄면 안 된다.

        **합계로 보면 손실이 숨는다** — 한 항목이 얻고 다른 항목이 잃으면
        `C 합계 39 → 39` 로 아무 일도 없어 보인다. 항목마다 따로 보고,
        C 항목 열 개가 아니라 **24개 전부**를 본다.
        """
        for name in CANDIDATES:
            for item in ITEMS:
                with self.subTest(name=name, item=item):
                    self.assertGreaterEqual(self.metrics[name]["items"][item]["tp"],
                                            self.metrics["head"]["items"][item]["tp"])

    def test_no_candidate_touches_another_part(self):
        """C 항목 밖 14개는 **정확히 0셀**이어야 한다. B·D 의 항목이다."""
        for name in CANDIDATES:
            off = [c for c in self.changed(name) if c[1] in OFF_TARGET]
            self.assertEqual(off, [], (name, off))


class StackShape(unittest.TestCase):
    """스택이 무엇으로 만들어졌는가."""

    def setUp(self):
        self.source = (ROOT / CANDIDATES["stack"]).read_text(encoding="utf-8")

    def test_it_does_not_define_its_own_pattern(self):
        """정규식을 새로 만들거나 공고 문구를 박지 않는다 — 폐기 조건이다."""
        self.assertNotIn("re.compile", self.source)

    def test_it_reuses_both_candidates_instead_of_copying_them(self):
        """규칙을 옮겨 적으면 원본이 바뀔 때 조용히 갈린다. 불러 쓴다."""
        for path in (CANDIDATES["v13"], CANDIDATES["v11"]):
            self.assertIn(Path(path).name, self.source)
        self.assertIn("STEP1.verify_company_size", self.source)

    def test_it_never_lowers_the_item_it_raises(self):
        """2단계는 **올리기만 한다.** 이미 1 인 셀을 건드리지 않는다."""
        self.assertIn("already != 1", self.source)

    def test_the_fixed_order_is_written_down(self):
        """순서를 코드에도 적는다 — 문서만 있으면 따로 논다."""
        self.assertIn("ORDER", self.source)
        order = re.search(r"ORDER = \((.+?)\)", self.source, re.S)
        self.assertIsNotNone(order)
        self.assertLess(order[1].index("STEP1"), order[1].index("STEP2"))


if __name__ == "__main__":
    unittest.main()
