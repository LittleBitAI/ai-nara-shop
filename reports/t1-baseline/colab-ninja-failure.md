# Colab ninja 초기화 실패 (2026-09-17)

입력: 사용자 제공 `colab-results-1789602422101717812.zip`.
SHA-256: `05650ddf90b417b6b082834ac4e30bfbec0200b3709ce3209b2130aa47f83de6`.
실행 커밋: `a6313732b32c4ebb9c9620e5344f2dbe0a46bb14`.

## 확인된 원인

- A100-SXM4-80GB, Python 3.12.13, torch 2.11.0+cu130, vLLM 0.26.0,
  transformers 5.14.1, xgrammar 0.2.3. 고정 리비전 다운로드 exit 0, 141.83초.
- `pip-freeze.log`: `ninja==1.13.2` 설치됨.
- `sample.log`: FlashInfer 샘플러 JIT 빌드의 `subprocess.run`에서
  `FileNotFoundError: [Errno 2] No such file or directory: 'ninja'`.
  vLLM이 `RuntimeError: Engine core initialization failed`로 종료. 샘플 exit 1, 170.40초.
- 노트북은 venv Python의 절대 경로만 실행하고 venv/bin을 PATH에 넣지 않았다.
  Python 패키지는 로드되지만 하위 프로세스가 설치된 실행 파일을 찾지 못하는 경로다.

## 수정과 검증 경계

`run_logged`에서 venv Python 명령에만 venv 실행 경로를 PATH 앞에 넣고 VIRTUAL_ENV를 지정한다.
명시적으로 전달한 환경은 복사해서 보완하므로 토큰 제거 등 호출자의 환경 설정을 유지한다.
부트스트랩·git 명령은 기존 환경을 사용한다. 다운로드 전 `ninja --version`을 실제 자식 프로세스로
실행하고 경로·버전을 runtime.json에 기록한다. 제출 코드·패키지 버전·추론 설정은 변경하지 않는다.

회귀 검사는 임시 venv에 실제 실행 파일을 두고 노트북 함수로 자식 프로세스를 실행한다.
수정 전 탐색 실패, 수정 후 기본 환경과 명시 환경 모두 탐색 성공을 검사한다.
이는 로컬 실행 경로 검사이며 FlashInfer GPU 컴파일 성공을 대신하지 않는다.

실행 결과: `python -X utf8 tests/test_package.py` — 5개 통과, 13.360초.
기존 커밋의 setup 함수를 같은 회귀 검사에 넣으면 `FileNotFoundError`로 실패했다.
Ruff, notebook nbformat 검증, UTF-8 without BOM·LF, `git diff --check` 통과.

이번 실패는 공고 응답 생성 이전이다. 최초 서버의 62번 공고 ValueError 원인은 여전히 미확인이다.
다음은 최신 노트북을 첫 셀부터 다시 실행해 샘플 10건·dev 200건의 실제 성공과 채점을 확인하는 것이다.
