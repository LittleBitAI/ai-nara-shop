---
scope: project
severity: contract
triggers: ["절대 경로", "개인 경로", "run_report", "diagnostics", "script.py", "record_path", "check_live"]
domain: 'artifacts'
title: "fix: 제출 코드의 실행 기록에서도 절대 경로를 없앤다"
branch: "fix/portable-paths-in-script"
---

# fix: 제출 코드의 실행 기록에서도 절대 경로를 없앤다

무엇. [015](2026-09-17-015-fix-portable-paths-in-records.md)가 남겨 둔 자리를 닫습니다.
`script.py`에 `record_path()`를 넣어 `run_report.json`·`diagnostics.jsonl`·콘솔 로그에 적히는
경로를 제출 폴더 기준 상대 경로로 바꿉니다. 밖이면 `<외부>/<파일명>`입니다. 실제 입출력·해시
계산은 원래 값을 그대로 씁니다. Colab 노트북 `check_live`는 기록된 `model_dir`을 고정 리비전
이름으로 대조하도록 한 줄 바꿨습니다.

왜. 사용자 확인에 따라 제출 오류 위험을 먼저 조사했고, 기록된 경로 문자열을 기능적으로 읽는 곳이 없다는 것만 확인됐을 뿐 실제 GPU·서버 실행으로 증명한 것은 아닙니다.
소비처를 전수 확인했습니다. `tools/package.py`와 `tests/test_baseline.py`는 `mode`·
`model_success_count`·`model`만 읽고, `tools/langfuse_tail.py`는 `settings`를 표시용으로만
넘기며, `asset_sha256`은 별도 `assets` 딕셔너리로 계산해 이번 변경과 무관합니다. 유일한
결합은 노트북 `check_live`의 `settings["model_dir"] != MODEL_DIR` 비교였고 테스트가 잡았습니다.
절대 경로 접두사는 무결성 근거가 아니었으므로 스냅샷 폴더 이름이 고정 리비전인지로 바꿉니다.
`record_path()`는 어떤 입력에도 예외를 올리지 않게 만들어 기록이 추론을 깨뜨리지 않습니다.

검증: 수정 전 `script.py`를 그대로 mock 실행해 `run_report.json`·`diagnostics.jsonl` 양쪽에서
`C:/`가 잡히는 것을 재현했고, 수정 후 회귀 검사가 0건을 확인합니다.
`tests/test_baseline.py::test_mock_cli_and_invalid_inputs`에 기록 경로 형태와 패턴 검사를
넣었습니다. 28건 OK, Ruff 통과. 제출 ZIP SHA-256은 코드가 바뀌었으므로 함께 바뀝니다.
**실제 GPU·Colab 회차와 서버 제출로는 아직 확인하지 않았습니다.**

출처. `script.py` `record_path()` · `notebooks/colab-baseline.ipynb` `check_live` ·
`tests/test_baseline.py`
