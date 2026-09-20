"""A1 입력 분포 사전 점검과 실제 dev/무라벨 6,000건 발화율 대조. 모델 호출 없음.

--dev-case/--unlabeled-case가 없으면 발화율은 null이다. 입력 분포를 성과로 세지 않는다.
두 실제 회차가 있으면 같은 코드·설정·입력·ID·성공 건수를 확인한 뒤 대조한다.
"""

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import script  # noqa: E402
from tools import compare_runs  # noqa: E402


def profile(path, limit):
    recs = list(script.iter_records(str(path), limit=limit))
    bands = Counter()
    for rec in recs:
        price = script.estimated_price(rec)
        bands["unknown" if price is None else "below_100m" if price < script.SME_BAND_FLOOR_WON
              else "100m_to_notice" if price < script.NOTICE_AMOUNT_WON else "at_least_notice"] += 1
    return recs, {"count": len(recs), "input_sha256": script.file_sha256(path),
                  "records_sha256": script.records_sha256(recs),
                  "selection": "input_order_prefix", "limit": limit, "price_bands": dict(bands),
                  "complete_input_count": sum(r.get("input_completeness", {}).get("완전관측") is True for r in recs)}


def measured(case, recs, records_sha256):
    report = json.loads((case / "run_report.json").read_text(encoding="utf-8"))
    n = len(recs)
    if report.get("mode") != "live" or report.get("model_success_count") != n:
        raise ValueError("실제 고정 모델 전건 성공 회차가 아니다 (mock/api 불가)")
    if report["건수"] != n or report["records_sha256"] != records_sha256:
        raise ValueError("회차와 카나리 입력/건수가 다르다")
    if report.get("company_size_selected_count") != n:
        raise ValueError("기업규모 추출이 전건 선택되지 않았다")
    response_count = report.get("company_size_response_count", 0)
    if report.get("company_size_model_success_count") != response_count:
        raise ValueError("기업규모 정상 호출 기록이 다르다")
    if response_count + report.get("company_size_fallback_count", 0) != n:
        raise ValueError("기업규모 호출 성공/실패 건수 불일치")
    ids = [r["id"] for r in recs]
    expected_ids = set(ids)
    counts = {}
    for name in ("submission.csv", "company_size_baseline_submission.csv"):
        path = case / name
        errors = script.validate_csv(str(path), ids)
        if errors:
            raise ValueError(str(errors))
        with path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        counts[name] = {v: sum(row[v] == "1" for row in rows) for v in script.BAND_ITEMS}
    firings, seen = Counter(), set()
    with (case / "diagnostics.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            if event.get("event") != "company_size_verified":
                continue
            if event["id"] in seen or event["id"] not in expected_ids:
                raise ValueError("기업규모 진단 ID 중복/불일치")
            seen.add(event["id"])
            firings.update(v for v, value in event["flags"].items() if value == 1)
    if len(seen) != response_count:
        raise ValueError("기업규모 판정 진단 건수 불일치")
    return report, {"count": n, "fallback_count": report["company_size_fallback_count"],
                    "decisions": report["company_size_decisions"], "csv_positive_counts": counts,
                    "firings": {v: firings[v] for v in script.BAND_ITEMS},
                    "firing_rates": {v: firings[v] / n for v in script.BAND_ITEMS}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dev-input", type=Path, default=ROOT / "open/dev.jsonl")
    parser.add_argument("--unlabeled-input", type=Path, default=ROOT / "open/train_unlabeled.jsonl")
    parser.add_argument("--dev-case", type=Path)
    parser.add_argument("--unlabeled-case", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if bool(args.dev_case) != bool(args.unlabeled_case):
        parser.error("두 실제 회차를 함께 지정한다")
    dev, dp = profile(args.dev_input, 200)
    unlabeled, up = profile(args.unlabeled_input, 6000)
    if len(dev) != 200 or len(unlabeled) != 6000:
        parser.error("dev 200건/무라벨 6000건이 필요하다")
    result = {"status": "input_preflight_only", "model_called": False,
              "script_sha256": script.file_sha256(ROOT / "script.py"),
              "dev": dp, "unlabeled": up, "firing_rate_ratio": None}
    if args.dev_case:
        dr, dm = measured(args.dev_case, dev, dp["records_sha256"])
        ur, um = measured(args.unlabeled_case, unlabeled, up["records_sha256"])
        if dr["code_sha256"] != ur["code_sha256"] or dr["code_sha256"] != result["script_sha256"]:
            raise ValueError("두 회차/현재 코드가 다르다")
        keys = ("company_size_items", "split_items", "product_items", "seed", "quant", "max_chars", "max_tokens")
        ds, us = dr["reproduction"]["settings"], ur["reproduction"]["settings"]
        if any(ds[k] != us[k] for k in keys):
            raise ValueError("dev/무라벨 실행 설정이 다르다")
        if ds["split_items"] or ds["product_items"] or ds["company_size_items"] != script.BAND_ITEMS:
            raise ValueError("A1 외 실험이 섞여 있다")
        result.update(status="live_outputs_measured", dev_measurement=dm, unlabeled_measurement=um,
                      firing_rate_ratio={v: um["firing_rates"][v] / dm["firing_rates"][v]
                                         if dm["firing_rates"][v] else None for v in script.BAND_ITEMS})
        result["paired_comparison"] = compare_runs.compare(
            compare_runs.load_score(), ROOT / "open/dev_labels.csv",
            args.dev_case / "company_size_baseline_submission.csv", args.dev_case / "submission.csv",
            script.BAND_ITEMS)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
