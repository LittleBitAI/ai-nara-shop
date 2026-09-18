# 회차 대조

```text
기준 reports/runs/colab-1789655036303880754/dev-debug/submission.csv
후보 reports/team-c/c3-amount-gate/regression/replay/submission.csv
정답 open/dev_labels.csv · 공고 200건 · 대상 v16, v18

Macro F1  0.218203523963 → 0.218203523963  (+0.000000000000)
바뀐 셀   0 / 4800   (대상 밖 0)

churn    회차 간 실측 29~45셀, 그 Macro F1 영향 0.000008~0.003129 (10쌍)
         이번 차이는 그 범위 안이다. Macro F1만으로는 아무것도 말할 수 없다.
         대상 항목의 TP/FP/FN이 가설대로 움직였는지로 판단한다.
         근거 reports/runs/reproducibility.md

항목           TP        FP        FN                    F1  바뀐 공고
*v16     0→0       0→0       6→6     0.000000→0.000000    0  
*v18     0→0       0→0       7→7     0.000000→0.000000    0  

* = --items로 지정한 대상 항목. 대상 밖 변화는 회귀 후보다.
이 대조는 두 CSV만 본다. 실행 환경·시간·모델 호출 성공은 각 실행의 manifest.json이 소유한다.
```
