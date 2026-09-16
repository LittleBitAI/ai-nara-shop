# 공정과 산출물 계약

상태: 팀 설계. 원본: 발표용 9~13장. 오너와 파일 경계는 [design.md](design.md).
외부 API 사용 범위는 [rules.md](rules.md)의 R6·Q1을 먼저 적용합니다.

## C1. 공통 생명주기

`draft → reviewed → approved` 순서로 진행합니다. 반려는 `rejected`로 기록합니다.
승인 산출물의 내용·입력·생성 프롬프트가 바뀌면 새 버전의 `draft`로 돌아갑니다.
하위 산출물은 상위 버전/hash를 기록해 변경된 명세의 옛 프롬프트를 잘못 쓰지 않게 합니다.

| 필수 메타 | 의미 |
| --- | --- |
| `artifact_id`, `version`, `status` | 산출물 식별자·버전·승인 상태 |
| `sources` | 제공 자료의 상대 경로, SHA-256, 조문/문서/공고 ID 등 위치 |
| `generator` | 코드 commit 또는 파일 hash, 실행 명령·설정·시드 |
| `model`, `prompt_hash` | 모델 사용 시 이름·버전과 보존된 프롬프트 파일 hash; 미사용은 null |
| `parents` | 사용한 상위 산출물의 ID·버전/hash |
| `reviewer`, `reviewed_at`, `decision` | 사람 검토자·시각·승인/반려 근거 |

Markdown은 YAML front matter, JSON/JSONL은 필드 또는 옆 manifest로 기록합니다.
모든 레코드에 긴 공통 메타를 복제하지 않고 실행 단위 manifest를 재사용합니다.
승인 전 `reviewer`와 시각은 null입니다. AI가 실명·승인 일시를 지어내지 않습니다.

## C2. 여덟 공정

| 공정 | 입력 | 출력 | 통과 조건 |
| --- | --- | --- | --- |
| 1 명세 | 항목 정의·해당 조문 | `specs/vNN.md` | 아래 7칸 완비, 조건·예외가 제공 조문에 연결됨, 사람 검토 |
| 2 매핑 검토 | 항목→조문 표·법령 | `rules/law_map.json` | 정방향·역방향 불일치 검토, 국가/지방·해당 없음 구분 |
| 3 자가 라벨 | 제공 공고·검토 기준 | `labels/<run-id>.jsonl` + manifest | dev 기준선·항목별 검토 강도·예산 확정 후 대량 실행 |
| 4 사례 발굴 | 라벨·불일치·조건 경계 | `cases/<run-id>.jsonl` | 실제 원문 위치, 선정 이유, 사람 검토 여부 명시 |
| 5 지시문 생성 | 승인 명세 | `prompts/vNN.md` | 명세 버전 일치, 원문 근거 지시, dev 비교·토큰 검사 |
| 6 검색 질의 | 승인 매핑·항목·계약법 | `prompts/queries.json` | 관계있는 조문 포함률 비교, 중복·토큰 예산 검사 |
| 7 오답 분류 | 예측·정답·실행 추적 | `reports/<run-id>/errors.csv` | 원문·프롬프트·조문으로 원인을 설명, 담당자 연결 |
| 8 기록 정리 | 실험·생성·승인 기록 | `reports/<run-id>/manifest.json`, `result.md` | 입력부터 출력까지 파일·명령·버전 추적 가능 |

1·2·4~8의 외부 API 자동화는 Q1 확인 후 결정합니다.
확인 전에는 수동 검토, 템플릿 기반 변환, 결정적 채점·기록 집계로 동일한 파일 계약을 충족합니다.
설명문 자동 작성 여부와 점수 계산의 정확성을 분리합니다. 점수는 코드가 계산합니다.

## C3. 7칸 명세 양식

`specs/vNN.md`에 항목마다 아래 내용을 씁니다. 예시 24개를 빈 파일로 미리 만들지 않습니다.

```markdown
---
artifact_id: spec-vNN
version: 1
status: draft
sources: []
parents: []
generator: null
model: null
prompt_hash: null
reviewer: null
reviewed_at: null
decision: null
---
# vNN: 항목표의 정확한 항목명

## 적용 대상
계약법·업무·금액 구간·대상 품목. 경계의 이상/초과/미만/이하를 구분한다.
## 필요한 사실
확인할 docs/meta 필드와 위치. null·미입력·문서 누락을 구분한다.
## 위반 조건
판단 순서, AND/OR 조건, 제공 조문의 파일·조·항·호·정확한 인용.
## 예외
다만·각 호·별표의 적용 범위, 근거 위치. 찾지 못한 경우 미확인으로 표시한다.
## 정보 부족 시
판정 불가와 비위반을 내부적으로 구분하고 최종 0 처리 조건을 명시한다.
## 근거 위치
공고에서 인용할 doc_id와 위치. 부재탐지 항목은 e 빈칸.
## 사례
제공 공고 ID·doc_id·정확한 원문 span, 예상 판정, 경계·예외 이유.
```

금액·조문을 모델 기억으로 채우지 않습니다. v24는 법령 위반이 아닌 문서/meta 불일치 계약입니다.
“항목표와 다른 매핑”을 발견하면 항목표를 덮어쓰지 않고 불일치·검토 결과를 기록합니다.

## C4. 라벨·사례

라벨 행은 `id`, `judgments`(D4의 24항목 객체), `review_status`, `issues`, `run_id`를 가집니다.
manifest에는 모델·생성 프롬프트·입력 파일 hash·호출 조건·실패 수·재시도·비용을 보존합니다.
중단 후 재시작은 동일 입력 ID와 생성 버전으로 중복 생성을 피합니다. 실패 행을 정상 라벨로 채우지 않습니다.

사례 행은 `id`, `item_id`, `doc_id`, `start`, `end`, `quote`, `label`, `reason`,
`label_run_id`, `review_status`를 가집니다. 위치는 NFC 원문에서 Python 문자 인덱스, end는 제외입니다.
항상 `doc.text[start:end] == quote`를 확인합니다.
부재 사례는 인용 span을 null로 두고 확인한 문서 범위·관측성을 기록합니다.
수치 confidence가 필요하면 정의·산출 방법을 적습니다. 모델의 자기 확신을 실제 정확도로 간주하지 않습니다.

dev 라벨링 기준선에서는 모델 입력에 `dev_labels.csv`를 넣지 않습니다.
dev 입력에 대한 생성 결과를 생성 후에 정답과 비교합니다. 무라벨 20,000건과 dev가 겹친다고 가정하지 않습니다.
자가 라벨 사례를 검증에도 쓴다면 공고 ID 단위로 분리하고, 공식 dev 점수와 별도로 보고합니다.

## C5. 실험 기록

| 파일 | 필수 내용 |
| --- | --- |
| `manifest.json` | run ID, baseline run, 코드·입력·자산 hash, 모델/revision, 환경, 시드, 실행 명령·설정, mock/live 구분 |
| `metrics.json` | Macro F1, 24항목 F1·precision·recall·TP/FP/FN·support, ID 일치 검사 결과 |
| `errors.csv` | id, item, true, pred, 원인 코드, 근거 위치, 담당 역할 |
| `result.md` | 가설 하나, 변경 전후, 로드·추론·전체 시간, 토큰·메모리, 근거 폐기·JSON 결손, 채택/반려 이유 |

오답 원인 코드는 발표의 9유형을 고정 사용합니다.

| 코드 | 의미 | 담당 |
| --- | --- | --- |
| `spec` | 조건·예외 명세 오류 | 명세 |
| `truncation` | 중요한 문서 절단 | 프롬프트 |
| `retrieval` | 조문 주입 실패 | 프롬프트·명세 |
| `extraction` | 사실·문구 추출 오류 | 프롬프트 |
| `meta` | null·등록값 해석 오류 | 명세·프롬프트 |
| `judgment` | 입력 근거가 있어도 판단 흔들림 | 프롬프트 |
| `evidence` | 근거 원문 대조 실패 | 통합 |
| `json` | 구조화 출력 결손 | 통합 |
| `format` | CSV·ID·인코딩 형식 오류 | 통합 |

원인을 모르면 빈 값과 `미분류` 메모를 남깁니다. 9유형 중 아무 값이나 채우지 않습니다.
dev F1 개선만으로 최종 후보를 확정하지 않습니다. 일반화 근거·실행 제한·근거 품질·재현성을 함께 확인합니다.
