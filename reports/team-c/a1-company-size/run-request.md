# A1 실제 회차 실행 요청

상태: A1 전용 브랜치의 Colab 검증 후보. 실제 모델 실행·서버 제출 전.
아래 작업은 고정 모델을 실행할 Colab/A100급 환경에서 수행한다.

## 커밋된 후보로 실행 — 권장

1. `LittleBitAI/a1-company-size-v14` 브랜치의 `notebooks/colab-baseline.ipynb`를
   Colab에서 새로 연다. 이미 열어 둔 main/회차 A 사본은 사용하지 않는다.
2. 첫 설정 셀에서 `SOURCE_MODE="clone"`은 그대로 두고, `REPO_REF`만 실행할 A1 커밋 SHA로
   바꾼다. 최초 실행은 위 브랜치 이름도 가능하지만 반복 실행은 `source.json`의 SHA로 고정한다.
3. Colab GPU 런타임(A100 권장)과 `HF_TOKEN` secret 접근을 확인하고 위에서 아래로 실행한다.
   `RUN_DIAGNOSTIC=True`, `DIAGNOSE_ITEMS=""`는 기본값 그대로다.
   `script.py` 인자·seed·토큰 예산·양자화는 바꾸지 않는다. A1 v14~v18은 이미 켜져 있고
   N1·N3는 꺼져 있다. `main`이나 회차 A 전체를 병합한 후보가 아니라 기존 A1 기준선의 단독 실험이다.
4. 마지막 결과 ZIP을 받는다. 품질 게이트 통과 시 내려오는 제출 ZIP도 함께 보관한다.
   품질 게이트 미통과여도 마지막 로그 수집 셀을 실행해 실패/미개선 결과를 남긴다.
5. 이 기본 노트북 실행은 sample 10건·dev 200건·dev-debug 200건까지다.
   무라벨 6,000건은 자동 실행하지 않는다. 아래 카나리 절차가 별도로 필요하다.

채택 후보의 반복은 첫 회차의 제출 ZIP을 그대로 재사용한다. clone으로 재생성했다면 두 ZIP의
SHA-256이 같은지 먼저 확인한다. 실행 중 브랜치가 움직여도 고정 커밋을 바꾸지 않는다.

## dev 회차

1. `artifacts/a1-company-size/7e5b8565/colab-bundle.zip`을 사용한다.
   같은 폴더의 `colab-baseline.ipynb` 사본을 Colab에서 열고
   `SOURCE_MODE="upload"`로 이 번들을 선택한다.
   이 사본은 `6433a75`의 추가 호출 보호 열 수정을 A1에 반영한 판본이다.
   노트북은 clone/upload ZIP으로 교체되지 않는다. 이미 열어 둔 구판을 실행하지 않는다.
   `REPO_REF="main"` clone은 이 후보를 실행하지 않는다.
2. 고정 리비전/양자화로 샘플·dev를 실행한다. 진단 셀은 `RUN_DIAGNOSTIC=True`,
   `DIAGNOSE_ITEMS=""`가 기본이다. 갱신된 노트북을 사용하고 별도 구식 진단 가설은 섞지 않는다.
3. 마지막 결과 ZIP과 실제로 실행한 submit.zip을 받는다. `quality_pass`는 채택 근거가 아니다.
4. 원응답·회차 코드를 보존한 뒤 아래 대조를 실행한다. `dev-debug`가 실제로 쓴 제출 코드를
   `--script`로 지정하고, 재생이 그 회차 CSV와 같은지 확인한다.

```powershell
python -X utf8 tools/replay_run.py --case <dev-debug> --script <실행한-script.py> --verify
python -X utf8 tools/compare_runs.py --items v14,v15,v16,v17,v18 `
  --before <dev-debug>/company_size_baseline_submission.csv `
  --after <dev-debug>/submission.csv --output-dir <새-A1-전후-대조>
python -X utf8 tools/compare_runs.py --items v14,v15,v16,v17,v18 `
  --before reports/runs/colab-1789716500947261692/dev/submission.csv `
  --after <dev-debug>/submission.csv --output-dir <새-과거회차-대조>
```

첫 비교는 A1만의 효과이며 대상 밖 19항목 변화가 0셀이어야 한다.
둘째 비교에는 회차 churn이 섞이므로 항목별 TP/FP/FN을 본다.
v14·v15 첫 TP, v17 TP≥3/FP≤10을 먼저 확인하고 v16·v18 첫 TP와 보류 사유도 보고한다.
실패/미확인 사실을 0으로 강제하거나 예산·재시도를 같이 늘리지 않는다.

## 채택 후보의 동일 ZIP 재실행 — 필수

2026-09-20부터 Colab 회차 횟수 제한이 없다. 첫 실행이 채택 후보이면 같은 날 같은
업로드 번들·제출 ZIP을 그대로 한 번 더 실행한다. 재패키징·코드 수정 없이 새 작업 폴더에서
시작하고 `RUN_DIAGNOSTIC=True`로 두 번째 원응답을 보존한다.
단일 실행에서 나온 `dev`와 `dev-debug`만으로 이 별도 재실행 절차를 대신하지 않는다.

두 회차의 `submit.zip` SHA-256이 아래 후보 해시와 모두 같은지 먼저 확인한다.
이어 각 `run_report.json`의 `code_sha256`, `records_sha256`, 고정 모델 리비전,
양자화·seed·temperature·thinking·문서/토큰 예산·chunk 및 환경 기록을 대조한다.
조건이 다르면 같은 코드 churn 실측 쌍으로 세지 않는다.

```powershell
Get-FileHash <1회차-submit.zip>,<2회차-submit.zip> -Algorithm SHA256
python -X utf8 tools/compare_runs.py --items v14,v15,v16,v17,v18 --all `
  --before <1회차-dev-debug>/submission.csv `
  --after <2회차-dev-debug>/submission.csv --output-dir <새-동일ZIP-churn>
```

두 회차 모두 앞 절의 A1 적용 전/후 비교를 수행한다. 대상 TP/FP/FN의 회복이 반복되는지,
4,800셀 중 어느 공고·항목이 바뀌는지, 대상 밖 변화와 Macro F1 차이가 얼마인지 함께 남긴다.
과거 열한 쌍의 29~45셀 / 0.000008~0.004689는 이 후보의 허용선이 아니다.
도구의 `drift_reference`도 과거 참고치다. 이번 두 회차의 `changed_cells`, 항목별 `flipped`,
`macro_f1.delta`가 현재 코드에서 직접 관측한 값이며 이 한 쌍도 보편적인 상한은 아니다.

한 회차 한 가설·정답 dev 200건은 유지한다. Colab 회차 확대는 제출 하루 1회와
서버 7,200초를 바꾸지 않는다. 여유 2,919초, 추가 전건 한 단계 약 1,618초는 계획용이며
A1의 서버 목표 6,000초도 그대로다. Colab 반복 합산 시간을 서버 한 회차 시간과 혼동하지 않는다.

## 무라벨 발화율 카나리

개발 회차와 동일 코드·모델·설정으로 제공 `train_unlabeled.jsonl`의 앞 6,000건을 실행한다.
해당 원본은 기본 Colab 번들에 들어 있지 않으므로 제공 파일을 별도로 준비해야 한다.
이 명령은 전건 파이프라인을 재사용하여 모든 공고의 기본 판정과 추가 추출을 함께 보관한다.
6,000건은 dev 회차보다 상당히 긴 별도 GPU 작업이며 서버 제출이 아니다.

```powershell
python -X utf8 script.py --input open/train_unlabeled.jsonl --limit 6000 `
  --data-dir open/data --model-dir <고정모델-로컬경로> --debug-responses `
  --output-dir <새-무라벨-출력>
python -X utf8 tools/company_size_canary.py --dev-case <dev-debug> `
  --unlabeled-case <새-무라벨-출력> --output <새-발화율-보고서.json>
```

카나리 도구·`compare_runs.py`·현재 `script.py`·제공 입력이 있는 작업트리에서 마지막 명령을
실행한다. 무라벨이 다른 폴더에 있으면 `--unlabeled-input`을 지정한다. 새 보고서는
추출 결정표의 발화율과 최종 CSV 양성 수를 구분하며, dev 발화가 0이면 배율은 null이다.
mock·API 결과는 실제 카나리로 받지 않는다. 카나리 배율만으로 자동 채택/반려하지 않는다.
이 요건은 첫 추출 후보뿐 아니라 dev 재생에서 나온 기업등급 결정표 수정에도 적용한다(W5).
그때도 같은 후보 규칙을 dev·무라벨 6,000건의 보관 사실에 적용한 발화율을 보고해야 한다.
무라벨 사실이 없으면 아직 검사할 수 없다. dev 개선이나 금액 분포만으로 통과 처리하지 않는다.

## 등록·채택에 남은 조건

실제로 실행한 코드 커밋과 결과/제출 ZIP 한 쌍으로 회차를 등록한다.
`source.json`의 A1 커밋을 사용하며, 작업 시작 기준 커밋 `ae5e2ef`를 후보 커밋으로 등록하면 안 된다.

후보 script SHA-256: `7e5b85652e9c9f98c111f2e73dfad73213150ded69fa171bc22ebb85920e26cd`.
제출 ZIP SHA-256: `cc904a30f76ade75a5d3a074ce240cd7783f6f6bd117002dc62ecdd7b8940165`.
노트북 SHA-256: `559b664228af979d4872e5023ddbb42437dcdc41fee53ab39555fa12d19c1df0`.
`683d056e`와 루트의 이전 로컬 ZIP은 실행 대상에서 제외한다. 삭제하지 않고 이력으로 보존한다.
이전 ZIP에는 `extra_call_items` 보고서 필드가 없어 새 노트북만 열어도 A1 열 변경 검사가 실패한다.

```powershell
python -X utf8 tools/register_run.py --inbox artifacts/inbox --code-commit <후보코드-커밋>
```

원응답·dev 지표·무라벨 배율·시간을 A1 보고서에 추가한다. 서버 총시간 6,000초 이하는
실제 서버 실행으로 별도 확인한다. 이 문서는 제출 승인이나 성공 기록이 아니다.
동일 ZIP의 두 결과는 각각 새 inbox 디렉터리에서 등록하고 두 run ID를 churn 비교에 연결한다.
