# C6 — 통합 후보 GPU 회차 실행 요청서

담당 C · 2026-09-25 · **실행은 사람이 한다. 이 문서는 무엇을 어떻게 돌리고 무엇으로
판정하는지만 정한다.**

CPU 재생은 끝났다(`README.md`). 남은 것은 **재생으로는 못 재는 것**뿐이다.

## 0. 이 회차가 답하는 것 — 넷

| | 물음 | 왜 재생으로 못 재나 |
| --- | --- | --- |
| **(a)** | 새 모델 출력에서도 **세 규칙이 발동하는가** | 셋 다 모델이 낸 사실에 걸려 있다 — `direct_production_quote == null`(v11·v18) 과 `qualification_role`(v16). 고정 원응답의 값이 새 회차에서 같다는 보장이 없다 |
| **(b)** | 세 항목의 **TP/FP 가 새 출력에서 어떻게 나오나** | 재생에서 FP 가 v11 +4 · v18 +1 늘었다. 그것이 같은 공고인지 모른다 |
| **(c)** | 이 코드 기준의 **회차 간 churn** | 같은 코드 두 회차로만 잴 수 있다 |
| **(d)** | **대상 밖 항목의 회귀**가 새 출력에서도 **0** 인가 | 재생은 한 벌의 출력만 본다. 기준↔후보는 0 이어야 하고(D1) 회차 간 churn 은 별개다(D2) |

### 0-1. 이 회차가 **답하지 않는 것**

- **대회 서버 점수.** 회차는 서버가 아니다. 전이율 다섯 쌍이
  0.005 · 0.249 · 0.926 · −0.147 · −0.041 로 **고정 계수가 없다.**
- **제출 통과.** 이 회차는 진단 목적이고 제출 후보를 만들지 않는다(`docs/colab.md` §9).
- **무라벨 오탐.** 무라벨에는 라벨이 없다. `README.md` §6 의 배율은 발화율이고 정확도가
  아니며, 이 회차의 판정에도 쓰지 않는다.
- **과적합 여부.** dev 200건 위의 이득이다. 방침(2026-09-25)이 그것을 감수한다고 정했다.

## 1. 회차용 커밋 — 운영 `main` 은 안 바꾼다

| 항목 | 값 |
| --- | --- |
| **회차 브랜치** | **`run/c6-dev-macro`** ← Colab 이 받아 갈 곳 |
| **회차용 커밋 SHA** | **`<RUN_COMMIT>`** — **push 뒤 채운다** |
| 기준 커밋 | `90383808bf147145f526a85be0c987e17e2b8165` (`origin/main`) |
| 무엇이 들어 있나 | `c6-integrated.diff` **하나** — `verify_company_size()` 에 30줄 추가, 삭제 0 |
| 작업 브랜치 | `feat/c-dev-macro` — **`script.py` 를 안 바꾼다** |
| 운영 적용 | **`main` 의 `script.py` 를 바꾸지 않는다.** 운영 통합 판단은 B 와 A 가 한다 |

### 1-1. 왜 회차 코드를 별도 브랜치에 두나

**작업 브랜치에 두면 PR 이 빨간불이 된다.** C5 에서 실제로 그렇게 만들어 보고 확인했다.

저장소에는 HEAD 재생 CSV 를 고정값으로 박아 둔 검사가 여럿 있다(`tests/test_replay_run.py`
등). 그 검사의 docstring 이 "HEAD 후단을 일부러 바꿨다면 재생 결과를 **새로 고정하고** 그
이유를 PR 에 적는다"고 적는다. `script.py` 의 후처리를 바꾸면 그 고정값이 당연히 어긋나고,
그것을 "고치려고" 고정 CSV 를 다시 쓰면 **운영 `main` 의 재생이 아닌 것을 `main` 의
재생이라고 박아 두게 된다.**

그래서 B1·C5 가 쓴 방식을 따른다 — 회차 코드는 `run/…` 브랜치에 두고 작업 브랜치는
문서·후보·검사만 든다(`origin/run/b1-competitive-row` · `origin/run/c5-v11-absence-signal`
이 선례다).

### 1-2. 회차 브랜치를 만드는 법

```bash
git switch --detach 90383808bf147145f526a85be0c987e17e2b8165
patch -p1 --binary -i reports/team-c/c6-dev-macro/c6-integrated.diff
git commit -am "run: C6 통합 후보를 회차용으로 script.py 에 얹는다"
git switch -c run/c6-dev-macro
git push -u origin run/c6-dev-macro
git rev-parse HEAD        # ← 이 값을 위 표의 <RUN_COMMIT> 에 적는다
```

**`<RUN_COMMIT>` 을 안 채운 채 돌리면 `main` 으로 도는 사고가 난다.**

## 2. 노트북에서 고칠 것 — 두 곳

`notebooks/colab-baseline.ipynb` 를 연다.

### 2-1. 셀 `[1]` — 받아 갈 코드

`SOURCE_MODE` 는 `"clone"` 그대로 두고, **`REPO_REF` 를 위 `<RUN_COMMIT>` 으로 바꾼다.**
`REPO_REF` 를 정의하는 셀은 `[1]` 하나뿐이다.

### 2-2. 셀 `[18]` — 진단 회차

기본값이 이미 맞다(`RUN_DIAGNOSTIC = True`). 고칠 것이 없다. 이 셀이 도는 명령은

```
run_case("dev-debug", WORK / "open/dev.jsonl", args=DIAGNOSTIC_ARGS)
```

이고, `DIAGNOSTIC_ARGS` 는 `["--debug-responses"]` 다. **원응답이 보존돼야** §5 의 감사를
할 수 있다.

## 3. 회차 설계 — **두 번 돌린다**

| 회차 | 코드 | 왜 |
| --- | --- | --- |
| **회차 1** | `<RUN_COMMIT>` | (a)·(b)·(d) 를 새 출력에서 본다 |
| **회차 2** | `<RUN_COMMIT>` — **같은 커밋** | (c) churn. **같은 코드 두 회차**로만 잰다 |

두 회차의 ZIP 을 각각 `reports/runs/<run-id>/` 로 등록한다.

**기준선은 재생으로 만든다.** 회차 1 의 원응답 위에 **기준 커밋 `9038380` 의 `script.py`**
를 박아 재생한 것이 그 회차의 기준선이다 — 같은 모델 출력 위에서만 코드 효과가 결정적이다.

```bash
git show 9038380:script.py > <tmp>/script_9038380.py
py -X utf8 tools/replay_run.py --case reports/runs/<run1>/dev-debug \
  --script <tmp>/script_9038380.py --output-dir <tmp>/run1-base
py -X utf8 tools/score.py --truth open/dev_labels.csv \
  --pred <tmp>/run1-base/submission.csv --output-dir <tmp>/run1-base-score
py -X utf8 tools/score.py --truth open/dev_labels.csv \
  --pred reports/runs/<run1>/dev-debug/submission.csv --output-dir <tmp>/run1-score
```

## 4. 합격 기준 — **회차 전에 정한다**

`<tmp>/run1-base` 가 기준, 회차 1 의 CSV 가 후보다.

| | 기준 | 값 | 실패하면 |
| --- | --- | --- | --- |
| **Z** | **세 규칙이 다 발동했는가** — v11 FN **감소 ≥ 1** · v16 FP **감소 ≥ 1** · v18 FN **감소 ≥ 1**, 그리고 바뀐 셀 **> 0** | — | **가설 기각.** 발동이 안 보이면 나머지 기준을 통과해도 그것은 후보의 공이 아니다 |
| **A** | v11 TP | **≥ 5** | 재검토 |
| **B** | v11 FP | **≤ 6** | 재검토 |
| **C** | v16 FP | **≤ 1** | 재검토 |
| **D** | v18 TP / FP | **≥ 3** / **≤ 3** | 재검토 |
| **E** | C 항목 합계 TP | **≥ 44** (기준 39 에서 감소 0) | **기각** — 금지선 |
| **D1** | `changed_cells_off_focus` (기준↔후보, 같은 원응답) | **정확히 0** | **기각** — 금지선 |
| **D2** | 회차1↔회차2 바뀐 셀 (같은 코드) | **17~45셀** 안 | 범위 밖이면 그 사실을 적고 원인을 찾는다 |
| **F** | dev Macro | 기준선보다 **높다** | 재검토 |

**D1 과 D2 를 한 칸에 섞지 않는다.** 같은 원응답 위 `기준↔후보` 는 코드만 다르므로
**결정적**이고 대상 밖은 0 이어야 한다. churn 범위(17~45셀, Macro 0.000008~0.010088)는
**회차1↔회차2** 에만 쓴다 — 출처는 `reports/runs/reproducibility.md` 다. 한 칸에 섞으면
대상 밖 45셀까지 승인된다.

### 4-1. 고정 원응답에서의 값 — 이것과 비교한다

| | 기준 (`9038380`) | 통합 후보 |
| --- | --- | --- |
| dev Macro | 0.685506108460 | **0.708908686274** |
| v11 TP/FP/FN | 2/2/4 | **5/6/1** |
| v16 TP/FP/FN | 4/3/2 | **4/1/2** |
| v18 TP/FP/FN | 1/2/6 | **3/3/4** |
| C 합계 TP/FP/FN | 39/31/24 | **44/34/19** |
| 바뀐 셀 | — | 12 |
| **D1** | — | **0** |

## 5. 감사 — 무엇을 확인하나

### 5-1. 쌍 비교

```bash
py -X utf8 tools/compare_runs.py --before <tmp>/run1-base/submission.csv \
  --after reports/runs/<run1>/dev-debug/submission.csv \
  --items v11,v16,v18 --output-dir <tmp>/run1-compare
```

**`--items` 는 쉼표로 구분한다.** 공백으로 나누면 거부된다.

**왜 셋인가.** 이 후보가 쓰는 키가 v11 · v16 · v18 셋이다. 그 셋만 대상으로 잡아야
나머지 **21항목**이 `changed_cells_off_focus` 에 들어와 D1 이 그 회귀를 본다. 넷째를
더하면 그 항목의 회귀를 D1 이 못 본다. 세 항목 **사이의** 회귀는 D1 이 아니라 위 A~E 가
개별 TP/FP 로 본다.

### 5-2. `comparison.json` 을 읽는 법

`items` 는 **딕셔너리가 아니라 24개짜리 리스트**다. 각 원소에 `item` · `focus` ·
`flipped` · `before` · `after` · `support` 가 있다. 최상위에 `changed_cells` ·
`changed_cells_off_focus` · `macro_f1` 이 있다.

```bash
py -X utf8 -c "import json;d=json.load(open(r'<tmp>/run1-compare/comparison.json',encoding='utf-8'));print(d['changed_cells'],d['changed_cells_off_focus']);print([(x['item'],x['before'],x['after']) for x in d['items'] if x['focus']])"
```

### 5-3. 발동 확인 (기준 Z)

발동이 확인됐는데 대상 셀·TP/FP/FN 이 그대로면 **가설 기각**이다
(`.wiki/gpu-before-review`). 반대로 발동 자체가 0 이면 그 회차는 이 후보를 안 잰 것이다.

## 6. 예상되는 실패와 그때 할 일

| 무엇 | 왜 그럴 수 있나 | 그러면 |
| --- | --- | --- |
| v18 이 안 움직인다 | 새 출력에서 모델이 그 공고의 `scope` 를 `general` 로 냈다 — 그러면 D1 규칙의 적용 대상이 아니고, 결정표가 원래 경로로 v18 을 정한다 | 기각이 아니다. **대상이 없는 것**과 규칙이 틀린 것을 가른다. §2-1 의 v13 이 같은 일을 겪었다 |
| v16 이 안 움직인다 | `qualification_role` 이 `none` 인 공고가 새 출력에 없다 | 위와 같다. 다만 이 규칙은 **표본 2건**이라 처음부터 약하다 |
| v11 FP 가 6 을 넘는다 | 부재 관측이 새 출력에서 더 자주 참이다 | B 를 못 넘으면 **v11 규칙만** 빼고 나머지 둘을 다시 잰다 — 셋은 상호작용 0 이라 따로 뗄 수 있다 |
| 대상 밖이 0 이 아니다 | 후보가 안 건드리는 항목이 움직였다 | **기각.** 금지선이다 |
| C 합계 TP 가 44 미만 | 어딘가에서 TP 를 지웠다 | **기각.** 금지선이다 |

## 7. 이 회차 뒤에

회차가 Z·E·D1 을 통과하면 운영 통합을 제안할 수 있다. **통합은 B 와 A 가 한다** —
B 가 같은 시각에 후처리를 고치고 있고, 이 후보는 `postprocess()` 를 안 고치지만
근거 계약(#91)에서 만날 수 있다(`README.md` §7).

**제출은 하루 한 칸이다.** 한 칸에 이 변경 하나만 올려야 서버에서 무엇이 졌는지 가른다.
그 판단은 A 가 한다.
