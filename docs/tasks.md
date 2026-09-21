# AI 작업서

역할·AI 종류와 관계없이 같은 양식을 사용합니다. 모델은 맡은 작업의 허용 경로만 수정합니다.
하위 작업을 만들 때 아래 4칸을 빠뜨리지 않습니다. 한 파일을 두 오너가 동시에 수정하지 않습니다.

## 복사할 요청서

```text
작업 ID / 제목:
담당 역할 / 담당자:
상태: ready | in_progress | review | done | blocked
목표와 가설:
읽을 문서 / 보호할 규칙 ID:
규칙 판단: 작업 단계 / 활용할 A-ID / 지킬 R-ID·조건 / 불명확한 부분만 Q-ID
입력: 실제 파일·필드·버전
출력: 실제 파일·필드·실패 처리
수정 범위: 수정해도 되는 파일 경로 (관련 테스트·기록 경로 포함)
통과 조건: 실행 명령과 확인할 결과
선행 작업:
현재 기준선:
결과: 변경 / 실행한 검증 / 미실행·위험 / 다음 작업
```

새 작업 기록은 `docs/tasks/<id>-<topic>.md`에 생성합니다.
여기 표는 작업 큐이고, 수치·세부 실행 기록은 해당 작업서나 `reports/<run-id>/`가 소유합니다.
`blocked`에는 막힌 단계만 적고 독립된 작업은 진행합니다.

## 첫 작업 큐

`a8-v20-annex-injection`: **in_progress / 후보·CPU 계약 완료, GPU 미실행**,
[착수서](tasks/a8-v20-annex-injection.md) · [보고서](../reports/team-c/a8-v20-annex/README.md) ·
[실행 안내](../reports/team-c/a8-v20-annex/run-request.md).
후보 `experiments/a8_v20_annex.py`는 프롬프트 문자열만 바꾼다. 블록은 **실측 1,568자·586토큰**이고
**예산은 CPU 에서 확정**됐다 — 추가 축소 0/200, 두 군 본문 동일, `token_count_kind=actual`.
그 전제로 출력 예약을 두 군 모두 1,024로 내렸다(운영 예산에서는 13건이 깎였다).
고정 회차 v20 TP 상한 2 재확인. 검사 20개, 전체 295 통과.
**독립 리뷰 라운드 1~3의 P1 일곱을 모두 반영했다.** v13 근거 수리도 사용자 결정으로 이 PR에
넣었다 — `script.py:company_size_products()`가 검증된 인용을 요구한다. 실측 Macro −0.002838,
v13 4/9/2 → 3/8/3, 움직인 셀 3개·대상 밖 0셀, 법령 스윕과 결합 경로는 0셀이 됐다.
남은 채택 게이트는 A8 두 회차 실행뿐이다. GPU·무라벨·서버 미실행.
PR #84(코드 `d2c5f54`, 노트북 `d616c4a`). 열린 PR #82(`wiki-rag-pilot`)는 **다른 가설**이다 —
판정 페이지로 묶어 주는 효과를 재고 원문군을 대조로 둔다. A8 은 원문을 그대로 붙이는 단일 축이다.
코드 파일은 겹치지 않고 `docs/tasks.md`·`.wiki/plan-active.md` 텍스트만 겹친다.
1단계(법령 구조 인지 조회)는 PR #81로 `main`에 들어갔다 — 항목표 인용 31/31,
검사 23개, 독립 리뷰 9라운드에서 P1 21건을 잡고 `머지 허용`.
2단계는 「중소 소프트웨어사업자의 사업 참여 지원에 관한 지침」 제2조와 `[별표 1]`을
company_size 프롬프트에만 넣고 control/후보를 같은 ZIP으로 두 회차 비교한다.
**934자는 직접 조회 확인, 약 623토큰·baseline 초과 0/200은 추정**이다.
그 추정은 구현 후 실측으로 대체됐다 — 블록 586토큰·추가 축소 0/200. 스키마·소비자·관측 게이트는 유지한다.
PR #83 검토로 판정 경로와 TP≥3 전제를 정정했다. 입력·출력·허용 경로·반복 통과 조건은 착수서가 소유한다.
조회 근거는 [보고서](../reports/team-c/law-index/README.md)가 소유한다.

`a8-pr83-review`: **done / 검토와 필요한 문서 수정**, 사용자 요청 2026-09-21.
입력: PR #83 `26c38d3` diff, A8 착수서, 제공 원문, 현재 판정 경로와 보관 분석.
출력: 정정된 착수서·작업 큐·활성 계획, `artifacts/review/a8-pr83-result.md` 검토 근거.
수정 범위: 위 세 문서와 리뷰 기록. front matter 두 건은 형식·본문 보존만 확인한다.
통과 조건: 법령 조회/기본 검사, 문서 인코딩·링크·diff, 회차 문서 front matter 검증.
실제 모델 성과와 추정 분리, 반복 비교와 기존 소비자 보존을 계약으로 확인한다.
결과: 계획·큐·활성 계획 정정, 법령 조회/재생 37개·기본 검사 19개 통과, repo_lint 새 발견 없음.
검토 및 원격 본문 정정안은 `artifacts/review/a8-pr83-{result,body}.md`.
2026-09-21 후속 사용자 지시로 계획 정정 커밋을 진행한다. 기본 checkout의 회차 결정 문서 두 건도
front matter 누락을 재현해 PR #83과 같은 헤더로 수정했다. 양쪽 repo_lint·허브 lint 통과.
헤더 수정은 PR #83의 기존 `dd78047`에 이미 포함된다. 기본 checkout에는 동일 수정을 로컬 적용했으며
그곳의 별도 브랜치는 커밋하지 않는다. push·GPU 실행 없음.

`a5-v18-scope-review`: **done / 두 회차 기록 완료·후보 미채택**, [작업서](tasks/a5-v18-scope-review.md).
한 company 호출에 별도 scope 재검토 필드를 추가하고 v18에만 소비하는 후속 구현이다.
후보·CPU 계약 검사·Colab 준비·회차 기록을 완료했고, 2026-09-21 사용자 승인으로 PR #80의 보관 목적 병합을 진행한다.
[독립 분석](../reports/team-c/a5-label-definition/five-stuck-analysis.md)과
[방법](../reports/team-c/a5-label-definition/five-stuck-how.md)이 이 주제를 소유한다.
계획 상한 339.178초/200건, 후보 실측 280.871 / 299.693초. 기존 H3는 등록 회차에서 실행됐으며
아래 H3 “GPU 미측정”은 준비 당시 이력이다.
후보·OFF/ON 재생·두 회차 비교·dev 전용 노트북 구현, CPU 계약 33개 검증을 완료했다.
실행 소스 `44f5e4b`, 고정 노트북 `dd99efa`. 실제 company GPU 두 회차 등록 완료.
혼합 F1 0.600586987945 / 0.598735136094, v18 TP=1·OFF/ON 0셀·v13/v20 FP 증가 반복으로 미채택.
[24항목·시간·실패 결과](../reports/team-c/a5-v18-scope-review/results.md).
독립 리뷰·무라벨·전체 GPU·서버는 미실행이다. 후보 미채택과 운영 `script.py` 불변을 유지한다.
입력·출력·허용 경로·통과 조건은 작업서 §3~6, 실행 안내는
[v18 파일럿](../reports/team-c/a5-v18-scope-review/run-request.md)이 소유한다.

`a5-label-definition-wall`: 착수·진행 중. 배정 2026-09-21, astra. **v11 · v13 · v24** — 라벨 기준이 벽인 셋.
`18f07e5`(dev 0.599316 / 서버 0.508414)를 항목별로 갈랐다. v11은 오탐을 0으로 해도 최대 F1 0.500이고,
v13은 금액 구간·`scope`·`qualification`·`qualification_role`·직생 언급·인용 문장 **여섯 축이 전부
정탐과 오탐에서 같은 값**이다. v24는 [세 축 진단](../reports/team-c/v24-not-gateable/README.md)에 더해
빈 근거 22건이 게이트를 통과하는 구멍과 **"다르면 위반"이 아닌 반례 3건**을 새로 남겼다.
v10은 A3에 그대로 둔다 — `direct_production_demand()`가 v10 관련 15건 전부에서 직생 요구를 못 찾고
v11에서는 4건을 찾는 비대칭이 관측됐다. v18·v20에 줄 새 재료(`조항호내용`, 죽은 `정보화사업여부`,
안 쓴 SW 금액 4구간)도 §5에 있다. [작업서](tasks/a5-label-definition-wall.md).
이 배정 문단은 착수 시점의 것이며, 아래 H3·브리프 3·회차 2 항목이 그 뒤의 실제 결과다.

`a5-label-definition-wall / H3`: [동일 호출 조건 관측 파일럿](../reports/team-c/a5-label-definition/h3-scope-observation.md).
시간 예산 선계산·후보/실행기·Colab 준비·CPU 검사 5개 완료. 고정 코드 1735330, GPU 미측정.
이번부터 회차 ID·F1/24항목 지표·환경·시간·오답·실패 상태를 JSON/Markdown으로 자동 기록한다.
대조군/후보 dev 200건 + 진단 5건씩, 새 런타임에서 순서를 바꿔 반복한다. 기존 H2 소비자는 유지한다.
조건 인용은 진단에만 쓰고 새 강제 게이트는 넣지 않는다. 같은 호출 교체·추가 서버 호출 0.
실행 결과는 고정 기본/SME 응답을 결합한 혼합 CPU 재생이며 전체 GPU 점수와 구분한다.

`a5-label-definition-wall / 브리프 3`: [메타·규격 대조](../reports/team-c/a5-label-definition/catalog-findings.md).
발화 34건의 메타 적중 15·특이사항 5를 재현, 추가 네 건의 서버/햄/드론 규격 감사 완료.
조항호내용 필수 조건은 무라벨 발화 0·dev TP 하나 손실이라 기각한다. 메타 조회는 이미 입력에 있다.
조건 분해의 진단 자료로 사용하되 새 정답·scope 반례 네 건으로 세지 않는다. H2 채택 보류 유지.

`a5-label-definition-wall / 회차 2`: [재계산·판단](../reports/team-c/a5-label-definition/round2-decision.md).
후속 [원문 감사](../reports/team-c/a5-label-definition/observation-findings.md)에서 실제 발화의
240kW/고시 50kW 모순과 입력 분포 차이를 확인했다. 검증 완화·같은 H2 연속 수집은 기각했다.
실제 dev 3/200·무라벨 31/2,000 발화, 전체 검증 배율 1.033333·술어 배율 0.822222를 재현했다.
전수 수집 강제를 원문 타당성/분포 감사로 대체한다. 남은 18회차 일괄 수집 중단, 채택 보류.
부분 표본·대표성 미확인을 명시하며 `complete=false`는 유지한다. 서버 추가 호출 0, 머지하지 않는다.

`a5-label-definition-wall / H2`: CPU 검증 완료·채택 보류.
[결과](../reports/team-c/a5-label-definition/h2-absence.md): 명시적 기업규모 제한 부재를 v11에
연결해 TP 2→4, FP 3→4, FN 4→2. 다른 23항목 변화 0, CPU 재생 Macro 0.602504174073.
무라벨 2,000건 모델 사실은 확보·검증했다. A4 합본도 CPU 0.620382330538로 재현했다.
무라벨 TP/FP·합본 GPU/서버는 미측정이다. 운영 코드 변경 없음.

`a5-label-definition-wall`: in_progress. 2026-09-21 사용자 지정 `a5-label-wall` 작업.
입력·출력·범위·통과선은 [작업서](tasks/a5-label-definition-wall.md), 1차 결과는
[A5 진단](../reports/team-c/a5-label-definition/README.md)이 소유한다.
시간 예산 선계산 완료(추가 dev 추론 92.193초 한도), 원응답 200건 재생 동일.
H1은 대상 TP 변화 0·v12 FP +1로 기각. 무라벨 20,000건 규칙 발화율 측정 완료.
v13 조회 배선·v24 익명화 분기의 인수인계 전제를 정정했다. 실제 모델·서버는 미실행, 채택 없음.

`a3-zero-items / H4`: in_progress. 기준 `49475c3`, [회차 4](../reports/team-c/a3-zero-items/run4-facts.md).
H3는 v10 4/7/3·v18 0/2/7·v20 1/4/4로 동시 TP>0 미달이다. 다음은 기업등급보다 먼저
자격 문장의 역할을 출력하는 실험이다. v10/v20 소비·scope·A1 결정표·A2는 유지한다.
[작업서](tasks/a3-zero-items.md), [H4 보고서](../reports/team-c/a3-zero-items/h4-qualification-role.md).
실제 모델 효과·동일 ZIP 별도 반복·무라벨·시간은 미측정이며 아래 H3/H2/H1은 이력이다.

`a3-zero-items / H3`: in_progress. 기준 `c370aa2`, [회차 3](../reports/team-c/a3-zero-items/run3-facts.md).
v18 첫 TP 1건, v10·v20 TP=0으로 H2는 동시 통과 실패. 다음은 기존 company_size 출력에서
법적 필요 여부 상태를 제거하고 조항 원문/null을 추출하는 실험이다. SW 적용 대상은 짧은 원문을 쓴다.
입력·출력·범위·통과 조건은 [작업서](tasks/a3-zero-items.md), 결과는
[H3 보고서](../reports/team-c/a3-zero-items/h3-observed-clauses.md)가 소유한다. 실제 모델 미측정.
아래 H2/H1 항목은 이력이다.

`a3-zero-items / H2`: in_progress. `6738328`의 회차 2 기록을 반영한다.
H1 두 회차 모두 v10·v18·v20 TP=0. 기존 company_size 호출에서 등록 제한값과 본문 요건을
분리하고 v10·v20의 존재/부재 사실을 확장한다. v18 결정표·A2는 유지한다.
입력·출력·범위·관측 경계는 [작업서](tasks/a3-zero-items.md), 검증·실행은
[H2 보고서](../reports/team-c/a3-zero-items/h2-document-requirements.md)가 소유한다.
각 TP>0과 기존 일반화·FP·대상 밖 변화·반복·시간 조건을 모두 유지한다. 실제 모델 미측정.
아래 A3 H1·검사 복구 항목은 이전 기록이다.

`a3-colab-stage-guard`: 로컬 수정·검증 완료. A3 live dev 200건 완료 후 check_live의 옛 v13 보호 조건으로 중단.
입력: `colab-results-1789886517580784653.zip`, 고정 코드 `b7ac265`.
출력: 단계 소유권에 맞는 검사·실패 회귀 검사·원본 회차 등록·복구 채점·재개 안내.
범위: 공용/A3 노트북, `tests/test_package.py`, A3 보고서·작업서·실행 색인·위키 상태.
통과: 수정 전 실패 재현, 실제 저장 CSV로 수정 후 check_live 통과, 소유권 없는 v13·대상 밖
변경은 계속 차단, 추론 코드·고정 REPO_REF 불변. GPU 재실행과 CPU 복구 채점을 구분한다.
검증: 수정 전 동일 오류 재현 → 기존 검사 7개 통과, 실제 저장 CSV에서 두 수정 노트북 통과.
[회차·복구 결과](../reports/team-c/a3-zero-items/run-1789886517580784653/README.md).

`a3-zero-items`: in_progress. 배정 2026-09-20, `glassfish` 세션(astra). **부재탐지 축을 통째로 본다**
— v10·v18·v20, 합계 천장 +0.125로 남은 것 중 가장 크다.
[프레임·구조·통과 조건](tasks/a3-zero-items.md). **항목 셋을 하나씩 고치는 작업이 아니다** —
dev 양성 19건에 맞춘 규칙 셋은 무라벨에서 죽는다(v24 태그 규칙이 그렇게 반려됐다).
부재탐지 5개는 전부 작동하는 항목의 **음성 쌍둥이**이고, 공통 병목은 공고문에서
참가자격 제한·제출서류 목록·법령 인용을 못 가르는 것이다. 세 번 독립 관측됐다.
모델 1차 호출이 200건 전체에서 셋 다 한 번도 1이라 하지 않아 GPU 회차가 필요하다.
착수 기준 코드는 `6bb692d6162e6b604dae34e6e8044cc31dd7a60b`, 작업서 포함 HEAD는 `76e2a3f`다.
첫 가설은 기존 company_size 호출의 자격 추출에서 원천·문장 역할을 구분하는 것이다.
입력은 scope 회차 원응답·dev·제공 조문, 출력은 프롬프트 후보·진단 보고서·검증 번들이다.
수정 범위와 실제 모델 TP/FP·무라벨 발화율·동일 ZIP 반복·시간 조건은 작업서가 소유한다.
로컬 결과: 자격 문단만 수정, 기존 검사 44개·AST 범위 검사·ZIP mock 통과.
무라벨 6,000건 입력 사전 점검만 끝났고 모델 발화율은 미측정이다.
[원응답 감사·후보·실행 절차](../reports/team-c/a3-zero-items/README.md). GPU 회차 대기, 미채택.

`a4-precision`: 배정 2026-09-20, 주 세션. 재생으로 잴 수 있는 오탐·배선 전부.
`scope`→v12·v13 배선 완료(F1 0.444→0.727 · 0.167→0.444,
[보고서](../reports/team-c/scope-wiring/README.md)). v11은 재 보고 안 이었다 — F1이 내려간다.
v24는 예산·계약방법·지역제한 세 축을 코드로 대조해 봤으나 셋 다 정밀도 20% 미만이라
[채택 없이 진단만](../reports/team-c/v24-not-gateable/README.md) 남겼다.
남은 것: v9 FP 12 · v17 FP 9 · v13 FP 8 · v6 FP 5, v10 배선.
`a4-scope-gate`: 후보 준비 완료, 미채택. 2026-09-21, 주 세션. 적용범위 게이트 다섯을 한 묶음으로
구현·측정했다 — 하나씩 재서 이긴 것만 남기는 것이 dev 과적합의 경로라 한 번에 넣고 한 번 쟀다.
`18f07e5` 회차의 `dev-debug` 재생에서 **0.593846 → 0.611724 (+0.017878), 12셀, 대상 밖 0**.
**v6 0.462→0.667**(근거 없음·비지역·광역확대 셋을 내림, 오탐 4→0) ·
**v23 0.286→0.500**(지방+협상 범위 밖 0 + 낙찰자 결정기준 제7장 제3절 2-다의 설명일 8일) ·
v9 0.435→0.444(과업 명세 문서 밖 인용을 내림 — 남은 오탐 8건을 자를 축이 없다).
**0.6에 닿은 것은 v6 하나다.** v10·v13은 같은 묶음에서 재 봤고 열 재료가 없어
[A5](tasks/a5-label-definition-wall.md)로 넘겼다. 무라벨 20,000건 배율은 v6 1.11·v9 1.16으로
건강하나 **v23 규칙은 0.05배**라 비공개 집합 재현율 경고가 붙는다.
[보고서](../reports/team-c/a4-scope-gate/README.md) · `experiments/a4_scope_gate_candidate.py` ·
`tests/test_scope_gate_candidate.py` 10개 통과. `script.py`는 안 고쳤고 실제 회차·서버 미측정이다.

`a1-scope`: **완료.** `0a8459a`가 `scope` 절을 바꿔 회차 `colab-1789880471715651259`에서
경쟁제품 15건 중 `scope==competitive`가 0→15가 됐다. dev 0.505382 / dev-debug 0.512314.
[결과](../reports/team-c/merged-candidate/result.md). 무라벨 발화율·같은 ZIP churn은 미측정.

`a1-company-size`: in_progress. 사용자 지정 `merganser` 구현 세션이 기업등급 세로축과
v14~v18 결정표를 맡는다. [입력·출력·수정 범위·통과선](tasks/a1-company-size.md).
서버 기준선은 `57761ff` 0.2978624361 / 4,281초이며 새 A1 모델 회차는 아직 없다.
결정표·추출 단계·실패 보존·재생·카나리 집계 구현 및 로컬 검증 완료.
[결과·남은 GPU 실행](../reports/team-c/a1-company-size/result.md). 독립 리뷰 미실행.
9/20 측정 갱신: 동일 ZIP 재실행으로 현재 코드 churn 실측, 원응답 기본 보존.
Colab 회차 제한만 해제됐으며 제출·시간·정답 규모·한 회차 한 가설 제약은 유지한다.

`team-handoff`: 4명 기준 업무 분배 문서 작성.
- 공개 요청: 계획·분석 자료를 커밋/PR/머지하고 프로젝트 위키에서 현재 계획 질의와 세션 시작에
  최신 목표·담당·48시간 기준이 주입되는지 직접 검사한다. 추가 범위: `.wiki/project.md`, 위키 검사 기록.
  허브 공통 위키 코드는 변경하지 않는다. 머지 후 브랜치·스크래치를 확인하고 필요한 산출물은 보존한다.
- 후속 요청: 최신 dev 24항목·과거 실행·실제 오답을 집계해 점수 개선 중심의 연속 작업으로 재작성.
  추가 수정 범위는 `reports/team-score-audit/`와 `.wiki/plan-active.md`.
  통과 조건은 CSV 재채점 일치, 사례 원문 위치 대조, 수치에 연결된 담당·후속 순서·중단/채택 조건이다.
- 최신 요청 반영: 9/24 0.60 도전 일정, 48시간 0점 항목 TP 회복 점검, v20의 C 이관,
  C3·D1 우선 실행과 실패 단계별 후속 판단을 문서화하고 실제 과거 기록으로 점검 기준을 확인한다.
- 입력: `693c695` 코드·T1 실행 기록·현재 규칙, 사용자 지정 Opus 5 medium 개발 환경.
- 출력: [4인 업무 분배와 인수인계](tasks/team-handoff.md). 본인 포함 4명 기준이며 실명은 미배정.
- 수정 범위: 이 작업 큐, `docs/README.md`, `docs/tasks/team-handoff.md`.
- 통과 조건: 4명별 입력·출력·수정 범위·완료 조건·복사할 지시문, 파일 소유권·선행 관계,
  실제 검증과 미검증 구분, 로컬 링크·UTF-8 without BOM·LF 확인. 사람에게 배정·전송한 상태는 아님.
- 결과: 실제 6회 CSV의 24항목 재채점 일치, 최신 11항목 F1=0·부재탐지 FN=31·집중 오탐을 근거로 재작성.
  B/C/D에게 24항목을 중복 없이 배정하고 후속 티켓·구현 범위·통합·중단/채택 조건을 명시했다.
  `reports/team-score-audit/`에 수치·실행 이력·사례 원문 위치를 보존했다. 업무 자체의 구현·실제 실행은 후속이다.
  분석 확인: 24항목 배정·19개 티켓, 사례 원문 위치 12곳 대조 통과.
  공개 전 확인: 현재 계획·팀원 업무·다음 작업 질의 3개와 SessionStart 직접 실행에서
  0.60 목표·C3/D1·상세 작업서가 주입됐다. 머지 질의에는 정리 규칙이 주입됐다.
  위키 동기화·repo_lint 새 발견 없음. [직접 실행 기록](../reports/team-score-audit/wiki-checks.json) 참조.
  문서 인코딩·링크·diff 검사 통과. 자동 호스트 이벤트 전체와 팀원 PC 검증으로 확대하지 않는다.

`wiki-maintenance`: done. 종료 전 위키 검진·공개본 연결과 결정 기록 보완.
현재 연결·검사·공유 범위는 [위키 유지보수 기록](tasks/wiki-maintenance.md)을 따른다.

`public-push`: 사용자 지시로 하위 작업 공간 정리 및 공개 GitHub push.
입력·수정 범위·결과는 [공개 작업 기록](tasks/public-push.md)을 따른다.

`run-archive`: 결과 ZIP을 사람마다 전달하는 경로를 없애고 `git pull` 하나로 실행 기록을 받게 한다.
- 입력: 사용자가 전달한 `colab-results-1789621345861123113.zip`
  (SHA-256 `335796bce22ccdae6cf90e2da550a5c3575ed23feb1189b5f40e157b6c2feec8`, 기준 코드 `654c556`),
  `reports/team-score-audit/history.json`의 6회 기록.
- 출력: [실행 기록 색인과 보관 규약](runs.md), `reports/runs/colab-1789621345861123113/`,
  `.wiki/decisions/2026-09-17-013-docs-run-archive.md`.
- 수정 범위: `reports/runs/`, `docs/runs.md`, `docs/README.md`, 이 작업 큐,
  `.wiki/plan-active.md`, `.wiki/decisions/`. `script.py`·`tests`·`open/` 원본은 제외한다.
- 통과 조건: ZIP 해시·코드 커밋 일치, 추가 파일의 비밀정보 패턴·50MB 검사,
  `python -X utf8 -m unittest tests.test_baseline tests.test_package tests.test_score`,
  `git diff --check`, UTF-8 without BOM·LF·로컬 링크, 새 세션 문서 목록의 `docs/runs.md` 노출.
- 결과: 문서·기록 작업이며 모델 추론·재채점·서버 제출은 수행하지 않았다.
  수치는 실행이 남긴 파일과 `history.json`에서 옮겼고 다시 계산하지 않았다.
  세션 시작 문서 목록은 생성 색인 `.wiki/corpus.json`에서 나오므로 파일을 만든 직후에는 뜨지 않았다.
  공용 위키 `tool/sync.py`를 돌려 색인을 갱신한 뒤 `runs.md — 실행 기록`으로 표시되는 것을 확인했다.
  corpus 도구 자체는 고치지 않았다.

`label-compare`: T4의 첫 실행. 무라벨에 붙일 라벨의 **생성기를 고르기 위해** 외부 LLM 두 개를
dev 200건에 블라인드로 돌려 비교한다. 입력·출력·실행 절차·판단 기준은
[라벨 비교 작업서](tasks/label-compare.md)가 소유한다.
- 계획했던 `tools/gen_label.py`·`labels/`는 만들지 않았다. 같은 일을 `tools/label_bundle.py` 하나가
  하며, 정답 누출을 막는 격리 번들 생성까지 같은 도구가 갖는다. 복제 구현을 만들지 않는다.
- 상태: Opus 5 33/50 완료(나머지는 CLI 세션 한도), **Astra 0/50(할당량)이라 모델 비교는 없다**.
  Gemma가 6회 내내 TP=0이던 11항목에서 Opus 5가 TP=21을 냈고 v8·v14·v15는 전부 맞혔다.

`prompt-from-labels`: 그 33건의 근거 인용으로 Gemma 프롬프트의 v8·v14·v15 질문을 고치고
**얼마나 개선되는지 잰다.** 설계·측정·채택 조건은 [프롬프트 개선 실험](tasks/prompt-from-labels.md)이 소유한다.
- **다른 개선과 같은 회차에 섞지 않는다.** 이 실험이 곧 라벨링 트랙의 투자 회수 측정이라,
  섞으면 개선분의 귀속이 불가능해지고 "무라벨에 라벨을 더 붙일 값어치가 있나"에 답할 수 없다.
- 근거를 dev 33건에서 뽑았으므로 채점을 **본 33건 / 못 본 167건**으로 나눠 따로 낸다.
  167건에서 서는 개선만 일반화한 것이다.
- 프롬프트 변경은 모델 출력을 바꾸므로 replay로 못 잰다. Colab 회차가 필요하다.

`run-registrar`: 손으로 하던 결과 ZIP 언팩·대조·파일 작성을 한 명령으로 바꾼다. 검증 실패는 실패로 끝낸다.
- 입력: `artifacts/inbox/`의 `colab-results-<숫자>.zip`·`submit.zip` 한 쌍과 `--code-commit`.
  선택적으로 전달받은 해시 `--expect-results`·`--expect-submit`.
- 출력: `tools/register_run.py`, `reports/runs/<run-id>/`와 `manifest.json`, [색인](runs.md) 한 행,
  `.wiki/decisions/<날짜>-run-<run-id>.md` 초안. 커밋은 하지 않는다.
- 수정 범위: `tools/register_run.py`, `tests/test_register_run.py`, `docs/runs.md`, `docs/README.md`,
  `.wiki/adapter.toml`, 이 작업 큐. `script.py`·`open/` 원본은 제외한다.
- 통과 조건: 실패 조건마다 테스트 하나 — ZIP 후보 0개/2개, 해시 불일치, 예상 경로 없음,
  비밀정보 패턴, 단일 파일 50MB 초과, zip slip, 대상 폴더 선점. 정상 경로는 작은 가짜 ZIP으로 확인한다.
  `python -X utf8 -m unittest tests.test_register_run tests.test_baseline tests.test_package tests.test_score`,
  `python -m ruff check`, `git diff --check`.
- 결과: 도구·테스트 작업이며 모델 추론·재채점·서버 제출은 하지 않았다. 점수는 `score/metrics.json`에서
  옮기고 재계산하지 않으며, 로그에 없는 값은 null로 둔다. 실패는 부분 결과를 남기지 않는다 —
  모든 검사를 통과한 뒤 완성한 폴더를 rename으로 올리고 그다음에 색인·초안을 쓴다.
- 실패 재현: 구현 전 `tests.test_register_run`이 `tools/register_run.py` 없음으로 12건 모두 실패했다.
- 골든 대조: 원본 `colab-results-1789621345861123113.zip`(SHA-256 `335796bc…feec8`)과 `submit.zip`
  (`f4ee1634…81cc0`)을 그대로 넣어 임시 루트에 등록하고 손 등록본과 비교했다. 파일 56개로 같고
  **바이트 불일치 0개**다. `manifest.json`에서 다른 칸과 이유는 아래가 전부다.

  | 다른 칸 | 이유 |
  | --- | --- |
  | `registered_at`, `archived_at` | 등록 시각. 손 등록본은 날짜만 적었다 |
  | `zip_sha256` | 손: 결과 ZIP 하나 / 도구: `{results, submit}` 두 개 |
  | `code`, `environment` | 손이 덧붙인 `script_sha256`·`submit_zip_sha256`·`host: "Google Colab"` |
  | `inputs`, `status` | 손이 `bundle-manifest.json`·`validation.json`에서 옮겨 적은 칸. 도구는 안 만든다 |
  | `score`, `raw_responses` | 수치는 같고 손이 덧붙인 산문(`baseline_description`, `reason`)만 다르다 |
  | `cases.*.mode` | 도구가 더 남긴다. mock 회차를 실제 회차로 세지 않기 위한 칸 |
  | `cases.*.seconds.wall_clock` | 손은 3자리 반올림, 도구는 `*-command.json` 값을 그대로 옮긴다. 반올림하면 일치 |

  `cases`의 `count`·`counts`·`macro_f1`·나머지 `seconds`와 `score.final_macro_f1`
  `0.22078771129016228`, `baseline_macro_f1_same_run`, 코드 커밋, 원응답 여부는 손 등록본과 같다.
  대조 중 `extra_selected`(= 검증 + 폴백, `colab.md`의 항등식)와 `cases.*.macro_f1`
  (`score-command.json`의 `--pred` 인자로 채점 대상 case를 찾는다)이 빠져 있어 채웠다.
- 경로 정책: 등록기가 만든 `manifest.json`·색인 행·결정 초안과 푼 파일 55개 모두 개인 절대 경로 0건.
  Colab 컨테이너 경로는 살아 있다 — `/content/` 30개 파일, `/root/.cache` 7개 파일.
  `docs/runs.md`의 적중 2건은 규약 문장(45행) 자체이며 등록기가 쓴 줄이 아니다.
- 바이트 보존: `dev.log`·`sample.log`에 줄 끝 공백이 각각 7줄 있고 그대로 보존됐다.
  `git check-attr`로 `reports/runs/**`에 `whitespace: -trailing-space`가, 등록기가 만든
  `docs/runs.md`·`tools/*.py`에는 `unspecified`가 적용됨을 확인했다. `git diff --check` 통과.
- 본 적 없는 ZIP 6건: `Downloads/123/`의 과거 회차를 대역 `submit.zip`과 짝지어 임시 루트에 돌렸다.
  5건이 **손 수정 0**으로 등록됐고 점수·커밋이 기존 색인 기록과 모두 일치했다
  (`1c64604` 0.2208013652894021, `9363f21` 0.1847…, `40e2cc6` 0.2195…, `57c78cf` 0.2110…, `e9e4022` 0.2199…).
  색인은 행 수 6을 유지한 채 해당 `미보관` 행만 채웠다. 남은 1건은 설치 실패 로그
  `colab-results-1789602422101717812.zip`으로 `run_report.json`이 없어 거부됐다 — 추론이 돌지 않은
  회차를 `reports/runs/`에 남길지는 사람이 정할 문제다. 대역 `submit.zip`을 쓴 형태 시험이며 실제 등록이 아니다.
- 남은 미확인: D0의 새 Colab 회차와 대회 서버 제출로는 확인하지 않았다.

`run-cc1e61d`: 고친 스키마의 첫 GPU 회차. 수정은 됐는데 결과가 뒤집혔다.
- **스키마 수정은 들어갔다. 단 `판정=1` 66건 전부 `violation_found`는 성과가 아니다.**
  이 회차의 `판정`은 `parse()`가 `막힌_단계 == violation_found`로 만든 파생값이라 어긋남이
  정의상 불가능하다. 앞 회차 286/370 어긋남이 사라진 것은 두 칸이 서로를 반증하던 장치가
  없어졌다는 뜻이고, 단계 이름의 정확성은 아직 검증되지 않았다.
- **그런데 재현율이 무너졌다:** v16 6→1, v18 4→2, v20 3→0. 합계 13/18 → **3/18**.
  양성 판정 총수 370 → 66. 같은 모델·같은 공고이고 바뀐 것은 판정을 묻는 방식인데,
  **그 안에 변수가 둘이다** — `판정` 칸 제거와 프롬프트의 보수화 지시 두 문장이 한 회차에
  같이 들어갔다(`prompt_sha256` `69c76ca…` → `a450eea…`). 어느 쪽 효과인지는 아직 모른다.
  앞 회차의 "v16 6/6"이 모델 실력이 아니라 느슨하게 물은 결과였다는 것까지가 말할 수 있는 선이다.
  `reports/team-score-audit/absence-detection.md`를 두 회차 대조로 다시 썼다.
- **C3에게는 손잡이다.** 재현율·정밀도 다이얼이 프롬프트·스키마 쪽에 있다. F1로는 v18이
  합친 쪽(0.093 대 0.067), v16이 따로 둔 쪽(0.079 대 0.056)이 낫다. 아직 둘 다 쓸 만하지 않다.
- **v20은 다른 문제다.** 200건 중 192건이 `context_not_observed`이고 양성 0이다.
  v16·v18의 "봤는데 조건 미충족"과 다르므로 같은 처방을 쓰면 안 된다.
- 같은 `script.py`의 다섯 번째 측정: dev 0.2202239896. **코드가 같은** churn 관측을 열 쌍으로
  늘리고 셀 범위를 29~45로 잡았다. 코드가 다른 쌍은 표에 남기되 `DRIFT_*` 상수에서 뺐다 —
  섞으면 하한이 25로 내려가 churn을 실제보다 넓게 말한다. 상수와 인용 문서를 함께 고쳤고,
  상수를 표에 묶는 검사를 `tests/test_compare_runs.py`에 넣었다.
- **노트북 품질 게이트가 이번엔 반대로 뒤집혔다.** `validation.json`이 `quality_pass: false`이고,
  그 판정의 근거인 `macro_f1_delta` −0.0005773756926995555는 같은 폴더의
  `quality-comparison.json`에 있다(`validation.json`에는 이 키가 없다).
  run4가 **같은 기준선을 +0.00000477로 넘겨 통과**한 바로 그
  문이고 `script.py`는 동일하다. 문이 churn만으로 양방향으로 열리고 닫힌다는 뜻이라,
  `quality_pass`를 채택 근거로 쓰지 않는다는 규칙의 실측 사례가 하나 더 생겼다.
- 결정 기록이 번호 없이 `2026-09-18-run-<run-id>.md`로 나왔다. PR 번호와 안 부딪힌다.
- 미실행: 이 회차는 제출하지 않았다. 세 변수(항목 수·근거 null·출력 형식) 분리와
  넷째 변수(칸 제거 대 보수화 지시)를 둘로 가르는 일은 C3 몫이다.

`decision-collision`: 공용 위키 훅이 손으로 쓴 결정 기록 3개를 덮어썼다. 원인을 찾아 가드를 단다.
- 사고: `2026-09-17` 013·015·016의 한국어 전문과 `triggers`·`domain`이 PR 제목 기반 영문 스텁으로
  바뀌었다. 작업 트리 변경이라 `git restore`로 복구했고 커밋되지 않았다.
- 원인: 공용 위키 `tool/sync.py`가 Stop 이벤트에서 `harvest.record()`로 머지된 PR을 캔다.
  중복 가드 `recorded()`가 **frontmatter의 `pr:` 줄만** 보는데 손으로 쓴 기록에는 그 줄이 없다.
  그래서 미기록으로 판정되고 `write_text`가 **같은 이름을 덮었다.** 파일명 규칙이 같은 것
  (`<날짜>-<번호>-<슬러그>`)이 충돌의 조건이었다.
- 판단: 훅은 쓸모가 있다. `012`처럼 `triggers`·`domain`이 채워진 기록을 만들고 세션 시작 요약과
  주입에 쓰인다. 지우지 않고 가드를 달았다.
- 허브 수정(`ai-coding-agent-wiki-public`): ① `recorded()`가 파일명 앞의 번호도 읽는다.
  ② **있는 파일은 절대 안 덮는다** — 번호 판정이 또 틀려도 여기서 멈춘다. ③ 쓸 때 `newline="\n"`.
  `tool/test_harvest.py`에 두 가드 검사를 넣었다(11건 통과).
- 이 저장소 수정: `register_run.py`가 일련번호를 쓰지 않는다. `<날짜>-run-<run-id>.md`는
  PR 번호와 부딪힐 수 없다. 이미 만든 기록 3개를 그 이름으로 옮기고, 제출 장부 기록은 실제
  PR 번호 019로 맞췄다. 훅 생성본 6개는 LF로 바꿔 보존하고 중복 014는 지웠다.
- 같이 발견: 내 PR 본문에 `## 변경 요약`·`## 변경 이유` 절이 없어 훅이 본문을 뭉갰다.
  `docs/workflow.md` W4에 규약으로 적었다.
- 미확인: 훅이 실제 Stop 이벤트에서 다시 돌 때 가드가 먹는지는 다음 머지에서 확인한다.

`cpu-replay`: "후처리 후보는 CPU에서 잰다"고 두 번 적었는데 그걸 하는 도구가 없었다. 만든다.
- `tools/replay_run.py`는 보관된 원응답으로 `parse_judgment`→`verify_sme`→`postprocess`를 다시
  돌린다. 모델을 부르지 않는다. `--candidate`로 그 두 단계 중 정의한 것만 갈아 끼운다.
- **`--verify`는 보관 원응답의 무결성 검사다. HEAD 회귀 가드가 아니다.** 회차 `manifest.json`에
  기록된 커밋의 `script.py`를 `git show`로 읽어, 그 코드로 회차 자신의 CSV를 바이트 단위로
  재현하는지 본다(PR #30부터). HEAD의 후단이 바뀌어도 회차는 그 회차의 코드로만 재현되기 때문이다.
  `tests/test_replay_run.py`가 최종·기본 CSV 양쪽을 검사한다. 재현이 깨지면 보관 응답을 근거로
  쓸 수 없다는 뜻이므로 검사가 먼저 빨개져야 한다.
- **HEAD 회귀 가드는 따로 있다.** `test_head_replay_matches_the_pinned_head_csv`가 HEAD 코드의
  재생 결과를 고정 CSV(`reports/team-b/b5-port-replay/submission.csv`)와 바이트 대조한다.
  HEAD 후단을 일부러 바꾸면 그 CSV를 새로 고정하고 이유를 PR에 적는다.
- **비교 기준은 HEAD 재생 CSV다.** 후보 없이 `--verify` 없이 재생한 CSV를 `--before`로 쓴다.
  만드는 명령(후보와 같은 HEAD에서 돌린다):
  `python -X utf8 tools/replay_run.py --case <회차>/dev-debug --output-dir reports/<담당>/head-<커밋>-replay`.
  전체 순서는 [업무 분배 §0](tasks/team-handoff.md#0-시작-전에-읽을-것--2026-09-17-저녁-갱신)의 명령 블록이다.
  보관 회차의 `submission.csv`를 `--before`로 쓰면 그 뒤에 병합된 후처리의 효과가 후보에 섞인다.
- 실측: dev 200건 재생 **0.64초** + 채점 0.20초. 재생 점수가 회차 기록 0.218203523963과 일치했다.
  Colab 회차 12~16분이 0.84초가 된다.
- **회차 churn이 없다.** 같은 모델 출력을 쓰므로 후보와 기준의 차이가 곧 후보의 효과다.
  `compare_runs.py`의 churn 경고가 필요 없는 유일한 비교 경로다.
- 거부 조건: 원응답이 없는 회차, `sme_documents_shrunk > 0`인 회차(줄어든 공고의 건별 예산이
  로그에 없다), 후보를 넣은 채 `--verify`(그 경우 "회차와 같다"는 말이 뜻을 잃는다).
- 못 재는 것: 프롬프트·스키마를 바꾸는 후보. 저장된 응답 자체가 달라지므로 Colab 회차가 필요하다.
- 수정 범위: `tools/replay_run.py`, `tests/test_replay_run.py`, `docs/workflow.md` W5,
  `docs/README.md`, `docs/tasks/team-handoff.md`, `.wiki/plan-active.md`, 이 작업 큐.

`run-89a6a11`: 진단 도구 첫 GPU 회차. 부재탐지가 풀릴 수 있다는 실측과 재현성 재정정.
- **부재탐지 3항목을 별도 스키마 3항목 질의로 물었다.** v16 TP 0→**6/6**, v18 0→4/7, v20 0→3/5.
  대신 FP가 139/109/109로 정밀도가 무너져 F1은 0.079/0.067/0.051이다. 파이프라인은 전부 0.000.
  당시에는 **"문제는 미탐이 아니라 정밀도"**라고 적었다. 전문·한계는
  [부재탐지 진단](../reports/team-score-audit/absence-detection.md). C3의 출발점을 바꿨다.
  **→ `run-cc1e61d`가 이 단정을 좁혔다.** 느슨하게 물었을 때만 맞는 말이고, 보수적으로
  물으면 v16이 6건 중 1건이라 거기서는 다시 미탐 문제다.
- 세 변수(항목 수 24→3, 근거 null 고정 해제, 출력 형식) 중 무엇이 원인인지는 이 회차로 못 가른다.
- **도구 결함:** `판정`과 `막힌_단계`를 별도 칸으로 두어 `판정=1` 370건 중 286건이 어긋났다.
  단계 히스토그램을 못 쓴다. 두 칸을 하나로 합치고 위반 여부는 프로그램이 정하게 고쳤다.
- **재현성 재정정:** 같은 `script.py`(`2ad9ea8f`)의 네 번째 측정이 dev 0.2208061356으로,
  앞선 세 번의 0.2182에서 0.0026 벌어졌다. 코드 변경 0. churn 범위를 여덟 쌍 기준
  0.000008~0.003129로 넓히고 `reproducibility.md`·`compare_runs.py`·W5·plan-active·인수인계를 고쳤다.
- **노트북 `quality_pass`가 잡음으로 통과했다.** 과거 기준선을 0.00000477 넘겼는데 이는 관측된
  가장 작은 churn 0.0000079보다도 작다. 게이트는 바꾸지 않고 문서에 적었다.
- 수정 범위: `tools/diagnose_items.py`, `tests/test_diagnose_items.py`, `tools/compare_runs.py`,
  `reports/team-score-audit/absence-detection.md`, `reports/runs/reproducibility.md`,
  `reports/runs/colab-1789658250172468461/`, `docs/workflow.md`, `docs/tasks/team-handoff.md`,
  `.wiki/plan-active.md`, `.wiki/decisions/…-020-…`, 이 작업 큐.
- 미실행: 고친 스키마(단계 한 칸)로는 아직 GPU 질의를 안 했다. 이 회차는 아직 제출하지 않았다.

`run-b113425`: 원응답 회차 등록, 재현성 결론 정정, Colab 배선 버그 수정.
- 사용자가 노트북 전체를 `RUN_DIAGNOSTIC=True`·`DIAGNOSE_ITEMS="v16,v18,v20"`으로 돌렸다.
  검증 회차 통과(dev 0.21821144133644133), **원응답 307건 확보**, 진단 도구는 실패했다.
- **정정:** 앞서 `reports/runs/reproducibility.md`에 "회차 간 Macro F1이 0.0025 흔들린다"고
  적은 것은 한 번의 뽑기였다. 같은 `script.py` 세 쌍에서 셀은 33~41개 바뀌는데 Macro F1은
  0.000008~0.000044만 움직였다. `654c556`과의 0.0025도 코드 효과가 아니다 — run1과의 두 차이가
  26%만 겹치고 방향이 7:6으로 균형이다. 결론: **churn의 점수 영향이 0.000008~0.002576으로
  300배 벌어지고 셀 수로는 구분되지 않는다.** 한 쌍의 Macro F1 차이는 신호가 아니다.
  `reproducibility.md`를 다시 쓰고 `docs/workflow.md` W5·`tools/compare_runs.py`·
  `.wiki/plan-active.md`·인수인계 §0을 함께 고쳤다.
- **Colab 배선 버그 두 개.** ① `tools/diagnose_items.py`가 Colab 번들에 없었다 — clone은
  `WORK/repo`로 가고 `WORK`에는 번들만 푼다. ② `script.py`는 `WORK/submission/`에 있는데
  도구가 `ROOT/script.py`를 봤다. `COLAB_FILES`·`upload` 셀 허용 목록·`--script` 인자를 고쳤다.
- **왜 테스트가 못 잡았나:** `run_logged`를 스텁해 인자만 확인했고 경로 존재를 확인하지 않았다.
  이제 `tests/test_package.py`가 번들이 만든 배치에서 `--mock`으로 도구를 실제 실행한다.
  그 검사가 즉시 `upload` 셀 허용 목록 결합도 잡았다.
- 수정 범위: `tools/package.py`, `tools/diagnose_items.py`, `tools/compare_runs.py`,
  `tests/test_package.py`, `tests/test_compare_runs.py`, `notebooks/colab-baseline.ipynb`,
  `reports/runs/reproducibility.md`, `reports/runs/colab-1789655036303880754/`, `docs/workflow.md`,
  `docs/tasks/team-handoff.md`, `.wiki/plan-active.md`, `.wiki/decisions/…-019-…`, 이 작업 큐.
- 미실행: `diagnose_items.py`의 실제 GPU 질의는 여전히 없다. 다음 회차에서 확인한다.

`bench-ready`: 내일 팀원이 점수 기법을 붙일 기판의 구멍을 메운다. 점수 개선 자체는 담당자 몫이다.
- 확인한 구멍 세 개. ① 팀원이 여는 [인수인계 문서](tasks/team-handoff.md) 359줄에 오늘 발견이
  **0줄** 반영돼 있었다(서버 점수·시간 86%·흔들림 0.0025·새 도구 3개·새 테스트 3개).
  ② 채택 조건 §8이 요구하는 "대상별 TP/FP/FN 전→후 / 비대상 회귀"를 내는 도구가 없어
  오늘 세션에서 두 번 손으로 짰다. ③ 특정 공고만 골라 돌리는 서브셋 실험 경로가 없다.
- ①②를 메웠다. ③은 미착수 — `--limit`은 앞에서 N건을 자를 뿐이고 `tools/score.py`는 ID 집합
  완전 일치를 요구해 미니 라벨 CSV가 필요하다. 다만 모델 로드가 200~490초라 6건으로 줄여도
  4~8분이고 전체는 12~16분이라 이득은 2~3배다. 회차 수가 병목이 되면 그때 만든다.
- 출력: `tools/compare_runs.py`(신규), `tests/test_compare_runs.py`, 인수인계 §0 신설과
  §1·§10·§12·공통 지시문 갱신, `docs/README.md`·`docs/workflow.md` W5 연결.
- 왜 흔들림을 임계값으로 안 쓰나: 한 쌍의 관측이다. 도구는 실측 대비 **배수**만 찍고
  통과/실패를 판정하지 않는다. 처음엔 `abs(delta) <= DRIFT`로 짰다가 실제 두 회차에서
  배수가 정확히 1.00이 나와 경계에 걸리는 것을 보고 판정을 없앴다.
- 통과 조건: `python -X utf8 -m unittest tests.test_compare_runs`, ruff, `git diff --check`.
  실제 두 회차로 돌려 v17 6건·v24 4건 등 바뀐 공고 ID가 나오는 것을 확인했다.

`run-36b6cc1`: D0 회차 등록과 회차 간 재현성 확인. 모델 추론은 사용자가 Colab에서 돌렸다.
- 실측: `36b6cc1` dev Macro F1 0.21825534501066987, 같은 회차 기본 0.21499821620044368.
  `654c556`보다 0.0025 낮다. 추가 호출 200→107건, 추가 추론 330.8→110.7초(-66.5%),
  dev 전체 896.9→694.8초(-22.5%). `quality_pass=false`로 `submit.zip`은 안 내려왔다.
- 재현성: 두 회차의 기본 단계 입력이 해시로 동일한데(프롬프트·스키마·채팅템플릿·
  sampling_params·청크·공고순서·입력 토큰 200건 전부) 출력 토큰이 33/200건 달랐고 v 셀이
  25/4,800개 바뀌었다. **점수 하락 -0.0025는 전부 기본 단계의 흔들림이다** — v13 재검증
  기여는 두 회차가 정확히 +0.0032571288102262로 같았다. 근거는
  [reproducibility.md](../reports/runs/reproducibility.md). 한 쌍의 관측이므로 일반화하지 않는다.
- 등록기가 처음 실전에서 막힌 자리(⑦의 게이트): 품질 게이트 미달이면 노트북이 `submit.zip`을
  안 준다. `candidate.json`의 기록 해시를 쓰도록 고쳤고 파일이 있으면 대조한다.
  **손으로 고친 파일 2개** — `tools/register_run.py`, `tests/test_register_run.py`.
  교차 플랫폼 재현으로 때우려던 시도는 실패했다: `zipfile.ZipInfo.create_system`이
  Windows 0 / Linux 3이라 같은 소스도 ZIP 바이트가 다르다(`2744d943` 대 `a5e038ea`).
- 기록 결함: `input_sha256`이 회차마다 달랐던 것은 `gzip.open`이 헤더에 현재 시각을 넣기
  때문이었다. 노트북을 `gzip.GzipFile(..., mtime=0)`으로 고쳤고 `tests/test_package.py`가
  두 번 압축해 바이트 동일을 검사한다. **이 수정 이전 회차의 `input_sha256`은 대조 불가다.**
- 수정 범위: `tools/register_run.py`, `tests/test_register_run.py`, `tests/test_package.py`,
  `notebooks/colab-baseline.ipynb`, `reports/runs/reproducibility.md`, `reports/runs/colab-…581500/`,
  `docs/runs.md`, `docs/workflow.md` W5, `.wiki/plan-active.md`, `.wiki/decisions/…-018-…`, 이 작업 큐.
- 미실행: 이 회차는 제출하지 않았다. 서버 시간·점수는 모른다.

`submission-ledger`: 채점된 서버 제출을 적을 자리가 없어 점수가 기록되지 않았다. 장부를 만든다.
- 사실: `654c556`을 2026-09-17에 제출해 리더보드 0.2197036943을 받았다. 사용자 보고이며 제출 ID·
  정확한 시각·public/private 구분은 받지 못했다. 저장소에는 `server_submitted: false`만 있었다.
- 출력: [제출 장부](../reports/submissions.json)(신규), [실행 기록의 대회 서버 제출](runs.md#대회-서버-제출),
  `reports/runs/colab-1789621345861123113/manifest.json`의 `server` 블록,
  `.wiki/decisions/2026-09-17-017-docs-first-scored-submission.md`.
- 수정 범위: 위 파일과 `docs/roadmap.md` P1, `.wiki/plan-active.md`,
  `reports/team-score-audit/result.md` 머리말, 이 작업 큐.
- 왜 색인이 아니라 별도 파일인가: 제출은 실행과 다른 사건이고 점수는 실행이 끝난 뒤에 나온다.
  `docs/runs.md` 색인에 두면 `tools/register_run.py`가 같은 실행을 다시 등록할 때 행을 통째로
  바꾸므로 손으로 적은 서버 점수가 지워진다. 장부는 등록기가 건드리지 않는다.
- 측정: dev 200건 0.22078771129016228, 리더보드 1,853건 0.2197036943, 차이 0.0010840169901622787.
  **오차가 아니라 다른 입력 집합의 측정이다.** 표본 한 개로 dev의 대표성을 일반화하지 않는다.
- 시간: 같은 회차가 6,192초(103분 12초). 한도 7,200초의 **86.0%**이고 여유는 1,008초다.
  건당 3.3416초, 한도 건당 3.8856초. 서버 GPU는 L40S 1장(Q3)인데도 Colab A100 40GB에서 잰
  건당 3.469초를 1,853건에 곱한 6,428초보다 빨랐다. **이유는 모른다** — 서버 단계별 시간을
  받을 수 없다. dev 건당 초를 곱해 서버 시간을 추정하지 않는다는 근거로만 쓴다.
- 규명하지 않은 것: 앞선 `5506ca0` 제출의 실행 오류 원인. 두 제출은 코드가 다르고
  (`9abb9c4e` 대 `79a56041`) 서버 원응답을 볼 수 없다. 채점 성공이 그 원인을 설명하지 않는다.
- 남은 미확인: `693c695` 이후 코드(현재 `main` 포함)는 GPU 실행도 제출도 없다.
  R16의 오늘 남은 제출 횟수는 대회 제출 이력에서 확인한다.

`item-diagnosis`: 내일 C3·D1이 "막힌 단계"를 찾을 수 있게 계기를 놓는다. 점수 개선 자체는 담당자 몫이다.
- 왜: 등록된 유일한 실행은 `debug_responses=false`이고 `diagnostics.jsonl`에 응답 길이·토큰 수·종료
  사유만 있다. 실측으로 확인했다 — 610개 이벤트 중 `response_text`를 가진 것 0개.
- 확인한 사실 세 가지. ① `--debug-responses`는 `script.py`에 **이미 있다**(`:594`, `:1064`).
  막은 것은 노트북으로, `check_live`가 `argv == [PYTHON, "script.py"]`와 `debug_responses: False`를
  단언한다. ② 부재탐지 5항목은 스키마가 `근거문구`를 `{"type": "null"}`로 고정하므로(`:238`)
  **원응답을 켜도 v16/v18에서 새로 보이는 것이 없다.** ③ `postprocess`의 `if hit and v not in ABSENCE:`
  (`:781`)가 위반=0 판정의 인용을 버리므로, v8처럼 부재탐지가 아닌 0점 항목은 원응답이 유일한 기록이다.
  400개 응답 전부 `finish_reason: stop`·`status: valid`로 잘림·파싱 실패는 0건이다.
- 정정: 이전 권고였던 "`SME_ITEMS`에 v16/v18/v20 추가"는 현재 코드에서 틀렸다. `SME_ITEMS = ["v13"]`이고
  `verify_sme`는 v13 전용 로직이며 추가 호출은 baseline v13 양성 공고에만 돈다. 전건 확장은 693c695가
  줄인 330.8초 패스를 되살리는 것으로 `.wiki/plan-active.md`의 보호된 결정 반전이다. 사용자 선택에 따라
  제출물을 건드리지 않는 `tools/diagnose_items.py`로 갔다.
- 출력: `tools/diagnose_items.py`(신규, 제출물 아님), `tests/test_diagnose_items.py`,
  노트북 9절 `diagnose` 셀, `tests/test_package.py`의 진단 셀 검사 2건, [Colab 절차](colab.md#항목-진단-전용-회차-선택).
- 수정 범위: 위 파일과 `docs/README.md`, 이 작업 큐. `script.py`·`SME_ITEMS`·`submission.csv`는 안 바꾼다.
- 설계: `diagnose_items.py`는 제출물 `script.py`를 import만 해 `iter_records`·`item_table`·
  `build_messages`·`fit_to_budget`·`VLLMRunner`를 재사용한다. 별도 스키마로 항목마다
  `요구사항`·`공고_인용`·`판정`·`막힌_단계`를 받는다. `막힌_단계`는 plan-active의 네 단계와 같은 이름이다.
  부재탐지 항목에도 `공고_인용`을 문자열로 허용해 제출 스키마의 null 고정을 우회한다.
  `--labels`로 실제 정답을 같은 줄에 붙여 "0이라 한 이유"와 양성을 나란히 본다.
- 통과 조건: `python -X utf8 -m unittest tests.test_diagnose_items tests.test_package`,
  `python -m ruff check tools/diagnose_items.py tests/test_diagnose_items.py`, `git diff --check`.
- 결과: mock·스텁 러너로만 검증했다. 실제 GPU 질의·새 Colab 회차는 미실행이며 진단 결과는 아직 없다.
  노트북 두 스위치(`RUN_DIAGNOSTIC`, `DIAGNOSE_ITEMS`)는 기본이 꺼짐이고 `check_live`를 부르지 않는다.
  회차가 원응답을 안 켜거나 본문을 안 남기면 셀이 실패하도록 두 갈래를 테스트로 잡았다.
- 다음 담당자에게: C3의 양성 ID는 v16 `PPS-DEV-20|037|058|065|066|067`, v18 `PPS-DEV-22|038|039|040|041|043|044`,
  D1의 v8은 `PPS-DEV-05|11|042|048|054|071`([recall-check.csv](../reports/team-score-audit/recall-check.csv)).
  `metrics.csv`의 `positive_records_truncated`는 v16 1건·v18 2건뿐이라 문맥 관측이 주 원인은 아니다.

설치 작업 `team-setup` — 상태: review (구현·임시 환경 검증 완료, 독립 리뷰 미실행).
- 2026-09-16 사용자 선택: 설치 도구까지 공용화. 공용 `tool/setup_agents.py`가 환경·버전·호스트를 검사하고
  프로젝트 진입점은 위임만 한다. adapter는 각 checkout에서 직접 읽으며 허브에 복사하지 않는다.
- 추가 수정 범위: 공용 위키 `tool/setup_agents.py`, adapter를 읽는 설치·주입·감사·그래프 코드와 관련 테스트,
  공용 `README.md`, 프로젝트 설치 테스트·안내·작업 기록. 폴더명 변경·동명 checkout 격리를 통과 조건에 추가한다.
- 입력: 양쪽 저장소의 규칙·설치 기록, 프로젝트 adapter, 공용 `tool/apply.py`, 설치된 Claude/Codex와 공식 지원 문서.
- 출력: 프로젝트 설치 진입점, 고정 위키 버전, 임시 환경 검증, `docs/setup.md`의 팀 설치·신뢰·확인 안내.
- 수정 범위: `tools/setup_agents.py`, `tests/test_setup_agents.py`, `.wiki/adapter.toml`, `.wiki/wiki-revision`,
  `.gitignore`, `.codex/config.toml`, `docs/setup.md`, `docs/README.md`, 이 작업 기록.
  공용 위키 수정 범위는 위 사용자 선택에 따라 설치 공용화와 checkout-local adapter의 호출자까지 포함한다.
  리뷰 요청 기록은 `artifacts/review/team-setup-request.md`에 둔다.
- 통과 조건: 임시 환경에서 Claude/Codex/둘 다 설치·재설치·사용자 설정 보존·공백/한글 경로·오류 종료·생성 명령 실행·프로젝트 포인터 주입 확인.
  UTF-8 without BOM·LF·Git 제외를 검사한다. 자동 호스트 이벤트와 실제 질문 UI는 별도 증거 없으면 미검증으로 남긴다.
- 기준선: 프로젝트 `4816cf66f93f7303061cf55be1d98ca02e9ac2b4` (clean),
  위키 `481917b5560c9bc9f98e04052afaa295d954255b` (기존 `.wiki/corpus.json`, `graph.json`, 미추적 `adapters/ai-nara-shop.toml` 보존).
  양쪽 remote 없음. 공유 URL·팀 접근 권한 미확정. T1~T8, 실제 모델, 유료 API, 배포·커밋·push 제외.
- 결과 (2026-09-16): 환경·버전·호스트 검사와 복구를 공용 `tool/setup_agents.py`로 옮겼다.
  프로젝트 진입점은 명시적 `--wiki`와 자기 checkout을 전달한다. `ADAPTER` 상수·형제 폴더 자동 탐색을 제거했다.
  기존 `apply.py`가 설정을 병합하며 주입·슬롯 예산·배선 검사·감사·그래프는 로컬 adapter를 읽는다.
  PC별 설치 호스트는 Git 제외 `.wiki/installed-agents.json`에 보존한다. 허브 adapter와 공유 슬롯은 쓰지 않는다.
- 실패 재현: `python -X utf8 tool/test_local_adapter.py`가 수정 전
  `TypeError: slots_for() takes 1 positional argument but 2 were given`으로 실패했고, 구현 후 통과했다.
- 최종 검증: `python -X utf8 tests/test_setup_agents.py --wiki ../ai-coding-agent-wiki` — 2 tests, 62.667초, OK.
  Claude/Codex/둘 다 설치·재설치·기존 설정/사용자 전역 설정 보존·읽기 전용 check·rollback·공백/한글 경로·
  폴더 이동·동명 checkout 슬롯 격리·생성 명령 직접 실행·문서 포인터·Git 제외를 검사했다.
  의존성 누락·잘못된 위키 경로·SHA 불일치·dirty 실행 코드·비활성 hooks·잘못된 adapter/JSON·지원 밖 경로는 실패했다.
  환경: Windows, Python 3.13.9, Claude Code 2.1.273, Codex CLI 0.154.0. 실제 유료 세션은 열지 않았다.
- 공용 검증: 선언된 위키 게이트와 새 로컬 adapter 검사 총 13개 명령 통과 (7.43초).
  `python -X utf8 -m pytest -q tool/test_codex_hooks.py` — 13 passed (23.27초).
  프로젝트 Ruff·diff 검사와 이번 수정 파일의 UTF-8 without BOM·LF 검사 통과.
  위키 전체 `git diff --check`의 기존 `graph.json` CRLF 공백 오류는 보존했고, 이번 수정 파일 범위는 통과했다.
  `lint --check`는 종료 코드 0이며 기존 슬롯 차이 4건은 의도된 보고다.
- 증거 경계: 설치 검사는 임시 clone 위의 미커밋 도구 작업본에 `--allow-dirty-wiki`를 명시했다.
  기본 설치가 dirty 코드를 거부하는 것도 확인했다. 이 최초 작업본 검사는 배포 버전 검증이 아니다.
  실제 자동 호스트 이벤트 전달·다른 OS·팀원 PC·독립 리뷰는 미검증이다.
  이번 Default 세션 첫 `functions.request_user_input` 호출은 두 선택지를 받아 “설치 도구까지 공용화” 응답을 반환했다.
  이는 실제 동기 질문 호출의 증거이며 모든 호스트 UI·키 동작이나 hooks 자동 실행의 증거는 아니다.
- 커밋 후속: 사용자가 로컬 커밋을 요청했다. 위키 `15fc1fd110ee646563ebb415dc00a5e88fd188fa`를 만들고
  `.wiki/wiki-revision`에 고정했다. 테스트는 작업본 복사 없이 이 커밋의 임시 clone을 쓰도록 바꿨다.
  프로젝트 변경은 `chore/team-agent-setup` 브랜치에 기록한다. 기존 미커밋 자료는 제외한다.
- 고정 커밋 검증: 같은 설치 테스트 명령으로 2 tests OK (57.521초).
  작업본 복사·`--allow-dirty-wiki` 없이 위키 `15fc1fd`의 깨끗한 임시 clone을 설치했다.
  임시 실행 코드 변경을 심은 경우 기본 설치가 거부하는 것도 통과했다. Ruff·diff·UTF-8 without BOM·LF 검사 통과.
- 다음 작업: 내부 공유 경로를 확정하고 팀원은 새 세션에서 직접 신뢰·자동 이벤트·질문 UI를 확인한다.
  push·공개 배포·T1~T8 구현은 하지 않았다.

저장 작업 `initial-commit`: 사용자 요청으로 저장소 전체 변경을 첫 커밋에 기록합니다.
입력·범위는 기존 staged 자료와 미추적 작업 문서·설정 전체이며 `.gitignore` 제외 대상은 유지합니다.
출력은 `master`의 초기 커밋입니다. 보관본 바이트 보존을 위해 `.gitattributes`에 해당 경로의 변환 제외를 적용합니다.
통과 조건은 스테이징된 보관본 해시 일치, 신규 작업 문서 검사, 커밋 후 작업 트리 변경 없음입니다.
실제 커밋 결과는 Git 이력으로 확인합니다.

문서 작업 `contest-archive` — 상태: 완료.
- 입력: 기존 `대회/`의 4개 파일, 배포 README, 현재 작업 문서.
- 출력: 원문 없이 사용할 수 있는 주제별 작업 문서, 절별 통합 대응표, 별도 보관본.
- 수정 범위: `docs/`, `README.md`, `AGENTS.md`, `.wiki/project.md`, `대회/` → `archive/contest/` 이동 및 보관 색인.
- 통과 조건: 원문 각 절·FAQ의 작업 문서 대응 확인, 이동 전후 4개 파일 SHA-256 일치,
  작업 읽기 경로의 보관본 의존 제거, 로컬 링크·UTF-8 without BOM·LF·위키 검사 통과.
- 보관본은 원문 바이트를 보존하고, 새로 작성·수정하는 작업 문서는 UTF-8 without BOM·LF로 저장합니다.
- 결과: `contest.md`에 평가·운영·배경을 통합하고 `data.md`의 파일·관측성·익명화·실행 안내를 보완했습니다.
  규칙 원문 전체 절·데이터 명세 §1~§9와 FAQ 16개·배경 전체 절의 통합 위치를 `sources.md`에 기록했습니다.
  원본 4개는 해시 일치, 작업 문서 17개·로컬 링크/앵커 188개·A/R/Q ID·정상 dev 112건 검사를 통과했습니다.
  기본 읽기 경로에 보관본 의존이 없고, 위키 동기화 후 문서 15개·고립 문서 0개, `repo_lint` 새 발견 없음입니다.
  `git diff --check` 통과. 문서 재구성 작업으로 실제 모델·유료 API·대회 제출은 실행하지 않았습니다.

문서 작업 `rule-usage`: `대회/` 원문을 입력으로 규칙의 적용 시점·허용 활용법·조건·출처를 정리합니다.
수정 범위는 `docs/rules.md`, `docs/workflow.md`, `docs/README.md`, `docs/design.md`, `docs/sources.md`,
`.wiki/project.md`, 이 작업 기록입니다. 출력은 AI의 규칙 판단 절차와 작업서의 규칙 판단 칸입니다.
통과 조건은 원문과 허용·금지 범위 대조, 기존 R-ID 보존, 좁혀진 Q2의 관련 문서 일치,
로컬 링크·인코딩·위키 포인터 검사입니다. 상태: 완료.
결과: 원문과 허용·금지 조건을 대조하고 A1~A10·R1~R22·Q1~Q3의 누락·중복,
로컬 링크·앵커·UTF-8 without BOM·LF를 검사했습니다. `대회/`·`open/` 원본 변경 없음과 `git diff --check` 통과를 확인했습니다.

별도 문서 작업 `items`: 제공 항목표를 입력으로 `docs/items.md`의 24항목 색인을 작성합니다.
수정 범위는 `docs/items.md`, `AGENTS.md`, `README.md`, `docs/README.md`, `.wiki/project.md`, 이 작업 기록입니다.
통과 조건은 v1~v24 누락·중복 없음, 공식 항목명·조문·비고·부재탐지 일치, 문서 링크·UTF-8 without BOM·LF 검사입니다.
상태: 완료. Python 표준 라이브러리 검사로 24개 ID·공식 항목명·조문·비고·부재탐지를 원본과 대조했고,
진입점·로컬 링크·UTF-8 without BOM·LF 검사와 `git diff --check`를 통과했습니다.
상세 판정 명세와 실제 조문 위치를 검증한 매핑은 T3에서 별도로 작성합니다.

T2는 done(구현·로컬 검증 완료)입니다. 사용자 지시에 따라 별도 독립 리뷰는 진행하지 않습니다([실행 기록](tasks/t2-score.md)).
T1은 사용자 보고로 서버 제출 실패를 확인했습니다. 재시도 실패 경로와 상세 원인 누락을 재현했으며, 실제 서버 응답·종료 사유는 미확인입니다([작업서](tasks/t1-baseline.md#2026-09-17-서버-실패-진단)).
후속 요청의 진단 기록·[Colab 실행 노트북](colab.md)·번들 준비와 로컬 검사는 완료했습니다. HF_TOKEN 필수·서버 무인자 실행/설정 일치 검사를 추가했습니다. 실제 GPU 성공은 미확인이고, 이번 독립 리뷰는 사용자 지시로 생략합니다.
Colab 기본 준비 경로에 git clone·실제 커밋 기록·제출 ZIP 자동 생성을 추가합니다. 특정 로컬 번들 업로드는 선택 경로로 유지합니다.
사용자 Colab 실행은 다운로드 성공 후 ninja PATH 누락으로 초기화 실패했습니다. 실행 환경을 보완했으며
수정 후 실제 GPU 재검증은 남아 있습니다([진단 기록](../reports/t1-baseline/colab-ninja-failure.md)).
후속 결과: `1c64604`는 A100 40GB에서 샘플/dev 210건 실제 성공, F1 0.2208013652894021.
사용자가 실행 안정성과 성능 둘 다 개선하도록 선택했습니다. 실패 공고 분할 재시도와
v10·v11·v13 법령/품목 조회 파일럿을 구현·로컬 검증하며, 새 후보의 Colab 재실행은 남아 있습니다.
실제 후속 `9363f21` 결과는 210건 실행 성공, F1 0.18470988076251235로 하락했습니다.
사용자 지시로 전체 프롬프트 주입은 철회하고 기본 24항목 호출 + 별도 3항목 판정으로 분리합니다.
같은 실행에서 두 CSV를 비교하며 새 후보의 성능 개선·서버 성공은 아직 미확인입니다.
`40e2cc6` 실제 실행은 성공했지만 F1 0.219538로 과거 기준선 미달입니다. 사용자 승인으로
품목 적용 범위·서비스 조회 누락·자격 문구 구분을 보완했고 로컬 22개 검사를 통과했습니다.
새 후보의 실제 Colab 검증은 대기 중입니다([작업서](tasks/t1-baseline.md)).
후속 57c78cf도 F1 0.211008로 실패했습니다. 출력 잘림 3건의 실제 분할 복구는 성공했습니다.
사용자 요청으로 영어 지시·한국어 법적 용어와 3항목 사실 검증을 구현했고 로컬 24개 검사를 통과했습니다.
목표는 기존 다운로드 품질 기준의 실제 통과이며 임계값을 낮추지 않습니다.
T3~T8은 미착수입니다. live·비용·실제 제출은 해당 접근·예산·제출 권한 확보 후 수행합니다.

| ID / 오너 | 입력 | 출력 | 수정 범위 | 통과 조건·선행 |
| --- | --- | --- | --- | --- |
| T1 / 통합 | `open/baseline/`, 두 노트북, `open/data/`, 서버 평가 명세 | 결함 보완 제출 후보·모델 조사·실행 기록 | `script.py`, `requirements.txt`, `tests/test_baseline.py`, `tools/package.py`, `docs/tasks/t1-baseline.md`, `docs/gemma4.md`, `reports/t1-baseline/`, `artifacts/baseline/`; 상태·출처 문서는 작업서 참조 | mock 10건·dev 형식 및 ZIP 검사, live 정상 호출·총시간 기록, 서버 점수. 제공 원본 보존 |
| T2 / 실험 | `open/dev_labels.csv`, 같은 ID의 예측 CSV | 24항목 metrics·오답 목록 | `tools/score.py`, `tests/test_score.py`, `docs/tasks/t2-score.md`, `reports/` | 정답=예측이면 F1=1; 전부 0이면 F1=0; ID 누락·중복·추가·값 오류 거부; 행 순서가 달라도 ID로 대응 |
| T3 / 명세 | 항목표·제공 법령, v05·v10·v24 | 일반·부재·메타 불일치 명세 3개와 매핑 | `specs/v05.md`, `specs/v10.md`, `specs/v24.md`, `rules/law_map.json`, `docs/tasks/t3-specs.md` | C3의 7칸, 조문 출처, v24 해당 없음, 사람 검토 기록. 외부 API는 Q1 확인 전 사용 안 함 |
| T4 / 라벨 | dev 입력 200건·검토 기준, 생성 후 dev 정답 대조 | 외부 모델별 라벨 기준선·비용·검토 계획 | `tools/label_bundle.py`, `tests/test_label_bundle.py`, `reports/label-compare/`, `docs/tasks/label-compare.md` | T2 필요. 입력에서 정답 제외, 실패·중복·재개 검증, 항목별 결과·모델/프롬프트 기록; 2만 건 선실행 금지 |
| T5 / 프롬프트 | T3 승인 명세 1개 | 버전 연결된 지시문 1개 | `tools/gen_prompt.py`, `prompts/v05.md`, `tests/test_prompt.py`, `docs/tasks/t5-prompt.md` | 승인되지 않은 명세 거부, 조건·예외·근거 규약 유지; 초기에는 템플릿 변환 |
| T6 / 통합 | T1 검증본·D4 계약 | 공고별 독립 추론 모듈 경계 | `script.py`, `pipeline/run.py`, `pipeline/output.py`, `tests/test_output.py`, `docs/tasks/t6-runtime.md` | T1 후. 기존 입출력 보존, 호출 실패·CSV 오류가 성공 처리되지 않음, mock/live 구분 |
| T7 / 프롬프트 | T2 채점기·T3 매핑·T5 지시문·T6 호출부 | 직접 매핑 후보와 문서 선택 후보를 각각 비교 | `pipeline/input.py`, `pipeline/retrieve.py`, `pipeline/prompt.py`, `prompts/queries.json`, `tests/test_input.py`, `tests/test_retrieve.py`, `docs/tasks/t7-retrieval.md`, `reports/` | 한 번에 하나씩 실험; 실제 토크나이저 예산, 관련 첨부·관측성 보존, 항목별 점수·총시간 기록 |
| T8 / 통합·실험 | 채택 후보·승인 자산·생성 이력 | 검증된 ZIP·재현 안내·제출 기록 | `tools/package.py`, `tests/test_package.py`, `docs/tasks/t8-release.md`, `reports/release/`, `artifacts/release/` | R1~R22·D4 게이트, allowlist ZIP, 네트워크 없는 live 실행, hash·재현 명령 |

테스트 파일은 의미 있는 동작을 구현할 때 생성합니다. 위 경로는 허용 범위이며 빈 파일 생성 지시가 아닙니다.
명세를 24개로 확대하거나 라벨 20,000건을 실행할 때는 파일럿 결과를 근거로 별도 작업서를 만듭니다.

## 지금 팀원에게 전달할 예

```text
T2 dev 채점기를 구현해 주세요.
먼저 AGENTS.md, docs/workflow.md, docs/data.md의 D4·D5, docs/contracts.md의 C5를 읽으세요.
입력은 정답 CSV와 예측 CSV이며 id로 대응하세요.
출력은 Macro F1, 24항목별 TP/FP/FN·precision·recall·F1·support와 오답 목록입니다.
수정은 T2 행에 적힌 파일만 허용합니다. open/ 원본은 수정하지 마세요.
T2 통과 조건을 실패 테스트로 먼저 확인하고 최소 구현 후 결과를 기록하세요.
모델이나 유료 API를 호출할 필요는 없습니다.
```
