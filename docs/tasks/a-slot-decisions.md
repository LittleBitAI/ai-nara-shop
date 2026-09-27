# a-slot-decisions — decide items from shared relations in one table, admitted only through a fixed gate

Task ID / title: `a-slot-decisions` / replace per-item patches with a four-slot table and a mechanical gate
Owner: A+B (me)
Status: gate passed on saved responses; waiting for review and the 9/28 integration
Written: 2026-09-28, base `main` `3c36bba` (same post-processing as the 9/27 upload `9356dc6`)

## Why

Progress had stalled on a pattern: a rule fixed one item's reading and missed a neighbouring one.
Two causes, both visible in the code:

- Each item re-derived the same relation with its own regex or gate: the price band, the scope, whether
  a size limit exists, whether an exception lifts it, whether the notice was fully seen. A fix to one
  item's copy never reached the others.
- Rules were accepted one item at a time, on small evidence, and the raise/lower chain in `postprocess`
  is order-dependent: a new step changes what the steps around it see.

## What

1. `relation_slots()` computes the shared relations once per notice: price band (판로지원법 시행령 제2조의2),
   the company-size call's `scope` / `qualification` / `priority_exception`, the catalogue check and the
   text size-limit check. Unknown reads as no, so an unseen fact never raises.
2. `SLOT_RULES` states each item as four slots: applies, requirement (present, or missing for an absence
   item), exceptions, and "keep an existing positive only if". `decide_slots()` is the last word on the
   items it names; it runs after every raise and gate and before the 수의계약 zeroing.
3. `tools/slot_gate.py` is the only door into the table. It replays base and candidate on the same saved
   responses and returns PASS or FAIL on fixed rules, never a hold:
   1. Macro rises on every off-dev pool.
   2. It rises on both split halves (`half(id)`) of every off-dev pool.
   3. No trusted item loses more than one net (TP − FP) cell.
   4. Dev replay drops by no more than 0.01.
   5. The candidate beats the base in at least 95% of notice bootstrap resamples on every off-dev pool.
4. Rows were chosen by a search restricted to each item's definition (only the slots its name mentions),
   nested cross-fit: chosen on half A of the off-dev labels with dev half A as a no-loss constraint,
   scored on half B and dev half B, then swapped. Scripts: [reports/slot-decisions/](../../reports/slot-decisions/).

## Rows admitted

| Item | Applies | Requirement | Exception stops it | Nested cross-fit (both directions) |
| --- | --- | --- | --- | --- |
| v15 | 1억 ≤ price < 고시금액, not a catalogue product | only 소기업 may bid (company facts), quoted clause verified | — | same row chosen on A and on B; off-dev +0.238 / +0.080, dev +1.0 / 0 |
| v16 | 1억 ≤ price < 고시금액, general scope | no size limit (facts) and no size-limit wording in the text; positives outside the band are dropped | 우선조달 exception | off-dev +0.443 / +0.118; dev 0 / −0.026 (one direction picked a looser row) |
| v18 | price < 1억, general scope | no size limit (facts) | 우선조달 exception | same row chosen on A and on B; off-dev +0.192 / +0.204, dev 0 / 0 |

What changed against the old path is the observation slot: v16 and v18 no longer wait for the qualification
quote to verify or for the full document set to be visible. On the off-dev labels those holds cost 39 v18
and 17 v16 true positives for one false alarm each; on dev gold they cost nothing either way.

## Rejected

| Row | Why |
| --- | --- |
| v2 from a shared performance slot (price < 1억, main call's v3 says a performance requirement) | Gate rule 3: v2 net (TP − FP) 7 → 2 on the off-dev 600. The saved answers cannot tell an entry condition from an evaluation criterion; no definition-grounded variant adds more right cells than wrong ones. Same wall as the D facts call (#168) |
| v10, v11, v20 absence rows (competitive or software scope, no demanded clause) | Off-dev +0.25 to +0.34 F1, but dev gold falls (v10 0.533 → 0.303, v11 0.769 → 0.526, v20 0.833 → 0.556). The searcher rediscovered the labeler's own derivation, which dev calibration marks conditional or excluded for these items |
| v5, v7, v8, v12, v13, v14, v17, v19, v21 | No row gains in both cross-fit directions without a dev loss |
| Items with logprob cuts (v1, v3, v4, v6, v22, v23) | Not searched: the 2,000's saved responses have no `item_p1`, so their current answer there is not the server's |

## Gate result

`python -X utf8 tools/slot_gate.py` with base `3c36bba` and this branch, pools below, 수의계약 labeler
positives excluded (`reports/labels-3000/private-ids.txt`). Verdict **PASS**, no rule failed.
Record: [reports/slot-decisions/gate.json](../../reports/slot-decisions/gate.json).

| Pool | Notices | Base | Candidate | Half A | Half B | P(gain) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Off-dev 600 (`deb6831` GPU run, diag + sealed labels) | 352 | 0.527172 | 0.554116 | +0.012847 | +0.057582 | 1.000 |
| Labels 2,000 (unlabeled-d u00–u10 responses) | 1,030 | 0.453316 | 0.483885 | +0.031526 | +0.029756 | 1.000 |
| Dev (`colab-1790432295199698396` responses, gold) | 200 | 0.828334 | 0.834737 | — | — | — |

Moved cells (TP/FP/FN): off-dev 600 v15 2/2/1 → 3/2/0, v16 9/2/8 → 15/2/2, v18 32/9/15 → 46/9/1;
labels 2,000 v15 2/2/4 → 3/4/3, v16 9/4/24 → 26/7/7, v18 42/15/28 → 67/16/3; dev v15 4/1/2 → 5/1/1,
v16 4/2/2 → 5/3/1. No other item moves.

## Limits

- P(gain) is over notice resamples of the labelled pools. It does not cover label error: v16 and v18 are
  labelled by the facts labeler, trust verdict conditional. Dev gold does not fall on either.
- The main prompt and the company-size prompt are unchanged since 9/23, so the saved responses are the
  distribution a GPU run of this code produces; run-to-run churn is the remaining difference.
- No model call, prompt or schema changes; server time adds only three regex and catalogue checks per notice.

## Files this task may change

`script.py` (slot table, company facts carried into `postprocess`), `tools/replay_run.py` (carry the same
facts), `tools/slot_gate.py`, `tests/`, `reports/slot-decisions/`, this sheet, `docs/tasks.md`,
`.wiki/plan-active.md`.
