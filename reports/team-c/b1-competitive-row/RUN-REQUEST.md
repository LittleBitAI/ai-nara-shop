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
| `reports/team-c/b1-competitive-row/competitive-row.diff` | 프롬프트 1 · 스키마 2 · 검증 2 조각 |

**`script.py` 에 적용하지 않았다.** `git apply --check` 로 적용 가능성만 확인했고
(`c9398ad`/`1b34786` 기준 통과) 저장소의 `script.py` 는 그대로다.

```bash
git apply --check reports/team-c/b1-competitive-row/competitive-row.diff   # 통과 확인됨
git apply reports/team-c/b1-competitive-row/competitive-row.diff           # 회차 직전에만
```

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

프롬프트와 출력 스키마가 바뀐다. 보관 회차의 원응답에는 `competitive_row` 필드가 없으므로
`tools/replay_run.py` 로 잴 수 없다. 재생기도 그렇게 말한다.

> 모델을 부르지 않았다. **프롬프트·스키마를 바꾸는 후보는 이 경로로 잴 수 없다.**

**GPU 회차가 필요하다.** 그래서 이 요청서다.

## 3. 실행 절차

```bash
# 0) 기준 확인 — 이 값이 안 나오면 멈춘다
python -X utf8 tools/replay_run.py --case reports/runs/colab-1789902969401579900/dev-debug \
  --output-dir <head>
python -X utf8 tools/score.py --truth open/dev_labels.csv --pred <head>/submission.csv \
  --output-dir <head-score>
#    Macro 0.609274806721 · v14 7/2/1 · v15 4/1/2 · v16 4/2/2 · v17 5/6/1 · v18 1/2/6

# 1) diff 적용
git apply reports/team-c/b1-competitive-row/competitive-row.diff

# 2) dev 200건 회차 1회 (company_size 단계 포함 전 파이프라인)
#    같은 ZIP·같은 시드. 노트북 커밋을 회차 기록에 고정한다.

# 3) 회차 등록·채점
python -X utf8 tools/register_run.py --zip <새 ZIP>
python -X utf8 tools/score.py --truth open/dev_labels.csv --pred <new>/submission.csv \
  --output-dir <new-score>
python -X utf8 tools/compare_runs.py --before <head>/submission.csv --after <new>/submission.csv \
  --truth open/dev_labels.csv --items v14,v15,v16,v17,v18 --output-dir <cmp-c>
python -X utf8 tools/compare_runs.py --before <head>/submission.csv --after <new>/submission.csv \
  --truth open/dev_labels.csv --items v10,v11,v12,v13 --output-dir <cmp-scope>

# 4) 되돌린다
git checkout -- script.py
git diff --stat            # 빈 출력이어야 한다
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
| CPU 재생 | **불가** (프롬프트·스키마 변경) |
| 실제 GPU 회차 | **미실행** |
| 대회 서버 | **미실행** |
| `script.py` 적용 | **안 함.** `git apply --check` 만 통과 |

**TP/FP/FN 전→후가 없다.** 후보의 효과를 이 문서가 주장하지 않는다.
`§1` 의 무리별 TP 수는 **현재 회차의 실측**이고 이 관측의 결과가 아니다.

## 8. 무라벨 배율

**아직 못 잰다.** `open/train_unlabeled.jsonl` 이 저장소·`open/`·홈 어디에도 없다
(A 티켓 §7 에 찾은 곳을 적었다).

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
