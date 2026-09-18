"""D 보고서가 인용하는 입력·코드·산출물 해시를 다시 적는다. 모델을 부르지 않는다.

왜 파일로 두는가. 해시를 보고서 본문에 손으로 적으면 코드를 한 번 더 고칠 때마다
조용히 낡는다. 실제로 PR #34 리뷰에서 후보 코드 해시가 어떤 커밋의 것도 아닌
값으로 남아 있었고, 해시로 감사하는 사람에게는 증거 사슬 전체가 깨진 것으로 보인다.

`tests/test_qualification_candidate.py`가 이 파일의 후보 해시를 실제 파일과 대조한다.
후보를 고치고 이 도구를 다시 돌리지 않으면 검사가 빨개진다.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/team-d/final/hashes.json"

# 보고서가 인용하는 것만 담는다. 목록을 늘리면 그만큼 다시 적을 일이 늘어난다.
TRACKED = {
    "candidate": "experiments/qualification_candidate.py",
    "script": "script.py",
    "dev_input": "open/dev.jsonl",
    "dev_labels": "open/dev_labels.csv",
    "test_sample": "open/data/test.jsonl.gz",
    "case_submission": "reports/runs/colab-1789655036303880754/dev-debug/submission.csv",
    "case_responses": "reports/runs/colab-1789655036303880754/dev-debug/diagnostics.jsonl",
    "candidate_replay": "reports/team-d/final/replay/submission.csv",
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def head_short():
    done = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else None


def build():
    head = head_short()
    files = {name: sha256(ROOT / rel) for name, rel in TRACKED.items()}
    paths = dict(TRACKED)
    baseline = ROOT / f"reports/team-d/final/head-{head}-replay/submission.csv" if head else None
    if baseline and baseline.is_file():
        files["head_baseline_replay"] = sha256(baseline)
        paths["head_baseline_replay"] = baseline.relative_to(ROOT).as_posix()
    return {"head": head, "paths": paths, "sha256": files}


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="다시 적지 않고 기록과 실제가 같은지만 본다")
    args = parser.parse_args(argv)
    current = build()
    if args.check:
        if not OUT.is_file():
            print(f"error: {OUT} 가 없다", file=sys.stderr)
            return 1
        recorded = json.loads(OUT.read_text(encoding="utf-8"))
        drift = [name for name, value in current["sha256"].items()
                 if recorded.get("sha256", {}).get(name) != value]
        if drift:
            print("기록이 낡았다: " + ", ".join(drift), file=sys.stderr)
            return 1
        print("기록과 실제가 같다")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"{OUT} 에 {len(current['sha256'])}개 기록")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
