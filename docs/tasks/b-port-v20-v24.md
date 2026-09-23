# Handover — port v20 (#111) and the v24 budget axis (#119) into `script.py`

Status: review. Both ports are in, rebased on `main` `c8d99fe` (#98 v17 gate and
#114 merged; its `script.py` is the same as `9631dbd`'s). Each commit is separately green on the full suite except the two
`test_setup_agents` errors that `main` also has (environmental). Awaiting the
independent review of the operating-code port and A's submission decision.

Started 2026-09-23 by a session opened in another repository
(`ai-coding-agent-wiki-public`), finished the same day from this repository.

## Why

Two changes were adopted and merged but live only in `experiments/`, so the
submitted `script.py` does not include them.

| Change | Candidate | Plan status |
| --- | --- | --- |
| v20 from two facts in the notice | `experiments/v20_sw_clause_candidate.py` (#111) | adopted |
| v24 budget axis, field by field | `experiments/b_v24_budget_axis_candidate.py` (#119) | adopted, "운영 이전 대기" |

The user asked for everything adopted to be reflected in `script.py`.

## Measured — dev replay, `reports/runs/colab-1789902969401579900/dev-debug`, no model call

| Code | Macro F1 | v20 TP/FP/FN | v24 TP/FP/FN |
| --- | ---: | --- | --- |
| last submission `227631fe2` | 0.609275 | 1/4/4 | 4/12/4 |
| `main` `c8d99fe` (#98 v17 gate) | 0.622918 | 1/4/4 | 4/12/4 |
| + v24 port (commit 1) | 0.625695 | 1/4/4 | 5/12/3 |
| + v20 port (commit 2) | 0.652084 | 5/2/0 | 5/12/3 |

- Each port's `submission.csv` is byte-identical to the candidate's replay. For
  commit 2 the comparison is against a scratch module that stacks both
  candidates. That was measured on `788c7df` (0.615376 → 0.618154 → 0.644543);
  the steps after the rebase are the same, +0.002778 and +0.026389.
- #111 recorded 0.644816 on `788c7df`. The 0.0003 gap there is #122's
  deliberate v9 change (FP 9 → 13).
- Pinned replays move only these cells. v24: `PPS-DEV-29` v24·e24 in every
  comparison. v20: 7 cells on the HEAD pin, 10 in `DELIBERATE_MOVES`·`_A7`
  (FPs 056·064·068·144 cleared, FNs 24·131·132·134 raised, new FPs 124·135),
  7 in `_H2`. No other item and no v20 evidence cell moves.
- This is dev only. The server has not followed dev: the last two submissions
  gained on dev and lost on the server (`reports/submissions.json`,
  `dev_versus_leaderboard`).

## Where it is

- Branch `feat/port-v20-v24`, based on `main` `c8d99fe`.
  - feat(v24): `budget_mismatch()` and its helpers after the
    「왜 예산 축을 껐나」 block. `postprocess` raises v24 with the quoted amount.
    It stays out of `AXES`, as the task doc asks. `_as_int` became the existing
    `_int`, and the module-level `_` pattern became `_SP`. Re-pins the v24 cells.
    The A7 candidate predates the budget axis, so `test_v24_meta_diff_candidate`
    now pins its overlay's gap to exactly the budget-axis cells.
  - feat(v20): `v20_decision()` and its patterns go just above `postprocess`;
    the decision overrides the model, evidence blank. Generic names got an
    `SW_` prefix. Re-pins the v20 cells; `test_a8_v20_annex` expects 5/2/0.
- `tests/test_ported_candidates.py` holds the port tests: on all 200 dev
  notices the operating function must equal the candidate's. Stubbing either
  function out turns its two tests red.
- Synthetic tests whose notices named no software provider had v20 overridden
  to 0 — the adopted rule working. Their inputs changed, not the rule:
  `test_baseline`, `test_company_size` (two) and `test_sme_candidate` give the
  notice a 1468 registration with no 제48조 statement. `test_wiki_rag_pilot`'s
  consumer-wiring test stubs `v20_decision` to abstain, because no dev notice
  both abstains and gives the verifier v20=1.

## What is left

1. Review before it goes live. The plan requires the operating-code port to be
   reviewed before any run, and the v24 task doc says "옮긴 운영 코드는 그 PR
   에서 다시 리뷰한다". Use the `sol` Codex cell.
2. Push and open the PR. The PR body needs the evidence-source and
   unlabeled-check sections (#117).

## A's decision (the user's)

`docs/tasks/b-v24-budget-axis.md` says v24 goes in "다른 규칙과 묶지 않고
단독 제출한다". Merging both commits means the next `main` submission carries
both. A decides whether to submit v24 alone first, which commit 1 by itself
allows, or both together.

Decided 2026-09-23: both together. The server result will not separate the
two rules; that cost was accepted.

## Reproduce

```bash
python -X utf8 tools/replay_run.py --case reports/runs/colab-1789902969401579900/dev-debug \
  --script script.py --output-dir <new dir>
python -X utf8 tools/score.py --truth open/dev_labels.csv --pred <new dir>/submission.csv \
  --output-dir <another new dir>
```
