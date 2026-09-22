# B 전달 — 회차 ① `round1-unlock-absence-evidence.diff`

보낸 사람 C · 2026-09-18 · 대상 `script.py` (B 소유) · 적용하지 않았다. 판단은 B 것이다.

## 요지 네 줄

1. 자리는 4개다. `script.py:238` 하나만 고치면 아무것도 바뀌지 않는다.
2. 제출 CSV 계약은 바뀌지 않는다. 검사로 못 박았다. 주장이 아니다.
3. 추가 모델 호출 0. 24항목 합동 호출을 그대로 둔다. 서버 시간 증가 0초.
4. 로컬 검사 74건 OK, ruff 통과. 실제 GPU·서버 검증은 없다.

## 왜 238 단독은 무효인가

`open/data/정답스키마_디코딩.json` 이 실제로 존재한다. 그래서 `decode_schema` 는
파일 적재 분기(224-228)를 타고 `return s` 로 빠져나간다. 238 의 `props` 조립 블록에는
도달하지 않는다.

그 파일이 v10·v11·v16·v18·v20 의 `근거문구` 를 `{"type": "null"}` 로 못 박고 있고,
기존 코드의 루프는 `if v not in ABSENCE` 라 부재탐지 항목을 건드리지 않고 지나간다.
즉 제약 디코딩이 부재탐지 항목의 인용 생성을 원천 차단한다.

확인 방법:

```bash
py -X utf8 -c "
import importlib.util, json
spec = importlib.util.spec_from_file_location('s', 'script.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(json.dumps(m.decode_schema('open/data')['properties']['v16']['properties']['근거문구'], ensure_ascii=False))"
```

적용 전 `{"type": "null"}` · 적용 후 `{"type": ["string", "null"], "maxLength": 100}`.
v16 은 부재탐지 항목이라 100 이다. 부재가 아닌 항목(예: v1)을 찍으면 500 이 나온다.

## 4개 자리

| # | 위치 | 바뀌는 것 |
| --- | --- | --- |
| 1 | `decode_schema` 224-228, 파일 적재 분기 | 실효 자리. 모든 항목의 `근거문구` 를 `string\|null` 로 덮어쓴다. 부재탐지 5항목은 100자, 나머지는 500자 |
| 2 | `decode_schema` 238, fallback 조립 | 스키마 파일이 없는 환경에서 같은 결과가 되도록 맞춘다 |
| 3 | `SYSTEM_HEAD` 규칙 3 | "Their 근거문구 is always null" → 위반 판정 시 관측한 조항을 인용하고, 그런 조항이 없을 때만 null |
| 4 | `build_system_prompt` 항목표 태그 | `[absence detection; evidence=null]` → `[absence detection]` |

3·4 를 빼고 1·2 만 풀면 스키마는 열리지만 프롬프트가 계속 null 을 지시한다. 네 자리는 한 묶음이다.

## CSV 계약이 불변인 근거 — 검사

`postprocess` 의 `if hit and v not in ABSENCE` 와 `validate_csv` 의 부재탐지 e 빈칸 검사는
diff 가 건드리지 않는다. 모델이 생성할 수 있는 것만 열고, 제출되는 것은 그대로다.

`tests/test_sme_candidate.py::SubmissionContract` 4건이 이것을 고정한다.
모델이 부재탐지 항목에 인용을 낸 출력을 만들어 넣고 확인한다:

| 검사 | 고정하는 것 |
| --- | --- |
| `test_postprocess_blanks_absence_evidence_even_when_model_quotes` | 모델이 인용을 내도 `postprocess` 가 e 를 빈칸으로 만든다 |
| `test_candidate_postprocess_keeps_the_same_contract` | 금액 게이트 후보를 끼워도 같다 |
| `test_written_csv_passes_validate_csv` | 그 행으로 쓴 CSV 가 `validate_csv` 를 통과한다 |
| `test_validate_csv_still_rejects_absence_evidence` | e 를 일부러 채우면 `validate_csv` 가 잡는다 (검사가 무력하지 않다) |

이 4건은 diff 적용 여부와 무관하게 통과한다. 둘 다에서 돌렸다.

## 검사·실행 명령

```bash
git apply reports/team-c/c3-amount-gate/round1-unlock-absence-evidence.diff

py -X utf8 -m unittest tests.test_baseline tests.test_package tests.test_score \
  tests.test_register_run tests.test_compare_runs tests.test_replay_run tests.test_sme_candidate
py -m ruff check --isolated --select E4,E7,E9,F script.py tools tests experiments reports/team-c

git checkout -- script.py   # 내 트리에서는 되돌렸다
```

| 상태 | 결과 |
| --- | --- |
| diff 미적용 · 6개 모듈 | 56건 OK |
| diff 미적용 · `test_sme_candidate` 포함 | 74건 OK |
| **diff 적용 · `test_sme_candidate` 포함** | 74건 OK |
| ruff (`--isolated --select E4,E7,E9,F`) | All checks passed |

ruff 버전 주의. 내 PC 에 ruff 가 없어 0.16.8 을 설치했다. 0.16 의 기본 규칙 집합이
넓어져 설정 없이 `ruff check` 하면 기존 코드에서 180건이 나온다. 위 통과는 종래
기본값 집합 기준이다. `docs/tasks.md` 의 `python -m ruff check` 는 버전을 고정하지 않는다.

## 이 diff 가 증명하지 않는 것

- 회차 ① 이 재현율을 살린다는 증거가 아니다. 별도 질의와 합동 호출의 차이는 셋이었고
  (항목 수 24→3, 근거 null 해제, 출력 2칸→4칸) 이 diff 는 그중 하나만 푼다.
  나머지 둘이 원인이면 이 회차는 효과가 0 이다. 그것을 가르는 것이 회차 ① 의 목적이다.
- 실제 GPU 회차·대회 서버 제출은 하지 않았다. 증거 수준은 CPU 검사뿐이다.
- 금액 게이트(`experiments/sme_candidate.py`)는 이 diff 에 들어 있지 않다. 별도 후보다.

## B 에게 필요한 판단

1. diff 를 `script.py` 에 반영할지.
2. 반영한다면 회차 ① Colab 실행은 A 승인 사항이다. 한 회차에 한 변수 — 출력 4칸(회차 ②)을
   같이 넣지 않는다.
3. `experiments/` 가 `.gitignore:7` 에 걸려 후보 모듈이 커밋되지 않는다.
   `tests/test_sme_candidate.py` 가 그것을 import 하므로 clone 한 사람에게는 이 검사가 깨진다.
   A 확인 사항이며 나는 `.gitignore` 를 건드리지 않았다.
