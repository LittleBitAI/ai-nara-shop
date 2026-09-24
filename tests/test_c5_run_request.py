"""실행 요청서가 **노트북 소스와 어긋나지 않는가**.

과거에 요청서의 셀 번호가 노트북과 어긋나 **실행자가 셀을 못 찾은 적이 있다.** 요청서는
사람이 보고 그대로 따라 하는 문서라, 틀리면 회차 하나가 통째로 버려진다.

이 검사가 고정하는 것.
  1. 요청서가 가리키는 셀 번호에 **실제로 그 스위치가 있다**
  2. 그 셀이 만드는 **명령 문자열**이 요청서에 옮긴 것과 같다
  3. 요청서의 합격 기준 수치가 후보 보고서의 실측값과 **같다**
  4. `<RUN_COMMIT>` 자리표시자가 남아 있으면 **그 사실이 보이게** 한다

모델을 부르지 않는다.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks/colab-baseline.ipynb"
REQUEST = ROOT / "reports/team-c/c5-v11-paths/RUN-REQUEST.md"
CANDIDATE = ROOT / "reports/team-c/c5-v11-paths/CANDIDATE.md"

# 요청서 §2-1 이 가리키는 셀과 그 셀에 있어야 하는 이름.
CELLS = {1: ("SOURCE_MODE", "REPO_REF"), 18: ("RUN_DIAGNOSTIC", "DIAGNOSTIC_ARGS")}
# 요청서 §2-2 가 옮겨 적은 명령. 노트북에 그대로 있어야 한다.
COMMAND = 'run_case("dev-debug", WORK / "open/dev.jsonl", args=DIAGNOSTIC_ARGS)'


def cells():
    data = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    return ["".join(cell["source"]) for cell in data["cells"]]


class RequestMatchesNotebook(unittest.TestCase):
    """요청서가 가리키는 자리에 실제로 그것이 있는가."""

    @classmethod
    def setUpClass(cls):
        if not NOTEBOOK.is_file():
            raise unittest.SkipTest(f"{NOTEBOOK} 가 없다")
        cls.cells = cells()
        cls.request = REQUEST.read_text(encoding="utf-8")

    def test_the_named_cells_hold_the_named_switches(self):
        for index, names in CELLS.items():
            self.assertLess(index, len(self.cells), f"셀 [{index}] 가 없다")
            source = self.cells[index]
            for name in names:
                self.assertIn(name, source, f"셀 [{index}] 에 {name} 이 없다")

    def test_the_request_points_at_those_cells(self):
        for index in CELLS:
            self.assertIn(f"`[{index}]`", self.request,
                          f"요청서가 셀 [{index}] 을 안 가리킨다")

    def test_the_quoted_command_exists_in_the_notebook(self):
        """§2-2 가 옮긴 명령이 노트북에 그대로 있는가."""
        self.assertIn(COMMAND, self.cells[18])
        self.assertIn(COMMAND, self.request)

    def test_the_diagnostic_default_is_still_true(self):
        """요청서는 "기본값이 이미 맞다" 고 적는다. 기본이 바뀌면 그 문장이 거짓이 된다."""
        self.assertRegex(self.cells[18], r"RUN_DIAGNOSTIC\s*=\s*True")

    def test_no_other_cell_defines_the_repo_ref(self):
        """`REPO_REF` 를 고칠 자리가 하나여야 실행자가 헷갈리지 않는다."""
        defining = [i for i, s in enumerate(self.cells)
                    if re.search(r"^REPO_REF\s*=", s, re.MULTILINE)]
        self.assertEqual(defining, [1], f"REPO_REF 를 정의하는 셀이 여럿이다: {defining}")


class RequestMatchesTheCandidate(unittest.TestCase):
    """합격 기준의 수치가 후보 보고서의 실측과 같은가."""

    @classmethod
    def setUpClass(cls):
        cls.request = REQUEST.read_text(encoding="utf-8")
        cls.candidate = CANDIDATE.read_text(encoding="utf-8")

    def test_the_replayed_result_is_quoted_the_same(self):
        for number in ("5/6/1", "0.615376122347", "788c7df"):
            self.assertIn(number, self.candidate, f"후보 보고서에 {number} 이 없다")
        self.assertIn("5/6/1", self.request)

    def test_the_churn_range_comes_from_the_recorded_source(self):
        """§4 기준 D 는 과거 실측에서 온 수다. 출처를 같이 적었는가."""
        self.assertIn("0.000008~0.010088", self.request)
        self.assertIn("reproducibility.md", self.request)

    def test_the_criteria_are_read_as_a_difference_not_an_absolute(self):
        """리뷰 [P2] — 후보가 아무것도 안 해도 통과하던 자리.

        기준이 전부 절대값이면 무효과 후보가 B·C·D 를 통과한다(기준 v11 이 2/3/4 라
        FP 3 ≤ 6). **움직였는가를 먼저 묻는 기준 Z** 가 있어야 한다.
        """
        self.assertIn("| **Z** |", self.request, "기준 Z 가 없다")
        self.assertIn("FN **감소 ≥ 1**", self.request)
        self.assertIn("가설 기각", self.request,
                      "Z 실패 시 기각한다는 말이 없다")

    def test_the_off_target_rule_is_exactly_zero_not_the_churn_range(self):
        """리뷰 [P2] — 대상 밖 승인 규칙이 틀렸던 자리.

        같은 원응답 위 `기준↔후보` 는 코드만 다르므로 **결정적**이고 대상 밖은 0 이어야
        한다. churn 범위(17~45셀)는 **회차1↔회차2** 에만 쓴다. 한 칸에 섞으면 대상 밖
        45셀까지 승인된다.
        """
        self.assertIn("| **D1** |", self.request)
        self.assertIn("| **D2** |", self.request)
        # D1 은 기준표와 감사표 양쪽에 나온다. **어느 줄에도** churn 범위가 섞이면 안 된다.
        d1 = [line for line in self.request.splitlines() if line.startswith("| **D1** |")]
        self.assertTrue(d1, "D1 줄이 없다")
        for line in d1:
            self.assertIn("정확히 0", line)
            self.assertNotIn("17~45", line, "D1 에 churn 범위가 섞였다")
        d2 = [line for line in self.request.splitlines() if line.startswith("| **D2** |")]
        self.assertTrue(d2, "D2 줄이 없다")
        self.assertTrue(any("17~45" in line for line in d2))

    def test_the_pair_comparison_focuses_on_v11_alone(self):
        """`--items` 는 `v11` 하나여야 D1 이 v10·v12·v13 의 회귀까지 덮는다.

        넷을 다 대상으로 잡으면 그 셋이 **대상 안**이 되어 `changed_cells_off_focus` 가
        그 회귀를 못 본다. CPU 재생에서 두 옵션의 `대상 밖`은 둘 다 0 이고
        `after.tp`(4·4·3)도 그대로 읽히므로, 좁히는 쪽이 손해 없이 더 엄격하다.
        """
        self.assertIn("--items v11 --output-dir", self.request)
        self.assertNotIn("--items v11,v10,v12,v13", self.request,
                         "쌍 비교가 넷을 대상으로 잡으면 D1 이 그 셋을 못 본다")
        self.assertIn("23항목", self.request, "왜 좁히는지가 안 적혔다")

    def test_the_audit_keys_match_the_real_comparison_json(self):
        """요청서가 적은 `comparison.json` 표기가 실제 구조와 같은가.

        `items` 는 딕셔너리가 아니라 리스트다. 틀리게 적으면 실행자가 막힌다.
        """
        self.assertIn("딕셔너리가 아니라", self.request)
        self.assertIn("changed_cells_off_focus", self.request)
        self.assertNotIn("items.v11", self.request, "리스트를 딕셔너리처럼 적었다")

    def test_the_run_commit_placeholder_is_visible_until_filled(self):
        """push 뒤 채우는 자리다. 안 채운 채 실행하면 `main` 으로 도는 사고가 난다."""
        if "<RUN_COMMIT>" in self.request:
            self.assertIn("push 뒤 채운다", self.request,
                          "자리표시자가 남았는데 채워야 한다는 말이 없다")
        else:
            self.assertRegex(self.request, r"\b[0-9a-f]{40}\b",
                             "자리표시자를 지웠으면 40자리 SHA 가 있어야 한다")


if __name__ == "__main__":
    unittest.main()
