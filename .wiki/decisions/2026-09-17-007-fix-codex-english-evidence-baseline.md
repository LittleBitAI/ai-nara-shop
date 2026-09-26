---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: English judgment instructions and 3-item fact verification"
pr: 7
merged: 2026-09-17
branch: "fix/codex-english-evidence-baseline"
---

# feat: English judgment instructions and 3-item fact verification

What. The previous 3-item supplementation was lower than the same execution baseline judgment at dev F1 0.211008, and it also judged phrases allowing medium-sized enterprises in v13 as violations. Per user request, basic, separate, and retry instructions are changed to English, while Korean legal terms and provided original texts are maintained.

Why. The separate step extracts item codes, target citations, application conditions, qualification phrases, and exceptions into the facts schema. The code compares the actually provided notification candidates and original text citations with the judgment status, and filters out qualifications including medium-sized enterprises and assertions of unobserved absence. If the fact response format is broken, existing split recovery is used, and failures are not replaced with normal 0. Colab compares English baseline judgment and post-verification judgment. Download conditions remain the same: the final F1 must exceed the same execution baseline F1 and be 0.2208013652894021 or higher. Other 21 items are preserved, and HF_TOKEN download, server entry point, fixed settings, and ZIP identity checks are maintained. Verification: 15 local baselines, 5 package/Colab, and 4 scores passed. …

Source. PR #7 · `fix/codex-english-evidence-baseline`
