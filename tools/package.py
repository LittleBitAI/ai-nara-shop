"""T1 제출 ZIP을 두 파일로 만들고 압축 해제한 코드의 mock 입출력을 확인한다."""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = ("script.py", "requirements.txt")


def package(output):
    if output.exists():
        raise ValueError("기존 ZIP은 덮어쓰지 않는다. 새 출력 경로를 사용하세요")
    sources = {name: (ROOT / name).read_bytes() for name in FILES}
    for name, content in sources.items():
        content.decode("utf-8")
        if content.startswith(b"\xef\xbb\xbf") or b"\r" in content:
            raise ValueError(f"{name}: UTF-8 without BOM·LF 위반")
    compile(sources["script.py"], "script.py", "exec")
    # ponytail: 첫 제출은 추가 의존성 없음. 도입 시 고정 패키지 제한과 설치 검사를 확장한다.
    if any(line.strip() and not line.lstrip().startswith("#")
           for line in sources["requirements.txt"].decode("utf-8").splitlines()):
        raise ValueError("T1 패키지는 추가 의존성이 없어야 한다")
    with tempfile.TemporaryDirectory(prefix="t1-package-") as temporary:
        staging = Path(temporary)
        archive = staging / "submit.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            for name, content in sources.items():
                info = zipfile.ZipInfo(name, (2026, 9, 16, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, content)
        extracted = staging / "extracted"
        with zipfile.ZipFile(archive) as z:
            if z.namelist() != list(FILES) or z.testzip() is not None:
                raise ValueError("ZIP 구성/CRC 오류")
            if sum(i.file_size for i in z.infolist()) > 8_000_000_000:
                raise ValueError("압축 해제 후 8GB 초과")
            z.extractall(extracted)  # 위에서 직접 만든 고정 allowlist만 포함한다.
        env = {**os.environ, "PPS_DATA_DIR": str(ROOT / "open/data"),
               "PPS_OUTPUT_DIR": str(staging / "mock"), "PYTHONDONTWRITEBYTECODE": "1",
               "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
        command = [sys.executable, "-X", "utf8", "script.py", "--mock"]
        completed = subprocess.run(command, cwd=extracted, env=env, capture_output=True,
                                   text=True, encoding="utf-8", timeout=60)
        if completed.returncode:
            raise RuntimeError(f"압축 해제 mock 실패: {completed.stderr}")
        raw = (staging / "mock/submission.csv").read_bytes()
        if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
            raise ValueError("CSV 인코딩/줄바꿈 오류")
        with (staging / "mock/submission.csv").open(encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f))
        expected_header = ["id"] + [f"v{i}" for i in range(1, 25)] + [f"e{i}" for i in range(1, 25)]
        if rows[0] != expected_header or len(rows) != 11 or any(len(row) != 49 for row in rows):
            raise ValueError("공식 샘플 10건·49열 검사 실패")
        runtime = json.loads((staging / "mock/run_report.json").read_text(encoding="utf-8"))
        if runtime["mode"] != "mock" or runtime["model_success_count"] != 0:
            raise ValueError("mock/live 표시 오류")
        # python script.py 기본 진입은 모델 경로 없을 때 실패해야 한다. mock으로 대체되면 안 된다.
        env["PPS_OUTPUT_DIR"] = str(staging / "no-model")
        env["PPS_MODEL_DIR"] = str(staging / "model-not-provided")
        default = subprocess.run(command[:-1], cwd=extracted, env=env, capture_output=True,
                                 text=True, encoding="utf-8", timeout=30)
        if default.returncode == 0 or (staging / "no-model/submission.csv").exists():
            raise ValueError("모델 없는 기본 진입이 성공 처리됐다")
        content = archive.read_bytes()
        if len(content) > 2_000_000_000:
            raise ValueError("ZIP 2GB 초과")
        manifest = {
            "artifact_id": "t1-submit", "version": 1, "status": "draft",
            "run_id": "t1-baseline", "model": None, "prompt_hash": None,
            "parents": [], "reviewer": None, "reviewed_at": None, "decision": None,
            "mode": "package_validation_mock", "live_verified": False, "server_submitted": False,
            "archive": {"path": output.as_posix(), "bytes": len(content),
                        "sha256": hashlib.sha256(content).hexdigest()},
            "sources": [{"path": name, "sha256": hashlib.sha256(data).hexdigest()}
                        for name, data in sources.items()],
            "generator": {"path": "tools/package.py", "argv": sys.argv,
                          "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
            "environment": {"python": platform.python_version(), "platform": platform.platform()},
            "checks": {"root_allowlist": list(FILES), "extracted_mock_rows": len(rows) - 1,
                       "columns": 49, "utf8_no_bom_lf": True, "default_requires_model": True},
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as f:
            f.write(content)
        output.with_suffix(".manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/baseline/submit.zip")
    args = parser.parse_args()
    try:
        manifest = package(args.output)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        parser.exit(1, f"error: {exc}\n")
    print(json.dumps(manifest["archive"], ensure_ascii=False))
    print("ZIP 검증 PASS (압축 해제 mock 10건·49열). 실제 모델·서버 제출 미검증.")


if __name__ == "__main__":
    main()
