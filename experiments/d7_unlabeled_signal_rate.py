"""D7 게이트가 보는 신호의 무라벨 발화율(W5). 모델을 부르지 않는다.

A4 §5(`reports/team-c/a4-scope-gate/README.md`)와 같은 방식이다 — 규칙의 최종 판정이 아니라
**게이트가 읽는 신호의 보유율**을 dev 200건과 무라벨 20,000건에서 각각 세고 배율을 낸다.

**v5 는 이 경로로 끝까지 잰다.** 반증이 `region_price_limit(rec)`(적용계약법·업무구분)와
`estimated_price(rec)` 두 메타만 보기 때문이다. 모델 출력이 필요 없다.

**v3 는 여기서 기준액까지만 잰다.** 그 게이트는 모델이 낸 인용 안의 실적 금액을 읽으므로
무라벨에 모델 출력이 있어야 한다 — 그것은 GPU 회차이고
`experiments/d7_collect_v3_firing.py` 가 맡는다.

  python -X utf8 experiments/d7_unlabeled_signal_rate.py

무라벨 원본이 없으면 dev 쪽만 내고 종료 코드 2로 멈춘다. 배율을 지어내지 않는다.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNLABELED_SHA256 = "f46449fb84f980a5ddf868d66f5daff2bcf0991135d9b81da5656dd607275698"


def load_script(repo=ROOT):
    spec = importlib.util.spec_from_file_location("submission", Path(repo) / "script.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def file_hash(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def signals(script, records):
    """게이트가 읽는 신호의 보유 건수. 판정이 아니라 **읽히는가**를 센다."""
    total = 0
    counts = {"v5_limit_known": 0, "v5_price_known": 0, "v5_decidable": 0, "v5_refutes": 0,
              "v3_basis_known": 0}
    for rec in records:
        total += 1
        limit = script.region_price_limit(rec)
        price = script.estimated_price(rec)
        counts["v5_limit_known"] += limit is not None
        counts["v5_price_known"] += price is not None
        if limit is not None and price is not None:
            counts["v5_decidable"] += 1
            counts["v5_refutes"] += price < limit
        meta = rec.get("meta") or {}
        counts["v3_basis_known"] += bool(meta.get("입찰추정가격") or meta.get("배정예산금액"))
    return total, counts


def compare(dev, dev_total, unlabeled, unlabeled_total):
    """dev 대비 배율. dev 가 0이면 배율은 None 이다 — 0으로 나누어 숫자를 만들지 않는다."""
    rows = []
    for name in dev:
        base = dev[name] / dev_total if dev_total else None
        other = unlabeled[name] / unlabeled_total if unlabeled_total else None
        rows.append({"signal": name, "dev": base, "unlabeled": other,
                     "multiple": (other / base) if base and other is not None else None})
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=str(ROOT))
    parser.add_argument("--dev", default=str(ROOT / "open/dev.jsonl"))
    parser.add_argument("--unlabeled", default=str(ROOT / "open/train_unlabeled.jsonl"))
    parser.add_argument("--skip-hash", action="store_true",
                        help="무라벨 SHA256 대조를 건너뛴다. 제공 원본이 아니면 결과를 보고에 쓰지 않는다")
    args = parser.parse_args(argv)

    script = load_script(args.repo)
    dev_total, dev = signals(script, script.iter_records(args.dev))

    unlabeled_path = Path(args.unlabeled)
    if not unlabeled_path.is_file():
        print(f"무라벨 입력이 없다: {unlabeled_path}")
        print("dev 쪽만 낸다. 배율은 낼 수 없다 — 안 잰 값을 기대값으로 적지 않는다.\n")
        for name, count in dev.items():
            print(f"  {name:18s} dev {count:5d}/{dev_total} = {count / dev_total:6.1%}")
        return 2

    if not args.skip_hash and file_hash(unlabeled_path) != UNLABELED_SHA256:
        print(f"무라벨 SHA256 불일치: {unlabeled_path}")
        return 1

    unlabeled_total, unlabeled = signals(script, script.iter_records(str(unlabeled_path)))
    rows = compare(dev, dev_total, unlabeled, unlabeled_total)
    print(f"| 신호 | dev {dev_total}건 | 무라벨 {unlabeled_total}건 | 배율 |")
    print("| --- | ---: | ---: | ---: |")
    for row in rows:
        multiple = "—" if row["multiple"] is None else f"{row['multiple']:.2f}"
        print(f"| {row['signal']} | {row['dev']:.1%} | {row['unlabeled']:.1%} | {multiple} |")
    print()
    print(json.dumps({"dev_total": dev_total, "unlabeled_total": unlabeled_total, "rows": rows},
                     ensure_ascii=False, indent=2))
    print("\nv3 의 인용 쪽(실적 금액이 인용 안에 있는가)은 여기서 안 잰다 — 모델 출력이 필요하다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
