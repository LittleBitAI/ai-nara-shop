# C-variance 실행 카드 — 같은 코드로 dev 200건 6회

담당 C · 2026-09-26 · 한 장이다. 왜 이것을 재는지는 `README.md` 가 소유한다.

## 왜 지금 이 회차인가 (2026-09-26 저녁)

GPU 예산 1시간 반에 무엇을 태울지 고르려고 **회차 후보 셋의 상한을 재생으로 먼저 쟀다.**
둘은 거기서 밀렸다.

| 후보 | 상한 측정 | 판단 |
| --- | --- | --- |
| scope 인용 개선 | 인용이 **다 통과한다고 가정해도** 정탐 2(`036` v15 · `041` v18) 대 **오탐 4**(`09`·`041`·`160` 의 v10, `041` 의 v11). `13` 은 통과해도 안 올라간다 | 순효과가 마이너스일 수 있다 — **안 돌린다** |
| v10 품명 대조 | 품번 없는 122건에서 고시 품명이 걸리는 41건의 v10 양성률 **2.4%**, 안 걸리는 81건은 **7.4%**. 게이트로 쓰면 양성 6건이 죽는다(`script.py:102` 가 경고한 사고) | 방향이 반대다 — **안 돌린다** |
| C7 을 실은 회차 | 후처리 재생 후보라 같은 원응답 비교가 결정적이고, 이미 세 원응답에서 확인했다 | 새로 얻는 것이 적다 |
| **변동폭 N=6** | 팀 전체 판정의 분모. 지금 관측이 **0.034 하나**뿐이라 C 의 +0.0064 도 A 의 제출 판단도 잴 자가 없다 | **이것을 돌린다** |

이 회차가 채우는 빈칸은 `AUDIT.md` §5 의 판정 문장이다.

> 관측 6회의 Macro 범위는 **X** 다. 따라서 **X** 보다 작은 차이는 한 쌍의 회차로
> 판정하지 않는다.

## 한눈에

| | |
| --- | --- |
| 무엇 | `origin/main` 코드를 **한 글자도 안 바꾸고** dev 200건을 6회 돌린다 |
| 회차 브랜치 | **없다.** 코드를 안 바꾸므로 `origin/main` 을 그대로 받는다 |
| 받아 갈 커밋 | **`772ca12`** (`origin/main`) — 아래 `REPO_REF` 한 줄에 박는다 |
| 바꿀 줄 | 셀 `[1]` 의 `REPO_REF` **하나** + 맨 끝에 붙여넣는 셀 **하나** |
| 예상 소요 | 셋업 + 약 **1시간 35분**(통과당 15.4분 × 6) |
| 받을 파일 | 결과 ZIP 1개 — 그 안에 `var-01` … `var-06` 여섯 폴더 |
| 한 세션 | **한 세션에서 6회를 다 돈다.** 나누면 런타임이 바뀌어 변수가 하나 늘어난다 |

## 0. 회차 직전 점검 (2026-09-26)

**`origin/main` 이 `772ca12` 에서 `ea56ef0` 으로 움직였다.** PR #154(A 파트, off-dev
batch 2)가 머지되며 `script.py` 가 세 곳 바뀌었다 — `local_small_quote()` 신설,
v8 규칙 예외, `SIZE_LIMIT` 의 확인서 따옴표 허용. 전부 A 항목이고 C 항목은 안 건드린다.

**그래도 이 회차는 `772ca12` 를 그대로 쓴다.** 이유 둘.

- 질문을 만든 관측(12셀 · Macro 0.034367)이 그 코드 위에서 났다. 기준을 옮기면 N=6 의
  범위와 그 한 쌍을 나란히 못 놓는다.
- 이 카드와 `AUDIT.md` · `aggregate.py` 가 회차 **전에** `772ca12` 로 고정됐다.
  결과를 보기 전에 기준을 바꾸는 것이 이 실험이 피하려는 바로 그 일이다.

보고에는 "`772ca12` 코드에서 잰 값이고 `ea56ef0` 에서 다시 재지 않았다"를 적는다.

받은 뒤에 돌릴 두 게이트를 **회차 전에 기존 자료로 예행했다** — ZIP 이 온 뒤에 처음
터지면 1시간 35분을 다시 태워야 한다.

| 게이트 | 예행 | 결과 |
| --- | --- | --- |
| `replay_run.py --verify` | `colab-1790318892216968298/dev-debug` 를 `ca352d6` 판 `script.py` 로 | `재생 200건 · 회차 CSV와 동일` · exit 0 |
| `aggregate.py` | 같은 회차의 두 통과(`dev` · `dev-debug`) | 끝까지 돈다. 설정 16칸 중 `debug_responses` 하나만 `**다르다**` 로 잡고 범위 `0.034366790617` · 12셀을 낸다 |

예행의 `**다르다**` 는 **예정된 것이다.** 그 두 통과는 설정이 실제로 갈린 쌍이다.
이 회차의 여섯 통과는 전부 `--debug-responses` 라 그 칸도 `같다` 가 되어야 하고,
**`같다` 가 아니면 그 수를 변동폭이라 부르지 않는다.**

## 1. 셀 `[1]` — 한 줄만 고친다

`SOURCE_MODE` 는 `"clone"` 그대로 둔다. `REPO_REF` 를 아래로 바꾼다.

```python
REPO_REF = "772ca1284c8918c1fa4ca5729cc15dfe4dedb2d4"  # origin/main. 이 실험은 코드를 바꾸지 않는 것이 전부다
```

**40자 전체를 쓴다.** 노트북이 약칭 SHA 를 명시적으로 거부한다
(`REPO_REF="…"는 약칭 SHA입니다`). 브랜치 이름 `main` 도 쓰지 않는다 — 회차 도중
`main` 이 움직이면 여섯 통과가 같은 코드가 아니게 된다.

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
| `source.json` | `commit` 이 `772ca1284c8918c1fa4ca5729cc15dfe4dedb2d4` 인가 |

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
