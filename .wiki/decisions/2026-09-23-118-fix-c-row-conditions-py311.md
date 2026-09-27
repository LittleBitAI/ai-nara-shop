---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: B1 cleanup investigation script does not parse in Python 3.11"
pr: 118
merged: 2026-09-23
branch: "fix/c-row-conditions-py311"
---

# fix: B1 cleanup investigation script does not parse in Python 3.11

What. The B1 cleanup investigation script in `main` does not even parse in the supported environment, Python 3.11. Not a single line runs.

Why. The required environment set by ``` invalid-syntax: Cannot reuse outer quote character in f-strings on Python 3.11 --> reports/team-c/b1-aftermath/row_conditions.py:81:117 --> reports/team-c/b1-aftermath/row_conditions.py:82:24 ``` `docs/setup.md:51` is "Python 3.11 or higher". The syntax in question is PEP 701, which is from 3.12 onwards. It had not been revealed until now because the development environment was 3.12 or higher. PR #115 review caught the same defect in `c-unlabeled-multiplier/multiplier.py`. …

Source. PR #118 · `fix/c-row-conditions-py311`
