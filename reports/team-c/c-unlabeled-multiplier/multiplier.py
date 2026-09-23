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
from statistics import NormalDist

ROOT = Path(__file__).resolve().parents[3]
ITEMS = ["v10", "v11", "v12", "v13", "v14", "v15", "v16", "v17", "v18", "v20"]


# 항목별 명목 구간. 한 항목만 미리 정해 놓고 봤다면 이것을 쓴다.
Z_NOMINAL = NormalDist().inv_cdf(0.975)
# 열 항목을 한 번에 훑고 그중 튀는 것을 고르므로 다중비교 보정이 필요하다.
# Bonferroni — 항목마다 0.05/10 을 쓴다. 이래야 "열 중 어느 하나라도 헛발" 확률이 5% 다.
Z_SIMULTANEOUS = NormalDist().inv_cdf(1 - 0.05 / len(ITEMS) / 2)


def ratio_interval(dev_k, dev_n, unl_k, unl_n, z=Z_NOMINAL):
    """배율(두 이항 비율의 비)의 신뢰구간 — Katz 로그법.

    **양쪽의 불확실성을 같이 넣는다.** 처음 판은 dev 쪽만 넣었는데, 무라벨 쪽 분모가
    열 배라고 해서 그쪽 분자가 확실한 것은 아니다. v12 는 무라벨 발화가 14건뿐이라
    그 항을 빼면 상한이 0.90 으로 나오고 넣으면 **1.05** 로 나온다 — 판정이 뒤집힌다.
    """
    if not dev_k or not unl_k:
        return (None, None)          # 한쪽이 0 이면 로그법을 못 쓴다. 미정으로 둔다
    ratio = (unl_k / unl_n) / (dev_k / dev_n)
    spread = math.sqrt(1 / dev_k - 1 / dev_n + 1 / unl_k - 1 / unl_n)
    return (ratio * math.exp(-z * spread), ratio * math.exp(z * spread))


def constrained_p1(x1, n1, x2, n2, theta):
    """`p2 = theta·p1` 제약 아래의 최대우도 `p1`. 점수식을 이분법으로 푼다."""
    lo, hi = 1e-12, min(1.0, 1.0 / theta) - 1e-12

    def score(p1):
        return ((x1 + x2) / p1 - (n1 - x1) / (1 - p1)
                - (n2 - x2) * theta / (1 - theta * p1))
    if score(hi) > 0:
        return hi
    for _ in range(300):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if score(mid) > 0 else (lo, mid)
    return (lo + hi) / 2


def score_interval(x1, n1, x2, n2, z):
    """Miettinen–Nurminen 점수 구간. Katz 와 다른 근사라 **갈리는지 보려고** 같이 낸다."""
    if not x1 or not x2:
        return (None, None)
    ratio = (x2 / n2) / (x1 / n1)
    target = z * z

    def stat(theta):
        p1 = constrained_p1(x1, n1, x2, n2, theta)
        p2 = theta * p1
        return ((x1 - n1 * p1) ** 2 / max(n1 * p1 * (1 - p1), 1e-18)
                + (x2 - n2 * p2) ** 2 / max(n2 * p2 * (1 - p2), 1e-18))

    def edge(up):
        far = ratio
        for _ in range(4000):
            far = far * 1.02 if up else far / 1.02
            if far <= 1e-9 or far >= 1e9 or stat(far) >= target:
                break
        near = far / 1.02 if up else far * 1.02
        for _ in range(200):
            mid = math.sqrt(near * far)
            near, far = (near, mid) if stat(mid) >= target else (mid, far)
        return (near + far) / 2
    return edge(False), edge(True)


def fisher_two_sided(x1, n1, x2, n2):
    """2x2 Fisher 정확검정 양측 p. 근사가 아니라 초기하 확률의 합이라 희소 표본에 버틴다.

    scipy 를 안 쓴다 — 이 저장소의 제출 경로는 의존을 안 늘린다.
    `scipy.stats.fisher_exact` 와 열 항목에서 `1e-9` 안쪽으로 일치함을 확인했다.
    """
    total, hits = n1 + n2, x1 + x2
    denominator = math.comb(total, hits)

    def prob(k):
        return math.comb(n1, k) * math.comb(n2, hits - k) / denominator
    observed = prob(x1)
    span = range(max(0, hits - n2), min(n1, hits) + 1)
    return min(1.0, sum(prob(k) for k in span if prob(k) <= observed * (1 + 1e-9)))


def holm(pvalues):
    """Holm–Bonferroni. Bonferroni 보다 덜 보수적이고 FWER 는 같게 지킨다."""
    order = sorted(pvalues, key=pvalues.get)
    out, running = {}, 0.0
    for rank, item in enumerate(order):
        running = max(running, pvalues[item] * (len(order) - rank))
        out[item] = min(running, 1.0)
    return out


def direction(low, high):
    """구간이 1 을 물면 방향을 말하지 않는다. 점추정을 방향으로 읽지 않는다."""
    if low is None or high is None or (low <= 1 <= high):
        return "미정"
    return "더 적다" if high < 1 else "더 많다"


def agreed(katz_dir, score_dir, holm_p):
    """**세 방법이 다 같은 말을 할 때만** 방향을 말한다.

    리뷰 [P1]. dev 발화가 5~9건인 자리에서 Katz 동시 구간만 보면 v15·v16 이 닫히는데
    (`[0.07, 0.95]`·`[0.09, 0.97]`), Fisher+Holm 은 둘 다 `0.10` 으로 안 닫는다.
    **결론이 구간 방법에 달려 있으면 그것은 결론이 아니다.**
    """
    if katz_dir != score_dir or katz_dir == "미정":
        return "미정"
    return katz_dir if holm_p < 0.05 else "미정"


def show(value, spec):
    """`None` 은 `미산출` 로 적는다. 숫자 서식을 그대로 먹이면 TypeError 로 죽는다."""
    return "미산출" if value is None else format(value, spec)


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
        counts = (len(fired_dev), len(dev), fired_unl, len(unlabeled))
        low, high = ratio_interval(*counts)
        sim_low, sim_high = ratio_interval(*counts, z=Z_SIMULTANEOUS)
        sc_low, sc_high = score_interval(*counts, z=Z_SIMULTANEOUS)
        out["items"][item] = {
            "dev_fired": len(fired_dev), "dev_rate": dev_rate,
            "unlabeled_fired": fired_unl, "unlabeled_rate": unl_rate,
            "multiplier": (unl_rate / dev_rate) if dev_rate else None,
            # 항목별 명목 95% 구간. 구간이 1 을 물면 방향을 말할 수 없다.
            "multiplier_low": low, "multiplier_high": high,
            "direction": direction(low, high),
            # 열 항목 동시 95% (Bonferroni), Katz 로그법.
            "simultaneous_low": sim_low, "simultaneous_high": sim_high,
            "katz_direction": direction(sim_low, sim_high),
            # 같은 수준의 점수법(Miettinen–Nurminen). Katz 와 갈리는지 본다.
            "score_low": sc_low, "score_high": sc_high,
            "score_direction": direction(sc_low, sc_high),
            "fisher_p": fisher_two_sided(*counts) if fired_dev and fired_unl else None,
            "dev_tp": tp, "dev_fp": len(fired_dev) - tp,
        }

    # Holm 은 열 항목을 같이 봐야 하므로 항목 순회가 끝난 뒤에 붙인다.
    pvalues = {i: r["fisher_p"] for i, r in out["items"].items() if r["fisher_p"] is not None}
    adjusted = holm(pvalues) if pvalues else {}
    for item, row in out["items"].items():
        row["holm_p"] = adjusted.get(item)
        row["direction_agreed"] = agreed(row["katz_direction"], row["score_direction"],
                                         row["holm_p"] if row["holm_p"] is not None else 1.0)

    # f-string 안에서 바깥과 같은 따옴표를 다시 쓰지 않는다. 그 문법은 3.12 부터이고
    # 이 저장소가 지원하는 3.11 에서는 파싱 자체가 실패한다.
    def span(low, high):
        if low is None or high is None:
            return "미산출"
        return "[{:.2f}, {:.2f}]".format(low, high)

    print(f'{"항목":<6}{"dev 발화":>9}{"무라벨":>8}{"배율":>7}'
          f'{"Katz 동시":>17}{"점수 동시":>17}{"Holm p":>9}'
          f'{"Katz":>6}{"점수":>6}{"합의":>7}{"dev TP/FP":>11}')
    for item in ITEMS:
        row = out["items"][item]
        tally = "{}/{}".format(row["dev_tp"], row["dev_fp"])
        print(f'{item:<6}{row["dev_fired"]:>9}{row["unlabeled_fired"]:>8}'
              f'{show(row["multiplier"], ">7.2f")}'
              f'{span(row["simultaneous_low"], row["simultaneous_high"]):>17}'
              f'{span(row["score_low"], row["score_high"]):>17}'
              f'{show(row["holm_p"], ">9.4f")}'
              f'{row["katz_direction"]:>6}{row["score_direction"]:>6}'
              f'{row["direction_agreed"]:>7}{tally:>11}')
    print(f'dev {out["dev_n"]}건 · 무라벨 {out["unlabeled_n"]}건')
    print(f'명목 z={Z_NOMINAL:.4f} · 동시 z={Z_SIMULTANEOUS:.4f} '
          f'(Bonferroni, {len(ITEMS)}항목).')
    print('**결론은 `합의` 열이다** — Katz·점수법·Fisher+Holm 이 다 같은 말을 할 때만 방향을 쓴다.')

    # **출력을 다 낸 뒤에 쓴다.** 먼저 쓰면 표를 못 찍고 죽은 실행도 산출물을 남기고,
    # 다음 사람은 그 JSON 을 성공한 회차의 것으로 읽는다.
    # 줄끝을 LF 로 고정한다. 기본값으로 열면 윈도에서 CRLF 로 나간다.
    with io.open(args.out, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(out, stream, ensure_ascii=False, indent=1)
        stream.write("\n")


if __name__ == "__main__":
    main()
