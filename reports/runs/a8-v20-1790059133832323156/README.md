# a8-v20 회차 2 — 주입이 v20 을 한 칸도 못 움직였다

2026-09-22 등록. 두 회차 중 2 번째이며 짝은 [회차 1](../a8-v20-1790057577391794027/README.md)다.
판정 전문은 [결과 보고서](../../team-c/a8-v20-annex/results.md)가 소유하고
판정 기준은 [두 회차 실행 설계](../../../docs/tasks/a8-v20-two-episode-run.md)가 소유한다.
이 문서는 등록·대조 기록이다.

이 회차는 제출 파이프라인 회차가 아니다. `company_size` 한 단계만 GPU 로 돌리고
나머지는 보관 원응답으로 재생한 A/B 이며 제출 ZIP 이 없다.
아래 값을 [색인](../../../docs/runs.md#색인)의 전체 GPU 점수와 같은 저울로 읽지 않는다.

## 네 측정

| 군 | 소비자 | Macro F1 | v20 TP/FP/FN | company 단계초 | 서버 조건부 환산초 |
| --- | --- | ---: | --- | ---: | ---: |
| a8 | off | 0.589442740036 | 1/4/4 | 265.742 | 6546.832 |
| a8 | on | 0.589442740036 | 1/4/4 | 265.742 | 6546.832 |
| control | off | 0.586932341938 | 1/4/4 | 247.898 | 6388.124 |
| control | on | 0.586932341938 | 1/4/4 | 247.898 | 6388.124 |

군 간 차이는 Macro F1 0.586932341938 → 0.589442740036 (+0.002510398099) 이고 바뀐 셀 7/4,800 인데 전부 대상 밖이다.
대상 밖 변화: v10 PPS-DEV-041·PPS-DEV-146, v12 PPS-DEV-106, v15 PPS-DEV-18, v16 PPS-DEV-037, v17 PPS-DEV-035, v18 PPS-DEV-154.

## 기전은 서지 않았다

`v20-audit.json` 의 `paired_changes` 는 4건이고 전부 `other` 다.
`verified_quote`·`verified_absence`·`fallback_only` 는 0건이다.

| ID | 바뀐 필드 | gain_kind |
| --- | --- | --- |
| `PPS-DEV-25` | requirements_complete no→yes | `other` |
| `PPS-DEV-135` | software_business yes→no, v20_applicable True→False, software_business_quote_state exact→null | `other` |
| `PPS-DEV-158` | requirements_complete no→yes | `other` |
| `PPS-DEV-162` | requirements_complete yes→no | `other` |

주입 뒤에도 참여 조항 인용은 400응답 중 0건이다 — `participation_nonnull` 이 두 군 모두 0/200 으로
H4 보관 기준과 같다. `v20_write_1` 5건, `v20_write_0` 0건, `v20_preserve` 195건도 네 군이 모두 같다.
의미 검토는 미완료다(`semantic_review_complete=false`, 위 4건 모두 `pending`).

## 같은 군 반복 churn

회차 1 의 같은 군과 대조한 `repeat-<군>-<소비자>.json` 네 개가 이 폴더에 있다.

| 군 | 바뀐 셀 | Macro F1 차이 | 바뀐 공고 | v20 churn |
| --- | ---: | ---: | --- | ---: |
| control | 2 | -0.004075846181 | v10 `PPS-DEV-23`, v16 `PPS-DEV-037` | 0 |
| a8 | 1 | +0.000974658869 | v10 `PPS-DEV-09` | 0 |

OFF/ON 이 같은 조건이므로 군별 두 파일은 같은 값이며 독립 반복 네 번이 아니다.
control 군의 회차 간 churn 0.004076 이 이 회차의 군 간 차이 0.002510 보다 크다.

## 불변식과 실패

- 네 군 모두 OFF/ON 혼합 CSV 가 바이트 동일이다. `consumer-comparison.json` 의 바뀐 셀 0 과 일치한다.
- `budget.json`: 추가 축소 0, 문서 동일, 절단 0, 예약 1,024 · 예산 15,296.
- `diagnostics.jsonl`: 1,618 이벤트, 실제 호출 400회, 실패 0, 재시도 0, 최종 미복구 0.
- 두 군 모두 단계 상한 339.178초 안이다.

## 등록

`register_run.py` 는 `colab-results-*.zip` 과 `submit.zip` 한 쌍만 받으므로
이 회차는 [보관 규약](../../../docs/runs.md#보관-규약)대로 손으로 등록했다.

- ZIP `a8-v20-results-1790059133832323156.zip`, SHA-256 `7880e1b6097b8591de8cb6637de82ef8e132190ce7104b0f7d49076c41ebe101`
- 코드 `e6d9b98b7a40c6a6f563802445c24e2e61d9a3af` (`source.json` 의 `requested_ref` 와 일치)
- 입력 30건 `input-check.status = verified`, 명세는 `reports/team-c/a8-v20-annex/inputs.json`
- 등록 전 `hf_` 토큰값·`api_key`·`Bearer`·개인 절대 경로 패턴을 검사했고 위반 0건이다.
- 큰 파일 세 개는 넣지 않았다. 경로·크기·sha256·이유는 `manifest.json` 의 `raw_responses` 에 있다.
  회차당 70.2MB 이고 두 회차 143MB 라 사용자 결정으로 뺐다. `docs/runs.md` 의 제외선 50MB 를 넓힌 결정이다.
- 화면 항목은 `a8-v20-1790059133832323156.control-off`·`.control-on`·`.a8-off`·`.a8-on` 네 개다.
- 수치는 회차가 남긴 파일에서 그대로 옮겼고 다시 계산하지 않았다.

## 이 기록이 증명하지 않는 것

- 전체 GPU 파이프라인 점수가 아니다. `company_size` 400응답 관측 + 보관 기본/SME 응답의 혼합 재생이다.
- 서버 점수가 아니다. 같은 코드의 dev 와 서버 사이 간격은 알려져 있다.
- 채택된 것이 없다. `script.py`·운영 코드는 바뀌지 않았다.
- 실행 실패가 아니다. 계약·불변식·완료·시간을 모두 충족한 성능 기각이다.
- 한 회차만으로는 반복을 말하지 못한다. 짝 회차와 함께 읽는다.
