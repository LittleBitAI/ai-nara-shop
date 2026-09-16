"""고정 위키 커밋과 설치 CLI를 임시 checkout에서 검증한다. 호스트 자동 실행 검사는 아니다."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest

PROJECT = Path(__file__).resolve().parents[1]
WIKI = None  # 실행 시 --wiki로 명시한다.


def run(command, cwd, env, **kwargs):
    return subprocess.run(command, cwd=cwd, env=env, capture_output=True,
                          text=True, encoding="utf-8", timeout=60, **kwargs)


class SetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="team setup 한글 ")
        cls.root = Path(cls.temp.name)
        cls.wiki = cls.root / "공용 wiki"
        cls.env = {**os.environ, "HOME": str(cls.root / "home"),
                   "USERPROFILE": str(cls.root / "home"),
                   "CODEX_HOME": str(cls.root / "home/.codex"),
                   "CLAUDE_CONFIG_DIR": str(cls.root / "home/.claude"),
                   "LOCALAPPDATA": str(cls.root / "local-app-data"),
                   "PYTHONDONTWRITEBYTECODE": "1"}
        cls.global_config = cls.root / "home/.codex/config.toml"
        cls.global_config.parent.mkdir(parents=True)
        cls.global_config.write_bytes(b'# keep user settings\n[features]\nhooks = true\n')
        cls.global_hooks = cls.global_config.with_name("hooks.json")
        cls.global_hooks.write_bytes(b'{"hooks":{}}\n')
        cloned = run(["git", "clone", "--quiet", "--no-hardlinks", "--no-checkout",
                      str(WIKI), str(cls.wiki)], cls.root, cls.env)
        assert cloned.returncode == 0, cloned.stderr
        revision = (PROJECT / ".wiki/wiki-revision").read_text(encoding="utf-8").strip()
        checked = run(["git", "-c", "core.autocrlf=false", "checkout", "--quiet", "--detach", revision],
                      cls.wiki, cls.env)
        assert checked.returncode == 0, checked.stderr
        cls.hub_adapters = {p.name: p.read_bytes() for p in (cls.wiki / "adapters").glob("*.toml")}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def project(self, name):
        project = self.root / name / "같은 checkout"
        project.mkdir(parents=True)
        for relative in ("tools/setup_agents.py", ".wiki/adapter.toml", ".wiki/wiki-revision",
                         ".wiki/project.md", ".wiki/plan-active.md", ".codex/config.toml",
                         ".gitignore", "AGENTS.md", "CLAUDE.md", "README.md"):
            target = project / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(PROJECT / relative, target)
        shutil.copytree(PROJECT / "docs", project / "docs")
        adapter = project / ".wiki/adapter.toml"
        adapter.write_text(adapter.read_text(encoding="utf-8").replace("artifacts/review", f"artifacts/{name}/review"),
                           encoding="utf-8", newline="\n")
        (project / ".wiki/checkout.md").write_text(
            '---\nseverity: contract\ntriggers: [프로젝트]\n---\n# 격리 검사\n규칙. {review_dir}\n',
            encoding="utf-8", newline="\n")
        result = run(["git", "init", "--quiet"], project, self.env)
        self.assertEqual(result.returncode, 0, result.stderr)
        # Stop을 직접 실행해도 gh/원격 이력을 조회하지 않는다.
        (project / ".wiki/.sync").write_text(str(time.time()), encoding="utf-8")
        return project

    def setup_cli(self, project, *args, allow_dirty=False):
        return run([sys.executable, "-X", "utf8", "tools/setup_agents.py",
                    "--wiki", str(self.wiki), *( ["--allow-dirty-wiki"] if allow_dirty else []),
                    *args], project, self.env)

    def test_install_and_failure_contracts(self):
        for choice in ("claude", "codex", "both"):
            with self.subTest(agent=choice):
                project = self.project("프로젝트 " + choice)
                paths = {"claude": project / ".claude/settings.json", "codex": project / ".codex/hooks.json"}
                user = {"permissions": {"allow": ["Bash(git status*)"], "deny": ["Read(secret)"]},
                        "hooks": {"SessionEnd": [{"hooks": [{"type": "command", "command": "echo keep"}]}]},
                        "user_note": "한글 보존"}
                for path in paths.values():
                    path.parent.mkdir(exist_ok=True)
                    path.write_text(json.dumps(user, ensure_ascii=False), encoding="utf-8", newline="\n")
                before = {key: path.read_bytes() for key, path in paths.items()}
                adapter_before = (project / ".wiki/adapter.toml").read_bytes()
                fresh = self.setup_cli(project, "--agent", choice, "--check")
                self.assertEqual(fresh.returncode, 2, fresh.stdout + fresh.stderr)
                self.assertEqual(before, {key: path.read_bytes() for key, path in paths.items()})
                self.assertFalse((project / ".wiki/installed-agents.json").exists())
                result = self.setup_cli(project, "--agent", choice)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                selected = ("claude", "codex") if choice == "both" else (choice,)
                installed = {key: path.read_bytes() for key, path in paths.items()}
                for key, path in paths.items():
                    if key not in selected:
                        self.assertEqual(installed[key], before[key])
                        continue
                    self.assertNotIn(b"\r", installed[key])
                    self.assertFalse(installed[key].startswith(b"\xef\xbb\xbf"))
                    config = json.loads(installed[key])
                    for field in ("user_note", "permissions"):
                        if field == "permissions" and key == "claude":
                            self.assertEqual(config[field]["allow"], user[field]["allow"])
                            self.assertIn("Read(secret)", config[field]["deny"])
                        else:
                            self.assertEqual(config[field], user[field])
                    self.assertEqual(config["hooks"]["SessionEnd"], user["hooks"]["SessionEnd"])
                    self.execute_hooks(project, key, config)
                again = self.setup_cli(project, "--agent", choice)
                self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
                self.assertEqual(installed, {key: path.read_bytes() for key, path in paths.items()})
                check = self.setup_cli(project, "--agent", choice, "--check")
                self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
                lint = run([sys.executable, str(self.wiki / "tool/repo_lint.py"), "--repo", str(project)], project, self.env)
                self.assertEqual(lint.returncode, 0, lint.stdout + lint.stderr)
                ignored = run(["git", "check-ignore", ".claude/settings.json", ".codex/hooks.json",
                               ".wiki/trajectory.jsonl", ".wiki/corpus.json", ".wiki/installed-agents.json"], project, self.env)
                self.assertEqual(len(ignored.stdout.splitlines()), 5)
                self.assertEqual(self.global_config.read_bytes(), b'# keep user settings\n[features]\nhooks = true\n')
                self.assertEqual(self.global_hooks.read_bytes(), b'{"hooks":{}}\n')
                self.assertEqual((project / ".wiki/adapter.toml").read_bytes(), adapter_before)
                self.assertEqual(json.loads((project / ".wiki/installed-agents.json").read_bytes()), list(selected))

                # 두 번째 호스트를 추가해도 먼저 설치한 호스트를 지우거나 중복 생성하지 않는다.
                if choice == "claude":
                    added = self.setup_cli(project, "--agent", "codex")
                    self.assertEqual(added.returncode, 0, added.stdout + added.stderr)
                    self.assertEqual(paths["claude"].read_bytes(), installed["claude"])
                    self.assertEqual(json.loads((project / ".wiki/installed-agents.json").read_bytes()), ["claude", "codex"])

                moved = project.with_name("바뀐 폴더 이름")
                project.rename(moved)
                stale = self.setup_cli(moved, "--agent", choice, "--check")
                self.assertEqual(stale.returncode, 2, stale.stdout + stale.stderr)
                fixed = self.setup_cli(moved, "--agent", choice)
                self.assertEqual(fixed.returncode, 0, fixed.stdout + fixed.stderr)
                for key in selected:
                    self.execute_hooks(moved, key, json.loads((moved / (".claude/settings.json" if key == "claude" else ".codex/hooks.json")).read_bytes()))

        self.assertEqual(self.hub_adapters, {p.name: p.read_bytes() for p in (self.wiki / "adapters").glob("*.toml")})
        # 동일 이름 checkout 둘을 교대로 재검사해 뒤 설치가 앞 슬롯을 바꾸지 않음을 확인한다.
        for choice in ("claude", "codex"):
            project = self.root / ("프로젝트 " + choice) / "바뀐 폴더 이름"
            result = self.setup_cli(project, "--agent", choice, "--check")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.execute_hooks(project, choice, json.loads((project / (".claude/settings.json" if choice == "claude" else ".codex/hooks.json")).read_bytes()))

        # 실패는 설정 쓰기 이전이거나 원래 바이트로 복구해야 한다.
        project = self.project("오류 project")
        bad_path = self.setup_cli(project, "--wiki", str(self.root / "없는 위키"))
        self.assertEqual(bad_path.returncode, 2, bad_path.stdout + bad_path.stderr)
        no_yaml = run([sys.executable, "-S", str(self.wiki / "tool/setup_agents.py"),
                       "--project", str(project)], project, self.env)
        self.assertEqual(no_yaml.returncode, 2, no_yaml.stdout + no_yaml.stderr)
        self.assertIn("PyYAML", no_yaml.stdout + no_yaml.stderr)
        self.assertFalse((project / ".claude/settings.json").exists())

    def test_preflight_preserves_files(self):
        project = self.project("사전 검사")
        config = project / ".codex/config.toml"
        original = config.read_bytes()
        config.write_bytes(b'[features]\nhooks = false\n')
        failed = self.setup_cli(project, "--agent", "codex")
        self.assertEqual(failed.returncode, 2, failed.stdout + failed.stderr)
        self.assertIn("hooks = true", failed.stderr)
        self.assertEqual(config.read_bytes(), b'[features]\nhooks = false\n')
        config.write_bytes(original)
        target = project / ".claude/settings.json"
        target.parent.mkdir()
        target.write_bytes(b'{"disableAllHooks":true}\n')
        failed = self.setup_cli(project, "--agent", "claude")
        self.assertEqual(failed.returncode, 2, failed.stdout + failed.stderr)
        self.assertIn("disableAllHooks", failed.stderr)
        self.assertEqual(target.read_bytes(), b'{"disableAllHooks":true}\n')
        self.assertFalse((project / ".wiki/installed-agents.json").exists())
        adapter = project / ".wiki/adapter.toml"
        adapter.write_bytes(b'[invalid')
        failed = self.setup_cli(project, "--agent", "codex")
        self.assertEqual(failed.returncode, 2, failed.stdout + failed.stderr)
        self.assertEqual(adapter.read_bytes(), b'[invalid')
        self.assertFalse((project / ".codex/hooks.json").exists())
        unsafe = self.project("unsupported $path")
        failed = self.setup_cli(unsafe, "--agent", "claude")
        self.assertEqual(failed.returncode, 2, failed.stdout + failed.stderr)
        self.assertIn("지원하지 않는 문자", failed.stderr)
        self.assertFalse((unsafe / ".claude/settings.json").exists())
        project = self.project("오류 경계")
        dirty_source = self.wiki / "tool/setup-uncommitted-test.py"
        dirty_source.write_bytes(b'# uncommitted runtime change\n')
        try:
            dirty = self.setup_cli(project, allow_dirty=False)
        finally:
            dirty_source.unlink()
        self.assertEqual(dirty.returncode, 2, dirty.stdout + dirty.stderr)
        self.assertIn("고정 버전과 다른", dirty.stderr)

        (project / ".wiki/wiki-revision").write_text("0" * 40 + "\n", encoding="utf-8")
        mismatch = self.setup_cli(project)
        self.assertEqual(mismatch.returncode, 2)
        self.assertIn("버전 불일치", mismatch.stderr)
        shutil.copyfile(PROJECT / ".wiki/wiki-revision", project / ".wiki/wiki-revision")

        rollback = self.project("복구")
        target = rollback / ".claude/settings.json"
        target.parent.mkdir()
        limited = {"hooks": {"UserPromptSubmit": [{"matcher": "never", "hooks": [
            {"type": "command", "command": '"python" "old/tool/inject.py"'}]}]}}
        target.write_bytes(json.dumps(limited).encode("utf-8"))
        original_settings = target.read_bytes()
        original_adapter = (rollback / ".wiki/adapter.toml").read_bytes()
        failed_check = self.setup_cli(rollback, "--agent", "claude")
        self.assertEqual(failed_check.returncode, 2, failed_check.stdout + failed_check.stderr)
        self.assertEqual(target.read_bytes(), original_settings)
        self.assertEqual((rollback / ".wiki/adapter.toml").read_bytes(), original_adapter)
        self.assertFalse((rollback / ".wiki/installed-agents.json").exists())
        self.assertFalse((rollback / ".codex/hooks.json").exists())
        adapter = project / ".wiki/adapter.toml"
        original = adapter.read_bytes()
        adapter.write_bytes(original.replace(b'review_dir =', b'missing_review_dir ='))
        conflict = self.setup_cli(project)
        self.assertEqual(conflict.returncode, 2, conflict.stdout + conflict.stderr)
        self.assertIn("review_dir", conflict.stdout + conflict.stderr)
        self.assertIn(b'missing_review_dir', adapter.read_bytes())
        adapter.write_bytes(original)
        (project / ".codex/hooks.json").parent.mkdir(exist_ok=True)
        (project / ".codex/hooks.json").write_bytes(b'{broken')
        malformed = self.setup_cli(project)
        self.assertEqual(malformed.returncode, 2, malformed.stdout + malformed.stderr)
        self.assertEqual((project / ".codex/hooks.json").read_bytes(), b'{broken')
        self.assertFalse((project / ".claude/settings.json").exists())

    def execute_hooks(self, project, agent, config):
        spec = importlib.util.spec_from_file_location("setup_agents", self.wiki / "tool/setup_agents.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for event, groups in config["hooks"].items():
            for group in groups:
                for hook in group["hooks"]:
                    if "/tool/" not in hook["command"]:
                        continue
                    payload = {"session_id": "manual-team-setup-" + agent, "cwd": str(project),
                               "hook_event_name": event, "prompt": "프로젝트 작업을 진행해 주세요",
                               "source": "startup", "tool_name": "Bash",
                               "tool_input": {"command": "git status", "description": "상태 확인"},
                               "last_assistant_message": "검증을 마쳤습니다.", "stop_hook_active": False}
                    result = run([*module.hook_shell(agent), hook["command"]], project,
                                 {**self.env, "PYTHONIOENCODING": "cp949"}, input=json.dumps(payload, ensure_ascii=False))
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stderr, "")
                    answer = json.loads(result.stdout or "{}")
                    if event in ("UserPromptSubmit", "SessionStart"):
                        context = answer["hookSpecificOutput"]["additionalContext"]
                        self.assertIn("docs/tasks.md", context)
                        if event == "UserPromptSubmit":
                            expected = tomllib.loads((project / ".wiki/adapter.toml").read_text(encoding="utf-8"))["slots"]["review_dir"]
                            self.assertIn(expected, context)
                            self.assertNotIn("{review_dir}", context)
                            self.assertIn("docs/workflow.md", context)
                            self.assertIn("두 역할 모두 Claude 또는 Codex", context)
                    if "sync.py" in hook["command"]:
                        self.assertTrue((project / ".wiki/corpus.json").exists())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--wiki", type=Path, required=True)
    args = parser.parse_args()
    WIKI = args.wiki.resolve()
    unittest.main(argv=[sys.argv[0]], verbosity=2)
