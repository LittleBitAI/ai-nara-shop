---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: Anyone can do Colab links/run preparation without approval"
pr: 138
merged: 2026-09-25
branch: "docs/colab-open-access"
---

# docs: Anyone can create Colab links and session preparations without approval

What. `docs/workflow.md` W4: Added an exception that fully permits Colab session preparation. For any session of B, C, or D, upon request, create a notebook without approval, push to `run/`/working branch, and provide a Colab link with a pinned commit. "Not needed" or "A approval required" are not valid reasons for refusal. `main` push, `main` operation `script.py` changes, merge, and competition submission follow existing permissions. `.wiki/project. …

Why. C session blocked Colab links and session requests, claiming "A approval is required." There was no such rule. W5 removed the session count limit starting 9/20, and D had already created `colab-d7-v3-firing.ipynb`(#101). The cause of the blockage was twofold. The §6 file ownership table gave `notebooks/` only to B, and phrases like "after A approval" from before 9/20 remained in places like `reports/team-c/README.md`. Per A's decision on 2026-09-25, it is now fully permitted.

Source. PR #138 · `docs/colab-open-access`
