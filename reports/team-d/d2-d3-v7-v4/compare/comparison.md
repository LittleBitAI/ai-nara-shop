# 회차 대조

```text
기준 reports/runs/colab-1789655036303880754/dev-debug/submission.csv
후보 reports/team-d/d2-d3-v7-v4/replay/submission.csv
정답 open/dev_labels.csv · 공고 200건 · 대상 v8, v7, v4

Macro F1  0.218203523963 → 0.337251143011  (+0.119047619048)
바뀐 셀   19 / 4800   (대상 밖 0)

churn    회차 간 실측 25~43셀, 그 Macro F1 영향 0.000008~0.003129 (8쌍)
         이번 차이는 관측 범위를 넘는다. 그래도 항목별 변화를 함께 확인한다.
         근거 reports/runs/reproducibility.md

항목           TP        FP        FN                    F1  바뀐 공고
*v4      0→6       2→2       6→0     0.000000→0.857143    6  PPS-DEV-042, PPS-DEV-051, PPS-DEV-053, PPS-DEV-059, PPS-DEV-06, PPS-DEV-062
*v7      0→7       0→0       7→0     0.000000→1.000000    7  PPS-DEV-039, PPS-DEV-050, PPS-DEV-054, PPS-DEV-063, PPS-DEV-072, PPS-DEV-09…
*v8      0→6       0→0       6→0     0.000000→1.000000    6  PPS-DEV-042, PPS-DEV-048, PPS-DEV-05, PPS-DEV-054, PPS-DEV-071, PPS-DEV-11

* = --items로 지정한 대상 항목. 대상 밖 변화는 회귀 후보다.
이 대조는 두 CSV만 본다. 실행 환경·시간·모델 호출 성공은 각 실행의 manifest.json이 소유한다.
```
