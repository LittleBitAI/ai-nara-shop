# C6 — 통합 후보 GPU 회차 실행 요청서

담당 C · 2026-09-25 · 실행은 사람이 한다. 이 문서는 무엇을 어떻게 돌리고 무엇으로
판정하는지만 정한다.

CPU 재생은 끝났다(`README.md`). 남은 것은 재생으로는 못 재는 것뿐이다.

## 0. 이 회차가 답하는 것 — 넷

| | 물음 | 왜 재생으로 못 재나 |
| --- | --- | --- |
| (a) | 새 모델 출력에서도 세 규칙이 발동하는가 | 셋 다 모델이 낸 사실에 걸려 있다 — `direct_production_quote == null`(v11·v18) 과 `qualification_role`(v16). 고정 원응답의 값이 새 회차에서 같다는 보장이 없다 |
| (b) | 세 항목의 TP/FP 가 새 출력에서 어떻게 나오나 | 재생에서 FP 가 v11 +4 · v18 +1 늘었다. 그것이 같은 공고인지 모른다 |
| (c) | 이 코드 기준의 회차 간 churn | 같은 코드 두 회차로만 잴 수 있다 |
| (d) | 대상 밖 항목의 회귀가 새 출력에서도 0 인가 | 재생은 한 벌의 출력만 본다. 기준↔후보는 0 이어야 하고(D1) 회차 간 churn 은 별개다(D2) |

### 0-1. 이 회차가 답하지 않는 것

- 대회 서버 점수. 회차는 서버가 아니다. 전이율 다섯 쌍이
  0.005 · 0.249 · 0.926 · −0.147 · −0.041 로 고정 계수가 없다.
- 제출 통과. 이 회차는 진단 목적이고 제출 후보를 만들지 않는다(`docs/colab.md` §9).
- 무라벨 오탐. 무라벨에는 라벨이 없다. `README.md` §6 의 배율은 발화율이고 정확도가
  아니며, 이 회차의 판정에도 쓰지 않는다.
- 과적합 여부. dev 200건 위의 이득이다. 방침(2026-09-25)이 그것을 감수한다고 정했다.

## 1. 회차용 커밋 — 운영 `main` 은 안 바꾼다

| 항목 | 값 |
| --- | --- |
| 회차 브랜치 | `run/c6-dev-macro` ← Colab 이 받아 갈 곳 |
| 회차용 커밋 SHA | `<RUN_COMMIT>` — push 뒤 채운다 |
| 기준 커밋 | `90383808bf147145f526a85be0c987e17e2b8165` (`origin/main`) |
| 무엇이 들어 있나 | `c6-integrated.diff` 하나 — `verify_company_size()` 에 30줄 추가, 삭제 0 |
| 작업 브랜치 | `feat/c-dev-macro` — `script.py` 를 안 바꾼다 |
| 운영 적용 | `main` 의 `script.py` 를 바꾸지 않는다. 운영 통합 판단은 B 와 A 가 한다 |

### 1-1. 왜 회차 코드를 별도 브랜치에 두나

작업 브랜치에 두면 PR 이 빨간불이 된다. C5 에서 실제로 그렇게 만들어 보고 확인했다.

저장소에는 HEAD 재생 CSV 를 고정값으로 박아 둔 검사가 여럿 있다(`tests/test_replay_run.py`
등). 그 검사의 docstring 이 "HEAD 후단을 일부러 바꿨다면 재생 결과를 새로 고정하고 그
이유를 PR 에 적는다"고 적는다. `script.py` 의 후처리를 바꾸면 그 고정값이 당연히 어긋나고,
그것을 "고치려고" 고정 CSV 를 다시 쓰면 운영 `main` 의 재생이 아닌 것을 `main` 의
재생이라고 박아 두게 된다.

그래서 B1·C5 가 쓴 방식을 따른다 — 회차 코드는 `run/…` 브랜치에 두고 작업 브랜치는
문서·후보·검사만 든다(`origin/run/b1-competitive-row` · `origin/run/c5-v11-absence-signal`
이 선례다).

### 1-2. 회차 브랜치를 만드는 법

패치 파일은 기준 커밋에 없다. `c6-integrated.diff` 는 `feat/c-dev-macro` 에서 태어났고
기준 커밋 `9038380` 에는 없다. `git switch --detach 9038380` 하는 순간
`reports/team-c/c6-dev-macro/` 폴더가 작업 트리에서 통째로 사라진다 — 그 뒤에
`patch -i reports/team-c/c6-dev-macro/c6-integrated.diff` 를 부르면 입력 파일이 없어 죽는다.

그래서 패치를 작업 트리가 아니라 `git show` 로 읽는다. `git show <ref>:<path>` 는
지금 무엇이 체크아웃돼 있든 그 ref 에서 파일을 꺼내므로 detach 상태에서도 돈다.

```bash
git switch --detach 90383808bf147145f526a85be0c987e17e2b8165
git show feat/c-dev-macro:reports/team-c/c6-dev-macro/c6-integrated.diff | patch -p1 --binary
git diff --stat            # script.py 한 파일 · 30줄 추가 · 삭제 0 이어야 한다
git commit -am "run: C6 통합 후보를 회차용으로 script.py 에 얹는다"
git switch -c run/c6-dev-macro
git push -u origin run/c6-dev-macro
git rev-parse HEAD         # ← 이 값을 위 표의 <RUN_COMMIT> 에 적는다
git switch feat/c-dev-macro   # 작업 브랜치로 돌아온다. `git switch -` 는 여기서 안 된다
```

마지막 줄에 `git switch -` 를 쓰면 안 된다. `-` 는 *직전에 있던 곳*으로 가는데, 여기서
직전은 `switch -c` 앞의 분리된 HEAD 다. 실제로 돌려 보면 브랜치로 안 가고 죽는다.

```
fatal: a branch is expected, got commit '1510440…'
hint: If you want to detach HEAD at the commit, try again with the --detach option.
```

죽은 뒤에도 `run/c6-dev-macro` 에 그대로 남으므로, 그 상태를 모르고 다음 작업을 이어가면
회차 브랜치 위에 작업 커밋이 쌓인다. 그래서 브랜치 이름을 그대로 적는다.

여기 적은 명령을 전부 실제로 돌려 확인했다 — detach 뒤
`reports/team-c/c6-dev-macro/` 가 사라지는 것, `git show … | patch` 가 그 상태에서도
`script.py` 에 30줄을 넣는 것, `git switch -` 가 위 메시지로 죽는 것.

PR 이 머지된 뒤라면 `feat/c-dev-macro` 대신 `origin/main` 을 써도 된다. 둘 중 그 파일이
실제로 있는 ref 를 쓴다 — `git cat-file -e <ref>:reports/team-c/c6-dev-macro/c6-integrated.diff`
로 미리 확인할 수 있다.

`<RUN_COMMIT>` 을 안 채운 채 돌리면 `main` 으로 도는 사고가 난다.

## 2. 노트북에서 고칠 것 — 두 곳

`notebooks/colab-baseline.ipynb` 를 연다.

### 2-1. 셀 `[1]` — 받아 갈 코드

`SOURCE_MODE` 는 `"clone"` 그대로 두고, `REPO_REF` 를 위 `<RUN_COMMIT>` 으로 바꾼다.
`REPO_REF` 를 정의하는 셀은 `[1]` 하나뿐이다.

### 2-2. 셀 `[18]` — 진단 회차

기본값이 이미 맞다(`RUN_DIAGNOSTIC = True`). 고칠 것이 없다. 이 셀이 도는 명령은

```
run_case("dev-debug", WORK / "open/dev.jsonl", args=DIAGNOSTIC_ARGS)
```

이고, `DIAGNOSTIC_ARGS` 는 `["--debug-responses"]` 다. 원응답이 보존돼야 §5 의 감사를
할 수 있다.

## 3. 회차 설계 — 두 번 돌린다

| 회차 | 코드 | 왜 |
| --- | --- | --- |
| 회차 1 | `<RUN_COMMIT>` | (a)·(b)·(d) 를 새 출력에서 본다 |
| 회차 2 | `<RUN_COMMIT>` — 같은 커밋 | (c) churn. 같은 코드 두 회차로만 잰다 |

두 회차의 ZIP 을 각각 `reports/runs/<run-id>/` 로 등록한다.

기준선은 재생으로 만든다. 회차 1 의 원응답 위에 기준 커밋 `9038380` 의 `script.py`
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

## 4. 합격 기준 — 회차 전에 정한다

`<tmp>/run1-base` 가 기준, 회차 1 의 CSV 가 후보다.

모든 기준을 그 회차의 기준선 대비 *차이* 로 읽는다. 고정 숫자로 읽지 않는다.
새 회차는 다른 모델 출력이라 기준선의 TP/FP/FN 자체가 고정 원응답과 다르다.
절대값으로 적으면 두 방향으로 틀린다 — 기준선이 낮은 회차에서는 멀쩡한 후보를 헛되이
기각하고, 기준선이 높은 회차에서는 TP 손실을 통과시킨다. 금지선인 E 가 특히 그렇다.

| | 기준 (그 회차의 기준선 대비) | 통과선 | 실패하면 |
| --- | --- | --- | --- |
| Z1 | 변경 기회 (§5-3 이 센다) — 규칙이 1 을 쓰겠다고 판단한 공고 | 세 규칙 각각 > 0 | 판정 보류 — 기각이 아니다. §4-2 |
| Z2 | 기회 중 실제로 바뀐 셀 | 각각 > 0 | 판정 보류 — 다른 경로가 먼저 올렸다. §4-2 |
| Z3 | 바뀐 셀이 있는 항목의 F1 | 기준선보다 높다 | 가설 기각 — §4-2 |
| A | v11 FN 감소 | ≥ 1 | 재검토 |
| B | v11 FP 증가 | ≤ +4 | 재검토 |
| C | v16 FP 감소 | ≥ 1 | 재검토 |
| D | v18 FN 감소 / FP 증가 | ≥ 1 / ≤ +1 | 재검토 |
| E | 24항목 각각의 TP 감소 — 합계가 아니다 | 모든 항목에서 정확히 0 | 기각 — 금지선 |
| D1 | `changed_cells_off_focus` (기준↔후보, 같은 원응답) | 정확히 0 | 기각 — 금지선 |
| D2 | 회차1↔회차2 바뀐 셀 (같은 코드) | 17~45셀 안 | 범위 밖이면 그 사실을 적고 원인을 찾는다 |
| F | dev Macro 증가 | > 0 | 재검토 |

A~D 의 통과선은 고정 원응답에서 실제로 나온 변화량이다(§4-3). 새 회차에서 그보다
나쁘면 "재검토"이지 자동 기각이 아니다 — 모델 출력이 달라졌다는 뜻일 수 있다.
E 와 D1 만 금지선이고, 이 둘은 회차와 무관하게 절대 어기면 안 된다.

E 를 합계로 읽으면 안 된다. 합계는 상쇄된다 — v11 이 TP 를 하나 얻고 v18 이 하나
잃으면 `C 합계 39 → 39` 로 아무 일도 없어 보인다. 그런데 금지선이 막으려는 것은
바로 그 v18 의 손실이다. 그래서 항목마다 따로 본다. 후보가 안 건드리는 항목까지 포함해
24개 전부를 보는 이유는, 대상 밖 셀이 움직이는 사고가 D1 과 E 양쪽에 걸리게 하기 위해서다.

```bash
py -X utf8 -c "import json;b=json.load(open(r'<tmp>/run1-base-score/metrics.json',encoding='utf-8'))['items'];a=json.load(open(r'<tmp>/run1-score/metrics.json',encoding='utf-8'))['items'];lost=[(k,b[k]['tp'],a[k]['tp']) for k in b if a[k]['tp']<b[k]['tp']];print('TP 가 줄어든 항목:', lost or '없음')"
```

`없음` 이 아니면 그 자리에서 기각이다. 합계는 참고로만 적는다.

D1 과 D2 를 한 칸에 섞지 않는다. 같은 원응답 위 `기준↔후보` 는 코드만 다르므로
결정적이고 대상 밖은 0 이어야 한다. churn 범위(17~45셀, Macro 0.000008~0.010088)는
회차1↔회차2 에만 쓴다 — 출처는 `reports/runs/reproducibility.md` 다. 한 칸에 섞으면
대상 밖 45셀까지 승인된다.

### 4-2. "안 움직였다"를 세 층으로 가른다 — 기각은 Z3 에서만 나온다

`applicability.py` 가 규칙마다 세 층을 센다. 층마다 0 의 뜻이 다르다.

| 층 | 뜻 | 0 이면 |
| --- | --- | --- |
| 조건 충족 | 규칙의 게이트를 통과했다 | 판정에 쓰지 않는다. 넓이일 뿐이다 |
| 변경 기회 (Z1) | 그중 규칙이 1 을 쓰겠다고 판단했다. 현재 값과 무관 | 판정 보류 — 이 회차는 그 규칙을 안 쟀다 |
| 실제 변경 (Z2) | 그중 현재 값이 달라 셀이 정말 바뀌었다 | 판정 보류 — 기회가 이미 1 이었다. 다른 경로가 먼저 올렸다 |

조건 충족을 변경 기회로 읽으면 규칙이 아니라 회차를 벌한다. 고정 원응답에서
v18 규칙은 게이트를 38건 통과하지만 결정표가 v18 을 세우는 것은 3건뿐이다.

```
decided 인데 v18 이 안 선다   23      ← general 로 다시 밟아도 금액·자격이 v18 을 안 세운다
unverified_qualification      9
absence_not_observable        3      ← 완전관측 게이트. 기각된 접근이라 그대로 둔다
```

새 회차에서 게이트 통과가 38건이어도 그중 v18 이 설 공고가 0이면 그것은 가설에 대해
아무 말도 하지 않는다. "대상 38건이 있는데 0셀"을 기각으로 적으면 안 된다.

그래서 기각은 Z3 에서만 나온다 — 셀이 실제로 바뀌었는데 그 항목의 F1 이 기준선보다
높지 않을 때다(`.wiki/gpu-before-review`: "발동이 확인됐는데 대상 셀·TP/FP/FN 이 그대로면
가설 기각"). 위 두 층의 0 은 전부 판정 보류다.

이 구분이 실제로 필요했다. C5 의 `c_v13_merge_candidate` 는 dev 에서 0셀이지만
조건은 117건에서 참이었고, 무라벨 5,500건에서는 같은 규칙이 6건을 닫는다.
규칙이 죽은 것이 아니라 그 출력에 겹치는 대상이 없었다.

세 규칙을 따로 판정한다. 하나가 Z1·Z2 에 걸려도 나머지 둘은 그대로 읽는다 — 셋은
상호작용 0 이라 따로 뗄 수 있다(`README.md` §5).

### 4-3. 고정 원응답에서의 값 — 통과선이 어디서 왔나

오른쪽 끝의 변화량이 위 표의 통과선이다. 가운데 두 열은 참고값이고, 새 회차에서
그 숫자가 그대로 나올 이유는 없다.

| | 기준 (`9038380`) | 통합 후보 | 변화량 ← 통과선 |
| --- | --- | --- | --- |
| dev Macro | 0.685506108460 | 0.708908686274 | +0.023402577814 |
| v11 TP/FP/FN | 2/2/4 | 5/6/1 | TP +3 · FP +4 · FN −3 |
| v16 TP/FP/FN | 4/3/2 | 4/1/2 | TP 0 · FP −2 · FN 0 |
| v18 TP/FP/FN | 1/2/6 | 3/3/4 | TP +2 · FP +1 · FN −2 |
| 항목별 TP | — | — | 24항목 중 줄어든 것 0개 ← 금지선 E |
| C 항목 TP (참고) | v10 4 · v11 2 · v12 4 · v13 3 · v14 7 · v15 4 · v16 4 · v17 5 · v18 1 · v20 5 | v11 5 · v18 3 · 나머지 그대로 | v11 +3 · v18 +2 · 나머지 0 |
| C 합계 TP (참고만) | 39 | 44 | +5 — 판정에 쓰지 않는다 |
| 조건 충족 / 변경 기회 / 실제 변경 | — | — | v18 38 / 3 / 3 · v16 2 / 2 / 2 · v11 7 / 7 / 7 |
| D1 | — | — | 0 |

세 층이 다르다는 데 주의한다. v18 규칙은 게이트를 38건 통과하지만 결정표가 v18 을
세우는 것은 3건뿐이고, 나머지 35건은 `general` 로 다시 밟아도 금액·자격·관측 조건에서
막힌다(§4-2). Z1 이 보는 것은 38 이 아니라 3 이다.

새 회차에서 조건 충족이 38 → 20 으로 줄어도 그 자체는 아무 실패가 아니다. 걸리는 것은
변경 기회가 0 이 될 때(Z1)와 기회가 있는데 하나도 안 바뀔 때(Z2)이고, 둘 다
기각이 아니라 판정 보류다.

## 5. 감사 — 무엇을 확인하나

### 5-1. 쌍 비교

```bash
py -X utf8 tools/compare_runs.py --before <tmp>/run1-base/submission.csv \
  --after reports/runs/<run1>/dev-debug/submission.csv \
  --items v11,v16,v18 --output-dir <tmp>/run1-compare
```

`--items` 는 쉼표로 구분한다. 공백으로 나누면 거부된다.

왜 셋인가. 이 후보가 쓰는 키가 v11 · v16 · v18 셋이다. 그 셋만 대상으로 잡아야
나머지 21항목이 `changed_cells_off_focus` 에 들어와 D1 이 그 회귀를 본다. 넷째를
더하면 그 항목의 회귀를 D1 이 못 본다. 세 항목 사이의 회귀는 D1 이 아니라 위 A~E 가
개별 TP/FP 로 본다.

### 5-2. `comparison.json` 을 읽는 법

`items` 는 딕셔너리가 아니라 24개짜리 리스트다. 각 원소에 `item` · `focus` ·
`flipped` · `before` · `after` · `support` 가 있다. 최상위에 `changed_cells` ·
`changed_cells_off_focus` · `macro_f1` 이 있다.

```bash
py -X utf8 -c "import json;d=json.load(open(r'<tmp>/run1-compare/comparison.json',encoding='utf-8'));print(d['changed_cells'],d['changed_cells_off_focus']);print([(x['item'],x['before'],x['after']) for x in d['items'] if x['focus']])"
```

### 5-3. 세 층을 센다 — 기준 Z1 · Z2

```bash
py -X utf8 reports/team-c/c6-dev-macro/applicability.py \
  --case reports/runs/<run1>/dev-debug
```

규칙마다 조건 충족 · 변경 기회 · 실제 변경을 나눠 내고 §4-2 의 판정을 그대로 찍는다.
판정 코드는 기준 커밋 `9038380` 으로 고정돼 있다 — 세 층 모두 "기준 코드가 무엇에
적용될 뻔했나"이므로 회차 코드가 아니라 기준 코드로 센다.

고정 원응답에서 이 스크립트가 내는 값은 다음과 같고, 실제 변경의 합 `3 + 2 + 7 = 12`
가 §5-1 쌍 비교의 `changed_cells` 와 일치한다.

```
규칙           조건 충족     변경 기회     실제 변경   판정
v18             38         3         3   발동했다
v16              2         2         2   발동했다
v11              7         7         7   발동했다
```

Z1 은 가운데 열로 읽는다. 왼쪽 열(조건 충족)은 넓이일 뿐이고, v18 에서 38 과 3 이
갈리는 이유는 스크립트가 같이 찍는다.

## 6. 예상되는 실패와 그때 할 일

§4-2 의 두 갈래를 여기서도 지킨다 — "안 움직였다"의 판정은 적용 대상이 정한다.

| 무엇 | 왜 그럴 수 있나 | 그러면 |
| --- | --- | --- |
| v18 의 변경 기회가 0 (조건 충족은 몇이든) | 새 출력에서 그 공고들의 `scope` 가 `general` 로 나왔거나, 게이트는 통과해도 금액·자격이 v18 을 안 세운다 | 판정 보류 (Z1). 기각이 아니다. `README.md` §2-1 의 v13 이 같은 일을 겪었다. 조건 충족이 38 이어도 기회가 0 이면 보류다 |
| 기회는 있는데 실제 변경이 0 | 그 셀을 앞 단계가 이미 1 로 올렸다 | 판정 보류 (Z2). 다른 경로와 겹친 것이지 규칙이 틀린 게 아니다 |
| 셀은 바뀌었는데 그 항목 F1 이 안 오른다 | 바뀐 셀이 전부 FP 쪽이다 | 가설 기각 (Z3). 여기서만 기각이 나온다 |
| v16 의 변경 기회가 0 | `qualification_role` 이 `none` 이면서 결정표가 v16 을 올린 공고가 새 출력에 없다 | 판정 보류. 다만 이 규칙은 표본 2건이라 처음부터 약하다 |
| v11 FP 증가가 +4 를 넘는다 | 부재 관측이 새 출력에서 더 자주 참이다 | B 를 못 넘으면 v11 규칙만 빼고 나머지 둘을 다시 잰다 — 셋은 상호작용 0 이라 따로 뗄 수 있다 |
| 대상 밖이 0 이 아니다 | 후보가 안 건드리는 항목이 움직였다 | 기각. 금지선이다 |
| 어느 한 항목이라도 TP 가 그 회차 기준선보다 적다 | 거기서 TP 를 지웠다 | 기각. 금지선이다. 고정 숫자 44 가 아니라 그 회차의 기준선과 견주고, 합계가 아니라 항목별로 본다 — 합계는 상쇄돼 손실을 숨긴다 |
| 세 규칙이 다 Z1 에 걸린다 | 회차가 후보를 하나도 안 쟀다 | 회차를 버리지 말고 왜 대상이 사라졌는지를 적는다. 모델 출력이 그만큼 움직였다는 관측 자체가 값이다 |

## 7. 이 회차 뒤에

회차가 Z3·E·D1 을 통과하면 운영 통합을 제안할 수 있다. 통합은 B 와 A 가 한다 —
B 가 같은 시각에 후처리를 고치고 있고, 이 후보는 `postprocess()` 를 안 고치지만
근거 계약(#91)에서 만날 수 있다(`README.md` §7).

제출은 하루 한 칸이다. 한 칸에 이 변경 하나만 올려야 서버에서 무엇이 졌는지 가른다.
그 판단은 A 가 한다.
