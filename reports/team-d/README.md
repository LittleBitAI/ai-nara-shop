# D 담당 보고서 색인

티켓 하나에 한 장이다. 공통 입력·해시는 이 장에 한 번만 적고 각 티켓 장이 참조한다.

| 티켓 | 항목 | 결과 | 장 |
| --- | --- | --- | --- |
| D0 | 기준선 회차 | 대기 (건너뜀) | [d0.md](d0.md) |
| D1 | v8 중복제한 | 채택 대기 | [d1.md](d1.md) |
| D2 | v7 지역제한 인접 확대 | 채택 대기 | [d2.md](d2.md) |
| D3 | v4 특정기관·특정실적 | 채택 대기 | [d3.md](d3.md) |
| D4 | — | 이관 (C7) | [d4.md](d4.md) |
| D5 | v23 현장설명회 공고기간 | 반려 | [d5.md](d5.md) |
| D6 | v3 실적제한 1배수 이상 | 채택 대기 | [d6-v3.md](d6-v3.md) |
| D6 | v2 고시금액 미만 실적제한 | 대기 (규칙 미작성) | [d6-v2.md](d6-v2.md) |
| D7 | v3·v4·v5·v6 적용범위 게이트 | 채택 대기 (오탐 9건 제거 · `script.py` 수정) | [d7-fp-gates/README.md](d7-fp-gates/README.md) |

## 공통 입력과 해시

| 항목 | 값 |
| --- | --- |
| 증거 수준 | 저장 응답 재사용 (CPU 재생). 새 모델 실행·서버 제출이 아니다 |
| 기준 회차 | `colab-1789655036303880754` · `dev-debug` |
| 회차 커밋 | `b1134257d221cc066c09e5c31d439a3e6c098ef0` |
| 모델 | `google/gemma-4-26B-A4B-it` rev `4d7ae4984b7db7de8f8457170b3f1a419ee76d52` |
| 회차 제출 ZIP sha256 | `a5e038ea0113286877f84bf9eeef319b547f996951fa5736bcd40bb49c08b669` |

입력·코드·산출물 해시는 [final/hashes.json](final/hashes.json)이 소유한다.
본문에 손으로 적으면 코드를 한 번 더 고칠 때 조용히 낡는다. 실제로 PR #34 리뷰에서
후보 코드 해시가 어떤 커밋의 것도 아닌 값으로 남아 있었다. 그래서 파일로 옮기고
`tools/record_team_d_hashes.py`가 적는다. `tests/test_qualification_candidate.py`의
`RecordedHashes`가 기록과 실제를 대조하므로, 다시 적지 않으면 검사가 빨개진다.

```powershell
python -X utf8 tools/record_team_d_hashes.py          # 다시 적는다
python -X utf8 tools/record_team_d_hashes.py --check  # 낡았는지만 본다
```

### 증거 수준의 뜻

`tools/replay_run.py`가 보관된 원응답으로 모델 뒤 단계만 다시 돌린 결과다.
후보가 후처리만 바꾸므로 같은 응답을 쓴 GPU 회차와 결과가 같다.
새 GPU 실행도, 서버 제출도 하지 않았다. `final/replay/manifest.json`의
`model_called: false`가 이것을 기록한다.

### 비교 기준은 HEAD 재생이다

`--verify`는 보관 원응답 무결성 검사이며 회차가 기록한 커밋의 코드로 재현한다.
HEAD를 검사하지 않는다(PR #30).

**보관 회차의 `submission.csv`를 `--before`로 쓰지 않는다.** 그 뒤에 병합된 후처리
효과가 섞인다. 이 브랜치가 `origin/main`을 병합한 뒤 실제로 그렇게 됐다 — B의 PR #30이
`script.py`를 바꿔 같은 원응답의 기준 점수가 0.218204에서 0.235731로 올라갔다.
그래서 기준은 후보 없이 HEAD 코드로 재생한
[final/head-c5055e4-replay/](final/head-c5055e4-replay/)다.

## 전체 결과

기준은 HEAD `c5055e4`의 재생이다.

| 항목 | 티켓 | 전 TP/FP/FN | 후 TP/FP/FN | F1 | 기여 |
| --- | --- | --- | --- | --- | --- |
| v8 | D1 | 0 / 0 / 6 | 6 / 0 / 0 | 0.000000 → 1.000000 | +0.041667 |
| v7 | D2 | 0 / 0 / 7 | 7 / 0 / 0 | 0.000000 → 1.000000 | +0.041667 |
| v4 | D3 | 0 / 2 / 6 | 6 / 2 / 0 | 0.000000 → 0.857143 | +0.035714 |
| v3 | D6 | 8 / 10 / 0 | 8 / 5 / 0 | 0.615385 → 0.761905 | +0.006105 |
| 나머지 20항목 | — | 변화 없음 | 변화 없음 | — | 0 |

Macro F1 0.235731 → 0.360884 (+0.125153). 바뀐 셀 24 / 4800, 대상 밖 0.

기여 열은 규칙을 하나씩만 켜고 같은 원응답을 다시 재생해 잰 값이다.
네 규칙이 서로 다른 항목만 건드리므로 합(+0.125153)이 실측 전체 차이와 정확히 같다.
근거는 [final/contributions.json](final/contributions.json)이다.

## 산출물

| 경로 | 내용 |
| --- | --- |
| [final/head-c5055e4-replay/](final/head-c5055e4-replay/) | 기준 — 후보 없이 HEAD 코드로 돌린 재생 CSV |
| [final/replay/](final/replay/) | 후보를 끼운 재생 CSV와 `manifest.json` (`model_called: false`) |
| [final/score/](final/score/) | 후보 채점 |
| [final/score-before/](final/score-before/) | HEAD 기준 재생의 채점 |
| [final/compare/](final/compare/) | `compare_runs` 대조 |
| [final/contributions.json](final/contributions.json) | 규칙별 단독 기여 (`tools/record_team_d_contributions.py`) |
| [final/hashes.json](final/hashes.json) | 입력·코드·산출물 해시 |
| [review/firings-dev.md](review/firings-dev.md) | 사람 검토 시트 — dev 200건 (라벨 있음) |
| [review/firings-test-sample.md](review/firings-test-sample.md) | 사람 검토 시트 — test 샘플 10건 (라벨 없음) |

## 검사

- `python -X utf8 -m unittest tests.test_baseline tests.test_package tests.test_score tests.test_register_run tests.test_compare_runs tests.test_replay_run tests.test_qualification_candidate tests.test_sme_candidate tests.test_diagnose_items tests.test_label_bundle` — 전부 통과
- `python -m ruff check script.py tools tests experiments` — 통과
- `script.py`는 고치지 않았다.

## 공통으로 확인되지 않은 것

- 네 규칙 모두 공개 dev 200건을 보고 만들었다. 저장소에 다른 라벨 세트가 없어
  일반화를 수치로 검증할 방법이 없다.
  라벨 없는 공고는 `open/data/test.jsonl.gz`의 샘플 10건이 있고 git으로 추적된다.
  dev 발화 19건이 전부 정답 양성이므로 오탐을 찾을 로컬 재료는 그 10건뿐이다.
  사람 검토 시트를 둘 다 뽑아 두었다 —
  [review/firings-dev.md](review/firings-dev.md) (발화 19건, 전부 정답 양성),
  [review/firings-test-sample.md](review/firings-test-sample.md) (발화 1건, 읽은 결과 오탐 아님).
  표본이 10건이라 이것으로 일반화를 말할 수 없다.
- 정규식은 조문 표현과 dev 관측 표현을 주석으로 갈라 표시했다. 후자는 비공개 test에서
  다른 표기를 만날 수 있다.
- 운영 코드 반영은 B의 판단이다. 새 의존성·프롬프트 변경·토큰 증가·추론 시간 영향이 없다.

## 저장소 변경 중 D 소유가 아닌 것

`.gitignore`는 `origin/main`을 병합하면서 main 쪽(`!/experiments/*.py`)을 채택했다.
C가 같은 문제를 더 넓게 고쳐 두었고 그것이 내 예외 2줄을 포함한다. 이 브랜치가
따로 더하는 변경은 없다.
