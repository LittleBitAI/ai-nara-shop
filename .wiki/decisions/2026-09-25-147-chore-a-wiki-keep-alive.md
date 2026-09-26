---
scope: project
severity: contract
triggers: ["대화\\s*(모델|프롬프트|응답|생성)", "응답\\s*(정책|수리|스키마)", "페르소나", "말투", "gemini", "openai"]
domain: dialogue
title: "chore: keep the prompt cache of idle Claude sessions alive (keep_alive = 2)"
pr: 147
merged: 2026-09-25
branch: "chore/a-wiki-keep-alive"
---

# chore: Keep the prompt cache of idle Claude sessions alive (keep_alive = 2)

What. Insert `keep_alive = 2` into `.wiki/adapter.toml`. The wiki tool wakes up the Claude session resting in the Orca cell at 55 minutes, keeping the prompt cache alive for up to two times per utterance.

Why. This setting is intended to ensure the cache remains even after returning an hour later. This uploads the changes that remained uncommitted in this checkout as they are.

Source. PR #147 · `chore/a-wiki-keep-alive`
