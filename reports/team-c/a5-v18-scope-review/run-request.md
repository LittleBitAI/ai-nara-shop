# A5 v18 Colab 실행 안내

상태: **GPU 실행 준비 완료**. CPU 계약 33개 검증. 실제 후보 GPU 미실행.

- 실행 코드 `44f5e4b8c9a9d8b7b0e83b51f546c04be5e3316e` (`REPO_REF`).
- [고정 Colab 노트북](https://colab.research.google.com/github/LittleBitAI/ai-nara-shop/blob/dd99efacb80b645adecae689ebd62cb9cf99ed05/notebooks/colab-a5-v18-scope-review.ipynb).
- 노트북 커밋 `dd99efacb80b645adecae689ebd62cb9cf99ed05`.
  소스·검사·입력 명세 12개 파일은 실행 코드 커밋과 바이트 동일함을 확인했다.
  노트북은 해당 코드 커밋에서 `REPO_REF`만 고정한 사본이며 모든 코드 셀 컴파일을 통과했다.

## 입력 준비

PC의 `artifacts/a5-v18-scope-review/a5-v18-inputs.zip`을 Google Drive의
`내 드라이브/a5/a5-v18-inputs.zip`에 업로드한다.
입력 ZIP에는 [inputs.json](inputs.json)에 고정한 dev 200건·정답·제공 법령/고시·스키마와
H4 baseline/SME 보관 응답만 넣는다. 무라벨 전체 파일은 필요하지 않다.
노트북은 clone 후 누락 파일을 ZIP에서 복원하고 SHA256을 전부 검사한다.

## 실행

1. 노트북에서 A100 GPU를 선택하고 고정 Gemma 접근 권한의 `HF_TOKEN` 보안 비밀을 허용한다.
2. 회차 선택 셀(인덱스 5): `EPISODE=1`, `ATTEMPT="a"`. 위에서부터 실행한다.
3. 실행 셀(인덱스 13): control→v18 각 dev 200건. 단계별 상한 339.178초.
4. 마지막 ZIP 셀(인덱스 15)을 실행해 결과를 받는다. 실패해도 실행한다.
5. 회차 1 완료·시간 통과 후 런타임을 삭제하고 **새 A100 런타임**에서 같은 노트북,
   같은 ATTEMPT, `EPISODE=2`로 처음부터 실행한다. v18→control로 순서를 뒤집는다.

기존 패키지/모델/샘플링/문서·출력 예산을 사용한다. 설치·다운로드·모델 적재 시간은 별도다.
후보의 실제 시간은 미측정이며 과거 H3의 시간으로 새 후보 통과를 보장하지 않는다.

## 재실행·결과

Drive 결과: `MyDrive/a5/v18-scope-<코드 SHA 앞 12자리>-<ATTEMPT>/episode-1` 및 `episode-2`.
회차마다 `contract.json`, `run_report.json`, `run-record.md`, `summary.json`, `environment.json`,
군별 원응답·events·`off-hybrid.csv`/`on-hybrid.csv`·`*-score/`를 남긴다.
회차 2는 `repeat-<군>-<소비자>.json` 네 개를 남긴다.
결과 ZIP은 로컬 다운로드와 같은 Drive 상위 폴더에 `a5-v18-results-<시각>.zip`으로 보존한다.
실패 중간 events와 `.partial`도 ZIP에 넣는다.

기존 회차를 덮어쓰지 않는다. 실패 재시도는 ATTEMPT를 `b` 등으로 바꾸고 회차 1부터 실행한다.
회차 1 미완료·시간 초과·소스/입력/설정 불일치는 회차 2 실행을 막는다.
회차 2 모델 적재 후 GPU/추론 환경을 대조하고 불일치하면 추론 전에 멈춘다.
두 결과 ZIP을 전달하면 실제 시간·오답·scope 불일치 원문 감사부터 재개한다.
F1은 company 응답을 결합한 혼합 CPU 재생이며 전체 GPU/서버 점수는 아니다. 머지·제출하지 않는다.
