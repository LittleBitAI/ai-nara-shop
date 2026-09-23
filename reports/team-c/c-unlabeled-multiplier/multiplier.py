"""C 항목의 무라벨 발화 배율 — dev 200건 대비 무라벨 2,000건. 모델을 부르지 않는다.

배율 = (무라벨 발화 수 ÷ 무라벨 건수) ÷ (dev 발화 수 ÷ dev 건수).

**두 쪽을 같은 코드로 맞춘다.** 무라벨 회차는 `14f03d1` 로 돌았으므로 dev 쪽도 그 코드로
보관 회차를 재생해서 낸다. `main` HEAD 재생을 쓰면 다른 저울이다.

    # 1. 무라벨 회차 CSV 를 꺼낸다 (아직 main 에 없다 — §1 참고)
    git show origin/feat/unlabeled-d-run:reports/label-compare/unlabeled-d/\
run-1790141381430477242/u00/output/submission.csv > <unl>/u00.csv   # u00~u03

    # 2. dev 를 같은 코드로 재생한다
    git show 14f03d1:script.py > <tmp>/script_14f03d1.py
    py -X utf8 tools/replay_run.py \
      --case reports/runs/colab-1789902969401579900/dev-debug \
      --script <tmp>/script_14f03d1.py --output-dir <tmp>/dev14f

    # 3. 센다
    py -X utf8 reports/team-c/c-unlabeled-multiplier/multiplier.py \
      --unlabeled <unl> --dev <tmp>/dev14f/submission.csv

무라벨에는 정답이 없다. 이 스크립트는 **발화율만** 낸다. 오탐 수가 아니다.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ITEMS = ["v10", "v11", "v12", "v13", "v14", "v15", "v16", "v17", "v18", "v20"]


def ratio_interval(dev_k, dev_n, unl_k, unl_n, z=1.96):
    """배율(두 이항 비율의 비)의 95% 구간 — Katz 로그법.

    **양쪽의 불확실성을 같이 넣는다.** 처음 판은 dev 쪽만 넣었는데, 무라벨 쪽 분모가
    열 배라고 해서 그쪽 분자가 확실한 것은 아니다. v12 는 무라벨 발화가 14건뿐이라
    그 항을 빼면 상한이 0.90 으로 나오고 넣으면 **1.05** 로 나온다 — 판정이 뒤집힌다.
    """
    if not dev_k or not unl_k:
        return (None, None)          # 한쪽이 0 이면 로그법을 못 쓴다. 미정으로 둔다
    ratio = (unl_k / unl_n) / (dev_k / dev_n)
    spread = math.sqrt(1 / dev_k - 1 / dev_n + 1 / unl_k - 1 / unl_n)
    return (ratio * math.exp(-z * spread), ratio * math.exp(z * spread))


def direction(low, high):
    """구간이 1 을 물면 방향을 말하지 않는다. 점추정을 방향으로 읽지 않는다."""
    if low is None or (low <= 1 <= high):
        return "미정"
    return "더 적다" if high < 1 else "더 많다"


def read_rows(paths):
    rows = []
    for path in sorted(paths):
        with Path(path).open(encoding="utf-8", newline="") as stream:
            rows += list(csv.DictReader(stream))
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--unlabeled", required=True, help="무라벨 회차 CSV 들이 있는 디렉터리")
    parser.add_argument("--dev", required=True, help="같은 코드로 재생한 dev submission.csv")
    parser.add_argument("--labels", default=str(ROOT / "open/dev_labels.csv"))
    parser.add_argument("--out", default=str(Path(__file__).with_name("multiplier.json")))
    args = parser.parse_args(argv)

    unlabeled = read_rows(Path(args.unlabeled).glob("*.csv"))
    dev = read_rows([args.dev])
    with Path(args.labels).open(encoding="utf-8", newline="") as stream:
        truth = {r["id"]: r for r in csv.DictReader(stream)}

    seen = {r["id"] for r in unlabeled}
    if len(seen) != len(unlabeled):
        raise SystemExit(f"무라벨 공고가 겹친다: {len(unlabeled)}행 · {len(seen)}건")

    out = {"dev_n": len(dev), "unlabeled_n": len(unlabeled), "items": {}}
    for item in ITEMS:
        fired_dev = [r for r in dev if r[item] == "1"]
        fired_unl = sum(r[item] == "1" for r in unlabeled)
        tp = sum(truth[r["id"]][item] == "1" for r in fired_dev)
        dev_rate = len(fired_dev) / len(dev)
        unl_rate = fired_unl / len(unlabeled)
        low, high = ratio_interval(len(fired_dev), len(dev), fired_unl, len(unlabeled))
        out["items"][item] = {
            "dev_fired": len(fired_dev), "dev_rate": dev_rate,
            "unlabeled_fired": fired_unl, "unlabeled_rate": unl_rate,
            "multiplier": (unl_rate / dev_rate) if dev_rate else None,
            # 배율의 95% 구간. 구간이 1 을 물면 방향을 말할 수 없다.
            "multiplier_low": low, "multiplier_high": high,
            "direction": direction(low, high),
            "dev_tp": tp, "dev_fp": len(fired_dev) - tp,
        }

    # 줄끝을 LF 로 고정한다. 기본값으로 열면 윈도에서 CRLF 로 나간다.
    with io.open(args.out, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(out, stream, ensure_ascii=False, indent=1)
        stream.write("\n")

    # f-string 안에서 바깥과 같은 따옴표를 다시 쓰지 않는다. 그 문법은 3.12 부터이고
    # 이 저장소가 지원하는 3.11 에서는 파싱 자체가 실패한다.
    print(f'{"항목":<6}{"dev 발화":>9}{"dev율":>8}{"무라벨":>8}{"무라벨율":>10}'
          f'{"배율":>7}{"95% 구간":>16}{"방향":>7}{"dev TP/FP":>11}')
    for item in ITEMS:
        row = out["items"][item]
        low, high = row["multiplier_low"], row["multiplier_high"]
        span = "미산출" if low is None else "[{:.2f}, {:.2f}]".format(low, high)
        score = "{}/{}".format(row["dev_tp"], row["dev_fp"])
        print(f'{item:<6}{row["dev_fired"]:>9}{row["dev_rate"]:>8.3f}'
              f'{row["unlabeled_fired"]:>8}{row["unlabeled_rate"]:>10.4f}'
              f'{row["multiplier"]:>7.2f}{span:>16}{row["direction"]:>7}{score:>11}')
    print(f'dev {out["dev_n"]}건 · 무라벨 {out["unlabeled_n"]}건')


if __name__ == "__main__":
    main()
