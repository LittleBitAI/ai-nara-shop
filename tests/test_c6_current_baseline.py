"""`VERIFIED.md` §8 의 계약 — **현재 기준선 위에서 세 규칙이 아직 그 몫을 낸다.**

§3~§4 는 기준 `c68eb00` 위의 수이고 그 기준은 159 커밋 낡았다. §8 은 그것을 옮겨 적지
않고 따로 다시 잰 절이며, 이 검사가 그 수를 고정한다.

세 규칙은 PR #142 로 이미 운영 `script.py` 에 들어가 있다. 그래서 후보를 **얹어서**
잴 수 없고 **빼서** 잰다 — 기준 커밋의 `script.py` 에서 세 블록을 지운 대조본 넷을
만들고(셋 다 · 하나씩) 같은 보관 응답 위에서 다섯 벌을 재생한다.

이 검사가 고정하는 것 여섯.
  1. 다섯 판이 §8 표의 Macro 를 **자릿수까지 그대로** 낸다
  2. 각 규칙의 몫이 §8 표와 같다 — 그 수가 움직이면 "아직 살아 있다"는 판단도 다시 본다
  3. **하나씩의 합이 셋을 다 뺀 값과 같다** — §8 의 "세 규칙이 안 겹친다"
  4. 바뀐 셀이 §8 표와 같고 **전부 v11·v16·v18 안**이다 — `D1` 금지선
  5. **TP 가 줄어든 항목이 없다** — `E` 금지선
  6. **`TRUSTED` 항목을 하나도 안 건드린다** — 9/27 채택 게이트 3 이 걸릴 자리가 없다

기준 커밋은 `main` 이 아니라 `3c36bba` 로 박는다. `origin/main` 을 읽으면 `main` 이
움직일 때 같은 보관 응답에서 다른 수가 나오고 §8 만 낡는다 — `test_c6_integrated.py`
머리가 적은 #124 [P2] 와 같은 자리다.

모델을 부르지 않는다.
"""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "reports/runs/colab-1790432295199698396/dev-debug"
VERIFIED = ROOT / "reports/team-c/c6-dev-macro/VERIFIED.md"

# §8 이 잰 기준 커밋. `main` 이 아니라 그때의 sha 를 박는다.
BASE_REV = "3c36bba589ef9f8cc4232698b6009ebc3846089c"

ITEMS = [f"v{i}" for i in range(1, 25)]
TARGET = ("v11", "v16", "v18")
OFF_TARGET = [i for i in ITEMS if i not in TARGET]
# `tools/tune_offdev_thresholds.py:13` 이 소유한다. 여기서는 읽기만 한다.
TRUSTED = ("v1", "v2", "v3", "v5", "v6", "v7", "v8", "v12", "v13",
           "v14", "v15", "v19", "v21", "v22", "v23")

# 세 블록을 줄 번호가 아니라 문구로 찾는다 — `script.py` 가 위아래로 움직여도 버틴다.
BLOCKS = {
    "C6-1": ("    # v18 only: with no direct-production demand",
             '            out["v18"] = dict(cell)'),
    "C6-2": ("    # v16: an undetermined qualification role",
             '        out["v16"] = {"위반여부": 0, "근거문구": None}'),
    "C6-3": ("    # v11: a confirmed v10 absence",
             '        out["v11"] = {"위반여부": 1, "근거문구": None}'),
}

# §8 표. 자릿수까지 그대로다.
MACRO = {
    "main": "0.828333594510",
    "none": "0.812948979125",
    "no1": "0.819359235536",
    "no2": "0.826196842373",
    "no3": "0.824060090237",
}
# 뺀 판 → (그 규칙의 몫, 바뀐 셀, 항목별 셀)
SHARE = {
    "none": ("0.015384615385", 5, {"v18": 3, "v16": 1, "v11": 1}),
    "no1": ("0.008974358974", 3, {"v18": 3}),
    "no2": ("0.002136752137", 1, {"v16": 1}),
    "no3": ("0.004273504273", 1, {"v11": 1}),
}
# §8 의 항목표. 셋을 다 뺐을 때 → 기준 커밋 그대로.
PER_ITEM = {
    "v11": ((4, 2, 2), (5, 2, 1)),
    "v16": ((4, 3, 2), (4, 2, 2)),
    "v18": ((2, 1, 5), (4, 2, 3)),
}
CUT = {"none": ("C6-1", "C6-2", "C6-3"), "no1": ("C6-1",),
       "no2": ("C6-2",), "no3": ("C6-3",)}


def cut(source, name):
    """`name` 블록을 통째로 지운다. 머리 문구부터 꼬리 줄 끝까지다."""
    head, tail = BLOCKS[name]
    start = source.index(head)
    end = source.index(tail, start) + len(tail) + 1        # 줄바꿈까지
    return source[:start] + source[end:]


class CurrentBaselineShare(unittest.TestCase):
    """기준 커밋 `3c36bba` 위에서 §8 의 수가 나오는가."""

    @classmethod
    def setUpClass(cls):
        if shutil.which("git") is None:
            raise unittest.SkipTest("git 이 없다")
        if not (CASE / "diagnostics.jsonl").is_file():
            raise unittest.SkipTest(f"{CASE} 가 없다")
        shown = subprocess.run(["git", "-C", str(ROOT), "show", f"{BASE_REV}:script.py"],
                               capture_output=True)
        if shown.returncode != 0:
            raise unittest.SkipTest(f"{BASE_REV} 를 못 읽는다")
        cls.source = shown.stdout.decode("utf-8")
        for name in BLOCKS:
            if BLOCKS[name][0] not in cls.source:
                raise AssertionError(f"{BASE_REV} 의 script.py 에 {name} 이 없다")

        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.rows, cls.macro, cls.metrics = {}, {}, {}
        for variant in MACRO:
            text = cls.source
            for name in CUT.get(variant, ()):
                text = cut(text, name)
            script = root / f"{variant}.py"
            script.write_text(text, encoding="utf-8", newline="")
            cls.rows[variant], cls.macro[variant], cls.metrics[variant] = cls.replay(
                root, variant, script)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "tmp"):
            cls.tmp.cleanup()

    @classmethod
    def replay(cls, root, name, script):
        out = root / f"out-{name}"
        done = subprocess.run(
            [sys.executable, "-X", "utf8", str(ROOT / "tools/replay_run.py"),
             "--case", str(CASE), "--script", str(script), "--output-dir", str(out)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
        if done.returncode != 0:
            raise AssertionError(f"재생 실패 {name}\n{done.stdout}\n{done.stderr}")
        scored = subprocess.run(
            [sys.executable, "-X", "utf8", str(ROOT / "tools/score.py"),
             "--truth", str(ROOT / "open/dev_labels.csv"),
             "--pred", str(out / "submission.csv"),
             "--output-dir", str(root / f"score-{name}")],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
        if scored.returncode != 0:
            raise AssertionError(f"채점 실패 {name}\n{scored.stdout}\n{scored.stderr}")
        metrics = json.loads((root / f"score-{name}/metrics.json").read_text(encoding="utf-8"))
        with (out / "submission.csv").open(encoding="utf-8", newline="") as stream:
            rows = {r["id"]: r for r in csv.DictReader(stream)}
        return rows, f"{metrics['macro_f1']:.12f}", metrics

    def changed(self, variant):
        """`variant`(규칙을 뺀 판)와 기준 커밋 그대로의 판이 갈리는 셀."""
        full = self.rows["main"]
        return [(i, item) for i in full for item in ITEMS
                if full[i][item] != self.rows[variant][i][item]]

    def test_the_five_replays_give_the_documented_macro(self):
        for variant, expected in MACRO.items():
            with self.subTest(variant=variant):
                self.assertEqual(self.macro[variant], expected,
                                 f"{variant} 가 §8 표의 Macro 를 못 낸다")

    def test_each_rule_is_worth_what_the_table_says(self):
        """§8 표에 **적힌** 12 자리끼리 뺀다.

        `float` 로 빼면 마지막 자리가 1 씩 흔들린다(`0.004273504273` vs `…274`).
        이 검사가 고정하는 것은 표의 산수이지 이진 부동소수의 반올림이 아니다.
        """
        full = Decimal(self.macro["main"])
        for variant, (share, _cells, _by_item) in SHARE.items():
            with self.subTest(variant=variant):
                self.assertEqual(str(full - Decimal(self.macro[variant])), share)

    def test_the_three_rules_touch_disjoint_cells(self):
        """§8 의 핵심 주장 — 세 규칙이 안 겹친다. **셀로 증명한다.**

        Macro 합으로는 증명이 안 된다(아래 검사). 셀 집합은 정확하다.
        """
        singles = [set(self.changed(v)) for v in ("no1", "no2", "no3")]
        for a in range(len(singles)):
            for b in range(a + 1, len(singles)):
                with self.subTest(pair=(a, b)):
                    self.assertEqual(singles[a] & singles[b], set(),
                                     "두 규칙이 같은 칸을 건드린다")
        union = singles[0] | singles[1] | singles[2]
        self.assertEqual(union, set(self.changed("none")),
                         "하나씩의 합집합이 셋을 다 뺀 판과 다르다")

    def test_the_macro_sum_is_off_by_one_ulp_and_that_is_rounding(self):
        """하나씩의 합이 마지막 자리에서 1 만큼 어긋난다 — 상호작용이 아니다.

        다섯 Macro 를 각각 12자리로 자른 뒤 더했으니 남는 값이다. 셀이 안 겹친다는
        위 검사가 그것을 말해 준다. 이 검사는 그 어긋남이 **1e-12 를 안 넘는지**만
        본다 — 넘으면 반올림으로 설명이 안 되고 겹침을 다시 봐야 한다.
        """
        full = Decimal(self.macro["main"])
        singles = sum((full - Decimal(self.macro[v]) for v in ("no1", "no2", "no3")),
                      Decimal(0))
        gap = abs(singles - (full - Decimal(self.macro["none"])))
        self.assertLessEqual(gap, Decimal("0.000000000001"), f"어긋남 {gap}")

    def test_the_changed_cells_match_the_table(self):
        for variant, (_share, count, by_item) in SHARE.items():
            with self.subTest(variant=variant):
                cells = self.changed(variant)
                self.assertEqual(len(cells), count)
                seen = {}
                for _id, item in cells:
                    seen[item] = seen.get(item, 0) + 1
                self.assertEqual(seen, by_item)

    def test_nothing_outside_the_three_items_moves(self):
        """`D1` 금지선. 대상 밖이 한 칸이라도 움직이면 기각이다."""
        for variant in SHARE:
            with self.subTest(variant=variant):
                stray = sorted({item for _id, item in self.changed(variant)
                                if item in OFF_TARGET})
                self.assertEqual(stray, [], f"{variant} 가 대상 밖을 건드린다")

    def test_no_item_loses_a_true_positive(self):
        """`E` 금지선. 방침과 무관하다."""
        without = self.metrics["none"]["items"]
        with_them = self.metrics["main"]["items"]
        for item in ITEMS:
            with self.subTest(item=item):
                self.assertGreaterEqual(with_them[item]["tp"], without[item]["tp"])

    def test_no_trusted_item_is_touched(self):
        """9/27 채택 게이트 3. v11·v16·v18 은 `TRUSTED` 에 없다."""
        self.assertEqual([i for i in TARGET if i in TRUSTED], [])
        for variant in SHARE:
            with self.subTest(variant=variant):
                hit = sorted({item for _id, item in self.changed(variant)
                              if item in TRUSTED})
                self.assertEqual(hit, [])

    def test_the_per_item_table_matches(self):
        without = self.metrics["none"]["items"]
        with_them = self.metrics["main"]["items"]
        for item, (off, on) in PER_ITEM.items():
            with self.subTest(item=item):
                self.assertEqual(
                    (without[item]["tp"], without[item]["fp"], without[item]["fn"]), off)
                self.assertEqual(
                    (with_them[item]["tp"], with_them[item]["fp"], with_them[item]["fn"]), on)


class VerifiedSectionSaysTheSame(unittest.TestCase):
    """§8 의 본문이 위 상수와 어긋나면 둘 중 하나가 낡은 것이다."""

    @classmethod
    def setUpClass(cls):
        cls.text = VERIFIED.read_text(encoding="utf-8")
        head = cls.text.index("## 8.")
        cls.section = cls.text[head:]

    def test_the_section_exists_and_names_its_baseline(self):
        self.assertIn("3c36bba", self.section, "§8 이 기준 커밋을 안 밝힌다")
        self.assertIn("colab-1790432295199698396", self.section,
                      "§8 이 어느 원응답 위인지 안 밝힌다")
        self.assertIn("--script", self.section, "§8 이 코드를 박았다는 말이 없다")

    def test_every_macro_in_the_table_is_written_out(self):
        for variant, value in MACRO.items():
            with self.subTest(variant=variant):
                self.assertIn(value, self.section, f"{variant} 의 Macro 가 §8 에 없다")

    def test_every_share_in_the_table_is_written_out(self):
        for variant, (share, _cells, _by_item) in SHARE.items():
            with self.subTest(variant=variant):
                self.assertIn(share, self.section, f"{variant} 의 몫이 §8 에 없다")

    def test_the_section_does_not_present_this_as_an_adoption_proposal(self):
        """세 규칙은 이미 운영 중이다. 채택 제안으로 읽히면 안 된다."""
        self.assertIn("채택 제안이 아니다", self.section)

    def test_the_old_baseline_number_is_never_left_bare(self):
        """§3~§4 의 `c68eb00` 수를 §8 이 새 기준값처럼 옮겨 적지 않았다.

        나란히 적는 것 자체는 막지 않는다 — 기준선이 갈렸다는 것이 §8 의 말이다.
        막는 것은 **경고 없이** 적는 것이다. 그러면 다음 사람이 두 수를 한 줄에
        놓고 "좋아졌다"고 읽는다.

        경고는 **그 수가 든 문단 안에서** 찾는다. §8 어디서든 찾으면 게이트가 가짜가
        된다 — §8 은 반올림 문단에서 이미 "읽지 않는다"를 쓰므로, 정작 옛 기준 수
        옆의 경고를 지워도 검사가 초록으로 남는다.
        """
        for paragraph in self.section.split("\n\n"):
            if "0.007850135975" not in paragraph:
                continue
            self.assertIn("기준선", paragraph,
                          "옛 기준 수를 적으면서 기준선이 갈렸다는 말이 없다")
            self.assertTrue(
                any(w in paragraph for w in ("읽지 않는다", "견주지 않는다")),
                "§8 이 옛 기준 수를 경고 없이 적었다")
        self.assertIn("0.007850135975", self.text[:self.text.index("## 8.")],
                      "§3~§4 에서 옛 기준 수가 사라졌다")


if __name__ == "__main__":
    unittest.main()
