# A3 회차 3 — 측정값

2026-09-20. 주 세션이 `artifacts/inbox`의 결과 ZIP을 등록하고 잰 값이다.
해석을 적지 않는다. 각 수치의 출처 경로를 함께 적는다.

## 등록

`colab-1789894949866134428` → `reports/runs/colab-1789894949866134428/`
코드 `cc7c9719b60b84f1fe6a713969ca886044066d75`. `dev-debug` 원응답 200건 있음.

## 1. 목표 세 항목

| 항목 | 회차 2 `…9904147841755` | 회차 3 `…4949866134428` |
| --- | --- | --- |
| v10 | 0/0/7 | 0/1/7 |
| v18 | 0/1/7 | 1/2/6 (F1 0.200) |
| v20 | 0/0/5 | 0/0/5 |

기준 재생 `6bb692d` 0.547985038075 대비 0.544041527881 (−0.003943510194),
바뀐 셀 39/4800, 대상 밖 35. 이 차이는 과거 회차 간 실측 churn 범위(17~45셀,
0.000008~0.010088) 안이다.

## 2. 새 필드의 200건 분포

`reports/runs/colab-1789894949866134428/dev-debug/diagnostics.jsonl`의
`phase == "company_size"` 응답 200건을 그대로 셌다.

| 필드 | 분포 |
| --- | --- |
| `requirements_complete` | yes 189 · no 11 |
| `direct_production` | not_required 93 · present 55 · absent 36 · unknown 16 |
| `software_business` | no 189 · yes 10 · unknown 1 |
| `software_participation` | unknown 117 · absent 82 · present 1 |

## 3. v10 양성 7건이 막힌 자리

게이트(`scope == "competitive"` + `scope_quote` 원문 검증)는 7/7 열렸다.

| 공고 | `scope` | 인용 검증 | `direct_production` |
| --- | --- | --- | --- |
| `PPS-DEV-061` | competitive | 통과 | not_required |
| `PPS-DEV-062` | competitive | 통과 | not_required |
| `PPS-DEV-064` | competitive | 통과 | not_required |
| `PPS-DEV-068` | competitive | 통과 | not_required |
| `PPS-DEV-069` | competitive | 통과 | not_required |
| `PPS-DEV-075` | competitive | 통과 | present |
| `PPS-DEV-13` | competitive | 통과 | present |

양성 7건 중 `absent`는 0건이다.

`scope == "competitive"` 74건 전체의 `direct_production`:
present 50 · not_required 15 · unknown 6 · absent 3.

`direct_production == "absent"` 36건 전체 중 `scope == "competitive"`는 3건,
v10 정답 양성은 0건이다.

## 4. v20 양성 5건이 막힌 자리

| 공고 | `software_business` | 인용 검증 | `software_participation` |
| --- | --- | --- | --- |
| `PPS-DEV-131` | yes | 통과 | unknown |
| `PPS-DEV-132` | no | — | unknown |
| `PPS-DEV-133` | yes | 실패 (인용이 원문에 없다) | unknown |
| `PPS-DEV-134` | yes | 통과 | unknown |
| `PPS-DEV-24` | yes | 통과 | unknown |

`software_business == "yes"` 10건 전체의 `software_participation`:
unknown 9 · present 1 · absent 0.
그 10건 중 v20 정답 양성은 4건, 음성은 6건이다.

`software_participation == "absent"` 82건 전체 중
`software_business == "yes"`는 0건, v20 정답 양성은 0건이다.

## 5. 두 필드에 공통으로 관측된 것

| | `absent` 총 건수 | 그 중 게이트가 열린 것 | 그 중 정답 양성 |
| --- | ---: | ---: | ---: |
| `direct_production` | 36 | 3 | 0 |
| `software_participation` | 82 | 0 | 0 |

## 6. v18 — 첫 TP와 남은 6건의 사유

TP는 `PPS-DEV-041` 1건이다. `verify_company_size`가 각 양성에 대해 돌려준 사유:

| 공고 | `scope` | `qualification` | `입찰추정가격` | 사유 | v18 |
| --- | --- | --- | ---: | --- | --- |
| `PPS-DEV-038` | general | sme_allowed | 34,090,909 | `unverified_qualification` | 판정 없음 |
| `PPS-DEV-039` | competitive | small_only | 63,636,364 | `outside_general_scope` | 0 |
| `PPS-DEV-040` | competitive | unrestricted | 80,727,273 | `outside_general_scope` | 0 |
| `PPS-DEV-041` | general | unrestricted | 77,272,727 | `decided` | 1 |
| `PPS-DEV-043` | general | sme_allowed | 61,264,545 | `decided` | 0 |
| `PPS-DEV-044` | competitive | sme_allowed | 55,454,545 | `outside_general_scope` | 0 |
| `PPS-DEV-22` | general | unrestricted | 72,727,273 | `absence_not_observable` | 판정 없음 |

회차 2에서 `small_only`였던 `PPS-DEV-040`·`041`·`22`가 이번에 각각
`unrestricted`·`unrestricted`·`unrestricted`다.

## 7. 대상 밖 항목 (기준 재생 대비)

| 항목 | 기준 TP/FP/FN → 회차 3 | F1 |
| --- | --- | --- |
| v17 | 5/9/1 → 4/11/2 | 0.500 → 0.381 |
| v13 | 4/8/2 → 4/10/2 | 0.444 → 0.400 |
| v21 | 4/3/2 → 4/4/2 | 0.615 → 0.571 |
| v4 | 6/2/0 → 6/3/0 | 0.857 → 0.800 |
| v5 | 5/1/2 → 5/2/2 | 0.769 → 0.714 |
| v23 | 1/1/4 → 1/2/4 | 0.286 → 0.250 |
| v24 | 4/36/4 → 5/31/3 | 0.167 → 0.227 |
| v9 | 5/12/1 → 5/12/1 | 0.435 → 0.435 |
| v15 | 5/2/1 → 5/2/1 | 0.769 → 0.769 |

## 재현

```powershell
python -X utf8 tools/compare_runs.py --items v10,v18,v20 `
  --before reports/team-c/scope-wiring-replay/submission.csv `
  --after  reports/runs/colab-1789894949866134428/dev-debug/submission.csv
```

2~6절은 `reports/runs/colab-1789894949866134428/dev-debug/diagnostics.jsonl`과
`open/dev.jsonl`·`open/dev_labels.csv`만으로 계산했다. `script.py`는 고치지 않았다.

## 다음 회차의 요구

v10·v18·v20의 TP가 셋 다 0을 넘어야 한다. 발화 건수 증가가 아니라 TP다.
나머지 통과 조건은 `docs/tasks/a3-zero-items.md`가 소유한다 — 일반화 검사,
무라벨 발화율(W5), FP 동반 보고, 시간 예산, 같은 ZIP 재실행 churn.
