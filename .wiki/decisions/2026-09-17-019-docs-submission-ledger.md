---
scope: project
severity: contract
triggers: ["서버 점수", "리더보드", "제출", "submission", "0.2197", "dev 격차", "채점", "시간 한도", "2시간", "7200"]
domain: 'submission-ledger'
title: "docs: Record the first scored server submission in the submission ledger"
---

# docs: Record the first scored server submission in the submission ledger

What. Submitted `654c556` on 2026-09-17 and received a leaderboard score of **0.2197036943**. This fact was nowhere to be found in the repository, and only `server_submitted: false` remained. The cause was that there was no place to write it down, so I created a `reports/submissions.json` to have each submission as a single row. Failed `5506ca0` attempts were also included in the same ledger. `docs/runs.md`, `docs/roadmap.md`, `.wiki/plan-active.md`, and `reports/team-score-audit/result.md` point to this ledger.

I also noted that the same round took **6,192 seconds (103 minutes 12 seconds)**. This is 86.0% of the 2-hour limit, and the remaining margin is 1,008 seconds.

Why. A submission is a different event from an execution, and the score appears long after the execution finishes, so if I put it in the execution record index, `tools/register_run.py` would erase the manually written server score when re-registering the same execution. The difference between the public dev 200 count of 0.22078771129016228 and the private 1,853 count of 0.2197036943 is 0.0010840169901622787, but **the two numbers are measurements of different input sets, so it is not an error.** I do not generalize how well dev represents the server with a single sample. The fact that it was scored does not identify the cause of the previous `5506ca0` failure either — the server raw response cannot be seen, and the two submissions have different code (`9abb9c4e` vs `79a56041`). The score and submission date are values copied by the user from the competition screen, and the submission ID, exact time, and public/private distinction were not received. The remaining count for the once-a-day submission limit (R16) is checked in the competition submission history.

Time is more restrictive than the score. Changes that increase model calls must fit within 1,008 seconds, and estimating server time by multiplying the seconds per count of the 200 dev items is inaccurate — multiplying the 3.469 seconds per count of the Colab A100 40GB by 1,853 items results in 6,428 seconds, which exceeds the actual measured 6,192 seconds. Even though the server is a single L40S, it was faster. The reason is unknown, and the time per server step cannot be obtained. This margin is the value for that code and that input round, and it does not guarantee the next round.

Source. `reports/submissions.json` · `docs/runs.md` Competition server submission · `reports/t1-baseline/server-failure.md`
