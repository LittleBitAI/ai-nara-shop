---
scope: project
severity: preference
triggers: []
domain: ''
title: "chore: Record measurement trends ledger and a5-scope rounds"
pr: 76
merged: 2026-09-21
branch: "chore/measurements-ledger"
---

# chore: Record measurement trends ledger and a5-scope rounds

What. Measurements were scattered in three places, making trends invisible.

Why. | Where | Only what | Missing | | --- | --- | --- | | `docs/runs.md` Index | One line per round | CPU replay, pilot's four measurements | | `reports/submissions.json` | Server scoring only | All dev measurements | | (None) | — | CPU replay candidates | `reports/measurements.json` is now the source for all measurements. Line 29. ``` gpu-run 17 · gpu-pilot 4 · cpu-replay 4 · server 4 2026-09-17 gpu-run 654c556 0.220788 ← Start 2026-09-18 server 57761ff 0.297862 2026-09-20 gpu-run 18f07e5 0. …

Source. PR #76 · `chore/measurements-ledger`
