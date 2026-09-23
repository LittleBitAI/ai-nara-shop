"""D7 v3 무라벨 발화율 수집. 진단 전용 — 라벨·학습·제출 CSV·추가 운영 단계가 없다.

**왜 GPU 가 필요한가.** v3 게이트(`script.performance_below_budget`)는 **모델이 낸 인용**
안의 실적 금액을 읽는다. 무라벨 20,000건에는 모델 출력이 없으므로, A4 §5 가 v6·v9 에서 한
"게이트가 보는 신호의 보유율" 을 v3 에서는 텍스트만으로 셀 수 없다. 그래서 무라벨 공고에
**24항목 기본 호출**을 그대로 돌려 v3 판정과 인용을 받고, 그 위에서 게이트를 돌린다.

`experiments/a5_collect_facts.py` 의 샤드·재개·계약 뼈대를 그대로 쓰고 **호출 단계만**
`company_size` 에서 기본 단계로 바꿨다. 세는 것은 셋이다.

- `model_v3` — 모델이 v3=1 을 낸 비율.
- `gate_fired` — 그중 `performance_below_budget(rec, 근거문구)` 가 값을 돌려준 비율
  (= 게이트가 실제로 내리는 자리). 운영과 같은 입력을 쓴다 — `apply_qualification_rules`
  가 보는 것은 정제 전 원 인용이다(`script.py`).
- `final_v3` — 같은 응답을 `postprocess` 까지 통과시킨 결과. 게이트의 순효과를 본다.

dev 200건을 같은 회차에서 함께 수집해 **무라벨/dev 배율**을 낸다(W5).

  python -X utf8 experiments/d7_collect_v3_firing.py \
      --input open/train_unlabeled.jsonl --output-dir <드라이브 폴더> \
      --model-dir <스냅샷> --shards-per-episode 1

기본 1,000건 샤드 하나가 한 회차다. 20,000건 전체는 `complete=true` 로만 인정한다 —
부분 수집은 표본이고 표본이라고 적는다.
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

UNLABELED_SHA256 = "f46449fb84f980a5ddf868d66f5daff2bcf0991135d9b81da5656dd607275698"
SHARD_SIZE = 1000
CHUNK = 128
MAX_CHARS = 16000
DEV_COUNT = 200
UNLABELED_COUNT = 20000


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


def observe(rec, response):
    """한 응답에서 v3 세 값을 읽는다. 저장본 재검증도 이 함수를 다시 부른다."""
    parsed, _ = script.parse_judgment(response)
    cell = parsed.get("v3") or {}
    model_v3 = cell.get("위반여부") == 1
    # 운영과 같은 입력이다 — `apply_qualification_rules` 는 정제 전 원 인용을 본다.
    gate = script.performance_below_budget(rec, cell.get("근거문구")) if model_v3 else None
    final = script.postprocess(parsed, rec)["v3"]["위반여부"]
    return dict(model_v3=int(model_v3), gate_fired=int(model_v3 and gate is not None),
                final_v3=int(final))


def collect(records, runner, system_prompt, emit, budget=None):
    budget = script.PROMPT_BUDGET if budget is None else budget
    rows, inference_seconds = [], 0.0
    started = time.perf_counter()
    for start in range(0, len(records), CHUNK):
        group = records[start:start + CHUNK]
        batch, budgets = [], []
        for rec in group:
            messages, tokens, chars = script.fit_to_budget(
                rec, system_prompt, runner, MAX_CHARS, budget=budget)
            batch.append(messages)
            budgets.append((tokens, chars))
            emit("baseline_input", id=rec["id"], max_chars=chars, prompt_tokens=tokens,
                 prompt_sha256=digest(messages))
        identifiers = [r["id"] for r in group]
        before = time.perf_counter()
        try:
            responses = script.run_chunk(runner, batch, start=start, ids=identifiers,
                                         emit=emit, debug_responses=True, phase="baseline")
        finally:
            inference_seconds += time.perf_counter() - before
        # 실패한 재시도는 예외로 올라간다. 음성으로 대체해 발화율을 낮추지 않는다.
        for rec, response, (tokens, chars) in zip(group, responses, budgets):
            rows.append(dict(id=rec["id"], response_text=response, prompt_tokens=tokens,
                             max_chars=chars, **observe(rec, response)))
        print(f"baseline {len(rows)}/{len(records)}", flush=True)
    return dict(rows=rows, inference_seconds=inference_seconds,
                stage_seconds=time.perf_counter() - started)


def read_shard(path, records, contract_hash):
    value = json.loads(path.read_text(encoding="utf-8"))
    if (value["contract_sha256"] != contract_hash
            or value["payload_sha256"] != digest(value["payload"])
            or [r["id"] for r in value["payload"]["rows"]] != [r["id"] for r in records]):
        raise ValueError(f"Shard contract/content mismatch: {path.name}")
    for row, rec in zip(value["payload"]["rows"], records):
        again = observe(rec, row["response_text"])
        if not 128 <= row["max_chars"] <= MAX_CHARS or any(row[k] != v for k, v in again.items()):
            raise ValueError(f"Invalid saved observation: {rec['id']}")
    return value


def rates(rows):
    total = len(rows)
    model = sum(r["model_v3"] for r in rows)
    fired = sum(r["gate_fired"] for r in rows)
    final = sum(r["final_v3"] for r in rows)
    return dict(count=total,
                model_v3=model, model_v3_rate=model / total if total else None,
                gate_fired=fired, gate_fired_rate=fired / total if total else None,
                gate_fired_given_model_v3=fired / model if model else None,
                final_v3=final, final_v3_rate=final / total if total else None)


def summarize(completed):
    def group(names):
        return rates([r for name in names for r in completed[name]["payload"]["rows"]])
    dev = group(["dev"] if "dev" in completed else [])
    unlabeled = group([name for name in completed if name != "dev"])

    def multiple(key):
        base, other = dev[key], unlabeled[key]
        return other / base if base and other is not None else None

    return dict(
        mode="live_baseline_v3_only",
        dev=dev, unlabeled=unlabeled,
        unlabeled_over_dev={key: multiple(key) for key in
                            ("model_v3_rate", "gate_fired_rate", "final_v3_rate")},
        complete=dev["count"] == DEV_COUNT and unlabeled["count"] == UNLABELED_COUNT,
        completed_shards=sorted(completed),
        note=("v3 판정·게이트 발화율만 잰다. Macro F1·서버 통과·다른 항목의 값이 아니다. "
              "부분 수집은 표본이며 20,000건 증거가 아니다. dev 발화가 0이면 배율은 null 이다."))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--shards-per-episode", type=int, default=1)
    args = parser.parse_args(argv)
    if not 1 <= args.shards_per_episode <= 20:
        parser.error("--shards-per-episode must be 1..20")
    if args.model_dir.name != script.MODEL_REVISION or not args.model_dir.is_dir():
        parser.error("Use the fixed Hugging Face snapshot directory")
    if file_hash(args.input) != UNLABELED_SHA256:
        parser.error("Wrong train_unlabeled.jsonl SHA256")
    dev_path, data_dir = ROOT / "open/dev.jsonl", ROOT / "open/data"
    dev = list(script.iter_records(str(dev_path)))
    unlabeled = list(script.iter_records(str(args.input)))
    if len(dev) != DEV_COUNT or len(unlabeled) != UNLABELED_COUNT:
        parser.error(f"Expected dev {DEV_COUNT} and unlabeled {UNLABELED_COUNT} records")
    table = script.item_table(str(data_dir))
    system_prompt = script.build_system_prompt(table)
    contract = dict(
        files={str(p.relative_to(ROOT)).replace("\\", "/"): file_hash(p) for p in
               [ROOT / "script.py", Path(__file__), ROOT / "requirements.txt", dev_path,
                *sorted(p for p in data_dir.rglob("*") if p.is_file())]},
        input_sha256=UNLABELED_SHA256, model_id=script.MODEL_ID,
        model_revision=script.MODEL_REVISION, chunk=CHUNK, max_chars=MAX_CHARS,
        shard_size=SHARD_SIZE,
        prompt_sha256=hashlib.sha256(system_prompt.encode()).hexdigest(),
        schema_sha256=digest(script.decode_schema(str(data_dir))), seed=script.SEED,
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
        return 0
    started = time.perf_counter()
    script.load_sme_reference(str(data_dir))          # 경쟁제품 표를 후처리가 읽는다
    runner = script.VLLMRunner(script.decode_schema(str(data_dir)), model_dir=str(args.model_dir))
    if any(value["environment"] != runner.environment for value in completed.values()):
        raise ValueError("Different GPU/runtime/chat template: use a new output directory")
    source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    for name in pending:
        # 24항목 기본 호출은 company_size 보다 무겁다. 과거 dev 실측 677.1초/200건에서 출발하고,
        # 이 회차가 실제로 잰 속도가 생기면 그것을 쓴다. 예보이지 하드 타임아웃이 아니다.
        prior = [v["payload"] for v in completed.values()]
        per_record = max((v["stage_seconds"] / len(v["rows"]) for v in prior), default=677.1 / 200)
        forecast = per_record * len(groups[name])
        if time.perf_counter() - started + forecast * 1.25 > 7200:
            raise RuntimeError("Episode forecast exceeds 7,200s; completed shards saved. "
                               "Resume in a new runtime.")
        print(f"{name}: forecast {forecast:.0f}s (+25% planning margin), not a server estimate",
              flush=True)
        with (output / f"{name}-{time.time_ns()}.events.jsonl").open("x", encoding="utf-8",
                                                                     newline="\n") as log:
            def emit(event, **fields):
                log.write(json.dumps(dict(event=event, **fields), ensure_ascii=False) + "\n")
                log.flush()
            payload = collect(groups[name], runner, system_prompt, emit)
        value = dict(contract_sha256=contract_hash, payload_sha256=digest(payload), payload=payload,
                     environment=runner.environment, source_commit=source_commit,
                     model_load_seconds=runner.load_seconds)
        save(output / (name + ".json"), value)
        completed[name] = value
        save(output / "summary.json", summarize(completed))
    print(json.dumps(summarize(completed), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
