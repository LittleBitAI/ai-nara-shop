"""few-shot 의 대상과 단계를 정하는 측정. 모델을 안 부른다.

`TARGET.md` 의 §1~§4 를 낸다. 넷을 답한다.

  1. `main` 을 진단 200 에 재생한 C 항목 성적 — 9/27 배정의 "replay the diagnostic 200"
  2. FN 중 절단·누락이 몇인가 — 그 자리는 예시가 못 닿는다
  3. FN 을 어디서 잃나 — 모델이 0 인가, 게이트가 정탐을 내렸는가
  4. 고른 예시 쌍이 지금 맞는 판정인가 — 틀리는 공고를 예시로 쓰면 안 된다

무라벨 D 회차 11샤드의 저장된 원응답 위에서 돈다. `u11` 은 문서 예산이 축소돼 재생이
거부되는 것이 정상이다.

    py -X utf8 reports/team-c/c-fewshot/target.py
    py -X utf8 reports/team-c/c-fewshot/target.py --keep <경로>   # 재생 결과를 남긴다
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SHARDS = ROOT / "reports/label-compare/unlabeled-d"
DIAG = ROOT / "reports/labels-600/merged/diag.csv"
UNLABELED = ROOT / "open/train_unlabeled.jsonl"
DEV_RUN = ROOT / "reports/runs/colab-1790445336782946136/var-01"
ITEMS = ("v10", "v11", "v13", "v18")
# §4 가 고른 쌍. 같은 낱말을 담고 판정이 반대인 dev 공고 둘.
PAIR = {"PPS-DEV-118": "0", "PPS-DEV-043": "1"}


def read_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as stream:
        return {row["id"]: row for row in csv.DictReader(stream)}


def f1(tp, fp, fn):
    return 0.0 if not tp else 2 * tp / (2 * tp + fp + fn)


def pinned(ref):
    source = subprocess.run(["git", "-C", str(ROOT), "show", f"{ref}:script.py"],
                            capture_output=True, check=True).stdout
    path = Path(tempfile.mkdtemp(prefix="c-fewshot-")) / "script.py"
    path.write_bytes(source)
    return path


def shard_inputs(work):
    """샤드마다 `ids.json` 으로 무라벨 말뭉치를 잘라 입력 jsonl 을 만든다."""
    shards = {}
    for shard in sorted(SHARDS.glob("run-*/u*")):
        ids_file = shard / "ids.json"
        if ids_file.is_file() and (shard / "output/diagnostics.jsonl").is_file():
            shards[shard] = set(json.loads(ids_file.read_text(encoding="utf-8")))
    wanted = set().union(*shards.values()) if shards else set()
    lines = {}
    with UNLABELED.open(encoding="utf-8") as stream:
        for line in stream:
            rec = json.loads(line)
            if rec["id"] in wanted:
                lines[rec["id"]] = line
    for shard, ids in shards.items():
        (work / f"{shard.name}.jsonl").write_text(
            "".join(lines[i] for i in ids if i in lines), encoding="utf-8")
    return shards


def replay(work, shards, script):
    """11샤드를 `main` 의 코드로 재생한다. 되는 것만 센다."""
    done, refused = [], []
    for shard in shards:
        out = work / f"out-{shard.name}"
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(ROOT / "tools/replay_run.py"),
             "--case", str(shard / "output"), "--input", str(work / f"{shard.name}.jsonl"),
             "--script", str(script), "--output-dir", str(out)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
        (done if result.returncode == 0 else refused).append(shard.name)
    return done, refused


def raw_baseline(ids):
    """원응답의 `baseline` 판정. 게이트가 내렸는지 가르는 데 쓴다."""
    out = {}
    for path in SHARDS.glob("run-*/u*/output/diagnostics.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if (event.get("event") == "response" and event.get("phase") == "baseline"
                    and event.get("id") in ids):
                try:
                    out[event["id"]] = json.loads(event["response_text"])
                except ValueError:
                    pass
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ref", default="origin/main")
    parser.add_argument("--keep", help="재생 결과를 남길 경로")
    args = parser.parse_args(argv)

    work = Path(args.keep) if args.keep else Path(tempfile.mkdtemp(prefix="c-target-"))
    work.mkdir(parents=True, exist_ok=True)
    script = pinned(args.ref)
    shards = shard_inputs(work)
    done, refused = replay(work, shards, script)
    print(f"=== 1. {args.ref} 를 진단 200 에 재생 ===")
    print(f"  샤드 {len(done)}개 재생 · 거부 {refused or '없음'}"
          " (u11 은 문서 예산 축소로 거부되는 것이 정상)")

    diag = read_csv(DIAG)
    pred = {}
    for out in sorted(work.glob("out-u*")):
        path = out / "submission.csv"
        if path.is_file():
            for key, row in read_csv(path).items():
                if key in diag:
                    pred[key] = row
    print(f"  진단 200 중 덮인 공고 {len(pred)}건")
    print(f"  {'항목':6}{'TP':>4}{'FP':>4}{'FN':>4}{'F1':>10}")
    errors = {}
    for item in ITEMS:
        tp = fp = fn = 0
        false_pos, false_neg = [], []
        for key, row in pred.items():
            label, guess = diag[key][item], row[item]
            if label == guess == "1":
                tp += 1
            elif label == "0" and guess == "1":
                fp += 1
                false_pos.append(key)
            elif label == "1" and guess == "0":
                fn += 1
                false_neg.append(key)
        errors[item] = (false_pos, false_neg)
        print(f"  {item:6}{tp:>4}{fp:>4}{fn:>4}{f1(tp, fp, fn):>10.4f}")

    spec = importlib.util.spec_from_file_location("pinned_script", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    wanted = {i for item in ITEMS for side in errors[item] for i in side}
    recs = {}
    with UNLABELED.open(encoding="utf-8") as stream:
        for line in stream:
            rec = json.loads(line)
            if rec["id"] in wanted:
                recs[rec["id"]] = rec

    print("\n=== 2. FN 중 절단·누락 — 그 자리는 예시가 못 닿는다 ===")
    print(f"  {'항목':6}{'FN':>4}{'절단·누락':>10}{'그 밖':>8}")
    for item in ITEMS:
        false_neg = errors[item][1]
        cut = 0
        for key in false_neg:
            rec = recs.get(key)
            if rec is None:
                continue
            visible = module.build_context(rec, max_chars=16000)
            cut += ("[Truncated documents; unseen remainder]" in visible
                    or "[Missing documents]" in visible)
        print(f"  {item:6}{len(false_neg):>4}{cut:>10}{len(false_neg) - cut:>8}")

    print("\n=== 3. FN 을 어디서 잃나 ===")
    raw = raw_baseline(wanted)
    print(f"  {'항목':6}{'FN':>4}{'모델이 0':>10}{'게이트가 내림':>14}{'알수없음':>10}")
    for item in ITEMS:
        false_neg = errors[item][1]
        said_zero = lowered = unknown = 0
        for key in false_neg:
            verdict = (raw.get(key) or {}).get(item, {}).get("위반여부")
            if verdict is None:
                unknown += 1
            elif verdict == 1:
                lowered += 1
            else:
                said_zero += 1
        print(f"  {item:6}{len(false_neg):>4}{said_zero:>10}{lowered:>14}{unknown:>10}")
    print("  → 게이트가 내린 것이 0 이면 고칠 곳은 판정 단계(baseline)다")

    print("\n=== 4. 고른 예시 쌍이 지금 맞는가 ===")
    truth = read_csv(ROOT / "open/dev_labels.csv")
    dev_pred = read_csv(DEV_RUN / "submission.csv")
    for key, expected in PAIR.items():
        label, guess = truth[key]["v18"], dev_pred[key]["v18"]
        mark = "OK" if label == guess == expected else "**틀림**"
        print(f"  {key:14} v18 라벨 {label} / 판정 {guess} / 기대 {expected}   {mark}")
    print("  → 틀리는 공고를 예시로 쓰면 무엇을 가르치는지 알 수 없다")

    if not args.keep:
        shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
