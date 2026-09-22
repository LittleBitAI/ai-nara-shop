# A8 이후 다음 작업 설계

작성일: 2026-09-22. 설계 기준: 당시 checkout `3f8241a`. 상태: 설계, 구현·모델 실행 없음.
추적되지 않는 `artifacts/design/` 작업본에서 옮겨 온 설계 기록이다.
[두 회차 실행 설계](../../../docs/tasks/a8-v20-two-episode-run.md)가 이 문서의 §1·§6을 인용하므로
진입점이 추적되는 경로만 참조하도록 여기로 옮겼다. §3~§5의 구현 설계는 PR #87로 들어갔다.

## 1. 결정 — A8을 짧게 마무리하고, API를 선행 조건으로 두지 않는다

권고는 A8 두 회차를 실행하는 것이다. 최소한의 파일 관측을 먼저 붙이고, 기존 사전 등록 조건으로 한 번만 결론을 낸다. Langfuse 화면 구축이나 API 파일럿을 기다리지 않는다. 높은 성능 기대 때문이 아니라, 준비된 단일 가설을 고정 모델로 판별하는 비용이 제안된 API 사전 실험보다 작기 때문이다. GPU가 준비되지 않았다면 CPU 관측·분석까지 완료하고 회차를 대기시킨다. API로 우회하지 않는다.

가장 유망한 후속 원인은 인용 추출과 SW 적용 대상이다. 다만 지금 새 후보를 만들기 전에 A8의 작은 블록·system 위치·문서 무손실 조건이 이 실패를 줄이는지 확정할 가치는 남아 있다. 기존 wiki 실험은 A8의 기대값을 낮추지만 동일 실험은 아니다. 동시에 위치·길이·본문 보존이 달라서 A8이 이겨도 어느 차이의 기여인지 분리할 수 없다. 새 위치/분량 조합 탐색으로 이어 가지 않는다.

| 판단 근거 | 수치와 한계 | 출처 |
| --- | --- | --- |
| wiki 파일럿 | 두 회차 1,200응답, 참여 인용 검증 0건, v20 TP 모두 1. 독립 공고 1,200건의 표본이 아니며, 법령군만의 호출 수는 800 | `reports/wiki-rag-pilot/results.md` |
| A8의 차이 | system에 586토큰, 추가 축소 0/200. wiki 파일럿은 공통 본문 추가 절단 98건·417,678자 | 위 보고서, `reports/team-c/a8-v20-annex/budget-cpu.json` |
| A8 시간 | 200건 × 2군 × 2회차 = 800 최초 생성 요청. 군별 단계 상한으로 합계 `4×339.178=1,356.712초`, 22.61분. 모델 적재·설치·예산 검사·재생·다운로드는 별도이며 전체 소요 시간 상한이 아니다 | `experiments/a5_scope_pilot.py:execute`, A8 `cpu-checks.json.time_budget` |
| 비교 가능한 기존 단계 시간 | wiki control 207.333~221.108초, raw 275.803~276.111초. 단순 참고 환산 `2×(207.333+275.803)`~`2×(221.108+276.111)` = 16.10~16.57분. A8 실측 예측으로 사용하지 않음 | wiki 결과표 |
| API 사전 실험 | 아래 42건 × 2군 = 84최초 생성, median 10,941토큰 가정만으로 약 57.44분. 재시도·countTokens·실제 pacing으로 더 길어질 수 있음 | 의뢰서 §3, A8 `cpu-checks.json.output_reservation` |

따라서 “A8에 2시간을 더 쓴다”는 비용 전제는 현재 실행 경로로 확인되지 않는다. 전체 Colab 벽시계 시간은 미측정이며 런타임 준비 비용이 매우 크다면 순서는 다시 판단할 수 있다. 이 결정은 GPU 실행 권한·비용 승인을 새로 부여하지 않는다.

기존 사전 등록은 완화하지 않는다. 문서 동일·추가 절단 0, 두 회차 각각 TP 비감소/FP 비증가 및 반복 개선, 대상 밖 반복 손실 보류, 최종 미복구 0, 단계 ≤339.178초를 유지한다. 기존 여섯 채택 게이트에 더해, 기각된 wiki 실험과 같은 잘못된 인용→판정 보류→우연한 baseline 정답을 개선으로 인정하지 않는 해석을 실행 전에 명문화한다. 이것은 TP≥3 같은 도달 불가능한 새 목표를 넣는 것이 아니다.

### 점수 거리와 상한

- 서버 최고에서 0.60까지 `0.60−0.5084137874=0.0915862126`. 24항목 F1 합으로는 2.1980691024가 더 필요하다. dev 전체 GPU 최고에서의 거리 `0.000684140922`와 섞지 않는다. 출처: `docs/runs.md`, `reports/submissions.json`.
- H4 v20 1/4/4에서 FP만 전부 지우면 F1 `2/(2+4)=0.333333`, Macro 증가 0.005556. TP 상한 2에 FP 0까지 가정하면 F1 `4/(4+3)=0.571429`, Macro 증가 0.015476. 둘 다 조건부 산수이며 기대값·서버 예상치가 아니다.
- 세 누락 공고를 그대로 두는 A8은 v20 F1 0.60에도 못 닿는다. v20 한 항목을 만점으로 만들어도 그 dev 기준 Macro 기여는 `(1−0.2)/24=0.033333`이다. A8 하나로 서버 0.60에 도달한다는 주장을 하지 않는다.
- v13 수리 뒤 현 코드의 H4 재생 기준은 0.591008188119, 수리 전 0.593846165415가 아니다. 최고 GPU 0.599315859078은 다른 측정이다. 후보 비교는 같은 코드의 새 control과 한다.

## 2. 작업 계약과 현재 확인 범위

이번 설계의 입력: 의뢰서, `docs/{workflow,README,tasks,rules,items,contracts,design,runs,langfuse}.md`, A8 작업서·CPU 원장·실행 안내, wiki/A4/A5/A7 보고서, 아래 호출 경로와 리뷰 기록.

이번 출력·수정 범위: 이 파일 하나. 소스·작업 큐·활성 위키·기존 보고서·.env는 수정하지 않았다. 기존 untracked 결정 문서 14개를 보존했다. 실제 브랜치는 `feat/a8-v20-annex-injection`이다. 주입된 요약의 `main` 표기와 구분한다.

로컬 `git branch -a --contains`로 코드 `b139807723c22ec570d65635b0d654ba5e6149e2`와 노트북 `a033d5bb1fb74fc5287dd04cb173e0c3b1e168b6`가 로컬 객체로 존재하고 origin/main 추적 이력에 포함됨을 확인했다. 원격 fetch 가능성은 이번에 확인하지 않았다. 삭제 브랜치 이름으로 실행하지 않는다.

아래는 다음 구현 작업의 허용 범위 제안이다. 이 설계 작성 중에는 어느 것도 고치지 않는다.

| 파일 | 구분 | 책임 |
| --- | --- | --- |
| `experiments/a5_collect_facts.py` | 수정 | 실제 호출 메시지와 입력 예산 기록; 기존 호출·복구 동작 보존 |
| `experiments/a5_scope_pilot.py` | 수정 | A8의 실행/군/청크 생명주기, 파일 진단 로그, 결과 감사 연결 |
| `tools/langfuse_tail.py` | 수정 | 새 진단 이벤트를 부모·군·실제 호출로 투영; dev/로컬 송신 검증 |
| `experiments/a8_v20_audit.py` | 신규 | 순수 CPU 인용·판정 경로 감사, 선택적 API 표본 명세 생성 |
| `tests/test_a5_collect_facts.py`, `tests/test_langfuse_tail.py`, `tests/test_a8_v20_annex.py` | 수정 | 관측 비간섭·재시도·계약·새 감사 검사 |
| `notebooks/colab-a8-v20-annex.ipynb` | 수정 | 관측 구현 후의 새 실행 핀과 실패 산출물 보존 |
| `reports/team-c/a8-v20-annex/` | 갱신/신규 | 아래 상태·감사·시간·결과 파일 |
| `docs/langfuse.md`, A8 작업서, `docs/tasks.md`, `.wiki/plan-active.md` | 수정 | 실제 구현 시 바뀐 절차·상태를 동시 갱신 |

`script.py`, 제출 requirements·allowlist, 법령·원자료·과거 회차 바이트, A8 주입 문자열은 변경하지 않는다. `tools/api_run.py`, `tools/langfuse_local.py`, `experiments/wiki_rag_pilot.py`도 이번 필수 구현에서 수정하지 않는다. 실패한 wiki 후보에 관측 기능을 소급해서 모델 재실행하지 않는다.

통과 조건: 새 관측 ON/OFF의 메시지·스키마·호출 순서·생성 인자·반환 원응답·기존 소비 결과가 동일하고, 재시도 메시지를 최초 메시지로 잘못 표시하지 않으며, dev-only 검증 전에는 송신하지 않을 것. 다음 구현자는 아래 계약을 작업서에 옮긴 뒤 시작한다.

## 3. 관측 구멍 — 고칠 정확한 자리

### 3.1 호출 경로에서 확인한 사실

```text
a5_scope_pilot.execute
  → activate_arm(control/a8)
  → a5_collect_facts.collect
      → fit_to_budget(조항호내용 제외 meta, products, 16000자, 15296토큰)
      → run_chunk(items=COMPANY_SIZE_KEYS, phase="company_size")
          → runner.chat
          → 실패하면 runner.retry_chat → runner.chat(변경된 system 메시지)
  → hybrid_replay → replay_run.replay → 현 script.py 소비자 → score/compare_runs
```

1. `collect()`는 완성된 `messages`를 이미 갖고 있으므로 이곳에서 저장해야 한다. 사이드카가 원자료로 다시 조립하면 실제 절단·프롬프트·재시도와 달라질 수 있다.
2. `run_chunk`는 `response_text`만 남긴다. `VLLMRunner.retry_chat`은 system 뒤에 `[Output scope for this call] ...`를 붙이고 출력 예산도 다시 계산한다. 최초 입력의 복사본을 attempt=2의 실제 입력이라고 기록하면 안 된다.
3. 파일럿은 `chunk_started`도 내지 않는다. 지금의 generation 시작 시각은 실제 청크 시간이 아니며 군도 구분하지 못한다.
4. `langfuse_tail.plan()`은 `state.run is None`이면 모든 이벤트를 버린다. 루트 누락의 직접 원인은 `run_started` 부재다. `phase_started`는 현재 코드에서 point event일 뿐 루트를 만들지 않는다. 그 이벤트만 추가해서 해결했다고 검사하면 가짜 초록이다.
5. 과거 로그에는 `time_unix`도 없다. 재수출 시각을 과거 추론 시각으로 꾸미지 않는다. 과거 로그는 읽기 분석만 하고, 새 정확한 시간 관측은 새 회차부터다.

### 3.2 수집기: 기존 위치 인자는 유지하고 선택적 관측을 붙인다

`experiments/a5_collect_facts.py`에서 다음을 구현한다. 타입 표시는 계약이며 별도 클래스 계층은 만들지 않는다.

```python
def collect(records, runner, products, emit, budget=None, plan=None, *,
            observe=False): ...

@contextmanager
def observe_chat(runner, emit, *, ids: list[str], phase: str): ...
```

`observe=False`는 기존 A5/H3/v18/wiki 호출자의 의미·로그 형식·성능 경로를 유지한다. 현재 `budget` 다섯 번째 위치 인자와 `plan=`를 바꾸지 않는다. A8에서만 `observe=True`를 전달한다. 기존 `collect(*args)` 테스트 래퍼는 `**kwargs`도 전달하게 고친다.

`collect()` 변경:

- 기존 `company_size_input`에 observe일 때만 `phase`, `global_index=start+i`, `token_count_kind=runner.TOKEN_COUNT`, `prompt_messages=messages`, `requested_max_chars=planned`, `truncated=(chars<planned)`, `visible_sha256`를 추가한다. 기존 `max_chars`, `prompt_tokens`, `prompt_sha256=collector.digest(messages)`는 유지한다.
- `visible_sha256`는 `script.build_context(rec, chars)`의 UTF-8 SHA256이다. 실제 모델 user 메시지의 식별은 별도로 `prompt_sha256`가 책임진다. 전체 문맥 hash와 순수 문서 동일성 검사를 혼동하지 않으며 A8 `budget_report`의 visible 검사를 그대로 유지한다.
- `run_chunk` 직전에 `chunk_started(phase, chunk_start, count, indices)`를 내고, 바로 그 호출만 `observe_chat(...)`으로 감싼다. 타이머와 기존 반환 payload는 그대로 둔다. 실제 저장 IO도 stage 시간에 들어간다.
- `finally`에서 `chunk_finished`를 낸다. 수집 실패는 기존처럼 raise하며 baseline 없는 실패를 0으로 채우지 않는다.

`observe_chat()`은 `runner.chat` 인스턴스 속성만 잠시 감싼다. 원래 bound method를 보존하고 `finally`에서 원래 인스턴스 속성이 있었는지까지 복원한다. 클래스 함수·`retry_chat`·전역 script 함수는 바꾸지 않는다. 실제 retry 내부의 `self.chat`도 이 래퍼를 지나므로 변경된 메시지와 sampling parameters를 얻는다.

래퍼 시그니처는 `chat(batch, sampling_params=None, items=None)`로 동일하게 둔다. 원본에 같은 객체/인자를 전달하며, 반환 리스트·예외·`last_response_info`를 변경하지 않는다. 유효 스키마를 기록할 때 `sampling_params`가 있으면 그 객체를 읽고, 없으면 원래 `parameters_for_items(items)` 또는 `sp`의 값을 읽는다. 기록 때문에 값이나 원본 schema를 수정하지 않는다.

각 `chat` 진입에 로컬 단조 정수 `call_seq`를 하나 배정한다. 첫 호출은 `ids`와 batch를 순서대로 대응시키고, 뒤의 singleton retry는 변하지 않는 비-system 메시지들의 digest로 원공고를 대응시킨다. 최초 목록 안에서 유일할 때만 id를 확정한다. 중복/미일치는 `id=null`, `identity_status="ambiguous"`로 기록하고 관측 검사에 실패시킨다. 추론을 다른 ID에 붙이거나 데이터 문구로 ID를 추측하지 않는다. A8 최초 batch와 company singleton retry 외의 호출 구조는 지원하지 않고 관측 실패로 분명히 표시한다.

물리적 모델 요청당 이벤트 계약:

| 이벤트 | 추가 키 | 의미 |
| --- | --- | --- |
| `model_call_started` | `call_seq`, `call_index`, `id`, `identity_status`, `prompt_text`(role/content 배열), `prompt_sha256`, `schema_sha256`, `max_tokens`, `items`, `call_kind="initial"/"retry"` | 실제 runner.chat 인자. 배열 한 요소당 1개, 재시도 system 추가문 포함 |
| `model_call_finished` | 동일 call 키, `response_text`, `prompt_tokens`, `output_tokens`, `finish_reason`, `stop_reason`, `model_version`, `response_id`, `transport_status="returned"` | API 전용 필드는 값이 있을 때만 기록. 반환되었다는 뜻이지 JSON 유효 판정이 아님 |
| `model_call_failed` | 동일 call 키, `error_type`, `transport_status="failed"` | 네트워크/모델 예외. 임의 원응답·사용량을 만들지 않음 |

`last_response_info`의 키를 통째로 펼치지 말고 위 allowlist만 복사한다. 예외 문자열에 비밀·경로가 섞일 수 있어 원문을 관측 로그에 무조건 넣지 않는다. 파싱 유효성은 기존 `response` 이벤트가 소유한다. batch 반환 건수 불일치는 알려진 요청들을 `response_count_mismatch`로 종결하고 정상 완료로 세지 않는다. `run_chunk`의 기존 복구는 그대로 실행한다.

`call_seq`는 청크마다 0부터 시작해도 된다. 전체 식별자는 `(run_id, episode, arm, sample, phase, chunk_start, call_seq, call_index)`다. 시간은 모델별 독립 지연이 아니라 동일 batch의 호출 시작·종료 시각임을 기록한다. `response`의 attempt 번호와 실제 호출 수를 같은 것으로 집계하지 않는다.

### 3.3 파일럿: 한 실행 로그, 군별 원응답은 계속 보존

`experiments/a5_scope_pilot.py`에 추가:

```python
def make_emit(run_log, arm_log=None, *, run_id: str, episode: int,
              arm: str | None = None, sample: str | None = None): ...
```

반환 함수는 기존과 같은 `emit(event, **fields)`다. 공통 키는 `event`, `time_unix=time.time()`, `run_id`, `episode`, `arm`, `sample`, `phase`이며 각 행을 UTF-8/LF로 기록·flush한다. caller가 공통 키를 덮어쓰려 하면 오류로 처리한다. `phase`는 호출 경로가 준 값을 사용하며 company 수집은 항상 `company_size`다. arm을 phase 이름에 붙이지 않는다.

A8일 때 `main()`에서 새 `output/diagnostics.jsonl`을 exclusive 생성하고 아래 생명주기를 실행한다. 기존 군별 `control/dev.events.jsonl`, `a8/dev.events.jsonl`도 동일 공고 이벤트를 보존하되 전체 루트 이벤트를 중복으로 넣지 않는다. Langfuse 입력은 통합 파일 한 개다.

```text
run_started → model_loading → model_loaded
  → arm_started(control) → phase_started(company_size)
    → company_size_input… → chunk_started
      → model_call_started… → model_call_finished… → response…
      → 필요하면 retry의 model_call_* → response 또는 retry_failed
    → chunk_finished → arm_finished
  → arm_started(a8) → … → arm_finished
→ run_succeeded 또는 run_failed
```

회차2는 기존대로 a8→control이다. `run_started`는 모델 생성 전에 기록하고 `run_failed`는 budget 검사·모델 적재 실패도 포함한다. `KeyboardInterrupt`도 실패 파일을 남기는 기존 `BaseException/finally` 방식을 유지한다. 갑작스러운 프로세스 종료는 끝 이벤트가 없으므로 `incomplete`다.

run 시작 필수 키: `mode="live"`, `experiment="a8"`, `dataset="dev"`, `dataset_sha256`, `dev_ids`, `source_commit`, `code_sha256`, `contract_sha256`, `expected_model={"id":...,"revision":...}`, `capture_protocol=1`, `settings`(기존 계약의 비밀 없는 설정만). 모델 적재 뒤 `runner.MODE`가 live가 아니면 실제 모델 성공으로 세지 않는다. 테스트 대역은 시작 mode도 `test_double`로 주입하고 종료 시 실제 mode와 대조한다.

arm 시작 키: `arm`, `sample="dev"`, `selected_count=200`, `system_prompt_sha256`, `schema_sha256`, `output_reserved=1024`, `prompt_budget=15296`. 종료 키: `status`, `stage_seconds`, `valid_response_count`, `failed_response_count`. 기존 `record_run()`은 `*.events.jsonl`의 논리 response만 센다. 새 `model_call_finished`까지 합쳐 성공을 두 배로 세지 않는다.

통합 diagnostics writer는 기존 `execute`에 keyword-only `run_emit=None`으로 전달한다. `execute(..., *, run_emit=None)`로 바꾸되 기존 테스트 호출은 유지한다. 신규 로그·감사 소스를 `contract.files`에 넣고 회차2 계약 검증에 포함한다. A8 외 분기는 기능이 꺼진 채 기존 호출 경로를 따른다.

### 3.4 사이드카: 군과 실제 호출을 투영한다

`tools/langfuse_tail.py`의 기존 `plan(event: dict, state: State) -> list`와 `Op` 구조를 재사용한다. `State`에 `arm: str | None`, `capture_protocol: int | None`, `inputs: dict`, `calls: dict`만 추가한다. 별도 tracing framework를 만들지 않는다.

- `run_started`는 실제 루트. metadata에 `run_id`, `episode`, `experiment`, `dataset`, `dataset_sha256`, `capture_protocol` 추가.
- `arm_started`/`arm_finished`는 `arm:{arm}:{sample}` span을 열고 닫는다. `phase_started` point의 부모도 현재 arm으로 연결한다.
- 청크 key에 arm/sample을 포함한다. 이전 arm의 청크를 새 군으로 이어 붙이지 않는다. `chunk_finished`에서 닫고 `run_failed`에서 남은 청크→arm→run 순서로 닫는다.
- `company_size_input`은 `(arm,sample,id)`로 캐시하고 input-budget event를 남긴다. 위 §3.2 입력 키 및 A8 `budget.json`의 군 간 추가 절단 판정을 구분해서 표시한다. `chars<16000`만으로 문서 누락·추가 절단을 단정하지 않는다.
- `model_call_started`는 generation span을 열고 `prompt_text`를 `langfuse.observation.input`으로 보낸다. key는 위 전체 식별자다. finish/failed는 같은 key를 닫고 output/usage/error를 붙인다. metadata에 arm·sample·id·call_kind·prompt/schema hash·max_chars·token_count_kind·`duration_note="shared batch latency"`를 넣는다.
- `capture_protocol=1`이면 기존 `response`는 `parse-result` event로 보낸다. generation을 또 만들지 않는다. 최초 invalid·최종 valid·retry_failed는 모두 남긴다. 최종 조립된 retry 응답을 단일 물리 생성으로 위장하지 않는다.
- 구 로그에서 capture_protocol이 없으면 기존 response→generation 투영을 유지한다. prompt가 없으면 그대로 비우고 `prompt_capture="unavailable"`로 표시한다. 없는 입력을 만들어 넣지 않는다.
- usage가 일부 누락되면 그 필드를 생략한다. 입력/출력을 모두 알 때만 total을 계산한다. 알 수 없는 토큰 수를 0으로 쓰지 않는다.
- 새 로그의 hash 불일치·중복 call 시작·종료 없는 call은 관측 계약 실패다. 사이드카는 수출을 중단하고 원파일은 보존한다. 모델 프로세스·채점에는 영향을 주지 않는다.

### 3.5 dev 원문 송신 경계

원문 로깅과 외부 전송은 별개다. 파일럿은 로컬 JSONL을 쓰고, 회차 뒤 다운로드한 파일을 대회 전용 로컬 Langfuse로 재생하는 것을 기본으로 한다. Colab→공개 터널 실시간 송신은 이 설계에서 요구하지 않는다.

`tools/langfuse_tail.py` 신규 순수 사전 검사:

```python
def validate_dev_export(events_path: Path, dev_path: Path, *, host: str) -> dict: ...
```

`run()`이 provider 생성 전에 호출한다. 호스트는 이번 기능에서 `http://localhost:3002`, `http://127.0.0.1:3002`, `http://[::1]:3002`만 허용하며 userinfo·query·fragment·다른 경로/포트를 거부한다. 로컬 URL의 redirect를 통한 외부 송신도 허용하지 않는다. 요청한 full-prompt 수출은 완성 파일에 한정해 `--follow`, `--from-line != 0`을 거부한다. 기존 metadata-only 경로는 그대로 두되 full prompt 경로에는 이 검사가 필수다.

CLI `--dev-input open/dev.jsonl --include-prompts`를 추가한다. `--include-prompts`가 없으면 input 메시지 본문은 보내지 않는다. 이 플래그는 안전성 근거가 아니며 아래 데이터 대조가 근거다.

검사 계약: run_started의 `dataset="dev"`, 입력 파일 SHA256이 프로젝트에 고정된 공개 dev hash와 일치, dev_ids가 정확히 해당 입력의 고유 ID 집합(또는 표본 manifest의 부분집합), 모든 공고 이벤트의 id가 그 집합에 속함, 원로그 contract hash 일치. unknown/ambiguous ID·다른 데이터 source는 수출 중단. ID 접두사만 검사하면 안 된다. 미래 sample 경로는 기록한 표본 manifest와 원문 레코드 hash까지 대조한다. 실험 실행기는 고정 dev 파일만 읽도록 사전에 강제하므로 임의 입력에 dev 이름을 붙이는 경로를 제공하지 않는다.

R9·R17은 비공개 평가 자료의 튜닝/유출 경계다. 제공 dev를 로컬 관측하는 것이 그 금지와 같은 것은 아니다. 그렇다고 로컬 주소라는 사실만으로 비공개 자료가 허용되는 것도 아니다. 평가 입력·서버 추론 로그에는 이 도구를 연결하지 않는다. Langfuse 비밀키·환경변수 전체·.env·절대 개인 경로는 span에 넣지 않는다. `langfuse_local.py keys/share/reset`은 이번 작업에 필요 없다.

`docs/langfuse.md`의 “debug-responses이면 프롬프트가 들어간다”와 “script.py에 한 줄 추가 요청”은 현재 경로와 어긋나므로, 실제 구현 시 수집기 관측과 새 재시도 계약으로 교체한다. 로컬 서비스 기동·적재·UI 확인은 CPU 테스트 통과와 구분해서 기록한다. Langfuse 장애는 GPU 회차 시작을 막지 않지만 파일 진단 누락은 관측 구현 수정 사유다.

## 4. A8 결과 감사 — 문자열 성공과 판정 성공을 분리한다

새 `experiments/a8_v20_audit.py`는 모델을 부르거나 파일럿 판정을 바꾸지 않는다.

```python
def quote_check(quote: str | None, rec: dict, visible: str) -> dict: ...
def audit_row(rec: dict, facts: dict, *, max_chars: int) -> dict: ...
def audit_episode(episode_dir: Path, *, dev_path: Path, data_dir: Path) -> dict: ...
def main(argv: list[str] | None = None) -> int: ...
```

`quote_check`는 null/空白/원문 정확 일치/기존 공백 복원/불일치를 구분한다. `script.restore_spacing`을 그대로 사용한다. 반환 키는 `state`(`null`, `empty`, `exact`, `spacing_restored`, `invalid`), `effective_quote`, `in_visible`, `in_document`, `matches`다. matches는 동일 공고 문서의 `{doc_id,start,end}` 배열이며 `text[start:end]==effective_quote`, Python 문자 인덱스·end 제외다. NFC 재정규화 등 원문 변경은 하지 않고 `script.iter_records`가 주는 텍스트 기준을 manifest에 명시한다. 문서가 doc_id를 제공하지 않으면 ordinal을 별도 `doc_index`로 기록하며 ID를 꾸며내지 않는다.

`audit_row` 출력 필드:

```json
{
  "id": "실제 공고 ID",
  "max_chars": 16000,
  "visible_sha256": "...",
  "software_business": "yes",
  "software_business_quote_check": {},
  "software_participation_quote_check": {},
  "requirements_complete": "yes",
  "input_complete": true,
  "dropped_doc_counts": {},
  "software_docs_visible": true,
  "v20_write": null,
  "v20_action": "preserve",
  "company_writes": {},
  "company_reason": "기존 반환 reason",
  "semantic_review": "pending"
}
```

`company_writes, company_reason = script.verify_company_size(facts, rec, max_chars)`를 실제 호출한다. `v20_write`는 company_writes에 v20이 없으면 null, 있으면 `위반여부`; action은 `preserve`/`write_0`/`write_1`이다. `company_reason`이 outside_general_scope여도 v20은 따로 쓸 수 있으므로 이것을 v20 차단 이유로 사용하지 않는다. `software_docs_visible`은 공고문 존재 및 공고문/RFP가 visible에 전량 있는지의 관측 보조값이며 새 게이트가 아니다.

`audit_episode`는 먼저 `script.load_sme_reference(data_dir)`로 같은 module의 `_PRODUCTS`를 채우고 nonempty를 단언한다. products를 로컬 변수로 받기만 하고 전역을 비워 두는 테스트 금지. 입력·응답 200 ID의 정확한 일치, 중복 없음, 군·코드·prompt/schema/hash·max_chars 계약을 검사한 뒤 각 군의 기존 `dev.json.payload.rows`를 파싱한다.

산출물은 회차별 `v20-audit.json`이다. 최상위 키: `source_commit`, `contract_sha256`, `execution_mode="cpu_audit"`, `arms`, `paired_changes`, `complete`, `semantic_review_complete`. 각 arm에 `rows`, `counts`를 둔다. counts: `software_yes`, `participation_nonnull`, `participation_exact`, `participation_spacing_restored`, `participation_invalid`, `v20_write_0`, `v20_write_1`, `v20_preserve`. 문자열 검증된 인용 수와 의미상 적용 안내인 인용 수는 다르다. 의미 검토가 끝나기 전 latter는 null이다.

후보에서 v20 또는 위 인용 상태가 바뀐 공고 전부에 대해 사람이 같은 공고 원문과 제공 지침으로 검토한다. 기록은 `reports/team-c/a8-v20-annex/semantic-review.jsonl`, 행 키는 `episode`, `arm`, `id`, `field`, `quote`, `doc_id`, `start`, `end`, `role`(`participation_disclosure`, `exception_disclosure`, `bare_reference`, `unrelated`, `unclear`), `source_ref`, `reviewer`, `reviewed_at`, `reason`이다. 사람이 하지 않은 검토의 reviewer를 채우지 않는다. 운영진 답변이 필요한 새 법 해석을 만들어 자동 통과시키지 않는다.

회차 결과에는 24항목 TP/FP/FN·실제 최종 CSV 변화도 기존 compare_runs로 함께 둔다. `verify_company_size` 반환만으로 baseline 보존 뒤 최종 label을 추정하지 않는다. 오인용에서 preserve로 빠진 변화는 `paired_changes`에 `gain_kind="fallback_only"`로 표시한다. 이 변화만 좋아졌다면 탐색 성공으로 승격하지 않는다. 검증·의미 검토를 통과한 참여 조항으로 write_0가 된 FP 감소, 또는 근거 있는 applicability 변경에 따른 TP 증가가 반복되어야 한다.

법령 문자열의 우연한 공고 포함도 있을 수 있으므로 인용 출처를 “법령과 글자가 같다”만으로 무효화하지 않는다. 실제 공고 내 위치와 의미가 기준이다. v20은 부재항목이므로 e20은 계속 빈칸이다.

## 5. API 파일럿 — 조건부 설계, 이번 선행 작업에서는 실행하지 않는다

### 5.1 규칙과 판정 효력

`docs/rules.md` R6/A3은 라벨 생성에 외부 API를 명시 허용한다. Q1과 `docs/contracts.md` C2는 프롬프트/오답 분석 등의 외부 API 자동화를 확인 전 보류한다. 반면 `tools/api_run.py` 주석은 “로컬 검증이므로 Q1은 자산 채택 때만”이라고 설명한다. 도구 주석으로 상위 계약의 범위를 넓힐 수 없다. 이번처럼 모델 반응을 보고 다음 프롬프트/GPU 우선순위를 정하는 API 관측은 Q1 확인 전 실행 보류한다. 이를 형식적으로 “라벨 생성”이라고 이름만 바꿔 돌리지 않는다.

CPU 표본 선정·기록 계약·대역 검사는 지금 구현 가능하다. 외부 API 실행 분기는 Q1에 대한 운영진 답변과 실행 예산이 기록된 뒤에만 구현·활성화한다. 현재 설계의 필수 경로는 고정 모델 A8이므로 이 확인 때문에 전체 작업을 멈추지 않는다.

API의 통과는 그 API에서 요청·출력 계약이 작동했다는 뜻뿐이다. API 음성 결과로 고정 모델의 A8을 기각하지 않고, API 양성 결과로 GPU 측정/채택을 생략하지 않는다. `reports/api-proxy-check/result.md`의 동일 100건 114셀 차이와 W5가 이 경계를 요구한다.

### 5.2 표본은 41건이 아니라 42건

이번 읽기 전용 계산으로 아래를 확인했다.

- 원천: `reports/runs/wiki-rag-1789985574572142052/pilot/episode-1/control/dev.json`.
- `software_business=yes` 11개 ID: `056,064,068,082,086,101,131,133,134,144,24`(실제 문자열은 PPS-DEV 접두사 포함; 24를 024로 고치지 않음).
- v20 양성 5건 중 위 집합 밖은 `PPS-DEV-132` 하나다. 합집합 12건.
- 나머지 188건에서 비복원 단순 무작위 30건. 합계 42건, 두 군 84최초 생성. 라벨은 표본 선정·사후 채점에만 쓰고 모델 메시지에는 넣지 않는다.

N=30의 근거는 드물지 않은 구조 결함 탐색이다. 나머지 집합에 결함률 10%가 있다고 가정할 때 한 건 이상 관측 확률의 보수적 근사는 `1−0.9^30=95.76%`. 5%라면 `1−0.95^30=78.54%`뿐이다. 무결함 30건은 전량 안전성 보장이 아니고, 목적 표본 12건과 합쳐 모집단 precision을 추정하지 않는다.

CPU 함수는 `a8_v20_audit.py`에 둔다:

```python
def select_sample(dev_ids: list[str], software_yes_ids: set[str],
                  positive_ids: set[str], *, random_n: int = 30,
                  seed: int = 20260922) -> dict: ...
```

`sorted(set(dev_ids) - mandatory)`에서 `random.Random(seed).sample(...,30)`로 뽑고 최종 실행 순서는 원래 dev 순서로 한다. 반환 키: `seed`, `random_n`, `mandatory_ids`, `random_ids`, `selected_ids`, `strata_by_id`; strata 값은 `software_yes`, `label_positive`, `random`의 배열이다. 중복·원천 밖 ID·부족 표본은 raise. 저장할 `api-sample.json`에는 dev/labels/원응답 원천 hash·알고리즘·Python 버전·selected record hash도 넣는다. seed만 기록하지 않는다.

### 5.3 향후 허용된 경우의 실행 계약

선행 권한이 생기면 새 `experiments/a8_api_probe.py` 한 파일에서 기존 `APIRunner`와 collector를 사용한다. `tools/api_run.py` 전체 pipeline CLI를 부르면 baseline/SME까지 호출되므로 사용하지 않는다.

```python
def run_probe(records: list[dict], runner, products: list[dict], *,
              output_dir: Path, sample_manifest: dict) -> dict: ...
def main(argv: list[str] | None = None) -> int: ...
```

main 인자는 `--sample-manifest`, `--output-dir`, `--q1-evidence`, `--max-seconds`(기본 7200), `--max-input-tokens`(기본 1200000). Q1 evidence는 답변 원문·날짜·적용 범위를 가리키는 로컬 승인 기록의 경로/hash이고, 단순 `approved=true` 스위치가 아니다. 이 제한은 API 총비용의 통화 상한을 대신하지 않는다. 단가/계정 요금이 확인되지 않으면 금액은 미측정으로 남긴다.

명시적 API 실행에서 키가 없으면 오류로 종료하며 mock 자동 전환하지 않는다. `APIRunner.SCRIPT`는 collector가 참조하는 동일 `script` 모듈, `WORKERS=1`, `max_tokens=1024`, `MODE="api"`, `TOKEN_COUNT="api_count"`를 유지한다. 두 군은 한 runner/한 TokenBucket을 공유한다. 군마다 새 bucket으로 쿼터를 재설정하지 않는다. 키는 환경에서만 받으며 로그에 넣지 않는다.

군은 control/a8 두 개뿐이고 A8 블록·스키마·소비자는 기존과 같다. API 토큰화로 A8 `budget_report`에 해당하는 두 군 입력 대조를 다시 해야 한다. 고정 토크나이저의 586을 API 토큰 차이로 복사하지 않는다. API에서 추가 절단되면 표본 대조를 멈추고 구조 미완료로 보고한다. 군 공통 본문을 더 줄여 통과시키지 않는다.

84생성 이전에 `countTokens` 요청이 별도로 발생한다. generation 요청 수/성공 반환/HTTP 재시도/countTokens 요청을 분리 기록한다. quota 시도 예산은 `_post`가 송신하기 직전의 동일 bucket에 모든 HTTP generation 재시도도 계상해야 한다. 기존 `_one()` 진입에서 한 번만 차감하는 구현을 실제 HTTP 시도 상한으로 오해하지 않는다. 이 후속 기능을 켤 때만 `APIRunner`에 keyword-only 제한 callback을 추가하여 countTokens/HTTP 재시도 경로에서도 deadline·입력 예산을 확인한다. 키 탐색/HTTP 오류가 비밀값을 출력하지 않는 검사도 함께 둔다. callback을 제공하지 않는 기존 CLI 동작은 보존한다.

검사 callback 계약: `before_request(kind: str, input_tokens: int | None) -> None`; kind=`count_tokens`/`generate`. 매 시도 전에 호출, 시간 초과 또는 잔액 부족이면 전용 `ProbeBudgetExceeded`를 발생시키고 일반 네트워크 재시도로 삼키지 않는다. API quota 사용량 자체는 provider가 보고한 값과 별도로 `estimated_attempt_input_tokens`로 표시한다. 동시 실행은 하지 않는다.

결과 `probe-report.json` 키: `mode="api"`, `token_count_kind="api_count"`, `model_success_count=0`, `sample_manifest_sha256`, `contract_sha256`, `arms`, `generation_attempts`, `count_token_attempts`, `http_retries`, `input_tokens_reported`, `output_tokens_reported`, `elapsed_seconds`, `structural_status`, `gpu_decision`, `stop_reason`. 실패 전 로그·성공 응답은 남기고 미완료 행은 null이다. v20 사실 해석은 §4를 재사용한다. 부분 표본 CSV를 200건 회차에 빈 응답을 채워 끼우지 않는다.

### 5.4 사전 판정 규칙

| 관측 | structural_status | GPU 결정 |
| --- | --- | --- |
| 잘못된 ID/군 결합, 메시지 hash 불일치, 허용 입력/예산 위반, 최종 파싱 결손 | `broken_contract` | 구현을 수정하고 CPU 검사를 다시 한다. 후보 성능 기각이 아님 |
| 정상 42×2 응답·같은 본문·원응답/스키마/호출 출처 모두 보존 | `complete` | 고정 모델 측정 가능. 성능 건강성은 아직 모름 |
| 064/068 같은 known clause에서 새로 검증된 적합 인용, 무작위 표본의 새 잘못된 적용 확대 없음 | `complete` + `mechanism_signal=true` | 가설의 관측 근거 추가. 기존 A8 GPU/채택 기준은 그대로 |
| 검증 인용 0 또는 fallback_only 개선만 있음 | `complete` + `mechanism_signal=false` | API에서는 기전 미확인. 그 이유만으로 A8 GPU를 버리지 않음 |
| 429/키/시간·토큰 상한으로 미완료 | `incomplete` | 환경·예산 문제. 성능/구조 성공으로 세지 않음 |

API로 GPU를 “살릴지/버릴지”를 가르는 성능 문턱은 두지 않는 것이 이 저장소의 실측과 맞다. CPU로 재현되는 계약 위반만 GPU 착수를 막는다. API 구조 실패가 서버에서도 날 것이라고 일반화하지 않는다. 특히 responseJsonSchema와 vLLM 제약 디코딩은 다른 실행이다.

## 6. 후속 우선순위 — A8 이후의 성능 작업

아래 순위는 예상 서버 이득 순위가 아니다. 일반적인 실패 원인을 직접 바꾸는가, 새 TP 경로를 여는가, 실제 입력으로 검증할 수 있는가를 우선한다. 서버 전이율 0.005·0.249·0.926·−0.147은 성공확률이나 곱할 계수가 아니다. “세 번 중 한 번”도 미래 실패 확률로 쓰지 않는다.

| 순위 | 다음 한 가설 | 가능한 범위·첫 산출물 | 제외할 접근 |
| --- | --- | --- | --- |
| 1 | 공고 인용을 다시 쓰지 않고 공고 구간을 선택하게 하면 evidence 실패가 줄어드는가 | A8 감사에서 남은 비-null invalid와 null인데 실제 안내가 있는 건을 나눔. 다음 별도 티켓에서 문서별 고정 구간 ID 선택→원문 문자열 복원 실험. v20만 시작하되 전송/스키마 변경의 24항목 손실을 함께 측정 | 모델에게 긴 문자 offset을 암산시킴, fuzzy 인용 허용, 068 접두어만 제거하는 후처리 |
| 2 | 실제 구매 SW와 과업 수행 도구를 구분하면 applicability 과탐이 줄어드는가 | 제공 소프트웨어 정의와 공고 deliverable을 대조한 v20 적용 대상 관측. 056·144·088의 역할을 감사하고 무라벨에서도 같은 오류를 확인. 인용 후보와 별도 회차 | 업종 1468·특정 제목·법 이름 존재를 정답 규칙으로 삼음, 사업 인용이 맞으면 적용 판단도 맞다고 간주 |
| 3 | v24 동일 필드의 확인된 일치/불일치/미관측을 구분하면 오탐이 줄어드는가 | A7 기존 코드·CPU 재생부터. 5/36/3→4/12/4, Macro +0.005385는 이미 측정됐으나 TP 손실 1. 새 CPU 설계는 `unknown`과 `consistent`의 근거를 먼저 감사 | “불일치를 못 찾음=일치”로 양성 제거, 빈 e24면 0, 꺼진 예산 축 복원 |
| 4 | 경쟁제품 범위·참가자격/서류 역할·완전관측 중 실제 어느 원인을 바꿀 수 있는가 | v10/v11/v18의 A5 `five-stuck-analysis.md`와 scope 감사에서 분해된 장애별 관측을 재사용. 고시 조건과 실제 구매 사양을 대조하는 한 가설로 제한 | 이미 미채택인 H2/v18 재검토 반복, 메타 조항호내용을 본문 요건으로 대체 |
| 5 | 공급된 문서의 절단만 회복하는 입력 선택 | 실제 있는 문서가 토큰 때문에 사라지는 공고에 한정. 입력이 애초에 빠진 v20 24·131·134와 분리. 최소 추가 호출 비용 선계산 | 존재하지 않는 RFP 복원, 완전관측 게이트 해제, 전체 공고 전건 추가 호출 |

v24 오탐 질량은 같은 H4 재생으로 36/111(약 32%)이고, 별도 dev 추론의 32/107(약 30%)과 섞지 않는다. H4 기준 FP만 0으로 만든 산술 상한은 v24 F1 `10/(10+3)=0.769231`, Macro +0.023548이다. 큰 상한이 A7처럼 TP를 내리는 게이트 채택의 근거는 아니다. A7 무라벨 941/6000과 배율 1.206은 불일치 검출 규칙 발화율이지 실제 모델 양성 중 제거율·정밀도 아니다. 모델 사실이 없는 무라벨은 그 효과가 미측정이다.

v11·v18·v20·v23은 기존 TP 고정 시 FP를 전부 지워도 각각 F1 상한 0.500·0.250·0.333·0.333으로 0.6에 못 닿는다(`docs/tasks.md`·활성 계획의 같은 dev 기준). 따라서 오탐 제거만으로 전체 목표를 계획하지 않는다. 입력 자체 누락은 현재 제공 자료로는 회복 불가능할 수 있다는 상한도 유지한다.

A4 결과를 후보 선택에 반영하는 방법: (1) dev 문구 맞춤 규칙보다 출처/관측의 일반 오류를 먼저 친다, (2) 대상 TP 손실을 숨기지 않는다, (3) 실제 무라벨 모델 사실로 변경/보류/발화율을 잰다, (4) 낮은 배율 후보의 dev 이득을 서버 계획에 더하지 않는다, (5) 새 규칙을 한 제출에 묶어 귀인을 잃지 않는다. 배율이 높아도 안전성 보장은 아니다. W5의 자동 반려 임계값을 새로 만들지 않는다.

## 7. 검사와 실패 처리

기존 unittest/pytest 기반에 추가한다. 새 프레임워크·의존성은 없다. 아래는 구현자가 실행해야 할 검사이며 이번 설계 세션에서 통과했다고 기록하는 목록이 아니다.

| 검사 이름/위치 | 단언 | 빨개져야 하는 버그 |
| --- | --- | --- |
| `test_observation_does_not_change_calls_or_payload` / test_a5_collect_facts | 같은 대역 응답으로 observe OFF/ON의 메시지·schema·인자·호출 순서·원응답 동일; 시간값은 비교 제외 | 로깅 과정에서 prompt 수정/재정렬/추가 모델 호출 |
| `test_retry_records_actual_prompt_and_restores_chat` / 동일 | 진짜 VLLMRunner.retry_chat을 대역 chat과 함께 실행. retry system 추가문·줄어든 max_tokens 포착, 예외 뒤 instance 상태 복원 | 최초 prompt를 retry에 연결; 감싼 메서드가 다음 군에 남음 |
| `test_batch_failure_keeps_partial_calls_without_fake_success` / 동일 | 최초 batch 예외→singleton recovery 및 최종 실패의 call/parse 개수 구분, 실패 전 응답 보존 | 누락 응답을 valid/0으로 채움; 이전 last_response_info 재사용 |
| `test_capture_identity_is_not_guessed` / 동일 | 동일 user 메시지 중복이면 ambiguous 기록; wrong id 부착 금지 | digest 하나로 서로 다른 ID 혼합 |
| `test_a8_lifecycle_closes_on_budget_and_model_failure` / test_a8_v20_annex | 모델 적재/예산/중간 군 실패 각각에 run_started 1·run_failed 1, complete=false | phase_started만 추가해 루트가 계속 없음; 정상 종료 위장 |
| `test_arm_and_retry_generations_are_distinct` / test_langfuse_tail | 같은 id·global_index의 control/a8/retry가 서로 다른 key와 부모; 각 open 정확히 close | 군 덮어쓰기, retry 중복 합산, arm 부모 오류 |
| `test_captured_response_is_parse_event_not_second_generation` / 동일 | physical model_call 수와 generation 수 동일, invalid/valid parse 보존 | 새 호출 로그+옛 response를 이중 generation으로 셈 |
| `test_dev_export_rejects_wrong_dataset_and_host` / 동일 | dev hash·ID/record·contract 불일치/외부 host/redirect 거부, provider 미호출 | 접두사만 보고 비공개 원문 수출 |
| `test_missing_prompt_and_tokens_remain_unknown` / 동일 | 구 로그 input 없음, unknown usage 생략, legacy 이벤트 지원 | 없는 prompt 재구성·미측정 토큰 0 기입 |
| `test_v20_audit_matches_real_consumer` / test_a8_v20_annex | 200건 실제 카탈로그 초기화 후 audit v20_write와 직접 소비 결과 동일; known v13 양성 경로 nonempty | products 전역 누락으로 모든 결함 0; company_reason을 v20 이유로 오해 |
| `test_invalid_quote_is_preserve_not_verified_negative` / 동일 | 원문 밖 인용은 preserve, null+완전관측+yes는 write_1, 원문 적합 인용은 write_0 | wiki 068과 같은 fallback 개선을 정밀도 회복으로 기록 |
| `test_quote_roles_and_missing_documents_are_independent` / 동일 | software yes/no/unknown × 인용 null/valid/invalid × 완전관측/누락 결합; baseline 0/1 양쪽에서 최종 병합 대조 | 한 인용 필드 스윕만으로 전체 계약 통과 선언 |
| `test_sample_has_12_mandatory_and_30_disjoint_random` / 동일 | 실제 원천에서 42 ID·중복 없음·132 포함·같은 manifest 반복 동일; 라벨이 메시지로 안 감 | 11+30=41로 양성 한 건 누락; 표본 선택 후 seed만 기록 |

기존 A8 `LawQuotationTests`의 7개 인용 필드·분류/역할 결합 검사, v13 세 셀 변경 계약, A5/v18/wiki 예산/collector 호출 계약, replay/compare_runs 검사를 함께 실행한다. 최종 수정 위치에 맞는 회귀 검사까지만 실행하고 무관한 테스트를 늘리지 않는다.

권장 묶음:

```text
python -X utf8 -m pytest -q tests/test_a5_collect_facts.py tests/test_a8_v20_annex.py tests/test_langfuse_tail.py tests/test_a5_v18_scope_review.py tests/test_wiki_rag_pilot.py tests/test_replay_run.py
```

관측기 결함이면 원응답은 보존하고 관측 준비 완료를 중단한다. 성능 회차의 모델 호출 자체가 유효했다면 그 사실은 유지하되 빠진 prompt/시간은 미측정으로 표시한다. 소비자/입력/예산/회차 동일성 위반이면 해당 비교·채택을 중단한다. GPU에서 목표 미달이면 실패 결과를 보존하고 A8을 미채택으로 닫는다. 결과를 보고 프롬프트·표본을 살짝 바꿔 같은 실험 이름으로 반복하지 않는다.

## 8. 시간·토큰·쿼터 장부

| 작업 | 계산 | 해석 |
| --- | --- | --- |
| CPU 관측/계약/감사 | 모델 0회, 외부 API 0회 | 소요 시간은 구현 후 재며 기존 테스트 시간을 재사용하지 않음 |
| A8 두 회차 최초 입력 | H4 mean 참고 `800×10370 + 400×586 = 8,530,400토큰` | A8 15296 예산에서의 실제 평균은 다를 수 있어 추정. 실제는 각 generation의 usage 합계 |
| A8 출력 예약 합 | `800×1024=819,200토큰` | 생성량 예측이 아니라 최초 요청 예약 총량. retry는 별도 |
| A8 실제 단계 | `4×339.178=1356.712초` | 통과 가능한 네 단계의 합. CPU 예산 검사·적재·파일 처리·회차 전환은 별도 |
| 서버 조건부 환산 | `6380+(candidate_stage−246.985)×8.8944` | 회사 단계 교체 기준. 실제 전체 pipeline/서버 검증 필요 |
| API 표본 | `84×10941=919,044토큰`, `919044/16000×60=3446.415초` | 약 57.44분, median 기반 근사. 같은 API의 A8 증가량은 미측정 |
| API A8 증가 참고 | `42×586=24,612`, 16000 TPM 가정 +92.295초 | 고정 모델 토큰을 API로 옮긴 민감도 계산일 뿐, 실제는 api_count 사용 |
| API pacing 주의 | 1건 10,941이면 2건=21,882>16,000 | 기존 60초 window bucket은 약 1건/분이 될 수 있음. 84건이면 대기만 약 83분+마지막 지연; 41초/건을 보장하지 않음 |
| 유망 후보 무라벨 | `6000×2=12000` 최초 company 요청, `6000/200=30`배 | 단계 시간 단순 환산 `30×(control_stage+candidate_stage)` + 준비 시간. 둘 다 상한이면 약 5.65시간. 대량 실행 예산 별도 |

무라벨은 dev 통과 전 실행하지 않는다. API 약 1시간을 아껴 GPU 22.6분짜리 조건부 비교를 직접 하자는 판단이지 GPU/API의 시간·출력을 등가로 본다는 뜻이 아니다. GPU/Colab 요금·쿼터 잔액·현재 가용성은 미측정이다.

prompt 로그 용량도 실측해야 한다. 입력 배열의 `len(json.dumps(messages, ensure_ascii=False).encode("utf-8"))` 합계를 저장하고 retry를 더한다. 16,000 문자를 16,000 bytes라고 세지 않는다. 50MB 초과 파일은 `docs/runs.md` 보관 규약대로 경로·크기·이유를 적고 임의로 원문을 잘라 실측 로그라 부르지 않는다.

## 9. 대회 규칙 대조

| 단계 | 활용 허용 | 지킬 조건·미확정 |
| --- | --- | --- |
| 설계·CPU 감사 | A1·A4·A9·A10 | R5/R11 제공 공고·스냅샷만. dev 선정/튜닝 사실 공개. 법률의 최신성을 웹으로 갱신하는 작업 아님 |
| A8 고정 모델 파일럿 | A1·A6·A9 | R1 고정 모델, R3 학습/가중치 변경 없음, R4 live와 mock 분리, R8 공고 간 판정 공유 없음. 관측 데이터는 출력 경로에만 흐름 |
| 로컬 Langfuse | A1·A9 | R9 평가자료 튜닝 금지, R17 평가자료 송신 금지. 고정 공개 dev와 로컬 전용 수출. 비밀/개인경로 없음 |
| API 관측(조건부) | A3와 R6의 적용 범위를 확인해야 함 | Q1 확인 전 실행 보류. 라벨 생성 허용과 관측/프롬프트 최적화 허용을 구분. R11 제공 스냅샷 고정, R15 요청·응답·모델 버전 보존 |
| 패키징·제출 | A4·A6 | R7 API/telemetry/키/사이드카를 제출물에서 배제, R14 allowlist 유지, R15 재현, R18 e20 빈칸·CSV 계약, R19 고정 패키지 보존, R21 실제 전체 시간 검증 |

R7은 제출 추론의 외부 호출 금지이고 모든 개발 시 script.py 편집을 영구 금지하는 조문은 아니다. 이번 script.py 불변은 의뢰 범위와 검증 ZIP 보존 계약이다. 향후 후보가 유망해 운영 통합을 한다면 새 코드·새 ZIP으로 전체 검증해야 하며 옛 ZIP의 검증을 승계할 수 없다.

## 10. 구현 순서와 커밋 단위

커밋은 아래의 검토 가능한 작업 단위 제안이며 이번 세션에서 커밋·push 권한을 행사하지 않는다.

1. `feat: capture A8 model calls without changing inference`
   - collector와 A8 파일럿 lifecycle, raw call/parse 분리, 실패 보존 및 해당 검사.
   - 통과: 관측 OFF/ON 비간섭·실제 retry capture·기존 A5/wiki 호출 호환·script.py hash 동일.
   - `docs/langfuse.md`에서 기존 script 수정 요청을 삭제하고 새 파일 기록 계약을 같이 반영한다. 아직 Langfuse 적재 성공이라고 쓰지 않는다.
2. `feat: project A8 diagnostics into local dev traces`
   - tail의 arm/call/예산 mapping 및 dev/full-prompt 수출 검사, 관련 tests.
   - 통과: 한 run 루트·서로 다른 군·재시도 prompt·정확한 lifecycle·원격/타 데이터 차단. 네트워크 없는 Op 검사와 실제 로컬 적재를 따로 기록한다.
   - 더 단순한 대안은 통합 JSONL과 감사 JSON만 읽는 것이다. 화면은 없어도 성능 회차를 진행할 수 있다. 이 설계는 요청된 네 관측 구멍을 기존 sidecar에 메우되 새 UI를 만들지 않는다.
3. `feat: audit A8 quotation mechanism and freeze inputs`
   - `a8_v20_audit.py`, 표본 manifest 생성, 소비자 대조 검사. API 실행기 신규 구현은 제외.
   - 통과: 카탈로그 활성·24항목 기존 재생·인용 결합 검사·fallback_only 분리·표본 42개.
   - `reports/team-c/a8-v20-annex/observation-contract.json`에 `capture_protocol`, sources hashes, tests, `gpu_status="not_run"`, `api_status="blocked_q1"`, `langfuse_status`를 둔다. reviewer/미측정 값은 null. 단일 원장을 문서들이 링크한다.
4. `docs: pin the observed A8 two-episode run`
   - 앞 구현 커밋을 40자리 SHA로 고정하고 notebook REPO_REF를 별도 커밋에 넣는다. 새 SHA를 지금 지어내지 않는다. 입력 ZIP 30개 원자료가 그대로면 재번들하지 않는다. manifest 일치는 다시 확인한다.
   - 새 핀의 `script.py`, 후보 프롬프트, schema, chat template, seed, model revision, 1024/15296 값이 기존 b139807과 같음을 기록한다. 관측 소스만 바뀐 것을 diff로 확인한다.
   - 코드·노트북을 새 환경에서 확보 가능한지 실행 담당자가 첫 생성 전에 확인한다. 실패하면 해당 준비 단계 중단. 이번 로컬 branch contains 결과를 원격 fetch 증거로 쓰지 않는다.
   - A8 작업서·README·run-request·cpu-checks의 현재 핀·노트북 hash·docs/tasks·활성 계획을 같은 커밋 단위로 맞춘다. 과거 실행 기록은 history로 보존한다. 오래된 “남은 수리”·“두 회차뿐”·“운영 불변” 등의 모순도 해당 현재 상태 절에서 해소한다.
5. 실행·결과 기록(소스 수정 없는 회차)
   - 동일 새 소스/노트북·동일 입력 ZIP으로 새 런타임 두 회차. 원응답·diagnostics·budget·environment·contract·audit·원본 ZIP hash 보존.
   - 한 회차가 유효하게 실패했으면 실패 종류를 보고한다. 부호만 보고 두 번째를 취소하지 않는다. 입력/시간 상한/복구 실패처럼 사전 등록 중단 조건이면 후속 회차를 중단하고 이유를 기록한다.
   - `reports/team-c/a8-v20-annex/results.md`, 실행 색인, 작업서·큐·위키·기계 원장을 함께 갱신. 중복 episode-1 사본은 canonical episode 하나로 센다.
   - 두 회차의 검증된 동일 기전 개선·대상 밖·시간을 통과한 경우에만 무라벨 6,000건 두 군 작업서를 확정한다. 그 뒤 결과 독립 리뷰와 운영 통합/전체 검증을 별도로 거친다. 사용자가 마련한 독립 리뷰 세션을 쓰며 하위 에이전트를 만들지 않는다.

A8 미달이면 다음 착수서는 §6 순위1의 구간 선택 실험이다. 이 문서는 그 미래 소비자/스키마를 미리 구현하라는 지시가 아니다. A8 감사 결과로 실패 분모를 확인한 뒤 한 가설·별도 작업서로 시작한다.

## 11. 하지 말 것

- 한 인용 필드만 바꾼 검사를 전체 계약이라고 부르지 않는다. 범위·역할·자격·인용·완전관측과 baseline 보존의 결합 경로를 검사한다. 기존 가드를 제거했을 때 실제 검사 실패가 나는지도 확인한다.
- `_PRODUCTS=[]` 상태에서 실제 결과가 0이라 안전하다고 하지 않는다. 같은 script 모듈을 load_sme_reference로 초기화하고 알려진 양성 경로가 작동하는 대조를 먼저 둔다. `run_submission`의 옛 모듈을 잘못 집지 않는다.
- 재시도에 최초 prompt를 붙이지 않는다. retry의 system 추가문·출력 예산·물리 호출과 parse 결과를 따로 보존한다.
- Langfuse에 span이 보인 것만으로 CPU/GPU/API/서버 성공을 선언하지 않는다. 로컬 JSONL이 분석의 원본이다.
- A8 법령 위치/양과 인용 스키마/소비자/완전관측을 한 회차에서 같이 바꾸지 않는다. 1024 예약으로 성능이 좋아졌다면 그 효과와 법령 효과를 같은 baseline 차이로 주장하지 않는다. 두 군 예약은 같다.
- null/invalid 인용/법적으로 해당 없음/문서가 없음/입력이 잘림을 하나의 “없음”으로 묶지 않는다. invalid→preserve는 검증된 비위반이 아니다.
- A4 서버 스칼라만으로 v6·v9·v23별 손실을 실측했다고 하지 않는다. 배율·법적 근거가 있어도 전이를 보장하지 않는다.
- API를 제출물 밖이라고 무조건 허용하지 않는다. API 실패로 고정 모델 가설을 기각하지 않는다. API 토큰·시간을 서버 예산으로 쓰지 않는다.
- 문서 한두 개만 갱신하지 않는다. 작업서·큐·활성 위키·README·실행 안내·기계 원장·노트북 핀을 한 상태로 확인한다. 과거 문단은 현재 상태와 명확히 구분한다. 모든 숫자를 여러 곳에 다시 복제하기보다 소유 원장으로 링크한다.
- 관측 때문에 새 서비스·UI·통합 실험 프레임워크·범용 task DAG를 만들지 않는다. 기존 CLI·파일·수집기·sidecar로 끝낸다.

## 12. 착수 판정

이번에 수행한 검증은 로컬 코드/문서/리뷰 읽기, Git 상태·핀 포함 이력 확인, 저장 JSON/CSV를 이용한 12건 필수 표본 합집합 및 산식의 읽기 전용 계산이다. 새 코드 테스트·토크나이저 재측정·GPU·API·Langfuse 접속은 실행하지 않았다. 위 테스트와 관측 함수는 설계이며 존재/통과를 주장하지 않는다.

필수 구현은 §3~4와 §7~10의 CPU 관측·감사·고정 모델 A8 준비다. API는 선택적 미래 분기이며 Q1 확인 전 실행하지 않는다. 이 설계가 보장하는 것은 구현할 계약의 구체성이고, 성능·원격 실행·운영 채택의 성공이 아니다.

구현 착수 가능
