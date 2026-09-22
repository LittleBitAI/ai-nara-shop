# A3 첫 live 회차 — 추론 완료 후 노트북 검사 오류

2026-09-20. 실행 코드 `b7ac2650eccd0d8a6ae41919260b158987fd30ff`.
[원본 실행 기록](../../../runs/colab-1789886517580784653/manifest.json).
sample 10건·dev 200건 추론은 정상 종료, 노트북 전체 검증은 중단됐다.
이 보고서의 채점·검사 재현은 저장 파일을 읽은 CPU 작업이며 새 모델 실행이 아니다.

## 원인

`check_live`는 먼저 `extra_call_items`로 단계별 변경 권한을 모으지만, 뒤에서는 SME 선택을
생략한 공고의 v13/e13을 무조건 보호했다. company_size도 v13을 소유하도록 바뀐 계약과
충돌한다. 기존 검사 44개와 전용 노트북 검사 7개는 이 소유권 중첩을 검사하지 않았다.

실제로 걸린 한 건은 `PPS-DEV-184`다.

| 단계 CSV | v13 |
| --- | ---: |
| baseline_submission.csv | 0 |
| company_size_baseline_submission.csv | 0 |
| submission.csv | 1 |

실행 보고서의 `extra_call_items.company_size`에는 v12·v13이 포함돼 있다.
SME 호출 생략을 company_size의 변경 금지로 해석한 것이 오류다. 이 변경의 정답 여부와
파이프라인상 변경 권한은 별개다. 해당 공고는 dev 정답 기준으로 FP이며 점수에도 반영했다.

## 수정·검증

공용 `colab-baseline.ipynb`와 `exp-a3-source-role.ipynb`에서 기존 단계 소유권 맵을 재사용한다.
SME 미선택 행에서는 다른 추가 단계가 소유하지 않는 SME 항목만 보존 검사한다.
대상 밖 항목·ID·선택 건수·모델 성공·코드/설정·ZIP 일치 검사는 유지한다.
추론 코드·프롬프트·후처리·A3 `REPO_REF`는 바꾸지 않았다.

1. 회귀 사례를 먼저 추가하고 기존 노트북에서 사용자와 같은 RuntimeError로 실패를 재현했다.
2. 수정 후 `python -X utf8 -m unittest tests.test_package` 7개 통과(20.799초).
   두 노트북에서 company_size의 v13 변경은 허용하고, v13 소유권을 제거하면 같은 변경을
   차단한다. 기존 대상 밖 변경·모델 실패·설정/패키지·ZIP 변조 검사는 유지한다.
3. `python -X utf8 reports/team-c/a3-zero-items/run-1789886517580784653/check.py`로
   실제 저장 CSV에 옛 검사와 수정 검사를 실행했다. 옛 검사 실패, 두 수정판 통과.
   [검사 기록](gate-check.json). 이는 check_live의 CSV 구간 검사이며 GPU 재실행이나
   원본 런타임의 전체 검사 재완료가 아니다. ruff·diff 검사도 통과했다.

## 보존한 실행 결과

dev 프로세스 종료 코드 0, 실제 모델 성공 200/200, company_size 응답 200/200.
dev 전체 프로세스 시간 883.168초. 서버 1,853건 처리 시간의 실측이 아니다.
등록기는 원본 ZIP의 텍스트 47개를 바이트 그대로 보관했고, 원본에 없는 score·validation을
만들어 끼우지 않았다. 원본 실행 색인과 manifest의 점수는 미기록으로 유지한다.

CPU 복구 채점은 별도 [score/metrics.json](score/metrics.json)에 있다.
dev Macro F1 0.5357800832065538. 정확한 저장값은 metrics 파일이 소유한다.

| 항목 | 기준 재생 TP/FP/FN | 이번 live dev TP/FP/FN |
| --- | --- | --- |
| v10 | 0/0/7 | 0/0/7 |
| v18 | 0/2/7 | 0/1/7 |
| v20 | 0/0/5 | 0/0/5 |

[compare_runs](compare/comparison.json): 기준 재생 0.547985038075와 비교하면
Macro 차이 -0.012204954868, 변경 41/4,800셀, 대상 밖 40셀이다.
v13은 TP 4 유지·FP 8→10, v16은 TP 2→1, v17은 TP 5→4·FP 9→11이다.
서로 다른 모델 회차이므로 그 차이를 H1 효과 하나로 귀속하지 않는다.
세 목표 항목의 TP 회복은 없으며 성능 채택 근거는 아니다.

이번 dev는 `debug_responses=False`, 원응답 0건이다. 뒤의 dev-debug 셀 전에 멈췄으므로
메타 복사·문장 역할 개선 여부를 볼 원응답이 없다. 동일 ZIP 별도 반복과 무라벨 발화율도 미측정이다.

실제 Colab `submit.zip` 해시는 `c1ef2c840e0cc4d28321c345faa07361a689c3a90347f63d4c472c0079359a15`다.
로컬 패키징 기록의 ZIP 해시와 다르지만 `script.py` 해시는 `0e432eac…`로 동일하다.
ZIP 바이트 차이의 원인은 원본 submit.zip이 없어 확정하지 않는다. 같은 코드라는 이유만으로
같은 ZIP이라고 쓰지 않는다. 반복 회차는 Colab에 남은 실제 ZIP을 유지한다.

## 재개

현재 Colab 런타임이 살아 있으면 처음부터 다시 실행할 필요가 없다.
수정판의 check_live 함수 정의만 현재 커널에 적용하고 `check_live("dev", 200)`을 실행한 뒤,
7. 채점 셀 → 원응답 보존(dev-debug) 셀 → 결과 다운로드 셀로 진행한다.
sample/dev 실행 셀은 다시 실행하지 않는다. 이미 존재하는 로그를 덮어쓰지 않도록 중복 실행을 거부한다.
dev-debug는 원응답 확보를 위한 별도 추론이며 완료된 dev를 복구 채점하는 데는 필요하지 않다.

런타임이 종료됐어도 dev 결과는 저장소에서 복구됐다. 다음 GPU 회차에는 수정된 A3 노트북을
사용하며, REPO_REF는 같은 추론 후보 b7ac265 전체 SHA를 유지한다. 모델 성공과 노트북 전체
완주·서버 제출 성공을 구분한다. 대회 제출과 독립 리뷰는 수행하지 않았다.
