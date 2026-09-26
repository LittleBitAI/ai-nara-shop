---
scope: project
severity: contract
triggers: ["절대 경로", "개인 경로", "manifest", "산출물", "기록", "score.py", "portable", "cwd"]
domain: 'artifacts'
title: "fix: Do not leave absolute paths in committed artifacts"
branch: "fix/portable-paths-in-records"
---

# fix: Do not leave absolute paths in committed artifacts

What. Change the paths that `tools/score.py` wrote in manifest·result to repository-based relative paths.
If it is outside the repository, it is `<외부>/<파일명>`, the working folder is `.`, and the interpreter is `python`. I also removed paths containing usernames in the same format from line 14 of `reports/t2-self-check`·`t2-zero-check`·`t2-zero-shuffled` that were already committed. The rule is owned by `docs/workflow.md` W3.

Why. This path is not so much a security issue as it is a problem where the wiki reads it as a fact and follows it as is on other PCs, and this change only fixes the records created by the repository and does not touch the original execution logs.
`/content/...` in the Colab log is bytes created by execution, so it is left as is according to the [execution record](../../docs/runs.md) protocol. The remaining spots are `run_report.json`·`diagnostics.jsonl` of `script.py`, and those files are submissions and owned by B, so they were not included in this scope. If a team member runs it on their own PC, that record will still contain the personal path.

Verification: I reproduced that `C:/` is caught in both manifest·result by running `tools/score.py` as is before the fix, and there are 0 cases in the same test after the fix. I added regression test `test_records_keep_no_absolute_path` to `tests/test_score.py`, which fails if an absolute path or interpreter path appears.
28 cases of `tests.test_baseline`·`test_package`·`test_score` OK, Ruff passed.
In the full repository re-inspection, the remaining hits are only the `\n` escape of competition data `open/dev.jsonl`, docker volume mapping, and container paths in archived Colab logs.

Source. `docs/workflow.md` W3 · `tools/score.py` `portable()` · `tests/test_score.py`
