"""공용 위키 설치 도구에 이 checkout을 전달한다."""

import argparse
from pathlib import Path
import subprocess
import sys


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki", required=True, type=Path, help="공용 위키 checkout 경로")
    parser.add_argument("--agent", choices=("claude", "codex", "both"), default="both")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--allow-dirty-wiki", action="store_true", help="미커밋 위키 개발 검증 전용")
    args = parser.parse_args()
    script = args.wiki.expanduser().resolve() / "tool/setup_agents.py"
    if not script.is_file():
        print(f"공용 설치 도구가 없습니다: {script}. 공용화를 포함한 위키 버전을 지정하세요.", file=sys.stderr)
        return 2
    command = [sys.executable, "-X", "utf8", str(script), "--project",
               str(Path(__file__).resolve().parents[1]), "--agent", args.agent]
    if args.check:
        command.append("--check")
    if args.allow_dirty_wiki:
        command.append("--allow-dirty-wiki")
    return subprocess.run(command).returncode


if __name__ == "__main__":
    raise SystemExit(main())
