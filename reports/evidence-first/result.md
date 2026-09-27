# Combined evidence-first run — result: rejected (2026-09-28)

Judged by [plan.md](plan.md). Only the off-dev 600 run was scored: it lost, so the dev run no longer decides anything.

ZIP `offdev-600-results-1790514300384312892`, code `8a274ec`, shards u00 500 + u01 100, both replay byte-identically.
Scored on the 352 non-수의계약 notices of the diagnostic 200 + sealed 400.

| | Off-dev 600 | Half A | Half B |
| --- | ---: | ---: | ---: |
| Baseline `be87c9f` (on the `c23ed84` responses) | 0.570612 | 0.485084 | 0.500073 |
| Combined code as built | 0.482453 | 0.391577 | 0.457069 |
| Role gate off | 0.482453 | 0.391577 | 0.457069 |
| No logprob cuts | 0.528989 | 0.431620 | 0.487373 |

Across items TP 151 → 138 with FP unchanged at 45. The loss sits in items the main call decides: v22 2/0/0 → 0/0/2,
v19 2/0/4 → 0/0/6, v13 15/2/6 → 8/0/13 (the SME check runs only on a main-call v13 positive; SME seconds 137 → 13),
v3 2/2/2 → 1/0/3, v4 and v17 one false alarm more, v1 false alarms 1 → 4. Items decided by the other calls (v2, v10,
v11, v16, v18, v20) did not move. No response was invalid, so output length was not the cause: writing the quote first
made the model write `null` and answer 0 more often. The role gate changed nothing. Main-call time rose 29%
(1,135.8 s against 882.4 s for 500 notices).

This candidate was uploaded on 9/27 before this run finished and scored 0.584 on the server
(`reports/submissions.json`). At the usual transfer of about 0.5 the measured −0.088 is about −0.044 on the server,
which puts `be87c9f` itself near 0.628.

Not to reopen as is: evidence-first field order, the role field and the contrastive examples in the main call.
