# AI 작업서

역할·AI 종류와 관계없이 같은 양식을 사용합니다. 모델은 맡은 작업의 허용 경로만 수정합니다.
하위 작업을 만들 때 아래 4칸을 빠뜨리지 않습니다. 한 파일을 두 오너가 동시에 수정하지 않습니다.

## 복사할 요청서

```text
작업 ID / 제목:
담당 역할 / 담당자:
상태: ready | in_progress | review | done | blocked
목표와 가설:
읽을 문서 / 보호할 규칙 ID:
규칙 판단: 작업 단계 / 활용할 A-ID / 지킬 R-ID·조건 / 불명확한 부분만 Q-ID
입력: 실제 파일·필드·버전
출력: 실제 파일·필드·실패 처리
수정 범위: 수정해도 되는 파일 경로 (관련 테스트·기록 경로 포함)
통과 조건: 실행 명령과 확인할 결과
선행 작업:
현재 기준선:
결과: 변경 / 실행한 검증 / 미실행·위험 / 다음 작업
```

새 작업 기록은 `docs/tasks/<id>-<topic>.md`에 생성합니다.
여기 표는 작업 큐이고, 수치·세부 실행 기록은 해당 작업서나 `reports/<run-id>/`가 소유합니다.
`blocked`에는 막힌 단계만 적고 독립된 작업은 진행합니다.

## 첫 작업 큐

`team-handoff`: 4명 기준 업무 분배 문서 작성.
- 공개 요청: 계획·분석 자료를 커밋/PR/머지하고 프로젝트 위키에서 현재 계획 질의와 세션 시작에
  최신 목표·담당·48시간 기준이 주입되는지 직접 검사한다. 추가 범위: `.wiki/project.md`, 위키 검사 기록.
  허브 공통 위키 코드는 변경하지 않는다. 머지 후 브랜치·스크래치를 확인하고 필요한 산출물은 보존한다.
- 후속 요청: 최신 dev 24항목·과거 실행·실제 오답을 집계해 점수 개선 중심의 연속 작업으로 재작성.
  추가 수정 범위는 `reports/team-score-audit/`와 `.wiki/plan-active.md`.
  통과 조건은 CSV 재채점 일치, 사례 원문 위치 대조, 수치에 연결된 담당·후속 순서·중단/채택 조건이다.
- 최신 요청 반영: 9/24 0.60 도전 일정, 48시간 0점 항목 TP 회복 점검, v20의 C 이관,
  C3·D1 우선 실행과 실패 단계별 후속 판단을 문서화하고 실제 과거 기록으로 점검 기준을 확인한다.
- 입력: `693c695` 코드·T1 실행 기록·현재 규칙, 사용자 지정 Opus 5 medium 개발 환경.
- 출력: [4인 업무 분배와 인수인계](tasks/team-handoff.md). 본인 포함 4명 기준이며 실명은 미배정.
- 수정 범위: 이 작업 큐, `docs/README.md`, `docs/tasks/team-handoff.md`.
- 통과 조건: 4명별 입력·출력·수정 범위·완료 조건·복사할 지시문, 파일 소유권·선행 관계,
  실제 검증과 미검증 구분, 로컬 링크·UTF-8 without BOM·LF 확인. 사람에게 배정·전송한 상태는 아님.
- 결과: 실제 6회 CSV의 24항목 재채점 일치, 최신 11항목 F1=0·부재탐지 FN=31·집중 오탐을 근거로 재작성.
  B/C/D에게 24항목을 중복 없이 배정하고 후속 티켓·구현 범위·통합·중단/채택 조건을 명시했다.
  `reports/team-score-audit/`에 수치·실행 이력·사례 원문 위치를 보존했다. 업무 자체의 구현·실제 실행은 후속이다.
  분석 확인: 24항목 배정·19개 티켓, 사례 원문 위치 12곳 대조 통과.
  공개 전 확인: 현재 계획·팀원 업무·다음 작업 질의 3개와 SessionStart 직접 실행에서
  0.60 목표·C3/D1·상세 작업서가 주입됐다. 머지 질의에는 정리 규칙이 주입됐다.
  위키 동기화·repo_lint 새 발견 없음. [직접 실행 기록](../reports/team-score-audit/wiki-checks.json) 참조.
  문서 인코딩·링크·diff 검사 통과. 자동 호스트 이벤트 전체와 팀원 PC 검증으로 확대하지 않는다.

`wiki-maintenance`: done. 종료 전 위키 검진·공개본 연결과 결정 기록 보완.
현재 연결·검사·공유 범위는 [위키 유지보수 기록](tasks/wiki-maintenance.md)을 따른다.

`public-push`: 사용자 지시로 하위 작업 공간 정리 및 공개 GitHub push.
입력·수정 범위·결과는 [공개 작업 기록](tasks/public-push.md)을 따른다.

`run-archive`: 결과 ZIP을 사람마다 전달하는 경로를 없애고 `git pull` 하나로 실행 기록을 받게 한다.
- 입력: 사용자가 전달한 `colab-results-1789621345861123113.zip`
  (SHA-256 `335796bce22ccdae6cf90e2da550a5c3575ed23feb1189b5f40e157b6c2feec8`, 기준 코드 `654c556`),
  `reports/team-score-audit/history.json`의 6회 기록.
- 출력: [실행 기록 색인과 보관 규약](runs.md), `reports/runs/colab-1789621345861123113/`,
  `.wiki/decisions/2026-09-17-013-docs-run-archive.md`.
- 수정 범위: `reports/runs/`, `docs/runs.md`, `docs/README.md`, 이 작업 큐,
  `.wiki/plan-active.md`, `.wiki/decisions/`. `script.py`·`tests`·`open/` 원본은 제외한다.
- 통과 조건: ZIP 해시·코드 커밋 일치, 추가 파일의 비밀정보 패턴·50MB 검사,
  `python -X utf8 -m unittest tests.test_baseline tests.test_package tests.test_score`,
  `git diff --check`, UTF-8 without BOM·LF·로컬 링크, 새 세션 문서 목록의 `docs/runs.md` 노출.
- 결과: 문서·기록 작업이며 모델 추론·재채점·서버 제출은 수행하지 않았다.
  수치는 실행이 남긴 파일과 `history.json`에서 옮겼고 다시 계산하지 않았다.
  세션 시작 문서 목록은 생성 색인 `.wiki/corpus.json`에서 나오므로 파일을 만든 직후에는 뜨지 않았다.
  공용 위키 `tool/sync.py`를 돌려 색인을 갱신한 뒤 `runs.md — 실행 기록`으로 표시되는 것을 확인했다.
  corpus 도구 자체는 고치지 않았다.

설치 작업 `team-setup` — 상태: review (구현·임시 환경 검증 완료, 독립 리뷰 미실행).
- 2026-09-16 사용자 선택: 설치 도구까지 공용화. 공용 `tool/setup_agents.py`가 환경·버전·호스트를 검사하고
  프로젝트 진입점은 위임만 한다. adapter는 각 checkout에서 직접 읽으며 허브에 복사하지 않는다.
- 추가 수정 범위: 공용 위키 `tool/setup_agents.py`, adapter를 읽는 설치·주입·감사·그래프 코드와 관련 테스트,
  공용 `README.md`, 프로젝트 설치 테스트·안내·작업 기록. 폴더명 변경·동명 checkout 격리를 통과 조건에 추가한다.
- 입력: 양쪽 저장소의 규칙·설치 기록, 프로젝트 adapter, 공용 `tool/apply.py`, 설치된 Claude/Codex와 공식 지원 문서.
- 출력: 프로젝트 설치 진입점, 고정 위키 버전, 임시 환경 검증, `docs/setup.md`의 팀 설치·신뢰·확인 안내.
- 수정 범위: `tools/setup_agents.py`, `tests/test_setup_agents.py`, `.wiki/adapter.toml`, `.wiki/wiki-revision`,
  `.gitignore`, `.codex/config.toml`, `docs/setup.md`, `docs/README.md`, 이 작업 기록.
  공용 위키 수정 범위는 위 사용자 선택에 따라 설치 공용화와 checkout-local adapter의 호출자까지 포함한다.
  리뷰 요청 기록은 `artifacts/review/team-setup-request.md`에 둔다.
- 통과 조건: 임시 환경에서 Claude/Codex/둘 다 설치·재설치·사용자 설정 보존·공백/한글 경로·오류 종료·생성 명령 실행·프로젝트 포인터 주입 확인.
  UTF-8 without BOM·LF·Git 제외를 검사한다. 자동 호스트 이벤트와 실제 질문 UI는 별도 증거 없으면 미검증으로 남긴다.
- 기준선: 프로젝트 `4816cf66f93f7303061cf55be1d98ca02e9ac2b4` (clean),
  위키 `481917b5560c9bc9f98e04052afaa295d954255b` (기존 `.wiki/corpus.json`, `graph.json`, 미추적 `adapters/ai-nara-shop.toml` 보존).
  양쪽 remote 없음. 공유 URL·팀 접근 권한 미확정. T1~T8, 실제 모델, 유료 API, 배포·커밋·push 제외.
- 결과 (2026-09-16): 환경·버전·호스트 검사와 복구를 공용 `tool/setup_agents.py`로 옮겼다.
  프로젝트 진입점은 명시적 `--wiki`와 자기 checkout을 전달한다. `ADAPTER` 상수·형제 폴더 자동 탐색을 제거했다.
  기존 `apply.py`가 설정을 병합하며 주입·슬롯 예산·배선 검사·감사·그래프는 로컬 adapter를 읽는다.
  PC별 설치 호스트는 Git 제외 `.wiki/installed-agents.json`에 보존한다. 허브 adapter와 공유 슬롯은 쓰지 않는다.
- 실패 재현: `python -X utf8 tool/test_local_adapter.py`가 수정 전
  `TypeError: slots_for() takes 1 positional argument but 2 were given`으로 실패했고, 구현 후 통과했다.
- 최종 검증: `python -X utf8 tests/test_setup_agents.py --wiki ../ai-coding-agent-wiki` — 2 tests, 62.667초, OK.
  Claude/Codex/둘 다 설치·재설치·기존 설정/사용자 전역 설정 보존·읽기 전용 check·rollback·공백/한글 경로·
  폴더 이동·동명 checkout 슬롯 격리·생성 명령 직접 실행·문서 포인터·Git 제외를 검사했다.
  의존성 누락·잘못된 위키 경로·SHA 불일치·dirty 실행 코드·비활성 hooks·잘못된 adapter/JSON·지원 밖 경로는 실패했다.
  환경: Windows, Python 3.13.9, Claude Code 2.1.273, Codex CLI 0.154.0. 실제 유료 세션은 열지 않았다.
- 공용 검증: 선언된 위키 게이트와 새 로컬 adapter 검사 총 13개 명령 통과 (7.43초).
  `python -X utf8 -m pytest -q tool/test_codex_hooks.py` — 13 passed (23.27초).
  프로젝트 Ruff·diff 검사와 이번 수정 파일의 UTF-8 without BOM·LF 검사 통과.
  위키 전체 `git diff --check`의 기존 `graph.json` CRLF 공백 오류는 보존했고, 이번 수정 파일 범위는 통과했다.
  `lint --check`는 종료 코드 0이며 기존 슬롯 차이 4건은 의도된 보고다.
- 증거 경계: 설치 검사는 임시 clone 위의 미커밋 도구 작업본에 `--allow-dirty-wiki`를 명시했다.
  기본 설치가 dirty 코드를 거부하는 것도 확인했다. 이 최초 작업본 검사는 배포 버전 검증이 아니다.
  실제 자동 호스트 이벤트 전달·다른 OS·팀원 PC·독립 리뷰는 미검증이다.
  이번 Default 세션 첫 `functions.request_user_input` 호출은 두 선택지를 받아 “설치 도구까지 공용화” 응답을 반환했다.
  이는 실제 동기 질문 호출의 증거이며 모든 호스트 UI·키 동작이나 hooks 자동 실행의 증거는 아니다.
- 커밋 후속: 사용자가 로컬 커밋을 요청했다. 위키 `15fc1fd110ee646563ebb415dc00a5e88fd188fa`를 만들고
  `.wiki/wiki-revision`에 고정했다. 테스트는 작업본 복사 없이 이 커밋의 임시 clone을 쓰도록 바꿨다.
  프로젝트 변경은 `chore/team-agent-setup` 브랜치에 기록한다. 기존 미커밋 자료는 제외한다.
- 고정 커밋 검증: 같은 설치 테스트 명령으로 2 tests OK (57.521초).
  작업본 복사·`--allow-dirty-wiki` 없이 위키 `15fc1fd`의 깨끗한 임시 clone을 설치했다.
  임시 실행 코드 변경을 심은 경우 기본 설치가 거부하는 것도 통과했다. Ruff·diff·UTF-8 without BOM·LF 검사 통과.
- 다음 작업: 내부 공유 경로를 확정하고 팀원은 새 세션에서 직접 신뢰·자동 이벤트·질문 UI를 확인한다.
  push·공개 배포·T1~T8 구현은 하지 않았다.

저장 작업 `initial-commit`: 사용자 요청으로 저장소 전체 변경을 첫 커밋에 기록합니다.
입력·범위는 기존 staged 자료와 미추적 작업 문서·설정 전체이며 `.gitignore` 제외 대상은 유지합니다.
출력은 `master`의 초기 커밋입니다. 보관본 바이트 보존을 위해 `.gitattributes`에 해당 경로의 변환 제외를 적용합니다.
통과 조건은 스테이징된 보관본 해시 일치, 신규 작업 문서 검사, 커밋 후 작업 트리 변경 없음입니다.
실제 커밋 결과는 Git 이력으로 확인합니다.

문서 작업 `contest-archive` — 상태: 완료.
- 입력: 기존 `대회/`의 4개 파일, 배포 README, 현재 작업 문서.
- 출력: 원문 없이 사용할 수 있는 주제별 작업 문서, 절별 통합 대응표, 별도 보관본.
- 수정 범위: `docs/`, `README.md`, `AGENTS.md`, `.wiki/project.md`, `대회/` → `archive/contest/` 이동 및 보관 색인.
- 통과 조건: 원문 각 절·FAQ의 작업 문서 대응 확인, 이동 전후 4개 파일 SHA-256 일치,
  작업 읽기 경로의 보관본 의존 제거, 로컬 링크·UTF-8 without BOM·LF·위키 검사 통과.
- 보관본은 원문 바이트를 보존하고, 새로 작성·수정하는 작업 문서는 UTF-8 without BOM·LF로 저장합니다.
- 결과: `contest.md`에 평가·운영·배경을 통합하고 `data.md`의 파일·관측성·익명화·실행 안내를 보완했습니다.
  규칙 원문 전체 절·데이터 명세 §1~§9와 FAQ 16개·배경 전체 절의 통합 위치를 `sources.md`에 기록했습니다.
  원본 4개는 해시 일치, 작업 문서 17개·로컬 링크/앵커 188개·A/R/Q ID·정상 dev 112건 검사를 통과했습니다.
  기본 읽기 경로에 보관본 의존이 없고, 위키 동기화 후 문서 15개·고립 문서 0개, `repo_lint` 새 발견 없음입니다.
  `git diff --check` 통과. 문서 재구성 작업으로 실제 모델·유료 API·대회 제출은 실행하지 않았습니다.

문서 작업 `rule-usage`: `대회/` 원문을 입력으로 규칙의 적용 시점·허용 활용법·조건·출처를 정리합니다.
수정 범위는 `docs/rules.md`, `docs/workflow.md`, `docs/README.md`, `docs/design.md`, `docs/sources.md`,
`.wiki/project.md`, 이 작업 기록입니다. 출력은 AI의 규칙 판단 절차와 작업서의 규칙 판단 칸입니다.
통과 조건은 원문과 허용·금지 범위 대조, 기존 R-ID 보존, 좁혀진 Q2의 관련 문서 일치,
로컬 링크·인코딩·위키 포인터 검사입니다. 상태: 완료.
결과: 원문과 허용·금지 조건을 대조하고 A1~A10·R1~R22·Q1~Q3의 누락·중복,
로컬 링크·앵커·UTF-8 without BOM·LF를 검사했습니다. `대회/`·`open/` 원본 변경 없음과 `git diff --check` 통과를 확인했습니다.

별도 문서 작업 `items`: 제공 항목표를 입력으로 `docs/items.md`의 24항목 색인을 작성합니다.
수정 범위는 `docs/items.md`, `AGENTS.md`, `README.md`, `docs/README.md`, `.wiki/project.md`, 이 작업 기록입니다.
통과 조건은 v1~v24 누락·중복 없음, 공식 항목명·조문·비고·부재탐지 일치, 문서 링크·UTF-8 without BOM·LF 검사입니다.
상태: 완료. Python 표준 라이브러리 검사로 24개 ID·공식 항목명·조문·비고·부재탐지를 원본과 대조했고,
진입점·로컬 링크·UTF-8 without BOM·LF 검사와 `git diff --check`를 통과했습니다.
상세 판정 명세와 실제 조문 위치를 검증한 매핑은 T3에서 별도로 작성합니다.

T2는 done(구현·로컬 검증 완료)입니다. 사용자 지시에 따라 별도 독립 리뷰는 진행하지 않습니다([실행 기록](tasks/t2-score.md)).
T1은 사용자 보고로 서버 제출 실패를 확인했습니다. 재시도 실패 경로와 상세 원인 누락을 재현했으며, 실제 서버 응답·종료 사유는 미확인입니다([작업서](tasks/t1-baseline.md#2026-09-17-서버-실패-진단)).
후속 요청의 진단 기록·[Colab 실행 노트북](colab.md)·번들 준비와 로컬 검사는 완료했습니다. HF_TOKEN 필수·서버 무인자 실행/설정 일치 검사를 추가했습니다. 실제 GPU 성공은 미확인이고, 이번 독립 리뷰는 사용자 지시로 생략합니다.
Colab 기본 준비 경로에 git clone·실제 커밋 기록·제출 ZIP 자동 생성을 추가합니다. 특정 로컬 번들 업로드는 선택 경로로 유지합니다.
사용자 Colab 실행은 다운로드 성공 후 ninja PATH 누락으로 초기화 실패했습니다. 실행 환경을 보완했으며
수정 후 실제 GPU 재검증은 남아 있습니다([진단 기록](../reports/t1-baseline/colab-ninja-failure.md)).
후속 결과: `1c64604`는 A100 40GB에서 샘플/dev 210건 실제 성공, F1 0.2208013652894021.
사용자가 실행 안정성과 성능 둘 다 개선하도록 선택했습니다. 실패 공고 분할 재시도와
v10·v11·v13 법령/품목 조회 파일럿을 구현·로컬 검증하며, 새 후보의 Colab 재실행은 남아 있습니다.
실제 후속 `9363f21` 결과는 210건 실행 성공, F1 0.18470988076251235로 하락했습니다.
사용자 지시로 전체 프롬프트 주입은 철회하고 기본 24항목 호출 + 별도 3항목 판정으로 분리합니다.
같은 실행에서 두 CSV를 비교하며 새 후보의 성능 개선·서버 성공은 아직 미확인입니다.
`40e2cc6` 실제 실행은 성공했지만 F1 0.219538로 과거 기준선 미달입니다. 사용자 승인으로
품목 적용 범위·서비스 조회 누락·자격 문구 구분을 보완했고 로컬 22개 검사를 통과했습니다.
새 후보의 실제 Colab 검증은 대기 중입니다([작업서](tasks/t1-baseline.md)).
후속 57c78cf도 F1 0.211008로 실패했습니다. 출력 잘림 3건의 실제 분할 복구는 성공했습니다.
사용자 요청으로 영어 지시·한국어 법적 용어와 3항목 사실 검증을 구현했고 로컬 24개 검사를 통과했습니다.
목표는 기존 다운로드 품질 기준의 실제 통과이며 임계값을 낮추지 않습니다.
T3~T8은 미착수입니다. live·비용·실제 제출은 해당 접근·예산·제출 권한 확보 후 수행합니다.

| ID / 오너 | 입력 | 출력 | 수정 범위 | 통과 조건·선행 |
| --- | --- | --- | --- | --- |
| T1 / 통합 | `open/baseline/`, 두 노트북, `open/data/`, 서버 평가 명세 | 결함 보완 제출 후보·모델 조사·실행 기록 | `script.py`, `requirements.txt`, `tests/test_baseline.py`, `tools/package.py`, `docs/tasks/t1-baseline.md`, `docs/gemma4.md`, `reports/t1-baseline/`, `artifacts/baseline/`; 상태·출처 문서는 작업서 참조 | mock 10건·dev 형식 및 ZIP 검사, live 정상 호출·총시간 기록, 서버 점수. 제공 원본 보존 |
| T2 / 실험 | `open/dev_labels.csv`, 같은 ID의 예측 CSV | 24항목 metrics·오답 목록 | `tools/score.py`, `tests/test_score.py`, `docs/tasks/t2-score.md`, `reports/` | 정답=예측이면 F1=1; 전부 0이면 F1=0; ID 누락·중복·추가·값 오류 거부; 행 순서가 달라도 ID로 대응 |
| T3 / 명세 | 항목표·제공 법령, v05·v10·v24 | 일반·부재·메타 불일치 명세 3개와 매핑 | `specs/v05.md`, `specs/v10.md`, `specs/v24.md`, `rules/law_map.json`, `docs/tasks/t3-specs.md` | C3의 7칸, 조문 출처, v24 해당 없음, 사람 검토 기록. 외부 API는 Q1 확인 전 사용 안 함 |
| T4 / 라벨 | dev 입력 200건·검토 기준, 생성 후 dev 정답 대조 | API 라벨 기준선·비용·검토 계획 | `tools/gen_label.py`, `tests/test_label.py`, `labels/`, `docs/tasks/t4-labels.md`, `reports/` | T2·예산 필요. 입력에서 정답 제외, 실패·중복·재개 검증, 항목별 결과·모델/프롬프트 기록; 2만 건 선실행 금지 |
| T5 / 프롬프트 | T3 승인 명세 1개 | 버전 연결된 지시문 1개 | `tools/gen_prompt.py`, `prompts/v05.md`, `tests/test_prompt.py`, `docs/tasks/t5-prompt.md` | 승인되지 않은 명세 거부, 조건·예외·근거 규약 유지; 초기에는 템플릿 변환 |
| T6 / 통합 | T1 검증본·D4 계약 | 공고별 독립 추론 모듈 경계 | `script.py`, `pipeline/run.py`, `pipeline/output.py`, `tests/test_output.py`, `docs/tasks/t6-runtime.md` | T1 후. 기존 입출력 보존, 호출 실패·CSV 오류가 성공 처리되지 않음, mock/live 구분 |
| T7 / 프롬프트 | T2 채점기·T3 매핑·T5 지시문·T6 호출부 | 직접 매핑 후보와 문서 선택 후보를 각각 비교 | `pipeline/input.py`, `pipeline/retrieve.py`, `pipeline/prompt.py`, `prompts/queries.json`, `tests/test_input.py`, `tests/test_retrieve.py`, `docs/tasks/t7-retrieval.md`, `reports/` | 한 번에 하나씩 실험; 실제 토크나이저 예산, 관련 첨부·관측성 보존, 항목별 점수·총시간 기록 |
| T8 / 통합·실험 | 채택 후보·승인 자산·생성 이력 | 검증된 ZIP·재현 안내·제출 기록 | `tools/package.py`, `tests/test_package.py`, `docs/tasks/t8-release.md`, `reports/release/`, `artifacts/release/` | R1~R22·D4 게이트, allowlist ZIP, 네트워크 없는 live 실행, hash·재현 명령 |

테스트 파일은 의미 있는 동작을 구현할 때 생성합니다. 위 경로는 허용 범위이며 빈 파일 생성 지시가 아닙니다.
명세를 24개로 확대하거나 라벨 20,000건을 실행할 때는 파일럿 결과를 근거로 별도 작업서를 만듭니다.

## 지금 팀원에게 전달할 예

```text
T2 dev 채점기를 구현해 주세요.
먼저 AGENTS.md, docs/workflow.md, docs/data.md의 D4·D5, docs/contracts.md의 C5를 읽으세요.
입력은 정답 CSV와 예측 CSV이며 id로 대응하세요.
출력은 Macro F1, 24항목별 TP/FP/FN·precision·recall·F1·support와 오답 목록입니다.
수정은 T2 행에 적힌 파일만 허용합니다. open/ 원본은 수정하지 마세요.
T2 통과 조건을 실패 테스트로 먼저 확인하고 최소 구현 후 결과를 기록하세요.
모델이나 유료 API를 호출할 필요는 없습니다.
```
