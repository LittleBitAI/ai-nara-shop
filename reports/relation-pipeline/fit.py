"""Pick relation rows for the slot table from a GPU run that saved relation labels. No model call.

Every candidate row is read off its item's definition (CANDIDATES below): the price band or scope the item
names, the relation its requirement names and the exception it allows. A relation row owns its cell: it also
lowers a positive the shared labels do not derive.
Nested cross-fit, as in reports/slot-decisions/fit3.py: on half A of the off-dev labels pick the row that
gains most among rows that do not lower dev half A, score it on half B and dev half B, then swap.
An item is admitted only when both directions pick a row, both held-out off-dev halves gain and neither
held-out dev half falls. The admitted row is then picked on both halves as training data, never by a
held-out score. It is written as a candidate script and still has to pass tools/slot_gate.py; that gate
scores the same labels, so the cross-fit is the held-out evidence and the gate is the in-sample check.

  python -X utf8 reports/relation-pipeline/fit.py \
      --pool dev <case> <input.jsonl> <dev_labels.csv> \
      --pool offdev600 <case>,<case> <input>,<input> reports/labels-600/merged/diag.csv,reports/labels-600/merged/sealed.csv \
      --exclude reports/labels-3000/private-ids.txt --out <new dir>
"""

import argparse
import csv
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "reports" / "labels-3000"))
import replay_run  # noqa: E402
from pick import half  # noqa: E402
from slot_gate import ITEMS, f1, read_labels  # noqa: E402

MARGIN = 0.02     # the least held-in F1 gain a row must show, as in the slot-table fit

GENERAL = [("scope_general",), ("!catalogue_product",)]
SIZE_EXCEPTIONS = [(), ("priority_exception",), ("stated_exception",), ("priority_exception", "stated_exception")]


def rows(applies, requirements, exceptions=((),)):
    # No "keep only if" option: a relation row owns its cell (`slot_row_cell`), so it lowers what it does not derive.
    return [(a, r, x, None) for a in applies for r in requirements for x in exceptions]


def banded(band, scopes):
    return [(band, *scope) for scope in scopes]


CANDIDATES = {
    "v1": rows([()], [("entry_institution",)]),
    "v2": rows([("under_notice",)], [("entry_performance",)]),
    "v3": rows([()], [("entry_performance_budget",)]),
    "v4": rows([("over_notice",)], [("entry_performance_institution",)]),
    "v5": rows([("over_region_limit",)], [("entry_location",)]),
    "v6": rows([("region_allowed",)], [("entry_location_basic",)]),
    # The item is 인접 확대: only the adjacency label, not any listed provinces.
    "v7": rows([("region_allowed",)], [("entry_location_adjacent",)]),
    "v8": rows([(), ("region_allowed",)], [("entry_performance", "entry_location")]),
    "v10": rows([("scope_competitive", "relations_complete")], [("!entry_direct_production",)]),
    "v11": rows([("scope_competitive", "relations_complete")], [("!entry_size",)], SIZE_EXCEPTIONS),
    "v12": rows(GENERAL, [("entry_direct_production",)]),
    "v13": rows([("scope_competitive",)], [("entry_small",)]),
    "v14": rows(banded("over_notice", GENERAL), [("entry_size",)]),
    "v15/relation": rows(banded("mid", GENERAL), [("entry_small",)]),
    "v16/relation": rows(banded("mid", GENERAL[:1]), [("!entry_size", "relations_complete")], SIZE_EXCEPTIONS),
    "v17": rows(banded("small", GENERAL), [("entry_sme",)], SIZE_EXCEPTIONS[:1] + SIZE_EXCEPTIONS[2:3]),
    "v18/relation": rows(banded("small", GENERAL[:1]), [("!entry_size", "relations_complete")], SIZE_EXCEPTIONS),
    "v19": rows([()], [("pledge_at_bid",)]),
    "v20": rows([("software", "relations_complete")], [("!sw_limit_stated",)]),
    "v22": rows([("negotiation",)], [("briefing_entry",)]),
}


# The scope each item's official name sets (docs/items.md). Every candidate's applies must name one slot of
# every group, so no candidate can fire outside its item whatever the score says. Checked on import.
GENERAL_SCOPE = {"scope_general", "!catalogue_product"}
SCOPE = {
    "v2": [{"under_notice"}], "v4": [{"over_notice"}],
    "v6": [{"region_allowed"}], "v7": [{"region_allowed"}], "v5": [{"over_region_limit"}],
    "v10": [{"scope_competitive"}], "v11": [{"scope_competitive"}], "v13": [{"scope_competitive"}],
    "v12": [GENERAL_SCOPE], "v14": [{"over_notice"}, GENERAL_SCOPE],
    "v15": [{"mid"}, GENERAL_SCOPE], "v16": [{"mid"}, GENERAL_SCOPE],
    "v17": [{"small"}, GENERAL_SCOPE], "v18": [{"small"}, GENERAL_SCOPE],
    "v20": [{"software"}], "v22": [{"negotiation"}],
}
for _key, _candidates in CANDIDATES.items():
    for _row in _candidates:
        for _group in SCOPE.get(_key.split("/")[0], ()):
            assert _group & set(_row[0]), (_key, _row, "applies outside the item's scope")


def capture(script, cases, inputs, data_dir):
    """Replay once; per notice keep the final cells, the slots and which relation slots have a quotable clause."""
    seen = {}
    original = script.decide_slots

    def hooked(out, judgment, rec):
        out = original(out, judgment, rec)
        quotable = {name: bool(script._slot_evidence(((), (name,), (), None), judgment, rec))
                    for name in script.RELATION_SLOTS}
        seen[rec["id"]] = {"slots": script.relation_slots(judgment, rec), "quotable": quotable,
                           "labelled": script.RELATION_KEY in judgment}
        return out

    script.decide_slots = hooked
    try:
        final = {}
        for case, input_path in zip(cases, inputs):
            result = replay_run.replay(script, case, input_path=input_path, data_dir=data_dir)
            text = replay_run.to_csv_bytes(script, result["rows"]).decode("utf-8")
            for row in csv.DictReader(io.StringIO(text)):
                final[row["id"]] = {v: int(row[v]) for v in ITEMS}
    finally:
        script.decide_slots = original
    return {i: dict(seen[i], final=final[i]) for i in final}


def predict(script, key, row, notices, ids):
    item = key.split("/")[0]
    out = []
    for i in ids:
        n = notices[i]
        cell = {"위반여부": n["final"][item], "근거문구": ""}
        quote = (lambda n=n: "q" if any(n["quotable"].get(name) for name in row[1]) else "")
        # 수의계약 notices have no labels, so the row leaves them as the replay left them.
        out.append(script.slot_row_cell(item, row, cell, n["slots"], n["labelled"], quote)["위반여부"])
    return out


def score(truth, pred, ids, item):
    c = [0, 0, 0]
    for i, p in zip(ids, pred):
        t = truth[i][item]
        c[0] += t & p
        c[1] += p & (1 - t)
        c[2] += t & (1 - p)
    return f1(c), c


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--script", default=str(ROOT / "script.py"))
    parser.add_argument("--pool", nargs=4, action="append", required=True, metavar=("NAME", "CASES", "INPUTS", "LABELS"))
    parser.add_argument("--exclude")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    out = Path(args.out)
    if out.exists():
        raise SystemExit(f"{out} already exists")
    script = replay_run.load_module(Path(args.script), "fit_script")
    drop = set(Path(args.exclude).read_text(encoding="utf-8").split()) if args.exclude else set()
    pools = {}
    for name, cases, inputs, labels in args.pool:
        notices = capture(script, cases.split(","), inputs.split(","), ROOT / "open" / "data")
        truth = read_labels(labels.split(","))
        ids = [i for i in truth if i in notices and (name == "dev" or i not in drop)]
        pools[name] = (notices, truth, ids)
    if "dev" not in pools or len(pools) != 2:
        raise SystemExit("give exactly two pools: dev and one off-dev pool")
    off_name = next(n for n in pools if n != "dev")
    report, chosen = {}, {}
    for key, candidates in CANDIDATES.items():
        item = key.split("/")[0]
        split = {}
        for name, (notices, truth, ids) in pools.items():
            labelled = [i for i in ids if truth[i][item] is not None]
            split[name] = {h: [i for i in labelled if half(i) == h] for h in "AB"}
        def gain(name, halves, row):
            notices, truth, _ = pools[name]
            ids = [i for h in halves for i in split[name][h]]
            base = score(truth, [notices[i]["final"][item] for i in ids], ids, item)
            cand = score(truth, predict(script, key, row, notices, ids), ids, item)
            return cand[0] - base[0], base[1], cand[1]

        def pick(halves):
            """The best row on these halves only: off-dev gain above MARGIN, no dev loss on the same halves."""
            best = (MARGIN, None)
            for row in candidates:
                g = gain(off_name, halves, row)[0]
                if g > best[0] and gain("dev", halves, row)[0] >= 0:
                    best = (g, row)
            return best[1]

        cross = {}
        for fit_h, test_h in (("A", "B"), ("B", "A")):
            row = pick(fit_h)
            cross[fit_h] = {"row": row}
            if row is not None:
                for name in pools:
                    g, b, c = gain(name, test_h, row)
                    cross[fit_h][name] = {"gain": round(g, 4), "base": b, "candidate": c}
        rows_picked = [cross[h]["row"] for h in "AB"]
        admitted = (all(rows_picked)
                    and all(cross[h][off_name]["gain"] > 0 and cross[h]["dev"]["gain"] >= 0 for h in "AB"))
        if admitted:
            # The held-out halves only decide whether the item is admitted. The row itself is chosen on
            # training-side evidence (both halves as training), so no held-out score picks it. The gate that
            # follows scores the same labels, so its gain is in-sample; the cross-fit above is the held-out test.
            row = pick("AB")
            admitted = row is not None
            if admitted:
                chosen[key] = row
        report[key] = {"admitted": admitted, "cross": cross, "row": chosen.get(key)}
        print(key, json.dumps(report[key], ensure_ascii=False), flush=True)
    out.mkdir(parents=True)
    source = Path(args.script).read_text(encoding="utf-8")
    # After the table, so a "vN/relation" row runs after vN's own row, as it did in the fit.
    end = source.index("\n}\n", source.index("SLOT_RULES = {")) + 3
    added = "".join(f"SLOT_RULES[{json.dumps(k)}] = {tuple(tuple(p) if p is not None else None for p in row)!r}\n"
                    for k, row in chosen.items())
    (out / "candidate.py").write_text(source[:end] + added + source[end:], encoding="utf-8", newline="\n")
    (out / "fit.json").write_text(json.dumps({"chosen": chosen, "items": report}, ensure_ascii=False, indent=1) + "\n",
                                  encoding="utf-8", newline="\n")
    print(f"{len(chosen)} rows proposed -> {out / 'candidate.py'}; next: tools/slot_gate.py --base {args.script} "
          f"--candidate {out / 'candidate.py'} with the same pools")
    return 0


if __name__ == "__main__":
    sys.exit(main())
