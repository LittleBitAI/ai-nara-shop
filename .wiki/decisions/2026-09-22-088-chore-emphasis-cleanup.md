---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: Remove bold emphasis to clear markdown document rule violations"
pr: 88
merged: 2026-09-22
branch: "chore/emphasis-cleanup"
---

# docs: Remove bold emphasis to clear markdown document rule violations

What. `repo_lint` discovery 293 cases → 1 case.

Why. | Discovery | Count | Resolution | | --- | --- | --- | | hook drift | 5 | Upload to wiki pin 9ebdc0e and reinstall `setup_agents.py` (81945b4) | | Excessive emphasis (`emphasis-is-scarce`) | 288 | Remove 3,075 bolds from 99 `.md` (77b43a0) | | Remaining | 1 | `archive/contest/데이터 명세.md` — Competition provided archive | The `emphasis-is-scarce` rule for the new `write-markdown` skill on the hub wiki prohibits bolding in paragraph labels, commands, paths, and identifiers. This repository document was written before that rule, and there were 99 documents with dozens of bolds in a single document. - This is block-level processing. …

Source. PR #88 · `chore/emphasis-cleanup`
