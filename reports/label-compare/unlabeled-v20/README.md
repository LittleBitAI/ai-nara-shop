# v20 후보의 무라벨 층 — 라벨 전

[v20 후보](../../../experiments/v20_sw_clause_candidate.py)는 v20 을 모델 대신 두 결정적 신호로 **대체**한다.
dev 재생은 v20 1/4/4 → 5/2/0, Macro +0.026389 지만 양성 5건을 보고 만든 규칙이다.
서버 점수를 정하는 것은 무라벨에서 후보가 모델과 갈리는 셀이다. 그 셀을 라벨로 잰다.

## 층 — 2,000건, 모델 미사용

입력은 `feat/unlabeled-d-run` `58af667` 의 [무라벨 D 회차](../unlabeled-d/README.md) CSV 네 묶음이다
(운영 `script.py` = HEAD, 표본 순서 seed 20260923 의 앞 2,000건). 생성:
`python -X utf8 experiments/v20_unlabeled_layers.py --unlabeled <train_unlabeled.jsonl> --out <dir>`

| 층 | 모델 → 후보 | 공고 |
| --- | --- | ---: |
| U | 0 → 1 (후보가 올림) | 34 |
| W | 1 → 0 (후보가 내림) | 46 |
| K | 1 → 1 (6 은 후보 보류, 모델 유지) | 31 |
| Z | 0 → 0 | 1,889 |

현재 후보 기준이다. 첫 판(보류 없음)은 U 35 · W 53 · K 24 였다.

첫 판의 라벨 대상은 U·W·K 112건 전부였다([ids.txt](ids.txt), [layers.jsonl](layers.jsonl)). 대체형이라 한쪽 층만 재면
부호를 못 정한다. 12건은 문서 탈락 공고다.

## 판정식

라벨의 양성 수를 `U1`·`W1`·`K1`, Z 층의 놓친 양성을 `Z1` 이라 하면 무라벨 2,000건에서

- 모델: TP = `K1 + W1`, 예측 77
- 후보: TP = `K1 + U1`, 예측 65 (첫 판 59)
- 정답 양성 P = `K1 + W1 + U1 + Z1`

F1 = 2TP / (예측 + P) 이므로 후보가 이기는 조건은 `(K1+U1)/(65+P) > (K1+W1)/(77+P)` 이다.
`Z1` 은 라벨하지 않으므로 0 과 dev 비율(FN 0/200 이던 후보 기준 0, 모델 기준 4/200 → 40)의
양 끝에서 둘 다 계산해 부호가 같을 때만 채택 근거로 쓴다.

## 라벨러 보정이 먼저다

기존 외부 라벨(`opus5*`·`opus55-recall*`)에는 v20 dev 양성이 한 건도 없다. v20 에서 라벨러가
양성을 얼마나 잡고 음성을 얼마나 지키는지 잰 적이 없다. dev 13건으로 먼저 잰다.

- 양성 5: `PPS-DEV-24` `131` `132` `133` `134`
- 음성 8: `04` `056` `064` `068` `082` `124` `135` `144` — 모델·후보가 헷갈린 공고

라벨러 설정은 무라벨 D 설계 7절과 같다 — Opus 5.5 · effort medium, 도구 Read·Glob·Grep, 웹 차단,
prompt SHA-256 `ba3f89c8…`. 번들은 저장소 밖에 만든다(`tools/label_bundle.py export`).
통과선은 결과를 보기 전에 정했다 — 양성 5건 중 4건 이상을 1로, 음성 8건 중 7건 이상을 0으로 찍어야
무라벨 112건으로 넘어간다. 후보가 올리기도 내리기도 하므로 라벨러의 두 방향 오류가 다 판정을 흔든다.
`정보부족=true` 는 맞힌 것으로 세지 않는다.

라벨러의 `1`·`0` 은 초안이고 사람이 전부 확인한다 — 확인 기준은 1468 등록 요구와 제48조 참여제한 문구의
실재, 탈락 문서 여부다.

## 라벨러 보정 결과 — 통과 못 함, 112건은 돌리지 않았다

2026-09-23, 13/13 성공, 510초. [opus55-dev13.jsonl](opus55-dev13.jsonl) · [manifest](opus55-dev13.jsonl.manifest.json).

| | 1로 찍음 | 통과선 |
| --- | ---: | --- |
| 양성 5 | **0** (`131`·`134` 는 `정보부족=true`) | 4 이상 |
| 음성 8 | 0 (8/8 을 0 으로) | 7 이상 0 |

라벨러는 v20 을 13건 전부 0 으로 찍었다. 음성 8/8 은 판별이 아니라 전부 0 의 결과다.
`131`·`134` 는 1468 등록 요구를 원문 그대로 인용하고도 제안요청서 탈락을 이유로 정보부족을 냈고,
`24`·`132`·`133` 은 정보부족 없이 0 이다. 운영진이 따로 설명해야 했던 정의(S7-13)라 라벨러가
대회의 v20 을 그 정의대로 읽지 않는다. 이 라벨러의 v20 `0` 은 쓸 수 없고, 112건을 돌려도
U 층은 전부 0 으로 나와 후보가 지는 쪽으로 기울 뿐이다.

## Better method — fact-check only the removals

With the two shared counts fixed, F1 = 2TP / (predicted + P) and the candidate keeps K, so it beats the
model whenever `(K1+U1)(77+P) > (K1+W1)(pred+P)`. If no removal is a true positive (`W1 = 0`) it wins for
every value of `U1` (a tie only when `K1 = U1 = 0`) — the additions, where the legal reading is hard, do
not decide the sign. `P` includes `Z1`, the positives neither side predicts; see the bounds under Result.

Every removal rests on a text fact, not a legal reading: the notice has no software-provider registration of
any kind, or it contains the 제48조 sentence. dev: 191/191 notices without registration are v20=0, 3/3 with
the sentence are v20=0.

A first regex pass over the removals found notices registering other software categories (1426, 1470) or
1468 in other wording. The candidate now abstains on any software-provider registration it cannot place
(keeps the model), adds only on 1468, and removes only on the two facts. dev replay is unchanged
(v20 5/2/0, Macro +0.026389, 10 cells, all v20).

Review round 1 found that the sentence counted in any document. 지침 제3조② puts it in 공고문 or
제안요청서 (`script.py` `software_docs`), so only there does it remove; found only in 과업지시서 or
규격서 (40 of 20,000 unlabeled, 0 in dev) the candidate abstains. That moved `PPS-D-001203` and
`PPS-D-014608` from W to K.

Review round 2 found that a bare name counted as the sentence: `PPS-D-004071` cites 시행령 제41조
"중소 소프트웨어사업자의 기준" as a qualification, with no 대기업 or 하한 wording, and was set to 0. The
pattern is now split. The restriction itself (제48조, the pre-renumbering 제24조의2, the 하한 고시 title
"대기업인 소프트웨어사업자가 참여할 수 있는 사업금액의 하한", 사업금액별 참여, 입찰참여 제한금액) removes; a bare
`중소 소프트웨어사업자` / `대기업인 소프트웨어` abstains (56 of 20,000 unlabeled, 0 in dev). The three W
removals that had matched only the loose names (`003055`, `014211`, `018645`) quote 제24조의2 and the 하한
title and still remove. The same audit found the 제48조 citation missed half-width `｢…｣` brackets
(9 of 20,000, 0 in dev; `PPS-D-019424` was set to 1 while citing 제48조); the bracket class now has `｣`.
Layers now: U 34, W 46, K 31 (6 abstain), Z 1,889; candidate predicts 65.

[experiments/v20_fact_check.py](../../../experiments/v20_fact_check.py) asks an external LLM the two facts
(no verdict) and verifies every quote as a substring. Pass line, fixed before running: on dev
`04` `056` `064` `068` `124` `131` `144`, whose facts are known, 14/14 answers match and every `yes`
has a verified quote. Only then are the 48 removals checked. A removal the LLM reads as
"registration yes, sec48 no" with a verified quote is a possible wrong removal.

### Result — 2026-09-23

- Calibration [facts-dev7.jsonl](facts-dev7.jsonl): 14/14, every `yes` quote verified, about 7 s per notice. Passed.
- Removals [facts-w48.jsonl](facts-w48.jsonl): 48/48 answered, 0 failures. The LLM agrees with the regex on
  every notice — the 6 regex-clause removals read "registration yes, sec48 yes" and the 42 no-registration
  removals read "registration no, sec48 no". After round 1, 46 of them remain removals; the 4 clause
  removals left all have the LLM's sec48 quote inside the 공고문.

So every removal is one of the two facts, read the same way by two independent readers. `W1 = 0` then
holds as far as the definition does: dev has 0 positives among 191 notices without registration
(95% Wilson upper bound 1.97%, about 0.8 expected among 42) and among 3 with the sentence.
If `W1 = 0` the candidate beats the model on v20 for any `U1`. Worst case `U1 = 0`, pred 65 vs 77, the
smallest `K1` (of 31) that still wins:

| `W1` | `Z1 = 0` | `Z1 = 40` |
| ---: | ---: | ---: |
| 1 | 7 | 10 |
| 2 | 14 | 22 |
| 3 | 23 | 37 (impossible) |

Simulation (seed 20260923, 20,000 draws; rule-1 precision Beta(6,3) from dev 5/7, abstain-kept model
precision Beta(2,5) from dev 1/5, rule-0 positive rate Beta(1,195) from dev 0/194 for both W and Z):
P(candidate wins v20) 1.0, v20 F1 gain 5%/50% +0.264/+0.425, Macro +0.0110/+0.0177. With `Z1 = 40`
fixed: 1.0, F1 +0.202/+0.331, Macro +0.0084/+0.0138.

What this does not measure: the additions `U1` and whether the unlabeled 2,000 stand in for the evaluation
set. Server score is still the only direct measurement.

## 상태

Adopted 2026-09-23 (PR #111, held unmerged for the combined submission build). Review rounds 1–2: three P1
repaired, plus the bracket gap found auditing the same pattern. No unlabeled v20 labels; external verdict labelling stays blocked. Not in `script.py`.
