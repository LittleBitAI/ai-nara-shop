# 근거와 해석 기록

작성일: 2026-09-16. 법령 판정 자료는 사용자가 제공한 파일만 사용했습니다.
초기 문서 통합 뒤 T1에서 공식 대회 운영·고정 모델·런타임 문서와 논문을 웹으로 확인했습니다.
모델 조사 문서는 개발 참고이며 법령 판정 데이터·검색 인덱스·제출 ZIP에 결합하지 않습니다.

## 통합 범위와 원본 지도

`docs/contest.md`·`rules.md`·`data.md`·`items.md`에 대회 자료를 주제별로 통합했습니다.
아래 보관본은 출처 감사·변경 대조용이며, 작업 문서 사용에 필요하지 않습니다.
기존 `대회/`는 `archive/contest/`로 이동했고 원문 바이트를 보존했습니다. 해시는 [보관 색인](../archive/README.md)에 기록합니다.

| 원본·출처 ID | 사용한 내용 | 작업 문서 |
| --- | --- | --- |
| S1 [규칙 보관본](../archive/contest/rules.md) | 고정 모델, 허용 자료·자가 라벨링, 독립 예측, 재현·제출 의무 | [rules](rules.md) |
| S2 [데이터 명세 보관본](../archive/contest/데이터%20명세.md) | 파일·레코드·meta·CSV·FAQ | [data](data.md), [rules](rules.md), [items](items.md), [contest](contest.md) |
| S3 [datasets 보관본](../archive/contest/datasets.md) | 빈 파일(0바이트); 통합할 본문 없음 | 없음; 빈 상태도 보존 |
| S4 [배경 보관본](../archive/contest/배경.md) | 문제 배경·평가 방식·참가·운영 안내 | [contest](contest.md) |
| S5 [배포 README](../open/README.md) | 제공 파일·입출력·실행환경 | [data](data.md), [rules](rules.md) |
| S6 [지역제한 금액 공지 보관본](../archive/contest/notice-region-limit.md) | 법령패키지를 보완하는 대회 제공 자료. 지방 지역제한 금액(시·도 3억 5천만원 등)과 항목별 `고시금액`의 뜻 | [rules](rules.md#지역제한-금액과-고시금액), [items](items.md) v2·v5~v7·v14~v16 |
| [발표용.pptx](../발표용.pptx) 7~13장·발표자 노트 | AI 초안→사람 검토, 8공정, 품질 게이트, 승인 책임 | [contracts](contracts.md) |
| 발표용 14~15장 | 공정 오너십·파일 경계·작은 브랜치 | [workflow](workflow.md), [design](design.md) |
| 발표용 16~18·21장 | 일정·첫 산출물·예산·미정 질문 | [roadmap](roadmap.md), [tasks](tasks.md) |
| [로드맵.pptx](../로드맵.pptx) 3~11장 | 베이스라인 흐름·데이터·토큰·프롬프트·제약 디코딩 | [data](data.md), [design](design.md) |
| 로드맵 12~19장 | 조문 직접 매핑→BM25 개선→임베딩, 실험·과적합, 요청서 4칸 | [design](design.md), [tasks](tasks.md) |
| [open/baseline/script.py](../open/baseline/script.py) | 실제 loader·prompt·vLLM·mock·후처리·CSV 구현 | 현재 실행 명령과 실패 경계 |
| 루트 `[Baseline]_Gemma + 법령 RAG 법령위반 판정.ipynb` | 조문 단위 BM25, topk=8, RAG_CHARS=8000, QUERY_CHARS=3000 | 검색 개선 기준선 |
| 루트 `[Baseline]_Gemma 제약 디코딩 법령위반 판정.ipynb` | 16,384 context, 1,536 출력, 제약 디코딩 | 예산 기준선 |

두 PPTX의 슬라이드 XML과 발표 노트를 읽었습니다. 슬라이드 외형을 변경하지 않았습니다.
초기 통합에서는 최신 공지를 확인하지 않았으며, 아래 T1 확인 기록으로 운영 정보를 보완했습니다.

## T1 추가 확인: 2026-09-16

- [공식 규칙](https://dacon.io/competitions/official/236754/overview/rules): 고정 모델·리비전,
  공고별 정상 모델 호출·독립 예측·허용 자료와 가중치 변경 제한을 대조했습니다.
- [공식 평가](https://www.dacon.io/competitions/official/236754/overview/evaluation):
  ZIP 루트·PPS 경로·49열 CSV·설치/실행 제한·서버 패키지·오류 시 일일 횟수 차감을 확인했습니다.
- [공식 일정](https://dacon.io/competitions/official/236754/overview/schedule): 팀 병합 9/23 23:59,
  리더보드 제출 9/29 10:00, 종료 9/30 10:00을 구분했습니다.
- 두 베이스라인 노트북의 전체 셀과 `open/baseline/script.py`를 읽었습니다.
  노트북 자체를 실행하지 않았고 제공 원본은 변경하지 않았습니다.
- Gemma 개발팀 기술 보고서·고정 리비전 모델 카드/템플릿/생성 설정과 XGrammar·Lost in the Middle
  논문을 읽고 [모델 조사](gemma4.md)에 출처·사실·적용 판단·미검증 가설을 구분했습니다.
  arXiv 기술 보고서를 동료심사 논문으로 표시하지 않습니다.
- 실제 결과와 한계는 [T1 실행 기록](../reports/t1-baseline/result.md)에 있습니다.

## 원문 절별 통합 대응

중복 규정은 아래 소유 문서로 합쳤습니다. 원문의 안내문·FAQ를 별도 규칙 사본으로 유지하지 않습니다.
표는 2026-09-16 제공 파일 전체 절과 FAQ 16개를 대조한 기록이며 새 공식 공지까지 포괄한다는 뜻은 아닙니다.

| 출처·원문 구간 | 내용이 있는 작업 문서·ID |
| --- | --- |
| S1 핵심 규칙 | [rules](rules.md) R1~R4·R14·R20, A4~A6·A9 |
| S1 외부 데이터: 허용 목록 6개 | [rules](rules.md) A1~A4·A7·A8, R5·R6·R12·R13 |
| S1 외부 데이터: 금지·법령 기준 목록 8개 | [rules](rules.md) R6·R7·R10~R13, 개인 법령 공부 안내 |
| S1 재현 가능성·출처 의무 | [rules](rules.md) R15·2차 평가 준비, [contracts](contracts.md) 생성 이력 |
| S1 비공개 평가 데이터 추가 학습 금지 | [rules](rules.md) R9 |
| S1 공고 단위 독립 예측 | [rules](rules.md) A5·R8 |
| S1 2차 평가 자료 제출 | [rules](rules.md) 2차 평가 준비: 메일·기한·별도 양식·코드·출처·팀원 정보 |
| S1 유의 사항 5개 | [rules](rules.md) R14·R16~R18, [contest](contest.md) E2·E3 |
| S2 배포 구조·파일별 명세(§1·§2) | [data](data.md) D1, 스키마·법령 변환 한계; 베이스라인 흐름 D6 |
| S2 §3 레코드 | [data](data.md) D2: 공통 레코드·문서 5종·관측성·누락·첨부 |
| S2 §4 meta·익명화 | [data](data.md) D3: 21필드·결측·토큰·유지 정보 |
| S2 §5 24개 검토 항목 | [items](items.md) v1~v24 이름·부재탐지·조문·비고 |
| S2 §6 제출 형식 | [data](data.md) D4·D5, [contest](contest.md) E2 |
| S2 §7 자가 라벨링 | [rules](rules.md) A1~A3·A6·A8, R6·R13·R15 |
| S2 §8 시작 가이드 | [contest](contest.md) E3의 시작 순서, [README](../README.md) 실행 명령, [tasks](tasks.md) 작업 큐 |
| S2 §9 FAQ 1 라벨 없음 / 2 dev 학습 | [contest](contest.md) E1, [rules](rules.md) A1·A2 |
| S2 §9 FAQ 3 외부 데이터 / 4 외부 법령 | [rules](rules.md) R10~R12·개인 공부 안내 |
| S2 §9 FAQ 5 파인튜닝 / 6 모델 제출 | [rules](rules.md) R1~R3·R14·R21, [data](data.md) D6 |
| S2 §9 FAQ 7 정규식 후처리 / 8 GPU 없음 | [rules](rules.md) A4·A9·R4·R20, [data](data.md) D6 |
| S2 §9 FAQ 9 근거 점수 / 10 제출 제한 | [contest](contest.md) E2·E3, [rules](rules.md) R16·R19·R21·R22 |
| S2 §9 FAQ 11 Public/Private / 12 점수 대기 | [contest](contest.md) E2·E3 |
| S2 §9 FAQ 13 서버 실수 / 14 제출 오류 | [data](data.md) D4·D6 |
| S2 §9 FAQ 15 모델 병용 / 16 로컬·서버 차이 | [data](data.md) D6, [rules](rules.md) A6·A9 |
| S3 전체 | 빈 파일이므로 이관할 내용 없음 |
| S4 배경·주제·설명 | [contest](contest.md) E1; 상세 계약은 data·items·rules로 연결 |
| S4 대회 방식 | [contest](contest.md) E2: 상위 15팀·정량 80%/정성 20%·수상 7팀 |
| S4 코드 제출 대회 | [contest](contest.md) E3: ZIP·자동 실행·대기 |
| S4 참가 자격·주최/운영 | [contest](contest.md) E4 |

## 옮겨오면서 해결한 차이

| 차이 | 적용한 기준 |
| --- | --- |
| PPTX의 “공고당 단 한 번” vs 규칙의 “1회 이상” | 규칙은 최소 1회 정상 호출. 초기 설계는 효율을 위해 1회 |
| 발표 8장의 광범위한 준비 API 허용 vs 규칙 R6·발표 21장의 미정 질문 | 라벨 생성만 명시 허용. 기타 용도는 Q1로 분리 |
| 기존 Q2가 자가 라벨 사례집 전체를 미확정으로 읽히게 함 | 규칙의 허용 목록·데이터 명세 §7에 사례집 활용이 명시됨. A2·A6으로 활용하고 Q2는 불명확한 특수 캐시 방식에만 적용 |
| 금지와 검사에 치우친 규칙 요약 | rules.md에 작업 단계·영향 분류, 허용 활용 A1~A10·조건·출처, 작업서 적용 절차 추가. R1~R19는 유지하고 R20~R22 보완 |
| “dev 정답과 겹치는 부분” 표현 | dev 입력을 독립 라벨링한 뒤 정답 대조. train과 dev 중복을 가정하지 않음 |
| 배포 설명의 train/dev `.gz` vs 실제 파일 | 로컬은 `.jsonl`, 샘플 test는 `.jsonl.gz` |
| 발표의 “베이스라인 BM25” vs 배포 Python 코드 | BM25는 RAG 노트북에 있음. `open/baseline/script.py` 자체에는 검색 없음 |
| “형식은 이미 안전” vs 실제 실패 처리 | CSV 검사는 존재하나 live 호출 실패의 빈 응답·0 대체는 정상 호출 증거가 아님. 별도 게이트 필요 |
| “예산 내 축소” vs `fit_to_budget()` 종료 조건 | 2,000자 이하에서 예산 초과여도 반환 가능한 기존 동작. 팀 구현은 초과 검출 필요 |
| 약 4초/건 | 7,200/1,853≈3.89초의 단순 나눗셈. 로드·입출력·배치를 포함한 성능 보장 아님 |
| “약한 항목 하나의 평균 기여가 가장 큼” | 항목별 동일 F1 증가량은 평균에 동일하게 기여. 약한 항목은 개선 여지·비용을 보고 우선화 |
| “충돌은 같은 줄을 고칠 때만” | 파일이 달라도 계약 충돌 가능. 모듈 계약과 통합 검증을 둠 |
| 한글 1글자≈1토큰·temperature 0이면 동일 | 교육용 근사. 실제 토크나이저로 측정하고 환경·시드·버전 기록 |

## 참고 저장소의 작업 방식 적용

`../ai-coding-wiki/CLAUDE.md`의 구현 절차와 `AGENTS.md`의 세션 역할을 읽었습니다.
측정 우선, 호출자 추적, 의미 있는 TDD, 테스트 가지치기, 작은 diff, 독립 리뷰,
실행 증거·결과 기록을 적용했습니다. 저장 위치는 도구 중립적인 `docs/workflow.md`로 바꿨습니다.

| 참고 저장소의 특성 | 이 프로젝트의 적용 |
| --- | --- |
| Claude 이름의 파일이 공통 구현 계약을 소유 | 공통 문서가 소유, 두 진입점은 안내만 |
| 일부 작업을 특정 Claude 모델/세션이 수행 | 팀원·세션 역할 기준. Claude/Codex 구현·리뷰 동등 |
| 단독 개발·학습 플랫폼·Docker/PostgreSQL/Elo | 가져오지 않음. 5개 공정 오너와 오프라인 대회 파이프라인 |
| 저장소 문서는 영어 | 한국어 팀 자료와 검토자가 바로 사용할 수 있게 작업 문서는 한국어, 식별자는 영어 |
| 구현 승인 후 PR | 이미 허가된 가역 작업은 진행. 비용·외부 제출·병합은 기존 권한 범위 확인 |

## 도구 설정 근거

- [Codex hooks 공식 문서](https://learn.chatgpt.com/docs/hooks): 프로젝트 hook 위치와 정의별 신뢰 절차.
- [Codex 설정 공식 문서](https://learn.chatgpt.com/docs/config-file/config-reference): 프로젝트 설정과 `features.hooks`.
- 로컬 `codex-cli 0.154.0`, `codex features list`: `hooks`는 stable,
  `default_mode_request_user_input`은 under development. 후자는 공식 설정 표에서 찾지 못했으므로 로컬 지원 확인으로 한정합니다.
- `../ai-coding-agent-wiki/README.md`, `tool/apply.py`, `tool/test_codex_hooks.py`: 도구별 설치·검증.
- 같은 위키 `operator/ask-with-arrow-key-options.md`: Claude `AskUserQuestion`, Codex `request_user_input`, async 질문 차단.

이번 설정은 선택형 질문 기능을 켜는 것까지입니다. 이미 열린 세션의 도구 목록이나 호스트 UI가
즉시 바뀐다고 보장하지 않습니다. 신뢰·재시작·실제 이벤트 확인은 [setup.md](setup.md)를 따릅니다.
