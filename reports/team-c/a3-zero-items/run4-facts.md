# A3 회차 4 — 측정값

2026-09-20. 주 세션이 `artifacts/inbox`의 결과 ZIP을 등록하고 잰 값이다.
해석을 적지 않는다. 각 수치의 출처 경로를 함께 적는다.

## 등록

`colab-1789898958261656296` → `reports/runs/colab-1789898958261656296/`
코드 `ec3dee43a85200a585410b145cbbb0097158e5eb`. `dev-debug` 원응답 200건 있음.

## 1. 목표 세 항목

| 항목 | 회차 3 `…4949866134428` | 회차 4 `…8958261656296` |
| --- | --- | --- |
| v10 | 0/1/7 | 4/7/3 · F1 0.444 |
| v18 | 1/2/6 · F1 0.200 | 0/2/7 · F1 0.000 |
| v20 | 0/0/5 | 1/4/4 · F1 0.200 |

`score/metrics.json` Macro F1 0.5743735227782543(dev).
`dev-debug` 기준 0.573802514249, 기준 재생 `6bb692d` 0.547985038075 대비
+0.025817476175, 바뀐 셀 52/4800, 대상 밖 34. 이 차이는 과거 회차 간 실측 churn
범위(17~45셀, 0.000008~0.010088)를 넘는다.

## 2. v18 — TP 1이 0으로 되돌아갔다

회차 3의 유일한 TP였던 `PPS-DEV-041`의 `scope`가 바뀌었다.

| 공고 | `scope` 3 → 4 | `qualification` 3 → 4 | 회차 4의 사유 | v18 |
| --- | --- | --- | --- | --- |
| `PPS-DEV-038` | general → general | sme_allowed → sme_allowed | `unverified_qualification` | 판정 없음 |
| `PPS-DEV-039` | competitive → competitive | small_only → small_only | `outside_general_scope` | 0 |
| `PPS-DEV-040` | competitive → competitive | unrestricted → unrestricted | `outside_general_scope` | 0 |
| **`PPS-DEV-041`** | general → competitive | unrestricted → unrestricted | `unverified_scope` | 판정 없음 |
| `PPS-DEV-043` | general → general | sme_allowed → sme_allowed | `decided` | 0 |
| `PPS-DEV-044` | competitive → competitive | sme_allowed → sme_allowed | `outside_general_scope` | 0 |
| `PPS-DEV-22` | general → general | unrestricted → unrestricted | `absence_not_observable` | 판정 없음 |

회차 4의 v18 양성 7건 `scope`: competitive 4 · general 3.
v18 판정은 `_company_size_bands`를 거치고, 그 함수는 `scope`가 competitive/other면
`outside_general_scope`로 밴드 다섯을 전부 0으로 돌려준다.

## 3. v10 — 양성 7건과 오탐 7건

게이트(`scope == "competitive"` + `scope_quote` 원문 검증)는 7/7 열렸다.

| 공고 | 판정 | `direct_production_quote` | 막힌 자리 |
| --- | --- | --- | --- |
| `PPS-DEV-061` | 1 | null | — |
| `PPS-DEV-062` | 1 | null | — |
| `PPS-DEV-064` | 1 | null | — |
| `PPS-DEV-068` | 1 | null | — |
| `PPS-DEV-069` | 0 | null | `complete`의 "안 잘림"이 False |
| `PPS-DEV-075` | 0 | 있음 | 인용이 있어 present로 읽힘 |
| `PPS-DEV-13` | 0 | 있음 | 인용이 있어 present로 읽힘 |

오탐 7건: `PPS-DEV-039` `040` `059` `12` `126` `128` `23`.
**일곱 전부 `scope == "competitive"`이고 카탈로그 대조가 `None`이다.**

200건 `direct_production_quote`: 있음 58 · null 142.

### 카탈로그로 조이면 TP가 다 죽는다 — 채택하지 않았다

| v10 읽기 | TP | FP | FN | F1 |
| --- | ---: | ---: | ---: | ---: |
| 회차 4 그대로 | 4 | 7 | 3 | 0.444 |
| + `competitive_product(...) is True` | 0 | 0 | 7 | 0.000 |
| + `competitive_product(...) is not False` | 4 | 7 | 3 | 0.444 |

TP 4건(`061`·`062`·`064`·`068`)의 카탈로그 대조가 **전부 `None`**이다.
오탐 7건과 같은 값이라 이 축으로는 안 갈린다.

## 4. v20 — 조항 인용이 200건 전부 null이다

`software_participation_quote`가 200건 중 200건 null이다.

| 공고 | 판정 | `software_business` | 막힌 자리 |
| --- | --- | --- | --- |
| `PPS-DEV-131` | 0 | yes | `완전관측 == False`, dropped 문서 있음 |
| `PPS-DEV-132` | 0 | no | 게이트 안 열림 |
| **`PPS-DEV-133`** | 1 | yes | — |
| `PPS-DEV-134` | 0 | yes | `완전관측 == False`, dropped 문서 있음 |
| `PPS-DEV-24` | 0 | yes | `완전관측 == False`, dropped 문서 있음 |

오탐 4건: `PPS-DEV-056` `064` `068` `144`.

`131`·`134`·`24`는 `requirements_complete == "no"`이기도 하다.

## 5. 관측 완전성 조건이 걸리는 비율

`verify_document_requirements`의 두 조건을 200건에 그대로 계산했다.

| 조건 | 전부 참인 건수 |
| --- | ---: |
| `complete` (v10용) | 110 / 200 |
| `software_complete` (v20용) | 129 / 200 |

`requirements_complete`: yes 190 · no 10.
즉 나머지는 `input_completeness.완전관측`·`dropped_doc_counts`·절단 표시가 막는다.

## 6. 대상 밖 항목 (기준 재생 대비)

| 항목 | 기준 TP/FP/FN → 회차 4 | F1 |
| --- | --- | --- |
| v17 | 5/9/1 → 4/15/2 | 0.500 → 0.320 |
| v13 | 4/8/2 → 4/10/2 | 0.444 → 0.400 |
| v11 | 2/2/4 → 2/3/4 | 0.400 → 0.364 |
| v3 | 8/4/0 → 8/5/0 | 0.800 → 0.762 |
| v4 | 6/2/0 → 6/3/0 | 0.857 → 0.800 |
| v16 | 2/2/4 → 3/2/3 | 0.400 → 0.545 |
| v15 | 5/2/1 → 5/1/1 | 0.769 → 0.833 |
| v21 | 4/3/2 → 5/4/1 | 0.615 → 0.667 |
| v24 | 4/36/4 → 5/36/3 | 0.167 → 0.204 |
| v6 | 3/5/3 → 3/4/3 | 0.429 → 0.462 |

## 재현

```powershell
python -X utf8 tools/compare_runs.py --items v10,v18,v20 `
  --before reports/team-c/scope-wiring-replay/submission.csv `
  --after  reports/runs/colab-1789898958261656296/dev-debug/submission.csv
```

2~5절은 `reports/runs/colab-1789898958261656296/dev-debug/diagnostics.jsonl`과
`open/dev.jsonl`·`open/dev_labels.csv`만으로 계산했다. `script.py`는 고치지 않았다.

## 다음 회차의 요구

v10·v18·v20의 TP가 셋 다 0을 넘어야 한다. 발화 건수 증가가 아니라 TP다.
같은 회차에서 동시에 넘어야 한다 — 회차 3은 v18만, 회차 4는 v10·v20만 넘었다.
나머지 통과 조건은 `docs/tasks/a3-zero-items.md`가 소유한다 — 일반화 검사,
무라벨 발화율(W5), FP 동반 보고, 시간 예산, 같은 ZIP 재실행 churn.
