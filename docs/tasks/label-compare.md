# label-compare / 외부 LLM 두 개의 라벨 품질 비교

작업 ID / 제목: `label-compare` / GPT 6.0 Astra와 Claude Opus 5의 dev 블라인드 라벨링 비교
담당 역할 / 담당자: 구현자 / A(본인)
상태: in_progress — 도구·번들은 완성, 외부 모델 실행은 아직 없다

## 목표와 가설

목표는 무라벨 20,000건에 붙일 라벨의 생성기를 고르는 것이다. 점수를 올리는 작업이 아니다.

가설: 정답이 있는 dev 200건에 두 모델이 블라인드로 라벨을 붙이면, `open/dev_labels.csv` 대비
항목별 TP/FP/FN으로 둘의 라벨링 능력을 비교할 수 있다. 특히 현재 F1=0인 11항목에서
양성을 잡아내는지가 판별력 있는 신호다.

이 비교의 점수는 대회 점수가 아니다. 제출 추론은 고정 `google/gemma-4-26B-A4B-it`이며(R1),
외부 모델이 dev에서 몇 점을 내든 리더보드는 그대로다. 외부 모델의 역할은 라벨 생성뿐이다.

## 읽을 문서 / 보호할 규칙 ID

[rules](../rules.md) A2·A3·R6·R7·R9·R11·R15, [data](../data.md) D4·D5, [items](../items.md),
[workflow](../workflow.md) W5, [현재 계획](../../.wiki/plan-active.md).

## 규칙 판단

| 칸 | 값 |
| --- | --- |
| 작업 단계 | 개발 · 라벨 생성 |
| 활용할 A-ID | A2 제공 무라벨·dev의 자가 라벨링 전면 허용. A3 라벨 생성 단계의 외부 LLM 허용 |
| 지킬 R-ID | R6 입력은 제공 자료만, 웹 검색·외부 문서 결합 금지. R7 제출 추론에서 외부 호출 금지. R9 비공개 평가 데이터에는 쓰지 않음. R11 법령은 배포 스냅샷 고정. R15 코드·프롬프트·모델 버전·생성 라벨 보존 |
| Q-ID | Q1 외부 LLM에 판정 규칙·프롬프트·알고리즘 자체를 생성시키는 용도는 확인 전 보류. 이 작업은 라벨(+근거 인용)만 출력시키므로 A3의 명시적 허용 범위 안이다 |

R15의 재현 방식: 외부 API·CLI의 재실행 출력이 달라지는 것은 재현 실패가 아니다. 규칙 원문이
*"외부 LLM 라벨은 코드·프롬프트·모델 버전·생성 라벨 제출로 재현을 갈음"*한다고 명시한다.
따라서 `tools/label_bundle.py`, `prompt.md`의 SHA-256, `--model` 이름과 `--cmd` 문자열,
원응답, 생성 라벨 JSONL을 전부 남긴다. 이것이 2차 평가 제출물이다.

## 정답 누출 — 이 작업의 제1 위험

CLI 에이전트를 이 저장소 안에서 돌리면 블라인드가 자동으로 깨진다.

| 파일 | 들어 있는 것 |
| --- | --- |
| `open/dev_labels.csv` | dev 200건 49열 정답 |
| `reports/team-score-audit/cases.jsonl` | 사례별 `"true"`·`"pred"`와 근거 span |
| `reports/runs/*/score/metrics.json` | 항목별 정답 대비 지표 |

에이전트는 악의 없이도 문맥을 찾으려고 저장소를 뒤진다. 그래서 `tools/label_bundle.py export`는
저장소 안 경로를 거부한다. 번들에는 공고 본문·항목표·제공 법령 스냅샷만 들어가고 정답은 없다.
실행 시 CLI의 작업 폴더는 번들이며, 저장소 밖에 두어 `..` 탐색으로도 정답에 닿지 않게 한다.

## 전량 200건을 돌리지 않는 이유 — 실측

첫 실제 라벨링(`PPS-DEV-01`, Opus 5)이 303초 걸렸다. 200건×2모델이면 33.7시간이다.

dev 200건 중 양성이 하나라도 있는 공고는 88건뿐이고 112건은 24항목 전부 0이다. Macro F1은
양성 클래스 지표라 그 112건은 오탐 정보만 준다. 그래서 `export --cover N`이 항목마다 양성 N건을
덮는 공고만 고른다. 실측 선택 결과:

| 선택 | 공고 수 | 1모델 | 2모델 |
| --- | ---: | ---: | ---: |
| 항목당 양성 ≥1 | 11건 | 0.9h | 1.9h |
| 항목당 양성 ≥3 + 무양성 15건 | 50건 | 4.2h | 8.4h |
| 전량 | 200건 | 16.8h | 33.7h |

무양성 15건은 오탐 측정의 편향을 줄이려고 넣는다. 양성 있는 공고만 쓰면 "전부 1"이라고 답하는
라벨러가 잘해 보인다. 선택은 탐욕이며 최소성은 보장하지 않고, 동점을 ID 사전순으로 깨서
같은 입력이 같은 목록을 낸다(R15).

이 부분집합의 F1은 `654c556`의 dev 0.2208과 같은 축이 아니다. 양성이 과대표집된 공고 집합이라
절대값이 부풀어 있다. 두 모델이 같은 50건을 보므로 둘 사이의 비교만 유효하다.

## 입력

- `open/dev.jsonl` 200건 (SHA-256 `5507f5ab0ba53b708f87211ed050dbe531b48a626ace6084c3ccaefb53147534`)
  중 `--cover`가 고른 50건. 정답 CSV는 선택에만 쓰고 번들에 넣지 않는다
- `open/data/항목표.json` (SHA-256 `368cb41f376d8ad7edbbdf181542e6e959de356f7f70d86e72943325ecad61d9`)
- `open/data/법령패키지/` 파일 25개 — 번들로 복사한다(R11 스냅샷 고정)
- 채점 정답 `open/dev_labels.csv` — 라벨 생성이 끝난 뒤에만 쓴다

## 출력

- `reports/label-compare/<model>.jsonl` — 공고별 24항목 라벨. 셀은 `위반여부`·`근거문구`·`정보부족`과
  프로그램이 계산한 `인용_원문일치`·`인용_길이초과`.
- `reports/label-compare/<model>.jsonl.manifest.json` — 모델 이름·명령·프롬프트 hash·실패 목록·시간.
- `reports/label-compare/<model>.csv` — 49열 예측 CSV. e열은 전부 빈칸이다. 근거는 점수에서
  제외되고(D5) 인용 원문은 JSONL이 갖는다.
- `reports/label-compare/score-<model>/` — `tools/score.py`의 채점 결과.
- 번들과 원응답은 저장소 밖에 남는다. 2차 평가에 낼 때 별도로 모은다.

실패 처리: 명령이 0이 아닌 코드로 끝나거나 응답이 24항목 스키마를 어기면 그 공고만 실패로 적고
다음으로 넘어간다. 실패는 manifest의 `failures`에 ID와 이유로 남는다. 같은 명령을 다시 돌리면
이미 끝난 ID는 건너뛰고 실패분만 다시 시도한다.

## 수정 범위

`tools/label_bundle.py`, `tests/test_label_bundle.py`, 이 문서, `docs/tasks.md`의 작업 큐,
`reports/label-compare/`. `script.py`·`open/`·기존 도구는 읽기 전용이다.

## 통과 조건

1. `python -X utf8 -m unittest tests.test_label_bundle` 통과. — 통과함(8건)
2. `export`가 저장소 안 경로를 거부하고, 만든 번들에 정답 파일이 없다. — 통과함
3. 두 모델 모두 선택된 50건 라벨이 실패 없이 모인다. — 부분 달성. Opus 5 33/50(세션 한도),
   Astra 0/50(할당량)
4. `collect`가 낸 CSV가 `tools/score.py`의 49열 계약을 통과한다. — 통과함
5. 두 모델의 항목별 TP/FP/FN 표와 0점 11항목 비교가 나온다. — Opus 5만 나왔다.
   모델 비교는 Astra 실행 후로 남는다

## 실행 절차

### 1. 번들 만들기 (저장소 밖)

```powershell
python -X utf8 tools/label_bundle.py export --bundle "$env:TEMP/label-compare-50" `
  --truth open/dev_labels.csv --cover 3 --negatives 15
```

50건 기준 약 8MB, 공고 1건당 프롬프트+본문 약 28,500자다.

### 2. 두 모델 돌리기

`--cmd`는 프롬프트를 stdin으로 받아 모델 응답을 stdout으로 내는 명령이다. 아래 두 줄은
파일럿 1건으로 실제 확인했다(Opus 5: 종료 코드 0, JSON 한 덩어리, 인용 9개 전부 원문 일치).

```powershell
python -X utf8 tools/label_bundle.py run --bundle "$env:TEMP/label-compare-50" `
  --model opus5 --out reports/label-compare/opus5-cover3.jsonl `
  --cmd "claude -p --model claude-opus-5 --allowedTools Read,Glob,Grep --disallowedTools WebSearch,WebFetch"

python -X utf8 tools/label_bundle.py run --bundle "$env:TEMP/label-compare-50" `
  --model astra --out reports/label-compare/astra-cover3.jsonl `
  --cmd "del reply.json 2>nul & codex exec -m gpt-6-astra -s read-only --skip-git-repo-check --ephemeral -o reply.json >nul && type reply.json"
```

`codex exec`는 진행 로그를 stdout에 섞으므로 `-o`로 최종 메시지만 받아 `type`으로 낸다. 앞의 `del`이
없으면 codex가 중간에 죽었을 때 직전 공고의 답을 이번 공고 라벨로 조용히 쓴다. 자식 셸은 cmd.exe다.
웹 검색은 claude는 `--disallowedTools`로 막고, codex는 `--search`를 주지 않으면 기본 off다(설정에도 없음).
두 모델에 같은 `prompt.md`가 가는 것은 도구가 hash로 검사한다.

끊기면 같은 명령을 다시 친다. 끝난 ID는 건너뛴다. 진행은 stderr에 한 줄씩 나온다.

### 3. 채점

`tools/score.py`는 정답과 예측의 ID 집합이 정확히 같아야 채점한다. 그 검사는 부분 제출을 막는
제출 계약이라 그대로 두고, `--truth-out`이 라벨 있는 ID만 남긴 정답 부분집합을 만든다.

```powershell
python -X utf8 tools/label_bundle.py collect --labels reports/label-compare/opus5-cover3.jsonl `
  --out reports/label-compare/opus5-cover3.csv `
  --truth open/dev_labels.csv --truth-out reports/label-compare/truth-cover3.csv

python -X utf8 tools/score.py --truth reports/label-compare/truth-cover3.csv `
  --pred reports/label-compare/opus5-cover3.csv --output-dir reports/label-compare/score-opus5
```

astra도 같게 한다. 두 예측 CSV가 나오면 `tools/compare_runs.py`로 항목별 차이를 본다.

## 판단 기준과 중단선

- Macro F1 한 숫자로 고르지 않는다. 항목당 양성이 5~8건이라 1건이 그 항목 F1을 약 0.08,
  Macro F1을 약 0.003 움직인다. 우선 볼 것은 F1=0인 11항목(v4·v7·v8·v10·v11·v12·v14·v15·v16·v18·v20)에서
  실제로 양성을 잡았는지다.
- 두 모델의 차이가 항목당 1~2건 수준이면 결론을 내지 않는다. 그 규모는 이 표본에서 잡음이다.
- `인용_원문일치=false` 비율은 근거 품질 지표다. 라벨을 사례집으로 쓸 때 이 비율이 높은 모델의
  인용은 사람 검수 없이 쓰지 않는다.
- `정보부족=true`는 비위반이 아니다. 비교표에 따로 세고 0과 섞지 않는다.
- dev는 이미 반복 분석한 개발셋이다. 이 점수를 독립 검증으로 보고하지 않는다(A1).

## 선행 작업 / 현재 기준선

선행 없음. 현재 기준선은 고정 Gemma 파이프라인의 dev Macro F1 0.2207877113(`654c556`),
서버 0.2197036943이다. 외부 모델의 dev 점수는 이 수치와 같은 축이 아니다 — 모델이 다르다.

## 후속 작업

1. `label-mine`: 이긴 모델로 `open/train_unlabeled.jsonl`에서 0점 11항목 후보를 뽑아 라벨링한다.
   무작위 전수가 아니라 BM25·키워드·meta로 후보를 먼저 거른다. dev 기준 항목당 양성률이 2.5~4%라
   무작위 표본은 예산 대부분을 음성 확인에 쓴다. 전수 20,000건은 CLI 처리량으로도 불가능하다.
2. `label-casebook`: 검수한 무라벨 사례를 프롬프트 사례집으로 쓰고 **측정은 dev에서 한다.
   사례를 dev에서 뽑으면 채점표를 프롬프트에 넣고 그 채점표로 채점하는 순환이 된다(A1).
   공급원과 측정 도구의 분리가 무라벨 라벨링의 진짜 이유다.

이 두 작업은 임계 경로가 아니다. 점수를 실제로 움직이는 것은 v16 별도 스키마의 정밀도(FP 139)와
v24·v17·v21의 오탐 117개이며, 둘 다 라벨이 아니라 프롬프트·스키마·후처리 문제다.

## 결과

- 변경: `tools/label_bundle.py`(export/run/collect), `tests/test_label_bundle.py`, 이 작업서.
  `script.py`의 `iter_records`·`build_context`·`format_meta`·`item_table`·`extract_json`·
  `record_path`·`file_sha256`을 그대로 가져다 쓰고 사본을 만들지 않았다. 채점은 `tools/score.py`를 재사용한다.
- 실행한 검증: `tests.test_label_bundle` 8건 통과. dev 200건 실제 `export` 성공(13MB, 정답 파일 0건,
  법령 25개). stub 명령으로 `run`→`collect`→`score.load_csv` 경로 통과.
  전체 스위트 73건 중 실패 1건은 `tests/test_setup_agents.py`이며 `--wiki` 인자 없이는 항상 실패하는
  기존 환경 의존이다. 이 변경과 무관하다.
- **Opus 5 파일럿 1건 실측(`PPS-DEV-01`, 303초, 종료 코드 0). 24항목 스키마 통과, 인용 9개가
  전부 원문 부분문자열, `정보부족` 전부 false. 정답 대조로 TP=1(v1)·FN=0·FP=2(v4·v24).
  이 공고의 정답 양성은 1건이다. 1건은 통계가 아니다 — 확인한 것은 기계가 돈다는 것뿐이다.
  이 라벨은 `reports/label-compare/opus5.jsonl`에 있고, 50건 부분집합에는 뽑히지 않아 채점에 안 쓴다.
- Opus 5 50건 실행 실측(2026-09-18): 33건 완료, 17건은 CLI 세션 한도로 막혔다
  (`You've hit your session limit`). 건당 평균 179초, 33건에 100.2분. 한도 리셋 후 같은 명령을
  다시 치면 이어서 한다. 채점은 [score-opus5-33](../../reports/label-compare/score-opus5-33/),
  Macro F1 0.6205. 이 수치를 `654c556`의 dev 0.2208과 비교하지 않는다 — 양성이
  과대표집된 33건이고 모델도 다르다.

  | 묶음 | TP | FN | FP |
  | --- | ---: | ---: | ---: |
  | Gemma가 6회 내내 TP=0이던 11항목 | 21 | 14 | 4 |
  | 나머지 13항목 | 31 | 7 | 22 |

  - v8 3/3, v14 5/5, v15 3/3 — 전부 맞혔다. Gemma는 6회 실행 내내 이 셋에서 TP=0이다.
  - v12·v10·v11·v18·v4·v7도 부분 회복(F1 0.333~0.857).
  - v16만 0/3으로 실패했다. 처음에는 "Gemma의 3항목 별도 스키마 실험이 v16에서 6/6을
    냈으니 서로 다른 곳에서 막힌다"고 적었으나 그 근거는 철회됐다 — 같은 도구의 두 번째
    회차에서 v16은 1/6이었고, 6/6은 Gemma의 실력이 아니라 느슨하게 물어서 나온 값이다
    (200건 중 145건을 위반이라 했다). 그러므로 지금 말할 수 있는 것은 Opus 5도 v16을
    0/3으로 놓쳤다는 것뿐이고, Gemma가 "다른 곳에서 막힌다"고는 말할 수 없다.
    v16의 재현율·정밀도는 묻는 방식이 가르므로 이 트랙이 아니라 C3의 부재탐지 실험이
    다룬다 — [부재탐지 진단](../../reports/team-score-audit/absence-detection.md).
  - v24는 FP 12개로 무너졌다. Gemma도 v24 FP 43이다. 공통 약점이며 라벨러를 바꿔도 안 풀린다.
  - 33건에 v20·v22·v23의 양성이 없어 그 셋은 판단 불가다.

  이 결과가 바꾸는 것: 같은 공고·같은 법령 스냅샷·같은 항목 정의를 받은 다른 모델이
  v8·v14·v15를 전부 맞혔다. 따라서 그 항목들의 TP=0은 항목 난이도가 아니라 제출 파이프라인의
  결함이다. 무라벨 공고는 이 구분을 못 해준다 — 정답이 없으면 Gemma가 틀린 것인지 원래 답이
  0인지 알 수 없다. 후속은 [프롬프트 개선 실험](prompt-from-labels.md)이 소유한다.

  기각된 가설: v14·v15·v17의 근거 인용이 거의 같은 문장이라 "Gemma가 그 조항을 전부 v17로
  몰아넣는다"고 추정했으나 데이터가 반증했다. `colab-1789621345861123113`의 v17 오탐 42건 중
  34건은 v13~v18 어느 것도 양성이 아닌 공고였고, v14 양성 8건 중 v17로 찍힌 것은 1건뿐이다.
  v17 오탐은 오분류가 아니라 조항 문구만 보고 터지는 과잉 발화이며, v14·v15의 미탐은 별개 실패다.
- 미실행·위험: Astra는 한 번도 부르지 않았다 — 할당량. 두 모델 비교는 아직 없다.
  50건 중 17건도 미실행이다.
  웹 검색이 실제로 꺼졌는지는 이 도구가 강제하지 못하고 명령 문자열만 기록한다.
  CLI가 사용자 전역 설정·훅을 읽으므로 세션이 완전히 격리된 것은 아니다 — 정답은 안 닿지만
  이 저장소 밖 문맥이 섞일 수 있다.
- 다음: 50건 × 2모델을 돌린다. 실측 303초/건 기준 모델당 4.2시간이다.
