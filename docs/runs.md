# 실행 기록

Colab·GPU 실행 결과를 저장소에 보관하는 규약과, 지금까지의 실행 한 줄 요약입니다.
ZIP을 사람마다 따로 전달하지 않습니다. 팀원은 `git pull` 하나로 같은 기록을 받습니다.

## 보관 규약

- 폴더는 `reports/runs/<run-id>/`입니다. run-id는 결과 ZIP 이름의 숫자를 그대로 씁니다.
  `colab-results-1789621345861123113.zip` → `colab-1789621345861123113`.
- ZIP 바이너리는 커밋하지 않습니다. 내용을 풀어 텍스트(CSV·JSON·로그)만 넣습니다.
  ZIP 안의 폴더 구조와 파일명을 그대로 두고 바이트를 고치지 않습니다.
- 폴더에 `manifest.json` 한 개를 추가합니다. 적는 값은 아래와 같습니다.

| 칸 | 내용 | 출처 |
| --- | --- | --- |
| `zip_sha256` | 원본 ZIP의 SHA-256 | 전달받은 파일 |
| `code.commit` | 실행한 코드 커밋 | `source.json`, `git-commit.log` |
| `environment.gpu` | GPU·CUDA·Python·고정 패키지 버전 | `resources.json`, `runtime.json` |
| `inputs.sha256`, `cases.*.input_sha256` | 입력 자산 해시 | `bundle-manifest.json`, `run_report.json` |
| `cases.*.seconds` | 모델 로드 / 기본 추론 / 추가 추론 / 전체 시간 | `run_report.json`, `*-command.json` |
| `cases.*.counts` | 실패·선택 건수(모델 성공, 추가 호출 선택·폴백, 유효 JSON, 근거 폐기) | `run_report.json` |
| `raw_responses.included` | 원응답 포함 여부와 그 이유 | 실행 설정 `debug_responses` |

- 수치는 실행이 남긴 파일에서 그대로 옮깁니다. 다시 계산하거나 추정하지 않습니다.
- 파일 하나가 50MB를 넘으면 넣지 않고 경로·크기·이유를 남깁니다.
  GitHub 한도로 제외한 전례는 [publication.json](../reports/publication.json)에 있습니다.
- 등록 전에 `HF_TOKEN`·`hf_`·`api_key`·`Bearer`·개인 절대 경로 패턴을 검사합니다.
  값이 붙은 것만 위반입니다. 환경변수 이름, `hf_xet` 같은 패키지 이름, 이 규칙 문장 자체는 오탐입니다.
- 로그의 줄 끝 공백도 실행이 만든 바이트이므로 지우지 않습니다. 대신 `.gitattributes`에서
  이 폴더의 `whitespace=-trailing-space`를 켜 `git diff --check`가 그 줄을 보지 않게 합니다.
- 요약은 `.wiki/decisions/`에 한 장만 남기고 전문은 이 폴더가 소유합니다.
  로그 본문을 위키 기록에 붙여넣지 않습니다.

## 색인

한 행이 한 실행입니다. Macro F1과 커밋은 [history.json](../reports/team-score-audit/history.json)과
각 실행의 `manifest.json`에 기록된 값이며 이 표에서 다시 계산하지 않았습니다.

| run-id | 코드 커밋 | 최종 Macro F1 | 실행 환경 | 원응답 | 폴더 |
| --- | --- | ---: | --- | --- | --- |
| `colab-1789604529719466871` | `1c64604` | 0.2208013652894021 | 미보관 | 미보관 | — |
| `colab-1789607374469265263` | `9363f21` | 0.18470988076251235 | 미보관 | 미보관 | — |
| `colab-1789609860516528072` | `40e2cc6` | 0.21953760438037098 | 미보관 | 미보관 | — |
| `colab-1789613533157944500` | `57c78cf` | 0.21100769349007198 | 미보관 | 미보관 | — |
| `colab-1789616952134769089` | `e9e4022` | 0.2199212207545541 | 미보관 | 미보관 | — |
| `colab-1789621345861123113` | `654c556` | 0.22078771129016228 | Colab A100-SXM4-40GB, vLLM 0.26.0, CUDA 13.0 | 없음 | [reports/runs/colab-1789621345861123113/](../reports/runs/colab-1789621345861123113/) |

`미보관`은 그 실행의 ZIP을 이 규약으로 등록하기 전이라는 뜻입니다. 없었다는 뜻이 아닙니다.
점수만 [history.json](../reports/team-score-audit/history.json)에 남아 있고 실행 환경·원응답 여부는
그 파일에 없습니다. 24항목 지표와 개선 우선순위는 [점수 진단](../reports/team-score-audit/result.md)이 소유합니다.

`원응답 없음`은 `debug_responses=false`로 실행해 모델 응답 본문이 로그에 없다는 뜻입니다.
`diagnostics.jsonl`에는 응답 길이·토큰 수·종료 사유만 있습니다.

## 이 기록이 증명하지 않는 것

Colab 실행 성공은 대회 서버 성공이 아닙니다. 비공개 평가 입력 1,853건, 서버 GPU·메모리,
전체 실행 시간, 컨테이너·네트워크 차단은 확인하지 않았습니다. 실행 절차는
[Colab 실행](colab.md), 코드 변경 이력은 [T1 작업 기록](tasks/t1-baseline.md)이 소유합니다.
