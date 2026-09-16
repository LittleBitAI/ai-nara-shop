# Agent entry

- 모든 텍스트 파일은 **UTF-8 without BOM**, LF로 작성한다.
- Claude와 Codex는 같은 권한과 작업 절차를 따른다. 모델 이름으로 구현자·리뷰어를 나누지 않는다.
- 먼저 [docs/workflow.md](docs/workflow.md), [docs/README.md](docs/README.md)를 읽는다.
- 작업별 추가 문서는 문서 지도의 읽기 표를 따른다. 대회 제약은 [docs/rules.md](docs/rules.md)가 정리한다.
- 대회 문서는 `docs/`의 주제별 작업본을 사용한다. `archive/contest/`는 출처 대조용 보관본이며 기본 읽기 대상이 아니다.
- 항목 관련 작업 전 [docs/items.md](docs/items.md)에서 v1~v24의 뜻·부재탐지·국가/지방 조문을 확인한다. 번호의 의미를 추측하지 않는다.
- 기본 역할은 구현자다. 리뷰 요청을 받은 세션은 리뷰어이며 소스 수정 대신 근거 있는 발견 사항을 남긴다.
- 작업을 시작할 때 [docs/tasks.md](docs/tasks.md)의 입력·출력·수정 범위·통과 조건을 확정한다.
- 완료 여부는 실행 증거로 판단한다. mock 성공, 실제 모델 성공, 서버 제출 성공을 구분한다.
- Codex의 선택형 질문은 사용 가능한 `request_user_input`을 쓴다. 프로젝트 실험 설정과 미지원 시 대안은 [docs/setup.md](docs/setup.md)에 있다.
- 공통 규칙 변경은 `docs/workflow.md`에서 한다. 이 파일에 사본을 늘리지 않는다.
