---
scope: project
severity: contract
triggers: ["게이트", "검증기", "인용 검증", "quoted", "restore_spacing", "evidence_refutes", "조기 반환", "early return", "후처리", "postprocess"]
domain: 'judgement-pipeline'
title: "fix: The gate does not call the validator even though it is right next to it — A defect family that appeared three times in one day"
---

# The gate does not call the validator even though it is right next to it

2026-09-22 I found the same type of defect in three places in one day. All three were in the form of "the validator needed for the judgment is already in the code, but the gate does not call it." Two moved the score and one was neutral, but I only realized it was the same disease on the third one while fixing them separately.

| Location | What is missing | Symptom |
| --- | --- | --- |
| `evidence_refutes()` | The top `if not evidence: return False` was before the v24 branch | Most of the v24 false positives were evidence-empty positives, so they did not even reach the contrast test. It stopped at v24 `5/28/3`, and the branch had to be moved above the early return to become `4/12/4` |
| `competitive_product()` lookup | Only looked up the code pointed out by the direct generation clause | `PPS-DEV-060` wrote 3 code matches in the body, but the catalog did not have a chance to speak |
| `_company_size_bands()`'s `quoted()` | Did not call `restore_spacing()` | An exact citation where a line break was pressed as a space fell as unverified. `PPS-DEV-043`·`PPS-DEV-22` were blocked by `unverified_qualification`, and both are v18 positives |

## Why does this pattern repeat?

Because the gate and the validator are created separately. The validator is carefully crafted to properly answer "is this citation in the original text?", but the gate filters it out first with a cheap condition in front of it. If that cheap condition cuts out cases that the validator could answer, the validator is not called even though it is perfectly fine.

`verify_document_requirements()`'s `quoted()` calls `restore_spacing()`.
`_company_size_bands()`'s `quoted()` did not call it. Two functions with the same name were judging the same citation differently, and since neither could be said to be wrong, they survived for a long time.

## How to catch it

If there are two or more functions that make the same judgment, check if they both call the same validator. This is especially true if the names are the same — the same name means the same judgment, and if they judge differently, one of the two is a bug. When adding an early return, check if the branches below it can answer regardless of that condition.

I left a regression test for the third one —
`tests/test_baseline.py::test_both_quote_gates_restore_spacing_before_judging` checks if `restore_spacing` exists in the source of the two `quoted()`s. I reverted the fix to confirm that it actually turns red. If you only look at the pass, you cannot distinguish it from a test that does nothing.

## What is not proven

There is no evidence that these repairs increase the server score. Submission `227631f`, which contained the first two, raised dev by +0.015428 with the same original response playback, but the server was 0.5084137874 → 0.5077356078 (−0.0006781796) ([Result ](../../reports/submission-227631f-server-result.md)).
The third one is dev neutral. The value of this record is not the score, but the name of the defect family.
