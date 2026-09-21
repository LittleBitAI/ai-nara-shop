"""A5 H2 diagnostic only: collect unchanged company_size facts, resume 1,000-row shards.

No labels, training, submission CSV, or additional production inference stage.
"""

import argparse
import contextlib
from contextlib import contextmanager
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


@contextmanager
def observe_chat(runner, emit, *, ids, phase):
    """`runner.chat` 을 **인스턴스 속성으로만** 감싸 실제 모델 요청을 그대로 기록한다.

    왜 이 자리인가. 사이드카가 원자료로 프롬프트를 다시 조립하면 실제 절단·재시도와 달라진다.
    그리고 `VLLMRunner.retry_chat` 은 system 뒤에 출력범위 문장을 붙이고 출력 예산을 다시
    계산한 뒤 **`self.chat`** 을 부르므로, 인스턴스 속성을 감싸면 그 변경된 메시지가 그대로 잡힌다.
    클래스 함수·`retry_chat`·전역 `script` 함수는 건드리지 않는다.

    공고 대응. 첫 호출은 `ids` 와 batch 를 순서대로 잇는다. 뒤의 1건 재시도는 **system 을 뺀
    메시지들의 digest** 로 첫 batch 를 되짚는다. `build_user_prompt` 가 첫 줄에 `[Notice ID]` 를
    넣으므로 그 digest 는 **구조적으로 공고마다 유일하다** — 추측이 아니다.
    그래도 프롬프트 형식이 그 줄을 잃으면 대응이 무너지므로, digest 가 첫 batch 안에서
    유일할 때만 id 를 확정하고 중복이면 `identity_status="ambiguous"` 로 남긴다.
    추론을 다른 공고에 붙이거나 본문으로 id 를 추측하지 않는다.
    """
    original = runner.chat
    had_own = "chat" in vars(runner)
    known, seq = {}, 0

    def body_digest(messages):
        return digest([m for m in messages if m.get("role") != "system"])

    def identify(messages, index):
        if not known:
            return (ids[index] if index < len(ids) else None), "initial"
        found = known.get(body_digest(messages))
        if found is None:
            return None, "unmatched"
        return (found[0], "matched") if len(found) == 1 else (None, "ambiguous")

    def chat(batch, sampling_params=None, items=None):
        nonlocal seq
        seq += 1
        call_seq, first = seq, not known
        if first:
            for index, messages in enumerate(batch):
                known.setdefault(body_digest(messages), []).append(
                    ids[index] if index < len(ids) else None)
        marks = []
        for index, messages in enumerate(batch):
            identifier, status = (ids[index] if index < len(ids) else None, "initial") \
                if first else identify(messages, index)
            parameters = sampling_params if sampling_params is not None else getattr(runner, "sp", None)
            marks.append((index, identifier, status))
            emit("model_call_started", phase=phase, call_seq=call_seq, call_index=index,
                 id=identifier, identity_status=status,
                 call_kind="initial" if first else "retry",
                 prompt_text=messages, prompt_sha256=digest(messages),
                 items=list(items) if items else None,
                 max_tokens=getattr(parameters, "max_tokens", None),
                 schema_sha256=digest(getattr(getattr(parameters, "structured_outputs", None),
                                              "json", None)))
        try:
            texts = original(batch, **({"sampling_params": sampling_params}
                                       if sampling_params is not None else {}),
                             **({"items": items} if items is not None else {}))
        except BaseException as error:
            for index, identifier, status in marks:
                emit("model_call_failed", phase=phase, call_seq=call_seq, call_index=index,
                     id=identifier, identity_status=status, error_type=type(error).__name__,
                     transport_status="failed")
            raise
        info = list(getattr(runner, "last_response_info", []) or [])
        if len(texts) != len(batch):
            for index, identifier, status in marks:
                emit("model_call_failed", phase=phase, call_seq=call_seq, call_index=index,
                     id=identifier, identity_status=status,
                     error_type="ResponseCountMismatch", transport_status="response_count_mismatch")
            return texts
        for index, identifier, status in marks:
            # `last_response_info` 를 통째로 펼치지 않는다 — 이 allowlist 만 복사한다.
            one = info[index] if index < len(info) else {}
            emit("model_call_finished", phase=phase, call_seq=call_seq, call_index=index,
                 id=identifier, identity_status=status, transport_status="returned",
                 response_text=texts[index],
                 **{key: one.get(key) for key in
                    ("prompt_tokens", "output_tokens", "finish_reason", "stop_reason", "max_tokens")})
        return texts

    runner.chat = chat
    try:
        yield
    finally:
        if had_own:
            runner.chat = original
        else:
            del runner.chat


def collect(records, runner, products, emit, budget=None, plan=None, *, observe=False):
    """두 실험이 각자 한 축만 고정한다. 둘은 직교하므로 같이 쓸 수 있다.

    `budget`은 A8처럼 **출력 예약을 바꿔 공통 토큰 예산이 달라진** 실험이 그 값을 명시할 때만
    넘긴다. `plan`은 wiki-rag처럼 **공고별 문서 예산을 미리 고정**해 여러 군이 같은 공고 본문을
    보게 할 때 넘긴다. A8은 `budget`을 5번째 위치 인자로 받고 wiki-rag는 `plan=`을 키워드로
    준다 — 순서를 바꾸면 둘 중 하나가 깨진다.

    `observe=True`는 **실제 모델 요청과 청크 경계를 추가로 기록**한다. 기존 호출자의 메시지·
    스키마·호출 순서·반환 원응답은 바뀌지 않는다 — 기록만 늘어난다.
    """
    budget = script.PROMPT_BUDGET if budget is None else budget
    rows, inference_seconds = [], 0.0
    started = time.perf_counter()
    for start in range(0, len(records), CHUNK):
        group = records[start:start + CHUNK]
        batch, budgets = [], []
        for rec in group:
            company_rec = {**rec, "meta": {k: v for k, v in rec.get("meta", {}).items()
                                         if k != "조항호내용"}}
            planned = MAX_CHARS if plan is None else plan[rec["id"]]
            messages, tokens, chars = script.fit_to_budget(
                company_rec, script.COMPANY_SIZE_PROMPT, runner, planned,
                budget=budget, products=products)
            if plan is not None and chars != planned:
                raise ValueError(f"{rec['id']}: 계획한 문서 예산 {planned}이 토큰 예산을 넘었다")
            batch.append(messages)
            budgets.append((tokens, chars))
            extra = dict(phase="company_size", global_index=start + len(batch) - 1,
                         token_count_kind=getattr(runner, "TOKEN_COUNT", "test_double"),
                         requested_max_chars=planned, truncated=chars < planned,
                         visible_sha256=hashlib.sha256(
                             script.build_context(company_rec, chars).encode("utf-8")).hexdigest(),
                         prompt_messages=messages) if observe else {}
            emit('company_size_input', id=rec['id'], max_chars=chars, prompt_tokens=tokens,
                 prompt_sha256=digest(messages), **extra)
        identifiers = [r["id"] for r in group]
        if observe:
            emit("chunk_started", phase="company_size", chunk_start=start,
                 count=len(group), ids=identifiers)
        before = time.perf_counter()
        # 관측은 이 호출만 감싼다. 저장 IO도 stage 시간에 들어간다 — 시간을 좋게 보이게 하지 않는다.
        try:
            with observe_chat(runner, emit, ids=identifiers, phase="company_size") if observe \
                    else contextlib.nullcontext():
                responses = script.run_chunk(
                    runner, batch, start=start, ids=identifiers, emit=emit,
                    debug_responses=True, items=script.COMPANY_SIZE_KEYS, phase="company_size")
        finally:
            inference_seconds += time.perf_counter() - before
            if observe:
                emit("chunk_finished", phase="company_size", chunk_start=start, count=len(group))
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
