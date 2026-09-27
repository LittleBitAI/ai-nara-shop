"""오탐·누락을 파이프라인 다섯 지점으로 추적한다. 모델을 안 부른다.

`TARGET.md` §3 이 처음에 **원응답과 최종 두 점**만 봤다. 그래서 가운데에서 올라갔다
내려오는 셀을 "모델이 0" 으로 잘못 분류했다. 이 스크립트가 그 가운데를 연다.

지점 다섯. `tools/replay_run.py` 의 `replay()` 순서를 그대로 밟는다 — 내 추측이 아니라
재생기가 실제로 부르는 차례다.

  1. `raw`        `parse_judgment(baseline 원응답)`
  2. `post0`      그 위에 `postprocess` — 재생기의 `baseline_rows`.
                  **곁가지다.** `postprocess` 는 `parsed` 를 안 고치므로 이 값은 사슬로
                  이어지지 않는다. `post0` 가 1 인데 `phases` 가 0 인 것은 내려간 것이
                  아니라 **다른 갈래를 본 것**이다 — 사슬은 `raw→thr→phases→sme→cs→final` 이다
  3. `phases`     `merge_extra_call`(split·product) 뒤
  4. `sme`        `verify_sme` 뒤
  5. `cs`         `verify_company_size` 뒤
  6. `final`      맨 끝 `postprocess`

`0 → 1 → 0` 처럼 가운데가 솟는 셀이 있으면 고칠 곳은 모델이 아니라 그 단계다.

    py -X utf8 reports/team-c/c-fewshot/trace.py
    py -X utf8 reports/team-c/c-fewshot/trace.py --items v10 v18
"""

from __future__ import annotations

import argparse
import collections
import csv
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SHARDS = ROOT / "reports/label-compare/unlabeled-d"
DIAG = ROOT / "reports/labels-600/merged/diag.csv"
UNLABELED = ROOT / "open/train_unlabeled.jsonl"
DATA = ROOT / "open/data"
POINTS = ("raw", "thr", "post0", "phases", "sme", "cs", "final")


def pinned(ref):
    source = subprocess.run(["git", "-C", str(ROOT), "show", f"{ref}:script.py"],
                            capture_output=True, check=True).stdout
    path = Path(tempfile.mkdtemp(prefix="c-trace-")) / "script.py"
    path.write_bytes(source)
    spec = importlib.util.spec_from_file_location("pinned_script", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def shard_texts(shard):
    """한 샤드의 단계별 원응답과 기업규모 입력 예산."""
    texts = collections.defaultdict(dict)
    chars, probabilities = {}, {}
    for line in (shard / "output/diagnostics.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("event") == "response" and "response_text" in event:
            texts[event.get("phase")][event["id"]] = event["response_text"]
        elif event.get("event") == "company_size_input":
            chars[event["id"]] = event["max_chars"]
        if (event.get("event") == "response" and event.get("phase") == "baseline"
                and event.get("item_p1")):
            probabilities[event["id"]] = event["item_p1"]
    return texts, chars, probabilities


def verdict(cells, item):
    cell = (cells or {}).get(item)
    return None if cell is None else cell.get("위반여부")


def trace_shard(script, shard, wanted, items, settings):
    """`tools/replay_run.py::replay()` 의 차례를 그대로 밟으며 지점마다 값을 적는다."""
    texts, chars, probabilities = shard_texts(shard)
    ids = set(json.loads((shard / "ids.json").read_text(encoding="utf-8")))
    _, products = script.load_sme_reference(str(DATA))
    max_chars = settings.get("max_chars", 16000)
    out = {}
    with UNLABELED.open(encoding="utf-8") as stream:
        for line in stream:
            rec = json.loads(line)
            key = rec["id"]
            if key not in ids or key not in wanted:
                continue
            text = texts["baseline"].get(key)
            if text is None:
                continue
            parsed, _ = script.parse_judgment(text)
            steps = {"raw": {i: verdict(parsed, i) for i in items}}
            # 재생기가 `parse_judgment` 바로 뒤에 임계를 적용한다. 빠뜨리면 모델이 1 이라
            # 했는데 임계가 내린 셀을 "모델이 0" 으로 잘못 읽는다.
            thresholded = getattr(script, "apply_thresholds", None)
            if thresholded is not None:
                parsed = thresholded(parsed, probabilities.get(key))
            steps["thr"] = {i: verdict(parsed, i) for i in items}
            first = script.postprocess(parsed, rec)
            steps["post0"] = {i: verdict(first, i) for i in items}
            for phase in getattr(script, "VERDICT_PHASES", ()):
                script.merge_extra_call(parsed, rec, phase,
                                        script.extra_call_items().get(phase) or (),
                                        texts.get(phase, {}).get(key))
            steps["phases"] = {i: verdict(parsed, i) for i in items}
            extra = getattr(script, "needs_extra_call", lambda r: True)(rec)
            sme_text = texts["sme"].get(key) if extra else None
            if sme_text is not None:
                focused, _ = script.parse_judgment(sme_text, expected_items=script.SME_ITEMS,
                                                   sme=True)
                verified, _ = script.verify_sme(focused, rec, products, max_chars)
                parsed.update(verified)
            steps["sme"] = {i: verdict(parsed, i) for i in items}
            company = texts.get("company_size", {}).get(key) if extra else None
            if company is not None and key in chars:
                legacy = {}
                if (hasattr(script, "DOCUMENT_CHECK_ITEMS")
                        and not settings.get("company_size_document_checks")):
                    legacy["company_size_legacy"] = True
                if hasattr(script, "CLAUSE_QUOTE_MAX"):
                    legacy["company_size_clause_quotes"] = bool(
                        settings.get("company_size_clause_quotes"))
                if hasattr(script, "QUALIFICATION_ROLES"):
                    legacy["company_size_qualification_role"] = bool(
                        settings.get("company_size_qualification_role"))
                focused, _ = script.parse_judgment(company,
                                                   expected_items=script.COMPANY_SIZE_KEYS,
                                                   **legacy)
                verified, _ = script.verify_company_size(focused["company_size"], rec, chars[key])
                parsed.update(verified)
            steps["cs"] = {i: verdict(parsed, i) for i in items}
            last = script.postprocess(parsed, rec)
            steps["final"] = {i: verdict(last, i) for i in items}
            out[key] = steps
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ref", default="origin/main")
    parser.add_argument("--items", nargs="+", default=["v10", "v11", "v13", "v18"])
    args = parser.parse_args(argv)

    script = pinned(args.ref)
    diag = {row["id"]: row for row in csv.DictReader(DIAG.open(encoding="utf-8", newline=""))}
    traces = {}
    for shard in sorted(SHARDS.glob("run-*/u*")):
        if not (shard / "output/diagnostics.jsonl").is_file():
            continue
        report = json.loads((shard / "output/run_report.json").read_text(encoding="utf-8"))
        settings = report.get("reproduction", {}).get("settings", {})
        traces.update(trace_shard(script, shard, set(diag), args.items, settings))
    print(f"진단 200 중 추적한 공고 {len(traces)}건 · 기준 {args.ref}\n")

    for item in args.items:
        wrong = []
        for key, steps in traces.items():
            label = diag[key][item]
            final = steps["final"][item]
            if (label == "1") != (final == 1):
                wrong.append((key, label, steps))
        print(f"=== {item} — 틀린 셀 {len(wrong)}건 ===")
        shapes = collections.Counter()
        risen = []
        for key, label, steps in wrong:
            path = [steps[p][item] for p in POINTS]
            shape = "→".join("·" if v is None else str(v) for v in path)
            shapes[(label, shape)] += 1
            # 가운데가 솟았다가 내려온 셀 — 모델 탓이 아니다. **사슬만** 본다
            # (`post0` 은 곁가지라 뺀다 — 위 docstring).
            chain = [steps[p][item] for p in POINTS if p != "post0"]
            seen = [v for v in chain if v is not None]
            if label == "1" and seen and seen[-1] == 0 and 1 in seen:
                where = next(p for p, a, b in zip(
                    [q for q in POINTS if q != "post0"][1:], chain, chain[1:]) if a == 1 and b == 0)
                risen.append((key, shape, where))
        print(f"  {'라벨':4}{'raw→thr→post0→phases→sme→cs→final':40}{'건수':>4}")
        for (label, shape), n in sorted(shapes.items(), key=lambda kv: -kv[1]):
            print(f"  {label:^4}{shape:40}{n:>4}")
        if risen:
            print(f"  ** 가운데가 솟았다 내려온 누락 {len(risen)}건 — 모델이 아니라 그 단계다 **")
            for key, shape, where in risen:
                print(f"     {key}  {shape}   내린 단계: {where}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
