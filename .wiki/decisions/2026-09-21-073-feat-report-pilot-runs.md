---
scope: project
severity: contract
triggers: []
domain: ''
title: "feat: Diagnostic screen now includes pilot episodes"
pr: 73
merged: 2026-09-21
branch: "feat/report-pilot-runs"
---

# feat: Diagnostic screen now includes pilot episodes

What. Even if a pilot episode (`a5-scope-…`) was registered in the `reports/runs/`, it was never displayed on the screen.

Why. The builder searches for episodes by `reports/runs/*/dev/submission.csv` (`build_report.py:345`), but pilot episodes do not have that file. Since only one step like `company_size` is run on the GPU and the rest are replayed from the archived raw response, one episode produces as many CSVs as (group × consumer). ``` $ python -X utf8 tools/build_report.py --run a5-scope-1789959906563639676 error: a5-scope-1789959906563639676: dev/submission.csv 가 없다 ``` `*-hybrid.csv` is identical to the submission in 49 columns. Therefore, keeping the screen's premise of "one item = one CSV", `<run-id>. …

Source. PR #73 · `feat/report-pilot-runs`
