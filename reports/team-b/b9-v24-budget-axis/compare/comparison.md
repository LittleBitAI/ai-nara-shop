# 회차 대조

```text
기준 reports/team-b/b9-v24-budget-axis/head-replay/submission.csv
후보 reports/team-b/b9-v24-budget-axis/candidate-replay/submission.csv
정답 open/dev_labels.csv · 공고 200건 · 대상 v24

Macro F1  0.618427228373 → 0.621205006151  (+0.002777777778)
바뀐 셀   1 / 4800   (대상 밖 0)

churn    과거 코드의 회차 간 실측 17~45셀, 그 Macro F1 영향 0.000008~0.010088 (13쌍)
         이번 차이는 과거 관측 범위 안이다. 현재 코드의 churn 판정은 아니다.
         대상 항목의 TP/FP/FN이 가설대로 움직였는지로 판단한다.
         새 후보는 같은 ZIP을 재실행해 그날 그 코드의 churn을 직접 잰다.
         근거 reports/runs/reproducibility.md

항목           TP        FP        FN                    F1  바뀐 공고
*v24     4→5      12→12      4→3     0.333333→0.400000    1  PPS-DEV-29

* = --items로 지정한 대상 항목. 대상 밖 변화는 회귀 후보다.
이 대조는 두 CSV만 본다. 실행 환경·시간·모델 호출 성공은 각 실행의 manifest.json이 소유한다.
```
