---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: v20 판정 페이지 세 군 파일럿 — 구현·CPU 검증, GPU 미실행"
pr: 82
merged: 2026-09-21
branch: "feat/wiki-rag-pilot"
---

# feat: v20 판정 페이지 세 군 파일럿 — 구현·CPU 검증, GPU 미실행

무엇. v20 판정 페이지가 사실 추출을 개선하는지 재는 세 군 파일럿을 구현했다. 설계는 [착수서](docs/tasks/wiki-rag-pilot.md), 준비 상태·한계는 [reports/wiki-rag-pilot/README.md](reports/wiki-rag-pilot/README.md)가 소유한다. …

왜. v20은 부재탐지이고, 판정의 핵심은 지침 제3조제2항 한 조항 — 발주기관이 입찰공고문 또는 제안요청서에 대기업 참여제한 하한제도 적용 여부를 근거와 함께 명시해야 한다는 것이다. 그 조문과 조건·예외를 모델에게 어떤 모양으로 주는 것이 사실 추출을 바꾸는지는 아직 아무도 재 보지 않았다. `raw`와 `wiki`의 인용문 집합을 같게 고정했으므로 첫 실험은 증류나 압축이 아니라 표현 구조의 효과만 가른다. `raw`가 `wiki`와 같거나 좋으면 더 단순한 `raw`를 택한다 — 위키가 있다는 것은 근거가 아니다. 기존 collector는 군마다 독립적으로 본문을 줄이므로 세 번 부르는 것만으로는 같은 입력이 아니다. 그래서 공통 예산을 추론 전에 고정했다. 대가가 있다. …

출처. PR #82 · `feat/wiki-rag-pilot`
