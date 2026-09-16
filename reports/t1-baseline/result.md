# T1 제출 후보 검사 기록

2026-09-16. 구현·로컬 검사·ZIP 준비 완료, **실제 모델·서버 제출 미실행**.
실행 환경은 사용자 선택대로 대회 서버를 사용한다. 현 상태는 draft이며 점수 개선을 주장하지 않는다.
T2는 `90228e3`으로 커밋·로컬 머지했고 `9019bad`에 정리 기록을 남겼다.

## 산출물

- 제출 파일: `artifacts/baseline/submit.zip`, 10,756 bytes.
- SHA-256: `d3d6622e5171cb368adc4f9e5618f9f20f90442a5d3dc64e362a6766c36a9b6a`.
- ZIP 루트: `script.py`, `requirements.txt`만 포함. 추가 패키지 설치 없음.
- 실행 코드 SHA-256: `9abb9c4e53880a40701f14c724d1dfeff3604cea3f5e52ebfb593cdf993db5b7`.
- [manifest](manifest.json)에 원본·코드·패키징 도구·노트북 해시와 검사 범위를 기록한다.
- ZIP과 mock 출력은 Git에서 제외된다. 아래 명령으로 재생성할 수 있다.

## 변경과 검사

제공 코드의 흐름을 유지하면서 실패한 호출/JSON을 0으로 채우던 동작을 제거했다.
실패 건만 한 번 재시도하며, 정상 응답을 얻지 못하면 성공 CSV를 남기지 않는다.
실제 채팅 템플릿의 입력 토큰에 출력 예약을 더해 문맥 상한을 지킨다.
큰 첨부의 부분 수록·누락 표시, null 보존, 짧은 정확한 근거 지시, 엄격한 출력 검사를 추가했다.
외부 자료·RAG·새 모델·학습은 추가하지 않았다.
위키 gate는 반복 실행 가능한 `tests/test_baseline.py`, live 명령은 새 루트 `script.py`를 가리킨다.
기존 제공 원본을 검사하고 새 제출 코드를 검증했다고 오인하지 않도록 실행 경로를 맞췄다.

| 검사 | 결과 |
| --- | --- |
| 베이스라인 회귀 | 7 tests OK, 0.637초. 정수 판정·실패 재시도·예산·문서·원문 근거·CSV 특수문자 포함 |
| 채점기 회귀 | 4 tests OK, 6.453초 |
| Ruff | `script.py tools/package.py tests/test_baseline.py` PASS |
| 공식 샘플 mock | 10건·49열, ID·근거·자가검증 PASS, 모델 성공 0건 |
| dev mock | 200건·49열, ID·근거·자가검증 PASS, 모델 성공 0건 |
| 압축 해제 실행 | 실제 ZIP의 코드로 샘플 mock PASS; 모델 없는 기본 실행은 비정상 종료·CSV 없음 |
| 고정 토크나이저 | dev 200건 중 예산 초과 0건, 최대 입력 12,280토큰 |
| 문서 포함률 | 문서 전체 보존 8→115/200건, 정답 근거 노출 47→53/54개 |

문서 포함률은 제공 베이스라인 4,000자와 후보 16,000자의 입력 손실 비교다.
정답을 입력하거나 ID별 규칙을 만들지 않았다. 실제 판정의 FN 감소·F1 상승은 미측정이다.
[토크나이저 기록](tokenizer-check.json), [문서 포함 기록](context-coverage.json)을 참조한다.

`unittest discover -s tests`는 위 11개는 통과했으나 기존 설치 검사의 필수 `--wiki`가
전달되지 않아 `repository 'None' does not exist`로 실패했다. 전체 탐색 성공으로 보고하지 않는다.
설치 검사는 문서에 지정된 `python -X utf8 tests/test_setup_agents.py --wiki <위키 경로>`로
다시 실행해 2 tests OK, 102.757초를 확인했다. 제출 관련 테스트는 아래 두 명령이다.

## 재현

저장소 루트에서 실행하며 기존 출력 경로는 덮어쓰지 않는다.

```powershell
python -X utf8 tests/test_baseline.py
python -X utf8 tests/test_score.py
python -m ruff check script.py tools/package.py tests/test_baseline.py
python -X utf8 script.py --mock --data-dir open/data --output-dir artifacts/baseline/mock-sample
python -X utf8 script.py --mock --data-dir open/data --input open/dev.jsonl --output-dir artifacts/baseline/mock-dev
python -X utf8 tools/package.py
```

로컬은 Python 3.13.9, Windows 11이며 vLLM을 설치하거나 모델 가중치를 실행하지 않았다.
토크나이저 검사는 고정 리비전의 tokenizer.json·config·Jinja만 사용했다.
transformers 4.57.6의 범용 FastTokenizer 검사이며 서버 GemmaTokenizer/vLLM 검증과 다르다.
서버는 Python 3.12.13·vLLM 0.26.0·transformers 5.14.1이다.

## 남은 확인과 팀 분담

제출 담당자가 위 ZIP을 업로드한 뒤 제출 ID·모델 정상 실행·전체 시간·서버 점수를 기록한다.
2시간 내 완료와 실제 점수는 현재 보장할 수 없다. 업로드/대회 성공 기록이 없는 상태를 T1 완료로 표시하지 않는다.
독립 리뷰와 사람 승인은 이 로컬 검사에 포함하지 않았다.

팀원은 지금 규칙·실행법을 읽고 환경을 준비할 수 있다. 첫 유효 제출 커밋을 고정하면
T6의 함수 이동만 먼저 마치고 문서 선택·프롬프트/검색·항목 명세·실험/출력을 분담한다.
다음 성능 실험은 같은 dev 실제 예측→T2 채점→약한 항목의 조문 직접 주입/BM25 비교 순서다.
공통 GPU 또는 동일 서버 환경의 dev 실행 수단 확보도 필요하다. 플랫폼 팀 병합 마감은 9/23 23:59다.
