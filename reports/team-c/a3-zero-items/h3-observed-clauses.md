# A3 H3 — 법적 필요 여부와 본문 조항 관측을 분리한다

후속 실측: [회차 4](run4-facts.md)는 v10 4/7/3·v18 0/2/7·v20 1/4/4,
dev 0.5743735227782543이다. 세 항목 동시 TP>0 미달로 미채택이며,
다음 후보는 [H4](h4-qualification-role.md)다. 아래 미실행 표기는 H3 준비 당시 이력이다.

2026-09-20. 시작점 `c370aa2`. H3 실제 모델 미실행·성능 미채택이다.
[회차 3 사실](run3-facts.md)을 반영했다. H2는 v10 0/1/7, v18 1/2/6, v20 0/0/5로
v18 첫 TP를 얻었으나 세 항목 동시 TP>0 조건에는 실패했다.

회차 3의 기본 dev Macro는 `score/metrics.json`의 0.536027305106이다.
사실 문서의 0.544041527881은 dev-debug CSV와 기준 재생을 비교한 수치다.
두 실행을 섞지 않는다. 같은 ZIP 별도 회차 churn은 H3에서 다시 측정해야 한다.

## 원인 가설과 변경

H2는 문서 요건을 추출하는 상태값에 법적 필요 여부를 함께 물었다. competitive인데
not_required인 15건, software_business=yes인데 unknown인 9건이 나왔다.
이 관측이 두 판단의 혼동이라는 가설을 시험한다. 상태값을 부재로 강제 변환하지 않는다.

- 새 출력에서 상태 필드 두 개를 제거한다. direct_production_quote와
  software_participation_quote는 보이는 본문에서 찾은 조항 원문 또는 null이다.
  해당 법이 적용되는지와 독립적으로 조항을 찾는다. 서류 목록·법령명만으로 요건을 만들지 않는다.
- 기존 적용 대상·원문 인용·완전관측 조건을 통과한 경우에만 명시적인 null을 부재로 소비한다.
  키 결손·빈 문자열·실패·잘못된 인용·미관측 문서는 기존 판정을 보존한다.
- SW 적용 대상 인용은 120자 이내의 연속 원문 한 구간이다. 제목이나 짧은 한 구절을
  그대로 복사하고, 품목표의 여러 행을 문장으로 재조립하지 않는다.
- H1/H2/H3 스키마를 실행 설정으로 구분한다. 옛 unknown/not_required를 부재로 재해석하지 않는다.
  H2의 긴 인용도 과거 스키마의 500자 규격으로 재생한다.
- company_size 한 호출을 유지하고 사실 필드는 16개에서 14개로 줄인다. 입력의 조항호내용 제외,
  qualification 문단, scope 분류, A1 결정표와 A2 판정 함수는 그대로다.

이는 '조항 관측으로 답하게 한다'는 한 실험이다. 상태 제거와 짧은 인용의 효과를 각각
분리해 측정한 실험은 아니다. 120자는 법적 경계가 아니라 출력 길이 제한이다.
v18 첫 TP의 다음 회차 유지, v17·v13 손실 회복을 코드 보존만으로 보장하지 않는다.

## 검증과 한계

수정 전, 상태 필드 없이 인용/null만 있는 합성 응답은 v10·v20을 출력하지 못했다.
수정 후 정상 입력의 실행·CSV·재생 일치, 필드 결손 실패, 과거 상태 보류,
SW 새/과거 인용 길이 규격 구분 검사를 통과했다. 실제 모델 TP 검사가 아니다.

공유 파이프라인 10개 테스트 모듈의 150개 검사를 실행했다(35.221초).
149개 통과, 새 script 해시가 반영되지 않은 기록 검사 1개가 실패했다.
요구된 해시 기록을 갱신한 뒤 해당 검사만 다시 실행해 통과했다(0.048초).
Ruff·diff 검사도 통과했다. 위키 설치 등 추론 코드와 무관한 환경 검사는 실행하지 않았다.
압축 해제 mock 10건·49열, 모델 없는 기본 진입 실패도 확인했다([패키지 검사](h3-package-check.json)).

```powershell
python -X utf8 reports/team-c/a3-zero-items/h2-check.py --base c370aa2 --case colab-1789894949866134428
python -X utf8 -m unittest tests.test_baseline tests.test_company_size tests.test_competitive_product tests.test_sme_candidate tests.test_qualification_candidate tests.test_api_run tests.test_replay_run tests.test_package tests.test_diagnose_items tests.test_analyze_diagnose
```

공통 감사 도구의 H3 [검사 기록](h3-check.json): 보호 대상 함수 AST 불변,
H2 dev-debug 200건 재생 CSV 바이트 동일·변경 0셀. 따라서 H2의 실패를 CPU 재생으로
성공처럼 바꾸지 않았다. H3의 새 원응답은 없으므로 실제 TP/FP·시간·무라벨 발화율은 미측정이다.
새 null 관측이 늘면서 FP도 늘 수 있다. 적용 대상 오분류와 문서 누락은 이 변경으로 해결되지 않는다.
서버 제출·독립 리뷰는 수행하지 않았다.

## 다음 회차

[전용 노트북](../../../notebooks/exp-a3-source-role.ipynb)을 H3 커밋으로 고정한다.
추론 커밋: `ec3dee43a85200a585410b145cbbb0097158e5eb`.
script SHA-256: `da635b0c1ae9387032d63cad764e0a760c686227c3f4cd1df60381240ef70b61`.
새 A100급 런타임에서 HF_TOKEN 접근을 허용하고 첫 셀부터 실행한다. 설정값 수정은 필요 없다.
v10·v18·v20 각각 TP>0이 첫 관문이다. 하나라도 TP=0이면 통과로 보고하지 않는다.
TP 관문에 미달해도 원응답·결과 ZIP까지 보존한다.

새 원응답에는 direct_production/software_participation 상태 필드가 없다. 다음 분석은
각 quote의 null/실제 본문 일치 여부를 적용 대상·requirements_complete와 교차 집계한다.
실제 최종 TP/FP/FN, 038·043·044/039의 문장 역할, 대상 밖 21항목 변화도 함께 확인한다.
채택 후보는 같은 ZIP 별도 회차의 churn·무라벨 6,000건 발화율·시간까지 기존 조건 전부를 충족해야 한다.
