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

## Colab 에서 붙이기

노트북이 clone 한 저장소 안에서 사이드카를 띄운다. 제출 ZIP 은
`script.py` 와 `requirements.txt` **둘뿐**이므로(`tools/package.py` 의 `FILES`)
이 도구가 제출물에 섞일 수 없다.

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

## B 에게 요청할 한 줄

`script.py` 는 실제로 보낸 프롬프트를 남기지 않는다. `system_prompt_sha256` 만 있다.
계획이 첫 48시간에 확인하라는 `적용 대상 인식 → 전달 문맥 → 사실 추출 → 조건 비교 →
후처리` 중 **전달 문맥**이 그래서 비어 있다. `script.py:579` 에 한 줄이면 된다.

```python
        if debug_responses:
            fields["prompt_text"] = batch[i][-1]["content"]   # 실제 전달된 문맥
            fields["response_text"] = text
```

`batch` 는 `run_chunk` 의 인자라 이미 클로저에 있다. dev 진단 실행에서만 켜지고
200건 × 16,000자 ≈ 3MB 다. 사이드카는 이 필드가 오면 generation 의 input 으로 싣고,
없으면 그냥 비운다 — `tests/test_langfuse_tail.py` 가 두 경우를 모두 고정한다.

## 대회 규칙 경계

- **공개 dev 자료만 보낸다.** 비공개 평가 입력을 넣으면 [R17](rules.md) 즉시 실격이다.
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
