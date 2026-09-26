---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: Revert the existing .gitattributes"
pr: 66
merged: 2026-09-20
branch: "fix/restore-gitattributes"
---

# fix: Revert the existing .gitattributes

What. In PR #65, I treated `.gitattributes` as a diagnostic screen task and removed it entirely, but that was incorrect.

Why. `f455753` did not create that file; it added 6 lines for the launcher to the existing 19 lines. It was my mistake to read `--stat`'s `6 ++++` as adding a new file. | Rule | Why | | --- | --- | | `* text=auto eol=lf` | Repository default line endings | | `/archive/contest/ -text` | Preserve original bytes for archives | | `/reports/runs/ whitespace=-trailing-space` | Keep episode logs exactly as the execution produced the bytes | | `/compare/comparison.md whitespace=-trailing-space` | `compare_runs` table column alignment uses trailing spaces | | `*.diff` · `*. …

Source. PR #66 · `fix/restore-gitattributes`
