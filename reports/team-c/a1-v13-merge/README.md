# A-1 — v13 두 검증 경로의 합성 규칙

담당 C · 2026-09-21 · **CPU 재생만. 모델 호출 0회 · 추가 시간 0초.**

## 0. 한 줄

company 가 **검증된 인용으로 scope 를 `general` 이라고 확정**했을 때 그것과 모순되는
앞 단계 v13 양성을 유지하지 않는다. **FP 9 → 8 · TP 4 유지 · 대상 밖 0셀.**

## 1. 기준·후보·명령

| 항목 | 값 |
| --- | --- |
| 기준 commit | `7ab8e17` |
| 기준 CSV | **HEAD 재생** `reports/runs/colab-1789902969401579900/dev-debug` · Macro 0.593846165415 |
| 후보 | `experiments/c_v13_merge_candidate.py` (`verify_company_size` 만 정의) |
| 검사 | `tests/test_c_v13_merge_candidate.py` · 10건 |
| 변경 안 한 것 | `script.py` · `tools/` · `notebooks/` — `git diff --stat` 빈 출력 |

```bash
python -X utf8 tools/replay_run.py --case reports/runs/colab-1789902969401579900/dev-debug \
  --output-dir <head>
python -X utf8 tools/replay_run.py --case reports/runs/colab-1789902969401579900/dev-debug \
  --candidate experiments/c_v13_merge_candidate.py --output-dir <cand>
python -X utf8 tools/compare_runs.py --before <head>/submission.csv --after <cand>/submission.csv \
  --truth open/dev_labels.csv --items v13 --output-dir <cmp>
```

HEAD 재생이 회차 CSV 와 동일함을 먼저 확인했다(`재생 200건 · 회차 CSV와 동일`).

## 2. 경로 분해 — 보고서의 13건을 원응답에서 재확인했다

`five-stuck-analysis.md` 의 분해를 다시 유도하지 않고, 같은 결론이 나오는지만 확인했다.
`baseline → SME → company → 후처리` 를 재생기와 같은 순서로 태운 결과다.

| 공고 | 정답 | base | sme | company | scope | catalog | 경로 |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| 16 | 1 | 1 | 0 | **1** | competitive | True | company 되살림 |
| 077 | 1 | 1 | 0 | **1** | competitive | True | company 되살림 |
| 078 | 1 | 1 | 0 | **1** | competitive | True | company 되살림 |
| 069 | 1 | 1 | 1 | — | competitive | None | **앞 단계 보존** |
| 056 | 0 | 1 | 1 | **1** | competitive | True | company |
| 122 | 0 | 1 | 1 | **1** | competitive | True | company |
| 148 | 0 | 1 | 1 | **1** | competitive | True | company |
| 184 | 0 | 1 | 0 | **1** | competitive | True | company 되살림 |
| 192 | 0 | 0 | — | **1** | competitive | True | company 신규 |
| 198 | 0 | 1 | 0 | **1** | competitive | True | company 되살림 |
| **03** | **0** | 1 | 1 | — | **general** | None | **앞 단계 보존 · scope 모순** |
| 059 | 0 | 1 | 1 | — | competitive | None | 앞 단계 보존 |
| 193 | 0 | 1 | 1 | — | competitive | None | 앞 단계 보존 |

company 가 1 을 쓴 것 9건(TP 3 · FP 6), 앞 단계 보존 4건(TP 1 · FP 3)으로 보고서와 일치한다.
FN 은 074(company 무응답)·076(baseline 0, sme_allowed)로 이 후보의 대상이 아니다.

**보존 4건 중 company scope 가 v13 과 모순되는 것은 `03` 하나뿐이다.**
`03` 의 `reason` 은 `decided` 다 — scope 인용이 원문에서 확인됐고 금액 밴드까지 정해졌다.
나머지 셋은 `outside_general_scope`(competitive)이라 모순이 아니고, catalog 가 `None` 이라
company 가 v13 을 못 쓴 것뿐이다.

## 3. 규칙 — 새 판별축이 아니다

```
검증된 scope 가 general 이고 company 가 v13 을 쓰지 않았으면 → v13 = 0
```

근거는 **항목 정의**다. v13 의 공식 항목명은 "**중기간 경쟁제품** 소기업, 소상공인 제한"이고
(`docs/items.md`), 운영 코드 `company_size_products()` 도 같은 문장을 근거로 v13 을
`competitive` 에서만 올린다. **그 전제를 보존 경로에도 같게 적용한 것**이다.

**기각된 여섯 축으로 가르지 않는다.** 금액구간·scope·qualification·role·직생언급·인용문장이
정탐과 오탐에서 같은 값이라는 결론은 그대로다 — 이 규칙은 **경쟁제품 scope 안에서는
아무것도 가르지 않는다.** 적용 대상 밖인 건 하나를 적용 대상 밖이라고 적을 뿐이다.

**올리지 않는다.** 어떤 입력에서도 v13=1 을 새로 쓰지 않는다(검사로 고정).
`unverified_scope` 면 아무것도 하지 않는다(기본 판정 보존).

## 4. 결과

| 항목 | 전 | 후 | 바뀐 공고 |
| --- | --- | --- | --- |
| **v13** | 4 / 9 / 2 · F1 0.421053 | **4 / 8 / 2 · F1 0.444444** | `PPS-DEV-03` |

- **바뀐 셀 1 / 4800 · 대상 밖 0셀.**
- Macro F1 0.593846165415 → 0.594820824285 (**+0.000975**).
  **이 수로 개선을 주장하지 않는다.** 과거 회차 쌍 churn 이 최대 0.004689 이고 이 차이는
  그 안이다. 판단 근거는 대상 항목의 TP/FP/FN 이다.
- TP 4건(069·077·078·16) 전부 유지. 검사가 건별로 고정한다.

## 5. 발화율 — 적용 대상과 셀 변경은 다른 수다

| | dev 200건 | 무라벨 20,000건 |
| --- | ---: | --- |
| 적용 대상(검증 scope=general, company v13 미기재) | **118건 · 59.0%** | **측정 불가** |
| 실제 셀 변경 | **1건 · 0.5%** | 측정 불가 |

**적용 대상이 넓은 것 자체는 위험이 아니다.** 117건은 앞 단계도 이미 0 이라 명시적 0 을
써도 같은 값이다. **위험은 겹침에 있다** — 다른 회차에서 이 118건 중 어느 하나에 앞 단계
양성이 남으면 그것도 닫는다. dev 에서 겹친 1건은 FP 였지만 그것이 보장은 아니다.

**무라벨 배율은 이 저장소의 자료로 측정할 수 없다.** 이유를 그대로 적는다.

- `open/train_unlabeled.jsonl` 이 저장소에 없다(공개 push 때 제외된 790MB 파일).
- 이 규칙의 발화 조건은 **모델의 `company_size` 사실**(scope·scope_quote)이다. A4 의 W5 가
  잰 것은 문서·메타 같은 **입력 신호**라 원문만으로 셀 수 있었지만, 이것은 아니다.
- 무라벨 company 응답은 H2 에서 2,000건 수집됐으나 그 사실 파일이 `reports/` 에 없다.

측정하려면 무라벨 원본과 그 위의 company 응답이 함께 필요하다. **대신 입력 신호로
대체 추정하지 않았다** — 그것은 다른 것을 재는 것이다.

## 6. 시간·증거 수준

추가 모델 호출 **0회**, 추가 추론 시간 **0초**. 서버 예산(6,380/7,200초)에 영향 없다.
`verify_company_size` 안에서 이미 계산된 사실을 한 번 더 읽을 뿐이다.

**증거 수준: CPU 재생.** 저장 응답 재사용이며 **실제 GPU 회차도 대회 서버도 아니다.**
`18f07e5` 에서 dev↔서버 간격이 15% 였다. dev 에서 FP 1건 감소가 서버에서 같다고 읽지 않는다.

## 7. 채택 / 대기

| 대상 | 판단 |
| --- | --- |
| 합성 규칙 | **합격선 충족.** FP 감소 1 · TP 4 유지 · 대상 밖 0셀 |
| 채택 여부 | **대기.** 아래 두 가지를 A 가 저울질해야 한다 |

**작은 이득이다.** FP 9→8 은 항목당 양성 5~8건 위에서 F1 을 0.42→0.44 로 올린다.
한 건이 F1 을 0.1 넘게 움직이는 규모이므로 이 +1 을 과대평가하지 않는다.

**대신 비용이 0 이다.** 추가 호출·시간이 없고 대상 밖 셀을 건드리지 않으며, 규칙이
새 판별축이 아니라 이미 운영 중인 항목 정의를 한 경로에 더 적용한 것이다.

## 8. 미확인 사항

- **무라벨 발화 배율.** §5 의 이유로 이 저장소에서 못 잰다.
- **겹침의 안정성.** 118건 중 앞 단계 양성이 남는 것이 회차마다 몇 건인지 모른다.
  dev 한 회차에서 1건이었다. 같은 ZIP 재실행 churn 으로 이 수가 흔들리는지 안 쟀다.
- **`03` 의 라벨 근거.** company 가 general 이라 한 것이 옳은지는 확인하지 않았다.
  이 규칙은 "company 가 general 이라 확정하면 v13 은 적용 대상이 아니다" 만 쓴다.
- 실제 GPU 회차·서버 점수.
