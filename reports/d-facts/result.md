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

## On top of #163 (v3 cut 0.95) — what the PR carries: v2 (filtered), v6, v7

#163 merged into `main` while this ran. With its v3 cut the facts call's v3 fails the trusted-item guard
(off-dev 0/2/2 → 1/6/1, net −2 → −5), so v3 is off.

| | Off-dev Macro | Half A | Half B | Dev Macro |
| --- | ---: | ---: | ---: | ---: |
| `main` with #163, facts call off | 0.369842 | 0.395150 | 0.314146 | 0.821299 |
| v2, v6, v7 on | 0.400351 | 0.416500 | 0.331270 | 0.820920 |

Net (TP − FP): v2 4 → 3, v6 −5 → 0, v7 4 → 6. Dev −0.0004.

## Off-dev 600 run — how it is judged (fixed 2026-09-27 before its results)

Review #168 round 1 required the 9/27 rule's own evidence: a GPU run of the call change on the off-dev 600
(`reports/labels-600/offdev-600-ids.txt`, diagnostic 200 + sealed 400) and a check of `NOT_ENTRY_QUOTE` on
cases it was not written from. Code `c23ed84` (the filter narrowed to checklist, evaluation and form
markers, frozen), notebook `notebooks/colab-d-facts-600.ipynb`.

1. Replay the run with `QUALIFICATION_FACTS_ITEMS = []` (baseline) and `["v2", "v6", "v7"]` (candidate);
   the run's own CSV must replay byte-identically first.
2. Score against `reports/labels-600/merged/diag.csv` + `sealed.csv`, leaving out
   `reports/labels-3000/private-ids.txt` (수의계약, as all off-dev scoring since 9/27). Halves by `half(id)`.
3. The 9/27 rule: Macro over the labelled items rises; it rises on each half; no trusted item loses more
   than one net (TP − FP) cell; dev replay (the dev run above) drops by no more than 0.01.
4. An item that alone breaks rule 3 is dropped and the rest re-checked once. Nothing else is tuned.
5. The 400 above are reported next to it but do not decide.

## Off-dev 600 run — result: rejected

ZIP `offdev-600-results-1790507223022930981`, code `c23ed84`, shards u00 500 + u01 100, all complete, self-check PASS.
Both shards replay byte-identically. 352 of the 600 are scored (248 are 수의계약 and left out; the facts call
ran on the same 352).

| Items on | Macro | Half A | Half B | Net (TP − FP) |
| --- | ---: | ---: | ---: | --- |
| none | 0.535832 | 0.464728 | 0.482855 | v2 7, v6 −2, v7 15 |
| v2, v6, v7 | 0.545714 | 0.473145 | 0.489221 | v2 7 → −1 (7/0/20 → 18/19/9) |
| v6, v7 (step 4) | 0.538863 | 0.464728 | 0.482855 | v6 −2 → −1, v7 unchanged |

v2 breaks rule 3 (a trusted item loses 8 net cells). With v2 dropped, neither half rises, so rule 2 fails.
The facts call is rejected. `NOT_ENTRY_QUOTE` held its checklist and evaluation cases, but the model still
calls many plain performance clauses eligibility where the labels say otherwise: 11 true positives for 19
false alarms. The facts call cost 1.0 s per selected notice here (349 s over 352).

## v2 label audit — fixed before reading (2026-09-27, user decision)

v2 rises in F1 on dev gold (5/0/2 → 7/1/0), the 400 and the 600, and fails only rule 3, whose cells are
unaudited LLM labels (v2 trust rests on 5 dev positives). The 30 cells v2 changes on the 600 are read:
the 19 new false alarms and the 11 new true positives. Each is judged against `docs/items.md` v2 and S7-3:
v2 = 1 when the notice makes a past performance record (실적) of the bidder an entry condition
(입찰참가자격) and the estimated price is under 2.3억. Not v2: a record used only in evaluation or 적격심사,
a document checklist line that no eligibility clause requires, a licence or business registration, a
personnel career, a record-free condition. Unclear when the notice text cannot settle it; unclear cells
keep their label. This is a model reading (Claude), not a human one.

Pass line: v2's corrected net (TP − FP) on the 600 ≥ 6, i.e. at most one cell below the facts-off 7.
Pass → review round 2 on the facts call with `QUALIFICATION_FACTS_ITEMS = ["v2"]`. Fail → rejected stands.

### Audit result: fails — rejected stands

- 19 new false alarms: 14 label-0 correct (evaluation, proposal or 적격심사 sections: 005824, 014535, 007800,
  001080, 001938, 012494, 015176, 005294, 014771, 016313, 017650; licence or registration: 000225, 003606;
  personnel career: 006277; no record at all: 000491), 4 unclear (bid-registration document lists with a
  record certificate but no stated entry condition: 002003, 016375, 001714, 018514), 0 label errors.
- 11 new true positives: 10 correct (operative 입찰참가자격 clauses), 1 unclear (017667).
- Corrected v2 net stays −1 (pass line ≥ 6).

The call finds sentences that mention a performance record; it does not tell an entry condition from
an evaluation or proposal section. A before-the-audit glance at the quotes alone suggested about half
were label errors; read in their sections, none were.

## Server time

Dev phase seconds (200 notices, 165 non-수의계약): main 368, SME 90, company size 206, facts 151.
The facts call costs about 0.92 s per selected notice. The server total depends on its 수의계약 share:
about 6,200 s at the unlabeled pool's 45%, about 7,300 s at dev's 17.5%, which is over the 7,200 s limit.
`QUALIFICATION_DEADLINE_S = 6600` stops the facts call from starting chunks after 6,600 s; unreached
notices keep the main verdicts. The 9/27 upload of `main` (#166, no facts call) measures the share.
