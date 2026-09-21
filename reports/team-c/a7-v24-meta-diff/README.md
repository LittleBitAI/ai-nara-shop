# A7 — v24 오탐은 코드가 대조로 걷어낸다

2026-09-21. **모델을 부르지 않았다. GPU 0초.** 회차 `colab-1789902969401579900`(`18f07e5`)의
보관 원응답과 dev 200건으로 잰다. 후보이며 `script.py` 는 고치지 않았다.

## 결과

| 재생 | Macro F1 | v24 TP/FP/FN | v24 F1 |
| --- | ---: | --- | ---: |
| HEAD (회차 CSV와 바이트 동일) | 0.593846165415 | 5/36/3 | 0.204 |
| 후보 [a7_v24_meta_diff](../../../experiments/a7_v24_meta_diff.py) | **0.599231652943** | **4/12/4** | **0.333** |
| 차이 | **+0.005385487528** | FP −24 · TP −1 | +0.129 |

**바뀐 셀은 v24 24개뿐이고 대상 밖 23항목은 0셀이다.** 후보는 내리기만 하므로 0→1 셀이 없다.
같은 후보로 두 번 재생해 바이트 동일을 확인했다(결정적, 회차 churn 없음).

```powershell
python -X utf8 tools/replay_run.py --case reports/runs/colab-1789902969401579900/dev-debug `
    --candidate experiments/a7_v24_meta_diff.py --output-dir <새 폴더>
python -X utf8 tools/score.py --truth open/dev_labels.csv --pred <새 폴더>/submission.csv --output-dir <새 폴더2>
python -X utf8 -m pytest -q tests/test_v24_meta_diff_candidate.py
```

보관: [candidate-replay/submission.csv](candidate-replay/submission.csv),
[candidate-score/](candidate-score/). 기준은 회차 폴더의 `submission.csv` 를 그대로 쓴다.

## 왜 이 자리인가

v24 는 **오탐 36건으로 전체 오탐 111건의 32%** 다. 단일 항목 `FP→0` 이득으로 24항목 중 최대다(+0.0235).
그리고 [A5 독립 분석](../a5-label-definition/five-stuck-analysis.md)이 확인한 대로 v24 는
**company 소비 대상이 아니다** — baseline 판정과 후처리만 쓴다. `scope`·기업등급·부재 관측과
독립이라 보관 응답 재생으로 churn 0 에서 잴 수 있다. 같은 날 잰 GPU churn 은 **±0.0157** 이다
([astra 회차 기록](../a5-v18-scope-review/results.md)의 control 두 회차).

## 무엇이 비어 있었나

기존 `v24_consistent_with_meta()` 는 **모델이 준 근거 문구**의 금액·지역·제목태그를 메타와
대조해 전부 일치하면 그 양성을 내린다. 반환값이 `checked` 라 **대조할 것이 근거에 없으면
아무 말도 못 한다.** v24 양성 41건 중 **근거 빈칸이 24건(TP 2 · FP 22)** 이다 —
검증기가 오탐 질량의 **61%** 에 닿지 못했다.

## 무엇을 바꿨나

대조 대상을 모델의 근거가 아니라 **공고 원문**으로 바꿨다. 항목표 `비고` 가 지정한 네 축
(`예산, 계약방법, 지역제한, 업종`)을 코드가 직접 공고↔메타로 대조하고, 어느 축에서도
불일치를 못 찾으면 양성을 내린다. 근거 유무와 무관하게 같은 검사를 건다.

축별 판정은 기존 자산을 그대로 쓴다 — `V24_TITLE_TAG`·`V24_UNIT`·`V24_AMOUNT`·`V24_REGION`·
`REGION`·`WIDE_REGION`·`_region_names`. 새 정규식은 본문 업종코드 표기 하나다.
[규칙 A10](../../../docs/rules.md) 이 이 용도를 명시로 허용한다 —
"기관 유형·지역 계층·금액·품목·문서를 함께 읽고 **v24 불일치 대조**".

### 한 가지를 더 넣었다 — 등록 지역 **집합** 비교

첫 측정은 `+0.002366`(4→3 TP, FP 12)이었다. 잃은 TP 가 `PPS-DEV-072` 인데,
**등록 `제한지역코드목록` 이 `경기도` 하나인데 본문은 "경기도 … 또는 제주도"** 였다.
기존 `v24_consistent_with_meta` 가 모델 근거에 대해 하는 바로 그 집합 비교인데,
근거가 없어서 못 걸렸다. 같은 비교를 원문의 지역제한 문구 창에 대해 하도록 넓혀
**TP 를 되찾고 FP 는 12 그대로**였다 → `+0.005385`.

## 못 살린 것과 안 한 것

- **`PPS-DEV-062` 는 네 축 어디에도 안 걸린다.** 등록 면허업종 `기타자유업(행사대행업)(9901)` 과
  본문 "'행사대행업'으로 등록한 업체" 가 **일치**하고, 지역·금액·계약방법도 어긋나지 않는다.
  정답은 1 이다. **그 한 건을 위해 축을 넓히지 않았다** — 검사가 이 상태를 고정한다.
- FN 3건(`29`·`049`·`055`)은 그대로다. 이 후보는 새 양성을 만들지 않는다.
  `055` 는 코드가 축 2개를 찾지만 baseline 이 0이라 필터가 닿지 않는다.
- **"빈 근거면 0"** 을 다시 제안하지 않는다. A5 가 기각했고 TP 2건을 잃는다.
  이 후보는 빈 근거를 따로 취급하지 않는다.
- 축을 하나씩 넣고 이긴 것만 남기지 않았다. 항목표가 지정한 네 축을 그대로 넣고 한 번 쟀다.

## 무라벨 카나리

W5 규약대로 `open/train_unlabeled.jsonl` 앞 **6,000건**에서 규칙 발화를 셌다(3초).

| | 불일치를 찾은 공고 | 비율 |
| --- | ---: | ---: |
| dev 200건 | 45 | 22.5% |
| 무라벨 6,000건 | 1,496 | 24.9% |

**배율 1.107.** 채택된 v6 1.11 · v9 1.16 과 같은 범위이고, 기각 사유가 됐던 v23 의 0.05 와 멀다.
축별 무라벨 발화는 지역제한 733 · 예산 641 · 업종 242 다.
`open/train_unlabeled.jsonl` 은 gitignore 라 워크트리에 없다 — 본 저장소 경로로 읽었다.

## 미측정

- **전체 파이프라인 GPU·서버 점수는 미측정이다.** 이 수치는 보관 원응답 혼합 재생이며
  `18f07e5` 의 dev GPU 0.599315859078 이나 서버 0.5084137874 를 갱신하지 않는다.
- 비공개 1,853건에서 네 축의 메타 품질이 dev 와 같다는 보장은 없다. 무라벨 배율이
  그 대리 지표이고, 실제 전이는 제출로만 확인된다.
- 독립 리뷰·채택·대회 제출은 하지 않았다.

## 부수 발견 — 후보 모듈이 **옛 커밋의 `script.py`** 를 집을 수 있다

일곱 후보가 전부 `sys.modules.get("run_submission") or sys.modules.get("submission")` 순서로
기준 모듈을 찾는다. 그런데 `run_submission` 은 `replay_run.run_script()` 가 **회차 커밋의**
`script.py` 를 꽂는 이름이고(`--verify` 전용), **`--verify` 는 후보를 아예 거부한다.**
그래서 후보가 그 이름을 집으면 언제나 틀린 코드다.

`tests/test_replay_run.py:29` 가 모듈 적재 시점에 그것을 등록한 채 남기므로, 같은 프로세스에서
뒤에 도는 후보 검사가 실제로 줍는다. 기본 알파벳 순서에서는 안 드러나고,
`pytest tests/test_v24_meta_diff_candidate.py tests/test_scope_gate_candidate.py tests/test_replay_run.py`
처럼 순서를 바꾸면 `a4_scope_gate_candidate` 의 v6 검사 3개가 깨진다.

이 후보는 `run_submission` 갈래를 빼서 고쳤다. **나머지 여섯은 안 고쳤다** —
다른 작업 갈래의 파일이고 기본 순서에서는 통과한다. 고칠 자리는
`experiments/*.py` 의 `baseline()` 한 줄씩이거나 `tests/test_replay_run.py:29` 의 정리 한 줄이다.
