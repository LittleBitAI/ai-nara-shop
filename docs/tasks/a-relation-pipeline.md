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

1. Stage 1, `clause_candidates()`. Numbered clauses: qualification sections first, then clauses with
   strong and then weak trigger words, within 160 clauses / 14,000 characters. PDF-wrapped lines are joined
   into one clause until a list marker or a sentence end, so the stage words on a wrapped line reach the
   model with the rest of the clause (PPS-DEV-110's pledge clause). Only a short top-level line
   (`N.`, Roman numeral, `제N조`, box) is a section heading; `N)` and `가.` are list items.
   A short `가.` line is kept as the clause's sub-heading (`4. 입찰자격 조건 › 나. 계약 시 제출서류`), so the
   stage a list heading states reaches the clauses under it (PPS-D-002037, PPS-D-008654).
   A clause's evidence is its exact document span. A clause over 800 characters is cut.
   The flag `complete` says every candidate clause, at any rank, reached the model whole: a dropped or
   cut candidate may hold the kind an absence row looks for. The slot `relations_complete` also needs
   `완전관측`, no dropped document, and fewer than 30 records.
   Dev gold evidence: every in-scope quote is covered. Median 6,117 characters, the largest 14,000
   (about 9,900 prompt tokens by the mock's characters/2 estimate, against 14,336 of room);
   `complete` holds on 144 of 200 notices.
2. Stage 2, the relation call. It runs on non-수의계약 notices, after the company-size call. It sees only
   the numbered clauses, grouped under their section lines, with no metadata. It returns up to 30 records:
   `id`, kind, stage (entry / bid_submission / evaluation / after_award / citation) and the attributes the
   items differ on (holder, size, region, orderer, amount).
   - It makes no verdict and writes no quote; the evidence is the labelled clause line itself.
   - xgrammar 0.2.3 (the server version) enforces the id range 1–160, the 30-record cap and every enum.
     This was checked locally.
   - Code, not the model, compares a won amount with the notice price, with the v3 deletion rule's own
     comparison (`_below_budget`: under one multiple only when under both the estimated price and the budget).
   - Region separates `adjacent` (the ordering area plus neighbours) from `multi_province` (listed provinces).
   - Deadline: a probe batch of 8 notices runs first, only if 600 s are left before the 300 s reserve.
     Its seconds per notice (timed from building the messages), then the slowest batch so far, sizes
     every later batch: at most `left / (1.5 × seconds per notice)` notices. A serial retry of a failed
     response starts only while one full decode (`RELATION_DECODE_S`, 300 s, unmeasured) still ends before
     the reserve; otherwise that notice keeps the path without labels. Postprocessing costs about 4 ms a
     notice.
3. Stage 3, the slot table. `relation_slots()` turns the labels into shared questions such as
   `entry_performance`, `entry_location_basic`, `entry_size`, `pledge_at_bid` and `sw_limit_stated`.
   A row in `SLOT_RULES` can name them next to the price and scope slots. A row that names a relation slot
   owns its item on every fully observed labelled notice: the cell is 1 only when the shared labels derive
   it, so a positive from the item's own path (a clause rule, the main call) is lowered when the labels do
   not derive it. Unknown never decides: on a notice that is not fully observed, the row neither lowers a
   positive nor raises an absence; it can only raise what the labels positively derive. A scope slot that
   does not read the labels (price band, product scope, `negotiation`) still decides when it is known to
   fail. When it is unknown (no price, `scope: unknown`), it is listed in `slots["unknown"]` and decides
   nothing. `region_allowed` is true also when unknown, so v5 reads the known `over_region_limit`, never
   its negation. `negotiation` is the same `negotiated()` test v22's clause rule uses
   (낙찰방법 or 계약방법).
   On a notice without labels such a row does nothing. `slot_row_cell()` is the one per-cell rule; the fit
   calls the same function. A key `vN/<tag>` adds a second row for an item that already has one.
4. **No relation row is on yet.** The GPU round only saves the labels, so its CSV equals the base code's.
   After it, [reports/relation-pipeline/fit.py](../../reports/relation-pipeline/fit.py) picks rows per item
   from definition-grounded candidates. `SCOPE` in fit.py lists the scope each item's official name sets,
   and every candidate's applies must name it; fit.py asserts this on import, so no candidate can fire
   outside its item (v4 over the threshold, v12/v14/v17 general products, v13 competitive, v7 adjacency). It uses the same nested cross-fit as the slot-table rows: pick on
   off-dev half A with dev half A as a no-loss constraint, score on the other halves, then swap. The held-out
   halves only admit an item; the row itself is then picked on both halves as training data. It writes
   `candidate.py`, and `tools/slot_gate.py` then decides PASS or FAIL on the same saved responses. That gate
   is in-sample for the chosen row; the cross-fit is the held-out evidence.

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
