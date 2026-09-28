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
   The flag `complete` says every candidate clause, at any rank, reached the model whole. It is reported
   per notice and decides nothing: the selector picks clauses by trigger words, so no flag can prove a
   clause of some kind was never in the notice (a `직생증명서` clause with no trigger word is never a
   candidate).
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
   - Deadline: no relation model call starts unless it can end before the 300 s reserve.
     - A probe batch of 8 notices runs first, only if 600 s are left.
     - Its seconds per notice (timed from building the messages), then the slowest batch so far, sizes
       every later batch: at most `(left − RELATION_DECODE_S) / (1.5 × seconds per notice)` notices.
       `RELATION_DECODE_S` (300 s, unmeasured) is one notice's full decode, kept spare for a retry.
     - After the messages are built, the batch starts only if its projected time plus that spare still fits.
     - `run_chunk(deadline=)` starts no call, first or retry, after `7200 − 300 − 300` s. Such a notice keeps
       the path without labels.
     - Postprocessing costs about 4 ms a notice.
3. Stage 3, the slot table. `relation_slots()` turns the labels into shared questions such as
   `entry_performance`, `entry_location_basic`, `entry_size`, `pledge_at_bid` and `sw_limit_stated`.
   A row in `SLOT_RULES` can name them next to the price and scope slots. A row that names a relation slot
   is evaluated with three values, yes, no and unknown. Unknown never decides and a known value always does:
   - A relation slot is yes when a label derives it. A missing label is a known no only for a positive
     cell whose every cited character was shown to the relation call, with the 30-record cap not hit.
     "Shown" means whole shown clauses and headings, plus pieces of consecutive shown clauses at the edges
     of a window quote. On dev, all six v4 clause-rule window quotes pass this check. Everywhere else a
     missing label is unknown.
   - A scope or exception slot that does not read the labels is known unless `slots["unknown"]` lists it.
     It is listed for no price, and for no registered estimated price or region limit (`region_allowed`,
     `over_region_limit`).
   - Every such slot a relation row reads comes from what an existing gate verified, never from the raw
     model answer. `attach_company_facts` records it, and `run()` and replay share it:
     - `purchase_general` / `purchase_competitive` come from `purchase_scope`, the outcome of
       `_company_size_bands` mapped by `PURCHASE_SCOPE_BY_REASON`. Only exits past every scope check are
       general (`decided`, and the unrestricted branch's exits); exits before the high-value joint check
       (`unknown_price`, `unverified_qualification`, `unverified_size_exception`) are unknown. The
       high-value `joint_small` conflict is decided on its own, whatever the qualification answer was: a
       general purchase with that exception at or over the notice amount is unknown. Further,
       `outside_general_scope` is the verified competitive or other, `competitive_by_catalogue` is not
       general with the purchase unproven, and `unverified_scope` / `unresolved_high_joint_scope` are
       unknown. An outcome not in the table is unknown, and a test keeps every return of that function in
       the table.
     - A verified competitive answer still yields to a confirmed catalogue exclusion, from the registered
       codes (`outside_catalogue`) or from the product the direct-production demand names
       (`competitive_product` false; PPS-DEV-054 has codes only in its text). A product outside the catalogue never stands in
       for a general purchase (construction stays other).
     - `software` and `priority_exception` are known only when their gates verify them (`software_verified`:
       the deliverable quote; `priority_verified`: "no", or "yes" with a verified quote), through
       `quote_verified`, the gates' own quotation check.
     - `sme_broadened` / `joint_exception` are the verified company-size `size_exception` (`none`, or a
       named exception with a verified quote). Each lifts only its own item, as `_company_size_bands`
       applies it: broadening to SMEs lifts v17, a joint-project product lifts v15. A relation label of
       some exception (PPS-DEV-073's nonprofit carve-out) admits an extra bidder and lifts neither, so no
       row reads the generic `size_exception` label.
     - The older `scope_general` / `scope_competitive` / `catalogue_product` are unchanged for the existing
       rows. Replaying the real off-dev 600 case with `ab9eb9e` and with this code gives byte-identical CSVs.
   - Applies and requirement combine by "and", exceptions by "or". Yes raises (with the clause as evidence);
     no sets the cell to 0; unknown leaves it.

   So a row raises only from a label, and lowers a positive only when the call read the clause that positive
   cites and labelled it otherwise. It never reads a missing label as absence. `negotiation` is the same
   `negotiated()` test v22's clause rule uses (낙찰방법 or 계약방법).
   On a notice without labels such a row does nothing. `slot_row_cell()` is the one per-cell rule; the fit
   calls the same function. A key `vN/<tag>` adds a second row for an item that already has one.
4. **No relation row is on yet.** The GPU round only saves the labels, so its CSV equals the base code's.
   After it, [reports/relation-pipeline/fit.py](../../reports/relation-pipeline/fit.py) picks rows per item
   from definition-grounded candidates. `SCOPE` in fit.py lists the scope each item's official name sets,
   and every candidate's applies must name it; fit.py asserts this on import, so no candidate can fire
   outside its item (v4 over the threshold, v12/v14/v17 general products, v13 competitive, v7 adjacency).
   It also asserts that each row's exceptions are exactly its item's own verified exception (`EXCEPTION`:
   v15 joint project, v17 SME broadening, v16/v18 priority procurement; none elsewhere), and
   that only the absence items (v10, v11, v16, v18, v20) negate a relation slot. For them
   the negation is unknown without a label and no with one, so those rows can only lower an absence
   positive that a shared label contradicts, such as v10 against a labelled entry direct-production demand. The fit hands `slot_row_cell` each cell's
   evidence as the run had it. It uses the same nested cross-fit as the slot-table rows: pick on
   off-dev half A with dev half A as a no-loss constraint, score on the other halves, then swap. The held-out
   halves only admit an item; the row itself is then picked on both halves as training data. It writes
   `candidate.py`, and `tools/slot_gate.py` then decides PASS or FAIL on the same saved responses. That gate
   is in-sample for the chosen row; the cross-fit is the held-out evidence.

## GPU round

| Notebook | Input | Why |
| --- | --- | --- |
| `notebooks/colab-relation-600.ipynb` | off-dev 600 (diag 200 + sealed 400 labels) | labels to fit and gate on |
| `notebooks/colab-relation-dev.ipynb` | dev 200, server flow + `dev-debug` | the dev no-loss constraint, and server-like time |

The round runs on `ab9eb9e`. Later commits change only post-processing and the deadline guard: the relation
prompt, schema and messages are identical to `ab9eb9e` over 700 notices (dev and off-dev shard u00), so
fit.py reads that round's labels with the current rule.

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
