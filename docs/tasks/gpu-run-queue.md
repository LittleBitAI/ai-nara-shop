# GPU 회차 대기열 — 무엇을 돌릴지 정한다

2026-09-18 작성. 2026-09-20 갱신: 회차 횟수 제한이 없어졌다.
사용자가 9/18에 알려 온 "GPU 회차 12번"은 그날까지의 사정이고, 오늘부터는 횟수가 풀렸다.
이 문서는 무엇을 어떤 순서로 돌릴지와 각 회차의 정확한 셀 변경을 적는다. 실행은 사람이 한다.

횟수가 풀려서 바뀌는 것은 하나다 — 이제 회차를 아끼지 않는다. 아래 §3의 R2(같은 코드로
한 번 더)처럼 "회차가 귀해서 못 하던 것"이 전부 가능해졌다. 같은 코드 두 번 돌려
churn을 재고 그 위에서 효과를 읽는 것이 예외가 아니라 기본이 된다.
`RUN_DIAGNOSTIC = True`(원응답 보관, 15분 추가)도 이제 망설일 이유가 없다.

병목은 그대로다. 늘어난 것은 회차뿐이고 제출은 여전히 하루 1회,
서버 실행 시간은 여전히 7,200초, 라벨은 여전히 dev 200건이다. §0을 보라.

---

# 실행 카드 — 돌리는 사람은 여기만 보면 된다

## 용어 두 개부터

| | 무엇 | 몇 번 |
| --- | --- | --- |
| GPU 회차 | Colab에서 노트북 돌리기. 연습·실험이다 | 제한 없음 (2026-09-20~) |
| 대회 제출 | 대회 사이트에 ZIP 올리기. 진짜 점수다 | 하루 1번 · 9/29 10:00까지 약 10번 |

회차는 연습이고 제출이 진짜다. 회차가 무제한이어도 서버 점수는 하루 한 번만 는다.
노트북이 하는 일은 여기까지다.

```
GitHub에서 코드 받아옴 → 모델 돌림 → 점수 냄 → submit.zip 뱉음
```

그 `submit.zip`을 사람이 대회 사이트에 올려야 제출이 된다. 노트북은 거기까지 안 간다.

## 준비 (한 번만)

Colab 왼쪽 열쇠 아이콘 → `HF_TOKEN` 등록 → 노트북 접근 허용을 켠다.
없으면 모델 다운로드 셀에서 멈춘다.

## 회차 A — 지금 코드 그대로

노트북(`notebooks/colab-baseline.ipynb`)을 열고 위에서부터 전부 실행한다.
아무것도 안 고친다. `REPO_REF = "main"` 이 최신 코드를 알아서 받아 온다.

나오는 것: 지금 코드의 실제 GPU 점수와 `submit.zip`. 이게 제출 후보다.

`RUN_DIAGNOSTIC` 은 이제 기본이 `True` 다(회차 제한이 없어졌다). 셀 18 을 안 건드려도
원응답이 보관되고, 그래야 그 프롬프트의 후처리 후보가 전부 GPU 0초가 된다.

### main 이 아닌 커밋을 돌릴 때 — 브랜치 이름 말고 SHA 를 쓴다

```python
# 셀 1 — 이 줄만 바꾼다
REPO_REF = "<40자리 커밋 SHA>"
```

브랜치는 움직인다. SHA 를 쓰면 그 회차가 무엇을 돌렸는지가 고정된다 —
`source.json` 의 `requested_ref` 와 `commit` 이 같아진다. 한 번 어긋나서 등록이
`코드 커밋이 로그와 다르다` 로 막힌 적이 있다.

### 돌리기 전에 GPU 없이 밟아 볼 수 있는 것

회차 하나를 날리기 전에 죽을 자리를 먼저 밟는다. 넷 다 로컬에서 몇 초다.

```powershell
# ① 셀 3 이 하는 일 그대로 — clone · fetch · checkout · package
git clone --depth 1 --branch main https://github.com/LittleBitAI/ai-nara-shop.git repo
git -C repo fetch --depth 1 origin <SHA>; git -C repo checkout --detach FETCH_HEAD
cd repo; python -X utf8 tools/package.py --output ..\submit.zip

# ② dev 200건 mock — 49열·자가검증과 함께, 기본/최종 CSV 가 허용 밖 열을 바꾸는지 본다
python -X utf8 script.py --mock --input open/dev.jsonl
```

②가 특히 중요하다. `check_live` 는 `settings["extra_call_items"]` 로 무엇이 갈려도
되는지를 정하는데, `postprocess` 안의 규칙은 기본 CSV 와 최종 CSV 양쪽에 들어가므로
차이를 안 만든다. 그 전제가 깨지면 회차가 샘플 10건에서 죽는다 — 아래 절의 사고가 그것이다.
두 CSV 를 열 단위로 대조해 허용 밖 변경이 0 인지 확인하고 돌린다.

### 노트북은 clone 대상이 아니다 — 열어 둔 사본이 돈다

`REPO_REF` 가 받아 오는 것은 `script.py` 뿐이다. 노트북 자체는 당신이 Colab 에서 연
그 사본이 그대로 돈다. 저장소의 노트북을 고쳐도 열어 둔 탭에는 안 온다.

그래서 노트북의 검사가 낡으면 코드를 아무리 고쳐도 같은 자리에서 죽는다. 실제로 그랬다 —
`check_live` 가 "두 CSV 는 v13/e13 에서만 갈릴 수 있다"고 단언했는데 N1 이 main 에 들어오면서
그 단언이 깨졌고, 회차가 샘플 10건에서 `RuntimeError` 로 멈췄다. mock 에서는 재현되지
않아 로컬 검사 178개가 전부 초록이었다.

회차를 돌리기 전에 노트북을 그 커밋 판본으로 다시 연다. 커밋을 지정해 열면 확실하다.

```
https://colab.research.google.com/github/LittleBitAI/ai-nara-shop/blob/<커밋>/notebooks/colab-baseline.ipynb
```

## 회차 N1 · N2 · N3 — 실험 노트북은 쓰지 않는다 (2026-09-25)

`notebooks/exp-n1-absence-split.ipynb` · `exp-n2-amount-band.ipynb` · `exp-n3-competitive-product.ipynb` 는
9/18 판이라 지금 코드와 맞지 않는다. 돌리지 않는다.

- 셋 다 `EXP_ITEMS` 로 `BAND_ITEMS` 를 덮는다. N1·N3 은 `[]` 로 기업규모 결정(v14~v18)을 통째로 끄고,
  N2 는 v14·v15·v17 만 남겨 v16·v18 을 뺀다. 점수의 큰 몫을 끈 채로 재는 것이다.
- 노트북의 `check_live` 가 v13 과 실험 항목만 바뀌어도 된다고 단언한다. 기업규모 단계가 켜진 지금 코드에서는
  샘플 10건에서 멈춘다. `colab-baseline.ipynb` 의 `check_live` 는 `extra_call_items` 로 허용 항목을 읽어 이 문제가 없다.

실험은 `run/` 브랜치에 커밋 둘로 만든다.

1. 코드 커밋 — `script.py` 에서 한 줄(`SPLIT_ITEMS` 또는 `PRODUCT_ITEMS`)만 켠다.
2. 링크 커밋 — `notebooks/colab-baseline.ipynb` 셀 1 의 `REPO_REF` 를 코드 커밋의 40자리 SHA 로 바꾼다.

노트북은 링크의 커밋과 무관하게 `REPO_REF` 를 clone 한다. 코드 커밋에서 연 노트북은 `REPO_REF = "main"` 그대로라
실험이 꺼진 `main` 을 돈다. 링크는 반드시 링크 커밋(브랜치 끝)으로 연다. 링크 커밋이 없으면 셀 1 의 `REPO_REF` 를
코드 커밋 SHA 로 손으로 바꾼 뒤 돌린다.
판정은 같은 날 기준 회차와 `tools/compare_runs.py` 로, 규칙 효과는 원응답 재생으로 뗀다.

| 실험 | 회차 브랜치 | 켜는 줄 | 코드 커밋 | 링크 커밋 | 추가 호출(dev 200건) |
| --- | --- | --- | --- | --- | ---: |
| N1 부재 분할 | `run/a-n1-split` | `SPLIT_ITEMS = ["v16", "v18"]` | `a29f680` | `684dbad` | 155 |
| N3 경쟁제품 | `run/a-n3-product` | `PRODUCT_ITEMS = ["v10", "v11", "v12"]` | `2a5a38c` | `d808922` | 200 |

링크 형식은 `https://colab.research.google.com/github/LittleBitAI/ai-nara-shop/blob/<링크 커밋 40자리>/notebooks/colab-baseline.ipynb` 다.

기업규모 단계가 뒤에 돌아 그 항목을 정하면 실험 단계의 답을 덮는다. 그래서 두 실험은 기업규모가 못 정한
자리에서만 효과가 난다. 추가 호출만큼 서버 시간이 늘어 지금(추정 6,472~6,675초)으로는 이겨도 그대로 싣지 못한다.

## 걸려 넘어지는 자리 둘

1. 항상 첫 셀부터 실행한다. 중간 셀만 누르면 앞 셀이 만든 이름이 없어 에러가 난다.
2. 점수가 기준에 못 미치면 `submit.zip` 을 안 준다. 노트북에 그 조건이 걸려 있다
   (아래 「품질 게이트」 참조). 결과 ZIP 은 받아지고 제출용 ZIP 만 안 나온다.
   고장이 아니다.

## 끝나면

결과 ZIP 한 쌍(`colab-results-<숫자>.zip`, `submit.zip`)을 받아 `artifacts/inbox/` 에 둔다.
등록·분석은 도구가 한다 — 손으로 표를 고치지 않는다.

```powershell
python -X utf8 tools/register_run.py --inbox artifacts/inbox --code-commit <커밋>
```

## 품질 게이트 — ZIP 을 안 주는 조건

```python
quality_pass = metrics["macro_f1"] > paired_metrics["macro_f1"] and metrics["macro_f1"] >= 0.2208013652894021
if quality_pass:
    files.download(submit.zip)
```

고정 기준선 `0.2208` 은 지금 코드(dev 0.3609)에 여유가 크다. 걸리는 쪽은 앞 조건 —
같은 회차 안의 기본 판정보다 나아야 한다. 그 차이는 v13 재검증 기여 약 +0.0033 이고,
회차 churn 이 0.000008~0.004689 이므로 잡음만으로 뒤집힐 수 있다.
실제로 같은 `script.py` 가 한 번은 `+0.00000477` 로 통과하고 한 번은 `−0.000577` 로 떨어졌다.

---

아래는 회차 배분의 근거다. 돌리는 데는 필요 없다.

회차별 결과 등록은 [실행 기록](../runs.md), 후처리 후보 측정은
[업무 분배 §0](team-handoff.md)의 명령 블록이 소유한다. 이 문서는 무엇을 돌릴지만 정한다.

## 0. 회차 제한이 풀려도 병목은 그대로다

| 자원 | 남은 것 | 회차가 무제한이면 풀리나 |
| --- | --- | --- |
| GPU 회차 | 제한 없음 (2026-09-20~) | — |
| 대회 제출 | 하루 1회 · 9/29 10:00까지 약 10회 | 아니오 |
| 서버 실행 시간 | 한도 7,200초 중 여유 2,919초 | 아니오 |
| 라벨 | `open/dev_labels.csv` 200건이 전부 | 아니오 |

GPU를 몇 번 돌려도 정답은 안 늘어난다. dev 밖의 일반화를 재는 채널은 제출 하나뿐이고
하루 1회다. 그러므로 회차는 *가설을 가르는 데* 쓰고, 일반화 확인은 *매일 제출로* 쌓는다.

회차가 싸졌으니 회차로 살 수 있는 것부터 산다. 셋이다.

1. 같은 코드 두 번. 그 차이가 그날 그 코드의 churn이고, 효과는 그 위에서만 읽힌다.
   지금 churn 기준(4,800셀 중 29~45개, Macro F1 0.000008~0.004689)은 과거 열한 쌍의 값이다.
2. 한 회차에 한 변수. 두 변수를 묶어 돌리면 회차를 아낀 것이 아니라 답을 잃는 것이다 —
   부재탐지에서 이미 한 번 그랬고 재현율 13/18 → 3/18의 원인을 아직 못 가른다.
3. 원응답을 매번 보관한다. `RUN_DIAGNOSTIC = True`. 그 회차 프롬프트의 후처리 후보가
   전부 GPU 0초가 된다. 프롬프트를 바꾸면 이전 원응답은 못 쓴다.

회차가 무제한이어도 dev 200건에 맞추는 것은 여전히 위험하다. dev 이득의 실측 전이율은
50.8%다([submissions.json](../../reports/submissions.json)). 회차를 많이 돌릴수록
dev에 맞출 기회도 늘어난다 — 새 규칙은 `open/train_unlabeled.jsonl` 발화율로 함께 확인한다.

## 1. 회차 하나에 세 가지를 담는다

노트북 셀 18은 서로 독립된 `if` 블록 둘이다. 기본 흐름(셀 14)의 dev 200건 실행까지
합치면 한 세션에서 셋이 같이 나온다.

| 나오는 것 | 스위치 | 값어치 |
| --- | --- | --- |
| dev 200건 판정·점수 | 기본 흐름 | 그 코드의 실측 |
| 원응답 보관 | `RUN_DIAGNOSTIC = True` | 이게 핵심이다 ↓ |
| 항목별 막힌 단계 | `DIAGNOSE_ITEMS = "..."` | 0점 항목의 원인 |

원응답을 받아 두면 그 프롬프트의 후처리 후보가 전부 공짜가 된다. `tools/replay_run.py`가
dev 200건을 0.6초에 재생하고 회차 churn이 없다. 지금 보관된 원응답은 `b113425`의 것이라
프롬프트를 바꾸는 순간 못 쓴다 — 바꾼 회차에서 새로 받아야 한다.

원응답은 모델 로드 포함 15분 안팎을 더 쓴다. 회차 제한이 없어졌으니 망설일 이유가 없다 —
이제 기본으로 켠다.

## 2. R1 — 회차① + v14·v15·v17 진단 (1회차) — 끝났다. 반려.

> 실측 ([colab-1789719173182820657](../runs.md), 커밋 `99ebbf1`):
> 근거문구를 풀자 v16·v18에 TP가 실제로 섰다 (각 1건, 그전엔 둘 다 0).
> 그런데 Macro F1 은 같은 날 회차 A 의 0.371978 에서 0.333464 로 내려갔다.
> 두 항목이 얻은 것보다 나머지 22항목이 잃은 것이 컸다 — 24항목 합동 호출이라
> 한 항목의 지시를 바꾸면 나머지 23개가 같이 움직인다는 첫 실측이다.
> 그래서 아래 §4 의 갈림길 중 어느 칸도 맞지 않았다 — "TP 가 섰다"와
> "Macro 가 내려갔다"가 같이 일어났다. 다음 수는 합동 호출을 건드리지 않고
> 따로 묻는 것이고 그것이 N1 이다.
>
> 코드는 브랜치가 아니라 `reports/team-c/c3-amount-gate/round1-unlock-absence-evidence.diff`
> 가 보관한다. 아래 절차는 그 회차를 재현할 때만 쓴다.

한 세션에서 돌린다. 두 측정은 서로 다른 항목을 보므로 섞이지 않는다.

### 코드

`reports/team-c/c3-amount-gate/round1-unlock-absence-evidence.diff`를 적용한 `script.py`로
제출 ZIP을 만든다. 이 diff는 추가 호출 0·추가 시간 0초다 — 24항목 합동 호출은 그대로 두고
부재탐지 5항목의 `근거문구`가 `{"type": "null"}`로 고정된 것만 푼다(238·253·296행).

```powershell
git apply --check reports/team-c/c3-amount-gate/round1-unlock-absence-evidence.diff
git apply       reports/team-c/c3-amount-gate/round1-unlock-absence-evidence.diff
python -X utf8 tools/package.py --output artifacts/round1/submit.zip
```

### 노트북 — 셀 18에서 두 줄

```python
RUN_DIAGNOSTIC = True                 # 원응답을 받는다. 다음 후처리 후보가 전부 공짜가 된다
DIAGNOSE_ITEMS = "v14,v15,v17"        # C의 승인된 요청 (reports/team-c/c5-v14-v15/RUN-REQUEST.md)
```

`DIAGNOSE_IDS`는 빈 문자열 그대로 둔다(dev 200건 전체). 첫 셀부터 실행한다 — 셀 18은
앞 셀이 만든 `RESULTS`·`WORK`·`PYTHON`·`MODEL_DIR`·`run_case`를 쓴다.

### 무엇을 보는가

| 물음 | 어디서 | 판정 |
| --- | --- | --- |
| 근거문구를 풀면 파이프라인의 v16·v18·v20이 살아나나 | `score/metrics.json` | TP가 하나라도 서면 성공 |
| 정밀도는 게이트가 잡나 | `experiments/sme_candidate.py`를 재생에 끼워 | v16 TP 유지하며 FP 40 이하 |
| 대상 밖 19항목이 흔들렸나 | `tools/compare_runs.py` | churn 판정 문장을 그대로 옮긴다 |
| v14·v15·v17이 어디서 막히나 | `diagnose/manifest.json`의 `stages` | 관측·추출·비교 중 어디인가 |

회차 하나의 Macro F1 차이는 신호가 아니다. 같은 코드가 dev 0.2182를 세 번, 0.2208과
0.2202를 한 번씩 냈다. 읽을 것은 대상 항목의 TP/FP/FN이다.

## 3. 같은 코드로 한 번 더 — 이제 기본이다

> 원래는 "R2 — 안 돌린다"였다. R1이 반려돼 재현할 값이 없어졌고 회차가 12번뿐이었다.
> 2026-09-20에 회차 제한이 풀려 그 이유가 둘 다 사라졌다.

프롬프트·스키마를 바꾸는 회차는 완전히 같은 ZIP으로 한 번 더 돌린다.
두 회차의 차이가 그날 그 코드의 churn이고, 그것을 알아야 후보의 차이 중 무엇이
코드 효과인지 갈린다. 지금 쓰는 churn 기준(4,800셀 중 29~45개, Macro F1
0.000008~0.003129)은 과거 열 쌍의 값이며([근거](../../reports/runs/reproducibility.md))
프롬프트가 바뀐 코드에 그대로 적용된다는 보장이 없다.

바꿀 것은 없다. `RUN_DIAGNOSTIC = True`도 그대로 둬 원응답을 한 벌 더 받는다.

후처리만 바꾸는 후보는 이 쌍이 필요 없다 — 재생은 churn이 0이다(§5).

## 4. R3 이후 — R1이 정한다

| R1 결과 | 다음 회차 |
| --- | --- |
| v16·v18에 TP가 섰다 | 정밀도는 후처리(게이트)로 잡는다 → GPU 불필요. 회차는 v14·v15로 |
| TP가 안 섰다 | 회차② 출력 4칸(요구사항·인용·판정·단계)을 같은 합동 호출 안에서 |
| 회차②도 실패 | 회차③ 3항목 별도 호출. 서버 예산 밖이므로 채택 후보가 아니라 원인 규명용 |
| v14·v15 진단이 단계를 짚었다 | 그 단계를 겨냥한 프롬프트 한 변수 |

한 회차에 한 변수다. 부재탐지에서 이미 한 번 어겼다 — `판정` 칸 제거와 보수화 지시가
한 회차에 같이 들어가 재현율 13/18 → 3/18의 원인을 아직 못 가른다.

## 5. 회차를 쓰지 않는 것

후처리만 바꾸는 후보는 전부 보관 원응답 재생으로 잰다. GPU 0초, 0.6초, churn 0이다.

- 금액 게이트·근거 대조·구간 필터 같은 모델 뒤 단계
- 임계값 조정, 정규식 수정
- 이미 재 보고 버린 것 — 전체 법령 프롬프트 주입(0.2208 → 0.1847),
  전건 추가 호출(v10·v11 TP 그대로 0, 시간만 증가), 문서 길이·검색 확대
  (회복한 양성 21건의 근거가 전부 모델이 본 16,000자 안에 있었다)

## 6. 회차마다 남길 것

```powershell
python -X utf8 tools/register_run.py --inbox artifacts/inbox --code-commit <커밋>
```

등록기가 `reports/runs/<run-id>/`·`manifest.json`·[색인](../runs.md) 한 행·결정 초안까지 쓴다.
손으로 세거나 표를 고치지 않는다. 가설 한 줄이 그 회차의 기록에 남아 있어야 한다.
