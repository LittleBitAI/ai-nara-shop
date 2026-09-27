# C7 · C9 — 바뀐 셀과 무라벨 발화 감사

담당 C · 2026-09-26 · 기준 `772ca1284c8918c1fa4ca5729cc15dfe4dedb2d4`

리뷰 [P1] — 두 후보에 **무라벨 발화와 셀 단위 감사 자료가 없다**는 지적을 받고 쟀다.
자료는 저장소에 이미 있었다(`reports/label-compare/unlabeled-d/`, 원응답 12샤드).
안 쟀던 것이다.

`audit.json` 이 공고·항목·라벨·전후 값·방향을 전부 든다. 아래는 그 요약이다.

## 1. dev — 무엇이 바뀌었나

회차 `colab-1790396310565903096` 의 `dev-debug` 원응답 위 재생이다.

| 후보 | 바뀐 셀 | 공고 · 항목 | 라벨 | 방향 |
| --- | ---: | --- | :-: | --- |
| C7 | 1 | `PPS-DEV-044` v18 | 1 | `FN → TP` |
| C9 | 1 | `PPS-DEV-126` v10 | 0 | `FP → TN` |
| C7+C9 | 2 | 위 둘 | — | — |

**C7 의 이득은 참양성 하나다.** `044` 하나가 전부이고 다른 셀은 안 움직인다.

## 2. 무라벨 — 5,500건에서 얼마나 터지나

11샤드 5,500건. `u11` 은 "문서 예산이 축소된 공고"가 있어 재생이 거부되므로 분모가
6,000 이 아니다.

| 후보 | dev | 무라벨 | 배율 | Katz 95% | Fisher p |
| --- | --- | --- | ---: | --- | ---: |
| **C7** | 1/200 | **0/5500** | 미산출 | 미산출 | 1.0000 |
| **C9** | 1/200 | 1/5500 | 0.036 | [0.002, 0.579] | 0.0690 |

### C7 — 발화가 0 이다

**"미정"이 아니라 측정된 0 이다.** 방침(2026-09-25)이 반려 사유로 삼지 않는 것은 배율이
*미정*인 경우인데, 여기는 재서 0 이 나왔다.

dev 200건에 1건, 무라벨 5,500건에 0건. 이 규칙이 닿는 공고가 **dev 그 한 건뿐**일
가능성을 이 자료로 배제할 수 없다. 규칙의 근거(운영 코드가 `checklist` 역할에서
`unrestricted` 만 받는 비대칭)는 그대로 서지만, **그것이 dev 밖에서 값을 낸다는 증거는
없다.**

Katz 로그법은 분자가 0 이면 배율을 못 낸다. Fisher 양측 p 는 1.0000 이다 — 두 비율이
다르다고 말할 근거가 없다.

### C9 — 무라벨에서 유의하게 덜 터진다

Katz 95% 구간 **[0.002, 0.579] 가 1 을 포함하지 않는다.** dev 보다 무라벨에서 덜
발화한다는 뜻이고, 과탐 쪽으로 새지 않는다는 신호라 안전한 방향이다.

다만 분자가 양쪽 다 1 이라 표본이 얇다. Fisher p 0.0690 은 명목 0.05 를 넘는다 —
**"덜 터진다"를 단정하지 않는다.** 구간과 p 가 엇갈리는 것 자체를 적어 둔다.

## 3. 재현

```bash
TMP=<tmp>; mkdir -p "$TMP"
git show 772ca1284c8918c1fa4ca5729cc15dfe4dedb2d4:script.py > "$TMP/pin.py"

# dev — 회차 원응답 위에서
py -X utf8 tools/replay_run.py --case reports/runs/colab-1790396310565903096/dev-debug \
  --script "$TMP/pin.py" --output-dir "$TMP/base"
py -X utf8 tools/replay_run.py --case reports/runs/colab-1790396310565903096/dev-debug \
  --script "$TMP/pin.py" --candidate experiments/c7_role_over_value_candidate.py \
  --output-dir "$TMP/c7"

# 무라벨 — 샤드마다 ids.json 으로 입력을 잘라 같은 코드로 재생한다
#   reports/label-compare/unlabeled-d/*/u*/output 이 케이스,
#   open/train_unlabeled.jsonl 에서 그 id 만 뽑아 --input 으로 준다
```

배율은 `reports/team-c/c-unlabeled-multiplier/multiplier.py` 의 `ratio_interval` ·
`fisher_two_sided` 를 그대로 썼다.

## 4. 이 문서가 답하지 않는 것

- **무라벨 정확도.** 무라벨에는 라벨이 없다. 여기 수는 **발화율**이고 오탐 수가 아니다.
- **서버 전이.** 회차도 서버도 아니다.
- **`u11` 샤드.** 재생이 거부돼 500건이 빠졌다.
- **C7 이 dev 밖에서 값이 있는지.** 0건이라 이 자료로는 못 말한다. 더 큰 무라벨이나
  실제 회차가 필요하다.
