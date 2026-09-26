---
scope: project
severity: contract
triggers: ["화면", "vision", "프레임", "스크린", "캡처", "공유"]
domain: vision
title: "feat: Diagnostic screen to view 200 dev items by category"
pr: 67
merged: 2026-09-20
branch: "feat/dev-diagnosis-screen"
---

# feat: Diagnostic screen to view 200 dev items by category

What. When a Colab result ZIP is uploaded, it displays F1 scores by category from v1 to v24, and allows viewing where the 200 dev items were correct or incorrect, including opening the original announcement text. This is a screen for viewing existing results, not for inference.

Why. ```powershell report.cmd # Windows (더블클릭도 됨) ./report.command # macOS (Finder 더블클릭) ``` The ZIP filename changes every round, so it is not recorded anywhere. `--latest` Select the most recent `colab-results-<숫자>.zip` from the box received. Left: List of 24 categories combined with F1 bars / Right: Category strip → Announcement drill-down - Strip — Only show what needs to be seen per category (FN, FP, TP) in large size, fold the approximately 180 TN cells - Drill-down — Original announcement + evidence highlight + model judgment. …

Source. PR #67 · `feat/dev-diagnosis-screen`
