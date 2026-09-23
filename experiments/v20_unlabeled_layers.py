"""무라벨 2,000건 회차 CSV 에서 v20 후보가 모델과 갈리는 층을 만든다. 모델을 부르지 않는다.

회차는 `feat/unlabeled-d-run` 의 `58af667`(`reports/label-compare/unlabeled-d/run-1790141381430477242`)이고
운영 `script.py` = HEAD 로 돌았다. CSV 는 그 커밋에서 `git show` 로 읽는다.

층은 모델 v20 과 후보 v20 의 쌍이다 — U(0→1, 후보가 올림) · W(1→0, 후보가 내림) · K(1→1) · Z(0→0).
후보는 v20 을 **대체**하므로 추첨하지 않고 U·W·K 를 전부 라벨 대상으로 낸다.

    python -X utf8 experiments/v20_unlabeled_layers.py --unlabeled <train_unlabeled.jsonl> --out <dir>
"""

import argparse
import csv
import importlib.util
import io
import json
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_COMMIT = "58af667c45540f15315934ef87188d4189e8b72d"
RUN_DIR = "reports/label-compare/unlabeled-d/run-1790141381430477242"
PARTS = ("u00", "u01", "u02", "u03")
LAYER = {(0, 1): "U", (1, 0): "W", (1, 1): "K", (0, 0): "Z"}

spec = importlib.util.spec_from_file_location("v20_sw_clause_candidate", ROOT / "experiments/v20_sw_clause_candidate.py")
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


def model_v20():
    out = {}
    for part in PARTS:
        data = subprocess.run(["git", "show", f"{RUN_COMMIT}:{RUN_DIR}/{part}/output/submission.csv"],
                              cwd=ROOT, capture_output=True, check=True).stdout.decode("utf-8")
        for row in csv.DictReader(io.StringIO(data)):
            out[row["id"]] = int(row["v20"])
    return out


def layers(model, recs):
    rows = []
    for rec_id, m in model.items():
        rec = recs[rec_id]
        decision = candidate.v20_decision(rec)
        rule = m if decision is None else decision
        rows.append({"id": rec_id, "layer": LAYER[(m, rule)], "model_v20": m, "rule_v20": rule,
                     "rule_abstains": decision is None,
                     "sw_required": candidate.sw_participation_missing(rec) is not None,
                     "license_1468": "1468" in ((rec.get("meta") or {}).get("면허업종제한목록") or ""),
                     "dropped_doc_counts": rec.get("dropped_doc_counts") or {}})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unlabeled", required=True)
    parser.add_argument("--out", required=True, help="새 디렉터리")
    args = parser.parse_args()
    model = model_v20()
    recs = {}
    with open(args.unlabeled, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec["id"] in model:
                recs[rec["id"]] = rec
    rows = layers(model, recs)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    targets = [r for r in rows if r["layer"] != "Z"]
    with open(out / "layers.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for r in targets:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (out / "ids.txt").write_text("".join(r["id"] + "\n" for r in targets), encoding="utf-8", newline="\n")
    summary = {"run_commit": RUN_COMMIT, "run_dir": RUN_DIR, "notices": len(rows),
               "layers": dict(Counter(r["layer"] for r in rows)),
               "targets_with_dropped_docs": sum(bool(r["dropped_doc_counts"]) for r in targets)}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                      encoding="utf-8", newline="\n")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
