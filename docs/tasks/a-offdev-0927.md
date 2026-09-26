# a-offdev-0927 — A's work from 9/27: steer by off-dev labels, retune thresholds, label 3,000 more

Task ID / title: `a-offdev-0927` / move adoption from dev 200 to the off-dev labelled pool, and grow that pool
Owner: A+B (me)
Status: ready
Written: 2026-09-27, base code `61c495c` (server 0.6203720648), deadline 9/29 10:00

## Target

The cutoff rose to 0.76 on 9/27 (leaderboard Macro F1).

| | Score | Needed from `61c495c` |
| --- | ---: | ---: |
| 9/27 slot | 0.70 | +0.0796 |
| Cutoff, by the 9/29 07:00 slot | 0.76 | +0.1396 over three slots (about +0.047 each) |

The best single day so far from post-processing was +0.0359 (9/25). Post-processing alone at the 9/26 pace (+0.027) reaches about 0.70 on 9/29, not 0.76.
The size needed is +1.9 summed item F1 today, for example six items at +0.32 each. Only a change that moves many items at once gets there.

## Decisions (user, 2026-09-27)

| Question | Decision |
| --- | --- |
| Adoption gate | Off-dev. A candidate is adopted on the off-dev labelled pool (diagnostic 200 + sealed 400, later the 3,000). A small dev drop is allowed |
| Sealed 400 | Unsealed. It is used for development and tuning, not as a holdout. The split-half check below replaces the holdout |
| Private score | The best submission counts. A losing slot costs nothing, so 9/27 and 9/28 may carry aggressive candidates |
| More labels | Label 3,000 more unlabeled notices, drawn from the pool that already has saved model responses |

## Why: where the loss is off dev

CPU replay of `61c495c` on the diagnostic 200 (saved responses of the unlabeled D run u00~u10, labels `reports/labels-600/merged/diag.csv`).
Macro over the 22 labelled items is 0.534; dev replay of the same code is about 0.81.

| Mostly missed (FN) | TP/FP/FN | Mostly false alarms (FP) | TP/FP/FN |
| --- | --- | --- | --- |
| v2 | 8/2/14 | v6 | 0/7/1 |
| v10 | 8/5/11 | v3 | 4/5/1 |
| v18 | 28/7/10 | v15 | 0/3/0 |
| v1 | 0/4/8 | v17 | 3/3/2 |
| v8 | 1/1/6 | v22 | 2/1/0 |
| v11 · v13 · v16 · v19 | 5 · 4 · 3 · 2 FN | | |

- Off dev the loss is mostly recall. The thresholds (v1 0.97, v4 0.995, v9 0.9998, v22 0.97) were fitted to dev's 5–8 positives per item and lean toward cutting false alarms.
- That run predates #134 and recorded no `item_p1`, so the replay applies no thresholds. v1, v6 and v22 read unreliably here.
- The labels are about 80% right, and the diagnostic 200 is not random (150 from notices where a weak item fired, 50 from the rest).
- Reproduce: `python -X utf8 tools/replay_run.py --case reports/label-compare/unlabeled-d/<run>/uNN/output --input <that chunk's records> --output-dir <new dir>` for u00~u10 (u11 cannot be replayed), then score against `merged/diag.csv`. A chunk's records are the lines of `open/train_unlabeled.jsonl` listed in its `ids.json`.

## Steps

| When | What | Output |
| --- | --- | --- |
| Now (D runs it) | GPU: the current `script.py` (same as `61c495c`) on the diagnostic 200 + sealed 400. `colab-unlabeled-d.ipynb` is pinned to its own ID list (`IDS_FILE`) and commit (`REPO_REF`), so copy it to `colab-offdev-600.ipynb`, point `IDS_FILE` at a 600-ID file committed with a manifest, set `REPO_REF` to that commit and `N_NOTICES = 600`. The main call saves `item_p1`. About 35–40 min on one A100 | Saved responses for 600 off-dev notices, registered under `reports/runs/` |
| Now | Label pilot: 100 notices drawn from the u00~u10 pool, minus the diagnostic 200, minus notices any labeler already saw. Seed `20260927`, ID list and manifest committed before labelling. Luna (effort high) + the fact labeler, same prompts as labels-600 | Measured seconds and dollars per notice |
| After the pilot | Scale to 3,000, or to whatever finishes by 15:00 (stop line below). Same labelers, same merge rules | `reports/labels-3000/merged.csv`, trust verdicts reused from labels-600 |
| Meanwhile | Missed-cell stage audit on the diagnostic 200: for each FN, did the model say 0 or did a gate lower a true positive? A gate that lowers true positives off dev is the cheapest fix | Per-item table: model / gate / rule |
| After the GPU run | Retune the thresholds for all labelled items on dev 200 + diagnostic 200 + sealed 400 (800 labels). `tools/tune_thresholds.py` takes one case today; extend it to several cases and label files | Candidate `ITEM_THRESHOLDS` with a split-half report |
| 15:00 | Replay `main` and each post-processing candidate on the 3,000; merge the winners from C and from the audit. Those saved responses have no `item_p1`, so a threshold candidate does not move there — thresholds are judged only on dev 200 + the off-dev 600 from D's run | One integration branch |
| 19:00 | Integration closes | PR, reviewed before the round (operational `script.py`) |
| 20:00 / 21:00 | Freeze and package with `tools/package.py`; upload | ZIP, SHA-256 in the ledger |

## Adoption rule (fixed before any result)

A candidate is adopted when all of these hold, otherwise it is rejected. No hold.

1. Macro over the labelled items on the off-dev pool rises (diagnostic 200 + sealed 400, plus the 3,000 once they are labelled).
2. Split-half: tune or write the rule on one half of the pool and score the other half, then swap. It must gain in both directions. Thresholds and rules are both held to this.
3. No trusted item loses more than one net `(TP − FP)` cell on the pool.
4. Dev replay does not drop by more than 0.01 Macro.
5. Server time estimate ≤ 6,800 s. Threshold and post-processing changes add none.

v9 and v24 have no labels off dev; their thresholds stay as they are.
The 3,000 enter the pool for post-processing rules only. For thresholds the pool is the off-dev 600, the only off-dev responses with `item_p1`.

The one exception: if nothing passes by 19:00, the slot carries an experimental submission (the best score counts, so a loss costs nothing).
It is the candidate with the highest off-dev pool Macro among those whose server time estimate is ≤ 6,800 s.
If no candidate beats `61c495c` on that Macro, upload `main` as it is. The ledger note says "experimental" and lists the conditions it failed.

## Stop lines

| Condition | Then |
| --- | --- |
| Pilot throughput says 3,000 will not finish by 15:00 | Label what finishes by 15:00 (at least 1,500); the rest keeps running for 9/28 |
| Pilot cost × 3,000 > $30 | Label fewer notices at effort high. The trust verdicts were calibrated for Luna high on dev 120; another effort needs its own calibration before its labels enter the gate |
| The threshold retune fails the split-half check | Keep the current thresholds; submit the rules only |
| Nothing passes by 19:00 | Experimental submission under the exception in the [adoption rule](#adoption-rule-fixed-before-any-result) |

## Files this task may change

`tools/tune_thresholds.py`, `notebooks/colab-offdev-600.ipynb`, `script.py` (`ITEM_THRESHOLDS` and rules that pass the gate), `tests/`, `reports/labels-3000/`, `reports/runs/`, this sheet, `docs/tasks/plan-0926-0929.md`, `.wiki/plan-active.md`.

## Results

Empty. One line per step as it finishes.
