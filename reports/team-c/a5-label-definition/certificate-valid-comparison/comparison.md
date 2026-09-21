# 회차 대조

```text
기준 reports/team-c/a5-label-definition/head-replay/submission.csv
후보 reports/team-c/a5-label-definition/certificate-valid-replay/submission.csv
정답 open/dev_labels.csv · 공고 200건 · 대상 v11, v13, v24

Macro F1  0.593846165415 → 0.591320912890  (-0.002525252525)
바뀐 셀   1 / 4800   (대상 밖 1)

churn    과거 코드의 회차 간 실측 17~45셀, 그 Macro F1 영향 0.000008~0.010088 (13쌍)
         이번 차이는 과거 관측 범위 안이다. 현재 코드의 churn 판정은 아니다.
         대상 항목의 TP/FP/FN이 가설대로 움직였는지로 판단한다.
         새 후보는 같은 ZIP을 재실행해 그날 그 코드의 churn을 직접 잰다.
         근거 reports/runs/reproducibility.md

항목           TP        FP        FN                    F1  바뀐 공고
*v11     2→2       3→3       4→4     0.363636→0.363636    0
 v12     4→4       1→2       2→2     0.727273→0.666667    1  PPS-DEV-110
*v13     4→4       9→9       2→2     0.421053→0.421053    0
*v24     5→5      36→36      3→3     0.204082→0.204082    0

* = --items로 지정한 대상 항목. 대상 밖 변화는 회귀 후보다.
이 대조는 두 CSV만 본다. 실행 환경·시간·모델 호출 성공은 각 실행의 manifest.json이 소유한다.
```
