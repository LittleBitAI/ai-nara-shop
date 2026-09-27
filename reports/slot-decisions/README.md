# Slot decisions — how the rows of `SLOT_RULES` were chosen

Task sheet: [docs/tasks/a-slot-decisions.md](../../docs/tasks/a-slot-decisions.md). No model call anywhere here.

| Step | Script | Output (in `SLOT_WORK`) |
| --- | --- | --- |
| 1 | `build_cache.py` replays `script.py` over dev 200, the off-dev 600 and the labelled 2,000, keeping the main answers, company-size facts and final cells per notice | `cache.pkl` |
| 2 | `features.py` computes the shared relations (price band, scope, size limit, exceptions, observation, text checks) per notice | `slots.pkl` |
| 3 | `fit3.py` searches, per item, only the slot sources its definition names; picks on half A of the off-dev labels with dev half A as a no-loss constraint, scores on the other halves, then swaps | printed, `fit3.json` |
| 4 | `tools/slot_gate.py` (repo tool) replays base and candidate and applies the fixed adoption rules | [gate.json](gate.json) |

`fit.py` is the first, unconstrained search. It showed the problem the constraint fixes: without dev gold
it rebuilds the labeler's own v10/v11/v20 derivation, which dev gold rejects.

Environment: `PPS_MAIN_REPO` = the checkout holding `open/train_unlabeled.jsonl`; `OFFDEV600_DIR` = the
unpacked `offdev-600-results-1790471557297701344.zip`; `SLOT_WORK` = a scratch directory.

```
python -X utf8 build_cache.py && python -X utf8 features.py && python -X utf8 fit3.py 0.02
```
