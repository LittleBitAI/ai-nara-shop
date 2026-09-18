# 회차 대조

```text
기준 reports/runs/colab-1789655036303880754/dev-debug/submission.csv
후보 reports/team-b/b1-v19-replay/submission.csv
정답 open/dev_labels.csv · 공고 200건 · 대상 v19

Macro F1  0.218203523963 → 0.220909151669  (+0.002705627706)
바뀐 셀   5 / 4800   (대상 밖 0)

churn    회차 간 실측 25~43셀, 그 Macro F1 영향 0.000008~0.003129 (8쌍)
         이번 차이는 그 범위 안이다. Macro F1만으로는 아무것도 말할 수 없다.
         대상 항목의 TP/FP/FN이 가설대로 움직였는지로 판단한다.
         근거 reports/runs/reproducibility.md

항목           TP        FP        FN                    F1  바뀐 공고
*v19     6→6      21→16      0→0     0.363636→0.428571    5  PPS-DEV-064, PPS-DEV-088, PPS-DEV-110, PPS-DEV-158, PPS-DEV-180

* = --items로 지정한 대상 항목. 대상 밖 변화는 회귀 후보다.
이 대조는 두 CSV만 본다. 실행 환경·시간·모델 호출 성공은 각 실행의 manifest.json이 소유한다.
```
