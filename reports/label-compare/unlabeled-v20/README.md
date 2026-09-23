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
| U | 0 → 1 (후보가 올림) | 35 |
| W | 1 → 0 (후보가 내림) | 53 |
| K | 1 → 1 | 24 |
| Z | 0 → 0 | 1,888 |

라벨 대상은 U·W·K 112건 전부다([ids.txt](ids.txt), [layers.jsonl](layers.jsonl)). 대체형이라 한쪽 층만 재면
부호를 못 정한다. 12건은 문서 탈락 공고다.

## 판정식

라벨의 양성 수를 `U1`·`W1`·`K1`, Z 층의 놓친 양성을 `Z1` 이라 하면 무라벨 2,000건에서

- 모델: TP = `K1 + W1`, 예측 77
- 후보: TP = `K1 + U1`, 예측 59
- 정답 양성 P = `K1 + W1 + U1 + Z1`

F1 = 2TP / (예측 + P) 이므로 후보가 이기는 조건은 `(K1+U1)/(59+P) > (K1+W1)/(77+P)` 이다.
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
every value of `U1` — the additions, where the legal reading is hard, do not decide the sign. Worst case
`U1 = 0`: one true positive among the removals needs `K1 ≥ 5`, two need `K1 ≥ 10`.

Every removal rests on a text fact, not a legal reading: the notice has no software-provider registration of
any kind, or it contains the 제48조 sentence. dev: 191/191 notices without registration are v20=0, 3/3 with
the sentence are v20=0.

A first regex pass over the removals found notices registering other software categories (1426, 1470) or
1468 in other wording. The candidate now abstains on any software-provider registration it cannot place
(keeps the model), adds only on 1468, and removes only on the two facts. dev replay is unchanged
(v20 5/2/0, Macro +0.026389, 10 cells, all v20). New layers: U 36, W 48, K 29 (4 abstain), Z 1,887.

[experiments/v20_fact_check.py](../../../experiments/v20_fact_check.py) asks an external LLM the two facts
(no verdict) and verifies every quote as a substring. Pass line, fixed before running: on dev
`04` `056` `064` `068` `124` `131` `144`, whose facts are known, 14/14 answers match and every `yes`
has a verified quote. Only then are the 48 removals checked. A removal the LLM reads as
"registration yes, sec48 no" with a verified quote is a possible wrong removal.

### Result — 2026-09-23

- Calibration [facts-dev7.jsonl](facts-dev7.jsonl): 14/14, every `yes` quote verified, about 7 s per notice. Passed.
- Removals [facts-w48.jsonl](facts-w48.jsonl): 48/48 answered, 0 failures. The LLM agrees with the regex on
  every notice — the 6 regex-clause removals read "registration yes, sec48 yes" and the 42 no-registration
  removals read "registration no, sec48 no". No possible wrong removal.

So every removal is one of the two facts, read the same way by two independent readers. `W1 = 0` then
holds as far as the definition does: dev has 0 positives among 191 notices without registration
(95% Wilson upper bound 1.97%, about 0.8 expected among 42) and among 3 with the sentence.
If `W1 = 0` the candidate beats the model on v20 for any `U1`. If one removal is a true positive anyway,
with pred 65 vs 77 the worst case (`U1 = 0`) still wins while `K1 ≥ 7` of the 29 kept notices are positive.

What this does not measure: the additions `U1` and whether the unlabeled 2,000 stand in for the evaluation
set. Server score is still the only direct measurement.

## 상태

Candidate revised, layers regenerated, removals fact-checked. No unlabeled v20 labels; external verdict
labelling stays blocked. Not committed, not reviewed, not in `script.py`.
