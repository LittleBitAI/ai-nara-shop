"""대회용 로컬 Langfuse 스택을 띄우고, 필요할 때만 터널로 팀에 연다.

같은 기계에서 도는 다른 프로젝트의 Langfuse 와 **다른 인스턴스**다. 이 스택은
Colab 수집 때문에 터널로 밖에 열리고, 팀원이 받는 주소에는 대회 자료만 있어야
한다. 무료 셀프호스트에는 프로젝트 단위 역할이 없으므로 인스턴스를 가른다.

    python -X utf8 tools/langfuse_local.py up      # 띄운다. UI 는 localhost:3002
    python -X utf8 tools/langfuse_local.py keys    # Colab 에 넣을 세 줄
    python -X utf8 tools/langfuse_local.py share   # cloudflared 로 팀에 연다
    python -X utf8 tools/langfuse_local.py down    # 내린다. 트레이스는 볼륨에 남는다
    python -X utf8 tools/langfuse_local.py reset    # 볼륨까지 지운다
"""

from __future__ import annotations

import argparse
import re
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

STACK_DIR = Path(__file__).resolve().parent.parent / "docker" / "langfuse"
PROJECT = "langfuse-nara"
WEB_PORT = 3002
LOCAL_URL = f"http://localhost:{WEB_PORT}"
TUNNEL = re.compile(rb"https://[a-z0-9][a-z0-9-]*\.trycloudflare\.com")

# `.env.example` 의 자리표시자와 그 자리에 넣을 값의 종류.
# `hex32` 는 `openssl rand -hex 32` 와 같다 - ENCRYPTION_KEY 는 정확히 64 hex 여야 한다.
PLACEHOLDERS = {
    "CHANGEME_NEXTAUTH_SECRET": "hex32",
    "CHANGEME_SALT": "hex32",
    "CHANGEME_ENCRYPTION_KEY": "hex32",
    "CHANGEME_POSTGRES_PASSWORD": "token",
    "CHANGEME_CLICKHOUSE_PASSWORD": "token",
    "CHANGEME_REDIS_PASSWORD": "token",
    "CHANGEME_MINIO_PASSWORD": "token",
    "CHANGEME_INIT_SECRET": "secret_key",
    "CHANGEME_INIT_PASSWORD": "token",
}


def _value(kind: str) -> str:
    if kind == "hex32":
        return secrets.token_hex(32)
    if kind == "secret_key":
        return "sk-lf-" + secrets.token_hex(16)
    return secrets.token_urlsafe(24)


def ensure_env() -> Path:
    """첫 기동에만 `.env` 를 만든다. 이미 있으면 손대지 않는다.

    POSTGRES_PASSWORD 는 initdb 때 한 번만 쓰인다. 볼륨이 남은 채로 `.env` 만
    새로 만들면 새 비밀번호로 옛 DB 에 붙으려다 죽으므로, 다시 만들 때는
    `reset` 을 같이 해야 한다.
    """
    env = STACK_DIR / ".env"
    if env.exists():
        return env
    text = (STACK_DIR / ".env.example").read_text(encoding="utf-8")
    for placeholder, kind in PLACEHOLDERS.items():
        # 같은 자리표시자가 여러 줄에 나오면 **같은 값**이어야 한다.
        # MinIO 비밀번호가 세 줄에 걸쳐 있고 셋이 갈리면 업로드가 죽는다.
        if placeholder in text:
            text = text.replace(placeholder, _value(kind))
    env.write_bytes(text.encode("utf-8"))
    print(f"[langfuse] 첫 기동. 비밀값을 {env} 에 썼다. 이 파일은 git-ignore 된다.")
    return env


def read_env(env: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in env.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, _, value = stripped.partition("=")
            values[key.strip()] = value.strip()
    return values


def set_env_value(env: Path, key: str, value: str) -> None:
    lines = env.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    env.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))


def compose(*args: str) -> int:
    return subprocess.call(["docker", "compose", "--project-name", PROJECT, *args], cwd=STACK_DIR)


def print_keys(env: Path, host: str = LOCAL_URL) -> None:
    values = read_env(env)
    print(f"LANGFUSE_HOST={host}")
    print(f"LANGFUSE_PUBLIC_KEY={values.get('LANGFUSE_INIT_PROJECT_PUBLIC_KEY', '')}")
    print(f"LANGFUSE_SECRET_KEY={values.get('LANGFUSE_INIT_PROJECT_SECRET_KEY', '')}")


def up() -> int:
    if subprocess.call(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL):
        print("[langfuse] Docker 데몬이 응답하지 않는다. Docker Desktop 을 먼저 켜라.")
        return 1
    env = ensure_env()
    code = compose("up", "-d")
    if code:
        return code
    print(f"[langfuse] UI: {LOCAL_URL}  (계정은 docker/langfuse/.env 의 INIT_USER 줄)")
    print_keys(env)
    return 0


def share() -> int:
    """cloudflared 임시 터널을 열고 그 주소로 웹 컨테이너를 다시 만든다.

    NextAuth 는 브라우저가 실제로 쓰는 주소와 `NEXTAUTH_URL` 이 다르면 로그인을
    거부한다. 임시 터널 주소는 띄워 봐야 알 수 있으므로 순서가 이렇게 된다.
    """
    if shutil.which("cloudflared") is None:
        print("[langfuse] cloudflared 가 없다.")
        return 1
    env = ensure_env()
    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", LOCAL_URL],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    url = ""
    try:
        assert proc.stdout is not None
        for raw in proc.stdout:
            sys.stdout.buffer.write(raw)
            sys.stdout.flush()
            found = TUNNEL.search(raw)
            if found and not url:
                url = found.group().decode()
                set_env_value(env, "NEXTAUTH_URL", url)
                # 이 재생성이 끝나야 팀원이 로그인할 수 있다.
                compose("up", "-d", "--force-recreate", "langfuse-web")
                print("\n[langfuse] 팀원에게 줄 주소: " + url)
                print("[langfuse] Colab 에 넣을 세 줄:")
                print_keys(env, url)
                print("[langfuse] 이 창을 닫으면 터널이 끊긴다. Ctrl+C 로 끝낸다.\n")
        proc.wait()
    except KeyboardInterrupt:
        pass
    finally:
        proc.terminate()
        if url:
            set_env_value(env, "NEXTAUTH_URL", LOCAL_URL)
            compose("up", "-d", "--force-recreate", "langfuse-web")
            print(f"[langfuse] 터널을 닫고 {LOCAL_URL} 로 되돌렸다.")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["up", "down", "reset", "keys", "share"])
    args = parser.parse_args(argv)

    if args.command == "up":
        return up()
    if args.command == "down":
        return compose("down")
    if args.command == "reset":
        print("[langfuse] 볼륨을 버린다. 지금까지 모은 트레이스가 사라진다.")
        return compose("down", "--volumes")
    if args.command == "keys":
        print_keys(ensure_env())
        return 0
    return share()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
