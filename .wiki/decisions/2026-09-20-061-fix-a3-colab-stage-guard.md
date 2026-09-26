---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: Fix A3 Colab check interruption and restore completed dev results"
pr: 61
merged: 2026-09-20
branch: "fix/a3-colab-stage-guard"
---

# fix: Fix A3 Colab check interruption and restore completed dev results

What. Modify check_live in the public/A3 Colab notebook to allow v13 change permissions for company_size even in rows where SME additional analysis is omitted. Modifiable items are read from the existing extra_call_items. Ownership-free v13, out-of-scope items/IDs, model success/selection counts/settings, and ZIP checks are maintained. Inference code and A3 REPO_REF remain unchanged. …

Why. Although 200 dev cases finished normally, the old protection condition blocked company_size from changing v13 from 0 to 1 in PPS-DEV-184. The previous check only verified v14~v18 changes for company_size, missing the v13 ownership overlap. The correctness of that judgment and the change permission in the pipeline are separate matters.

Source. PR #61 · `fix/a3-colab-stage-guard`
