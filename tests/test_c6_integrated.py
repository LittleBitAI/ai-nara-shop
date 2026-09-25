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
        """방침과 무관한 금지선. **어느 한 항목에서도** TP 가 줄면 안 된다.

        리뷰 [P1] — **합계로 보면 손실이 숨는다.** 한 항목이 TP 를 얻고 다른 항목이
        잃으면 `C 합계 39 → 39` 로 아무 일도 없어 보이는데, 금지선이 막으려는 것이
        바로 그 손실이다. 그래서 항목마다 따로 본다.

        C 항목 열 개가 아니라 **24개 전부**를 본다 — 대상 밖 셀이 움직이는 사고가
        D1(0셀)과 이 검사 양쪽에 걸리게 한다.
        """
        for name in CANDIDATES:
            for item in ITEMS:
                with self.subTest(name=name, item=item):
                    self.assertGreaterEqual(self.metrics[name]["items"][item]["tp"],
                                            self.metrics["head"]["items"][item]["tp"])

    def test_the_integration_keeps_every_item_tp(self):
        """통합의 항목별 TP 가 보고서 §8 의 표와 같은가 — 줄어든 항목이 0개인가."""
        head, done = self.metrics["head"]["items"], self.metrics["integrated"]["items"]
        lost = [i for i in ITEMS if done[i]["tp"] < head[i]["tp"]]
        self.assertEqual(lost, [], f"TP 를 잃은 항목이 있다: {lost}")
        gained = {i: done[i]["tp"] - head[i]["tp"]
                  for i in ITEMS if done[i]["tp"] != head[i]["tp"]}
        self.assertEqual(gained, {"v11": 3, "v18": 2},
                         "항목별 TP 변화가 보고서와 다르다")

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

    def request_section(self, start, end):
        """요청서의 한 절만 잘라 낸다. 규칙을 적는 줄과 옆 절의 문장을 안 섞으려고."""
        head = self.request.index(start)
        tail = self.request.index(end, head + len(start))
        return self.request[head:tail]

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

    def test_the_patch_command_reads_the_diff_from_a_ref_not_the_work_tree(self):
        """리뷰 [P1] — 회차 브랜치 명령이 패치 파일을 잃던 자리.

        `c6-integrated.diff` 는 기준 커밋에 **없다.** `git switch --detach <기준>` 하면
        `reports/team-c/c6-dev-macro/` 가 작업 트리에서 통째로 사라지고, 그 경로를
        `patch -i` 로 가리키면 입력 파일이 없어 죽는다. 그래서 `git show <ref>:<path>` 로
        읽어야 한다.
        """
        base = self.request_section("### 1-2.", "## 2.")
        self.assertIn("git show feat/c-dev-macro:"
                      "reports/team-c/c6-dev-macro/c6-integrated.diff | patch", base)
        self.assertNotRegex(
            base, r"patch\s+-p1\s+--binary\s+-i\s+reports/",
            "작업 트리 경로를 patch 의 입력으로 쓰면 detach 뒤에 그 파일이 없다")

    def test_the_return_step_names_the_branch(self):
        """리뷰 [P2] — `git switch -` 가 작업 브랜치로 못 돌아가던 자리.

        `-` 는 *직전에 있던 곳*으로 가는데 `switch -c` 앞의 직전은 **분리된 HEAD** 다.
        실제로 `fatal: a branch is expected, got commit …` 로 죽고, 그대로 회차
        브랜치에 남는다. 모르고 이어가면 회차 브랜치 위에 작업 커밋이 쌓인다.
        """
        block = self.request_section("### 1-2.", "## 2.")
        commands = [line.strip() for line in block.splitlines()
                    if line.strip().startswith("git switch")]
        self.assertTrue(commands, "브랜치 명령이 없다")
        self.assertNotIn("git switch -", [c.split("#")[0].strip() for c in commands],
                         "`git switch -` 는 분리된 HEAD 에서 돌아오지 못한다")
        self.assertTrue(any(c.startswith("git switch feat/c-dev-macro") for c in commands),
                        "돌아갈 브랜치를 이름으로 안 적었다")
        self.assertIn("a branch is expected", block,
                      "왜 `-` 를 못 쓰는지 실제 메시지가 없다")

    def test_the_diff_really_is_absent_from_the_base_commit(self):
        """위 검사의 전제가 아직 참인가 — 기준 커밋에 그 파일이 없는가.

        언젠가 diff 가 `main` 에 들어가면 전제가 바뀐다. 그때는 이 검사가 먼저 울어서
        §1-2 의 설명을 다시 보게 한다.
        """
        if shutil.which("git") is None:
            raise unittest.SkipTest("git 이 없다")
        found = subprocess.run(
            ["git", "-C", str(ROOT), "cat-file", "-e",
             f"{BASE_REV}:reports/team-c/c6-dev-macro/c6-integrated.diff"],
            capture_output=True)
        self.assertNotEqual(found.returncode, 0,
                            "기준 커밋에 diff 가 생겼다 — §1-2 의 설명을 다시 보라")

    def test_every_pass_mark_is_a_difference_not_a_fixed_number(self):
        """리뷰 [P1] — 새 회차의 TP 손실을 고정 숫자로 재던 자리.

        새 회차는 다른 모델 출력이라 **기준선의 TP 자체가 다르다.** 금지선 E 를
        `≥ 44` 같은 절대값으로 적으면 기준선이 높은 회차에서 TP 손실을 통과시킨다.
        """
        table = self.request_section("## 4.", "### 4-2.")
        rows = {line.split("|")[1].strip(): line
                for line in table.splitlines() if line.startswith("| ")}
        self.assertIn("E", rows, "금지선 E 가 없다")
        self.assertIn("감소", rows["E"])
        self.assertIn("정확히 0", rows["E"])
        self.assertNotIn("44", rows["E"], "E 를 고정 숫자로 적었다")
        self.assertIn("차이", table, "차이로 읽으라는 말이 없다")
        for key in ("A", "B", "C", "D", "F"):
            with self.subTest(key):
                self.assertRegex(rows[key], r"감소|증가",
                                 f"{key} 가 절대값으로 적혔다")

    def test_no_movement_has_one_verdict_across_the_document(self):
        """리뷰 [P2]·[P1] — "발동 없음"의 판정이 문서 안에서 충돌하던 자리.

        세 층으로 갈린다. **변경 기회 0 도, 실제 변경 0 도 판정 보류**이고,
        **기각은 Z3 에서만** 나온다 — 셀이 실제로 바뀌었는데 F1 이 안 오를 때.
        기준표·감사 절차·예상 실패가 같은 말을 해야 한다.
        """
        lines = self.request.splitlines()
        for key in ("Z1", "Z2", "Z3"):
            self.assertIn(f"| {key} |", self.request, f"기준 {key} 가 없다")
        for key in ("Z1", "Z2"):
            for line in [x for x in lines if x.startswith(f"| {key} |")]:
                with self.subTest(key):
                    self.assertIn("판정 보류", line)
                    self.assertNotIn("가설 기각", line,
                                     f"{key} 의 0 을 기각으로 적었다")
        for line in [x for x in lines if x.startswith("| Z3 |")]:
            self.assertIn("가설 기각", line)
        # 예상 실패표가 같은 구분을 쓰는가 — 옛 판은 여기서 "기각이 아니다" 라고만 했다.
        failures = self.request_section("## 6.", "## 7.")
        self.assertIn("판정 보류", failures)
        self.assertIn("§4-2", failures, "예상 실패표가 판정 규칙을 안 가리킨다")

    def test_the_trigger_criterion_reads_opportunity_not_gate_count(self):
        """리뷰 [P1] — 조건 충족 수를 변경 기회로 읽어 Z2 가 잘못 기각하던 자리.

        v18 규칙은 게이트를 **38건** 통과하지만 결정표가 v18 을 세우는 것은 **3건**뿐이다.
        나머지 35건은 `general` 로 다시 밟아도 금액·자격·관측에서 막힌다. Z1 이 38 을
        보면, 기회가 0 인 회차를 "대상은 있는데 안 바뀌었다"로 읽어 **규칙이 아니라
        회차를 벌한다.**
        """
        z1 = [x for x in self.request.splitlines() if x.startswith("| Z1 |")]
        self.assertTrue(z1)
        for line in z1:
            self.assertIn("변경 기회", line)
            self.assertNotIn("적용 대상", line, "Z1 이 게이트 수를 본다")
        section = self.request_section("### 4-2.", "### 4-3.")
        self.assertIn("조건 충족", section)
        self.assertIn("변경 기회", section)
        self.assertIn("실제 변경", section)
        self.assertIn("판정에 쓰지 않는다", section,
                      "조건 충족을 판정에 안 쓴다는 말이 없다")
        self.assertIn("38", section, "38 과 3 이 갈리는 실측이 없다")

    def test_the_forbidden_line_is_per_item_not_a_sum(self):
        """리뷰 [P1] — 금지선 E 를 합계로 재면 손실이 숨던 자리.

        v11 이 TP 를 하나 얻고 v18 이 하나 잃으면 `C 합계 39 → 39` 로 아무 일도
        없어 보인다. 그런데 금지선이 막으려는 것이 바로 그 v18 의 손실이다.
        **요청서와 보고서가 둘 다 항목별이라고 적어야 한다.**
        """
        rows = [line for line in self.request.splitlines() if line.startswith("| E |")]
        self.assertTrue(rows, "금지선 E 가 없다")
        for line in rows:
            self.assertIn("각각", line, "E 가 항목별이 아니다")
            self.assertNotRegex(line, r"합계 TP\s*\|",
                                "E 를 합계로 적었다 — 상쇄되어 손실이 숨는다")
        section = self.request_section("## 4.", "### 4-2.")
        self.assertIn("상쇄", section, "왜 합계로 읽으면 안 되는지가 없다")
        # 보고서의 합격선도 같은 말을 해야 한다.
        verdict = self.report[self.report.index("## 8. 판정"):]
        self.assertIn("항목별로 본다", verdict)
        self.assertIn("상쇄", verdict)
        self.assertNotIn("C 항목 합계 TP 감소 0", verdict,
                         "보고서의 합격선이 아직 합계다")

    def test_the_applicability_counter_is_wired_into_the_audit(self):
        """Z1 을 사람이 눈대중하지 않게 — 세는 명령이 문서에 있고 실제로 있는가."""
        self.assertTrue((FOLDER / "applicability.py").is_file())
        self.assertIn("applicability.py", self.request)

    def test_the_off_target_rule_is_exactly_zero_not_the_churn_range(self):
        """D1 은 **정확히 0**, churn 범위는 D2 에만. 섞으면 대상 밖 45셀이 승인된다."""
        lines = self.request.splitlines()
        d1 = [line for line in lines if line.startswith("| D1 |")]
        self.assertTrue(d1, "D1 줄이 없다")
        rules = [line for line in d1 if "off_focus" in line or "대상 밖" in line]
        self.assertTrue(rules, "D1 의 규칙을 적는 줄이 없다")
        for line in rules:
            self.assertIn("정확히 0", line)
            self.assertNotIn("17~45", line, "D1 에 churn 범위가 섞였다")
        d2 = [line for line in lines if line.startswith("| D2 |")]
        self.assertTrue(any("17~45" in line for line in d2), "D2 에 churn 범위가 없다")
        self.assertIn("reproducibility.md", self.request, "churn 범위의 출처가 없다")

    def test_the_pair_comparison_covers_exactly_the_three_keys(self):
        """`--items` 는 후보가 쓰는 셋이어야 나머지 21항목을 D1 이 본다."""
        self.assertIn("--items v11,v16,v18", self.request)
        self.assertIn("21항목", self.request, "왜 셋인지가 안 적혔다")

    def test_the_comparison_json_shape_is_described_correctly(self):
        """`items` 는 리스트다. 딕셔너리처럼 적으면 실행자가 막힌다."""
        self.assertIn("딕셔너리가 아니라", self.request)
        self.assertIn("changed_cells_off_focus", self.request)
        self.assertNotIn("items.v11", self.request)

    def test_the_counter_reports_the_documented_numbers(self):
        """§5-3 이 옮겨 적은 세 층을 집계기가 실제로 내는가.

        **실제 변경의 합이 §5-1 쌍 비교의 `changed_cells` 와 같아야 한다.** 둘이 갈리면
        Z2 가 재는 것과 D1 이 재는 것이 다른 대상이라는 뜻이다.

        그리고 **v18 은 조건 충족과 변경 기회가 달라야 한다** — 둘이 같아지면 리뷰가
        잡은 [P1] 이 되돌아온 것이다.
        """
        if shutil.which("git") is None:
            raise unittest.SkipTest("git 이 없다")
        if not (CASE / "diagnostics.jsonl").is_file():
            raise unittest.SkipTest(f"{CASE} 가 없다")
        done = subprocess.run(
            [sys.executable, "-X", "utf8", str(FOLDER / "applicability.py"),
             "--case", str(CASE)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
        self.assertEqual(done.returncode, 0, done.stderr)
        counted = {m[1]: (int(m[2]), int(m[3]), int(m[4])) for m in
                   re.finditer(r"^(v\d+)\s+(\d+)\s+(\d+)\s+(\d+)", done.stdout, re.MULTILINE)}
        self.assertEqual(counted,
                         {"v18": (38, 3, 3), "v16": (2, 2, 2), "v11": (7, 7, 7)},
                         f"집계기가 문서와 다른 수를 낸다\n{done.stdout}")
        for item, layers in counted.items():
            with self.subTest(item):
                self.assertRegex(self.request,
                                 rf"(?m)^{item}\s+{layers[0]}\s+{layers[1]}\s+{layers[2]}\s",
                                 "§5-3 이 옮겨 적은 수가 집계기와 다르다")
        self.assertNotEqual(counted["v18"][0], counted["v18"][1],
                            "조건 충족과 변경 기회가 같아졌다 — [P1] 이 되돌아왔는지 보라")
        self.assertEqual(sum(layers[2] for layers in counted.values()),
                         EXPECTED_CHANGED["integrated"],
                         "실제 변경의 합이 통합 후보의 changed_cells 와 다르다")

    def test_the_counter_never_calls_a_quiet_run_a_rejection(self):
        """**어느 층의 0 도 기각으로 찍지 않는가.** [P1] 의 핵심.

        옛 판은 "대상이 있는데 안 바뀌었다 — 가설 기각" 을 찍었다. 그 "대상"이
        게이트 통과 수였기 때문에, 변경 기회가 애초에 없던 회차를 기각으로 적었다.
        """
        source = (FOLDER / "applicability.py").read_text(encoding="utf-8")
        verdicts = re.findall(r'verdict = "(.+?)"', source)
        self.assertTrue(verdicts, "판정 문구가 없다")
        for verdict in verdicts:
            with self.subTest(verdict):
                self.assertNotIn("가설 기각", verdict,
                                 "집계기가 스스로 기각을 찍는다 — 기각은 채점(Z3)이 본다")
        self.assertTrue(any("판정 보류" in v for v in verdicts))
        self.assertIn("Z1", source)
        self.assertIn("Z2", source)
        self.assertIn("BASE_REV", source, "판정 코드를 커밋으로 고정하지 않았다")
        self.assertNotIn('load("submission", ROOT / "script.py")', source,
                         "작업 트리의 script.py 를 부르면 main 이 움직일 때 수가 바뀐다")

    def test_the_counter_explains_why_a_gate_hit_is_not_an_opportunity(self):
        """38 과 3 이 갈리는 이유를 스크립트가 같이 찍는가 — 안 찍으면 사람이 헤맨다."""
        source = (FOLDER / "applicability.py").read_text(encoding="utf-8")
        self.assertIn("blocked", source, "막힌 곳을 안 센다")
        self.assertIn("기회가 아닌 것들이 막힌 곳", source)

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
