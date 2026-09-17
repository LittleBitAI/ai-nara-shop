# T1 / 오늘 제출할 베이스라인

## 2026-09-17 성능 회귀 철회·3항목 별도 판정

- 입력: `9363f21` 사용자 실제 결과 ZIP `colab-results-1789607374469265263.zip`.
  F1 0.18470988076251235로 기준선 0.2208013652894021보다 하락. 사용자 지시로 전체 프롬프트 주입은 철회한다.
- 출력: 기존 24항목 프롬프트 복원 + 같은 모델에서 v10·v11·v13 별도 호출,
  다른 21항목 보존, 같은 실행의 baseline CSV와 최종 CSV 비교. 응답 분할 복구 유지.
- 수정 범위: `script.py`, `tests/test_baseline.py`, `tests/test_package.py`,
  `notebooks/colab-baseline.ipynb`, `docs/colab.md`, 이 작업서·`docs/tasks.md`·`.wiki/plan-active.md`,
  `reports/t1-baseline/`, `artifacts/isolated-sme/`. 기존 결과·ZIP·제공 자료는 보존한다.
- 통과 조건: 기본 24항목 메시지가 1c64604와 동일, 3항목 범위/재시도/병합 검증,
  다른 21항목 및 근거 보존, 실패 시 성공 산출물 금지, mock/패키징·토큰 예산 검사.
  Colab은 한 번의 모델 로드로 양쪽 CSV를 생성·채점하고 개선 전에는 ZIP 자동 다운로드를 보류한다.
- 규칙: A1·A5·A6·A9, R1·R3·R4·R7~R9·R11·R15·R17~R21. 정답은 채점에만 사용한다.
  실제 성능·시간·서버 성공은 후속 GPU 실행으로 확인한다. 독립 리뷰 생략·커밋/PR/병합 권한 유지.
- 결과: baseline 12개·패키징/노트북 5개·채점기 4개 검사 통과. 기본 dev 메시지 200건 동일,
  별도 판정 토큰 예산·Ruff·nbformat·인코딩·diff 검사 통과. 후보 ZIP/번들 생성 완료.
  [실행 기록](../../reports/t1-baseline/isolated-sme.md). 실제 GPU 재검증은 남아 있다.

## 2026-09-17 응답 복구와 성능 파일럿

- 사용자 선택: 서버 실행 오류와 판정 성능 둘 다 개선한다. 독립 리뷰 생략 지시 유지.
- 입력: Colab `colab-results-1789604529719466871.zip` (커밋 1c64604), 제공 법령·경쟁제품 CSV.
  A100 40GB에서 샘플 10건/dev 200건 성공, Macro F1 0.2208013652894021을 비교 기준으로 보존한다.
- 출력: 실패 공고의 항목 분할 재시도, v10·v11·v13 제공 법령·품목 조회 파일럿, 새 제출/Colab 번들.
- 수정 범위: `script.py`, `tests/test_baseline.py`, `tools/package.py`, `tests/test_package.py`,
  `notebooks/colab-baseline.ipynb`, `docs/colab.md`, 이 작업서·`docs/tasks.md`·`.wiki/plan-active.md`,
  `reports/t1-baseline/`, `artifacts/recovery-sme/`. 제공 자료·기존 ZIP은 보존한다.
- 통과 조건: 잘림·빈 응답·부분 응답의 실패 재현과 분할 복구, 복구 실패 시 성공 CSV 금지,
  제공 원문·품목 코드/예외 보존·공고별 독립 조회·입출력/패키징 회귀.
  같은 Colab dev 재실행에서 F1·대상 3항목 FP/FN·시간 비교 후 채택 여부를 판단한다.
- 규칙 판단: 개발/로컬 검증, A1·A5·A6·A9·A10, R1·R3·R4·R7~R9·R11·R15·R17~R21.
  외부 법령·ID별 정답 하드코딩 없음. 서버 원인 확정·실제 성능 개선은 별도 실행 증거가 필요하다.
- 결과: 응답 복구/파일럿 구현, 로컬 검사 20개·고정 토크나이저 dev 200건 검사 통과.
  새 후보 ZIP/Colab 번들 생성 완료. [세부 결과](../../reports/t1-baseline/recovery-sme.md).
  새 후보의 실제 GPU·서버 성공과 F1 개선은 아직 미검증이며 T1 전체는 진행 중이다.

## 2026-09-17 Colab 실행 경로 보완

- 입력: 사용자 제공 `colab-results-1789602422101717812.zip`, main `a631373` 실행 로그.
- 원인: 설치된 ninja 1.13.2를 FlashInfer 자식 프로세스가 PATH에서 찾지 못해 모델 초기화 실패.
- 출력·범위: `notebooks/colab-baseline.ipynb`의 공통 실행 환경·ninja 사전 검사,
  `tests/test_package.py`의 실제 자식 프로세스 회귀 검사, Colab 안내·T1 보고서·작업 상태.
- 통과 조건: 수정 전 실행 파일 탐색 실패 재현, 수정 후 기본/명시 환경 모두 탐색 성공,
  기존 토큰 격리·로그·ZIP 검사 유지. 실제 GPU 재실행 성공은 별도 확인한다.
- 규칙: 환경 진단 A1·A9, 고정 모델 R1·R4 및 실행·제출 제한 R7·R15·R17 유지.
  이전 사용자 지시대로 독립 리뷰 없이 커밋·PR·병합한다.
- 결과: 수정 전 실제 자식 프로세스 FileNotFoundError 재현 → 패키징·노트북 검사 5개 통과.
  nbformat·Ruff·인코딩·diff 검사 통과. [증거·남은 검증](../../reports/t1-baseline/colab-ninja-failure.md).

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

## 2026-09-17 서버 실패 진단

- 요청: 제출 오류의 원인 조사. T1은 in_progress 유지, 이번 작업은 진단과 기록에 한정한다.
- 입력: 사용자 보고 오류 `InstallError : 청크 내 62번 공고: 정상 모델 응답 재시도 실패 (ValueError)`,
  사용자가 선택 질문으로 확인한 로컬 T1 ZIP, 제출 전 manifest·현재 소스·제공 스키마·고정 토크나이저.
- 출력: [진단 기록](../../reports/t1-baseline/server-failure.md). 확인된 실패 경로와 미확정 원인을 구분한다.
- 수정 범위: 이 문서, `docs/tasks.md`, `docs/roadmap.md`, `.wiki/plan-active.md`, 위 진단 기록.
  제출 코드·ZIP·제공 원본·제출 전 manifest는 보존한다.
- 통과 조건: ZIP 해시·내부 코드 일치 확인, ZIP 코드로 같은 오류 문구 재현,
  원인 정보가 사라지는 경로와 추가로 필요한 증거 명시. 서버 실패의 근본 원인 확정은 별도다.
- 규칙 판단: 로컬 검증 / A1·A9 / R4·R8·R9·R15·R17·R19. 모델 실행·외부 제출 없음.
- 결과: ZIP은 기록된 SHA-256과 일치. 서로 다른 5개 실패를 주입했을 때 같은 문구가 발생했다.
  출력 예산 부족은 가능한 경로지만 실제 서버 응답이 없어 확정하지 않았다.
  제출 시각·제출 ID·전체 로그·실제 런타임 설정은 미확인이다. 아래 제출 전 검사 기록과 구분한다.

## 오늘 반영할 작은 수정

### 후속 요청: 진단 기록과 Colab 실행 준비 (2026-09-17)

- 상태: in_progress. 사용자 요청으로 오류 진단 정보를 보강하고 Colab 사전 검증 경로를 만든다.
  환경 선택 질문에서 사용자는 **실행 노트북부터 준비**를 선택했다. 실제 Colab GPU 실행은 후속 검증이다.
- 입력: 현재 제출 코드, 실패 진단 기록, 제공 샘플·dev·스키마, 서버 고정 모델/패키지 명세.
- 출력: 실패에도 남는 JSONL 진단·원인 traceback·실행 설정, 같은 ZIP 코드로 실행하는 Colab 노트북/업로드 번들.
- 수정 범위: `script.py`, `tests/test_baseline.py`, `tools/package.py`, `tests/test_package.py`,
  `notebooks/colab-baseline.ipynb`, `docs/colab.md`, `README.md`, `docs/README.md`,
  이 문서, `docs/tasks.md`, `.wiki/plan-active.md`, `reports/t1-baseline/`, `artifacts/baseline-diagnostics/`,
  `artifacts/review/t1-diagnostics-request.md`. 이전 제출 ZIP·제공 원본은 보존한다.
- 통과 조건: 서로 다른 실패 원인과 최초/재시도 생성 정보를 구분하는 회귀 검사,
  mock 10건·200건, ZIP 압축 해제 검사, Colab 번들 해시/경로/셀 문법 및 실행 도우미 검사.
  실제 GPU·서버 성공은 실행 증거 없으면 미검증으로 남긴다. 사용자 후속 지시로 이번 변경의 독립 리뷰는 생략한다.
- 규칙 판단: 개발·로컬 검증 준비 / A1·A9 / R1·R3·R4·R7~R9·R15·R17~R21.
  모델 다운로드는 Colab 준비 단계에서 고정 리비전만 사용하고 제출 추론에는 추가하지 않는다.
  기본 진단에 공고 본문·원응답을 넣지 않으며 명시적 원응답 옵션은 공개 dev 로컬 진단용이다.
- 결과: 구현·로컬 검사·ZIP/Colab 번들 준비 완료. 회귀 검사 9개·패키징/노트북 검사 3개·채점기 4개 통과,
  mock 샘플 10건·dev 200건 통과. [검증 기록](../../reports/t1-baseline/diagnostics-colab.md)에 해시·증거 경계를 기록했다.
  실제 Colab GPU·서버 재제출은 미실행이다. 사용자 후속 지시로 리뷰 요청은 취소했다.
- 추가 요청: Colab 검증과 대회 실행의 차이를 줄인다. `HF_TOKEN` 필수 다운로드, Python/패키지 버전 검사,
  같은 ZIP의 무인자 `python script.py`·PPS 경로·기본 추론 설정 검사, 통과한 ZIP 다운로드를 구현한다.
  수정 범위는 위 노트북·테스트·관련 안내/기록이다. 서버의 비공개 입력과 물리 GPU 차이에 대한 보장은 하지 않는다.
  통과 조건에 토큰 누락 거부·토큰 미기록, 무인자 실행·설정 불일치 거부·검증 ZIP 동일성 검사를 추가한다.
- 추가 결과: 토큰 없는 기존 셀의 신규 검사 실패 → 수정 후 3개 검사 통과.
  노트북의 실제 경로 준비·로그 함수로 무인자 호출(mock 대체)과 dev gzip 경로를 검사했고,
  패키지/추론 설정/실행 파일 변경을 심으면 성공 검사가 거부하는 것을 확인했다.
  Python 설치·모델 다운로드·Colab 실제 GPU 실행은 미검증이다. 기존 제출 후보·Colab 번들은 그대로 사용한다.

### Colab clone 준비 보완 (2026-09-17)

- 입력: 공개 `LittleBitAI/ai-nara-shop` main, 현재 노트북의 ZIP 검증 경로.
- 출력: clone → 실제 커밋 기록 → 기존 package 도구로 ZIP/번들 생성 → 기존 ZIP 검증·실행.
- 수정 범위: `notebooks/colab-baseline.ipynb`, `tests/test_package.py`, `docs/colab.md`,
  이 작업서, `docs/tasks.md`, `.wiki/plan-active.md`, `README.md`, `reports/t1-baseline/diagnostics-colab.md`.
- 통과 조건: 로컬 Git 저장소를 clone하는 노트북 셀 실제 실행, 커밋 기록·생성 ZIP/실행 코드 일치,
  기존 수동 업로드 경로 회귀·노트북 문법/nbformat 검사. 실제 GPU 검증은 별도다.
- 규칙 판단: 개발·로컬 검증 / A1·A9 / R1·R4·R7·R15·R17. clone은 Colab 준비 단계만 사용한다.
  기존 리뷰 생략 지시를 유지한다.
- 결과: clone 셀 부재를 신규 검사에서 `KeyError: clone`으로 재현한 뒤 구현했다.
  `python -X utf8 tests/test_package.py` — 4 tests OK (12.564초).
  로컬 main을 실제 clone한 뒤 package 도구로 생성한 ZIP의 코드·커밋 기록 일치를 확인했다.
  Colab GPU 실행은 미검증이다. 이전 커밋·PR·머지 요청의 후속 보완으로 공개 main에 반영한다.

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
