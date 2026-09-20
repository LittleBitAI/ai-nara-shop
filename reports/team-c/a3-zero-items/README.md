# A3 H1 — 기업등급 사실의 원천·문장 역할 구분

2026-09-20, glassfish. **프롬프트 후보·로컬 검증 완료, 실제 모델 실행 대기. 미채택.**
작업 계약은 [A3](../../../docs/tasks/a3-zero-items.md). 독립 리뷰·대회 제출은 하지 않았다.

## 기준선과 범위

고정 코드 `6bb692d6162e6b604dae34e6e8044cc31dd7a60b`, 작업서까지 받은 HEAD는
`76e2a3fa1e07409cff40a7086a87750ae0f25401`이다. 두 커밋의 추론 코드는 같다.
`colab-1789880471715651259/dev-debug`의 원응답을 이 코드로 재생하고 재채점했다.

| 항목 | TP / FP / FN | F1 |
| --- | --- | ---: |
| v10 | 0 / 0 / 7 | 0 |
| v11 | 2 / 2 / 4 | 0.400000 |
| v12 | 4 / 1 / 2 | 0.727273 |
| v13 | 4 / 8 / 2 | 0.444444 |
| v14 | 7 / 2 / 1 | 0.823529 |
| v15 | 5 / 2 / 1 | 0.769231 |
| v16 | 2 / 2 / 4 | 0.400000 |
| v17 | 5 / 9 / 1 | 0.500000 |
| v18 | 0 / 2 / 7 | 0 |
| v20 | 0 / 0 / 5 | 0 |

재생 Macro F1 **0.5479850380745521**. [200건 기준 CSV](baseline/submission.csv),
[24항목 채점](baseline-score/metrics.json). 새 모델 점수나 서버 점수가 아니다.
회차 당시 CSV는 후처리가 다른 코드로 생성됐으므로 이번 비교 기준으로 쓰지 않는다.

## 원응답이 가리킨 원인

기업등급 추출은 `build_user_prompt`가 메타·문서·고시 후보를 함께 넣고,
`fit_to_budget → run_chunk(company_size) → verify_company_size`로 흐른다.
`verify_company_size`는 인용의 존재를 검증하므로 메타 인용을 차단할 수 있지만,
잘못 추출된 기업등급 대신 올바른 사실을 새로 만들 수는 없다.

v18 양성 7건 중 **4건이 `meta.조항호내용`을 자격 인용으로 그대로 복사했다.**
공고문에 소기업 말이 없는데 추출됐다는 현상은 이 4건에서 원천 혼동으로 좁혀진다.
전체 dev 200건에서는 같은 현상이 **8건**이다. 나머지 4건을 포함한 ID와 원응답은
[audit.json](audit.json)에 있다. 이것은 후보 효과 측정이 아니라 기존 응답의 감사다.

| v18 양성 | 기존 qualification | 인용의 실제 원천·역할 |
| --- | --- | --- |
| 22, 040, 041 | small_only | meta.조항호내용의 `[판로지원법 시행령] 소기업,소상공인제한` |
| 044 | small_only | meta.조항호내용의 금액·기업 분류 설명 |
| 038 | small_only | 공고문 제출서류 목록 |
| 043 | sme_allowed | 공고문 제출서류 목록 |
| 039 | small_only | 공고문 `입 찰 방 법: 제한경쟁(소기업·소상공인)` |

따라서 작업서의 044 법령 인용은 역할을 구별할 **원문 표본**이고, 이 회차 모델이 실제로
인용한 문자열은 아니다. 두 관측을 섞지 않는다. 043의 출력도 small_only가 아닌 sme_allowed다.

## 한 가설: 자격을 정하기 전에 원천과 역할을 읽는다

`COMPANY_SIZE_PROMPT`의 qualification 문단만 수정했다. 스키마·scope·예외 문단·금액
결정표·A2 정규식·company_size_products·호출 단계·판정 병합은 바꾸지 않았다.
추가 호출은 **0회**다. 기존의 동일 사실 추출을 정확하게 만드는 실험이다.

| 구분 기준 | 추출에서의 취급 | 확인할 원문 표본 |
| --- | --- | --- |
| 문서에서 기업 범주와 입찰 자격을 연결함 | 실제 기업등급 제한. 명시적인 제한경쟁 표제도 포함 | 039: 제한경쟁(소기업·소상공인) |
| 확인서 명칭·부수·제출 순서만 나열함 | 그 목록만으로 기업등급을 결정하지 않음 | 038: `거. 소기업 또는 소상공인확인서 1부`; 043: `12) 중·소기업, 소상공인확인서 중 1부` |
| 법령 제목·조문 또는 참여 배제 대상을 적음 | 이름에 중소기업이 있다는 이유로 허용 등급을 추정하지 않음 | 044: 제8조의2에 해당하는 자는 참여할 수 없다는 문맥 |
| 메타의 법적 분류·조항호내용 | 공고문에 없는 자격·인용을 보충하지 않음 | 기존 원응답의 메타 복사 8건 |
| 직접생산 자격·계약 후 의무 | 기업등급과 별개의 사실로 읽음 | 기존 후속 분석의 직생→중소기업 오독 |

명시적으로 자격을 갖추려면 확인서를 소지해야 한다는 문장은 여전히 제한으로 읽는다.
제출서류라는 제목만 보고 모두 버리는 규칙이 아니다. 상세 자격과 표제가 명시적으로 다르면
상세 자격을 우선하고, 상세 절의 침묵만으로 표제의 제한을 지우지 않는다.
자격 문서가 불완전하면 unknown을 유지한다. 유효한 제한을 못 찾았다는 이유만으로
불완전관측을 unrestricted로 바꾸지 않는다.

이는 제공 판로지원법 시행령 제2조의2의 기업범주·제한경쟁 조건을 읽기 위한 **추출 가설**이다.
서류 목록 자체의 법적 효력을 일괄 부정하는 새 법률 규칙을 추가한 것이 아니다.
제2조의3 예외와 기존 관측성 게이트는 유지한다. 원문 표본 네 건의 doc_id·문자 위치는
감사 파일에서 검증했다. **모델이 네 역할을 구별했다는 증거는 아직 없다.**

039는 v18 정답이 1이지만 원문에 실제 제한이 있다. 그 불일치는 보존하며, 이 한 건을
맞추기 위한 ID 예외·표제 무시를 넣지 않았다. 038·039·040·041은 기존 scope도 competitive라
H1의 자격만 바로잡아도 v18이 열리지 않을 수 있다. 모든 미탐을 이 가설로 설명하지 않는다.

## 검증

```powershell
python -X utf8 reports/team-c/a3-zero-items/check.py
python -X utf8 -m unittest tests.test_company_size tests.test_baseline tests.test_replay_run tests.test_package
python -m ruff check script.py reports/team-c/a3-zero-items/check.py
git diff --check
```

- 기존 계약 **44개 통과**(30.082초, Windows / Python 3.13.9). 파싱·복구·부재 관측성·재생·패키징 검사다.
- AST 대조에서 qualification 문단 외 코드 동일, 프롬프트에 dev ID 없음.
- 후보로 같은 보관 응답을 재생한 CSV는 기준 CSV와 바이트 동일.
  [compare_runs 결과](compare/comparison.json): **변경 0/4,800셀**, 대상 밖 0셀.
  프롬프트 효과나 새 코드 churn의 측정으로 사용하지 않는다.
- 기존 package 도구로 제출 ZIP·Colab 번들 생성. ZIP을 풀어 샘플 **10행·49열** mock,
  모델 없는 기본 진입 실패·인코딩 검사 통과. [번들 해시·검사](package-check.json).
- 무라벨 파일은 이 워크트리에 없어 원본 저장소의 같은 제공 파일을 읽었다.
  기존 `company_size_canary.py`로 순서상 첫 6,000건의 입력 hash·완전관측 5,781건을 확인했다.
  [입력 사전 점검](input-preflight.json)의 `firing_rate_ratio`는 **null**이다.
  입력 분포로 W5 발화율 검사를 대신하지 않는다.

## 실행할 번들

로컬 경로: `artifacts/a3-zero-items/0e432eacf041/`.
그 안의 **colab-baseline.ipynb**를 열고 **colab-bundle.zip**을 업로드한다.
`SOURCE_MODE="upload"`, `RUN_DIAGNOSTIC=True`, `DIAGNOSE_ITEMS=""`로 준비했다.
아직 커밋·push하지 않은 후보이므로 현재 HEAD를 clone하면 이 프롬프트를 받지 못한다.
clone으로 전환할 때는 게시된 **후보의 전체 40자 SHA**를 사용한다.

- script SHA-256: `0e432eacf0416bbf8d478fca5b3c8fe78d0c454dcd5ccb6ee7a6871375831b89`
- submit ZIP SHA-256: `1da28ce977e944ddab264576589ed14f7be7bcd92f53187ed804246bc2206d1a`
- 코드 외 번들 자료는 `76e2a3f`의 Git blob을 임시 폴더에서 읽어 기존 package 도구로 묶었다.
  원본 자료를 편집하지 않았으며 Git의 LF 바이트를 보존했다.

첫 회차는 dev 200건·원응답을 보관한다. 채택 검토 시 **동일 ZIP으로 별도 재실행**한다.
dev/debug 한 쌍으로 반복을 대신하지 않는다. 같은 모델·리비전·설정·입력 hash를 확인한다.

```powershell
python -X utf8 tools/compare_runs.py --items v10,v18,v20 --before reports/team-c/a3-zero-items/baseline/submission.csv --after <새-dev-debug>/submission.csv --output-dir <새-비교-폴더>
python -X utf8 tools/compare_runs.py --items v11,v12,v13,v14,v15,v16,v17,v18 --before reports/team-c/a3-zero-items/baseline/submission.csv --after <새-dev-debug>/submission.csv --output-dir <새-축-비교-폴더>
python -X utf8 tools/compare_runs.py --items v10,v18,v20 --before <첫-회차>/submission.csv --after <별도-재실행>/submission.csv --output-dir <새-churn-폴더>
```

첫 비교로 대상 밖 21항목도 보고하고, 두 번째로 같은 축의 TP/FP 방향을 분리한다.
원응답에서는 메타 복사 8건과 네 역할 표본이 어떻게 바뀌었는지 별도 확인한다.
quote가 null로만 바뀌거나 unknown이 늘었다면 올바른 자격 추출로 회복됐다고 세지 않는다.
과거 churn 17~45셀은 참고 기록이며 새 코드 허용선이 아니다.

무라벨 첫 6,000건은 같은 후보로 별도 live 회차가 필요하다. 기존 canary 도구로 v14~v18의
발화 건수·비율·dev 대비 배율을 낸다. dev 분모 0은 배율 null로 표시한다.
전체 CSV의 v10·v20과 추출 원천·역할의 변화도 함께 집계해야 하며 기존 canary 도구의
BAND_ITEMS 집계만으로 A3 전체 W5 통과를 선언하지 않는다.

## 남은 작업

H1은 v13~v18이 공유하는 사실 추출 실험이다. v10 배선은 주 세션이 맡고,
v20은 실제 구매 대상이 소프트웨어 사업인지와 문서의 참가 제한을 구분하는 **별도 가설**이다.
이미 확인한 v20 문자열·금액 통계는 다시 조사하지 않았다. H1에 별도 호출이나 v20 전용
판정을 섞지 않았다. v10·v18·v20 각각 TP>0이라는 A3 전체 완료 조건은 모두 남아 있다.

GPU 실행·후보 TP/FP/FN·동일 ZIP 반복 churn·무라벨 발화율·실제 토큰 증가·시간은 미측정이다.
호출 수는 그대로여도 긴 프롬프트가 문서 축소와 추론 시간에 미치는 영향은 측정해야 한다.
회차의 건당 시간 환산과 서버 실측을 구분한다. **A3 완료 또는 점수 개선으로 보고하지 않는다.**
