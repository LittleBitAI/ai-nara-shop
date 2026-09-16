# T1 / 오늘 제출할 베이스라인

- 담당: 통합 / Codex. 상태: in_progress. 사용자 목표: 2026-09-16 첫 제출, 팀원 합류 전 기준점 확보.
- 입력: 제공 `open/baseline/script.py`, 두 루트 베이스라인 노트북 전체 셀,
  `open/data/`, `open/dev.jsonl`, 공식 규칙·평가·일정.
- 출력: 루트 `script.py`, `requirements.txt`, 검증한 `artifacts/baseline/submit.zip`, 실행 기록.
- 수정 범위: 위 파일, `tests/test_baseline.py`, `tools/package.py`, 이 문서,
  `reports/t1-baseline/`, `docs/tasks.md`, `docs/gemma4.md`, `docs/README.md`, `docs/contest.md`, `docs/rules.md`,
  `docs/roadmap.md`, `docs/sources.md`, `docs/design.md`, `README.md`, `.wiki/plan-active.md`의 현재 작업 상태,
  `.wiki/adapter.toml`의 현재 구현을 가리키는 gate/live 명령.
  제공 원본·설치 도구·사용자의 다른 변경은 보존한다.
- 규칙 판단: 개발·로컬 검증·제출 준비 / A1·A4·A9·A10 / R1~R5·R7~R22,
  D4·D5·C5. 외부 데이터·외부 모델·자가 라벨링 미사용. Q1 의존 없음.
- 선행: T2 `90228e3` 머지 완료. 작업 기준 `9019bad`.
- 통과 조건: 결함 실패 재현→수정 후 테스트; 샘플 10건·dev 200건 mock 형식 검사;
  ZIP 루트·파일 allowlist·인코딩·해시·압축 해제 후 실행·원본 불변 검사.
  실제 모델과 2시간 제한 통과·서버 점수는 대회 서버 결과가 있어야 확인한다.
- 사용자 선택: 실제 모델 실행 환경은 대회 서버. 유료 GPU·API 실행 없음.

## 오늘 반영할 작은 수정

제약 디코딩 베이스라인의 함수·흐름을 재사용한다. 전체 파이프라인 분리는 첫 제출 뒤 수행한다.
1. 모델 호출/JSON 오류의 전항목 0 대체를 제거하고 실패한 공고만 1회 재시도한다.
2. 실제 채팅 템플릿으로 토큰을 세고 출력 예산을 함께 예약한다. 초과 상태의 조기 성공을 제거한다.
3. 4,000자 상한을 늘리고 큰 첨부도 남은 예산만큼 읽는다. 관측성·문서 누락을 프롬프트에 전달한다.
4. 비위반 근거 null·짧은 정확한 인용·v24 메타 대조를 명확히 하며 스키마 근거 상한을 500자로 맞춘다.
5. ID·49열·0/1·근거 규약을 검증한 CSV만 게시한다. 오류 시 정상 산출물로 보이지 않게 한다.
6. mock/live·성공 건수·토큰·시간을 기록한다. 모델 미사용 검사를 모델 성능으로 보고하지 않는다.

RAG 노트북은 BM25·공고 앞 3,000자 질의·8,000자 조문 주입이다. 검색 부분을 노트북에서
변경해도 포장 셀은 원래 `baseline/script.py`를 포장한다. 제출 코드 반영 여부를 반드시 확인한다.
오늘은 런타임·출력 결함과 문서 손실 수정에 집중한다. RAG는 첫 서버 기준선 뒤 동일 dev로 비교한다.

## 공식 운영 확인 (2026-09-16)

[규칙](https://dacon.io/competitions/official/236754/overview/rules),
[평가](https://www.dacon.io/competitions/official/236754/overview/evaluation),
[일정](https://dacon.io/competitions/official/236754/overview/schedule)을 직접 확인했다.
판정용 법령은 제공 스냅샷만 사용한다. 웹 확인은 운영·런타임 명세에 한정했다.

- 9/23 23:59 팀 병합, 9/29 10:00 리더보드 제출 마감, 9/30 10:00 대회 종료.
- 하루 1회. ZIP 2GB·해제 후 8GB, 설치 10분·로드 포함 실행 2시간.
- L40S 1장(가용 약 44.7GiB), 7 vCPU·RAM 60GiB. Python 3.12.13·CUDA 13.0.
- vLLM 0.26.0, torch 2.11.0+cu130, transformers 5.14.1, xgrammar 0.2.3 고정.
- 설치 오류는 횟수 미차감, script.py 실행 이후 오류는 차감.
- ZIP 루트 script.py; PPS 경로 사용, 서버가 data를 읽기 전용 제공. output/submission.csv 필수.

## 팀원 합류 기준

규칙 읽기·환경 준비는 지금 시작할 수 있다. 코드 개선은 첫 유효 제출을 확인한 기준 커밋,
동일 dev 채점법, 실행·패키징 명령, 담당 함수 경계가 준비되면 바로 시작한다.
오늘 제출 후 결과를 기다리는 동안 온보딩하고, 정상 실행이 확인되면 내일부터 분담하는 것이 목표다.
첫 기준선 이후 문서 선택·프롬프트/법령 검색·항목 명세·실험/출력 검증으로 나눈다.
전체 파이프라인 설계 완성을 합류 조건으로 삼지 않는다. 플랫폼 팀 병합은 9/23 마감 전에 끝낸다.

## 실행 증거

추가 사용자 요청: 고정 모델의 특성·적합한 프롬프트/처리를 공식 논문과 문서로 조사한다.
결과는 [Gemma 4 조사](../gemma4.md)에 기록하며 판정용 법령·제출 자산에는 섞지 않는다.

구현·로컬 검사·ZIP 준비 완료. 서버 live·제출 성공·모델 성능은 미확인이므로 T1 전체는 진행 중이다.

| 검사 | 결과 | 의미 |
| --- | --- | --- |
| 결함 재현 → 수정 | 최초 7개 테스트에서 15개 실패·2개 오류 → 7개 통과 | 실패 은폐·예산·근거·CSV 계약 회귀 검사 |
| T2 회귀 | 4개 통과 | 기존 채점 계약 유지 |
| 샘플 / dev mock | 10건 / 200건, 49열·ID·값·근거 규약 PASS | 모델 미호출, 성능 점수 아님 |
| ZIP 압축 해제 | 실제 포장 코드 mock 10건 PASS, 모델 없는 기본 실행 실패 확인 | 기본 실행이 mock으로 바뀌지 않음 |
| 고정 토크나이저 파일 | dev 최대 12,280 + 출력 2,048 + 여유 64 ≤ 16,384 | 범용 FastTokenizer 검사, 서버 런타임 미검증 |
| 문서 보존 비교 | 전체 문서 보존 8→115건, 정답 인용 노출 47→53/54 | 입력 손실 감소, F1 상승을 뜻하지 않음 |

상세 명령·환경·원본/코드/ZIP 해시는 [실행 기록](../../reports/t1-baseline/result.md)과
[manifest](../../reports/t1-baseline/manifest.json)을 따른다.

## 오늘 제출 순서와 다음 작업

1. `python -X utf8 tools/package.py`로 만든 `artifacts/baseline/submit.zip`을 제출한다.
   CSV나 mock 출력은 업로드하지 않는다. ZIP 루트는 `script.py`, `requirements.txt` 두 파일이다.
2. 대회 서버는 `python script.py`를 실행한다. 모델 로드·공고별 응답·최종 CSV·총시간·서버 점수를 확인한다.
   서버 결과·제출 ID를 기록하기 전 T1을 완료로 바꾸지 않는다. 하루 1회 제한을 따른다.
3. 첫 유효 제출의 코드·ZIP 해시를 팀 기준선으로 고정한다. T6에서 기존 함수를 공정별로 옮기고
   같은 입력의 프롬프트·후처리 출력이 같음을 확인한다. 동작 변경과 모듈 분리를 섞지 않는다.
4. 같은 dev의 실제 모델 예측을 T2로 채점한 뒤 FN/FP가 많은 항목부터 조문 직접 주입과 BM25를 비교한다.
   공통 실행 GPU가 아직 없으므로 dev live 환경은 팀 합류 때 함께 확보할 운영 과제다.

모듈 분리 전 담당 경계는 `build_context`·`format_meta`(문서), `build_system_prompt`·
`build_user_prompt`(프롬프트), `VLLMRunner`·`run_chunk`·`run`(통합),
`postprocess`·CSV와 `tools/score.py`(검증)다. 같은 `script.py`를 여러 명이 동시에 고치기 전 T6를 끝낸다.
