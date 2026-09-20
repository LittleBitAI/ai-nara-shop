"""회차 진단 화면을 띄운다. report.cmd 와 report.command 가 부르는 한 곳이다.

런처 두 개가 순서 로직을 나눠 가지면 한쪽만 고쳐지고 갈린다. 배치 파일과 셸
스크립트는 파이썬 찾는 일까지만 하고, 그다음은 전부 여기다.

    python -X utf8 tools/report.py              받은 함의 최근 ZIP을 채점하고 띄운다
    python -X utf8 tools/report.py --all        등록된 회차 전부 다시 만들고 띄운다
    python -X utf8 tools/report.py --run <id>   그 회차만

붙는 인자는 그대로 tools/build_report.py 로 넘어간다. ZIP 파일명은 회차마다
바뀌므로 어디에도 적지 않는다. 인자가 없으면 --latest 가 고른다.
"""

import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
INDEX = WEB / "public/runs/index.json"
BUILD = ROOT / "tools/build_report.py"


def npm_command(args):
    """Windows 의 npm 은 npm.cmd 다. CreateProcess 가 배치 파일을 직접 못 띄우므로
    거기서만 cmd.exe 를 앞에 세운다. shell=True 는 인자에 공백이 있으면 깨진다."""
    exe = shutil.which("npm")
    if exe is None:
        raise SystemExit("npm 이 없다. Node.js 를 먼저 깐다: https://nodejs.org")
    if os.name == "nt":
        return [os.environ.get("COMSPEC", "cmd.exe"), "/c", exe, *args]
    return [exe, *args]


def build(args):
    return subprocess.run([sys.executable, "-X", "utf8", str(BUILD), *args], cwd=ROOT).returncode


def say(message):
    """파이프로 받을 때도 자식 출력과 순서가 맞게 바로 내보낸다."""
    print(message, flush=True)


def main(argv):
    if not WEB.is_dir():
        raise SystemExit(f"{WEB} 가 없다. 저장소 루트에서 실행한다")

    # 띄우는 단계만 뺀다. 런처 두 개가 저장소를 제대로 찾는지 검사가 이걸로 확인한다.
    serve = "--no-serve" not in argv
    passthrough = [a for a in argv if a != "--no-serve"] or ["--latest"]

    say(f"[1/3] 채점한다 — build_report.py {' '.join(passthrough)}")
    if build(passthrough):
        say("      건너뛴다. 이미 만든 회차로 화면만 띄운다.")

    if not INDEX.exists():
        say("      화면이 읽을 회차 목록이 없다. 등록된 회차 전부로 채운다.")
        if build(["--all"]):
            raise SystemExit("회차를 하나도 못 만들었다. 위 오류를 먼저 본다.")

    say("[2/3] web 의존성을 확인한다")
    if not (WEB / "node_modules").is_dir():
        say("      npm install — 처음 한 번만 걸린다.")
        if subprocess.run(npm_command(["install"]), cwd=WEB).returncode:
            raise SystemExit("npm install 이 실패했다.")

    if not serve:
        say("[3/3] --no-serve 라 여기서 멈춘다. 저장소는 제대로 찾았다.")
        return 0
    say("[3/3] 화면을 띄운다. 끄려면 이 창에서 Ctrl+C.")
    return subprocess.run(npm_command(["run", "dev", "--", "--open"]), cwd=WEB).returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        raise SystemExit(0)
