"""C6 통합 후보의 계약 — **셋을 합쳐도 TP 를 안 지우고, 순서에 안 흔들리고, diff 와 같다.**

보고서(`reports/team-c/c6-dev-macro/README.md`)가 낸 수를 여기에 고정한다.
재생은 기준 커밋 `9038380` 의 `script.py` 로만 한다 — 작업 트리 판을 쓰면 `main` 이 움직일 때
같은 보관 응답에서 다른 수가 나오고 보고서만 낡는다(#124 의 [P2] 가 그 자리였다).

이 검사가 고정하는 것 여섯.
  1. 기준선이 보고서 §1 의 Macro·C 합계를 **그대로** 낸다
  2. 후보 넷(D1·D2·E·통합)이 각각 보고서의 Macro·바뀐 셀을 낸다 — **기각한 D2 도 고정한다.**
     기각 사유가 수이므로 그 수가 움직이면 기각 판단도 다시 봐야 한다
  3. 통합이 **개별 합과 정확히 같다** — §3 의 "상호작용 0"
  4. **순서를 뒤집어도 같다** — §3 의 "순서 의존성 없음"
  5. 어떤 후보도 **TP 를 안 줄이고 C 항목 밖 14개를 안 건드린다** — 방침과 무관한 금지선
  6. **운영 diff 를 기준 코드에 적용하면 통합 후보와 셀 단위로 같다** — 문서의 diff 가
     실제로 그 수를 내는지. 이것이 틀리면 회차 하나가 통째로 버려진다

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
FOLDER = ROOT / "reports/team-c/c6-dev-macro"
REPORT = FOLDER / "README.md"
DIFF = FOLDER / "c6-integrated.diff"
BASE_REV = "9038380"

ITEMS = [f"v{i}" for i in range(1, 25)]
C_ITEMS = ("v10", "v11", "v12", "v13", "v14", "v15", "v16", "v17", "v18", "v20")
OFF_TARGET = [i for i in ITEMS if i not in C_ITEMS]

CANDIDATES = {
    "narrow": "experiments/c6_band_no_demand_narrow_candidate.py",
    "wide": "experiments/c6_band_no_demand_wide_candidate.py",
    "v16": "experiments/c6_v16_role_none_candidate.py",
    "v11": "experiments/c5_v11_absence_signal_candidate.py",
    "integrated": "experiments/c6_integrated_candidate.py",
}
BASE_MACRO = "0.685506108460"
BASE_C_TOTALS = (39, 31, 24)          # TP · FP · FN
EXPECTED_MACRO = {
    "narrow": "0.696403544358",
    "wide": "0.683762590540",          # 기각 — 기준선보다 낮다
    "v16": "0.690168113122",
    "v11": "0.693349245715",
    "integrated": "0.708908686274",
}
EXPECTED_CHANGED = {"narrow": 3, "wide": 13, "v16": 2, "v11": 7, "integrated": 12}
# 통합이 실제로 벌어야 하는 것. 세 후보의 단독 이득을 더한 값이다.
ADDENDS = ("narrow", "v16", "v11")

# §3 의 역순 판(3 → 2 → 1). 저장소에 남기지 않는다 — 이 검사만 쓰는 대조용이다.
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


S1 = _load("c6_band_no_demand_narrow_candidate",
           ROOT / "experiments/c6_band_no_demand_narrow_candidate.py")
S2 = _load("c6_v16_role_none_candidate",
           ROOT / "experiments/c6_v16_role_none_candidate.py")
S3 = _load("c5_v11_absence_signal_candidate",
           ROOT / "experiments/c5_v11_absence_signal_candidate.py")


def baseline():
    return sys.modules.get("submission") or _load("baseline_script", ROOT / "script.py")


def verify_company_size(facts, rec, max_chars):
    script = baseline()
    out, reason = S3.verify_company_size(facts, rec, max_chars)
    if (facts.get("qualification_role") == S2.UNDECIDED_ROLE
            and (out.get(S2.ITEM) or {{}}).get("위반여부") == 1):
        out = dict(out)
        out[S2.ITEM] = {{"위반여부": 0, "근거문구": None}}
    if reason == UNVERIFIED:
        return out, reason
    if facts.get("scope") == S1.CONTESTED_SCOPE and S1.demand_absent(script, rec):
        assumed, _r = script.verify_company_size(
            dict(facts, scope=S1.ASSUMED_SCOPE), rec, max_chars)
        out = dict(out)
        for item in S1.ITEMS:
            cell = assumed.get(item)
            if (cell and cell.get("위반여부") == 1
                    and (out.get(item) or {{}}).get("위반여부") != 1):
                out[item] = dict(cell)
    return out, reason
'''


class IntegratedReplay(unittest.TestCase):
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
        cls.pinned.write_bytes(cls.pinned_source())

        reverse = root / "reversed_integration.py"
        reverse.write_text(REVERSED_SOURCE.format(root=str(ROOT)),
                           encoding="utf-8", newline="\n")

        cls.rows, cls.macro, cls.metrics = {}, {}, {}
        cls.rows["head"], cls.macro["head"], cls.metrics["head"] = cls.replay(
            root, "head", None)
        for name, path in CANDIDATES.items():
            cls.rows[name], cls.macro[name], cls.metrics[name] = cls.replay(
                root, name, str(ROOT / path))
        cls.rows["reversed"], cls.macro["reversed"], _m = cls.replay(
            root, "reversed", str(reverse))

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "tmp"):
            cls.tmp.cleanup()

    @staticmethod
    def pinned_source():
        return subprocess.run(["git", "-C", str(ROOT), "show", f"{BASE_REV}:script.py"],
                              capture_output=True, check=True).stdout

    @classmethod
    def replay(cls, root, name, candidate, script=None):
        out = root / name
        command = [sys.executable, "-X", "utf8", str(ROOT / "tools/replay_run.py"),
                   "--case", str(CASE), "--script", str(script or cls.pinned),
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

    def test_the_wide_variant_stays_rejected(self):
        """넓은 판은 **기준선보다 낮다.** 그것이 기각 사유다.

        첫 측정에서는 합격으로 보였는데, 그때 후보가 `근거문구: None` 을 써서 v14·v15·v17 이
        근거 계약(#91)에 걸려 후처리에서 도로 내려갔기 때문이다. 셀을 그대로 가져오게
        고치자 결론이 뒤집혔다. 그 수를 여기 박아 둔다.
        """
        self.assertLess(float(self.macro["wide"]), float(self.macro["head"]))

    def test_the_integration_is_exactly_the_sum_of_its_parts(self):
        """§5 "상호작용 0" — 셋이 서로 다른 키를 쓰므로 합이 그대로다.

        `delta` 는 **문서에 적은 12자리를 더한 반올림**만 허용한다. 세 항을 더하면
        마지막 자리가 1 틀릴 수 있고 그것은 상호작용이 아니다. 실제 상호작용은 한 셀만
        움직여도 1e-4 단위로 나오므로 이 여유로는 안 가려진다.
        """
        base = float(self.macro["head"])
        total = base + sum(float(self.macro[n]) - base for n in ADDENDS)
        self.assertAlmostEqual(total, float(self.macro["integrated"]), delta=5e-12)

    def test_the_order_does_not_change_the_result(self):
        """§3 "순서 의존성 없음". 어느 하나가 옆 항목까지 건드리면 여기서 먼저 갈린다."""
        self.assertEqual(self.rows["integrated"], self.rows["reversed"])

    def test_no_candidate_loses_a_true_positive(self):
        """방침과 무관한 금지선. C 항목 어디서도 TP 가 줄면 안 된다."""
        for name in CANDIDATES:
            for item in C_ITEMS:
                with self.subTest(name=name, item=item):
                    self.assertGreaterEqual(self.metrics[name]["items"][item]["tp"],
                                            self.metrics["head"]["items"][item]["tp"])

    def test_no_candidate_touches_another_part(self):
        """C 항목 밖 14개는 **정확히 0셀**이어야 한다. B·D 의 항목이다."""
        for name in CANDIDATES:
            off = [c for c in self.changed(name) if c[1] in OFF_TARGET]
            self.assertEqual(off, [], (name, off))

    def test_the_operational_diff_reproduces_the_candidate(self):
        """**문서의 diff 가 실제로 그 수를 내는가.** 틀리면 회차 하나가 통째로 버려진다."""
        if shutil.which("patch") is None:
            raise unittest.SkipTest("patch 가 없다")
        work = Path(self.tmp.name) / "patched"
        work.mkdir()
        (work / "script.py").write_bytes(self.pinned_source())
        applied = subprocess.run(
            ["patch", "-p1", "--binary", "-i", str(DIFF)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=work)
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        rows, macro, _m = self.replay(Path(self.tmp.name), "diff-applied", None,
                                      script=work / "script.py")
        self.assertEqual(rows, self.rows["integrated"],
                         "diff 를 적용한 운영 코드가 통합 후보와 다른 CSV 를 낸다")
        self.assertEqual(macro, EXPECTED_MACRO["integrated"])


class IntegrationShape(unittest.TestCase):
    """통합이 무엇으로 만들어졌는가."""

    def setUp(self):
        self.source = (ROOT / CANDIDATES["integrated"]).read_text(encoding="utf-8")
        self.report = REPORT.read_text(encoding="utf-8")

    def test_it_does_not_define_its_own_pattern(self):
        """정규식을 새로 만들거나 공고 문구를 박지 않는다 — 폐기 조건이다."""
        for path in CANDIDATES.values():
            self.assertNotIn("re.compile", (ROOT / path).read_text(encoding="utf-8"), path)

    def test_it_reuses_the_three_candidates(self):
        """규칙을 옮겨 적으면 원본이 바뀔 때 조용히 갈린다. 불러 쓴다."""
        for key in ADDENDS:
            self.assertIn(Path(CANDIDATES[key]).name, self.source)

    def test_the_fixed_order_is_written_down(self):
        """순서를 코드에도 적는다 — 문서만 있으면 따로 논다."""
        order = re.search(r"ORDER = \((.+?)\)", self.source, re.S)
        self.assertIsNotNone(order)
        positions = [order[1].index(f"STEP{n}") for n in (1, 2, 3)]
        self.assertEqual(positions, sorted(positions))

    def test_the_dev_label_based_rule_is_marked_in_every_place(self):
        """**dev 라벨 기반임을 보고서·후보·운영 diff 가 모두 적는가.**

        방침이 다시 바뀔 때 무엇을 되돌릴지 알아야 한다. 한 군데만 적으면
        다른 곳을 읽은 사람이 그것을 조문 기반 규칙으로 읽는다.
        """
        for text in (self.report, self.source,
                     (ROOT / CANDIDATES["v16"]).read_text(encoding="utf-8"),
                     DIFF.read_text(encoding="utf-8")):
            self.assertIn("dev 라벨 기반", text)

    def test_the_report_records_no_extra_model_calls(self):
        """추가 호출 0 이라야 서버 시간이 안 늘어난다. 그 주장을 문서가 적는가."""
        self.assertIn("추가 호출 0", self.source)
        self.assertIn("추가 호출 0", self.report)


class RunRequest(unittest.TestCase):
    """실행 요청서가 **노트북 소스·보고서와 어긋나지 않는가.**

    요청서는 사람이 보고 그대로 따라 하는 문서라, 셀 번호 하나가 틀리면 회차가
    통째로 버려진다. C5 에서 실제로 그 일이 있었다.
    """

    NOTEBOOK = ROOT / "notebooks/colab-baseline.ipynb"
    REQUEST = FOLDER / "RUN-REQUEST.md"
    # 요청서 §2 가 가리키는 셀과 그 셀에 있어야 하는 이름.
    CELLS = {1: ("SOURCE_MODE", "REPO_REF"), 18: ("RUN_DIAGNOSTIC", "DIAGNOSTIC_ARGS")}
    COMMAND = 'run_case("dev-debug", WORK / "open/dev.jsonl", args=DIAGNOSTIC_ARGS)'

    @classmethod
    def setUpClass(cls):
        if not cls.NOTEBOOK.is_file():
            raise unittest.SkipTest(f"{cls.NOTEBOOK} 가 없다")
        data = json.loads(cls.NOTEBOOK.read_text(encoding="utf-8"))
        cls.cells = ["".join(cell["source"]) for cell in data["cells"]]
        cls.request = cls.REQUEST.read_text(encoding="utf-8")
        cls.report = REPORT.read_text(encoding="utf-8")

    def test_the_named_cells_hold_the_named_switches(self):
        for index, names in self.CELLS.items():
            self.assertLess(index, len(self.cells), f"셀 [{index}] 가 없다")
            for name in names:
                self.assertIn(name, self.cells[index], f"셀 [{index}] 에 {name} 이 없다")
            self.assertIn(f"`[{index}]`", self.request,
                          f"요청서가 셀 [{index}] 을 안 가리킨다")

    def test_the_quoted_command_exists_in_the_notebook(self):
        self.assertIn(self.COMMAND, self.cells[18])
        self.assertIn(self.COMMAND, self.request)

    def test_the_diagnostic_default_is_still_true(self):
        """요청서는 "기본값이 이미 맞다" 고 적는다. 기본이 바뀌면 그 문장이 거짓이 된다."""
        self.assertRegex(self.cells[18], r"RUN_DIAGNOSTIC\s*=\s*True")

    def test_no_other_cell_defines_the_repo_ref(self):
        defining = [i for i, s in enumerate(self.cells)
                    if re.search(r"^REPO_REF\s*=", s, re.MULTILINE)]
        self.assertEqual(defining, [1], f"REPO_REF 를 정의하는 셀이 여럿이다: {defining}")

    def test_the_pass_marks_match_the_measured_numbers(self):
        """합격 기준의 수치가 보고서의 실측과 같은가."""
        for number in ("0.708908686274", "5/6/1", "4/1/2", "3/3/4", "9038380"):
            with self.subTest(number):
                self.assertIn(number, self.request)
                self.assertIn(number, self.report)

    def test_the_off_target_rule_is_exactly_zero_not_the_churn_range(self):
        """D1 은 **정확히 0**, churn 범위는 D2 에만. 섞으면 대상 밖 45셀이 승인된다."""
        lines = self.request.splitlines()
        d1 = [line for line in lines if line.startswith("| **D1** |")]
        self.assertTrue(d1, "D1 줄이 없다")
        rules = [line for line in d1 if "off_focus" in line or "대상 밖" in line]
        self.assertTrue(rules, "D1 의 규칙을 적는 줄이 없다")
        for line in rules:
            self.assertIn("정확히 0", line)
            self.assertNotIn("17~45", line, "D1 에 churn 범위가 섞였다")
        d2 = [line for line in lines if line.startswith("| **D2** |")]
        self.assertTrue(any("17~45" in line for line in d2), "D2 에 churn 범위가 없다")
        self.assertIn("reproducibility.md", self.request, "churn 범위의 출처가 없다")

    def test_the_criteria_ask_whether_it_moved_at_all(self):
        """무효과 후보가 절대값 기준만으로 통과하던 자리 — 기준 Z 가 막는다."""
        self.assertIn("| **Z** |", self.request, "기준 Z 가 없다")
        self.assertIn("가설 기각", self.request)

    def test_the_pair_comparison_covers_exactly_the_three_keys(self):
        """`--items` 는 후보가 쓰는 셋이어야 나머지 21항목을 D1 이 본다."""
        self.assertIn("--items v11,v16,v18", self.request)
        self.assertIn("21항목", self.request, "왜 셋인지가 안 적혔다")

    def test_the_comparison_json_shape_is_described_correctly(self):
        """`items` 는 리스트다. 딕셔너리처럼 적으면 실행자가 막힌다."""
        self.assertIn("딕셔너리가 아니라", self.request)
        self.assertIn("changed_cells_off_focus", self.request)
        self.assertNotIn("items.v11", self.request)

    def test_the_run_commit_placeholder_is_visible_until_filled(self):
        """안 채운 채 돌리면 `main` 으로 도는 사고가 난다."""
        if "<RUN_COMMIT>" in self.request:
            self.assertIn("push 뒤 채운다", self.request,
                          "자리표시자가 남았는데 채워야 한다는 말이 없다")
        else:
            self.assertRegex(self.request, r"\b[0-9a-f]{40}\b",
                             "자리표시자를 지웠으면 40자리 SHA 가 있어야 한다")


if __name__ == "__main__":
    unittest.main()
