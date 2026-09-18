"""C4 준비 — 경쟁제품 조회가 v10·v11 의 적용 구간을 가르는지 GPU 없이 잰다.

`script.py` 의 `sme_product_lookup` 을 그대로 부른다. 새 조회를 만들지 않는다.
dev 200건에 대해 조회 결과를 내고 `open/dev_labels.csv` 의 v10·v11·v12·v13 과 대조한다.

이것은 판정이 아니라 **적용 구간의 판별력 측정**이다. 조회가 맞힌 것을 위반으로 세지 않는다.

실행:
    py -X utf8 reports/team-c/c4-v10-v11/probe_competitive_product.py
"""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DEV = REPO / "open/dev.jsonl"
LABELS = REPO / "open/dev_labels.csv"
DATA = REPO / "open/data"
OUT = Path(__file__).resolve().parent / "lookup-result.json"

ITEMS = ("v10", "v11", "v12", "v13")


def load_script():
    spec = importlib.util.spec_from_file_location("baseline_script", REPO / "script.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    script = load_script()
    _, products = script.load_sme_reference(str(DATA))

    with LABELS.open(encoding="utf-8", newline="") as stream:
        labels = {row["id"]: {item: int(row[item]) for item in ITEMS}
                  for row in csv.DictReader(stream)}

    rows = []
    for rec in script.iter_records(str(DEV)):
        context = script.build_context(rec, max_chars=16000)
        found = script.sme_product_lookup(rec, context, products)
        matches = found["일치후보"]
        sources = {m["일치출처"] for m in matches}
        rows.append({
            "id": rec["id"],
            "업무구분": (rec.get("meta") or {}).get("업무구분"),
            "후보수": len(matches),
            "코드일치": bool(sources & {"메타코드", "문서코드"}),
            "품명만일치": bool(matches) and not (sources & {"메타코드", "문서코드"}),
            "고시미등재코드": len(found["메타코드_고시미등재"]),
            "서비스보조목록": len(found["서비스보조목록"]),
            "truth": labels.get(rec["id"], {}),
        })

    def tally(predicate, item):
        tp = sum(1 for r in rows if predicate(r) and r["truth"].get(item) == 1)
        fp = sum(1 for r in rows if predicate(r) and r["truth"].get(item) == 0)
        fn = sum(1 for r in rows if not predicate(r) and r["truth"].get(item) == 1)
        return {"적용": tp + fp, "양성포함": tp, "놓친양성": fn}

    gates = {
        "코드일치(메타/문서)": lambda r: r["코드일치"],
        "코드 또는 품명 일치": lambda r: r["후보수"] > 0,
        "게이트 없음(전건)": lambda r: True,
    }

    report = {
        "notices": len(rows),
        "purpose": "적용 구간의 판별력 측정. 위반 판정이 아니다",
        "support": {item: sum(1 for r in rows if r["truth"].get(item) == 1) for item in ITEMS},
        "gates": {name: {item: tally(pred, item) for item in ITEMS}
                  for name, pred in gates.items()},
        "rows": rows,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8", newline="")

    print(f"공고 {len(rows)}건 · 양성 {report['support']}")
    print(f"\n{'적용 게이트':<22}{'항목':<6}{'적용 건수':>10}{'그중 양성':>10}{'놓친 양성':>10}")
    for name, per_item in report["gates"].items():
        for item, data in per_item.items():
            print(f"{name:<22}{item:<6}{data['적용']:>10}{data['양성포함']:>10}{data['놓친양성']:>10}")
    print(f"\n기록: {OUT.relative_to(REPO).as_posix()}")


if __name__ == "__main__":
    main()
