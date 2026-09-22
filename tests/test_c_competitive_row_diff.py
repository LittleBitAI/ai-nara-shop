"""B1 `competitive_row` diff 의 회귀 검사.

리뷰 [P1] 이 잡은 것: 새 필드를 무조건 필수로 만들면 **보관 회차 재생이 죽는다**
(`company_size: 사실 필드 결손`). 보관된 옛 원응답에는 그 필드가 없기 때문이다.

이 검사가 고정하는 것 넷.
  1. diff 를 **적용하지 않은** 저장소 코드로 보관 회차를 재생하면 HEAD 재생과 바이트 동일
  2. diff 를 **적용한** 코드로 재생해도 **같은 바이트**. 구 회차의 동작이 안 바뀐다
  3. 새(비-legacy) 경로에서는 `competitive_row` 가 **필수**다
  4. 검증 실패 시 `scope` 는 `unknown` 이고 **`general` 로 뒤집지 않는다**

모델을 부르지 않는다. diff 는 임시 사본에만 적용하고 저장소의 `script.py` 는 건드리지 않는다.
"""

from __future__ import annotations

import importlib.util
import json
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
DIFF = ROOT / "reports/team-c/b1-competitive-row/competitive-row.diff"
DEV = ROOT / "open/dev.jsonl"
DATA = ROOT / "open/data"


def load_module(name, path):
    """`sys.path` 를 고친 뒤 실어야 하므로 모듈 최상단 import 를 쓰지 않는다."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def replay_to(script_path: str, out_dir: Path) -> bytes:
    """그 코드로 보관 회차를 재생하고 제출 CSV 바이트를 돌려준다."""
    tools = Path(script_path).parent / "tools" / "replay_run.py"
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", str(tools),
         "--case", str(CASE), "--script", str(script_path),
         "--data-dir", str(DATA), "--input", str(DEV), "--output-dir", str(out_dir)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise AssertionError(f"재생 실패 rc={proc.returncode}\n{proc.stdout}\n{proc.stderr}")
    return (out_dir / "submission.csv").read_bytes()


class DiffApplies(unittest.TestCase):
    """diff 자체의 계약."""

    def test_diff_applies_cleanly_to_the_repository(self):
        proc = subprocess.run(["git", "apply", "--check", str(DIFF)],
                              cwd=ROOT, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_diff_is_not_applied_to_the_repository(self):
        """운영 코드는 그대로여야 한다. diff 로만 남긴다."""
        source = (ROOT / "script.py").read_text(encoding="utf-8")
        self.assertNotIn("COMPETITIVE_ROW_PATTERN", source)
        self.assertNotIn("competitive_row", (ROOT / "tools/replay_run.py").read_text(encoding="utf-8"))


class ArchivedReplayUnchanged(unittest.TestCase):
    """보관 회차 재생이 diff 적용 전후로 **바이트 동일**한가. 리뷰 [P1] 의 핵심."""

    @classmethod
    def setUpClass(cls):
        if not (CASE / "diagnostics.jsonl").is_file():
            raise unittest.SkipTest(f"{CASE} 가 없다")
        if shutil.which("git") is None:
            raise unittest.SkipTest("git 이 없다")
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.plain = root / "plain"
        cls.patched = root / "patched"
        for dst in (cls.plain, cls.patched):
            (dst / "tools").mkdir(parents=True)
            shutil.copy2(ROOT / "script.py", dst / "script.py")
            shutil.copy2(ROOT / "tools/replay_run.py", dst / "tools/replay_run.py")
        proc = subprocess.run(["git", "apply", "-p1", str(DIFF)],
                              cwd=cls.patched, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            raise AssertionError(f"사본에 diff 적용 실패\n{proc.stderr}")
        cls.before = replay_to(str(cls.plain / "script.py"), root / "out-plain")
        cls.after = replay_to(str(cls.patched / "script.py"), root / "out-patched")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_patched_code_still_replays_the_archived_run(self):
        """적용 후에도 재생이 죽지 않는다. 죽으면 setUpClass 에서 이미 터진다."""
        self.assertTrue(self.after)

    def test_archived_replay_is_byte_identical(self):
        self.assertEqual(self.before, self.after,
                         "diff 적용이 보관 회차 재생을 바꿨다 — 구 회차에 새 필드를 소급한 것이다")

    def test_archived_run_has_no_competitive_row_setting(self):
        """구 회차 설정에 이 키가 없어야 legacy 경로가 발동한다 — 전제를 고정한다."""
        settings = json.loads((CASE / "run_report.json").read_text(encoding="utf-8"))
        settings = settings["reproduction"]["settings"]
        self.assertNotIn("company_size_competitive_row", settings)


class PatchedSchemaContract(unittest.TestCase):
    """적용된 코드에서 새 경로의 계약이 유지되는가."""

    @classmethod
    def setUpClass(cls):
        if shutil.which("git") is None:
            raise unittest.SkipTest("git 이 없다")
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        (root / "tools").mkdir(parents=True)
        shutil.copy2(ROOT / "script.py", root / "script.py")
        shutil.copy2(ROOT / "tools/replay_run.py", root / "tools/replay_run.py")
        proc = subprocess.run(["git", "apply", "-p1", str(DIFF)], cwd=root,
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            raise AssertionError(proc.stderr)
        cls.script = load_module("patched_submission", root / "script.py")

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop("patched_submission", None)
        cls.tmp.cleanup()

    def test_new_path_requires_competitive_row(self):
        props = self.script.company_size_schema()["properties"]
        self.assertIn("competitive_row", props)
        self.assertIn("competitive_row", self.script.company_size_schema()["required"])

    def test_legacy_and_flag_off_paths_omit_it(self):
        """보관 회차가 타는 두 경로. 여기에 넣으면 재생이 죽는다."""
        self.assertNotIn("competitive_row",
                         self.script.company_size_schema(legacy=True)["properties"])
        self.assertNotIn("competitive_row",
                         self.script.company_size_schema(competitive_row=False)["properties"])

    def test_old_facts_without_the_field_are_not_judged(self):
        """필드가 없으면 `None` — 구 회차의 동작을 바꾸지 않는다."""
        self.assertIsNone(self.script.verified_competitive_row({"scope": "competitive"}, {}, ""))

    def test_null_row_fails_verification(self):
        self.assertIs(self.script.verified_competitive_row(
            {"scope": "competitive", "competitive_row": None}, {}, ""), False)

    def test_scope_becomes_unknown_never_general(self):
        """검증 실패 시 `unknown` 이다. `general` 로 뒤집으면 v10~v13 TP 가 죽는다."""
        script = self.script
        seen = {}
        original = script._company_size_bands

        def spy(facts, rec, max_chars):
            seen.update(facts)
            return {}, "unverified_scope"

        script._company_size_bands = spy
        try:
            rec = {"id": "T", "docs": [{"type": "공고문", "doc_id": "D0", "text": "본문"}],
                   "input_completeness": {"완전관측": True}, "meta": {}}
            facts = {"scope": "competitive", "scope_quote": None, "competitive_row": None,
                     "qualification": "unknown", "qualification_quote": None}
            script.verify_company_size(facts, rec, 16000)
        finally:
            script._company_size_bands = original
        self.assertEqual(seen.get("scope"), "unknown")
        self.assertNotEqual(seen.get("scope"), "general")


if __name__ == "__main__":
    unittest.main()
