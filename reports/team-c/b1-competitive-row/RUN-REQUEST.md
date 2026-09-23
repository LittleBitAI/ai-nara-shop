# B1 — 경쟁제품 판정의 근거 행 (`competitive_row`) 실행 요청서

담당 C · 2026-09-22 · **설계와 요청서까지다. 적용하지 않았고 회차도 돌리지 않았다.**

**실행은 C(사용자)가 한다.** 이 문서의 합격 기준은 **회차 전에 고정된 것**이며
결과를 보고 고치지 않는다.

## 0. 무엇을 바꾸나

company 출력에 필드 하나를 더한다.

> **`competitive_row`** — 그 공고에 제공된 `일치후보`·`서비스보조목록` 중
> 구매 대상이 일치하는 **행 하나의 `세부품명번호`**, 없으면 `null`.

코드는 **그 번호가 제공 목록 안에 있는지만 대조한다.** 그 번호가 경쟁제품인지 다시
판단하지 않는다. **판정은 목록 행의 존재로 확인된다.**

검증된 행이 없으면 `scope=competitive` 를 채택하지 않고 **`unknown`** 으로 둔다.

**`general` 로 뒤집지 않는다.** 그 길은 이미 기각됐다 — v10·v11·v12·v13 의 현재 TP 셀
10개가 정의상 사라진다. `unknown` 은 "경쟁제품이 아니다" 가 아니라 **"확인되지 않았다"**
이고, `_company_size_bands` 가 `unverified_scope` 로 기본 판정을 보존한다.

| 파일 | 내용 |
| --- | --- |
| `reports/team-c/b1-competitive-row/competitive-row.diff` | `script.py` 8조각 + `tools/replay_run.py` 1조각 |

**`script.py`·`tools/replay_run.py` 에 적용하지 않았다.** `git apply --check` 로 적용
가능성만 확인했고(**`c9398ad`·`1b34786`·`37fe53e` 셋 다 통과**) 저장소의 두 파일은 그대로다.

```bash
git apply --check reports/team-c/b1-competitive-row/competitive-row.diff   # 통과 확인됨
git apply reports/team-c/b1-competitive-row/competitive-row.diff           # 회차 직전에만
```

### 0-1. 리뷰 [P1] 수정 — 구 회차에 소급하지 않는다

**첫 판은 보관 회차 재생을 깨뜨렸다.** `competitive_row` 를 `props` 에 무조건 넣어
`company_size_schema(legacy=True)` 에서도 필수가 됐고, 보관된 옛 원응답에는 그 필드가
없으므로 재생이 **`company_size: 사실 필드 결손`** 으로 즉시 죽었다.

기존 `clause_quotes`·`qualification_role` 과 **같은 방식**으로 고쳤다.

| 자리 | 무엇 |
| --- | --- |
| `script.py` 마커 상수 | `COMPETITIVE_ROW_PATTERN` — 재생기가 `hasattr` 로 코드 능력을 가린다 |
| `company_size_schema(…, competitive_row=True)` | `competitive_row and not legacy` 일 때만 넣는다 |
| `parse_judgment(…, company_size_competitive_row=True)` | 스키마에 그대로 넘긴다 |
| 회차 설정 기록 | `"company_size_competitive_row": True` 를 남겨 **다음 재생이 이 회차의 능력을 안다** |
| `tools/replay_run.py` | `hasattr(script, "COMPETITIVE_ROW_PATTERN")` 이면 `settings.get(...)` 로 켠다 |
| `verified_competitive_row()` | 필드 자체가 없으면 **`None`** — 판단하지 않는다 |

**옛 원응답에 기본값을 채워 넣지 않는다.** 필드가 없으면 `None` 이고
`verify_company_size` 의 조건이 `is False` 라 걸리지 않는다 — 그 회차의 동작이 그대로다.

**실측으로 확인했다.**

| 코드 | 보관 회차 재생 | 제출 CSV |
| --- | --- | --- |
| diff **미적용** (저장소 그대로) | 성공 | `sha256 7dd13743d39564db…` |
| diff **적용** (임시 사본) | **성공** | **같은 `7dd13743d39564db…` · 바이트 동일** |
| **첫 판 diff** (참고) | **실패** | `company_size: 사실 필드 결손` |

`tests/test_c_competitive_row_diff.py` **10건**이 이것을 고정한다 — 바이트 동일,
새 경로에서 필수, legacy·플래그 꺼짐 경로에서 제외, 검증 실패 시 `unknown`(`general` 아님),
그리고 **diff 가 저장소에 적용돼 있지 않음**까지 본다.

> **이 검사는 미적용 저장소를 전제한다.** 현재 저장소 파일을 사본으로 떠서 거기에 diff 를
> 적용해 전후를 비교하기 때문이다. **`git apply` 앞에서 돌린다**(§3 절차 1단계).
> 이미 적용된 저장소에서는 전제가 깨졌음을 알리며 **10건 전부 skip** 된다 — 빨간불로 두면
> 진짜 회귀와 구분되지 않는다. 적용 뒤의 확인은 CSV 바이트를 직접 비교한다(§3 2-1단계).

## 1. 왜 이 관측인가 — 입력 신호로는 못 가른다

`039`·`040`·`041`·`044` 는 `scope` 를 **사업명·품명**으로 `competitive` 라 했다.
네 공고의 원문에 "경쟁제품" 표기는 **0회**다.

**그렇다고 문자열이나 후보 유무로 거르면 안 된다** — 이미 측정하고 버린 길이다.

| 무리 | 공고 수 | 현재 TP 셀 |
| --- | ---: | ---: |
| 모델이 `competitive` 라 한 것 중 "경쟁제품" 표기 **있음** | 11 | **0** |
| 같은 것 중 표기 **없음** | 67 | **10** |
| 그 4건이 속한 "일치후보 0 · 서비스보조목록만 있음" | 19 | **5** |

**표기가 있는 쪽의 TP 가 0이고 없는 쪽이 10이다.** 문자열로 거르면 TP 10 이 죽는다.
후보 목록이 비었다고 거르면 그 안의 TP 5 가 죽는다.

**그래서 거르지 않고 모델에게 근거를 지목하게 한다.** 코드는 지목된 행의 존재만 대조한다.
이것은 새 판별축이 아니라 **이미 내린 판정에 근거를 요구하는 것**이다.

## 2. 왜 CPU 재생으로 못 재나

프롬프트와 출력 스키마가 바뀐다. 보관 회차의 원응답에는 `competitive_row` 필드가 **없다.**
재생기도 그렇게 말한다.

> 모델을 부르지 않았다. **프롬프트·스키마를 바꾸는 후보는 이 경로로 잴 수 없다.**

**두 가지를 구분한다.**

| | |
| --- | --- |
| 보관 회차 재생이 **죽지 않는다** | §0-1 이 고친 것. 바이트 동일까지 확인했다 |
| 그 재생으로 **이 후보의 효과를 잴 수는 없다** | 옛 원응답에 새 필드가 없어 관측 자체가 없다 |

재생이 도는 것은 **회귀가 없다는 뜻**이지 효과를 쟀다는 뜻이 아니다.
**GPU 회차가 필요하다.** 그래서 이 요청서다.

## 3. 실행 절차

```bash
# 0) 기준 확인 — 이 값이 안 나오면 멈춘다
python -X utf8 tools/replay_run.py --case reports/runs/colab-1789902969401579900/dev-debug \
  --output-dir <head>
python -X utf8 tools/score.py --truth open/dev_labels.csv --pred <head>/submission.csv \
  --output-dir <head-score>
#    Macro 0.609274806721 · v14 7/2/1 · v15 4/1/2 · v16 4/2/2 · v17 5/6/1 · v18 1/2/6

# 1) 회귀 검사는 **적용 전에** 돌린다. 이 검사는 미적용 저장소를 전제한다
python -X utf8 -m pytest tests/test_c_competitive_row_diff.py -q
#    10 passed 여야 한다. 적용 뒤에 돌리면 전제가 깨져 전부 skip 된다

# 2) diff 적용 — script.py 와 tools/replay_run.py 둘 다 바뀐다
git apply reports/team-c/b1-competitive-row/competitive-row.diff

# 2-1) 적용 뒤의 회귀 확인은 CSV 바이트를 직접 본다
python -X utf8 tools/replay_run.py --case reports/runs/colab-1789902969401579900/dev-debug \
  --output-dir <regr>
python -X utf8 -c "import sys,hashlib; a=open(sys.argv[1],'rb').read(); b=open(sys.argv[2],'rb').read(); \
print('바이트 동일' if a==b else '★ 다르다 — 여기서 멈춘다', hashlib.sha256(a).hexdigest()[:16])" \
  <head>/submission.csv <regr>/submission.csv
#    "바이트 동일" 이 아니면 여기서 멈춘다

# 3) **실험 커밋으로 두 파일을 고정한다** — 회차 재생이 이 커밋에 걸린다
git add script.py tools/replay_run.py
git commit -m "run: B1 competitive_row 회차 코드 고정"
git rev-parse HEAD          # 이 값을 회차 기록의 code.commit 으로 쓴다

# 4) dev 200건 회차 1회 (company_size 단계 포함 전 파이프라인)
#    같은 ZIP·같은 시드. 노트북 커밋과 위 실험 커밋을 회차 기록에 고정한다.

# 5) 회차 등록·채점
python -X utf8 tools/register_run.py --zip <새 ZIP>
#    manifest.json 의 code.commit 이 3) 의 커밋인지 확인한다 (docs/runs.md 보관 규약)
python -X utf8 tools/score.py --truth open/dev_labels.csv --pred <new>/submission.csv \
  --output-dir <new-score>
python -X utf8 tools/compare_runs.py --before <head>/submission.csv --after <new>/submission.csv \
  --truth open/dev_labels.csv --items v14,v15,v16,v17,v18 --output-dir <cmp-c>
python -X utf8 tools/compare_runs.py --before <head>/submission.csv --after <new>/submission.csv \
  --truth open/dev_labels.csv --items v10,v11,v12,v13 --output-dir <cmp-scope>

# 6) 새 회차가 그 커밋의 코드로 재현되는지 확인한다
python -X utf8 tools/replay_run.py --case <new>/dev-debug --verify
#    --verify 는 manifest 의 code.commit 에서 script.py 를 꺼내 쓴다

# 7) 작업 트리를 되돌린다 (실험 커밋은 이력에 남는다)
git checkout -- script.py tools/replay_run.py
git diff --stat            # 빈 출력이어야 한다
```

### 3-1. 왜 실험 커밋이 필요한가 — 되돌리면 새 회차를 못 재생한다

**첫 판은 "설정 키만 있으면 새 회차도 재생된다" 고 적었다. 틀렸다.**

`reproduction.settings.company_size_competitive_row` 를 **읽는 코드가 이 diff 안에만** 있다.
두 파일을 되돌리면 그 키는 아무도 안 본다. 그보다 앞서, **미적용 `script.py` 는 새 응답의
`competitive_row` 를 파싱 단계에서 버린다.**

실측(같은 JSON 을 양쪽에 먹였다):

| 코드 | 파싱 | `competitive_row` |
| --- | --- | --- |
| 미적용 `script.py` | OK · 키 **15**개 | **버려짐** |
| 적용 `script.py` | OK · 키 **16**개 | 보존 |

`parse_judgment` 가 `{k: facts[k] for k in properties}` 로 스키마 밖 필드를 버리기 때문이다.
필드가 사라지면 `verified_competitive_row()` 가 `None` 을 내고(애초에 그 함수도 없다)
**`scope=competitive` 가 `null` 이거나 목록 밖 행이어도 `unknown` 게이트를 거치지 않는다.**
즉 **되돌린 코드로는 새 회차의 근거 행 판정을 재현할 수 없다.**

그래서 `docs/runs.md` 보관 규약대로 **회차에 쓴 코드를 커밋으로 고정하고
`manifest.json` 의 `code.commit` 에 적는다**(출처 `source.json`·`git-commit.log`).
이후 그 회차의 재생은 **그 커밋의 코드**로 한다.

**한 가지 더 — `--verify` 는 `script.py` 만 꺼낸다.** `tools/replay_run.py:run_script()` 가
`git show <commit>:script.py` 로 한 파일만 읽고 재생기 자신은 HEAD 것을 쓴다.

| 무엇을 재생하나 | 되는가 | 이유 |
| --- | --- | --- |
| **새 회차**를 `--verify` 로 | **된다** | 고정 커밋의 `script.py` 가 쓰이고, `parse_judgment` 의 `company_size_competitive_row` 기본값이 `True` 라 HEAD 재생기가 그 키를 안 넘겨도 새 스키마로 파싱된다 |
| **옛 보관 회차**를 diff 적용 상태에서 | **재생기도 그 커밋 것이어야 한다** | HEAD 재생기는 키를 안 넘기고 기본값이 `True` 라 옛 응답이 "사실 필드 결손" 으로 죽는다. 고정 커밋의 `tools/replay_run.py` 가 `settings.get(...)` 로 꺼 준다 |

**두 파일을 함께 고정해야 하는 이유가 이것이다.** 워크트리로 통째로 꺼내 쓰면 확실하다.

```bash
git worktree add <dir> <실험 커밋>
python -X utf8 <dir>/tools/replay_run.py --case <case> --script <dir>/script.py \
  --data-dir open/data --input open/dev.jsonl --output-dir <out>
```

## 4. 합격 기준 — **회차 전에 고정한다**

네 가지를 **전부** 충족해야 채택 후보로 올린다. 하나라도 어긋나면 반려다.

| # | 기준 | 임계값 | 왜 이 값인가 |
| --- | --- | --- | --- |
| **1** | **v18 FN 감소** | **3셀 이상** (6 → 3 이하) | 같은 ZIP 재실행 churn 이 1~2셀이다. 그보다 커야 회차 잡음과 구분된다 |
| **2** | **scope 를 함께 쓰는 항목의 TP 보존** | v10·v11·v12·v13 의 현재 **TP 셀 10개 전부 유지** | 같은 `scope` 사실을 소비한다. 하나라도 죽으면 이 관측이 TP 를 깎은 것이다 |
| **3** | **대상 밖 항목 변화** | 같은 ZIP 재실행 churn 범위 **안** (과거 13쌍 실측 17~45셀) | 밖으로 새면 회귀다 |
| **4** | **추가 호출 0 · 출력 토큰 증가 실측** | dev 200건 추가 추론 **92.193초 한도 안** | 서버 예산 6,380/7,200초 중 남은 전부다 |

### 기준 1 의 근거 — v18 FN 6건의 최초 차단

| 차단 사유 | 공고 | 이 관측이 닿는가 |
| --- | --- | --- |
| `outside_general_scope` | **039 · 040 · 044** | **닿는다.** `scope=competitive` 가 근거 행 없이 선 자리다 |
| `unverified_scope` | **041** | **닿는다.** 같은 축이다 |
| `absence_not_observable` | 22 | 닿지 않는다 (A 티켓이 다룬다) |
| `unverified_qualification` | 038 | 닿지 않는다 |

**사정권이 4건이므로 3셀을 임계로 둔다.** 4건 전부는 요구하지 않는다 —
`039` 는 `qualification=small_only` 라 scope 만 바뀌어도 부재가 아니고,
`044` 는 `unknown` 정규화가 더 남는다(A-2 §6 이 이미 기록).

### 기준 4 의 근거 — 토큰 실측 기준선

| 값 | 실측 |
| --- | --- |
| 현재 `company_size` 단계 추론 | **247.363초 / 200건** |
| 현재 company 유효 응답 | 200건 · 출력 평균 **698자** · 최대 **998자** |
| `competitive_row` 한 필드의 출력 증가 상한 | 키·값·구분 약 **31자** → 200건 **6,200자** ≈ **2,480토큰** |

**이것은 산술 추정이다.** 프롬프트가 길어져 입력 토큰도 늘고, 모델이 목록을 더 꼼꼼히
읽느라 느려질 수 있다. **회차에서 `company_size_inference_seconds` 를 실측해
247.363초 대비 증가분이 92.193초 안인지 확인한다.**

넘으면 기준 4 위반이다. 다른 기준을 충족해도 **반려**한다 — 서버 예산을 넘기면
제출 자체가 불가능하다.

## 5. 회차에서 반드시 기록할 것

| 항목 | 왜 |
| --- | --- |
| `company_size_inference_seconds` | 기준 4 판정 |
| `company_size_response_count` · 출력 한도 실패 건수 | 스키마가 길어져 잘리는지 |
| `competitive_row` 가 **null 이 아닌** 공고 수 | 발화율 |
| 그중 **제공 목록에 실제로 있던** 수 | 모델이 번호를 지어내는지 |
| `scope` 분포 전→후 (competitive 78건이 몇으로) | 관측의 실제 효과 |
| `039·040·041·044` 각각의 `competitive_row`·`scope`·v18 | 사정권 4건의 개별 결과 |
| v10·v11·v12·v13 의 TP 셀 10개 개별 생존 | 기준 2 판정 |

**`competitive_row` 가 목록 밖 번호였던 건수를 반드시 센다.** 모델이 공고 본문이나
메타의 코드를 베껴 오면 이 관측은 무효다 — 그 경우 관측 자체를 반려한다.

## 6. 예상되는 실패 방식 — 미리 적는다

| 실패 | 징후 | 그때의 판단 |
| --- | --- | --- |
| 모델이 아무 행이나 지목해 `competitive` 를 유지 | 목록 밖 번호가 많다 · scope 분포가 안 움직인다 | **반려.** 근거 요구가 작동하지 않는다 |
| 모델이 지나치게 보수적이 되어 전부 `null` | competitive 78 → 거의 0 · v10~v13 TP 가 죽는다 | **기준 2 위반으로 반려** |
| v18 은 열렸는데 v14·v17 FP 가 함께 는다 | 대상 항목 FP 증가 | 기준 1·3 을 각각 본다. Macro 로 뭉쳐 읽지 않는다 |
| 출력이 길어져 한도 실패가 는다 | `company_size_response_count` < 200 | **기준 4 위반으로 반려** |

**무응답을 0 으로 채워 성공 처리하지 않는다.** 실패 건은 실패로 적는다.

## 7. 증거 수준

이 문서는 **설계와 요청서뿐**이다.

| 사건 | 상태 |
| --- | --- |
| CPU 재생 — **효과 측정** | **불가** (프롬프트·스키마 변경) |
| CPU 재생 — **회귀 검사** | **실행함.** 보관 회차가 적용 전후 바이트 동일(`7dd13743d39564db…`) |
| 실제 GPU 회차 | **미실행** |
| 대회 서버 | **미실행** |
| `script.py`·`tools/replay_run.py` 적용 | **안 함.** 임시 사본에서만 적용해 재생을 확인했다 |
| 회차 코드 커밋 고정 | **안 함.** 회차를 안 돌렸다. §3 3단계가 그 절차다 |
| 새 회차 재생 가능성 | **미측정.** 새 회차가 없어 `--verify` 를 못 돌렸다. §3-1 은 코드를 읽고 파싱 동작을 실측한 결론이지 회차로 확인한 것이 아니다 |

**TP/FP/FN 전→후가 없다.** 후보의 효과를 이 문서가 주장하지 않는다.
`§1` 의 무리별 TP 수는 **현재 회차의 실측**이고 이 관측의 결과가 아니다.

## 8. 무라벨 배율

**아직 못 잰다.** `open/train_unlabeled.jsonl` 이 **이 작업 환경에** 없다.
`reports/publication.json` 이 `excluded[0].path` 로 기록한 790MB 제외 파일이고,
**리뷰어 환경에는 있다(수정 시각 2026-09-20).** 찾은 경로와 구분은 A 티켓 §7 에 있다.

**파일이 있어도 이 후보의 배율은 그것만으로 안 나온다.** 발화가 모델의 `competitive_row`
출력에 걸리므로 **무라벨 입력에 대한 `company_size` 원응답**이 따로 필요하다.
입력 파일은 "제공 목록에 후보 행이 있는 공고의 비율" 같은 **입력 측 조건**까지만 답한다.

회차가 기준 1~4 를 전부 통과해도 **채택은 무라벨 배율을 잰 뒤**다.
과거 dev +0.0179 후처리 규칙이 서버에서 −0.0026 이었다.

## 9. 미확인 사항

- **모델이 목록 행을 실제로 지목할 수 있는지.** 회차 전에는 알 수 없다.
- **`unknown` 으로 두는 선택이 v18 FN 을 여는지.** 이 관측의 회복 경로는 코드가
  뒤집는 것이 아니라 **모델이 스스로 `general` 을 내는 것**이다. 코드 쪽은 방어막이다.
  그 전환이 실제로 일어나는지는 회차가 답한다.
- **`서비스보조목록` 의 29행 규모.** 목록이 커지면 토큰이 늘어 기준 4 가 흔들린다.
- **`041` 의 `unverified_scope` 가 이 관측으로 풀리는지.** 인용 검증 실패가 원인이면
  근거 행을 더해도 안 풀린다.
- **새 회차가 고정 커밋으로 실제 재생되는지.** §3-1 은 파싱 동작을 실측하고 코드를 읽어
  세운 결론이다. **새 회차가 없어 `--verify` 로 확인하지 못했다.** §3 6단계가 그 확인이다.
- **실험 커밋을 어느 시점에 되돌릴지.** 작업 트리는 §3 7단계에서 되돌리지만 커밋은 이력에
  남는다. 그 커밋을 `main` 에 올릴지 실험 브랜치에 둘지는 정하지 않았다.
