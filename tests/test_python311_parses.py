"""지원 환경(Python 3.11)에서 **파싱조차 안 되는 파일**이 다시 들어오지 않게 한다.

`docs/setup.md:51` 이 정한 필수 환경은 "Python 3.11 이상" 이다. 그런데 같은 결함이
**두 번** 나왔다 — 둘 다 f-string 안에서 바깥과 같은 따옴표를 다시 쓴 것이고,
그 문법은 PEP 701 이라 **3.12 부터**다. 개발 환경이 3.12 이상이라 안 드러났다.

| 언제 | 어디 |
| --- | --- |
| PR #115 리뷰 | `reports/team-c/c-unlabeled-multiplier/multiplier.py` |
| PR #118 | `reports/team-c/b1-aftermath/row_conditions.py` |

세 번째가 나오지 않게 `E9`(구문 오류)를 **0건으로 고정**한다.

**`--isolated` 와 `--select` 를 반드시 준다.** 저장소 설정과 ruff 기본값이 버전마다
달라서, 고정하지 않으면 ruff 를 올리는 것만으로 기존 코드 수백 건이 뜬다(0.16 에서 겪었다).
여기서 보는 것은 **파싱 가능 여부 하나**이고 문체 규칙이 아니다.

`E4,E7,F` 는 **일부러 안 본다** — 저장소에 이미 45건이 있고(E402 30 · F401 5 · E731 4 ·
F841 3 · E702 3) 그것은 이 검사가 막으려는 결함과 다른 것이다. 그걸 같이 켜면 이 검사는
첫날부터 빨간불이라 아무도 안 본다.

ruff 가 없으면 **조용히 통과하지 않는다** — 건너뛴 이유를 이름으로 남긴다.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 이 저장소가 지원한다고 적어 둔 최저 버전. `docs/setup.md` 가 소유한다.
TARGET = "py311"
# 구문 오류만 본다. 문체는 이 검사의 일이 아니다.
SELECT = "E9"
# 팀 C 의 보고서·조사 스크립트, 후보, 공용 도구.
TREES = ["reports/team-c", "experiments", "tools", "script.py"]


def ruff(*args):
    """설치된 ruff 를 모듈로 부른다. 없으면 `None` 을 돌려준다."""
    try:
        return subprocess.run([sys.executable, "-m", "ruff", *args],
                              capture_output=True, text=True,
                              encoding="utf-8", errors="replace", cwd=ROOT)
    except OSError:
        return None


class ParsesOnTheSupportedPython(unittest.TestCase):
    """지원 최저 버전에서 구문 오류 0건인가."""

    @classmethod
    def setUpClass(cls):
        probe = ruff("--version")
        if probe is None or probe.returncode != 0:
            # 조용히 통과시키지 않는다. 왜 안 봤는지가 남아야 한다.
            raise unittest.SkipTest(
                "ruff 가 없다 — `py -m pip install ruff` 뒤에 다시 돌린다. "
                "이 검사는 3.11 파싱 회귀를 막는 유일한 자리다")
        cls.version = probe.stdout.strip()

    def test_no_syntax_errors_on_the_supported_python(self):
        result = ruff("check", "--isolated", "--target-version", TARGET,
                      "--select", SELECT, *TREES)
        self.assertIsNotNone(result)
        self.assertEqual(
            result.returncode, 0,
            "지원 환경(Python 3.11)에서 파싱 안 되는 파일이 있다. "
            "f-string 안에서 바깥과 같은 따옴표를 다시 쓰지 않았는지 본다 — "
            f"그 문법은 3.12 부터다.\n{result.stdout}\n{result.stderr}")

    def test_the_guard_actually_catches_a_312_only_file(self):
        """**이 검사가 진짜로 잡는지 본다.** 안 잡는 검사는 없는 것과 같다."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "only_on_312.py"
            # PEP 701 — f-string 안에서 바깥과 같은 따옴표. 3.11 에서는 파싱 실패.
            bad.write_text('row = {"a": 1}\nprint(f"{row["a"]}")\n', encoding="utf-8")
            result = ruff("check", "--isolated", "--target-version", TARGET,
                          "--select", SELECT, str(bad))
            self.assertIsNotNone(result)
            self.assertNotEqual(result.returncode, 0,
                                "3.12 전용 문법을 안 잡는다 — 이 검사는 아무것도 못 막는다")
            self.assertIn("invalid-syntax", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
