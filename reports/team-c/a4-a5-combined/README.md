# A4 게이트와 A5 H2를 한 재생에서 합쳐 쟀다 — 간섭 0, 0.620382

2026-09-21. 모델을 부르지 않았다. GPU 0초. **새 규칙을 하나도 만들지 않았다.**
이미 각자 측정된 두 후보를 같은 원응답에 같이 끼워 돌린 것뿐이다.

## 결과

| | 값 |
| --- | ---: |
| 기준 (HEAD `c81644d` 재생) | 0.593846165415 |
| **합본** | **0.620382330538** |
| 차이 | **+0.026536165123** |
| 바뀐 셀 | 15 / 4,800 · **대상 밖 0** |
| 오답 | 161 → 151 |

| 항목 | TP/FP/FN 전 → 후 | F1 전 → 후 | 누구 |
| --- | --- | --- | --- |
| v6 | 3/4/3 → **3/0/3** | 0.461538 → **0.666667** | A4 |
| v9 | 5/12/1 → 4/8/2 | 0.434783 → 0.444444 | A4 |
| **v11** | 2/3/4 → **4/4/2** | 0.363636 → **0.571429** | A5 H2 (astra) |
| v23 | 1/1/4 → 2/1/3 | 0.285714 → **0.500000** | A4 |

## 두 후보가 정확히 더해진다 — 간섭 0

```
예측 산술  0.593846165415 + 0.017878156465 + 0.008658008658 = 0.620382330538
실측 합본                                                    = 0.620382330538
차이                                                          = +2.35e-13
```

소수점 12자리까지 같다. 남은 차이는 부동소수점 잡음이다.

**왜 더해지는가.** 두 후보가 바꾸는 항목이 겹치지 않는다(A4: v6·v9·v23 / H2: v11).
Macro F1은 항목별 F1의 평균이므로 서로 다른 항목의 변화는 정확히 더해진다.

**왜 그걸 그래도 쟀는가.** 둘이 `replay_run.replay()`의 **서로 다른 슬롯**에 꽂히고
그 사이에 순서가 있기 때문이다. 재생기는 `verify_company_size`(H2) → `parsed.update()` →
`postprocess`(A4) 순으로 돈다. H2가 올린 `v11=1`이 A4의 `postprocess`를 지나며 죽지 않는지가
유일한 간섭 지점이었다. 죽지 않았다 — `script.postprocess`의 `apply_product_rules()`는
`if cell.get("위반여부") != 1`일 때만 v11을 올리므로 이미 1인 것을 덮지 않고,
A4의 `postprocess`는 v6·v9·v23만 고쳐 쓴다.

**산술이 맞을 것이라는 예상과 실제로 맞는다는 것은 다르다.** 그 차이를 30초에 없앴다.

## 전제 검사 — `script.py`가 세 브랜치에서 같다

두 후보가 서로 다른 브랜치에서 왔으므로 기준 코드가 같아야 합칠 수 있다.

```
d2bcc73a29e722ffdf463b0d4c2ef280aa886896  main
d2bcc73a29e722ffdf463b0d4c2ef280aa886896  feat/a4-scope-gate
d2bcc73a29e722ffdf463b0d4c2ef280aa886896  LittleBitAI/a5-label-wall
```

블롭이 동일하다. 두 후보 모두 `script.py`를 안 고쳤다.

HEAD 재생이 회차 CSV와 **바이트 동일**함을 먼저 확인했고, 기준·후보를 같은 HEAD(`c81644d`)에서
돌렸다.

## 출처와 소유

| 파일 | 소유 | 비고 |
| --- | --- | --- |
| `experiments/a4_scope_gate_candidate.py` | 주 세션 · PR **#69**(머지됨) | v6·v9·v23 |
| `experiments/a5_v11_absence_candidate.py` | **astra** · PR **#71**(머지됨) | v11. **여기서 고치지 않는다** |
| `experiments/a4_a5_combined_candidate.py` | 이 보고 | 두 슬롯을 내보내기만 한다 |

**측정 당시에는 astra 후보의 사본을 벤더링했다.** #71이 머지되면서 원본이 `main`에 들어와
사본이 없어졌고, `main` 코드로 같은 재생을 다시 돌려 **#72 저장본과 바이트 동일**함을 확인했다.
Macro F1도 0.620382330538 그대로다. 그 사본의 SHA-256
`5515c631cc585705722c664940f4ee0b2f95b46a4fc6268decf43261b37b0a7d`은 astra의 GPU 회차
`facts/contract.json` 기록값과 일치했다 — 그 회차가 실제로 잰 코드와 같다.

이 후보의 수정은 astra 쪽에서 한다. 한 파일에 오너를 둘 두지 않는다.

## v11은 이제 오탐 하나 거리다

H2 전에는 v11이 TP=2라 **오탐을 0으로 해도 최대 F1이 0.500**이었다 — 0.6이 원리적으로
불가능했다. 지금 4/4/2다.

| v11 상태 | P | R | F1 | Macro |
| --- | ---: | ---: | ---: | ---: |
| 지금 (4/4/2) | 0.500 | 0.667 | 0.571429 | 0.620382 |
| 오탐 1건 제거 (4/3/2) | 0.571 | 0.667 | **0.615385** | **0.622213** |

그 한 건은 `PPS-DEV-040`이고, astra가 원인을 특정해 뒀다 — scope 인용이
`2026년 모범이장 해외 선진지연수 용역`인데 본문은 해외연수·여행업 자격을 요구한다.
**모델의 scope 오분류**이지 H2 규칙의 결함이 아니다. astra는 이 한 건을 지우는
ID·여행업 예외를 넣지 않았다. 맞는 판단이다.

## 이 보고가 증명하지 않는 것

- **`script.py`를 안 고쳤다.** 두 후보 다 채택 전이다. 실제 회차·서버 제출에 들어간 적이 없다.
- **재생이라 회차 churn이 없다.** 같은 모델 출력을 쓰므로 여기 차이는 후처리의 효과다.
  **프롬프트가 바뀌면 다시 재야 한다.**
- **H2의 채택 조건은 아직 안 찼다.** 무라벨 배율 0.933은 **1,000/20,000(5%)** 위의 값이고
  `summary.json`이 `complete: false`다. 그리고 그것은 **술어 발화율**이지 v11 TP/FP가 아니다.
- **A4의 v23 규칙은 무라벨 배율 0.05다.** dev의 +0.214가 비공개 집합에서 그대로 나온다고
  읽지 않는다.
- dev 200건 수치다. 같은 코드의 dev 0.599 대 서버 0.508이 그 간격이다.

## 재현

```powershell
python -X utf8 tools/replay_run.py --case reports/runs/colab-1789902969401579900/dev-debug --verify
python -X utf8 tools/replay_run.py --case reports/runs/colab-1789902969401579900/dev-debug `
  --output-dir reports/team-c/a4-a5-combined/head-c81644d-replay
python -X utf8 tools/replay_run.py --case reports/runs/colab-1789902969401579900/dev-debug `
  --candidate experiments/a4_a5_combined_candidate.py `
  --output-dir reports/team-c/a4-a5-combined/combined-replay
python -X utf8 tools/score.py --truth open/dev_labels.csv `
  --pred reports/team-c/a4-a5-combined/combined-replay/submission.csv `
  --output-dir reports/team-c/a4-a5-combined/combined-score
python -X utf8 tools/compare_runs.py --items v6,v9,v11,v23 `
  --before reports/team-c/a4-a5-combined/head-c81644d-replay/submission.csv `
  --after reports/team-c/a4-a5-combined/combined-replay/submission.csv
python -X utf8 experiments/a5_v11_absence_candidate.py   # astra self-check
python -X utf8 experiments/a4_a5_combined_candidate.py   # 배선 검사
python -X utf8 -m pytest -q
```
