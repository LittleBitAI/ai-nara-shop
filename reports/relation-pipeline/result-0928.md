# Relation label round 2026-09-28 — no row admitted

Verdict: rejected by the preset rule. `fit.py` admitted 0 of 21 candidate rows, so there is nothing to gate
and `RELATION_CALL` stays `False` on main. The slot-table rows v15/v16/v18 already on main are not affected.

## Run

| Pool | Code | Notices | Relation responses | Deadline skips | Replay = run CSV |
| --- | --- | ---: | ---: | ---: | --- |
| off-dev 600 (`relation-600-results-1790569331401496140.zip`) | `1bc6cd1` | 600 | 296 + 56 | 0 | yes, both shards |
| dev 200 (`relation-dev-results-1790579437558600222.zip`, `dev-debug`) | `1bc6cd1` | 200 | 165 | 0 | — |

`1bc6cd1` is main after #169 with the relation call on. Both ZIPs are in the main checkout's
`artifacts/inbox/`.

## Fit

`fit.py` on these two pools, private IDs excluded ([fit-0928.json](fit-0928.json)). A row is admitted only if
the row picked on one half gains on the other half off-dev and does not lose on dev, in both directions.

| Row picked on one half | Held-out off-dev | Held-out dev | Why not admitted |
| --- | --- | --- | --- |
| v3 entry performance ≥ budget (half B) | +0.0 | −0.20 | no gain, dev loss; half A picked nothing |
| v8 performance and location at entry (half A) | +0.57 (TP 0→6, FP 0→8) | −0.20 | dev loss; half B picked nothing |
| v11 competitive, no size label (half A) | +0.035 | −0.083 | dev loss; half B picked nothing |
| v18/relation small general, no size label (half A) | −0.028 | −0.42 | loses on both |

No other item found a row on either half. The labels move cells (v8 off-dev raises 14), but not in a direction
both label sets agree on.

## What this closes

Per `docs/workflow.md` step 3, a round with no effect leaves this report and closes the branch; review rounds do
not revive it. The relation call costs about 1.7 s a notice on dev (278 s for 165) and adds nothing, so it stays off.
