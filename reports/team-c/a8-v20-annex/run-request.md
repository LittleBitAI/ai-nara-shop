# A8 v20 별표 주입 Colab 실행 안내

상태: **GPU 미실행.** 두 회차를 실행하면 결과 ZIP 두 개를 받아 감사한다.
후보는 프롬프트만 바꾸며 채택 결정이 아니다. [보고서](README.md)가 준비 근거를 소유한다.

- 실행 코드 `<구현 커밋 40자리 SHA>` (노트북 `REPO_REF`). 커밋 후 이 줄과 노트북을 함께 고정한다.
- 노트북 [`notebooks/colab-a8-v20-annex.ipynb`](../../../notebooks/colab-a8-v20-annex.ipynb).
  `REPO_REF`가 40자리 16진수가 아니면 clone 전에 멈춘다.
- 모델은 고정 리비전 `4d7ae4984b7db7de8f8457170b3f1a419ee76d52`, Python 3.12.13 · vLLM 0.26.0 · CUDA 13.0.

## 입력 준비

PC의 `artifacts/a8-v20-annex/a8-v20-inputs.zip`(30개 파일, 3,264,446바이트)을
Google Drive의 `내 드라이브/a8/a8-v20-inputs.zip`에 업로드한다.
ZIP에는 [inputs.json](inputs.json)에 고정한 dev 200건·정답·제공 법령/고시·스키마와
H4 baseline/SME 보관 응답만 있다. 무라벨 20,000건 파일은 필요하지 않다.
주입 대상인 「중소 소프트웨어사업자의 사업 참여 지원에 관한 지침」 원문도 같은 명세로 검사한다.
노트북은 clone 후 누락 파일을 ZIP에서 복원하고 모든 SHA256을 검사한다.

## 실행

1. A100 GPU를 선택하고 고정 Gemma 접근 권한의 `HF_TOKEN` 보안 비밀을 허용한다.
2. 셀 1의 `REPO_REF`를 위의 40자리 SHA로 바꾼다.
3. 회차 선택 셀(인덱스 5): `EPISODE=1`, `ATTEMPT="a"`. 위에서부터 실행한다.
4. 실행 셀(인덱스 13): 실행기가 **생성 호출 전에** 예산을 재고 `budget.json`을 남긴다.
   추가 축소가 1건이라도 있으면 거기서 멈춘다 — 그때도 ZIP 셀을 실행해 `budget.json`을 보낸다.
   통과하면 control→a8 각 dev 200건. 군별 단계 상한 **339.178초/200건**이다.
5. 마지막 ZIP 셀(인덱스 15)을 실행해 결과를 받는다. **실패해도 실행한다.**
6. 회차 1 완료·시간 통과 후 런타임을 삭제하고 **새 A100 런타임**에서 같은 노트북,
   같은 ATTEMPT, `EPISODE=2`로 처음부터 실행한다. a8→control로 순서를 뒤집는다.

기존 패키지·모델·샘플링·문서/출력 예산을 그대로 쓴다. 설치·다운로드·적재 시간은 단계 시간과 별개다.
후보의 실제 시간은 미측정이며 과거 후보의 시간으로 통과를 보장하지 않는다.

## 결과와 재실행

Drive 결과: `MyDrive/a8/v20-annex-<코드 SHA 앞 12자리>-<ATTEMPT>/episode-1`, `episode-2`.
회차마다 `contract.json`, `budget.json`, `run_report.json`, `run-record.md`, `summary.json`,
`environment.json`, 군별 원응답·events·`off-hybrid.csv`/`on-hybrid.csv`·`*-score/`를 남긴다.
회차 2는 `repeat-<군>-<소비자>.json` 네 개를 더 남긴다.
결과 ZIP은 로컬 다운로드와 같은 Drive 상위 폴더에 `a8-v20-results-<시각>.zip`으로 보존한다.
실패 중간 events와 `.partial`도 ZIP에 들어간다.

기존 회차를 덮어쓰지 않는다. 실패 재시도는 ATTEMPT를 `b` 등으로 바꾸고 회차 1부터 실행한다.
회차 1 미완료·시간 초과·소스/입력/설정 불일치는 회차 2를 막는다.
회차 2는 모델 적재 후 GPU·추론 환경을 대조하고 불일치하면 추론 전에 멈춘다.

후보는 소비자를 바꾸지 않으므로 같은 군의 OFF/ON 재생은 24항목 CSV가 바이트까지 같아야 한다.
달라지면 배선 회귀이며 성능 해석보다 먼저 본다.
F1은 company 응답 + 보관 기본/SME 응답의 **혼합 CPU 재생**이다. 전체 GPU·서버 점수가 아니다.
두 회차 ZIP을 받으면 실제 시간·오답·24항목 churn 감사부터 재개한다. 머지·제출하지 않는다.
