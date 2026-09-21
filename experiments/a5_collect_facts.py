"""A5 H2 diagnostic only: collect unchanged company_size facts, resume 1,000-row shards.

No labels, training, submission CSV, or additional production inference stage.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import script
from experiments.a5_v11_absence_candidate import observed_absence

UNLABELED_SHA256 = "f46449fb84f980a5ddf868d66f5daff2bcf0991135d9b81da5656dd607275698"
SHARD_SIZE = 1000
CHUNK = 128
MAX_CHARS = 16000


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def file_hash(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8", newline="\n")
    temporary.replace(path)


def collect(records, runner, products, emit):
    rows, inference_seconds = [], 0.0
    started = time.perf_counter()
    for start in range(0, len(records), CHUNK):
        group = records[start:start + CHUNK]
        batch, budgets = [], []
        for rec in group:
            company_rec = {**rec, "meta": {k: v for k, v in rec.get("meta", {}).items()
                                         if k != "조항호내용"}}
            messages, tokens, chars = script.fit_to_budget(
                company_rec, script.COMPANY_SIZE_PROMPT, runner, MAX_CHARS,
                budget=script.PROMPT_BUDGET, products=products)
            batch.append(messages)
            budgets.append((tokens, chars))
            emit('company_size_input', id=rec['id'], max_chars=chars, prompt_tokens=tokens,
                 prompt_sha256=digest(messages))
        before = time.perf_counter()
        responses = script.run_chunk(
            runner, batch, start=start, ids=[r["id"] for r in group], emit=emit,
            debug_responses=True, items=script.COMPANY_SIZE_KEYS, phase="company_size")
        inference_seconds += time.perf_counter() - before
        # No baseline_texts: a failed retry raises instead of substituting a negative.
        for rec, response, (tokens, chars) in zip(group, responses, budgets):
            facts = script.parse_judgment(response, expected_items=script.COMPANY_SIZE_KEYS)[0]["company_size"]
            rows.append(dict(id=rec["id"], response_text=response, prompt_tokens=tokens,
                             max_chars=chars, h2_fired=observed_absence(facts, rec, chars)))
        print(f"company_size {len(rows)}/{len(records)}", flush=True)
    return dict(rows=rows, inference_seconds=inference_seconds,
                stage_seconds=time.perf_counter() - started)


def read_shard(path, records, contract_hash):
    value = json.loads(path.read_text(encoding="utf-8"))
    if (value["contract_sha256"] != contract_hash
            or value["payload_sha256"] != digest(value["payload"])
            or [r["id"] for r in value["payload"]["rows"]] != [r["id"] for r in records]):
        raise ValueError(f"Shard contract/content mismatch: {path.name}")
    for row, rec in zip(value["payload"]["rows"], records):
        facts = script.parse_judgment(row["response_text"], expected_items=script.COMPANY_SIZE_KEYS)[0]["company_size"]
        if not 128 <= row["max_chars"] <= MAX_CHARS or row["h2_fired"] != observed_absence(facts, rec, row["max_chars"]):
            raise ValueError(f"Invalid saved observation: {rec['id']}")
    return value


def summarize(completed):
    def rates(names):
        rows = [r for name in names for r in completed[name]["payload"]["rows"]]
        fired = sum(r["h2_fired"] for r in rows)
        return dict(count=len(rows), fired=fired, rate=fired / len(rows) if rows else None)
    dev = rates(["dev"] if "dev" in completed else [])
    unlabeled = rates([name for name in completed if name != "dev"])
    ratio = unlabeled["rate"] / dev["rate"] if dev["rate"] and unlabeled["rate"] is not None else None
    return dict(mode="live_company_size_only", dev=dev, unlabeled=unlabeled,
                unlabeled_over_dev_rate=ratio,
                complete=dev["count"] == 200 and unlabeled["count"] == 20000,
                completed_shards=sorted(completed),
                note="H2 predicate firing, not final v11 positives, F1, or server verification. Partial coverage is not 20,000-row evidence.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--shards-per-episode", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.shards_per_episode <= 20:
        parser.error("--shards-per-episode must be 1..20")
    if args.model_dir.name != script.MODEL_REVISION or not args.model_dir.is_dir():
        parser.error("Use the fixed Hugging Face snapshot directory")
    if file_hash(args.input) != UNLABELED_SHA256:
        parser.error("Wrong train_unlabeled.jsonl SHA256")
    dev_path, data_dir = ROOT / "open/dev.jsonl", ROOT / "open/data"
    dev = list(script.iter_records(str(dev_path)))
    unlabeled = list(script.iter_records(str(args.input)))
    if len(dev) != 200 or len(unlabeled) != 20000:
        parser.error("Expected dev 200 and unlabeled 20,000 records")
    contract = dict(
        files={str(p.relative_to(ROOT)).replace("\\", "/"): file_hash(p) for p in
               [ROOT / "script.py", Path(__file__), ROOT / "experiments/a5_v11_absence_candidate.py",
                ROOT / "requirements.txt", dev_path, *sorted(p for p in data_dir.rglob("*") if p.is_file())]},
        input_sha256=UNLABELED_SHA256, model_id=script.MODEL_ID, model_revision=script.MODEL_REVISION,
        chunk=CHUNK, max_chars=MAX_CHARS, shard_size=SHARD_SIZE,
        prompt_sha256=hashlib.sha256(script.COMPANY_SIZE_PROMPT.encode()).hexdigest(),
        schema_sha256=digest(script.company_size_schema()), seed=script.SEED,
        max_tokens=script.MAX_TOKENS, quant=script.QUANT)
    contract_hash = digest(contract)
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "contract.json"
    if manifest_path.exists():
        if json.loads(manifest_path.read_text(encoding="utf-8")) != contract:
            raise ValueError("Different code/data/settings: use a new output directory")
    else:
        if any(output.iterdir()):
            raise ValueError("Nonempty output directory without contract")
        save(manifest_path, contract)
    groups = {"dev": dev, **{f"unlabeled-{i // SHARD_SIZE:02d}": unlabeled[i:i + SHARD_SIZE]
                             for i in range(0, len(unlabeled), SHARD_SIZE)}}
    completed = {name: read_shard(output / (name + ".json"), records, contract_hash)
                 for name, records in groups.items() if (output / (name + ".json")).exists()}
    save(output / "summary.json", summarize(completed))
    pending = [name for name in groups if name != "dev" and name not in completed][:args.shards_per_episode]
    if "dev" not in completed:
        pending.insert(0, "dev")
    if not pending:
        print(json.dumps(summarize(completed), ensure_ascii=False, indent=2))
        return
    started = time.perf_counter()
    _, products = script.load_sme_reference(str(data_dir))
    runner = script.VLLMRunner(script.decode_schema(str(data_dir)), model_dir=str(args.model_dir))
    if any(value["environment"] != runner.environment for value in completed.values()):
        raise ValueError("Different GPU/runtime/chat template: use a new output directory")
    source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    for name in pending:
        # ponytail: historical/dev throughput is only a forecast, not a hard GPU timeout.
        prior = [v["payload"] for v in completed.values()]
        per_record = max((v["stage_seconds"] / len(v["rows"]) for v in prior), default=246.985 / 200)
        forecast = per_record * len(groups[name])
        if time.perf_counter() - started + forecast * 1.25 > 7200:
            raise RuntimeError("Episode forecast exceeds 7,200s; completed shards saved. Resume in a new runtime.")
        print(f"{name}: forecast {forecast:.0f}s (+25% planning margin), not a server estimate", flush=True)
        with (output / f"{name}-{time.time_ns()}.events.jsonl").open("x", encoding="utf-8", newline="\n") as log:
            def emit(event, **fields):
                log.write(json.dumps(dict(event=event, **fields), ensure_ascii=False) + "\n")
                log.flush()
            payload = collect(groups[name], runner, products, emit)
        value = dict(contract_sha256=contract_hash, payload_sha256=digest(payload), payload=payload,
                     environment=runner.environment, source_commit=source_commit,
                     model_load_seconds=runner.load_seconds)
        save(output / (name + ".json"), value)
        completed[name] = value
        save(output / "summary.json", summarize(completed))
    print(json.dumps(summarize(completed), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
