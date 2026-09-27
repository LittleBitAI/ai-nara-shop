"""Reproduce submission replay gains and inspect supplied input distributions."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.replay_run import load_module, replay
from tools.score import calculate, load_csv


def main():
    current = load_module(ROOT / "script.py", "audit_current")
    truth, _ = load_csv(ROOT / "open/dev_labels.csv")
    dev_contracts = {r["id"]: r["meta"]["계약방법"] for r in current.iter_records(str(ROOT / "open/dev.jsonl"))}
    # Check the reused metric against a known exact answer.
    assert calculate(truth, truth)[0]["macro_f1"] == 1.0
    ledger = json.loads((ROOT / "reports/submissions.json").read_text(encoding="utf-8"))
    latest = ledger["submissions"][-1]
    assert hashlib.sha256((ROOT / "script.py").read_bytes()).hexdigest() == latest["script_sha256"]
    result = {"mode": "cpu_audit_no_model_calls", "submission": latest, "distribution": {}, "replays": []}
    for name in ("dev", "train_unlabeled"):
        counts = {key: Counter() for key in ("contract", "business", "law", "complete", "context_cut")}
        n = 0
        with (ROOT / f"open/{name}.jsonl").open(encoding="utf-8") as stream:
            for line in stream:
                rec = json.loads(line)
                n += 1
                for key, source in (("contract", "계약방법"), ("business", "업무구분"), ("law", "적용계약법")):
                    counts[key][str(rec["meta"].get(source))] += 1
                counts["complete"][str(rec["input_completeness"].get("완전관측"))] += 1
                context = current.build_context(rec, 16000)
                counts["context_cut"][str("[Truncated documents;" in context or "[Missing documents]:" in context)] += 1
        assert n == (200 if name == "dev" else 20000)
        result["distribution"][name] = {"n": n, **counts}
    runs = ("1790229556644838226", "1790235508743452453", "1790246262386880643", "1790250265636150570", "1790318892216968298")
    with tempfile.TemporaryDirectory() as scratch:
        old_path = Path(scratch) / "script.py"
        old_path.write_bytes(subprocess.check_output(["git", "show", "21253f3:script.py"], cwd=ROOT))
        old = load_module(old_path, "audit_previous")
        for run in runs:
            entry = {"case": f"reports/runs/colab-{run}/dev-debug"}
            for label, module in (("previous", old), ("submitted", current)):
                data = replay(module, ROOT / entry["case"], input_path=ROOT / "open/dev.jsonl", data_dir=ROOT / "open/data")
                pred = {row["id"]: tuple(int(row[f"v{i}"]) for i in range(1, 25)) for row in data["rows"]}
                entry[label] = calculate(truth, pred)[0]
                strata = {}
                for contract in sorted(set(dev_contracts.values())):
                    subset = {i: v for i, v in truth.items() if dev_contracts[i] == contract}
                    strata[contract] = calculate(subset, {i: pred[i] for i in subset})[0]
                target = result["distribution"]["train_unlabeled"]["contract"]
                weighted = []
                for item in current.ITEMS:
                    totals = {k: sum(m["items"][item][k] * target[c] / m["truth_count"] for c, m in strata.items()) for k in ("tp", "fp", "fn")}
                    denominator = 2 * totals["tp"] + totals["fp"] + totals["fn"]
                    weighted.append(2 * totals["tp"] / denominator if denominator else 0.0)
                entry[label]["contract_reweighted_macro_sensitivity_only"] = sum(weighted) / 24
            result["replays"].append(entry)
            print(run, entry["previous"]["macro_f1"], entry["submitted"]["macro_f1"], flush=True)
    result["mean_replay_gain"] = sum(r["submitted"]["macro_f1"] - r["previous"]["macro_f1"] for r in result["replays"]) / len(runs)
    result["server_gain"] = latest["leaderboard_macro_f1"] - ledger["submissions"][-2]["leaderboard_macro_f1"]
    result["transfer"] = result["server_gain"] / result["mean_replay_gain"]
    Path(__file__).with_name("audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: result[k] for k in ("distribution", "mean_replay_gain", "server_gain", "transfer")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
