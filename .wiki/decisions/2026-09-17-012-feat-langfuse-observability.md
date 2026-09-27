---
scope: project
severity: contract
triggers: ["langfuse", "관측", "트레이스", "span", "docker", "터널", "cloudflared"]
domain: 'observability'
title: "feat: separate local Langfuse stack with a diagnostics.jsonl sidecar"
pr: 12
merged: 2026-09-17
branch: "feat/langfuse-observability"
---

# feat: separate local Langfuse stack with a diagnostics.jsonl sidecar

What. To monitor the competition execution in real-time and allow team members to view the same screen, run a local Langfuse v4 stack separately in `docker/langfuse/`, and have `tools/langfuse_tail.py` read and send `diagnostics.jsonl`. Do not modify `script.py`. Usage is owned by `docs/langfuse.md`.

Why was `script.py` not instrumented? That file is the submission itself. If the Langfuse client enters it, it violates R7 (prohibition of external calls for submission inference) and R17 (immediate disqualification for sending evaluation data externally), and also breaks the Colab rule of "submitting the verified ZIP as is." Since `script.py:851` performs `flush()` for every event, reading it from the side provides real-time monitoring. The submission ZIP only contains `script.py` and `requirements.txt` according to `tools/package.py`'s `FILES`, so this tool cannot be mixed in.

Why was the existing stack not reused? The `ai-companion-voice-agent` stack on the same machine's ClickHouse contains 107,635 original user screen model entries for that product. Since this repository must be opened via a tunnel due to Colab collection, using the same instance would place those original entries behind the team member login. Langfuse's project-level roles are a paid (Enterprise) feature, so in the free self-hosted version, organization members see all projects in the organization—this cannot be prevented by splitting projects; the instances must be separated. The compose file, secret generation rules, and operational knowledge were imported as-is from that stack, and only the ports were changed (project name `langfuse-nara`, web 3002 · worker 3031 · clickhouse 8124/9002 · minio 9092/9093 · redis 6380).

Things to observe. Do not create other projects in this instance. Invite team members as Member or Viewer, and do not share the `LANGFUSE_INIT_USER_*` Owner account. The tunnel only opens web 3002, while clickhouse, minio, and redis remain on the loopback. Send only public dev materials. Do not include langfuse or opentelemetry in `requirements.txt`. The `~/.wslconfig` limit was raised from 5500MB to 11000MB, and it should be reverted when this stack is taken down after the competition ends (recorded in the file comments along with past OOM incident logs).

Analysis input is still `diagnostics.jsonl`. This stack is `LANGFUSE_MIGRATION_V4_WRITE_MODE=events_only`, so the read-only public API returns 404, and the only way for humans to view it is through the UI. Langfuse does not replace that file.

Verification (2026-09-17, this machine). Stack 6-container startup and health `4.27.0`, 6 mock diagnostics sent as a sidecar to load 12 spans into the new ClickHouse, at the same time the voice-agent stack remains at 107,635 entries with 0 competition spans, confirmed external health 200 and login 200 via temporary tunnel before closing and automatic restoration of `NEXTAUTH_URL`. Passed `tests/test_langfuse_tail.py` 3 cases and Ruff.
**Actual GPU/Colab session, real-time tracking of `--follow`, and team member account invitations have not been done yet.**

Remaining line. Adding `prompt_text` to the `debug_responses` branch of `script.py:579` will fill the "delivery context" field of the 5-stage diagnosis. Since `script.py` is owned by B, pass it to them.

Scope of disclosure. Since the repository is PUBLIC, other project names and the entry counts of that stack were removed from the disclosed files. This record is kept only locally along with other files in `.wiki/decisions/` (per `docs/tasks/public-push.md`'s "do not add existing untracked decision files to public").

Source. PR #12 · `docs/langfuse.md` · `tools/langfuse_tail.py` · `tools/langfuse_local.py`
