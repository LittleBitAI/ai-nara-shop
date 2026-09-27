---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: stop the decision-record collision and add the CPU replay path"
pr: 24
merged: 2026-09-17
branch: "fix/decision-numbering-and-cpu-replay"
---

# fix: stop the decision-record collision and add the CPU replay path

What. Remove the serial number from the decision record name. Since `tools/register_run.py` uses `<날짜>-run-<run-id>.md`, it cannot collide with records that the public wiki caches by PR number. Moved the 3 already created records, and matched the submission ledger record to the actual PR number `019`. Preserved the 6 hook creations by changing them to LF and deleted the duplicate `014`. Update the fixed wiki revision to `bf7200d` which includes the guard. Create a new `tools/replay_run.py`. …

Why. ### Decision record collision The public wiki `sync` overwrote the manually written decision records 013, 015, and 016. `recorded()` judged them as unrecorded PRs because it only looked at the `pr:` line of the frontmatter, and since the filename rules were the same, `write_text` overwrote them as they were. It was a working tree change, so it was restored and not committed. A guard was added to the hub ([PR #6](https://github.com/LittleBitAI/ai-coding-agent-wiki-public/pull/6) — reads the filename number, does not overwrite existing files, and writes in LF). On this side, the number is removed from the name so that the collision itself does not occur. The run-id is unique in itself. The hook was useful, so it was not deleted. …

Source. PR #24 · `fix/decision-numbering-and-cpu-replay`
