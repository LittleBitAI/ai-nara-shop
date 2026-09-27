"""few-shot 예시의 예산을 낸다. 모델을 안 부른다.

`BUDGET.md` 의 §1~§5 를 내는 스크립트다. 계획이 정한 순서의 "먼저" 에 해당한다 —
`docs/tasks/plan-0926-0929.md:275` "예시 토큰이 시간 예산을 먹으므로 먼저 초/건을 잰다".

내는 것 다섯.

  1. 지금의 초/건과 단계별 프롬프트·출력 토큰
  2. 예시 N 토큰의 서버 시간 대가 (계획용 **추정** — 상한이 아니다, 회차가 잰다)
  3. 단계별 토큰 여유 — 예시가 공고 본문을 미는 자리가 어디부터인가 (#166 뒤 남는 호출만)
  4. 절단률 — 토큰 예산이 아니라 `max_chars` 상한이 만드는 별개의 벽
  5. dev 와 진단 200 의 C 항목 양성 수

    py -X utf8 reports/team-c/c-fewshot/budget.py
    py -X utf8 reports/team-c/c-fewshot/budget.py --skip-truncation   # 4·5 를 뺀다
"""

from __future__ import annotations

import argparse
import collections
import csv
import importlib.util
import json
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "reports/runs/colab-1790445336782946136/var-01"
DIAG = ROOT / "reports/labels-600/merged/diag.csv"
# 서버 환산 — `docs/tasks/plan-0926-0929.md`. dev 200건을 1,853건으로 늘린다.
SERVER_NOTICES = 1853
DEV_NOTICES = 200
# 9/27 목표 상한과 `61c495c` 실측. 여유는 실측 쪽으로 잡는다.
SERVER_CEILING = 6800
SERVER_MEASURED = 6428
C_ITEMS = ("v10", "v11", "v13", "v18")


def load_pinned(ref):
    """기준 `script.py` 를 임시 폴더에 풀어 집는다. 작업 트리 판을 쓰지 않는다."""
    source = subprocess.run(["git", "-C", str(ROOT), "show", f"{ref}:script.py"],
                            capture_output=True, check=True).stdout
    path = Path(tempfile.mkdtemp(prefix="c-fewshot-")) / "script.py"
    path.write_bytes(source)
    spec = importlib.util.spec_from_file_location("pinned_script", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def responses(run):
    by_phase, ids = collections.defaultdict(list), collections.defaultdict(list)
    for line in (run / "diagnostics.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("event") == "response":
            by_phase[event.get("phase")].append((event["prompt_tokens"], event["output_tokens"]))
            ids[event.get("phase")].append(event.get("id"))
    return by_phase, ids


def records(path, keep=None):
    with Path(path).open(encoding="utf-8") as stream:
        for line in stream:
            rec = json.loads(line)
            if keep is None or rec["id"] in keep:
                yield rec


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", default=str(RUN))
    # 보고서 수(#166 뒤 호출 165·88)가 `a0d6aea` 에서 났다. 움직이는 `origin/main` 을 기본으로
    # 두면 main 이 바뀔 때 같은 명령이 다른 수를 낸다. 회차 자체의 코드는 `772ca12` 다.
    parser.add_argument("--ref", default="a0d6aea", help="기준 script.py 의 ref")
    parser.add_argument("--skip-truncation", action="store_true",
                        help="절단률·양성 수를 뺀다 (무라벨 20,000건 훑기가 빠진다)")
    args = parser.parse_args(argv)

    run = Path(args.run)
    report = json.loads((run / "run_report.json").read_text(encoding="utf-8"))
    by_phase, phase_ids = responses(run)
    seconds = report["추론_s"]
    count = report["건수"]
    calls = sum(len(v) for v in by_phase.values())
    prompt_total = sum(p for v in by_phase.values() for p, _ in v)

    print("=== 1. 지금의 초/건과 단계별 토큰 ===")
    print(f"  추론 {seconds}s / {count}건 = {seconds / count:.3f} 초/건 · 호출 {calls}회"
          f" = {calls / count:.2f} 회/건")
    print(f"  {'단계':14}{'호출':>6}{'프롬프트 중앙':>14}{'프롬프트 합':>14}{'출력 합':>10}")
    for phase, values in by_phase.items():
        prompts = [p for p, _ in values]
        outputs = [o for _, o in values]
        print(f"  {phase:14}{len(values):>6}{statistics.median(prompts):>14.0f}"
              f"{sum(prompts):>14,}{sum(outputs):>10,}")

    script = load_pinned(args.ref)

    # PR #166 이 수의계약 공고에서 `sme` · `company_size` 호출을 건너뛴다. 이 회차는 그
    # 이전 것이라 호출 수가 그대로다 — 남는 호출만 세어 다시 잡는다. 안 고치면 없어진
    # 호출에까지 예시 값을 매겨 대가를 부풀린다.
    quotes = {rec["id"] for rec in records(ROOT / "open/dev.jsonl")
              if not script.needs_extra_call(rec)}
    skipped = {"sme", "company_size"}
    live = {phase: (len(values) - sum(1 for _ in quotes) if phase in skipped else len(values))
            for phase, values in by_phase.items()}
    # `sme` 는 선택된 공고에만 붙으므로 그중 수의계약이 몇인지 따로 센다.
    sme_ids = [e for e in ()]  # 회차 로그에 단계별 id 가 있으면 쓴다
    for line in (run / "diagnostics.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("event") == "response" and event.get("phase") == "sme":
            sme_ids.append(event.get("id"))
    if all(i for i in sme_ids):
        live["sme"] = sum(1 for i in sme_ids if i not in quotes)

    per_1k = seconds / prompt_total * 1000
    print("\n=== 2. 예시 N 토큰의 서버 시간 대가 (계획용 추정 — 상한 아님) ===")
    print(f"  프롬프트 1,000토큰당 {per_1k:.4f}s")
    print(f"  여유 {SERVER_CEILING - SERVER_MEASURED}초"
          f" (목표 상한 {SERVER_CEILING:,} − 61c495c 실측 {SERVER_MEASURED:,})")
    print(f"  PR #166: dev {len(quotes)}건이 수의계약 → sme·company_size 호출이 없다")
    sizes = (200, 400, 800, 1600)
    print(f"  {'단계':14}{'호출(#166 뒤)':>14}" + "".join(f"{f'+{s}':>10}" for s in sizes))
    for phase, values in by_phase.items():
        row = []
        for size in sizes:
            dev_seconds = size * live[phase] * seconds / prompt_total
            row.append(f"{dev_seconds * SERVER_NOTICES / DEV_NOTICES:>9.0f}s")
        print(f"  {phase:14}{live[phase]:>14}" + "".join(row))
    print("  → 호출 수는 #166 뒤 값이고 1,000토큰당 시간은 그 이전 회차의 실측이다."
          " 둘을 섞은 추정이므로 회차가 실측한다")
    budget = script.PROMPT_BUDGET
    print(f"\n=== 3. 토큰 여유 (예산 {budget:,} − 그 호출, #166 뒤 남는 호출만) ===")
    print(f"  {'단계':14}{'호출':>6}{'여유 중앙':>10}" + "".join(f"{f'≥{s}':>8}" for s in sizes))
    for phase, values in by_phase.items():
        head = [budget - p for (p, _), i in zip(values, phase_ids[phase])
                if phase not in skipped or i not in quotes]
        share = "".join(f"{sum(h >= s for h in head) / len(head):>7.0%} " for s in sizes)
        print(f"  {phase:14}{len(head):>6}{statistics.median(head):>10.0f}  {share}")
    print("  → 여유보다 큰 예시를 넣으면 fit_messages 가 max_chars 를 줄여 본문이 잘린다")

    if args.skip_truncation:
        print("\n(4·5 는 --skip-truncation 으로 건너뛰었다)")
        return 0

    print("\n=== 4. 절단률 — max_chars 상한이 만드는 별개의 벽 ===")
    for path, label, keep in ((ROOT / "open/dev.jsonl", "dev", None),
                              (ROOT / "open/train_unlabeled.jsonl", "진단 200",
                               {r["id"] for r in csv.DictReader(DIAG.open(encoding="utf-8",
                                                                          newline=""))})):
        cut = missing = total = 0
        over = 0
        for rec in records(path, keep):
            total += 1
            visible = script.build_context(rec, max_chars=16000)
            cut += "[Truncated documents; unseen remainder]" in visible
            missing += "[Missing documents]" in visible
            over += sum(len(d["text"]) for d in rec["docs"]) > 16000

        print(f"  {label:10} {total}건 중 절단 {cut}건({cut / total:.1%})"
              f" · 문서 누락 {missing}건 · 16,000자 초과 {over}건")
    print("  → 절단은 토큰 예산이 아니라 max_chars 16,000 탓이다."
          " 절단은 부재탐지 규칙의 complete 게이트만 닫는다 — 모델의 1 은 안 막는다(trace.py --flip)")

    print("\n=== 5. C 항목 양성 수 — off-dev 기판이 두껍다 ===")
    truth = {r["id"]: r for r in csv.DictReader((ROOT / "open/dev_labels.csv").open(
        encoding="utf-8", newline=""))}
    diag = {r["id"]: r for r in csv.DictReader(DIAG.open(encoding="utf-8", newline=""))}
    print(f"  {'항목':6}{'dev 200':>10}{'진단 200':>10}")
    for item in C_ITEMS:
        dev_pos = sum(row[item] == "1" for row in truth.values())
        diag_pos = sum(row[item] == "1" for row in diag.values())
        print(f"  {item:6}{dev_pos:>10}{diag_pos:>10}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
