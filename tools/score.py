"""49열 예측 CSV의 24항목 양성 F1을 ID로 대응해 채점한다. 모델 미사용."""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import sys
import tempfile
import time
import unicodedata

ITEMS = [f"v{i}" for i in range(1, 25)]
HEADER = ["id"] + ITEMS + [f"e{i}" for i in range(1, 25)]
ERROR_HEADER = ["id", "item", "true", "pred", "cause", "evidence_location", "owner", "note"]
ABSENCE = {10, 11, 16, 18, 20}


def load_csv(path):
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"{path}: UTF-8 BOM is not allowed")
    reader = csv.reader(io.StringIO(raw.decode("utf-8"), newline=""), strict=True)
    if next(reader, None) != HEADER:
        raise ValueError(f"{path}: expected header id,v1,...,v24,e1,...,e24 (49 columns)")
    records = {}
    for row in reader:
        location = f"{path}: line {reader.line_num}"
        if len(row) != len(HEADER):
            raise ValueError(f"{location}: expected 49 columns, got {len(row)}")
        identifier = row[0]
        if not identifier.strip():
            raise ValueError(f"{location}: empty ID")
        if identifier in records:
            raise ValueError(f"{location}: duplicate ID {identifier!r}")
        if any(not unicodedata.is_normalized("NFC", cell) for cell in row):
            raise ValueError(f"{location}: non-NFC cell (no automatic normalization)")
        for i, value in enumerate(row[1:25], 1):
            if value not in ("0", "1"):
                raise ValueError(f"{location}: v{i} must be 0 or 1, got {value!r}")
        for i, evidence in enumerate(row[25:], 1):
            if evidence and (row[i] == "0" or i in ABSENCE):
                raise ValueError(f"{location}: e{i} must be empty for v=0 or absence detection")
            if len(evidence) > 500 or evidence.startswith(("=", "+", "@")):
                raise ValueError(f"{location}: e{i} exceeds 500 characters or has a forbidden prefix")
        records[identifier] = tuple(int(v) for v in row[1:25])
    if not records:
        raise ValueError(f"{path}: no data rows")
    return records, hashlib.sha256(raw).hexdigest()


def calculate(truth, pred):
    if truth.keys() != pred.keys():
        missing = sorted(truth.keys() - pred.keys())
        extra = sorted(pred.keys() - truth.keys())
        raise ValueError(f"ID mismatch: missing={missing!r}, extra={extra!r}")
    counts = {item: {"tp": 0, "fp": 0, "fn": 0} for item in ITEMS}
    errors = []
    for identifier in sorted(truth):
        for item, actual, predicted in zip(ITEMS, truth[identifier], pred[identifier]):
            if actual and predicted:
                counts[item]["tp"] += 1
            elif actual != predicted:
                counts[item]["fn" if actual else "fp"] += 1
                errors.append([identifier, item, actual, predicted, "", "", "", "미분류"])
    for metrics in counts.values():
        tp, fp, fn = metrics["tp"], metrics["fp"], metrics["fn"]
        metrics.update(
            precision=tp / (tp + fp) if tp + fp else 0.0,
            recall=tp / (tp + fn) if tp + fn else 0.0,
            f1=2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
            support=tp + fn,
        )
    return {
        "macro_f1": sum(m["f1"] for m in counts.values()) / 24,
        "items": counts, "truth_count": len(truth), "pred_count": len(pred),
        "ids_match": True, "error_count": len(errors),
    }, errors


REPO = Path(__file__).resolve().parent.parent


def portable(path):
    """기록에 남길 경로. 저장소 밖 절대 경로는 기계·사용자 이름을 드러내므로 남기지 않는다."""
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(REPO).as_posix() or "."
    except ValueError:
        return "<외부>/" + resolved.name


def portable_argv(argv):
    """인터프리터는 이름만, 절대 경로 인자는 portable 형태로 남긴다."""
    return ["python"] + [portable(a) if Path(a).is_absolute() else a for a in argv[1:]]


def powershell_command(argv):
    return "& " + " ".join("'" + arg.replace("'", "''") + "'" for arg in argv)


def run(args, argv):
    started = time.perf_counter()
    code_path = Path(__file__).resolve()
    code_hash = hashlib.sha256(code_path.read_bytes()).hexdigest()
    if args.output_dir.exists():
        raise ValueError(f"output directory already exists: {args.output_dir}; use a new run ID")
    truth, truth_hash = load_csv(args.truth)
    pred, pred_hash = load_csv(args.pred)
    metrics, errors = calculate(truth, pred)
    argv = portable_argv(argv)
    command = powershell_command(argv)
    manifest = {
        "artifact_id": f"score-{args.output_dir.name}", "version": 1, "status": "draft",
        "run_id": args.output_dir.name, "baseline_run": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sources": [
            {"role": "truth", "path": portable(args.truth), "sha256": truth_hash},
            {"role": "pred", "path": portable(args.pred), "sha256": pred_hash},
        ],
        "generator": {
            "path": portable(code_path), "sha256": code_hash,
            "argv": argv, "command": command,
            "settings": {"output_dir": portable(args.output_dir), "zero_division": 0, "items": 24},
        },
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "cwd": portable(Path.cwd())},
        "mode": "local_scoring", "model": None, "prompt_hash": None, "seed": None,
        "parents": [], "reviewer": None, "reviewed_at": None, "decision": None,
        "execution_status": "complete",
        "validation": {"csv_contract": True, "evidence_substring": False, "evidence_quality": False},
    }
    args.output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".score-", dir=args.output_dir.parent) as temporary:
        staged = Path(temporary) / "result"
        staged.mkdir()
        with (staged / "errors.csv").open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(ERROR_HEADER)
            writer.writerows(errors)
        manifest["elapsed_seconds_before_publish"] = time.perf_counter() - started
        for name, data in (("metrics.json", metrics), ("manifest.json", manifest)):
            (staged / name).write_text(
                json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                encoding="utf-8", newline="\n",
            )
        result = (
            "# 로컬 채점 결과\n\n"
            f"- Macro F1: {metrics['macro_f1']:.12g}\n"
            f"- 정답/예측: {len(truth)}/{len(pred)}건, ID 집합 일치, 오답 {len(errors)}개\n"
            "- 상태: draft. 독립 리뷰·사람 승인 없음.\n"
            f"- 로컬 채점·저장 준비: {manifest['elapsed_seconds_before_publish']:.6f}초\n\n"
            "가설: 두 CSV의 24개 양성 F1을 ID로 대응해 계산한다. 비교 baseline은 지정되지 않았다.\n"
            "자기 대조·전부 0 등 합성 예측은 채점기 검사이며 모델 성능 검증이 아니다.\n"
            "예측 생성 모델·프롬프트·실험의 독립성은 CSV로 확인할 수 없다. 채점 과정은 모델 미사용이다.\n"
            "모델 로드·추론 시간, 토큰·GPU 메모리, 근거 폐기·JSON 결손은 해당 없음이다.\n"
            "헤더·ID·v값·인코딩/NFC·e의 길이/접두/빈칸 규약을 검증했다.\n"
            "e는 점수에서 제외했다. 근거 원문 부분문자열·의미 품질은 미검증이다.\n"
            "후보 채택·반려는 이 채점만으로 결정하지 않는다. 오답 원인은 미분류다.\n\n"
            "## 재실행\n\n"
            "실행 당시 작업 폴더에서 다음 명령의 --output-dir을 새 경로로 바꿔 실행한다.\n"
            "입력 경로·SHA-256과 채점 코드 SHA-256은 manifest.json에 기록했다.\n\n"
            f"```powershell\n{command}\n```\n"
        )
        (staged / "result.md").write_text(result, encoding="utf-8", newline="\n")
        staged.rename(args.output_dir)
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--truth", type=Path, required=True)
    parser.add_argument("--pred", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True, help="new directory; existing paths are rejected")
    args = parser.parse_args()
    argv = [sys.executable, "-X", "utf8", *sys.argv]
    try:
        metrics = run(args, argv)
    except (OSError, ValueError, csv.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Macro F1={metrics['macro_f1']:.12g}; errors={metrics['error_count']}; output={args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
