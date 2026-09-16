---
scope: project
severity: contract
triggers: ['\S']
reads: [docs/workflow.md, docs/contest.md, docs/rules.md, docs/data.md, docs/items.md, docs/design.md, docs/contracts.md]
---

# 대회 작업 계약

규칙. Claude/Codex 역할은 작업으로 정한다. 공통 절차는 `docs/workflow.md`를 따른다.
공통 위키는 `ai-coding-agent-wiki-public`의 `.wiki/wiki-revision` 고정 버전에 연결한다.
설치법은 `docs/setup.md`, 프로젝트 작업 이력은 `.wiki/decisions/`·`docs/tasks.md`가 소유한다.
사용자의 혼합 도구 팀 지시에 따라, 허브의 특정 모델·Codex 셀 전용 배정은 이 프로젝트에 적용하지 않는다.
구현과 독립 리뷰의 분리는 유지하되, 두 역할 모두 Claude 또는 Codex 세션이 맡을 수 있다.
대회 제약은 `docs/rules.md`, 입력·출력은 `docs/data.md`, 공정 경계는 `docs/design.md`에서 읽는다.
대회 평가·운영은 `docs/contest.md`에서 읽는다. `archive/contest/`는 보관본이므로 기본 읽기 대상에서 제외한다.
항목 작업 전 `docs/items.md`에서 v1~v24의 공식 이름·부재탐지·관련 조문을 확인한다. 번호의 뜻을 추측하지 않는다.
판정에는 대회 제공 자료만 사용한다. 공용 코딩 위키를 법령 자료로 사용하지 않는다.
외부 API 라벨링과 오프라인 제출 추론을 분리한다. R6의 확장 용도는 Q1 확인 전 보류한다.
`docs/rules.md`의 A표에서 허용된 활용 방법을 찾고 R표의 조건을 함께 적용한다. 명시적 허용을 임의로 금지하지 않고, 애매한 부분만 Q로 분리한다.
mock 성공은 모델 정상 호출·성능 검증이 아니다. 실제 상태와 미래 설계를 구분한다.

왜. 발표의 준비 공정 제안과 대회 규칙의 허용 범위가 다르며 팀은 두 AI를 함께 사용한다.
어겼을 때. 승인되지 않은 산출물 사용·역할 혼동·제출 요건 미충족이 발생한다.
