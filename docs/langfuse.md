# Langfuse 실행 관측

Colab 실행의 공고별 호출을 실시간으로 보고, 팀원도 같은 화면을 보게 한다.
**제출 코드는 바뀌지 않는다.** `script.py` 가 이미 이벤트마다 `flush()` 하며 쓰는
`diagnostics.jsonl` 을 사이드카가 옆에서 따라 읽어 보낸다.

기존 진단 파일을 손으로 읽는 방법은 [Colab 실행 안내](colab.md#진단-파일-읽기)에 그대로 있다.
Langfuse 는 그 파일을 대신하지 않는다 — **분석 입력은 여전히 `diagnostics.jsonl` 이다.**
이 스택은 `LANGFUSE_MIGRATION_V4_WRITE_MODE=events_only` 라서 읽기 공개 API
(`traces`/`observations`/`sessions`)가 404 다. 사람이 보는 길은 UI 뿐이다.

## 팀원에게 무엇이 보이는가

**이 인스턴스에는 대회 트레이스밖에 없다.** 그것이 설계의 첫 요구였다.

같은 기계에는 다른 프로젝트가 쓰는 Langfuse 스택이 따로 있고, 거기에는 이 대회와
무관한 자료가 들어 있다. 그 스택을 팀원에게 열면 같은 로그인 뒤에 그것이 놓인다.
Langfuse 의 **프로젝트 단위 역할은 유료(Enterprise) 기능**이라, 무료 셀프호스트에서
조직 멤버는 그 조직의 모든 프로젝트를 본다. 그래서 프로젝트를 나누는 것으로는
막을 수 없고 **인스턴스를 갈랐다.** 팀원이 받는 주소에는 대회 자료만 존재한다.

그 격리를 유지하는 운영 규칙 넷이다.

- 이 인스턴스에 **다른 프로젝트를 만들지 않는다.** 만드는 순간 조직 멤버 전원에게 보인다.
- 팀원은 UI 에서 **Member 또는 Viewer** 로 초대한다. Owner/Admin 은 본인만 갖는다.
- `.env` 의 `LANGFUSE_INIT_USER_*` 계정은 **Owner 다. 공유하지 않는다.**
- 터널이 여는 것은 웹(3002) 하나뿐이다. clickhouse·minio·redis 는 루프백에 남는다.

## 띄우고 내리기

```powershell
python -X utf8 tools/langfuse_local.py up      # 띄운다. UI 는 http://localhost:3002
python -X utf8 tools/langfuse_local.py keys    # Colab 에 넣을 세 줄
python -X utf8 tools/langfuse_local.py share   # cloudflared 로 팀에 연다
python -X utf8 tools/langfuse_local.py down    # 내린다. 트레이스는 볼륨에 남는다
python -X utf8 tools/langfuse_local.py reset   # 볼륨까지 지운다
```

첫 기동이 `docker/langfuse/.env` 에 비밀값을 만든다. 이 파일은 git-ignore 된다.
`POSTGRES_PASSWORD` 는 initdb 때 한 번만 쓰이므로, `.env` 를 손으로 다시 만들었으면
`reset` 을 같이 해야 한다. 안 그러면 새 비밀번호로 옛 DB 에 붙으려다 죽는다.

| 컨테이너 | 호스트 포트 | 같은 기계의 다른 스택 |
| --- | --- | --- |
| `langfuse-web` (UI·수집) | **3002** | 3001 |
| `langfuse-worker` | 3031 | 3030 |
| `clickhouse` — 스팬이 사는 곳 | 8124 · 9002 | 8123 · 9000 |
| `minio` — 이벤트 blob | 9092 · 9093 | 9090 · 9091 |
| `redis` | 6380 | 6379 |
| `postgres` | 안 연다 | 안 연다 |

`docker compose` 의 project name 은 `langfuse-nara` 다. 볼륨도 그 접두로 갈린다.

WSL2 메모리 상한은 스택 둘을 같이 띄우려고 `~/.wslconfig` 에서 5500MB → 11000MB 로
올렸다. **대회가 끝나 이 스택을 내리면 5500MB 로 되돌린다.** 그 파일의 주석에
과거 OOM 사고 기록과 함께 적어 두었다.

## 팀에 열기

```powershell
python -X utf8 tools/langfuse_local.py share
```

cloudflared 임시 터널을 띄우고, 그 주소로 `NEXTAUTH_URL` 을 바꿔 웹 컨테이너를 다시
만든다. NextAuth 는 브라우저가 실제로 쓰는 주소와 이 값이 다르면 로그인을 거부하므로
순서가 그렇다. Ctrl+C 로 끝내면 터널을 닫고 `NEXTAUTH_URL` 을 로컬로 되돌린다.

- 주소는 **재기동마다 바뀐다.** 팀 채널에 그때마다 올린다.
- 내 PC 가 켜져 있고 이 창이 살아 있는 동안만 유효하다.
- 팀원 OS 는 상관없다. Mac 이든 Windows 이든 브라우저로 들어온다.
- 임시 터널은 주소를 아는 누구나 로그인 화면까지 닿는다. 계정은 난수 비밀번호이고
  이 인스턴스에는 공개 dev 자료만 있다. 그래도 **필요할 때만 열고 닫는다.**

## 프롬프트 전문은 터널로 보내지 않는다

`capture_protocol=1` 회차(A8 관측)의 `diagnostics.jsonl` 에는 **모델에 실제로 보낸
프롬프트 전문과 응답 전문**이 들어 있다. 아래 터널 주소로 그것을 보내지 마라.
사이드카는 기본적으로 본문을 **안 싣고** `prompt_capture="withheld"` 만 남긴다.

본문까지 보려면 **회차 뒤에 ZIP 을 받아 로컬에서 재생**한다. 그때만 실린다.

```powershell
python -X utf8 tools/langfuse_tail.py --diagnostics <받은>/diagnostics.jsonl `
    --dev-input open/dev.jsonl --include-prompts
```

`LANGFUSE_HOST` 가 `http://localhost:3002`(또는 `127.0.0.1`·`[::1]`) 그대로가 아니면
거부한다. userinfo·query·fragment·다른 포트·다른 경로도 거부다 — 로컬처럼 생긴
주소가 밖으로 리다이렉트할 수 있다. `--follow`·`--from-line` 과도 같이 못 쓴다.

그리고 로그가 **고정 공개 dev 회차**인지 데이터로 대조한다. `run_started.dataset="dev"`,
dev 파일 실측 sha256 이 로그의 `dataset_sha256` 과 `inputs.json` 고정값과 모두 같고,
`dev_ids` 가 그 파일의 고유 id 집합과 정확히 같고, 모든 공고 이벤트 id 가 그 집합
안에 있고, 신원 미확정(`ambiguous`·`unmatched`) 본문이 0건이어야 한다.
**플래그는 안전의 근거가 아니다 — 이 대조가 근거다.** 접두사만 보면 안 된다.

그리고 **id 가 맞다는 것은 본문이 dev 에서 왔다는 근거가 아니다.** 유효한 공고 id 에
임의 문자열을 붙인 로그가 위 검사만으로는 통과한다. 그래서 공고별 user 프롬프트와
문서 본문 hash 를 **실제 dev 파일에서 다시 만들어** 한 글자까지 대조한다.
프롬프트는 **정확히 두 메시지**(system·user)여야 하고 각 메시지는 `role`·`content`
두 칸뿐이다 — 형태를 느슨하게 보면 그 사이에 끼운 메시지가 통과하고 배열 전체가 나간다.
system 은 제품 프롬프트나 후보 블록 중 **가장 긴 것**으로 시작해야 하고(짧은 쪽을
고르면 후보 블록이 모르는 꼬리가 되어 **진짜 회차가 거부된다**), 꼬리는
`COMPANY_SIZE_KEYS` 로 만든 분할 재시도 문자열과 정확히 같아야 한다.

전송 자체도 그 호스트에 묶는다. 셋을 막는다.

- **redirect.** `requests` 는 기본적으로 따라가므로 로컬 엔드포인트가 307 로 외부
  `Location` 을 돌려주면 검사를 통과한 본문이 밖으로 다시 POST 된다.
- **환경 프록시.** 세션의 `trust_env` 가 참이면 `HTTP_PROXY` 가 있는 환경에서
  `merge_environment_settings()` 가 **로컬 주소에도** 외부 프록시를 고른다. 본문과
  인증 헤더가 그쪽으로 간다. `trust_env`·`proxies` 를 끄고 호출마다 비운다.
- **호스트 위장.** url 을 `urlparse` 해 scheme·hostname·port 를 비교하고 userinfo 를
  거부한다 — `http://localhost:3002@evil.example/x` 가 문자열 `startswith` 를 통과한다.

세션을 못 잡으면 **수출을 거부한다.** 막았다고 믿는 것이 안 막힌 것보다 나쁘다.

`--session` 기본값도 절대경로를 안 쓴다 — 저장소 안이면 상대경로, 밖이면 파일명 +
경로 hash 앞자리다. 기본값이 그대로 `langfuse.session.id` 로 실리기 때문이다.

호출 하나도 짝이 맞아야 한다. `capture_protocol=1` 의 **모든 물리 호출**이 결속된
프롬프트를 가져야 하고, 본문을 내보내는 응답은 그 결속된 시작과 call key 로 짝이
맞아야 한다 — 시작에서 본문만 빼면 그 호출의 응답 위조가 검증을 건너뛴다.

## 구조화 필드도 위생을 지난다

**"구조화 필드라서 안전하다" 는 근거가 아니다.** `settings` 에 키를 하나 더 넣거나
`items` 에 다른 문자열을 넣은 로그가 그대로 루트 input·generation metadata 로 실렸다.

`_clean(name, value)` 이 span 으로 나가는 **모든 이벤트 유래 값**에 이름별 규칙을 건다.

| 모양 | 규칙 |
| --- | --- |
| 수치 | `int`·`float` 여야 한다. 문자열이면 버린다 |
| `*_sha256` | 16진수여야 한다 |
| enum | **값 집합까지** 고정한다(`identity_status`·`transport_status`·`mode`·`stage` 등) |
| `items`·`groups` | 제품의 항목 목록(`ITEMS`+`COMPANY_SIZE_KEYS`+`SME_ITEMS`)뿐 |
| `packages` | `이름==버전` 뿐 |
| 중첩 dict | 키마다 같은 규칙을 다시 건다 |
| 모르는 이름 | **안 내보낸다** |

`argv` 는 아예 싣지 않는다 — 명령줄에 경로가 들어간다. 짧은 식별자 패턴에서 `/` 와 `:` 를
뺀 것도 같은 이유다. 이 파일이 만든 고정 문구는 `_fixed()` 로 넣어 위생 대상에서 가른다.

## 구분할 수 없으면 평문을 안 보낸다

패턴을 조여도 **짧은 영문 토큰은 못 가른다.** 버전 자리의 `sk-live-secret123` 은 버전과
모양이 같다. 그래서 기본이 **요약**(`sha256:앞16`)이고 평문은 근거가 있을 때만이다.

**모양이 값을 증명한다고 볼 수 있는 것은 hash 뿐이다.** 나머지는 생산자 집합과 대조한다 —
패턴으로 두면 그 자리에 토큰형 비밀이 통과한다.

**모양으로 평문을 통과시키는 자리는 없다.** 평문은 전부 **집합 대조**를 지난다.

| 평문 | 무엇과 대조하나 |
| --- | --- |
| enum 값 | 생산자에서 읽는다 — `mode`·`token_count_kind` 는 실행기 클래스, `phase` 는 소스, `arm` 은 `DEV_ONLY`, `error_type` 은 `builtins` 의 예외 클래스 |
| `MODEL_ID`·`MODEL_REVISION`·`QUANT` | `script.py` 의 상수 |
| 버전 | 계약의 `pinned_environment`. 모양으로 두면 `123.456.789.012` 가 통과한다 |
| 공고 id | `open/dev.jsonl` + `open/data/test.jsonl.gz` 의 id 집합(210개). 회차가 **스스로 선언한** `dev_ids` 는 근거가 아니다 — 1층이 안 도는 모드에서 공격자가 자기 allowlist 를 만든다 |
| 자산 키 | `script.py:2072` 가 만드는 닫힌 집합 |
| 패키지 이름 | `script.py` 가 버전을 세는 목록 |
| 항목명 | `ITEMS`+`COMPANY_SIZE_KEYS`+`SME_ITEMS` |
| hash | **재계산한 digest**. 16진수 모양은 근거가 아니다 — `"deadbeef"*8` 이 같은 모양이다 |

hash 중 재계산할 수 있는 것은 열한 개다 — `script.py`·dev·제출 입력·항목표·
디코딩 스키마·`SME_FILES` 셋·제품과 후보 system 프롬프트·스키마. 재계산 못 하는 것
(`chat_template`·`contract`·`visible`·`prompt`)과 **옛 회차의 코드 hash** 는 요약된다.
그때의 `script.py` 는 지금과 다르므로 재계산할 수 없다. 요약해도 **같은 hash 는 같은
요약**이라 "회차 간 같은가" 는 답할 수 있고, 핀과 대조할 때는 핀도 같은 방식으로 요약한다.

**요약은 유실이 아니다** — 동일성과 변화는 남으므로 "같은 설정으로 돌았나" 는 답할 수 있다.
모르는 이름은 요약도 안 하고 아예 버린다. **map 은 값만이 아니라 키도 본다** — 값만 보면
키에 개인 경로가 남는다. span 이름·key 를 만드는 값도 위생을 지난 것만 쓴다.

## 출구는 하나다

`plan()` 이 돌려주는 모든 Op 가 `guard()` 를 지난다. 어느 분기가 무엇을 넣어도 직렬화
직전에 `name`·`status`·`key`·`usage_details`·`trace.name` 이 같은 기준을 지난다.
전송 루프가 span 에 직접 적는 속성도 같은 통로를 쓴다 — **통로를 만든 것과 모두가 그
통로를 쓰는 것은 다른 일이다.** 규칙은 허브 위키 `craft/gate-the-exit-not-the-callers`,
경위는 `.wiki/decisions/2026-09-22-087-fix-export-gate-at-one-exit.md` 에 있다.

**예외 메시지와 traceback 도 본문이다.** 개인 절대경로가 들어가므로 metadata 전용
모드에서는 `error_type`(클래스 이름)만 남기고 나머지는 `withheld` 로 적는다.

계약은 `reports/team-c/a8-v20-annex/observation-contract.json` 이 소유하고
`tests/test_langfuse_tail.py::PromptExportBoundary` 가 고정한다.

## Colab 에서 붙이기

노트북이 clone 한 저장소 안에서 사이드카를 띄운다. 제출 ZIP 은
`script.py` 와 `requirements.txt` **둘뿐**이므로(`tools/package.py` 의 `FILES`)
이 도구가 제출물에 섞일 수 없다.

아래는 **metadata 전용** 실시간 추종이다. 프롬프트 전문은 위 절을 따른다.

```python
# 1) 사이드카 의존성. 제출 requirements.txt 와 무관하다.
!pip -q install opentelemetry-sdk opentelemetry-exporter-otlp-proto-http

# 2) 이번 회차의 터널 주소와 키 (`langfuse_local.py share` 가 찍어 준 세 줄)
import os
os.environ["LANGFUSE_HOST"] = "https://<이번-터널>.trycloudflare.com"
os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-nara-..."
os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-..."

# 3) script.py 를 띄우기 직전에 붙인다. 파일이 없으면 생길 때까지 기다린다.
import subprocess, sys
tail = subprocess.Popen([sys.executable, "tools/langfuse_tail.py",
                         "--diagnostics", f"{OUTPUT_DIR}/diagnostics.jsonl",
                         "--follow", "--session", RUN_NAME])

# ... 기존 script.py 실행 셀 ...

tail.wait(timeout=180)   # 남은 배치를 보내고 끝난다
```

키가 스위치다. 셋 중 하나라도 없으면 사이드카는 아무것도 안 하고 끝난다.
런타임이 끊겨 중간부터 다시 붙일 때는 `--from-line N` 으로 이미 보낸 줄을 건너뛴다.
같은 `--session` 이면 같은 trace 에 이어 쌓인다.

## 무엇이 span 으로 오는가

| 진단 이벤트 | Langfuse |
| --- | --- |
| `run_started` → `run_succeeded`/`run_failed` | 트레이스 루트 span. 설정·해시·argv 가 input, 결과가 output |
| `model_loading` → `model_loaded` | `model-load` span, 로드 시간·환경 |
| `chunk_started` | 청크 span. 다음 청크가 시작될 때 닫힌다 |
| `response` | **generation.** 공고 ID 가 이름, 토큰 수는 usage, `finish_reason`·`stop_reason`·`attempt` 는 메타데이터 |
| `batch_failed`·`retry_failed` | ERROR 레벨 이벤트. 실패 단계와 예외가 status 로 |
| `sme_fallback` | WARNING 레벨 이벤트 |
| `sme_verified` | 항목 판정과 기각 사유 |

배치 호출이라 generation 의 **시작 시각은 그 청크의 시작과 같다.** 한 건의 순수
지연이 아니다. 그 사실을 span 메타데이터의 `duration_note` 에도 적어 둔다.

프롬프트 본문과 원응답은 `--debug-responses` 로 돌린 **진단 실행에만** 들어간다.
기본 실행은 토큰 수와 실패 사유만 남긴다.

### capture_protocol 1 — 실제 호출이 따로 온다

A8 관측 회차는 판형 번호 `1` 을 적는다. 그 로그에서는 **물리 호출과 파싱이 갈린다.**

| 진단 이벤트 | Langfuse |
| --- | --- |
| `arm_started` → `arm_finished` | 군 span. 같은 공고가 군마다 다른 key 를 받는다 |
| `model_call_started` → `model_call_finished`/`_failed` | **generation.** 실제 모델 요청 하나다. 분할 재시도는 별도 요청으로 남는다 |
| `response` | `parse-…` **이벤트.** generation 을 또 만들지 않는다 — 호출 하나가 둘로 세지 않게 한다 |
| `model_loaded` 의 `mode` | 루트 span 의 이름·metadata 를 고친다. 루트는 생성 전에 `pending` 으로 열리므로 이게 없으면 실제 회차와 대역 실행이 안 갈린다 |

`schema_sha256` 은 제품이 **실제로 쓴** 파라미터를 가리킨다 — `items` 가 있으면
`sp` 가 아니라 `parameters_for_items()` 로 제한한 스키마다(`script.py:967`).

판형 번호가 없는 옛 로그는 기존 `response` → generation 투영을 그대로 쓴다.

## 대회 규칙 경계

- **공개 dev 자료만 보낸다.** 비공개 평가 입력을 넣으면 [R17](rules.md) 즉시 실격이다.
- **프롬프트 전문은 로컬 주소로만, 고정 dev 대조를 통과할 때만 나간다.** 로컬 주소라는
  사실만으로 비공개 자료가 허용되는 것은 아니다. 평가 입력·서버 추론 로그에는 이 도구를
  연결하지 않는다. 비밀키·환경변수 전체·`.env`·개인 절대경로는 span 에 넣지 않는다.
- 제출 추론은 외부를 호출하지 않는다(R7). 사이드카는 제출물 밖의 별도 프로세스이고
  제출 ZIP 은 `script.py`·`requirements.txt` 둘뿐이다.
- `requirements.txt` 에 `langfuse`·`opentelemetry` 를 넣지 않는다. 평가 서버에 설치될
  이유가 없고, 제출 게이트의 "외부 호출·비밀키 없음" 과도 충돌한다.
- Langfuse 화면의 성공은 **관측의 성공이지 점수·서버 성공이 아니다.**

## 확인된 것과 아닌 것

2026-09-17 이 기계에서 확인했다.

- 스택 6컨테이너 기동, `GET /api/public/health` → `{"status":"OK","version":"4.27.0"}`
- mock 실행 6건의 진단을 사이드카로 보내 새 스택 ClickHouse 에 **span 12개** 적재
  (공고 6 + 청크 2 + model-load + assets + phase + 루트)
- 같은 시점 다른 스택은 기존 이벤트 수 그대로이고 대회 span **0건** — 격리 확인
- `share` 로 임시 터널을 열어 외부에서 health 200·로그인 화면 200 확인 후 닫음.
  닫을 때 `NEXTAUTH_URL` 이 로컬로 자동 복원됨
- **실제 GPU·Colab 회차에서는 아직 안 돌렸다.** `--follow` 의 실시간 추종도
  완성된 파일로만 확인했다. 팀원 계정 초대와 Member/Viewer 화면도 아직 안 만들었다

2026-09-22 `capture_protocol=1` 투영을 **CPU 재생 로그로만** 확인했다.
군별 파일럿 로그는 그전까지 `run_started` 가 없어 사이드카가 **모든 이벤트를 버렸다**
(400 → span 0). 지금은 1,618 이벤트 → 1,618 op, 생성 키 400개 전부 구별, 열고닫은 쌍 408,
미종료 0 이다. **로컬 스택 적재·UI 확인은 안 했고 GPU 회차에서도 안 돌렸다.**
프롬프트 수출 검사는 검사 6개로만 확인했으며 실제 적재로 확인한 것이 아니다.
