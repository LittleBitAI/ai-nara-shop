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
| 회차용 커밋 | `run/c-fewshot-v18` — **main `9356dc6`** 위에 `script.py` 한 곳만 바꿨다 |
| 바뀐 것 | `build_system_prompt()` 이 `items is None`(=`baseline`)일 때만 v18 예시 한 쌍을 붙인다 |
| 대상 | **회차 1 — off-dev 600**(진단 200 + 봉인 400) · **회차 2 — dev 200**(기준 4, §2-1) |
| ID 목록 | **`reports/labels-600/offdev-600-ids.txt`** — D 가 #163 으로 넣은 정본 |
| 예상 | A100 한 장에 **35~40분** (`a-offdev-0927.md` 의 같은 회차 추정) |
| 운영 `main` | **안 바꾼다.** 이 브랜치는 회차용이다 |

### 노트북 — **이미 있다. 한 줄만 바꾼다**

D 가 PR #163 으로 **`notebooks/colab-offdev-600.ipynb`** 를 넣었다. `IDS_FILE` 과
`N_NOTICES` 가 이미 박혀 있으므로 **손댈 곳은 `REPO_REF` 하나**다.

| | 노트북에 이미 박힌 값 | 바꿀 것 |
| --- | --- | --- |
| `IDS_FILE` | `REPO / "reports/labels-600/offdev-600-ids.txt"` | 그대로 |
| `N_NOTICES` | `600` | 그대로 |
| `REPO_REF` | `deb6831…` (D 의 기준선 회차용) | **`1f7a65cfdab898dad7939722c81044d1b594c8fb`** |

**약칭 SHA 를 쓰지 않는다** — 노트북이 명시적으로 거부한다. 브랜치 이름도 쓰지 않는다.

> **ID 목록을 D 의 정본으로 바꿨다(2026-09-27).** 처음엔 같은 600건을
> `reports/team-c/c-fewshot/offdev-600.ids.txt` 로 따로 만들었는데, #163 이
> `reports/labels-600/offdev-600-ids.txt` 를 정본으로 넣었다. **집합은 같고 순서만
> 다르다**(sha256 은 그래서 다르다). 두 벌을 두면 어느 것이 정본인지 흐려지므로
> **내 사본을 지웠다.** D 의 매니페스트가 `code_commit`·`input_sha256` 까지 들고 있어 더 낫다.

### 기준선 — 같은 코드로 짝을 맞춘다

> **정정(2026-09-27, 리뷰 4라운드 P1).** 처음엔 "D 의 600건 GPU CSV 를 그대로 짝으로 쓴다"고
> 적었다. **틀렸다.** D 의 산출(`offdev-600-results-1790471557297701344`)은 `deb6831` 로 돌았고
> 그것은 PR #166 이전이다. 그 뒤 #166 이 수의계약의 후처리와 호출을 바꿨고 #163 이 v3=`0.95` 를
> 넣었다. 그 CSV 와 후보 CSV 의 차이에는 예시 말고도 그 둘이 섞인다.

| | 코드 | 무엇 |
| --- | --- | --- |
| **후보** | `1f7a65c` = `9356dc6` + 예시 | 이 회차(GPU) |
| **기준선** | **`9356dc6`** — 후보의 부모 | D 의 저장된 600 원응답을 **이 코드로 재생**한 CSV. 모델을 안 부른다 |

두 코드의 `script.py` 차이는 예시(`V18_EXAMPLES` 와 그것을 붙이는 줄)뿐이다 — 아래로 확인한다.

```bash
git diff 9356dc6 1f7a65cfdab898dad7939722c81044d1b594c8fb -- script.py     # V18_EXAMPLES 와 build_system_prompt 만 나와야 한다
```

기준선 재생 명령. 원응답에는 #166 이전의 수의계약 `sme`·`company_size` 호출도 들어 있지만
재생기가 `needs_extra_call()` 로 그 응답을 건너뛴다(`tools/replay_run.py`).

D 의 아카이브는 한 회차가 아니라 **두 샤드**다. 노트북(`notebooks/colab-offdev-600.ipynb`)이
`SHARD_SIZE = 500` 으로 `offdev-600-ids.txt` 순서를 잘라 `u00`(앞 500건)·`u01`(뒤 100건)을 각각
`script.py` 한 번으로 돌린다. `replay_run.py` 는 한 회차의 `run_report.json` 건수와 입력 건수가
같아야 돌므로 샤드마다 따로 재생한다. 합칠 필요는 없다 — `score_offdev.py --pred` 가 CSV
여러 개를 받아 합치고, 중복 ID 와 예측이 빠진 라벨 공고를 거부한다.

D 의 ZIP(`offdev-600-results-<시각>.zip`)은 `register_run.py` 로 등록하지 않는다 — 그 도구는
`colab-results-<숫자>.zip` 과 `submit.zip`(또는 기록된 제출 해시)만 받는다. #163 처럼 풀어서 쓴다.
노트북은 샤드를 Drive 의 `<샤드>/output` 에 복사하고 ZIP 에는 `drive/<샤드>/output/...` 로 넣는다.

```bash
# <D>: D 의 ZIP 을 푼 폴더. 샤드 회차 폴더는 <D>/drive/u00/output, <D>/drive/u01/output 이다
mkdir -p artifacts/offdev-600-<시각> && unzip -q <D 의 ZIP> -d artifacts/offdev-600-<시각>
sha256sum <D 의 ZIP>                                    # 기록에 남긴다
grep -h '"commit"' artifacts/offdev-600-<시각>/drive/u0*/DONE.json   # 두 샤드 다 deb6831… 이어야 한다
D=artifacts/offdev-600-<시각>

git show 9356dc6:script.py > <tmp>/base-9356dc6.py
for s in u00 u01; do
  # 그 샤드가 실제로 돈 공고를 그 샤드 CSV 의 순서대로 뽑아 입력을 만든다
  py -X utf8 -c "import csv,json,sys; ids=[r['id'] for r in csv.DictReader(open(sys.argv[1],encoding='utf-8'))]; want=set(ids); rows={}; [rows.__setitem__(json.loads(l)['id'], l) for l in open('open/train_unlabeled.jsonl',encoding='utf-8') if json.loads(l)['id'] in want]; open(sys.argv[2],'w',encoding='utf-8',newline='\n').write(''.join(rows[i] for i in ids))" \
    $D/drive/$s/output/submission.csv <tmp>/$s.jsonl
  py -X utf8 tools/replay_run.py --case $D/drive/$s/output --input <tmp>/$s.jsonl \
    --script <tmp>/base-9356dc6.py --output-dir <tmp>/offdev-base-$s
done
```

`$D/drive/$s/output` 이 그 샤드의 `run_report.json`·`diagnostics.jsonl`·`submission.csv` 가 있는
회차 폴더다. 루프는 저장된 무라벨 샤드(`reports/label-compare/unlabeled-d/run-1790141381430477242/u00/output`,
같은 `<샤드>/output` 모양)로 시험했다 — 입력 500건, 재생 500건, 건수 검사 통과. 샤드 CSV 의 ID 로
입력을 뽑으므로 노트북의 실패 집합(`failed.json`)이 빠진 샤드도 그대로 돈다. 빠진 공고는
`score_offdev.py` 가 예측 없음으로 거부해 드러난다.

**아직 안 돌렸다.** D 의 복원 아카이브가 이 워크트리에 없다. D 의 보고서
(`reports/offdev-600-threshold-20260927.md`)가 적은 현재 코드 Macro 0.499681 → 0.508940 은
`62c76bc` 기준이고 **그 커밋은 #166 이전**이라 이 기준선 값으로 옮겨 쓰지 않는다.

**남는 차이 하나.** 기준선은 옛 GPU 응답, 후보는 새 GPU 응답이라 둘의 차에는 같은 코드의
회차 간 흔들림(#152)도 섞인다. 그것까지 빼려면 `9356dc6` 로 GPU 기준선 회차를 한 번 더
돈다 — 시간이 되면 그쪽이 더 깨끗하다.

## 2. 합격 기준 — 회차 전에 정한다

9/27 채택 규칙(`plan-0926-0929.md` "Adoption rule from 9/27")을 그대로 쓴다.
아래 넷이 다 서야 채택이고, 하나라도 무너지면 **보류 없이 기각**이다.

| | 기준 | 무엇으로 |
| --- | --- | --- |
| **1** | off-dev 라벨 항목의 Macro 가 **오른다** | `reports/offdev-0927/score_offdev.py` · 라벨 600 |
| **2** | **split-half**: 한쪽 절반에서 쓰고 다른 쪽에서 채점, 서로 바꿔도 양쪽에서 이긴다 | 같은 도구 |
| **3** | 신뢰 항목이 순 `(TP − FP)` **1셀 넘게 안 잃는다** | 항목별 표 |
| **4** | dev 가 Macro **0.01 넘게 안 내린다** | **후보로 돌린 dev 회차** — 재생 아님(§2-1) |
| **5** | 서버 총시간 **≤ 6,800초** | 두 샤드 `run_report.json` 의 `추론_s` **합** × 1853 ÷ 600 환산 |

**이 후보만 따로 본다.** 예시는 v18 을 겨냥했지만 24항목 호출을 바꾸므로 **다른 항목이
움직일 수 있다** — 기준 3 이 그것을 잡는다.

### 2-1. 기준 4 는 재생으로 못 채운다 — dev 회차도 돌려야 한다

**저장된 원응답 위의 dev 재생은 이 후보를 못 잰다.** 그 원응답은 **예시가 없는
프롬프트**로 받은 것이라, 재생은 예시를 넣기 **전** 모델 출력에 후처리만 다시 얹는다.
프롬프트가 바뀌었는데 모델 출력이 그대로면 잰 것이 후보가 아니다. `replay_run.py` 도
스스로 그렇게 적는다 — "프롬프트·스키마를 바꾸는 후보는 저장된 응답이 달라지므로
Colab 회차가 필요하다".

**그러므로 회차가 둘이다.**

| | 무엇 | 왜 |
| --- | --- | --- |
| 회차 1 | **off-dev 600** (진단 200 + 봉인 400) | 기준 1·2·3·5 — 채택 판정 |
| 회차 2 | **dev 200** | **기준 4** — 후보 프롬프트로 실제로 돌린 dev |

회차 2 의 짝은 **같은 dev 200 을 지금 `main` 으로 돌린 회차**다. 가장 가까운 것이
`colab-1790445336782946136`(`772ca12`, dev 200 × 6통과)인데 **그것은 `main` 이 아니다**
— 그 뒤로 #156·#166 이 들어갔다. 짝을 정확히 맞추려면 둘 중 하나다.

1. **`9356dc6`**(후보의 부모)으로 dev 200 을 한 번 돌려 짝을 만든다(추가 회차 하나)
2. D 의 통합 ZIP 회차가 dev 를 포함하고 **코드가 `9356dc6` 이면** 그것을 짝으로 쓴다. 코드가 다르면 짝이 아니다

**어느 쪽이든 기준 4 는 "재생했더니 안 내려갔다"로 통과 처리하지 않는다.**
회차가 없으면 기준 4 는 **미측정**이고, 미측정이면 채택 판단을 미룬다.

**재생을 아예 안 쓰는 것은 아니다.** 후보 `script.py` 를 옛 원응답 위에 얹어 돌리는 것은
**후처리·게이트가 깨졌는지 보는 안전 점검**으로 값이 있다(§4 의 주의). 다만 그것은
기준 4 가 아니다.

### 이 후보에만 붙는 관측 (판정 아님, 기록용)

| | 물음 |
| --- | --- |
| (a) | v18 의 FN 10건 중 **닿는 5건**(`trace.py --flip`)이 실제로 뒤집히나. 절단 여부와 상관없다 |
| (b) | **수의계약 5건**(`014858`·`010194`·`001840`·`000076`·`002698`)은 0 그대로인가 — `NO_BID_ZERO_ITEMS` 가 내리므로 0 이어야 맞다. 1 이 나오면 코드가 바뀐 것이다 |
| (c) | 프롬프트가 커져 **문서가 더 잘렸나** — `[Truncated documents…]` 붙은 건수 전후 |
| (d) | **v18 FP 가 늘었나** — 예시가 모델을 1 쪽으로 밀 수 있다 |

(c) 는 중요하다. 예시 403토큰이 `baseline` 여유(중앙 4,916) 안이라 **안 잘려야 한다**.
잘렸으면 예산 계산이 틀린 것이므로 그 사실부터 적는다.

**(d) 가 이 후보의 가장 큰 위험이다.** 파이프라인 일곱 지점 추적(`TARGET.md` §3)이
보인 것 — 지금 **v18 FP 7건 중 6건은 `verify_company_size` 가 올린 것**이고 모델 오탐은
1건뿐이다. 즉 **예시로 모델을 고쳐도 그 6건은 안 줄고**, 예시가 모델을 1 쪽으로 밀면
**새 FP 만 는다.** 기준 1(Macro 상승)과 기준 3(신뢰 항목 순 `TP−FP` 1셀 이내)이 그것을
잡지만, 회차 뒤에 **FP 증감을 방향별로 따로 적는다.**

### 기대 상한 — 다시 쟀다 (2026-09-27)

처음엔 "닿는 FN 7건" 으로 적었다. **틀렸다.** FN 마다 baseline 의 그 항목만 1 로 놓고
나머지 단계를 끝까지 돌려 **직접 시험하니 5건**이다(`TARGET.md` §2, `trace.py --flip`).

나머지 5건(`014858`·`010194`·`001840`·`000076`·`002698`)은 전부 **수의계약**이고
`NO_BID_ZERO_ITEMS` 에 v18 이 있어 **모델이 뭐라 하든 `postprocess` 가 0 으로 내린다.**
예시로 못 고친다.

| | 지금 | **상한**(닿는 FN **5건**이 다 뒤집힐 때) |
| --- | --- | --- |
| v18 (진단 200) | TP 28 · FP 7 · FN 10 · F1 **0.7671** | TP 33 · FP 7 · FN 5 · F1 **0.8462** |

**이 수를 못 넘으면 예시가 덜 들은 것이고, 넘으면 다른 항목이 움직인 것이다** — 어느
쪽이든 기준 3 으로 확인한다.

**라벨과 규칙이 부딪히는 5건은 사실로 남긴다.** 라벨이 1 인데 파이프라인이 수의계약
이라는 이유로 0 으로 내린다. few-shot 의 문제가 아니고 `NO_BID_ZERO_ITEMS` 를 볼 자리다
— A 에게 넘긴다.

## 3. 시간 — 미리 잰 값

| | |
| --- | --- |
| 예시 크기 | **692자** |
| 보수적 토큰 | **403** (회차 실측 1.716 자/토큰) · 한글·영문을 나눠 세면 약 229 |
| `baseline` 호출 | 600건 × 1회 |
| 서버 환산 증가 | **약 +114초 — 계획용 추정** (`BUDGET.md` §2 의 표, 400토큰 행) |
| 여유 | **372초** (목표 6,800 − `61c495c` 실측 6,428). PR #166 이 비운 시간을 더하면 더 넉넉 |

**계획용 추정이고 상한이 아니다.** 전체 추론 시간을 전체 프롬프트 토큰으로 나눈 평균이라
긴 프롬프트에 토큰을 더할 때의 한계 prefill 비용이나 출력 길이·배칭 변화를 묶지 못한다.
**기준 5(≤ 6,800초)는 이 회차의 실측 `추론_s` 로만 판정한다.**

## 4. 감사 — 받은 뒤에 할 일

```bash
# 0 — 후보 ZIP 도 같은 노트북의 offdev-600-results-<시각>.zip 이다. register_run.py 는 안 받는다(§1)
mkdir -p artifacts/c-fewshot-<시각> && unzip -q <후보 ZIP> -d artifacts/c-fewshot-<시각>
sha256sum <후보 ZIP>
grep -h '"commit"' artifacts/c-fewshot-<시각>/drive/u0*/DONE.json   # 두 샤드 다 1f7a65c… 이어야 한다
C=artifacts/c-fewshot-<시각>

# 1·3 — off-dev 라벨로 채점. 후보도 u00·u01 두 샤드다. 두 CSV 를 함께 넘긴다
py -X utf8 reports/offdev-0927/score_offdev.py \
  --pred $C/drive/u00/output/submission.csv $C/drive/u01/output/submission.csv \
  --labels reports/labels-600/merged/diag.csv reports/labels-600/merged/sealed.csv
py -X utf8 reports/offdev-0927/score_offdev.py \
  --pred <tmp>/offdev-base-u00/submission.csv <tmp>/offdev-base-u01/submission.csv \
  --labels reports/labels-600/merged/diag.csv reports/labels-600/merged/sealed.csv

# 4 — dev. **회차 2 의 CSV 로 잰다. 재생이 아니다**(§2-1)
py -X utf8 tools/score.py --truth open/dev_labels.csv \
  --pred <dev 회차>/submission.csv --output-dir <tmp>/dev-cand
py -X utf8 tools/score.py --truth open/dev_labels.csv \
  --pred <9356dc6 의 같은 dev 회차>/submission.csv --output-dir <tmp>/dev-base

# 안전 점검(판정 아님) — 후처리·게이트가 깨졌는지만 본다
git show <RUN_COMMIT>:script.py > <tmp>/pin.py
py -X utf8 tools/replay_run.py --case reports/runs/colab-1790445336782946136/var-01 \
  --script <tmp>/pin.py --output-dir <tmp>/safety
```

**주의.** 마지막 재생은 **프롬프트가 바뀐 코드를 옛 원응답 위에 얹는 것**이라 후보를
재는 것이 아니다 — 그 원응답에는 예시가 없다. 후처리·게이트가 깨지지 않았는지 보는
**안전 점검**이고, **기준 4 를 이것으로 통과 처리하지 않는다.** 기준 4 는 회차 2 가,
채택 판정은 회차 1(off-dev 600)이 한다.

## 5. 회차용 커밋

```
REPO_REF = "1f7a65cfdab898dad7939722c81044d1b594c8fb"
```

> **바꿨다(2026-09-27, 리뷰 4라운드).** 이전 `d92e0a3` 은 `a0d6aea` 위였다. 기준선과 코드를
> 맞추려고 main `9356dc6` 을 합치고, 옛 1/7 분류를 담은 주석을 고쳤다. 두 판의 코드 차이는
> v3=`0.95` 한 줄(#163)이다.

**이 커밋이 `script.py` 를 담은 커밋이다.** 이 문서의 SHA 는 그 뒤 커밋에 들어가므로
(문서가 자기 커밋 SHA 를 담을 수 없다) 브랜치 tip 과 `REPO_REF` 가 다를 수 있다.
**`script.py` 는 둘 사이에 안 바뀐다** — 확인하려면:

```bash
git diff --stat 1f7a65cfdab898dad7939722c81044d1b594c8fb run/c-fewshot-v18 -- script.py
# 빈 출력이어야 한다
```

`9356dc6` 대비 이 브랜치가 바꾼 것은 `script.py` **한 파일 41줄**과
`reports/team-c/c-fewshot/` 문서뿐이다.

## 6. 이 회차가 답하지 않는 것

- **v10.** 기계적으로는 FN 11건이 다 닿는다(`TARGET.md` §2). 다만 10건이 절단이라 겨냥할지는
  열린 판단이고(`TARGET.md` §4-1) 이 후보는 v18 만 겨냥한다.
- **v13 의 게이트 2건.** 모델이 아니라 게이트가 정탐을 내린 자리다. 단계도 `sme` 다.
- **예시를 늘렸을 때.** 이 회차는 한 쌍이다. 두 쌍은 예산을 다시 재고 따로 돈다.
- **서버 전이.** off-dev 이득이 서버로 얼마나 가는지는 고정 계수가 없다.
