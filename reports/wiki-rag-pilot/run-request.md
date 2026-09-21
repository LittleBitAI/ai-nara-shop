# Wiki RAG v20 Colab 실행 안내

상태: **실행 전**. 준비물은 갖췄고 GPU 회차는 아직 한 번도 돌지 않았다.
[README](README.md)의 공통 예산 손실을 먼저 읽고 돌릴지 결정한다.

## 고정 코드

- 실행 코드 커밋 `a9fdd0a86c6c4b1f8c7021561169fddb60cc6223` (노트북의 `REPO_REF`).
- 고정 노트북 커밋 `629bf101fe4415b28f20b1ea6623590770335434`.
  노트북은 실행 코드 커밋에서 `REPO_REF` 한 줄만 바꾼 사본이며 모든 코드 셀 컴파일을 통과했다.
  Colab이 실제로 clone하는 것은 `REPO_REF`이고, 그 커밋의 실행 소스·자산·입력 명세는
  노트북 커밋과 바이트 동일하다. 두 커밋의 차이는 노트북·검사·기록 세 파일뿐이다.
- 분기점 `8afae99`. `origin/main`의 조상이지만 PR #81만큼 뒤에 있다.
  최신 main과의 동기화를 주장하지 않는다.
- [고정 Colab 노트북](https://colab.research.google.com/github/LittleBitAI/ai-nara-shop/blob/629bf101fe4415b28f20b1ea6623590770335434/notebooks/colab-wiki-rag-pilot.ipynb).

## 입력 준비

`reports/wiki-rag-pilot/inputs.json`의 30개 파일이 전부 저장소에 추적돼 있으므로
보통은 clone만으로 충분하다. 노트북은 빠진 파일이 있을 때만 Drive의
`내 드라이브/wiki-rag/wiki-rag-inputs.zip`에서 복원하고, 어느 경우든 30개 SHA256을 모두 검사한다.
무라벨 20,000건 파일은 필요하지 않다.

## 실행

1. A100 GPU를 선택하고 고정 Gemma 접근 권한의 `HF_TOKEN` 보안 비밀을 허용한다.
2. 회차 선택 셀(인덱스 5): `EPISODE=1`, `ATTEMPT="a"`. 위에서부터 실행한다.
3. 실행 셀(인덱스 13): `control → raw → wiki` 각 dev 200건, 총 600응답.
   추론 전에 실행기가 세 군 공통 문서 예산을 실제 토크나이저로 고정하고 `budget.json`에 남긴다.
   최소 예산에서도 초과하면 모델을 부르지 않고 멈춘다. 단계 상한은 군별 339.178초/200건이다.
4. 마지막 ZIP 셀(인덱스 15)을 실행해 결과를 받는다. **실패해도 실행한다.**
5. 회차 1 완료·시간 통과 후 런타임을 삭제하고 **새 A100 런타임**에서 같은 노트북,
   같은 `ATTEMPT`, `EPISODE=2`로 처음부터 실행한다. 순서가 `wiki → raw → control`로 뒤집힌다.

기존 패키지/모델/샘플링/출력 예산을 그대로 쓴다. 설치·다운로드·모델 적재 시간은 별도다.
역순은 순서 영향 완화이며 완전한 통계적 통제가 아니다.

## 결과

Drive: `MyDrive/wiki-rag/v20-page-<코드 SHA 앞 12자리>-<ATTEMPT>/episode-1` 및 `episode-2`.
회차마다 `contract.json`, `run_report.json`, `run-record.md`, `summary.json`,
`environment.json`, `budget.json`, 군별 원응답·events·`<군>-hybrid.csv`·`score/`·
`verification.json`, 군 간 비교 3개를 남긴다. 회차 2는 `repeat-<군>.json` 3개를 더 남긴다.
결과 ZIP은 로컬 다운로드와 같은 Drive 상위 폴더에 `wiki-rag-results-<시각>.zip`으로 보존한다.
실패 중간 events와 `.partial`도 ZIP에 넣는다.

기존 회차를 덮어쓰지 않는다. 실패 재시도는 `ATTEMPT`를 `b` 등으로 바꾸고 회차 1부터 실행한다.
회차 1 미완료·시간 초과·소스/자산/입력/설정 불일치는 회차 2 실행을 막는다.
회차 2는 모델 적재 후 GPU 환경과 공고별 문서 예산을 대조하고 다르면 추론 전에 멈춘다.

두 결과 ZIP을 전달하면 예산 손실·군별 사실·바뀐 v20 판정의 원문 감사부터 재개한다.
F1은 company 응답만 새로 받은 혼합 CPU 재생이며 전체 GPU·서버 점수가 아니다.
머지·제출하지 않는다.
