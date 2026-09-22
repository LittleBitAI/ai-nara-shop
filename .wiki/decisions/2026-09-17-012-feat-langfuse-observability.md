---
scope: project
severity: contract
triggers: ["langfuse", "관측", "트레이스", "span", "docker", "터널", "cloudflared"]
domain: 'observability'
title: "feat: separate local Langfuse stack with a diagnostics.jsonl sidecar"
pr: 12
merged: 2026-09-17
branch: "feat/langfuse-observability"
---

# feat: separate local Langfuse stack with a diagnostics.jsonl sidecar

무엇. 대회 실행을 실시간으로 보고 팀원도 같은 화면을 보도록 로컬 Langfuse v4 스택을
`docker/langfuse/` 에 따로 띄우고, `tools/langfuse_tail.py` 가 `diagnostics.jsonl` 을
따라 읽어 보낸다. `script.py` 는 고치지 않는다. 사용법은 `docs/langfuse.md` 가 소유한다.

왜 `script.py` 를 계측하지 않았나. 그 파일이 제출물 자체다. Langfuse 클라이언트가
거기 들어가면 R7(제출 추론의 외부 호출 금지)·R17(평가 데이터 외부 송신은 즉시 실격)에
걸리고, "검증한 ZIP 을 그대로 제출한다"는 Colab 규율도 깨진다. `script.py:851` 이
이벤트마다 `flush()` 하므로 옆에서 따라 읽는 것으로 실시간이 된다. 제출 ZIP 은
`tools/package.py` 의 `FILES` 에 따라 `script.py`·`requirements.txt` 둘뿐이라
이 도구가 섞일 수 없다.

왜 기존 스택을 재사용하지 않았나. 같은 기계의 `ai-companion-voice-agent` 스택
ClickHouse 에는 그 제품의 사용자 화면 모델 원문이 107,635건 있다. 이 저장소는
Colab 수집 때문에 터널로 밖에 열어야 하므로, 같은 인스턴스를 쓰면 그 원문이 팀원용
로그인 뒤에 놓인다. Langfuse 의 프로젝트 단위 역할은 유료(Enterprise) 기능이라
무료 셀프호스트에서 조직 멤버는 그 조직의 모든 프로젝트를 본다 — 프로젝트를 나누는
것으로는 못 막고 인스턴스를 갈라야 한다. compose 파일·비밀값 생성 규칙·운영 지식은
그 스택에서 그대로 들여왔고 고친 것은 포트뿐이다(project name `langfuse-nara`,
web 3002 · worker 3031 · clickhouse 8124/9002 · minio 9092/9093 · redis 6380).

지켜야 할 것. 이 인스턴스에 다른 프로젝트를 만들지 않는다. 팀원은 Member 또는
Viewer 로 초대하고 `LANGFUSE_INIT_USER_*` Owner 계정은 공유하지 않는다. 터널이 여는
것은 웹 3002 하나뿐이고 clickhouse·minio·redis 는 루프백에 남는다. 공개 dev 자료만
보낸다. `requirements.txt` 에 langfuse·opentelemetry 를 넣지 않는다.
`~/.wslconfig` 상한을 5500MB → 11000MB 로 올렸으며, 대회가 끝나 이 스택을 내리면
되돌린다(그 파일 주석에 과거 OOM 사고 기록과 함께 적었다).

분석 입력은 여전히 `diagnostics.jsonl` 이다. 이 스택은
`LANGFUSE_MIGRATION_V4_WRITE_MODE=events_only` 라 읽기 공개 API 가 404 이고 사람이
보는 길은 UI 뿐이다. Langfuse 는 그 파일을 대신하지 않는다.

검증(2026-09-17, 이 기계). 스택 6컨테이너 기동·health `4.27.0`, mock 6건의 진단을
사이드카로 보내 새 ClickHouse 에 span 12개 적재, 같은 시점 voice-agent 스택은
107,635건 그대로이고 대회 span 0건, 임시 터널로 외부 health 200·로그인 200 확인 후
닫으며 `NEXTAUTH_URL` 자동 복원. `tests/test_langfuse_tail.py` 3건과 Ruff 통과.
**실제 GPU·Colab 회차, `--follow` 의 실시간 추종, 팀원 계정 초대는 아직 안 했다.**

남은 한 줄. `script.py:579` 의 `debug_responses` 분기에 `prompt_text` 를 추가하면
5단계 진단의 "전달 문맥" 칸이 채워진다. `script.py` 는 B 소유이므로 그쪽에 넘긴다.

공개 범위. 저장소가 PUBLIC 이므로 공개된 파일에서는 다른 프로젝트 이름과 그 스택의
건수를 뺐다. 이 기록은 `.wiki/decisions/` 의 다른 파일들과 같이 로컬에만 둔다
(`docs/tasks/public-push.md` 의 "기존 미추적 결정 파일은 공개에 추가하지 않는다").

출처. PR #12 · `docs/langfuse.md` · `tools/langfuse_tail.py` · `tools/langfuse_local.py`
