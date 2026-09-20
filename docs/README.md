# 문서 지도

## 과제 한 장 — 무엇이 입력이고 무엇이 기준이고 무엇이 출력인가

이 구분이 문서 여러 곳에 흩어져 있어 실제로 오해가 난 적이 있습니다. 먼저 읽습니다.

| | 무엇 | 어디 |
| --- | --- | --- |
| **입력** | 공고 1건의 본문·첨부와 나라장터 등록 정보 | [data D2·D3](data.md) |
| **기준** | 제공 법령 23개 txt와 중기부고시 CSV. **판정의 근거이지 출력이 아닙니다** | `open/data/법령패키지/`, [items](items.md) |
| **출력 ①** | `v1`~`v24` 각각 위반 여부 **0/1** | [data D4](data.md) |
| **출력 ②** | `e1`~`e24` 근거 문구 — **그 공고 문서의 원문에서 그대로** 인용한 연속 부분문자열 | [data D4-4](data.md) |

**근거는 법령 조문이 아니라 공고의 문장입니다.** D4-4가 "법령·meta에서 가져온 값만으로
대체 금지"라고 못 박습니다. 법령은 *"5%가 위반인가"* 를 정하는 데 쓰고, 제출하는 근거는
*"이 공고가 5%라고 썼다"* 입니다. 실제 제출 CSV의 근거는 전부 이런 모양입니다.

```
[PPS-DEV-03] v3  '공고일 기준 5년 이내 공공디자인 용역 실적이 3천만원 이상인 업체'
```

부재탐지 5항목(v10·v11·v16·v18·v20)은 **v 값과 무관하게 `e`가 항상 빈칸**입니다(D4-5) —
"없는 것"이 위반이라 인용할 문장이 없습니다.
`e`는 리더보드 점수에 들어가지 않고 **2차 평가(정량 80% + 정성 20%)**에 씁니다([contest E2](contest.md)).

**라벨은 `open/dev_labels.csv` 200건이 전부입니다.** train 20,000건은 무라벨이고
자가 라벨 설계도 과제에 포함됩니다([rules](rules.md) A1~A3). 그래서 dev를 안 보고
시작할 수 없지만, **dev는 어디가 틀렸는지 찾는 데 쓰고 고치는 근거는 법령·고시에서
가져옵니다** — 그 구분을 안 지킨 규칙이 서버에서 이득의 절반을 잃었습니다
([workflow W5](workflow.md#w5-실험검증)의 무라벨 발화율 규칙).

---

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

4명 팀의 현재 배정안과 Opus 5 medium에 전달할 지시문은
[업무 분배·인수인계](tasks/team-handoff.md)를 사용합니다. 실제 6회 dev 결과를 바탕으로
24항목의 책임자와 연속 개선 과제를 정한 배정안이며 [점수 진단](../reports/team-score-audit/result.md)을 함께 봅니다.

| 작업 | 추가로 읽기 | 실제 작업 입력·구현 |
| --- | --- | --- |
| 대회 이해·평가 전략·운영 | [contest](contest.md), [roadmap](roadmap.md) | 제공 안내의 평가 비중·일정, 새 공식 공지가 있는 경우 변경 사항 |
| 전처리·문서 선택 | [data](data.md), [design](design.md) | 현재 `script.py`의 입력·예산 처리, 제공 원본 `open/baseline/script.py`와 비교 |
| 명세·법령 매핑 | [items](items.md), [rules](rules.md), [contracts](contracts.md) | `open/data/항목표.json`, `open/data/법령패키지/` |
| 라벨·사례 생성 | [rules](rules.md), [contracts](contracts.md) | `open/train_unlabeled.jsonl`, `open/dev.jsonl` |
| 프롬프트·검색 | [design](design.md), [contracts](contracts.md) | 승인 명세, 항목표, RAG 노트북 |
| 고정 모델·프롬프트 실행 특성 | [Gemma 4 조사](gemma4.md) | 고정 리비전 모델 카드·기술 보고서·thinking/채팅 규약, 검증 전 실험 후보 |
| 채점·실험 | [data](data.md), [contracts](contracts.md), [roadmap](roadmap.md) | `open/dev_labels.csv` |
| 패키징·제출 | [rules](rules.md), [design](design.md) | 베이스라인, 제출 직전 공식 평가 탭 |
| Colab 사전 검증·오류 진단 | [Colab 실행 안내](colab.md), [T1 작업서](tasks/t1-baseline.md) | 실제 제출 ZIP·공개 샘플/dev·diagnostics.jsonl |
| 실행 관측·팀 공유 화면 | [Langfuse 실행 관측](langfuse.md) | 로컬 스택(3002), `tools/langfuse_tail.py`, 같은 diagnostics.jsonl |
| 과거 실행 대조·결과 공유 | [실행 기록](runs.md) | `reports/runs/<run-id>/`의 manifest·CSV·로그, `reports/team-score-audit/history.json` |
| 새 결과 ZIP 등록 | [실행 기록의 등록 절차](runs.md#등록-절차) | `artifacts/inbox/`의 결과·제출 ZIP 한 쌍, `tools/register_run.py` |
| 0점 항목이 막힌 단계 찾기 | [항목 진단 전용 회차](colab.md#항목-진단-전용-회차-선택) | `tools/diagnose_items.py`, 노트북 `diagnose` 셀, `reports/team-score-audit/recall-check.csv`의 양성 ID |
| 다음 GPU 회차에 무엇을 돌릴지 | [GPU 회차 대기열](tasks/gpu-run-queue.md) | 회차 제한 없음(2026-09-20~)·제출 1일 1회·여유 2,919초, 노트북 셀 18의 `RUN_DIAGNOSTIC`·`DIAGNOSE_ITEMS` |
| 후보가 정말 나아졌는지 판정 | [workflow W5](workflow.md#w5-실험검증), [회차 간 비결정성](../reports/runs/reproducibility.md) | `tools/compare_runs.py`로 항목별 TP/FP/FN과 대상 밖 회귀·churn 범위 |
| 프롬프트·스키마 후보를 Colab 없이 몇 건만 확인 | [workflow W5](workflow.md#w5-실험검증) | `tools/api_run.py`. 키가 있으면 API의 `gemma-4-26b-a4b-it`, 없으면 mock. 분당 입력 토큰 16,000 상한이라 표본용이고 전량 dev는 Colab 회차 |
| 모델 뒤 단계 후보를 GPU 없이 측정 | [workflow W5](workflow.md#w5-실험검증) | `tools/replay_run.py`와 보관된 원응답 `reports/runs/colab-1789655036303880754/dev-debug/`. `--verify`는 보관 응답 무결성 검사(회차 커밋 코드)이고, 비교 기준은 HEAD 재생 CSV |
| 리뷰 | [workflow](workflow.md), 변경한 계약 문서 | diff, 호출자, 실행 기록 |
| 도구 설치 | [setup](setup.md) | `tools/setup_agents.py` → 공용 `tool/setup_agents.py` → `tool/apply.py`; checkout의 `.wiki/adapter.toml` |
| 종료 전 위키 검진·공개 연결 | [유지보수 기록](tasks/wiki-maintenance.md) | `ai-coding-agent-wiki-public` 고정 SHA, 프로젝트 결정 기록·lint 결과 |

## 작업본과 보관본

- `docs/`: 주제별 작업본. 규칙·설계 변경은 해당 소유 문서 한 곳에서 관리합니다.
- `archive/contest/`: 기존 `대회/` 4개 파일의 보관본. 바이트·파일명을 보존하며 기본 AI 읽기 대상에 넣지 않습니다.
- [sources](sources.md): 원문 절·FAQ의 통합 위치, 선택적 원문 링크, PPTX 슬라이드·해석 차이를 추적합니다.
- `open/`: 실제 공고·정답·법령·베이스라인 입력. 보관 문서와 달리 구현·판정에 필요합니다.
- PPTX는 설계 근거로 유지합니다. `대회/`를 열라는 작업 지시는 사용하지 않습니다.

새 공지가 오면 해당 작업본과 출처 기록을 함께 갱신합니다. 내용 누락을 원문 재독 지시로 대신하지 않습니다.
