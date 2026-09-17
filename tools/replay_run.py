"""보관된 원응답으로 판정 후단계를 GPU 없이 다시 돌린다. 모델을 부르지 않는다.

`postprocess`·`verify_sme`처럼 모델 뒤에 오는 단계만 바꾸는 후보는 이것으로 잰다.
프롬프트·스키마를 바꾸는 후보는 저장된 응답이 달라지므로 Colab 회차가 필요하다.
"""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def saved_responses(case_dir):
    """`--debug-responses`로 남긴 원응답. 단계별로 공고 ID에 붙여 돌려준다."""
    path = Path(case_dir) / "diagnostics.jsonl"
    if not path.is_file():
        raise ValueError(f"{path} 가 없다")
    texts = {"baseline": {}, "sme": {}}
    for line in path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("event") != "response" or event.get("status") != "valid":
            continue
        if "response_text" not in event:
            raise ValueError(f"{path}: 원응답이 없다. --debug-responses로 돌린 회차가 필요하다")
        texts.setdefault(event["phase"], {})[event["id"]] = event["response_text"]
    if not texts["baseline"]:
        raise ValueError(f"{path}: 기본 단계 원응답이 없다")
    return texts


def replay(script, case_dir, *, input_path, data_dir, postprocess=None, verify_sme=None):
    """저장된 응답으로 행을 다시 만든다. 바꿀 단계만 인자로 갈아 끼운다."""
    case_dir = Path(case_dir)
    report = json.loads((case_dir / "run_report.json").read_text(encoding="utf-8"))
    settings = report["reproduction"]["settings"]
    max_chars = settings["max_chars"]
    if report.get("sme_documents_shrunk"):
        # 줄어든 공고의 실제 예산은 토크나이저가 정했고 로그에 건별 값이 없다.
        raise ValueError("이 회차는 문서 예산이 축소된 공고가 있어 재생할 수 없다")
    postprocess = postprocess or script.postprocess
    verify_sme = verify_sme or script.verify_sme

    texts = saved_responses(case_dir)
    _, products = script.load_sme_reference(str(data_dir))
    rows, baseline_rows, reasons = [], [], {}
    for rec in script.iter_records(str(input_path)):
        text = texts["baseline"].get(rec["id"])
        if text is None:
            raise ValueError(f"{rec['id']}: 저장된 기본 응답이 없다")
        parsed, _ = script.parse_judgment(text)
        baseline_rows.append(script.to_row(rec["id"], script.postprocess(parsed, rec)))
        sme_text = texts["sme"].get(rec["id"])
        if sme_text is not None:
            focused, _ = script.parse_judgment(sme_text, expected_items=script.SME_ITEMS, sme=True)
            verified, rejected = verify_sme(focused, rec, products, max_chars)
            reasons[rec["id"]] = rejected
            parsed.update(verified)
        rows.append(script.to_row(rec["id"], postprocess(parsed, rec)))
    if len(rows) != report["건수"]:
        raise ValueError(f"입력 건수가 회차와 다르다: {len(rows)} != {report['건수']}")
    return {"rows": rows, "baseline_rows": baseline_rows, "rejected_conditions": reasons,
            "settings": settings}


def to_csv_bytes(script, rows):
    """`script.write_csv`와 같은 바이트를 메모리에서 만든다."""
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=script.HEADER if hasattr(script, "HEADER")
                            else ["id"] + script.ITEMS + [f"e{i}" for i in range(1, 25)],
                            lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")  # 파이프에 붙은 파이썬은 로케일 인코딩으로 죽는다.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True,
                        help="원응답이 있는 회차 폴더, 예: reports/runs/<run-id>/dev-debug")
    parser.add_argument("--input", default=str(ROOT / "open/dev.jsonl"))
    parser.add_argument("--data-dir", default=str(ROOT / "open/data"))
    parser.add_argument("--script", help="제출 코드. 기본은 저장소 루트의 script.py")
    parser.add_argument("--candidate",
                        help="후보 모듈. postprocess·verify_sme 중 정의한 것만 갈아 끼운다")
    parser.add_argument("--output-dir", help="새 디렉터리. CSV와 기록을 남긴다")
    parser.add_argument("--verify", action="store_true",
                        help="회차 자신의 CSV를 바이트 단위로 재현하는지 확인한다")
    args = parser.parse_args(argv)
    try:
        script = load_module(Path(args.script) if args.script else ROOT / "script.py", "submission")
        candidate = load_module(Path(args.candidate), "candidate") if args.candidate else None
        result = replay(script, args.case, input_path=args.input, data_dir=args.data_dir,
                        postprocess=getattr(candidate, "postprocess", None),
                        verify_sme=getattr(candidate, "verify_sme", None))
        produced = to_csv_bytes(script, result["rows"])
        original = (Path(args.case) / "submission.csv").read_bytes()
        identical = produced == original
        if args.verify:
            if candidate:
                raise ValueError("--verify는 후보 없이, 회차를 그대로 재현할 때만 쓴다")
            if not identical:
                raise ValueError("재생이 회차의 CSV와 다르다. 이 재생 결과를 근거로 쓰지 않는다")
        if args.output_dir:
            out = Path(args.output_dir)
            if out.exists():
                raise ValueError(f"{out} 가 이미 있다. 새 경로를 쓴다")
            out.mkdir(parents=True)
            (out / "submission.csv").write_bytes(produced)
            (out / "manifest.json").write_text(json.dumps({
                "purpose": "cpu_replay_only", "model_called": False,
                "case": script.record_path(str(Path(args.case).resolve())),
                "candidate": script.record_path(args.candidate) if args.candidate else None,
                "matches_original": identical,
                "original_sha256": hashlib.sha256(original).hexdigest(),
                "replayed_sha256": hashlib.sha256(produced).hexdigest(),
                "notices": len(result["rows"]),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "note": "저장된 원응답으로 모델 뒤 단계만 다시 돌렸다. 새 모델 실행이 아니다.",
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    except (OSError, ValueError, KeyError, AttributeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"재생 {len(result['rows'])}건 · 회차 CSV와 {'동일' if identical else '다름'}"
          + (f" · 후보 {Path(args.candidate).name}" if args.candidate else ""))
    if args.output_dir:
        print(f"  → {args.output_dir}/submission.csv (tools/score.py로 채점한다)")
    print("모델을 부르지 않았다. 프롬프트·스키마를 바꾸는 후보는 이 경로로 잴 수 없다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
