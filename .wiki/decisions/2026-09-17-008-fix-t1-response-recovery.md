---
scope: project
severity: contract
triggers: ["대화\\s*(모델|프롬프트|응답|생성)", "응답\\s*(정책|수리|스키마)", "페르소나", "말투", "gemini", "openai"]
domain: dialogue
title: "fix: prevent optional analysis failures from aborting valid submissions"
pr: 8
merged: 2026-09-17
branch: "fix/t1-response-recovery"
---

# fix: prevent optional analysis failures from aborting valid submissions

What. If the retry of the 6 items in the basic judgment returned an incorrect response, the entire submission was aborted. Only the failed group is further divided into single items for recovery, and groups that have already received a normal response are preserved.

Why. Failure of the additional 3-item analysis reverts to the verified basic 24-item judgment of the same announcement. Announcements without a basic normal response are not processed as successful, and Colab distinguishes between additional successes and the number of preserved basic items. English prompts and score thresholds are maintained. Verification: Reproduced 2 interruption paths before the fix, passed baseline 16 + package 5 + score 4 checks. Chunk index 62 regression, basic response/neighbor announcement preservation, false success rejection, ZIP decompression mock, Ruff/notebook syntax/encoding passed. Confirmed the identity of basic/additional prompts for 200 dev cases. Actual new GPU/server success is unverified. Distinguished between evidence of recovering 3 cases of output truncation in the previous Colab and the undetermined cause of the initial server error. …

Source. PR #8 · `fix/t1-response-recovery`
