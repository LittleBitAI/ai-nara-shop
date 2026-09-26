---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: Supplement item scope and participant qualification judgment"
pr: 6
merged: 2026-09-17
branch: "fix/codex-sme-applicability"
---

# fix: Supplement item scope and participant qualification judgment

What. The existing separate judgments for v10, v11, and v13 mistook item name matching for confirmed application and missed notification candidates for services without formal item names. Distinguish between code/string matching sources and non-listed notification codes, and provide the list of provided services for services where codes do not match. Judgment instructions verify item specifics, contract exceptions, and actual participant qualifications, and distinguish conditions that allow only small and medium-sized enterprises and small businesses.

Why. Maintain the 21-item preservation structure, which differs from the basic 24-item message, model settings, and split retries, as well as the Colab quality standards. The analysis of previous actual results and the verification scope of new candidates are recorded in reports/t1-baseline/sme-applicability.md. Verification: 13 baseline, 5 package/Colab, and 4 score passed. Basic dev messages 200 cases identical, fixed revision FastTokenizer maximum 14,261 tokens, 0 additional document reductions. ZIP decompression mock, Ruff, UTF-8 without BOM/LF, links, and diff checks passed. Actual GPU execution, F1, time, and server success of new candidates are unverified. Users must re-run actual candidates in Colab. …

Source. PR #6 · `fix/codex-sme-applicability`
