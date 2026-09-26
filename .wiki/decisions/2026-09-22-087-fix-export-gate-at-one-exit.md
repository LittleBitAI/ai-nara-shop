---
scope: project
severity: landmine
triggers: ["langfuse", "사이드카", "수출", "위생", "span", "관측", "리뷰 라운드"]
domain: observability
title: "fix: Consolidate export boundaries into a single exit to break the five-round repetition"
pr: 87
branch: "feat/a8-observation-capture"
---

# fix: Consolidate export boundaries into a single exit to break the five-round repetition

## What happened

Received P0 for five consecutive rounds due to the prompt export boundary of `tools/langfuse_tail.py`.
12 out of 12 P0 cases were different sides of the same question — how far does the path where values go out as span reach?

| Round | Exit pointed out by review | Fix made at that time | What appeared in the next round |
| --- | --- | --- | --- |
| 1 | Body is included without conditions | gate at two slots `input`/`output` | Validation only looks at id, not body source |
| 2 | Body source·redirect·failure fields | Source comparison + transmission fix + failure field list | Prompt format is loose |
| 3 | Message format·environment proxy·session default | Format fix + proxy block + path removal | Validation is skipped if only the response is forged |
| 4 | Response binding·structured fields | Pair check + value sanitization by name | span name·`usage_details`·nested keys |
| 5 | Name·usage·nested keys, sanitization erases real values | Consolidated exits into one | Places writing directly outside the passage |
| 6 | Direct set in transmission loop, unsummarized tokens | Direct write places also into passage, default to summary | Places where plaintext exceptions were left as patterns |
| 7 | map keys, pattern of `phase`·`error_type`·version | Producer set comparison | Four remaining shape exceptions |
| 8 | Asset keys·self-declaration `dev_ids`·version·span name | Full set comparison | hash shape |
| 9 | `HEX` shape, missing producer error type | Recalculation comparison, read from source | Summary merges trace names |
| 10 | First seven digits of summarized hash | Use digest after prefix | — |

## Why it did not converge

It is not that two appeared when one was fixed. There were N sides from the beginning, and only two or three were closed each round.
The causes are two.

1. Blocked at every exit. There are multiple paths where values go out, and a gate was attached to each pointed-out spot.
   Then, the list to block is counted by hand, and that list is always insufficient. The insufficient amount became the discovery of the next round.
2. Guessed the criteria and performed checks via synthesis. The allowlist by name erased many of the producer's actual values (entire `settings.max_model_len`·`expected_model.id`·`environment` and `packages` which is a dict), and `groups`, assumed to be a list, was actually a list of dicts, causing a crash when run with actual logs. The "keep real value" check written with hand-written events caught none of the three. The enum set was also a guess, missing `mode="mock"` of the mock round.

## What was changed

Consolidated exits into one. `plan()` returns `[guard(op) for op in _plan(...)]`, and `guard()` looks at `name`·`status`·`key`·`usage_details`·`trace.name` right before serialization.
Even if a new field is created, it automatically passes through that passage — there is no list to enumerate.

key is also an exit. If `run()` has no name, it creates a span with key, and the orphan path writes key to metadata. Sanitizes `arm`·`sample`·`id`·`phase` used for assembly, and if it still does not match the shape, `guard()` changes it to a deterministic hash (same input → same key, pair maintained).

Changed criteria to actual measurements. `_producer_enums()` reads `mode`·`token_count_kind` from the executor class, and `phase`·`status`·`error_type` from the source. `_DICT_KEYS` is a key read from the actual H4 round log.

Changed checks to actual logs. Projects the H4 round log (1,020 events) to check for no crashes, real value preservation, and contamination blocking all at once.

## Four things learned from rounds 6~10

Creating a passage and everyone using that passage are different. A passage was created in round 5, but the transmission loop was not passing through it and was writing four attributes directly to the span.

If you cannot distinguish, do not send plaintext. The secret of the short English token spot cannot be distinguished from the version by looking only at the value. I used that indistinguishability as evidence for allowing plaintext, but that was P0 — the direction is reversed. Set the default to summary (`sha256:앞16`) and provide plaintext only when there is evidence.

Shape cannot prove the source of a value. Even hash is like that — `code_sha256="deadbeef"*8` passed. Now, plaintext passes the full set comparison:
Producer enum, producer constant, recalculated digest, contract's fixed version, input file's announcement id, closed asset keys.

One judgment that narrowed the check created the P0 set. In round 6, it narrowed the contamination sweep to body/path, saying "short tokens are blocked by the first floor." Since there is a mode where the first floor does not run, that judgment was wrong, and the P0 set of rounds 6, 7, and 8 came from that spot. As soon as the sweep was expanded to tokens, the next defect was caught.

## Divided the threat model into two layers

| Layer | What it blocks |
| --- | --- |
| `validate_dev_export()` | Is this log a fixed public dev round? Reconstructs prompt/document hash into actual dev and compares; if they differ, refuses the export itself |
| `_clean()`·`guard()` | Even in logs that passed, body/path/unknown strings are not exported as plaintext |

Do not defer to the upper layer what the lower layer cannot do. In metadata-only mode, the upper layer does not run at all, so to write "this value is blocked by the upper layer," you must verify that the upper layer actually sees that value.

## Summary is not a loss

The purpose of hash is "is it the same or different," and since the same hash is the same summary, that purpose is maintained. However, you must also look at the consumption path — in round 10, the first seven digits of the summarized value were all `sha256:`, so different rounds became the same trace name. A check that only compared `_clean()` return values missed that.

## Where are the rules

General rules are owned by the hub wiki [[gate-the-exit-not-the-callers]].
If P0 appears for two consecutive rounds on the same file/topic, do not wait for the third and change the blocking spot — expecting the review to find the next side is delegating the design to the reviewer.

Project-side contracts are owned by `docs/langfuse.md` and `reports/team-c/a8-v20-annex/observation-contract.json`.
