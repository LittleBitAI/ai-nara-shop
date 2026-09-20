# A3 H4 — 기업등급보다 문장의 역할을 먼저 출력한다

2026-09-20, 시작점 `49475c3`. **새 실제 모델 미측정·성능 미채택.**
[회차 4 사실](run4-facts.md)은 v10 4/7/3·v18 0/2/7·v20 1/4/4다.
H3의 dev 0.5743735227782543은 최고 측정값이지만 세 항목 동시 TP>0에는 미달했다.
dev-debug 0.573802514249와 원래 기준 재생의 차이는 +0.025817476175·52셀이다.
이는 과거 churn 범위를 넘는다. H3/H4 각각의 같은 ZIP 별도 반복까지 증명하지는 않는다.

## 가설과 경계

H1의 산문 역할 지시는 H3에서도 충분하지 않았다. `038`은 제출서류의 확인서를
잘못 바꾼 문장으로 인용했고 `043`은 확인서 목록을 sme_allowed로 읽었다.
두 공고의 참가자격 절에는 그 기업등급 조건이 없다. `039`의 제한경쟁 제목에는 실제
소기업·소상공인 제한이 있다. `044`의 법령상 배제와 업종 등록은 기업등급 조건이 아니다.
이는 [A3 작업서](../../../docs/tasks/a3-zero-items.md)의 문장 역할 구분을 다시 시험하는 근거다.
공고 ID·학교/여행 등 업무명은 추론 규칙에 넣지 않는다.

제공 판로지원법 시행령 제2조의2는 기업등급 간 제한경쟁 방법을 정한다. H4는 그 등급과
예외 결정표를 바꾸지 않고, 공고가 해당 참가자격을 실제로 명시했는지의 추출을 바꾼다.
확인서 목록과 참가자격을 구분하는 것은 이 작업의 추출 계약이며 새로운 법적 예외가 아니다.

company_size 한 호출에 `qualification_role` 하나를 추가한다(14→15 필드).
스키마 순서는 scope·scope_quote 다음에 역할·자격 인용·관측 완전성·기업등급이다.
역할을 먼저 출력하면 목록의 명사에서 바로 기업등급을 정하는 오류가 줄어드는지 본다.

| 역할 | 기준 | 기업등급 소비 |
| --- | --- | --- |
| eligibility | 기업등급을 입찰 가능 여부에 연결하는 실제 조항·제한경쟁 제목 | small_only 또는 sme_allowed |
| checklist | 기업등급이 제출서류에만 나오고 실제 제한은 없음 | 완전한 자격 관측·원문 인용을 갖춘 unrestricted만 허용 |
| legal_reference | 법령명·배제 조항에만 나오고 실제 제한은 없음 | 위와 같음 |
| none | 관측한 자격에 기업등급 언급 없음 | 위와 같음 |
| unknown | 미관측·충돌·판단 불가 | 보류 |

실제 제한은 다른 곳의 체크리스트보다 우선한다. 확인서 보유를 명시적 입찰 자격으로
연결한 조항은 eligibility다. 목록의 모든 서류를 내라는 지시만으로 기업등급 조건을 만들지 않는다.
역할과 기업등급이 모순이면 qualification을 unknown으로 보류한다. 체크리스트를 발견했다는
이유로 unrestricted를 만들지 않으며, 원응답 역할·등급은 진단 로그에 그대로 남는다.
보류는 자격 사실에만 적용하여 독립적인 직접생산·SW 관측을 버리지 않는다.

v10/v20 소비자, scope 지시, 문서 예산, 완전관측 조건, A1 금액 결정표·A2는 유지한다.
카탈로그 True 강제는 회차 4 TP 4건도 전부 지우므로 쓰지 않는다. `041`을 일반제품으로
강제하거나 `22`의 문서 절단을 허용하지 않는다. SW 인용 200건 전부 null 문제도 해결됐다고
주장하지 않는다. 호출은 늘지 않지만 프롬프트·출력 증가의 실제 시간은 다음 회차에서 잰다.

## 검증

수정 전 새 역할 필드가 파싱에서 사라지는 실패를 재현했다. 수정 후 역할 모순 보류,
필수 필드 결손, 기존 v10/v20 경로 보존, 합성 실행→CSV→재생 검사를 통과했다.
이는 모델의 문장 역할 이해나 TP 성과를 검증한 것이 아니다.

[CPU 감사](h4-check.json)는 원래 scope·H1 회차 2·H2 회차 3·H3 회차 4의 원응답 각각
200건에서 수정 전/후 CSV 바이트가 같음을 확인한다. 보호 함수 AST도 같다.
재생은 실행 설정의 `company_size_qualification_role`로 구분한다. 옛 응답에는 역할을 추측해
붙이지 않고, 새 응답에서 역할이 빠지면 정상 응답으로 받지 않는다.

공유 파이프라인 10개 모듈 **151개 검사 통과**(37.833초), Ruff·diff 검사 통과.
[패키지 검사](h4-package-check.json)는 압축 해제 mock 10건·49열과 모델 없는 기본 진입 실패를 확인했다.
로컬 submit.zip은 `artifacts/a3-zero-items/1691e8cc2e3a/submit.zip`이다.
script SHA-256은 `1691e8cc2e3a94c7af8a7dec703e58616dcc05337e633283630318ee69ac2a5b`다.
원문 실행 로그는 Git 제외 `artifacts/a3-h4-pipeline-tests.log`에 보관한다.
독립 리뷰·실제 GPU 실행·대회 제출은 수행하지 않았다.

```powershell
python -X utf8 reports/team-c/a3-zero-items/h2-check.py --base 49475c3 --case colab-1789880471715651259 --case colab-1789889904147841755 --case colab-1789894949866134428 --case colab-1789898958261656296
python -X utf8 -m unittest tests.test_baseline tests.test_company_size tests.test_competitive_product tests.test_sme_candidate tests.test_qualification_candidate tests.test_api_run tests.test_replay_run tests.test_package tests.test_diagnose_items tests.test_analyze_diagnose
```

## 다음 회차

[전용 노트북](../../../notebooks/exp-a3-source-role.ipynb)의 H4 전체 SHA를 고정해 게시한다.
새 A100급 런타임과 HF_TOKEN 접근만 준비하고 처음부터 실행한다. 기존 종료된 런타임은 필요 없다.
SOURCE_MODE/REPO_REF/RUN_DIAGNOSTIC/DIAGNOSE_ITEMS는 게시된 값 그대로 사용한다.

같은 회차의 **v10·v18·v20 각각 TP>0**을 먼저 확인한다. 미달이어도 원응답·결과 ZIP을 보존한다.
역할별 건수·인용·기업등급의 일관성과 038·043·044/039의 구분을 확인하고, 전체 TP/FP/FN·
대상 밖 21항목(특히 v17) 변화를 compare_runs로 낸다. v10/v20 코드 보존은 TP 유지의 보장이 아니다.
같은 ZIP 별도 반복, 무라벨 6,000건 발화율·배율, 시간까지 기존 채택 조건은 모두 남는다.
