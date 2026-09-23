"""무라벨 회차의 CSV 에서 v3·v17 삭제 집합 D 와 라벨 추첨 순서를 만든다. 모델을 부르지 않는다.

후보(`experiments/quoted_deletion_candidate.py`)는 운영 `postprocess` 가 낸 v3·v17 셀의 근거문구만
읽으므로, 회차 `submission.csv` 의 `e3`·`e17` 에 삭제 판정을 건 결과가 후보 재생과 같다.

층은 항목마다 셋이다 — D(B=1, 후보가 지움), R(B=1, 남음), Z(B=0). 추첨 순서는 표본 순서
(`ids.txt`, seed 20260923)를 그대로 쓴다. 그 순서는 라벨·예측과 무관하게 정해졌으므로 D 를 그 순서로
앞에서 n 개 자르면 D 안의 단순 무작위 추출이다. 선택 확률은 n / N_D.
"""

import argparse
import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ITEMS = {"v3": "e3", "v17": "e17"}


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def check_prefix(ids, failed, order):
    """Shards plus the failed set must be exactly the first k IDs of the sample order.

    A missing shard or an unexplained gap would still yield a D, just from a non-random
    subset of the sample (review round 2). Check the whole contract here, once.
    """
    if len(set(ids)) != len(ids):
        raise ValueError("묶음들에 같은 ID 가 두 번 있다")
    if set(ids) & set(failed):
        raise ValueError(f"성공과 실패 집합 F 에 같이 있다: {sorted(set(ids) & set(failed))[:5]}")
    seen = set(ids) | set(failed)
    if seen != set(order[:len(seen)]):
        missing = [i for i in order[:len(seen)] if i not in seen]
        raise ValueError(f"표본 순서의 앞 {len(seen)}건이 아니다 — 빠진 ID {missing[:5]} "
                         "(묶음이 빠졌거나 F 에 없는 누락이다)")


def layers(rows, recs, candidate):
    """rows: submission.csv 행, recs: id→공고. 항목별 D 셀 목록과 층 크기.

    Each cell must satisfy the production postprocess contract: 0/1 only, a positive carries
    a non-empty verified quote, a negative carries none. A cell outside it would be counted
    in the wrong layer and silently shrink D (review rounds 1-2).
    """
    out = {item: {"D": [], "R": 0, "Z": 0} for item in ITEMS}
    for row in rows:
        for item, evidence in ITEMS.items():
            if row[item] not in ("0", "1"):
                raise ValueError(f"{row['id']} {item}={row[item]!r}: CSV 계약 밖 값이다")
            if (row[item] == "1") != bool(row[evidence].strip()):
                raise ValueError(f"{row['id']} {item}={row[item]} 인데 {evidence} 가 "
                                 f"{'비었다' if row[item] == '1' else '있다'}: 후처리 계약 위반")
            if row[item] == "0":
                out[item]["Z"] += 1
                continue
            quote = row[evidence]
            reason = (candidate.v3_deletion(quote, recs[row["id"]]) if item == "v3"
                      else candidate.v17_deletion(quote))
            if reason:
                out[item]["D"].append({"id": row["id"], "item": item, "reason": reason, "quote": quote})
            else:
                out[item]["R"] += 1
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", required=True, action="append",
                        help="Drive 폴더를 받은 곳. u00/output/submission.csv, u00/ids.json … "
                             "여러 번 주면 묶음을 합친다(보관본은 회차별 폴더에 나뉘어 있다)")
    parser.add_argument("--input", default=str(ROOT / "open/train_unlabeled.jsonl"))
    parser.add_argument("--order", default=str(ROOT / "reports/label-compare/unlabeled-d/ids.txt"))
    parser.add_argument("--draw", default="v3=19,v17=32", help="항목별 추첨 수")
    parser.add_argument("--out", required=True, help="새 디렉터리")
    args = parser.parse_args(argv)
    script = load(ROOT / "script.py", "submission")
    candidate = load(ROOT / "experiments/quoted_deletion_candidate.py", "quoted_deletion_candidate")
    candidate.baseline = lambda: script
    order = {identifier: k for k, identifier in enumerate(Path(args.order).read_text(encoding="utf-8").split())}
    wanted = dict(pair.split("=") for pair in args.draw.split(","))

    shards = sorted((p.parent for run in args.run for p in Path(run).glob("u*/ids.json")),
                    key=lambda s: s.name)
    names = [s.name for s in shards]
    if len(set(names)) != len(names):
        raise ValueError(f"같은 묶음이 두 폴더에 있다: {sorted({n for n in names if names.count(n) > 1})}")
    ids = [i for s in shards for i in json.loads((s / "ids.json").read_text(encoding="utf-8"))]
    failed = set()
    for run in args.run:
        summary_path = Path(run) / "summary.json"
        if summary_path.is_file():
            failed |= set(json.loads(summary_path.read_text(encoding="utf-8")).get("failed", []))
    order_list = Path(args.order).read_text(encoding="utf-8").split()
    check_prefix(ids, failed, order_list)
    idset = set(ids)
    recs = {}
    for line in Path(args.input).read_bytes().decode("utf-8").split("\n"):
        if line.strip():
            record = json.loads(line)
            if record["id"] in idset:
                recs[record["id"]] = script.normalize(record)
    rows, sources = [], {}
    for s in shards:
        path = s / "output/submission.csv"
        sources[s.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        with path.open(encoding="utf-8", newline="") as stream:
            rows += list(csv.DictReader(stream))
    if [r["id"] for r in rows] != ids or len(recs) != len(ids):
        raise ValueError("CSV 행·표본 ID·입력 공고가 서로 맞지 않는다")

    found = layers(rows, recs, candidate)
    out = Path(args.out)
    out.mkdir(parents=True)
    summary = {"notices": len(ids), "order_prefix": max(order[i] for i in ids) + 1,
               "submission_sha256": sources, "items": {}}
    with (out / "d.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
        for item, layer in found.items():
            cells = sorted(layer["D"], key=lambda c: order[c["id"]])
            n = min(int(wanted.get(item, 0)), len(cells))
            for rank, cell in enumerate(cells):
                stream.write(json.dumps({**cell, "order": order[cell["id"]], "drawn": rank < n},
                                        ensure_ascii=False) + "\n")
            summary["items"][item] = {"N_D": len(cells), "N_R": layer["R"], "N_Z": layer["Z"],
                                      "wanted": int(wanted.get(item, 0)), "drawn": n,
                                      "reasons": {r: sum(c["reason"] == r for c in cells)
                                                  for r in sorted({c["reason"] for c in cells})}}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                      encoding="utf-8", newline="\n")
    print(json.dumps(summary["items"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
