---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: A4/A5 combined measurement and initial cleanup"
pr: 75
merged: 2026-09-21
branch: "docs/a4-a5-combined-report"
---

# docs: A4/A5 combined measurement and initial cleanup

What. Close #72 and move its outputs. As #69 and #71 were merged, the astra candidate copy that #72 was rendering is no longer needed.

Why. `main` I ran the same reproduction again with the code to confirm byte-for-byte identity with the #72 saved version. Macro 0.620382330538 remains the same. | | | | --- | --- | | `experiments/a4_a5_combined_candidate.py` | Only exporting the two candidates to different slots in the player. 0 lines of judgment rules | | `reports/team-c/a4-a5-combined/README.md` | Combined measurement — interference 0, 0.620382 | | `reports/team-c/a4-a5-combined/ROLLUP. …

Source. PR #75 · `docs/a4-a5-combined-report`
