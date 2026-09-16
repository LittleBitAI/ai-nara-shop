# 문서 지도

항상 읽는 규칙은 짧게 유지하고, 작업에 필요한 계약만 추가로 읽습니다.
각 규칙은 한 문서가 소유합니다. 다른 문서에서는 링크와 규칙 ID로 참조합니다.

항목 관련 작업 전 [items.md](items.md)에서 **v1~v24의 공식 항목명·부재탐지·관련 조문**을 확인합니다.
항목표 원본과의 연결을 제공하는 색인이며 상세 판정 명세의 승인 상태와는 구분합니다.

대회 파이프라인 작업은 먼저 [rules.md](rules.md)의 **A표(허용 활용)·R표(필수 조건)·Q표(미확정 범위)**를 읽습니다.
단계에 맞는 허용 방법과 지킬 조건을 함께 작업서에 기록합니다.
`docs/`는 기존 대회 산문 자료를 주제별로 통합한 작업 문서입니다. 보관본이 없어도 일상 작업이 가능하도록 필요한 내용을 이곳에 둡니다.

## 권위와 상태

| 자료 | 역할 |
| --- | --- |
| 사용자 지시·해당 경로의 AGENTS.md | 작업 권한·범위·인코딩 |
| 대회 공식 규칙·제공 명세 | 제출 적격성·데이터 계약. 팀 설계로 완화할 수 없음 |
| `docs/contest.md`, `docs/rules.md`, `docs/data.md`, `docs/items.md` | 각각 대회 안내·허용/금지·데이터 계약·24항목의 단일 작업 기준 |
| `docs/workflow.md` | 두 AI와 팀원의 공통 작업 방식 |
| `docs/design.md`, `docs/contracts.md` | 팀 설계. 구현 시 보호할 경계·산출물 계약 |
| `docs/roadmap.md`, `docs/tasks.md` | 우선순위·담당 역할·작업 상태 |
| PPTX·기존 위키 | 설계의 근거. 대회 규칙과 충돌하면 규칙 우선 |

`확정`은 제공 원문에서 확인한 사실, `팀 설계`는 이번에 구체화한 방안,
`미확정`은 담당자·예산·운영진 답변 등이 필요한 사항입니다.
최신 공식 공지와 다른 내용이 확인되면 출처·확인일을 기록해 갱신합니다.
발표에 나온 날짜를 새로 확인한 공식 일정처럼 인용하지 않습니다.

## 작업별 읽기

| 작업 | 추가로 읽기 | 실제 작업 입력·구현 |
| --- | --- | --- |
| 대회 이해·평가 전략·운영 | [contest](contest.md), [roadmap](roadmap.md) | 제공 안내의 평가 비중·일정, 새 공식 공지가 있는 경우 변경 사항 |
| 전처리·문서 선택 | [data](data.md), [design](design.md) | `open/baseline/script.py`의 입력·예산 처리 |
| 명세·법령 매핑 | [items](items.md), [rules](rules.md), [contracts](contracts.md) | `open/data/항목표.json`, `open/data/법령패키지/` |
| 라벨·사례 생성 | [rules](rules.md), [contracts](contracts.md) | `open/train_unlabeled.jsonl`, `open/dev.jsonl` |
| 프롬프트·검색 | [design](design.md), [contracts](contracts.md) | 승인 명세, 항목표, RAG 노트북 |
| 고정 모델·프롬프트 실행 특성 | [Gemma 4 조사](gemma4.md) | 고정 리비전 모델 카드·기술 보고서·thinking/채팅 규약, 검증 전 실험 후보 |
| 채점·실험 | [data](data.md), [contracts](contracts.md), [roadmap](roadmap.md) | `open/dev_labels.csv` |
| 패키징·제출 | [rules](rules.md), [design](design.md) | 베이스라인, 제출 직전 공식 평가 탭 |
| 리뷰 | [workflow](workflow.md), 변경한 계약 문서 | diff, 호출자, 실행 기록 |
| 도구 설치 | [setup](setup.md) | `tools/setup_agents.py` → 공용 `tool/setup_agents.py` → `tool/apply.py`; checkout의 `.wiki/adapter.toml` |

## 작업본과 보관본

- `docs/`: 주제별 작업본. 규칙·설계 변경은 해당 소유 문서 한 곳에서 관리합니다.
- `archive/contest/`: 기존 `대회/` 4개 파일의 보관본. 바이트·파일명을 보존하며 기본 AI 읽기 대상에 넣지 않습니다.
- [sources](sources.md): 원문 절·FAQ의 통합 위치, 선택적 원문 링크, PPTX 슬라이드·해석 차이를 추적합니다.
- `open/`: 실제 공고·정답·법령·베이스라인 입력. 보관 문서와 달리 구현·판정에 필요합니다.
- PPTX는 설계 근거로 유지합니다. `대회/`를 열라는 작업 지시는 사용하지 않습니다.

새 공지가 오면 해당 작업본과 출처 기록을 함께 갱신합니다. 내용 누락을 원문 재독 지시로 대신하지 않습니다.
