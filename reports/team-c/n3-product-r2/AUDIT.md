# N3 r2 — 결과 감사 절차

만든 사람 C · 2026-09-26 · **회차 전에 고정됐다. 결과를 보고 고치지 않는다.**

## 0. 경로 규약

| 쓰는 말 | 무엇 |
| --- | --- |
| `<inbox>` | 받은 결과 ZIP 을 푼 곳 |
| `<run1>` · `<run2>` | 등록 뒤 `reports/runs/<run-id>/` |
| `<tmp>` | 아무 빈 작업 폴더 |

등록된 회차의 CSV 는 루트가 아니라 `<run>/dev/submission.csv` 다.

## 1. 등록과 바이트 재현 — 두 회차 각각

```bash
py -X utf8 tools/register_run.py --inbox <inbox> \
  --code-commit ea1d8ad24da754a2537e8ffcb998926b09f0d9bb

git show ea1d8ad24da754a2537e8ffcb998926b09f0d9bb:script.py > <tmp>/n3.py

py -X utf8 tools/replay_run.py --case <run1>/dev --script <tmp>/n3.py \
  --output-dir <tmp>/verify1 --verify
py -X utf8 tools/replay_run.py --case <run2>/dev --script <tmp>/n3.py \
  --output-dir <tmp>/verify2 --verify
```

`--verify` 가 통과해야 그 회차의 CSV 를 근거로 쓴다.

**받은 커밋을 확인한다.** `<run>/source.json` 의 `commit` 이
`ea1d8ad24da754a2537e8ffcb998926b09f0d9bb` 여야 한다. `main` 이면 N3 가 꺼진 회차다 —
버리고 다시 돌린다(실행 카드 §4).

## 2. 기준선을 만든다 — 같은 원응답 위에서

N3 는 **추가 호출을 늘리는 모델 앞 단계** 후보다. 그래서 같은 원응답 재생으로 효과를
떼는 것이 **부분적으로만** 된다 — 추가 호출의 응답 자체가 회차에만 있기 때문이다.

그럼에도 기준선은 같은 회차의 원응답 위에서 만든다. 후단 차이를 섞지 않기 위해서다.

```bash
git show de5b873:script.py > <tmp>/base.py      # N3 가 꺼진 현재 main

py -X utf8 tools/replay_run.py --case <run1>/dev --script <tmp>/base.py \
  --output-dir <tmp>/r1-base
```

**주의.** 이 재생은 `product` 단계의 응답을 **안 쓴다**(`PRODUCT_ITEMS` 가 비어 있으므로).
그래서 `<tmp>/r1-base` 는 "같은 모델 출력에서 N3 단계만 뺀" 판이고, N3 효과를 떼는 데
쓸 수 있다. 다만 그 단계가 baseline 판정 자체를 바꾸지는 않는지 §4 로 확인한다.

## 3. 대조

```bash
py -X utf8 tools/compare_runs.py --before <tmp>/r1-base/submission.csv \
  --after <run1>/dev/submission.csv --truth open/dev_labels.csv \
  --items v10,v11,v12 --output-dir <tmp>/r1-cmp
```

`--items` 는 **쉼표로** 구분한다. 공백은 거부된다.

N3 가 쓰는 키가 v10·v11·v12 셋이므로 그 셋만 대상으로 잡는다. 나머지 21항목이
`changed_cells_off_focus` 에 들어와 대상 밖 회귀를 잡는다.

## 4. 볼 것 — 회차 전에 정한다

| | 무엇 | 왜 |
| --- | --- | --- |
| **A** | v12 TP | 과거 실측에서 0→1 로 오른 유일한 항목 |
| **B** | v10·v11 의 **FP 증가** | 과거 실측 **+38**. 이것이 이 실험의 값을 정한다 |
| **C** | `changed_cells_off_focus` | 대상 밖 회귀. 정확히 0 이어야 한다 |
| **D** | 24항목 각각의 **TP 감소** | 합계가 아니다. 하나라도 줄면 금지선 |
| **E** | dev Macro | 기준선 대비. 과거 **+0.003788** |
| **F** | 두 회차의 **churn** | `<run1>/dev` ↔ `<run2>/dev`, 같은 코드 |
| **G** | `추론_s` | 서버 시간 추정의 입력 |

```bash
# F — 두 회차 churn. 같은 코드이므로 이것이 흔들림이다
py -X utf8 tools/compare_runs.py --before <run1>/dev/submission.csv \
  --after <run2>/dev/submission.csv --truth open/dev_labels.csv \
  --all --output-dir <tmp>/churn

# D — 항목별 TP 감소. 합계로 보면 상쇄돼 숨는다
py -X utf8 tools/score.py --truth open/dev_labels.csv \
  --pred <tmp>/r1-base/submission.csv --output-dir <tmp>/base-score
py -X utf8 tools/score.py --truth open/dev_labels.csv \
  --pred <run1>/dev/submission.csv --output-dir <tmp>/n3-score
py -X utf8 -c "import json;b=json.load(open(r'<tmp>/base-score/metrics.json',encoding='utf-8'))['items'];a=json.load(open(r'<tmp>/n3-score/metrics.json',encoding='utf-8'))['items'];lost=[(k,b[k]['tp'],a[k]['tp']) for k in b if a[k]['tp']<b[k]['tp']];print('TP 가 줄어든 항목:', lost or '없음')"
```

## 5. 판정 문장 틀 — 구조를 바꾸지 않는다

> N3(`PRODUCT_ITEMS = ["v10","v11","v12"]`)를 `de5b873` 위에서 두 회차 돌렸다.
> 기준선 대비 dev Macro **`___`**, v12 TP `___`→`___`, v10·v11 FP **+`___`**,
> 대상 밖 `___`셀. 두 회차의 churn 은 `___`셀 · Macro 차 `___` 다.
> 추가 호출로 서버 추정이 **`___`초**가 되어 한도 7,200초의 **`___`%** 다.

그리고 반드시 함께 적는다.

> 이 이득은 관측된 회차 변동폭(같은 코드 두 통과 0.034,
> `reports/team-c/c-variance/`)보다 **작다/크다**. 작으면 두 회차로도 확정하지 못한다.

## 6. 이 감사가 답하지 않는 것

- **서버 점수.** 회차는 서버가 아니다. 게다가 이 변경은 시간 한도를 넘는다.
- **채택 여부.** A 가 정한다.
- **v10·v11 의 FP 가 왜 느는지.** 카탈로그를 게이트로 안 쓰기 때문이라는 설명이
  `script.py:102` 에 있지만, 이 회차는 그것을 다시 묻지 않는다.
- **N1 과 함께 켰을 때.** 한 회차에 한 변수다. N1 은 별도다.
