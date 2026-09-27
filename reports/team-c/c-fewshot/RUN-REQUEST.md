# C few-shot v18 — off-dev 600 회차 실행 요청

담당 C · 2026-09-27 · 회차는 사람이 돌린다. 이 문서는 무엇을 돌리고 무엇으로 판정하는지만 정한다.

## 0. 왜 회차가 필요한가 — 재생으로 못 잰다

이 후보는 **`baseline` 시스템 프롬프트를 바꾼다.** `tools/replay_run.py` 는 저장된 원응답
위에서 모델 **뒤** 단계만 갈아 끼우므로 프롬프트 변경은 그 경로로 못 잰다(도구가 스스로
그렇게 적는다). 9/27 게이트도 같은 말을 한다 — `plan-0926-0929.md:43`
"A candidate that changes the prompt or the calls still needs a GPU run on the off-dev 600."

## 1. 무엇을 돌리나

| | |
| --- | --- |
| 회차용 커밋 | `run/c-fewshot-v18` — `origin/main` 위에 `script.py` 한 곳만 바꿨다 |
| 바뀐 것 | `build_system_prompt()` 이 `items is None`(=`baseline`)일 때만 v18 예시 한 쌍을 붙인다 |
| 대상 | **off-dev 600** = 진단 200 + 봉인 400 |
| ID 목록 | `reports/team-c/c-fewshot/offdev-600.ids.txt` (600줄, 매니페스트 동봉) |
| 예상 | A100 한 장에 **35~40분** (`a-offdev-0927.md` 의 같은 회차 추정) |
| 운영 `main` | **안 바꾼다.** 이 브랜치는 회차용이다 |

### 노트북

`a-offdev-0927.md` §Steps 가 정한 방식 그대로다 — `notebooks/colab-unlabeled-d.ipynb`
를 복사해 셋만 바꾼다.

| 바꿀 것 | 값 |
| --- | --- |
| `REPO_REF` | `run/c-fewshot-v18` 의 **40자 커밋 SHA** (아래 §5) |
| `IDS_FILE` | `reports/team-c/c-fewshot/offdev-600.ids.txt` |
| `N_NOTICES` | `600` |

**약칭 SHA 를 쓰지 않는다** — 노트북이 명시적으로 거부한다. 브랜치 이름도 쓰지 않는다.

**기준선 회차는 따로 안 돈다.** D 가 같은 600건에 현재 `script.py` 를 돌리고 있고
(9/27 배정), 그 결과가 이 회차의 짝이다. 같은 ID 목록·같은 라벨로 견준다.

## 2. 합격 기준 — 회차 전에 정한다

9/27 채택 규칙(`plan-0926-0929.md` "Adoption rule from 9/27")을 그대로 쓴다.
아래 넷이 다 서야 채택이고, 하나라도 무너지면 **보류 없이 기각**이다.

| | 기준 | 무엇으로 |
| --- | --- | --- |
| **1** | off-dev 라벨 항목의 Macro 가 **오른다** | `reports/offdev-0927/score_offdev.py` · 라벨 600 |
| **2** | **split-half**: 한쪽 절반에서 쓰고 다른 쪽에서 채점, 서로 바꿔도 양쪽에서 이긴다 | 같은 도구 |
| **3** | 신뢰 항목이 순 `(TP − FP)` **1셀 넘게 안 잃는다** | 항목별 표 |
| **4** | dev 재생이 Macro **0.01 넘게 안 내린다** | `tools/replay_run.py` + `tools/score.py` |
| **5** | 서버 총시간 **≤ 6,800초** | 회차의 `추론_s` × 1853 ÷ 600 환산 |

**이 후보만 따로 본다.** 예시는 v18 을 겨냥했지만 24항목 호출을 바꾸므로 **다른 항목이
움직일 수 있다** — 기준 3 이 그것을 잡는다.

### 이 후보에만 붙는 관측 (판정 아님, 기록용)

| | 물음 |
| --- | --- |
| (a) | v18 의 FN 10건 중 **예시가 닿는 7건**이 실제로 뒤집히나 |
| (b) | 절단된 3건은 그대로인가 (그대로여야 맞다 — 게이트가 닫혀 있다) |
| (c) | 프롬프트가 커져 **문서가 더 잘렸나** — `[Truncated documents…]` 붙은 건수 전후 |

(c) 는 중요하다. 예시 403토큰이 `baseline` 여유(중앙 4,916) 안이라 **안 잘려야 한다**.
잘렸으면 예산 계산이 틀린 것이므로 그 사실부터 적는다.

## 3. 시간 — 미리 잰 값

| | |
| --- | --- |
| 예시 크기 | **692자** |
| 보수적 토큰 | **403** (회차 실측 1.716 자/토큰) · 한글·영문을 나눠 세면 약 229 |
| `baseline` 호출 | 600건 × 1회 |
| 서버 환산 증가 | **약 +114초** (`BUDGET.md` §2 의 표, 400토큰 행) |
| 여유 | **372초** (목표 6,800 − `61c495c` 실측 6,428). PR #166 이 비운 시간을 더하면 더 넉넉 |

**상한 추정이다** — 시간의 일부는 출력 디코딩이 쓰므로 실제 증가분은 이보다 작다.
회차가 실측한다.

## 4. 감사 — 받은 뒤에 할 일

```bash
py -X utf8 tools/register_run.py --inbox artifacts/inbox --code-commit <RUN_COMMIT>

# 1·3 — off-dev 라벨로 채점
py -X utf8 reports/offdev-0927/score_offdev.py --pred <run>/submission.csv \
  --labels reports/labels-600/merged/diag.csv reports/labels-600/merged/sealed.csv

# 4 — dev 재생이 0.01 넘게 안 내리는지
git show <RUN_COMMIT>:script.py > <tmp>/pin.py
py -X utf8 tools/replay_run.py --case reports/runs/colab-1790445336782946136/var-01 \
  --script <tmp>/pin.py --output-dir <tmp>/dev
```

**주의.** 4 의 dev 재생은 **프롬프트가 바뀐 코드를 옛 원응답 위에 얹는 것**이라
엄밀히는 같은 저울이 아니다. 후처리·게이트가 깨지지 않았는지 보는 **안전 점검**으로만
쓰고, 판정 수로 쓰지 않는다. 판정은 off-dev 600 이 한다.

## 5. 회차용 커밋

브랜치 `run/c-fewshot-v18` 을 푸시한 뒤 40자 SHA 를 여기 적는다.

```
REPO_REF = "<이 브랜치의 40자 커밋 SHA>"
```

## 6. 이 회차가 답하지 않는 것

- **v10.** FN 11건 중 10건이 문서 절단이라 예시 밖이다(`TARGET.md` §2).
- **v13 의 게이트 2건.** 모델이 아니라 게이트가 정탐을 내린 자리다. 단계도 `sme` 다.
- **예시를 늘렸을 때.** 이 회차는 한 쌍이다. 두 쌍은 예산을 다시 재고 따로 돈다.
- **서버 전이.** off-dev 이득이 서버로 얼마나 가는지는 고정 계수가 없다.
