---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: 회차 대기열이 반려된 브랜치를 실행하라고 시키지 않게 한다"
pr: 53
merged: 2026-09-18
branch: "docs/gpu-run-queue-refresh"
---

# docs: 회차 대기열이 반려된 브랜치를 실행하라고 시키지 않게 한다

무엇. 브랜치 정리 중 발견했다. `docs/tasks/gpu-run-queue.md` 의 실행 카드 — 팀원이 보고 그대로 돌리는 곳 — 이 아직 이렇게 적고 있었다.

왜. ```python REPO_REF = "exp/round1-absence-evidence" # 이렇게 ``` 그 실험은 반려됐다. 그리고 그 브랜치를 지우려던 참이다. 지우기 전에 이 문서부터 고친다. | 고친 곳 | 전 | 후 | | --- | --- | --- | | 실행 카드 회차 B | 반려된 브랜치로 손수정하라 | 무수정 노트북 셋 N1·N2·N3 | | §0 시간 여유 | 1,008초 (`654c556`) | 2,919초 (`57761ff`) | | §2 R1 | 앞으로 돌릴 것처럼 | 끝났다. 반려. + 실측 | | §3 R2 | 앞으로 돌릴 것처럼 | 안 돌린다 (재현할 값이 없어졌다) | 문서의 §4 갈림길표는 "TP 가 섰다 / 안 섰다" 두 칸뿐이었다. 실제로는 어느 칸도 맞지 않았다. …

출처. PR #53 · `docs/gpu-run-queue-refresh`
