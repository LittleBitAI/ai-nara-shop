# B10 — v21 는 하한 미만 지분율을 인용할 때만 선다 (채택)

| 칸 | 값 |
| --- | --- |
| 작업서 | [`docs/tasks/b-v21-quote-share.md`](../../../docs/tasks/b-v21-quote-share.md) — 판정 규칙을 라벨링 전에 적었다 |
| 변경 | `script.py` `evidence_refutes()` v21 가지 — 지분율 없는 인용은 v21 을 세우지 못한다. `V21_JOINT_BARRED` 삭제 |
| 후보 | [`experiments/b10_v21_quote_share_candidate.py`](../../../experiments/b10_v21_quote_share_candidate.py) — 운영 이전 전 재생용 |
| dev 재생 `colab-1789902969401579900` | 바뀐 셀 0 · Macro 0.652084267143 그대로 · v21 5/0/1 |
| dev 재생 `colab-1789655036303880754` | 바뀐 셀 1 — `PPS-DEV-143` v21 오탐 제거(구성원 수 조항 인용), 정탐 손실 0 |
| 무라벨 6,000건 | v21 양성 84 (1.4%) 전부 지분율 없는 인용 → 삭제 집합 84 |
| 라벨러 보정 (dev 20) | TP 셀 5/5 (s = 0.566) · 음성 0/14 · 20/20 일치 |
| 삭제 집합 라벨 | 하한 미만 지분율 0/84 · 98.75% Wilson 상한 0.069 < s·F/2 0.257 |
| 결론 | 채택 — 미리 정한 규칙 3 |

모델 뒤 규칙이라 서버 추가 시간 0초. 서버 점수는 아직 없다 — dev 가 움직이지 않는 변경이라 효과는 서버에서만 보인다.

## 왜 v21 인가

v21 은 dev 에서 오탐 0 이지만 무라벨에서는 모델이 1.4% 공고에 v21 을 낸다. 그 84건 인용은 전부
지분율이 없다 — `공동수급이 허용되지 않습니다.`(70건 남짓), `대표사 포함 2개사 이하로 함.`, `단독이행만 허용합니다.` 류다.
운영 규칙은 이런 인용을 불허 정규식으로 내리려 했지만 그 정규식이 84건 중 0건을 잡았다(`허용되지 않` 을 모른다).
표현을 늘리면 54건까지 잡히고 30건이 꼬리로 남아, 표현 목록이 아니라 정의(지분율 인용)로 가른다.

## 라벨러 — 세 번 돌렸고 마지막 설계만 판정에 썼다

| 판본 | 모델 | TP 셀 | 음성 1 | 호출당 토큰(캐시 기록 · 출력) | 쓰임 |
| --- | --- | --- | --- | --- | --- |
| v21 항목 판정 + 조문 발췌 | Opus 5.5 | 5/5 | 0/14 | 18k · 225 | 무라벨 1/84 에서 할당량 소진. 기록만 |
| v21 항목 판정 + 조문 발췌 | Sonnet 5 | 3/5 | 0/14 | 18k · 266 | 규칙 1 반려 조건 |
| 사실 추출, 판정은 코드 | Sonnet 5 | 5/5 | 0/14 | 17k · 115 | 판정에 씀 |

이전 24항목·법령 패키지 라벨러는 공고당 캐시 기록 약 104k · 캐시 읽기 약 421k · 출력 약 6.9k, 평균 8.9턴이었다
(`label-dev200` 전사본 181건). 도구를 끄고 한 항목만 물으니 1턴 · 약 17k 로 줄었다.

Sonnet 이 항목 판정에서 놓친 둘(`049` 지방 4%, `058` 국가 5%)은 모델 등급이 아니라 프롬프트 탓으로 봤다(사용자 판단).
발췌에 든 20% 가감 단서(지방 4~6%)를 대회 정의는 쓰지 않는데(dev 는 지방 2%·3%·4% 를 모두 1), 판정을 라벨러에게
맡기면 그 단서를 읽는다. 그래서 라벨러는 공고의 사실(공동계약 허용·방식·구성원별 최소지분율·인용)만 뽑고, 위반은
운영과 같은 하한표(`v21_minimum_share()`)로 코드가 정한다([`b10_v21_facts_verdict.py`](../../../experiments/b10_v21_facts_verdict.py)).
같은 Sonnet 5 가 이 설계에서 dev 20건을 전부 맞혔다.

## 삭제 집합 84건의 사실

| 공동계약 | 방식 | 최소지분율 | 건수 |
| --- | --- | --- | ---: |
| 불허 | — | 없음 | 70 |
| 허용 | 분담이행 | 없음 | 5 |
| 허용 | 명시 없음 | 없음 | 5 |
| 허용 | 공동이행 | 없음 | 2 |
| 허용 | 혼합 | 5% (지방 — 하한 이상) | 1 |
| 허용 | 분담이행 | 29 (지역업체 비율 오독, 분담이라 미적용) | 1 |

정보부족 0건. 하한 미만 지분율 0건 — k = 0.

## 증명하지 않는 것

- 서버 점수. 비공개 평가의 v21 분포는 모른다. 무라벨 비율이면 1,853건 중 약 26건의 v21 양성이 내려간다.
- 라벨러의 사실 추출 정확도는 dev 20건과 삭제 집합의 꼴로만 봤다. 사람 검토는 없다.
- 무라벨 CSV 는 회차 코드 `14f03d1` 의 것이다. 그 뒤 v21 경로는 이 변경 전까지 바뀌지 않았다.

## 파일

| 경로 | 내용 |
| --- | --- |
| `question-v21-facts.md` | 사실 추출 프롬프트 (판정에 쓴 것) |
| `law-excerpt-v21.txt` | 항목 판정 판본의 조문 발췌 — 스냅샷에서 그대로 옮김 |
| `deletion-set-ids.txt` | 삭제 집합 84건, 표본 순서(`unlabeled-d/ids.txt`) |
| `b10-facts-calib.jsonl` · `b10-facts-unlabeled.jsonl` | 사실 추출 라벨 · usage 포함 |
| `b10-calib-labels.jsonl` · `b10-calib-sonnet.jsonl` | 항목 판정 판본의 dev 보정 (Opus 5.5 · Sonnet 5) |
| `*.manifest.json` | 명령·프롬프트 SHA-256·번들 공고 해시 |

## 재현

```powershell
python -X utf8 tools/label_bundle.py export --bundle <저장소 밖 새 경로> --ids <dev 20건> `
  --question reports/team-b/b10-v21-quote-share/question-v21-facts.md `
  --keys joint_contract,method,min_share_percent,quote,정보부족
python -X utf8 tools/label_bundle.py run --bundle <번들> --model sonnet5-v21-facts --out <facts.jsonl> `
  --cmd 'claude -p --model claude-sonnet-5 --effort medium --tools "" --strict-mcp-config --system-prompt "…" --disable-slash-commands --no-session-persistence --output-format json'
python -X utf8 experiments/b10_v21_facts_verdict.py gate `
  --facts reports/team-b/b10-v21-quote-share/b10-facts-calib.jsonl `
  --unlabeled-facts reports/team-b/b10-v21-quote-share/b10-facts-unlabeled.jsonl
```
