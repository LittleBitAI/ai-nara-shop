# C6 — 회차를 안 돌리고 답을 받았다

담당 C · 2026-09-25 · **GPU 회차를 새로 돌리지 않았다.** `RUN-REQUEST.md` §0 의 네 물음이
다른 사람의 회차로 이미 답해졌고, 그 회차의 **새 모델 출력** 위에서 이 후보만 분리해 쟀다.

## 1. 무슨 일이 있었나

`run/c6-dev-macro` @ `072cd28` 을 만든 뒤, 회차를 돌리기 전에 `main` 이 한 번 더 움직였다.

| 커밋 | 무엇 |
| --- | --- |
| `ca352d6` | **"port #139's v18/v16/v11 rules and repair v13 quote checks (dev 0.7788 -> 0.7925)"** |
| `d73cfa1` | `run: register colab-1790318892216968298 (ca352d6, dev 0.7742)` |
| `0496ef0` | Merge PR #142 (`feat/a-dev-fit-stack`) |

**이 후보의 세 규칙이 운영 `script.py` 에 그대로 들어갔다.** 주석만 영어로 옮겼고 조건식은
같다 — `main:script.py` 에서 `C6-1` · `C6-2` · `C6-3` 이 그대로 검색된다.

그리고 **그 코드로 GPU 회차가 이미 돌았다.** 그러면 `072cd28` 회차는 같은 물음을 더 낡은
코드(v13 인용 수리가 빠진 판)로 다시 묻는 것이 된다.

## 2. 네 물음에 대한 답

`RUN-REQUEST.md` §0 이 물은 것과, 무엇이 그것을 답했는지.

| | 물음 | 답한 것 | 결과 |
| --- | --- | --- | --- |
| **(a)** | 새 모델 출력에서도 세 규칙이 **발동하는가** | §3 의 분리 재생 | **발동한다 — 6셀** |
| **(b)** | 세 항목의 **TP/FP 가 어떻게 나오나** | §3 | v11 +1TP/+2FP · v16 −1FP · v18 +1TP/+1FP |
| **(c)** | 이 코드 기준의 **회차 간 churn** | `d73cfa1` 등록문 | **같은 코드 두 패스 12셀** (Macro 0.7742 vs 0.7398) |
| **(d)** | **대상 밖 항목의 회귀**가 0 인가 | §3 | **C 항목 밖 0셀** |

(c)의 두 패스는 회차 `colab-1790318892216968298` 의 `dev` 와 `dev-debug` 이고, 둘의
`run_report.json` 이 같은 `code_sha256`(`7a27edd0…`)을 적는다 — **같은 코드 두 번**이라
churn 의 정의를 만족한다.

## 3. 새 모델 출력 위에서 이 후보만 분리해 쟀다

회차 `colab-1790318892216968298` 의 **원응답**(`dev-debug`, `mode: live`) 위에서
기준 코드와 회차 코드를 각각 재생했다. 같은 원응답 위에서는 코드 효과가 **결정적**이다.

```bash
# 원응답을 꺼낸다 (Git Bash 에서는 MSYS_NO_PATHCONV=1 을 붙인다)
for f in diagnostics.jsonl run_report.json submission.csv \
         baseline_submission.csv company_size_baseline_submission.csv; do
  MSYS_NO_PATHCONV=1 git show \
    "origin/main:reports/runs/colab-1790318892216968298/dev-debug/$f" > <tmp>/dev-debug/$f
done

git show c68eb00:script.py          > <tmp>/base.py
git show run/c6-dev-macro:script.py > <tmp>/run072.py

py -X utf8 tools/replay_run.py --case <tmp>/dev-debug --script <tmp>/base.py    --output-dir <tmp>/nb-base
py -X utf8 tools/replay_run.py --case <tmp>/dev-debug --script <tmp>/run072.py  --output-dir <tmp>/nb-run
py -X utf8 tools/score.py --truth open/dev_labels.csv --pred <tmp>/nb-base/submission.csv --output-dir <tmp>/nb-base-sc
py -X utf8 tools/score.py --truth open/dev_labels.csv --pred <tmp>/nb-run/submission.csv  --output-dir <tmp>/nb-run-sc
```

**모든 재생에 `--script` 로 코드를 박았다.** 작업 트리 판을 쓰지 않았다.

| | 기준 `c68eb00` | 회차코드 `072cd28` | 차이 |
| --- | ---: | ---: | ---: |
| dev Macro F1 | 0.725008120964 | **0.732858256939** | **+0.007850135975** |
| 바뀐 셀 | — | 6 / 4800 | — |
| **C 항목 밖** | — | **0셀** | — |
| **TP 줄어든 항목** | — | **0개** (24항목 각각) | — |
| C 합계 TP/FP/FN (참고) | 40/24/23 | 42/26/21 | — |

| 항목 | 기준 | 회차코드 | F1 |
| --- | --- | --- | --- |
| v11 | 4/3/2 | **5/5/1** | 0.615385 → 0.625000 |
| v16 | 3/3/3 | **3/2/3** | 0.500000 → 0.545455 |
| v18 | 1/2/6 | **2/3/5** | 0.200000 → 0.333333 |

바뀐 공고: `012` · `039` · `040` · `061` · `064` · `149`.

### 3-1. 회차 품질 — 버릴 이유가 없다

| | |
| --- | --- |
| `model_success_count` | **200 / 200** |
| `company_size_model_success_count` | **200 / 200** |
| `sme_fallback_count` · `company_size_fallback_count` | **0** · **0** |
| `mode` | `live` |

응답 실패·폴백이 0 이므로 이 출력을 근거로 쓸 수 있다.

## 4. 고정 원응답과 견주면

| | 고정 원응답 `colab-1790235508743452453` | 새 출력 `colab-1790318892216968298` |
| --- | ---: | ---: |
| 기준 `c68eb00` | 0.735764126941 | 0.725008120964 |
| 회차코드 `072cd28` | 0.749407019995 | 0.732858256939 |
| **차이** | **+0.013642893055** | **+0.007850135975** |
| 바뀐 셀 | 8 | 6 |
| C 항목 밖 | 0 | 0 |
| TP 줄어든 항목 | 0개 | 0개 |

**이득이 절반쯤으로 줄었지만 방향은 같고 금지선은 둘 다 지킨다.** 두 출력의 기준선 자체가
다르므로(0.735764 vs 0.725008) 이 차이는 후보가 나빠진 것이 아니라 **모델 출력이 달라진
것**이다. 같은 코드 두 패스가 12셀·Macro 0.7742 vs 0.7398 로 흔들린다는 것을 함께 읽는다.

**한 쌍의 회차 Macro 차이는 신호가 아니다.** 대상 항목 TP/FP/FN 을 본다.

## 5. 이 문서가 답하지 않는 것

- **대회 서버 점수.** 회차는 서버가 아니다. 전이율 다섯 쌍이
  0.005 · 0.249 · 0.926 · −0.147 · −0.041 로 **고정 계수가 없다.**
- **무라벨 오탐.** 무라벨에는 라벨이 없다. `README.md` §6 의 배율은 발화율이고 정확도가
  아니며, 판정에 쓰지 않았다.
- **과적합 여부.** dev 200건 위의 이득이다. 방침(2026-09-25)이 그것을 감수한다고 정했다.
- **`072cd28` 자체의 GPU 실행.** 그 커밋으로는 회차를 안 돌렸다. 여기 적은 수는
  **다른 코드로 돈 회차의 원응답 위에서 이 코드를 재생한 것**이다. 원응답을 만든 코드와
  판정에 쓴 코드가 다르다는 한계 안에서 읽는다 — 다만 후처리만 바꾸는 후보라 그 재생이
  결정적이라는 점은 `RUN-REQUEST.md` §3 이 이미 적었다.
- **dev 와 dev-debug 를 같은 저울로 읽지 않는다.** 위 수는 전부 `dev-debug` 재생이다.

## 6. 회차 브랜치는 그대로 둔다

`run/c6-dev-macro` @ `072cd2837390b6c98dff676dc53b5b4784d8c119` 은 지우지 않는다.
`c68eb00` + `c6-integrated.diff` 하나뿐이고 `script.py` 30줄 추가·삭제 0 이다.
나중에 같은 물음을 다시 물을 일이 생기면 `RUN-REQUEST.md` 를 그대로 쓰면 된다.

**`main` 이 또 움직였어도 이 브랜치를 재베이스하지 않는다** — 회차가 어느 코드로 돌았는지가
흐려진다.

## 7. 지금 `main` 과의 관계

`main` 은 `0496ef0` 이고 이 후보의 세 규칙이 이미 그 안에 있다. 그래서 **이 PR 의 값은
운영 코드를 바꾸는 데 있지 않고**, 다음 셋에 있다.

1. 그 규칙들이 **왜 그 규칙인지**와 무엇을 재고 무엇을 닫았는지의 기록(`README.md` §1~§8)
2. 두 기준(`9038380` · `c68eb00`)과 **새 모델 출력**에서의 실측(§3~§4)
3. 회차 절차와 판정 기준(`RUN-REQUEST.md`), 적용 대상 집계기(`applicability.py`),
   그리고 그것들을 고정하는 검사(`tests/test_c6_integrated.py`)

운영 반영 여부와 순서는 **B 와 A 가 판단한다.**
