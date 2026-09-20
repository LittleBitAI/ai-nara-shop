# 합본 후보 `0a8459a` 실행 요청

2026-09-20. **아직 실행 안 했다.** 이 문서는 무엇을 돌리는지와 무엇을 재는지만 정한다.

## 무엇이 들어 있나

| 변경 | 커밋 | 재생으로 잰 Δ | 비고 |
| --- | --- | ---: | --- |
| A2 경쟁제품 코드 게이트 | `ae5e2ef` | +0.035200 | 세 벌의 원응답에서 각각 확인 |
| v19 공고범위 | `b1` | +0.011 | 오탐 15→3 |
| v21 조문 하한 | `0a172a2` | +0.008 | 오탐 10→4 |
| 가설 A `competitive_by_catalogue` | `e32afa0` | +0.008420 | v17 FP 25→18, TP 손실 0 |
| v5 고시금액 구간 | `92be707` | +0.006614 | 오탐 6→1, TP 손실 0 |
| **`scope` 절 13줄** | **`0a8459a`** | **잴 수 없다** | 프롬프트 — 재생 0셀 |

앞의 다섯은 **보관 원응답 재생으로 정확히 측정돼 있다**(churn 0). 그러므로 이 회차의
결과에서 그 몫을 빼면 `scope` 절만의 효과가 남는다.

재생 기준 현재 dev **0.493138**. 서버는 `57761ff`(9/18) **0.2978624361** 이 마지막이다.

## 고정값

```
SOURCE_MODE = "clone"
REPO_URL    = "https://github.com/LittleBitAI/ai-nara-shop.git"   # 기본값 그대로
REPO_REF    = "0a8459a538cb55a02d2029b48b226f163224ce4d"          # 이것만 바꾼다
RUN_DIAGNOSTIC = True           # 기본값
DIAGNOSE_ITEMS = ""             # 기본값
```

**40자 전체 SHA 여야 한다.** 노트북은 `REPO_REF` 를 `git fetch origin <ref>` 에 그대로 넘기고
GitHub 은 임의 SHA fetch 를 전체 길이로만 받는다. 약칭 `0a8459a` 를 넣은 회차
`colab-1789877198887063146` 이 `fatal: couldn't find remote ref 0a8459a` 로 죽었다.
브랜치 이름 `feat/a1-a2-integrate` 도 되지만, 브랜치는 움직이므로 SHA 로 고정한다.

`MODEL_ID`·`REVISION`·seed·토큰 예산·양자화는 건드리지 않는다.
N1(`split`)·N3(`product`) 별도 호출은 꺼져 있고 A1(`company_size`)만 켜져 있다 —
`extra_call_items()` 가 `{'split': [], 'product': [], 'company_size': ['v14'..'v18']}` 를
돌려주는지로 확인한다.

## 클론 경로를 미리 확인했다

`0a8459a` 를 새로 클론해 확인한 값이다. Colab 이 받는 것과 같아야 한다.

| 파일 | sha256 앞 12자 | 줄바꿈 |
| --- | --- | --- |
| `script.py` | `75e066b641e6` | LF |
| `중기부고시_경쟁제품_세부품명.csv` | `445257e4821c` | LF |

**카탈로그 줄바꿈을 반드시 본다.** 작업본은 CRLF(`c372b24e…`)라 해시가 다르다.
git·Colab 이 쓰는 것은 LF 쪽이고, 기존 회차 셋도 전부 LF 로 돌았다.
CRLF 번들로 돈 회차는 `rejected-crlf-colab-bundle.zip` 으로 격리돼 있다.

클론에서 검사 191개 통과. `test_clone_prepares_bundle_from_recorded_commit` 하나는
그 클론에 `main` 로컬 브랜치가 없어 실패한다 — 클론 환경 탓이고 본 저장소에서는 192개 전부 통과한다.

## 회차 뒤에 재는 것

```powershell
python -X utf8 tools/replay_run.py --case <새-dev-debug> --script <실행한-script.py> --verify
python -X utf8 tools/compare_runs.py --items v10,v11,v13,v14,v15,v16,v17,v18 `
  --before reports/runs/colab-1789872032146524122/dev-debug/submission.csv `
  --after  <새-dev-debug>/submission.csv --output-dir reports/team-c/merged-candidate/vs-0a172a2
```

이 대조에는 **회차 churn 과 앞의 다섯 변경이 함께 섞인다.** 그래서 Macro F1 차이 하나로
`scope` 절을 판단하지 않는다. 먼저 볼 것은 이것이다.

- **모델의 `scope == "competitive"` 가 몇 건인가.** 지금 dev 200건에서 7건이고,
  v10·v11·v13 양성 합집합 15건과 **하나도 겹치지 않는다**.
  그 15건 중 몇 건이 열렸는지가 이 변경의 직접 지표다.
- 후보가 제대로 갔는데도 `general` 이던 9건
  (`PPS-DEV-076`, `-077`, `-14`, `-16`, `-063`, `-060`, `-13`, `-074`, `-078`)이 뒤집혔는가.
- 뒤집힌 자리에서 v10·v11·v13 의 TP 가 실제로 늘었는가. **게이트가 열린다고 판정이 맞는다는
  보장은 없다** — 근거는 지금까지 게이트가 열린 자리에서 v11·v12 가 각 TP 2건을 냈다는 것뿐이다.
- 대상 밖 16항목이 얼마나 움직였는가. 프롬프트 변경이라 0셀을 요구할 수 없고,
  과거 회차 간 실측 churn 은 17~45셀이다.

## 같은 ZIP 재실행

첫 회차가 채택 후보로 보이면 **같은 날 같은 제출 ZIP 을 그대로 한 번 더 돌린다.**
그래야 이 코드의 그날 churn 이 생긴다. 9/20 부터 Colab 회차 제한은 없다.
한 회차의 `dev` 와 `dev-debug` 만으로 이 절차를 대신하지 않는다.

## 제출

**하지 않는다.** dev 0.70 전에는 점수 목적의 제출을 하지 않는다.
제출로 얻는 정보는 Macro F1 스칼라 하나뿐이고 그것으로 무엇을 고칠지 정할 수 없다.
운영 확인 목적의 제출 1회는 9/29 10:00 전에 별도로 필요하다 — 첫 제출 `5506ca0` 이
실행 오류로 채점되지 않았기 때문이다.
