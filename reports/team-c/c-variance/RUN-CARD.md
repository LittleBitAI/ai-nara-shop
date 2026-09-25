# C-variance 실행 카드 — 같은 코드로 dev 200건 6회

담당 C · 2026-09-26 · 한 장이다. 왜 이것을 재는지는 `README.md` 가 소유한다.

## 한눈에

| | |
| --- | --- |
| 무엇 | `origin/main` 코드를 **한 글자도 안 바꾸고** dev 200건을 6회 돌린다 |
| 받아 갈 커밋 | **`e1474d1`** — 아래 `REPO_REF` 한 줄에 박는다 |
| 바꿀 줄 | 셀 `[1]` 의 `REPO_REF` **하나** + 맨 끝에 붙여넣는 셀 **하나** |
| 예상 소요 | 셋업 + 약 **1시간 35분**(통과당 15.4분 × 6) |
| 받을 파일 | 결과 ZIP 1개 — 그 안에 `var-01` … `var-06` 여섯 폴더 |
| 한 세션 | **한 세션에서 6회를 다 돈다.** 나누면 런타임이 바뀌어 변수가 하나 늘어난다 |

## 1. 셀 `[1]` — 한 줄만 고친다

`SOURCE_MODE` 는 `"clone"` 그대로 둔다. `REPO_REF` 를 아래로 바꾼다.

```python
REPO_REF = "e1474d1"        # origin/main. 이 실험은 코드를 바꾸지 않는 것이 전부다
```

`REPO_REF` 를 정의하는 셀은 `[1]` **하나뿐**이다(소스에서 확인).

## 2. 첫 셀부터 순서대로 실행한다

중간부터 실행하면 안 된다. 아래 이름들이 앞 셀에서 만들어진다.

| 셀 | 만드는 것 | 뒤에서 쓰는 곳 |
| --- | --- | --- |
| `[1]` | `WORK` · `RESULTS` · `SUBMISSION` · `case_inputs` · `SCRIPT_SHA256` | 전부 |
| `[3]` | 저장소·데이터 clone | `[12]` |
| `[8]` · `[10]` | 대회 Python · 고정 리비전 모델 | `[12]` |
| `[12]` | **`run_case()` 정의** | 붙여넣을 셀 |

`[14]` 부터 `[18]` 까지는 **돌려도 되고 건너뛰어도 된다.** 돌리면 `dev` · `dev-debug`
통과가 추가로 생기지만 설정(`debug_responses`)이 달라 이 실험의 6회와 같은 저울이
아니다. 시간을 아끼려면 `[12]` 까지만 돌리고 아래 셀로 간다.

## 3. 맨 끝에 이 셀을 붙여넣고 실행한다

저장소의 노트북 파일은 고치지 않는다. Colab 화면에서 셀 하나를 추가해 붙여넣는다.

```python
# C-variance: 같은 코드·같은 입력·같은 설정으로 dev 200건을 6회 돈다.
# check_live 는 debug_responses=False 를 요구하므로 여기서는 못 쓴다 — 자체 검사를 한다.
VARIANCE_N = 6
VARIANCE_ARGS = ["--debug-responses"]   # 여섯 통과 전부 같은 값. 원응답을 남겨 뒤에 재생에 쓴다

for k in range(1, VARIANCE_N + 1):
    name = f"var-{k:02d}"
    run_case(name, WORK / "open/dev.jsonl", args=VARIANCE_ARGS)
    report = json.loads((RESULTS / name / "run_report.json").read_text(encoding="utf-8"))
    settings = report["reproduction"]["settings"]
    if report["mode"] != "live" or not settings["debug_responses"]:
        raise RuntimeError(f"{name}: live 가 아니거나 원응답을 안 켰다")
    if report["건수"] != 200 or report["model_success_count"] != 200:
        raise RuntimeError(f"{name}: 200건 전건 성공이 아니다")
    if report["code_sha256"] != SCRIPT_SHA256:
        raise RuntimeError(f"{name}: 코드 해시가 다르다")
    if report["input_sha256"] != case_inputs[name]:
        raise RuntimeError(f"{name}: 입력 해시가 다르다")
    if report["sme_fallback_count"] or report["company_size_fallback_count"]:
        raise RuntimeError(f"{name}: fallback 이 있다 — 이 통과는 버린다")
    events = [json.loads(line) for line
              in (RESULTS / name / "diagnostics.jsonl").read_text(encoding="utf-8").splitlines()]
    responses = [e for e in events if e["event"] == "response"]
    if not responses or any("response_text" not in e for e in responses):
        raise RuntimeError(f"{name}: 원응답이 안 남았다")
    print(f"{name}: 전건 성공 · 추론 {report['추론_s']}s · 원응답 {len(responses)}건")

print(f"\n{VARIANCE_N}회 완료. 채점은 로컬에서 한다 — 노트북 점수를 판정에 쓰지 않는다.")
```

**여섯 통과가 전부 같은 설정이다.** `--debug-responses` 를 켜는 이유는 `README.md` §3-4 에
있다 — 판정 경로에 영향이 없음을 코드로 확인했고(§1-2), 원응답이 남으면 이 비싼 회차를
나중에 재생 실험에 다시 쓸 수 있다.

## 4. 결과 ZIP 을 받는다

셀 `[20]` 을 실행한다. **중간에 무엇이 실패했어도 이 셀은 따로 실행한다** —
추론이 끝난 통과의 자료는 이미 `RESULTS` 에 있다(`docs/colab.md` §8).

ZIP 안에 있어야 하는 것.

| 경로 | 확인 |
| --- | --- |
| `var-01/` … `var-06/` | 여섯 개 다 있는가 |
| `var-0k/submission.csv` | 200행인가 |
| `var-0k/run_report.json` | `code_sha256` 여섯 개가 전부 같은가 |
| `var-0k/diagnostics.jsonl` | `response_text` 가 200건씩 있는가 |
| `source.json` | `commit` 이 `e1474d1` 로 시작하는가 |

## 5. 중단되면 볼 곳

| 증상 | 어디 | 어떻게 |
| --- | --- | --- |
| `FileExistsError` | `run_case` 의 `data.mkdir(parents=True)` | 같은 `name` 을 두 번 불렀다. `var-0k` 이름이 겹치지 않는지 본다 |
| `서버 기본 추론 설정 불일치` | `check_live` | 이 회차에 `check_live` 를 부르면 안 된다 — `debug_responses=False` 를 요구한다(`README.md` §4-1) |
| `{name}: fallback 이 있다` | 위 셀의 자체 검사 | 그 통과만 버리고 나머지로 집계한다. 몇 회가 남았는지 보고에 적는다 |
| 세션이 끊겼다 | — | 남은 통과를 이어 돌리지 **않는다**. 런타임이 바뀌면 변수가 하나 늘어난다. 끝난 회차 수를 적고 거기까지로 집계한다 |
| 중간 셀 실패 | — | 셀 `[20]` 을 따로 실행해 로그 ZIP 을 받는다 |

## 6. 받은 뒤

`AUDIT.md` 의 명령을 그대로 돌린다. **그 문서는 회차 전에 고정됐다 — 결과를 보고
고치지 않는다.**
