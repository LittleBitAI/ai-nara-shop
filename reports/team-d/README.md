# D 담당 보고서 색인

티켓 하나에 한 장이다. 공통 입력·해시는 이 장에 한 번만 적고 각 티켓 장이 참조한다.

| 티켓 | 항목 | 결과 | 장 |
| --- | --- | --- | --- |
| D0 | 기준선 회차 | 대기 (건너뜀) | [d0.md](d0.md) |
| D1 | v8 중복제한 | 채택 대기 | [d1.md](d1.md) |
| D2 | v7 지역제한 인접 확대 | 채택 대기 | [d2.md](d2.md) |
| D3 | v4 특정기관·특정실적 | 채택 대기 | [d3.md](d3.md) |
| D4 | — | 이관 (C7) | [d4.md](d4.md) |
| D5 | v23 현장설명회 공고기간 | **반려** | [d5.md](d5.md) |
| D6 | v3 실적제한 1배수 이상 | 채택 대기 | [d6-v3.md](d6-v3.md) |
| D6 | v2 고시금액 미만 실적제한 | **대기** (규칙 미작성) | [d6-v2.md](d6-v2.md) |

## 공통 입력과 해시

| 항목 | 값 |
| --- | --- |
| 증거 수준 | **저장 응답 재사용 (CPU 재생)**. 새 모델 실행·서버 제출이 아니다 |
| 기준 회차 | `colab-1789655036303880754` · `dev-debug` |
| 회차 커밋 | `b1134257d221cc066c09e5c31d439a3e6c098ef0` |
| 모델 | `google/gemma-4-26B-A4B-it` rev `4d7ae4984b7db7de8f8457170b3f1a419ee76d52` |
| 제출 ZIP sha256 | `a5e038ea0113286877f84bf9eeef319b547f996951fa5736bcd40bb49c08b669` |
| `script.py` sha256 | `2ad9ea8f299e87ccf7acf5ce42b9fae2618a8167edbdbef0c51cc2ef5496c333` (현재 main과 같다) |
| 입력 `open/dev.jsonl` | `5507f5ab0ba53b708f87211ed050dbe531b48a626ace6084c3ccaefb53147534` |
| 정답 `open/dev_labels.csv` | `84c79302ac190b45b2487ec8e02aab73e59071ee745828e813a7db96d3a97a35` |
| 원응답 `dev-debug/diagnostics.jsonl` | `c7faa409c47eee02c0317103fba6e3e6012b49bd06aa149e9b2cb414766568f1` |
| 기준 CSV `dev-debug/submission.csv` | `d1c4d8d954c51f3848c2bb48fa0231ce64ae120c417e27eaacc624f6886e032e` |
| 후보 CSV `final/replay/submission.csv` | `71a87847155ae6d303590036bcd851ec8b845f77b5138310fa6fe4e21da53f3c` |
| 후보 코드 `experiments/qualification_candidate.py` | `8c4964f8da7b61a1aabaa48a45c3e3a978973f463b4ef1e25b74cbd39e8ab1a4` |

### 증거 수준의 뜻

`tools/replay_run.py`가 보관된 원응답으로 모델 뒤 단계만 다시 돌린 결과다.
후보 없이 `--verify`로 회차 CSV를 바이트 단위로 재현하는 것을 검사가 지킨다.
후보가 후처리만 바꾸므로 같은 응답을 쓴 GPU 회차와 결과가 같다.
**새 GPU 실행도, 서버 제출도 하지 않았다.** `final/replay/manifest.json`의
`model_called: false`가 이것을 기록한다.

## 전체 결과

| 항목 | 티켓 | 전 TP/FP/FN | 후 TP/FP/FN | F1 | 기여 |
| --- | --- | --- | --- | --- | --- |
| v8 | D1 | 0 / 0 / 6 | 6 / 0 / 0 | 0.000000 → 1.000000 | +0.041667 |
| v7 | D2 | 0 / 0 / 7 | 7 / 0 / 0 | 0.000000 → 1.000000 | +0.041667 |
| v4 | D3 | 0 / 2 / 6 | 6 / 2 / 0 | 0.000000 → 0.857143 | +0.035714 |
| v3 | D6 | 8 / 10 / 0 | 8 / 6 / 0 | 0.615385 → 0.727273 | +0.004662 |
| 나머지 20항목 | — | 변화 없음 | 변화 없음 | — | 0 |

Macro F1 0.218204 → 0.341913 (+0.123710). 바뀐 셀 23 / 4800, 대상 밖 0.

기여 열은 규칙을 하나씩만 켜고 같은 원응답을 다시 재생해 잰 값이다.
네 규칙이 서로 다른 항목만 건드리므로 합(+0.123710)이 실측 전체 차이와 정확히 같다.
근거는 [final/contributions.json](final/contributions.json)이다.

## 산출물

| 경로 | 내용 |
| --- | --- |
| [final/replay/](final/replay/) | 후보를 끼운 재생 CSV와 `manifest.json` (`model_called: false`) |
| [final/score/](final/score/) | 후보 채점 |
| [final/score-before/](final/score-before/) | 기준 회차 채점 |
| [final/compare/](final/compare/) | `compare_runs` 대조 |
| [final/contributions.json](final/contributions.json) | 규칙별 단독 기여 |
| [review/firings-dev.md](review/firings-dev.md) | 사람 검토용 발화 사례 시트 |

## 검사

- `python -X utf8 -m unittest tests.test_baseline tests.test_package tests.test_score tests.test_register_run tests.test_compare_runs tests.test_replay_run tests.test_qualification_candidate` — 97개 통과
- `python -m ruff check script.py tools tests experiments` — 통과
- `script.py`는 고치지 않았다.

## 공통으로 확인되지 않은 것

- **네 규칙 모두 공개 dev 200건을 보고 만들었다.** 저장소에 다른 라벨 세트가 없어
  일반화를 수치로 검증할 방법이 없다. 사람 검토용 발화 사례는
  [review/firings-dev.md](review/firings-dev.md)에 뽑아 두었다.
- 정규식은 조문 표현과 dev 관측 표현을 주석으로 갈라 표시했다. 후자는 비공개 test에서
  다른 표기를 만날 수 있다.
- 운영 코드 반영은 B의 판단이다. 새 의존성·프롬프트 변경·토큰 증가·추론 시간 영향이 없다.

## 저장소 변경 중 D 소유가 아닌 것

`.gitignore`의 `/experiments/`를 `/experiments/*` + 예외 2줄로 바꿨다.
배정표 196~197행이 지정한 후보 소스를 커밋할 수 없었기 때문이다.
**예외 대상에 C의 `experiments/sme_candidate.py`도 함께 넣었다.**
C가 그 파일을 만들면 별도 조치 없이 커밋된다. 다른 파일은 계속 무시된다.
