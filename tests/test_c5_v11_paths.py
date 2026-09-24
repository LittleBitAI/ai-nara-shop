"""C5 조사 스크립트가 **근거를 조용히 갈아치우지 않는가**.

리뷰 [P2] 가 잡은 것: 스크립트가 작업 트리의 `script.py` 를 불러 쓰고 추적 파일
`paths.json` 을 **늘 덮어썼다.** 그러면 판정 코드가 바뀐 뒤에 문서에 적힌 명령을 그대로
돌리기만 해도, **보고서의 기준 commit·Macro 는 그대로인 채 근거 수만 바뀐다.**
다음 사람은 그 JSON 을 §1 의 코드가 낸 것으로 읽는다.

이 검사가 고정하는 것 넷.
  1. 판정 코드가 `BASE_REV` 로 **고정**돼 있고 작업 트리 판을 안 쓴다
  2. `BASE_REV` 가 보고서 §1 의 기준 commit 과 **같다**
  3. 다른 커밋으로 돌리면 `paths.json` 을 **안 덮는다**
  4. 고정 커밋으로 돌리면 보관된 산출물과 **같은 수**가 나온다

모델을 부르지 않는다.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FOLDER = ROOT / "reports/team-c/c5-v11-paths"
SAVED = FOLDER / "paths.json"
REPORT = FOLDER / "README.md"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


paths = load_module("c5_v11_paths", FOLDER / "paths.py")


class PinnedCode(unittest.TestCase):
    """판정 코드가 커밋에 묶여 있는가."""

    def test_the_script_does_not_read_the_working_tree_script(self):
        source = (FOLDER / "paths.py").read_text(encoding="utf-8")
        self.assertNotIn('load("submission", ROOT / "script.py")', source,
                         "작업 트리의 script.py 를 부르면 main 이 움직일 때 수가 바뀐다")
        self.assertIn("BASE_REV", source)

    def test_the_pin_matches_the_report(self):
        """보고서 §1 의 기준 commit 과 어긋나면 둘 중 하나가 낡은 것이다.

        `**` 를 선택으로 둔다 — 이 저장소에는 강조 표기를 걷어내는 정리 작업이 있고,
        그것이 이 파일에 오면 `**` 를 요구하는 정규식은 "못 찾았다" 로 헛되이 죽는다.
        """
        found = re.search(r"기준 commit \| (?:\*\*)?`([0-9a-f]{7,40})`",
                          REPORT.read_text(encoding="utf-8"))
        self.assertIsNotNone(found, "README §1 에서 기준 commit 을 못 찾았다")
        self.assertTrue(paths.BASE_REV.startswith(found[1]) or found[1].startswith(paths.BASE_REV),
                        f"BASE_REV {paths.BASE_REV} 와 보고서 {found[1]} 이 다르다")

    def test_the_saved_result_records_its_code(self):
        saved = json.loads(SAVED.read_text(encoding="utf-8"))
        self.assertIn("code_commit", saved)
        self.assertTrue(saved["code_commit"].startswith(paths.BASE_REV))


class RefusesToOverwrite(unittest.TestCase):
    """다른 코드의 수로 보관 산출물을 덮지 않는가. 리뷰 [P2] 의 핵심."""

    @classmethod
    def setUpClass(cls):
        if shutil.which("git") is None:
            raise unittest.SkipTest("git 이 없다")
        if not (ROOT / "reports/runs/colab-1789902969401579900/dev-debug"
                / "diagnostics.jsonl").is_file():
            raise unittest.SkipTest("보관 회차가 없다")

    def run_with(self, rev):
        before = SAVED.read_bytes()
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", str(FOLDER / "paths.py"), "--rev", rev],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return before, SAVED.read_bytes(), proc

    def test_a_different_commit_leaves_the_file_alone(self):
        # 이 폴더의 첫 판이 쓰던 베이스. 그때도 v11 수는 같았지만 코드는 다르다.
        before, after, proc = self.run_with("788c7df")
        self.assertEqual(before, after, "다른 코드의 수로 보관 산출물을 덮었다")
        self.assertIn("덮어쓰지 않았다", proc.stderr)

    def test_the_pinned_commit_reproduces_the_saved_result(self):
        before, after, _proc = self.run_with(paths.BASE_REV)
        self.assertEqual(before, after, "고정 커밋인데 산출물이 달라졌다")


if __name__ == "__main__":
    unittest.main()
