# D facts call — GPU result (2026-09-27)

Code `278ca536f0707c9cb96e45fb4104ac3eef1eece8` on A100, both runs complete, self-check PASS.

- Off-dev: `notebooks/colab-d-facts.ipynb`, the 400 labelled non-수의계약 notices of [ids.txt](ids.txt), ZIP `d-facts-results-1790493234778894667`.
- Dev: `notebooks/colab-d-facts-dev.ipynb`, dev 200, ZIP `colab-results-1790496329821691244`.
- `tools/replay_run.py` reproduces both runs' `submission.csv` byte for byte. Every number below is a replay
  of those saved responses with the facts call switched on per item (`QUALIFICATION_FACTS_ITEMS`).
  Off-dev is scored against `reports/labels-3000/merged.csv`, halves by `half(id)`.

## Per item, facts call off → on

| Item | Off-dev 400 TP/FP/FN | Dev TP/FP/FN | Verdict |
| --- | --- | --- | --- |
| v1 | 2/6/28 → 15/160/15 | 4/0/3 → 7/74/0 | dropped |
| v2 | 4/0/20 → 16/28/8 | 5/0/2 → 7/4/0 | kept with `NOT_ENTRY_QUOTE` (below) |
| v3 | 1/11/1 → 1/7/1 | 8/0/0 → 8/0/0 | kept |
| v4 | 4/3/4 → 6/23/2 | 6/0/0 → 6/19/0 | dropped |
| v5 | no change | no change | dropped (moves nothing) |
| v6 | 1/6/1 → 1/1/1 | 5/0/1 → 4/0/2 | kept |
| v7 | 7/3/5 → 8/2/4 | no change | kept |
| v8 | 4/0/4 → 7/12/1 | 6/0/0 → 6/3/0 | dropped |

v2's 28 new false alarms quote submission checklists and evaluation criteria ("실적증명서 1부",
"평가 점수에 반영", "이행실적 심사분야"). `NOT_ENTRY_QUOTE` refuses such a quote as an entry condition:
v2 off-dev 15/12/9, dev 7/1/0. Its words follow the item definition but were written after reading
those quotes on the whole 400, so its split-half gain is not independent evidence.

## Candidate: v2 (filtered), v3, v6, v7

| | Off-dev Macro | Half A | Half B | Dev Macro |
| --- | ---: | ---: | ---: | ---: |
| Facts call off | 0.376335 | 0.406514 | 0.314146 | 0.824077 |
| Candidate | 0.409442 | 0.431652 | 0.331270 | 0.823698 |

Adoption rule of 9/27: pool Macro up; both halves up; no trusted item loses more than one net
(TP − FP) cell (v2 4 → 3, v3 −10 → −6, v6 −5 → 0, v7 4 → 6); dev −0.0004. Passes, with the
`NOT_ENTRY_QUOTE` caveat above.

## Server time

Dev phase seconds (200 notices, 165 non-수의계약): main 368, SME 90, company size 206, facts 151.
The facts call costs about 0.92 s per selected notice. The server total depends on its 수의계약 share:
about 6,200 s at the unlabeled pool's 45%, about 7,300 s at dev's 17.5%, which is over the 7,200 s limit.
`QUALIFICATION_DEADLINE_S = 6600` stops the facts call from starting chunks after 6,600 s; unreached
notices keep the main verdicts. The 9/27 upload of `main` (#166, no facts call) measures the share.
