# 진단 기록·Colab 준비 검증 (2026-09-17)

상태: 구현·로컬 검증·번들 준비 완료. 사용자 선택은 실행 노트북 우선 준비다.
실제 Colab GPU·vLLM 실행과 서버 재제출은 수행하지 않았다. 독립 리뷰는 사용자 후속 지시로 생략한다. T1 전체는 진행 중이다.

## 변경

- `script.py`는 실패해도 `diagnostics.jsonl`을 남긴다. 실행 인자·적용 설정·자산 해시·패키지 버전,
  모델 로드 단계, 공고 ID·청크/전체 위치, 최초/재시도별 생성 종료 사유·토큰 수·파싱 오류를 기록한다.
- 원인 예외 메시지와 traceback을 보존한다. 호출 실패 시 이전 응답의 생성 정보가 섞이지 않는다.
  기존 진단 디렉터리 재사용을 거부한다. 오류를 정상 CSV나 전항목 0으로 바꾸지 않는다.
- 원응답은 명시적 `--debug-responses`에서만 기록한다. 후속 요청에 따라 Colab 통과 검사에서는 대회와 같은 무인자 실행을 사용한다.
- `tools/package.py --colab-output`은 실제 제출 ZIP과 필요한 공개 검증 자료만 묶는다.
- `notebooks/colab-baseline.ipynb`는 번들 해시/허용 파일을 검사한 뒤 제출 ZIP의 코드를 실행한다.
  Python 3.12.13·별도 venv·HF_TOKEN 필수 고정 모델 준비 → 무인자 샘플/dev 실행 → 설정 검사·채점 → 검증 ZIP 다운로드 순서다.
  원본 베이스라인 노트북과 이전 제출 ZIP은 변경하지 않았다.

## 실행 증거

| 명령/검사 | 결과 | 증거 경계 |
| --- | --- | --- |
| 구현 전 `python -X utf8 tests/test_baseline.py` | 신규 검사 1 failure·1 error | 진단 인자 미지원·원인 메시지 유실 재현 |
| 구현 후 같은 명령 | 9 tests OK | 생성 응답을 모사한 메타데이터 보존·빈 응답·잘린 JSON·호출 실패·모델 경로 실패 검사 |
| `python -X utf8 tests/test_package.py` | 3 tests OK | 실제 ZIP→번들→노트북 경로·무인자 명령(mock 대체)·dev gzip·설정/버전/ZIP 변경 거부·토큰 필수/전달/미기록·로그 회수 |
| `python -X utf8 tests/test_score.py` | 4 tests OK | 기존 채점 계약 회귀 |
| dev mock 명령 (아래) | 200건·49열 PASS, 응답 진단 200개·원응답 미포함 | 실제 모델 성공 건수 0 |
| 패키징 명령 (아래) | ZIP 압축 해제 mock 10건 PASS | 기본 실행은 모델 경로 없으면 실패 |
| 노트북 | 모든 코드 셀 Python 문법·nbformat 검사 PASS | Colab UI·설치·CUDA·다운로드·실제 추론은 미검증 |

```powershell
python -X utf8 script.py --mock --input open/dev.jsonl --data-dir open/data --output-dir artifacts/baseline-diagnostics/mock-dev
python -X utf8 tools/package.py --output artifacts/baseline-diagnostics/submit.zip --colab-output artifacts/baseline-diagnostics/colab-bundle.zip
```

dev mock의 전체 출력은 `artifacts/baseline-diagnostics/mock-dev.log`, 실행 설정·자산 해시는
같은 디렉터리의 `mock-dev/diagnostics.jsonl`·`run_report.json`에 있다.
최종 코드/ZIP 생성 기록은 `artifacts/baseline-diagnostics/submit.manifest.json`에 있다.
기존 출력은 덮어쓰지 않으므로 재실행은 새 경로를 사용한다.

## 자산 식별

| 파일 | SHA-256 |
| --- | --- |
| 이전 제출 `artifacts/baseline/submit.zip` (보존) | `d3d6622e5171cb368adc4f9e5618f9f20f90442a5d3dc64e362a6766c36a9b6a` |
| 변경 `script.py` | `374fdaa7db4f9fd2bc38b77a5f8a50d94fee24ecac5abb5e65befd4c09754b0c` |
| `artifacts/baseline-diagnostics/submit.zip` | `f73c1e4cbc8dde290b53db4a017e29a7e114ef5e97729f6189f52539dd2c3af0` |
| `artifacts/baseline-diagnostics/colab-bundle.zip` | `bff98380b59cc6d83f2de9a178a34ff328b2dbc575bf5a7826fa2590e7d8f6af` |

Colab 노트북은 제출 ZIP의 코드 해시를 실제 성공 보고서와 대조한다. 번들은 대회 제출물이 아니다.
설치·모델 다운로드·GPU 추론까지 성공한 증거는 아직 없다.

후속 요청 검증: 토큰이 없어도 다운로드를 시도하던 기존 셀에서 신규 검사 실패를 확인한 뒤,
빈 토큰 거부와 `snapshot_download`의 명시적 token 전달을 구현해 통과했다.
서버 계약 검사는 mock 실행 결과를 일부 합성한 테스트 메타데이터로 검증했으며 실제 모델 성공으로 보고하지 않는다.
Colab 통과 시 내려받는 제출 ZIP은 위 해시의 파일 그대로다. 제출 코드는 이번 후속 요청에서 변경하지 않았다.

다음: [Colab 실행 안내](../../docs/colab.md)에 따라 실행한 결과 ZIP을 확인한다.
`finish_reason=length`인지, 호출/응답 건수/파싱 중 어느 단계인지 구분한 후 수정 대상을 결정한다.
현재 출력 예산·프롬프트·재시도 횟수는 유지했다. 서버 실패의 근본 원인은 여전히 미확정이다.

## clone 경로 보완

기본 `SOURCE_MODE="clone"`에서 공개 main을 가져와 실제 커밋 SHA·요청 ref·URL을 기록하고,
clone의 기존 package 도구로 제출 ZIP/번들을 생성한다. 이후 기존 ZIP 검증과 서버 진입점 검사를 그대로 사용한다.
수동 업로드는 `SOURCE_MODE="upload"`에서만 실행한다. HF_TOKEN 필수 모델 다운로드는 유지한다.

clone 셀 부재를 신규 검사에서 재현한 뒤 `tests/test_package.py` 4개를 통과했다 (12.564초).
로컬 Git main을 실제 clone하여 생성 ZIP 코드와 기록 커밋 일치를 확인했다. GPU 모델 실행은 하지 않았다.
이전 커밋·PR·머지 요청의 후속 보완으로 공개 main에 반영하며 독립 리뷰 생략 지시를 유지한다.
