---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: Place the set of experiment notebooks in main — they are not visible if they are only in the branch"
pr: 47
merged: 2026-09-18
branch: "docs/exp-notebooks"
---

# docs: Place the set of experiment notebooks in main — they are not visible if they are only in the branch

What. Place three experiment notebooks in the `notebooks/` of `main`. Move only the documents (notebooks) — do not touch `script.py`, `tools/`, or `tests/`. | Notebook | Pointing branch | Responsible item | | --- | --- | --- | | `exp-n1-absence-split.ipynb` | `exp/n1-absence-split` | v16·v18 | | `exp-n2-amount-band. …

Why. Since I uploaded the three notebooks only to their respective experiment branches, **the files were not visible in the working folder looking at `main`.** I cannot tell a team member to "please run this notebook." There is no reason for the notebook to be in the same branch as the experiment code. The only thing the notebook does is point to the experiment branch via `REPO_REF`, and Colab clones that branch directly. Therefore, the notebook should be in main, and the code should be in the branch.

Source. PR #47 · `docs/exp-notebooks`
