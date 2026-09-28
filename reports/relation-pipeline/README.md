# Relation pipeline — choosing relation rows after the GPU round

Task sheet: [docs/tasks/a-relation-pipeline.md](../../docs/tasks/a-relation-pipeline.md). No model call here.

| Step | Command | Output |
| --- | --- | --- |
| 1 | `fit.py` replays the round's saved responses once. It then scores each candidate row per item with `script.slot_row_cell` (the submission's own rule), under a nested cross-fit on off-dev halves with dev as a no-loss constraint | `fit.json`, `candidate.py` |
| 2 | `tools/slot_gate.py --base script.py --candidate candidate.py`, same pools | `gate/gate.json`, PASS or FAIL |

Only a PASS changes `SLOT_RULES`. If no row passes, `RELATION_CALL` goes back to `False` before a
submission, so the server does not pay for labels nothing reads.
