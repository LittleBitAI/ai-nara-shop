"""B11 — compare v1 and v2 false positives per item and sort v2's into two kinds.

reading  — the copied string does not establish the item (it is not a product name, not a supply
           pledge, not a bid-stage phrase). v2 was built to remove these.
unwritten — the string does establish the item as written, yet the human label is 0 (v9 names with
           동등 이상, v24 region direction). No fact schema removes these without fitting dev.

The split below is by rule, fixed here, not by reading each cell:
  v9  reading if the named string has no Latin letter or digit and no 상표·제조·브랜드 cue is needed —
      i.e. a pure Korean common noun; unwritten otherwise.
  v19 all v2 FPs are listed with their name and timing for inspection (few).
  v24 by axis; the region-direction axis (text restricts, register N) is unwritten.

    python -X utf8 experiments/b11_fp_breakdown.py --v1 <v1 facts> --v2 <v2 facts>
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))
import script  # noqa: E402
import b11_b_facts_verdict as v1  # noqa: E402
import b11_b_facts_v2_verdict as v2  # noqa: E402

LATIN_OR_DIGIT = re.compile(r"[A-Za-z0-9]")


def load(path):
    rows = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    return {r["id"]: r["facts"] for r in rows}


def v24_axes(f, rec):
    meta = rec.get("meta") or {}
    out = []
    region_text = f.get("v24_region_text")
    text_limited = isinstance(region_text, str) and v2.in_notice(region_text, rec)
    meta_limited = meta.get("지역제한여부") == "Y"
    if text_limited and not meta_limited:
        out.append("region:text_Y_meta_N")
    elif meta_limited and not text_limited:
        out.append("region:text_N_meta_Y")
    for name, probe in (("method", {"v24_method_text": f.get("v24_method_text")}),
                        ("industry", {"v24_industry_texts": f.get("v24_industry_texts")}),
                        ("amount", {"v24_amounts": f.get("v24_amounts")})):
        blank = {"v24_region_text": region_text if meta_limited else None}
        if v2.v24({**blank, **probe}, rec):
            out.append(name)
    return out or ["region:set"]


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--v1", required=True)
    parser.add_argument("--v2", required=True)
    args = parser.parse_args(argv)
    f1, f2 = load(args.v1), load(args.v2)
    ids = sorted(set(f1) & set(f2))
    recs = {r["id"]: r for r in script.iter_records(str(ROOT / "open/dev.jsonl"), None) if r["id"] in ids}
    with (ROOT / "open/dev_labels.csv").open(encoding="utf-8") as stream:
        truth = {r["id"]: r for r in csv.DictReader(stream)}
    print(f"notices compared: {len(ids)}")
    for item in ("v9", "v19", "v24"):
        stats = {}
        for name, verdict, facts in (("v1", v1.VERDICTS[item], f1), ("v2", v2.VERDICTS[item], f2)):
            tp = sum(1 for i in ids if verdict(facts[i], recs[i]) and truth[i][item] == "1")
            fp = [i for i in ids if verdict(facts[i], recs[i]) and truth[i][item] == "0"]
            fn = sum(1 for i in ids if not verdict(facts[i], recs[i]) and truth[i][item] == "1")
            f = 2 * tp / (2 * tp + len(fp) + fn) if tp + len(fp) + fn else float("nan")
            stats[name] = (tp, fp, fn, f)
        (a, b) = stats["v1"], stats["v2"]
        print(f"\n{item}: v1 {a[0]}/{len(a[1])}/{a[2]} F1 {a[3]:.3f} -> v2 {b[0]}/{len(b[1])}/{b[2]} F1 {b[3]:.3f} (optimistic)")
        print(f"  v1 FPs cleared by v2: {len(set(a[1]) - set(b[1]))} · new FPs in v2: {sorted(set(b[1]) - set(a[1]))}")
        if item == "v9":
            kinds = collections.Counter()
            for i in b[1]:
                names = [n for n in f2[i].get("v9_named") or [] if isinstance(n, str) and v2.in_notice(n, recs[i])]
                kind = "unwritten" if any(LATIN_OR_DIGIT.search(n) for n in names) else "reading?"
                kinds[kind] += 1
                print(f"  {kind:9} {i} {names[:3]}")
            print(f"  v2 FP kinds: {dict(kinds)}")
        elif item == "v19":
            for i in b[1]:
                docs = [(d.get("name"), d.get("timing")) for d in f2[i].get("v19_documents") or []
                        if isinstance(d, dict)]
                print(f"  {i} {docs[:2]}")
        else:
            axes = collections.Counter()
            for i in b[1]:
                axes.update(v24_axes(f2[i], recs[i]))
            print(f"  v2 FP axes: {dict(axes)} (region:text_Y_meta_N is the unwritten rule)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
