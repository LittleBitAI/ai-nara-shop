# a-relation-pipeline — one shared clause reading for every item, decided by the slot table

Task ID / title: `a-relation-pipeline` / label clauses once, derive items in code, admit rows only through the gate
Owner: A+B (me)
Status: code and mock run done; waiting for the GPU round (off-dev 600 + dev) that saves the labels
Written: 2026-09-28, base `feat/a-slot-decisions` `e67eb89`

## Why

The slot table ([a-slot-decisions](a-slot-decisions.md)) removed the post-processing half of the whack-a-mole
pattern. The decoding half remained: the joint 24-item call decides each item from its own reading of the
same clause. v2, v3, v4 and v8 each decide separately whether the one performance clause is an entry condition.
v5, v6 and v7 each read the one location clause separately. A prompt or threshold change for one item moves
its neighbours. D's facts call (#168) could not tell an entry condition from an evaluation clause, and
v2 net fell 7 → −1.

## What

1. Stage 1, `clause_candidates()`. Numbered clause lines: qualification sections first, then lines with
   strong and then weak trigger words, within 80 lines / 7,000 characters. The flag `complete` says every
   qualification-section and strong line fit; absence rows read it as the observation slot.
   Dev gold evidence: every in-scope quote is covered (45/45). Median 73 clauses and 5,482 prompt
   characters; `complete` holds on 167 of 200 notices.
2. Stage 2, the relation call. It runs on non-수의계약 notices, after the company-size call. It sees only
   the numbered clauses, grouped under their section lines, with no metadata. It returns up to 30 records:
   `id`, kind, stage (entry / bid_submission / evaluation / after_award / citation) and the attributes the
   items differ on (holder, size, region, orderer, amount).
   - It makes no verdict and writes no quote; the evidence is the labelled clause line itself.
   - xgrammar 0.2.3 (the server version) enforces the id range 1–80, the 30-record cap and every enum.
     This was checked locally.
   - Code, not the model, compares a won amount with the notice price.
   - A deadline guard (6,600 s from process start) stops the phase. Later notices keep the path without labels.
3. Stage 3, the slot table. `relation_slots()` turns the labels into shared questions such as
   `entry_performance`, `entry_location_basic`, `entry_size`, `pledge_at_bid` and `sw_limit_stated`.
   A row in `SLOT_RULES` can name them next to the price and scope slots. A row that names a relation slot
   does nothing on a notice without labels. `slot_row_cell()` is the one per-cell rule; the fit calls the
   same function. A key `vN/<tag>` adds a second row for an item that already has one.
4. **No relation row is on yet.** The GPU round only saves the labels, so its CSV equals the base code's.
   After it, [reports/relation-pipeline/fit.py](../../reports/relation-pipeline/fit.py) picks rows per item
   from definition-grounded candidates. It uses the same nested cross-fit as the slot-table rows: pick on
   off-dev half A with dev half A as a no-loss constraint, score on the other halves, then swap. It writes
   `candidate.py`, and `tools/slot_gate.py` then decides PASS or FAIL on the same saved responses.

## GPU round

| Notebook | Input | Why |
| --- | --- | --- |
| `notebooks/colab-relation-600.ipynb` | off-dev 600 (diag 200 + sealed 400 labels) | labels to fit and gate on |
| `notebooks/colab-relation-dev.ipynb` | dev 200, server flow + `dev-debug` | the dev no-loss constraint, and server-like time |

Pass condition for the round itself: every notice has a valid relation response, and the dev CSV equals
the base CSV (no row is on). The report's `relation_inference_seconds` gives the added time.

## After the round

```
python -X utf8 reports/relation-pipeline/fit.py \
    --pool dev <dev-debug case> open/dev.jsonl open/dev_labels.csv \
    --pool offdev600 <u00 case>,<u01 case> <u00 input>,<u01 input> reports/labels-600/merged/diag.csv,reports/labels-600/merged/sealed.csv \
    --exclude reports/labels-3000/private-ids.txt --out <dir>
python -X utf8 tools/slot_gate.py --base script.py --candidate <dir>/candidate.py <same two pools> --exclude ... --out <dir>/gate
```

Only a PASS goes into `SLOT_RULES`. The labels-2,000 pool has no labels, so relation rows leave it unchanged.
The gate therefore runs on off-dev 600 and dev.

## Limits

- The labels are unmeasured until the round. If the model cannot tell entry from evaluation even on isolated
  clauses, the fit admits no row and the round costs only its time.
- Server time: the call is shorter than the company-size call (about 3,000 prompt tokens against 10,000).
  Its output is up to 30 short records. The deadline guard bounds it either way.

## Files this task may change

`script.py`, `tools/replay_run.py`, `tests/test_slot_rules.py`, `reports/relation-pipeline/`,
`notebooks/colab-relation-*.ipynb`, this sheet.
