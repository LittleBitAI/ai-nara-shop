"""§7 의 가설 셋을 잰다. 모델을 안 부른다. GPU 도 안 쓴다.

세 측정이 각각 하나의 물음에 답한다.

  1. 명시적 제외 문구 — dev 와 무라벨에서 발화율이 같은가, 걸린 문구가 같은 뜻인가
  2. 제출서류 목록 — 목록 꼴 인용 중 **지금 맞는 판정**이 몇 건인가
  3. `069` 의 게이트 — `complete` 의 네 조건 중 무엇이 닫혔나

세 결과는 `README.md` §7 이 소유한다. 이 스크립트는 그 수를 다시 내기만 한다.

    py -X utf8 reports/team-c/v10-v11-v13-breakdown/hypotheses.py
    py -X utf8 reports/team-c/v10-v11-v13-breakdown/hypotheses.py --skip-unlabeled

무라벨 20,000건 훑기가 가장 오래 걸린다(수십 초). `--skip-unlabeled` 로 뺀다.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "reports/runs/colab-1790445336782946136/var-01"
BASE_REV = "772ca12"

# 가설 1 — `23` 의 문구를 일반화한 것. 특정 공고 문구를 그대로 박지 않으려고 넓게 잡았고,
# 넓게 잡은 결과가 무라벨에서 다른 뜻을 줍는다는 것이 이 측정의 결론이다.
EXCLUSION = re.compile(r"직접생산(?:확인)?(?:품목|대상)?[^.。\n]{0,20}제외"
                       r"|경쟁제품[^.。\n]{0,20}제외"
                       r"|일반물품으로\s*(?:입찰)?공고")
# 가설 2 — 목록 항목의 머리. `가.`~`하.` 와 `1)` `2)` 꼴.
LIST_ITEM = re.compile(r"^\s*(?:[가-하]\s*[.)]|\(?\d{1,2}\s*[.)])")


def read_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as stream:
        return {row["id"]: row for row in csv.DictReader(stream)}


def records(path):
    with Path(path).open(encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def full_text(rec):
    return "\n".join(d["text"] for d in rec["docs"])


def company_size_facts(run):
    """회차가 남긴 원응답에서 company_size 단계의 사실값을 꺼낸다."""
    out = {}
    for line in (run / "diagnostics.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("event") != "response" or event.get("phase") != "company_size":
            continue
        try:
            out[event["id"]] = json.loads(event["response_text"])["company_size"]
        except (KeyError, ValueError):
            continue
    return out


def pinned_script():
    """기준 커밋의 `script.py` 를 집는다. 작업 트리 판을 쓰지 않는다."""
    source = subprocess.run(["git", "-C", str(ROOT), "show", f"{BASE_REV}:script.py"],
                            capture_output=True, check=True).stdout
    # 저장소 안에 쓰지 않는다. 작업 트리도 `.git/` 도 이 스크립트의 자리가 아니다.
    path = Path(tempfile.mkdtemp(prefix="c-breakdown-")) / "script.py"
    path.write_bytes(source)
    spec = importlib.util.spec_from_file_location("pinned_script", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hypothesis_one(dev, truth, final, skip_unlabeled):
    print("=== 가설 1 — 명시적 제외 문구 ===")
    hits = [(r["id"], m) for r in dev if (m := EXCLUSION.search(full_text(r)))]
    print(f"  dev {len(dev)}건 중 발화 {len(hits)}건 · 발화율 {len(hits) / len(dev):.5f}")
    for key, match in sorted(hits):
        label, now = truth[key]["v10"], final[key]["v10"]
        kind = {("0", "1"): "FP — 닫으면 이득", ("1", "1"): "TP — 닫으면 손해",
                ("1", "0"): "FN", ("0", "0"): "TN — 닫아도 그대로"}[(label, now)]
        print(f"    {key:14} v10 정답 {label} / 현재 {now}   {kind}")
        print(f"      …{match.group(0)[:70]}…")
    if skip_unlabeled:
        print("  무라벨은 건너뛰었다 (--skip-unlabeled)")
        return
    unlabeled = ROOT / "open/train_unlabeled.jsonl"
    total = found = 0
    samples = []
    for rec in records(unlabeled):
        total += 1
        text = full_text(rec)
        match = EXCLUSION.search(text)
        if match:
            found += 1
            start = max(0, match.start() - 25)
            samples.append((rec["id"], text[start:match.end() + 35].replace("\n", " ")))
    print(f"  무라벨 {total}건 중 발화 {found}건 · 발화율 {found / total:.5f}")
    for key, context in samples[:6]:
        print(f"    {key}\n      …{context[:110]}…")
    print("  → 걸린 문구의 뜻이 같은지는 사람이 읽는다. README §7 이 그 판단을 소유한다.")


def hypothesis_two(truth, final, facts):
    print("\n=== 가설 2 — 제출서류 목록 꼴 ===")
    pool = [(key, f.get("direct_production_quote")) for key, f in facts.items()
            if f.get("scope") == "competitive" and f.get("direct_production_quote")]
    listed = [(key, quote) for key, quote in pool if LIST_ITEM.match(quote)]
    print(f"  scope=competitive 이고 인용이 있는 공고 {len(pool)}건 · 그중 목록 꼴 {len(listed)}건")
    right = wrong = 0
    for key, quote in sorted(listed):
        label, now = truth[key]["v10"], final[key]["v10"]
        ok = label == now
        right += ok
        wrong += not ok
        print(f"    {key:14} 정답 {label} / 현재 {now}  {'지금 맞음' if ok else '지금 틀림'}"
              f"   {quote[:44]}")
    print(f"  → 목록 꼴 {len(listed)}건 중 **{right}건이 지금 맞는 판정**이다."
          f" 부재로 뒤집으면 그만큼 FP 가 생긴다 (지금 틀린 것은 {wrong}건).")


def hypothesis_three(dev, script):
    print("\n=== 가설 3 — `069` 의 게이트는 어디서 닫혔나 ===")
    watch = ("PPS-DEV-069", "PPS-DEV-13", "PPS-DEV-075")
    index = {r["id"]: r for r in dev if r["id"] in watch}
    print(f"  {'공고':16}{'완전관측':10}{'dropped':16}{'문자':>8}  {'절단':6}{'누락':6}complete")
    for key in watch:
        rec = index[key]
        visible = script.build_context(rec, max_chars=16000)
        observed = (rec.get("input_completeness") or {}).get("완전관측")
        dropped = {k: v for k, v in (rec.get("dropped_doc_counts") or {}).items() if v}
        truncated = "[Truncated documents; unseen remainder]" in visible
        missing = "[Missing documents]" in visible
        complete = observed is True and not dropped and not truncated and not missing
        chars = sum(len(d["text"]) for d in rec["docs"])
        print(f"  {key:16}{str(observed):10}{str(dropped or '없음'):16}{chars:>8}  "
              f"{str(truncated):6}{str(missing):6}{complete}")
    print("  → 절단·누락은 부재탐지가 일부러 멈추는 자리다(`docs/items.md:51`)."
          " 이 둘은 고치지 않는다.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", default=str(RUN), help="원응답이 있는 통과 폴더")
    parser.add_argument("--truth", default=str(ROOT / "open/dev_labels.csv"))
    parser.add_argument("--dev", default=str(ROOT / "open/dev.jsonl"))
    parser.add_argument("--skip-unlabeled", action="store_true",
                        help="무라벨 20,000건 훑기를 뺀다")
    args = parser.parse_args(argv)

    run = Path(args.run)
    dev = list(records(args.dev))
    truth = read_csv(args.truth)
    final = read_csv(run / "submission.csv")
    facts = company_size_facts(run)

    hypothesis_one(dev, truth, final, args.skip_unlabeled)
    hypothesis_two(truth, final, facts)
    hypothesis_three(dev, pinned_script())
    return 0


if __name__ == "__main__":
    sys.exit(main())
