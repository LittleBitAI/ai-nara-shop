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
            f"{cite}의 예외에 해당한다면 중소기업자간 경쟁입찰 외의 방법으로 진행할 수 있습니다.": False,
            f"{cite}의 예외를 적용한다면 별도 심사를 거쳐야 합니다.": False,
            f"{cite}의 예외를 적용하여야 하는지 검토한다.": False,
            f"{cite}에 따라 경쟁입찰 외의 방법으로 진행할 수 있다.": False,
            f"{cite}의 예외를 적용하여 일반물품으로 입찰공고합니다.": True,
            f"{cite}의 예외를 적용하여 진행할 수 있다.": False,
            f"{cite}의 예외를 적용하여 입찰하는 경우 별도 심사한다.": False,
            f"{cite}의 예외를 적용하여 입찰하면 별도 심사한다.": False,
            f"{cite}의 예외를 적용하여 진행하도록 한다.": False,
            f"{cite}의 예외를 적용하여 진행하여야 한다.": False,
            f"{cite}의 예외를 적용하여 진행": False,
            f"{cite}의 예외에 해당하므로 대기업도 참여할 수 있습니다.": True,
            f"{cite} 제4호를 적용하여 대기업도 입찰에 참여할 수 있습니다.": True,
            f"{cite} 제4호를 적용하여 비영리법인도 참여할 수 있습니다.": True,
            f"{cite} 제4호를 적용하여 업체는 규격만 맞으면 참여할 수 있다.": False,
            f"{cite} 제4호를 적용하여 대기업도 참여할 수 있으면 중소기업도 참여할 수 있습니다.": False,
            f"{cite} 제4호에 따라 비영리법인, 대기업도 참여가 가능합니다.": True,
            f"{cite} 제4호에 따라 중견기업은 입찰에 참가할 수 있습니다.": True,
            f"{cite} 제4호에 따라 중소기업도 참여할 수 있습니다.": False,
            f"{cite} 제4호에 해당하는 경우 대기업도 참여할 수 있습니다.": False,
            f"{cite} 제4호에도 불구하고 대기업은 참여가 불가능합니다.": False,
            f"{cite} 제4호에 따라 대기업도 참여가 가능한 경우 별도 심사한다.": False,
            f"{cite} 제4호에 따라 대기업도 참여할 수 있으면 심사한다.": False,
            f"{cite} 제4호에 따른 특정한 기술이 필요한 경우에 해당되며, 경쟁입찰로는 목적 달성이 불가능함.": False,
            f"{cite}제4호에 따른 특별사유의 경우에 해당되며, 다만 본 입찰은 중소기업자간 경쟁입찰로 진행합니다."
            " 직접생산확인증명서는 요구하지 않습니다.": False,
            f"{cite} 제4호를 적용합니다. 본 입찰은 중소기업자간 경쟁입찰로 진행합니다.": False,
            f"{cite} 제4호를 적용합니다. 본 입찰은 중소기업자간 경쟁입찰 방식으로 진행합니다.": False,
            f"{cite} 제4호를 적용합니다. 본 입찰은 중소기업자간 경쟁입찰 대상입니다.": False,
            f"{cite} 제4호를 적용합니다. 입찰참가자격은 중소기업자로 제한합니다.": False,
            f"{cite} 제4호에 따라 예외를 적용합니다. 다만 본 입찰의 참가자격은 중소기업에 한합니다.": False,
            f"{cite} 제4호를 적용합니다. 중소기업만 참가할 수 있습니다.": False,
            f"{cite} 제4호에 따라 예외를 적용합니다. 입찰참가자격: 중소기업확인서를 소지한 업체만 입찰에 참가할 수"
            " 있습니다.": False,
            f"{cite} 제4호를 적용합니다. 참가자격은 소상공인 확인을 받은 업체로 제한합니다.": False,
            f"{cite} 제4호에 따라 예외를 적용합니다. 입찰참가자격: 중소기업확인서를 소지한 자.": False,
            f"{cite} 제4호를 적용합니다. 입찰참가자격 ○ 소기업·소상공인 확인서 보유 업체.": False,
            f"{cite} 제4호에 따라 예외를 적용합니다. 본 입찰에 참가할 수 있는 자는 중소기업확인서를 소지한 자입니다.": False,
            f"{cite}제4호의 예외 대신 중소기업자간 경쟁제품의 일반 규정을 적용합니다.": False,
            f"{cite} 제4호에 해당하지만 일반 규정을 적용합니다.": False,
            f"{cite} 대신 국가계약법 시행령 제26조의 예외를 적용합니다.": False,
            f"{cite} 대신 발주기관 내규의 예외를 적용합니다.": False,
            f"{cite}과 무관하게 「국가를 당사자로 하는 계약에 관한 법률」의 예외를 적용합니다.": False,
            f"{cite} 제4호 예외 적용 (□예 ■아니오).": False,
            f"{cite} 제4호 예외 적용 [ ] 해당 [V] 비해당.": False,
            f"{cite} 제4호 예외 적용 <미해당>.": False,
            f"{cite} 제4호를 적용합니다(단, 본 공고는 해당 없음).": False,
            f"{cite} 제4호의 예외를 적용합니다\"라는 문구는 삭제합니다.": False,
            f"{cite} 제4호를 적용함 → 삭제.": False,
            f"{cite} 제4호를 적용합니다(정정 전).": False,
            f"{cite} 제4호를 적용합니다? 아니오.": False,
            f"{cite} 제4호에 따라 대기업도 참여가 가능합니다(해당 없음).": False,
            f"{cite} 제4호에 따라 중소기업자간 경쟁입찰 예외 적용 <중소기업자간 경쟁제도 예외사유> ㅇ 본 용역은": True,
            f"{cite} 제4호의 경우 수의계약의 예외에 해당합니다.": False,
            f"{cite} 제4호에 따른 중소기업자 확인사항을 검토하고 발주기관 내규의 예외를 적용합니다.": False,
            f"{cite} 제4호를 적용합니다(사유가 확인되는 경우에만 적용하며 현재는 일반 규정을 따릅니다).": False,
            f"{cite} 제4호에 따라 부대장비에만 중소기업자간 경쟁입찰의 예외를 적용합니다.": False,
            f"{cite} 제4호에 따라 2권역만 중소기업자간 경쟁입찰의 예외를 적용합니다.": False,
            f"{cite} 제4호를 적용합니다(사유: 특정 기술·용역이 필요한 공공기관의 특별한 사정 있음, 본 건 미적용).": False,
            f"{cite} 제4호를 적용합니다(작성 예시).": False,
            f"{cite} 제4호에 따라 중소기업자간 경쟁입찰의 예외를 적용합니다(향후 공고부터).": False,
            f"{cite} 제4호를 적용함, 단 해당 품목은 제외.": False,
            f"{cite} 제4호의 예외를 적용함 여부는 수요기관이 결정.": False,
            f"{cite} 제4호를 적용합니다 / 해당없음.": False,
            f"{cite} 제4호를 적용합니다 ▷ 아니오.": False,
            f"{cite} 제4호를 적용합니다 : N.": False,
            f"{cite} 제4호를 적용합니다(부대장비에 한함).": False,
            f"{cite} 제4호에 따라 부대장비는 중소기업자간 경쟁입찰 제품에 해당하지 않음.": False,
            f"{cite} 제4호에 따라 부대장비 입찰에는 대기업도 참여가 가능합니다.": False,
            f"{cite} 제4호에 따라 2권역에 대해서는 중소기업자간 경쟁입찰의 예외를 적용합니다.": False,
            f"{cite} 제4호에 따라 본 물품은 중소기업자간 경쟁입찰 제품에 해당하지 않음.": True,
            f"{cite} 제4호에 따라 대기업도 참여가 가능합니다(2권역만 해당).": False,
            f"{cite} 제4호를 적용합니다 [폐지].": False,
            f"{cite} 제4호를 적용합니다(사유 없음).": False,
            f"{cite} 제4호를 적용합니다(특정 기술·용역이 필요한 경우).": True,
            f"{cite} 제4호를 적용합니다(사유: 붙임 참조).": True,
            "(「판로지원법 시행령」 제7조제1항 제4호 예외 적용) 입찰에 참가하려는 업체는 서류를 제출.": True,
            f"{cite} 제4호에 의거하여 중소기업자 우선조달계약에 대한 예외를 적용한다.": True,
            f"{cite} 제4호 규정을 적용하여 입찰을 진행합니다.": True,
            f"{cite}을 적용합니다.": True,
            f"{cite} 제4호를 적용합니다. 참가자격의 기업 구분과 다른 경우 - 발급된 중소기업ㆍ소상공인확인서의"
            " 유효기간 시작일이 마감일 이후인 경우 무효.": True,
            f"{cite} 제4호를 적용합니다. 입찰참가자격을 소기업·소상공인으로 한정한다.": False,
            f"입찰방법 : 중소기업자간 제한경쟁 / 총액. {cite} 제4호를 적용합니다.": False,
            f"{cite} 제4호에 따라 중소기업자간 경쟁입찰의 예외를 적용합니다. 계약방법 : 협상에 의한 계약.": True,
            f"{cite} 제4호를 적용합니다. 중소기업자간 경쟁입찰의 방법 등으로는 목적 달성이 어렵다.": True,
            f"{cite} 제4호에 따라 중소기업자간 경쟁입찰 외의 방법으로 추진함.": True,
            f"{cite} 제4호의 경우에 해당하지 않으므로 중소기업자간 경쟁입찰로 한다.": False,
            f"{cite} 제4호에 따라 특정 기술이 필요한 경우(서버)로 중소기업자간 경쟁입찰 제품에 해당하지 않음.": True,
            f"{cite} 제4호에 해당하는 경우 중소기업자간 경쟁입찰 제품에 해당하지 않음.": False,
            f"{cite} 제4호의 예외가 아니므로 중소기업자간 경쟁입찰 대상에 해당하지 않음은 아니다.": False,
            f"{cite} 제4호에 해당하는 경우로서 대기업도 참여할 수 있습니다.": True,
            f"{cite} 제4호를 적용하므로 대기업의 입찰 참여 제한이 없습니다.": True,
            f"{cite}의 예외에 해당하지 않으므로 일반 규정을 적용합니다.": False,
            f"{cite}의 예외를 적용하여 입찰하는 업체를 심사할 수 있다.": False,
            f"{cite}의 예외를 적용하여 많은 업체가 참여할 수 있다.": True,
            f"{cite} 제4호를 적용하여 대기업이 입찰에 참여할 수 있습니다.": True,
            f"{cite} 제4호를 적용하여 대기업도(비영리법인 포함) 입찰에 참여할 수 있습니다.": True,
            f"{cite} 제4호를 적용하여 대기업도 참여할 수 있는지 검토한다.": False,
            f"{cite} 제4호를 적용하여 대기업도 참여할 수 있도록 검토한다.": False,
            f"{cite} 제4호를 적용하여 기업이 제출한 서류를 검토할 수 있다.": False,
            f"{cite} 제4호를 적용하는 경우 대기업도 참여할 수 있다.": False,
            f"{cite} 제4호를 적용하여 업체가 참여하면 심사할 수 있다.": False,
            f"{cite}의 예외를 적용하여 진행할 수도 있다.": False,
            f"{cite}의 예외를 적용하여 일정 정도 조정할 수 있다.": False,
            f"{cite}의 예외를 적용하여 제도 개선을 검토할 수 있다.": False,
            f"{cite} 제4호를 적용하여 입찰참가자는 별도 서류를 낼 수 있다.": True,
            f"{cite}의 예외를 적용하여 관리자는 조정할 수 있다.": False,
            f"{cite}의 예외를 적용하여 수요기관은 조정할 수 있다.": False,
            f"{cite} 제4호 규정을 적용하여 직접생산확인품목에서 제외하고 일반물품으로 입찰공고합니다.": True,
            f"{cite}에 따라 중소기업자간 경쟁입찰 예외 적용 <예외사유>": True,
            f"{cite}제4호에 따라 경쟁입찰 외의 방법으로 추진함.": True,
            f"{cite} 제4호는 이 입찰과 무관하다.": False,
            f"{cite}제4호에 따라 중소기업자간 경쟁입찰의 예외에 해당합니다.": True,
            f"{cite}제4호를 적용합니다.": True,
            f"{cite}제3호에 따라 경쟁입찰의 예외를 적용합니다 ※ 공동수급을 허용하지 않습니다.": True,
            # #152 가 C 에게 넘긴 미해결 P2 셋. 셋 다 구성된 문장이고 제공 자료에는 없다.
            # 대조군을 짝지어 둔다 — 고친 것이 이웃한 참 발화까지 죽이면 안 된다.
            # (1) 범위 한정어 `에 한해서` — `에 한해` 만 잡고 `서` 를 놓쳤다.
            f"{cite} 제4호에 따라 부대장비에 한해서 중소기업자간 경쟁입찰의 예외를 적용합니다.": False,
            f"{cite} 제4호에 따라 부대장비에 한해 중소기업자간 경쟁입찰의 예외를 적용합니다.": False,
            f"{cite} 제4호에 따라 중소기업자간 경쟁입찰의 예외를 적용합니다.": True,
            # (2) `-하여` 뒤에 선 범위 — `partial_scope` 가 서술어 앞만 읽었다.
            f"{cite} 제4호에 따라 중소기업자간 경쟁입찰의 예외를 적용하여 부대장비만 일반입찰로 구매한다.": False,
            f"{cite} 제4호에 따라 중소기업자간 경쟁입찰의 예외를 적용하여 2권역에 대해서는 일반입찰로 한다.": False,
            f"{cite} 제4호에 따라 중소기업자간 경쟁입찰의 예외를 적용하여 일반입찰로 구매한다.": True,
            f"{cite} 제4호에 따라 중소기업자간 경쟁입찰의 예외를 적용하여 본 입찰은 일반입찰로 한다.": True,
            # (3) 곁말을 받아들인 뒤의 철회 — 곁말 **뒤**를 아무도 안 읽었다.
            f"{cite} 제4호를 적용합니다(사유: 특정 기술 필요), 그러나 본 공고에는 적용하지 않습니다.": False,
            f"{cite} 제4호를 적용합니다(사유: 특정 기술 필요), 다만 본 건은 미적용.": False,
            f"{cite} 제4호를 적용합니다(사유: 특정 기술 필요).": True,
            f"{cite} 제4호를 적용하므로 대기업의 참여 제한이 없습니다.": True,
            # #162 1라운드 — 꼬리의 주제를 `만`·`에 대해서는` 만 세어 `는`·`에는` 을 놓쳤다.
            # 맨 `는`·`은` 은 셋으로 갈린다: 범위를 좁히는 주제 · 뒤 절의 주어 · 관형형.
            # 셋을 다 넣어 둔다. 하나만 고치면 나머지 둘 중 하나가 죽는다.
            f"{cite} 제4호에 따라 예외를 적용하여 부대장비는 일반입찰로 구매한다.": False,
            f"{cite} 제4호에 따라 예외를 적용하여 2권역에는 일반입찰로 한다.": False,
            f"{cite} 제4호에 따라 예외를 적용하여 부대장비에는 일반입찰을 적용한다.": False,
            # 주어 갈래("…입찰참가자는 별도 서류를 낼 수 있다")는 위에 이미 있다.
            f"{cite} 제4호의 예외를 적용하여 많은 업체가 참여할 수 있다.": True,     # 관형형
            f"{cite} 제4호에 따라 예외를 적용하여 본 입찰은 일반입찰로 한다.": True,  # 공고 전체
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
