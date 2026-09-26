---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: Prepare submission ZIP via git clone in Colab"
pr: 2
merged: 2026-09-16
branch: "fix/codex-colab-clone"
---

# fix: Prepare submission ZIP via git clone in Colab

What. Complements the flow where Colab verification relied on manual local ZIP uploads. In default mode, it git clones a public repository, records the actual commit SHA, and then generates the submission ZIP/verification bundle using existing packaging tools. It continues to use the same ZIP verification, HF_TOKEN model preparation, server headless execution, and verification ZIP download, while also allowing for specific local ZIP uploads.

Why. Verification: 4 tests passed in tests/test_package.py. Confirmed consistency between local Git main actual clone→commit recording→packaging code, and regression check for manual upload path. Passed Ruff, diff, UTF-8 without BOM/LF, and nbformat. Actual Colab GPU execution is unverified. Independent review is omitted per user instruction, and this is a follow-up supplement to previous commits, PRs, and merge requests.

Source. PR #2 · `fix/codex-colab-clone`
