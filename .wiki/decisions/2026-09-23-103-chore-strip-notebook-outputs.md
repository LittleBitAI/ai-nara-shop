---
scope: project
severity: preference
triggers: []
domain: ''
title: "chore: Remove execution output and iteration REPO_REF from colab-baseline notebook"
pr: 103
merged: 2026-09-23
branch: "chore/strip-notebook-outputs"
---

# chore: Remove execution output and iteration REPO_REF from colab-baseline notebook

What. `1d6b106 "Colab을 통해 생성됨"` While saving this Colab session, execution output 11 cells and `execution_count` were committed together (+2,380 / −563 lines). Reverting that.

Why. ```diff -REPO_REF = "main" +REPO_REF = "9ed08054fc2c288a57fa33c689ea1f31703d15b2" ``` That SHA is an experimental commit for the B1 iteration. If it is embedded in the base notebook of `main`, the next person will run it as is, and the iteration will run with a rejected candidate instead of the production code. Iteration-specific values should be held by the request form and iteration records, not by notebook defaults. `1d6b106` Reverted to the version immediately preceding. Instead of fixing it manually, that version was extracted as is. …

Source. PR #103 · `chore/strip-notebook-outputs`
