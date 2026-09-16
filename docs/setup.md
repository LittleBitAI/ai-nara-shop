# Claude·Codex 설정

Claude와 Codex는 같은 권한·역할·작업 절차를 따릅니다. 작업 방법은 공용 위키,
프로젝트 규칙은 [workflow.md](workflow.md)를 비롯한 이 저장소의 `docs/`가 소유합니다.
구현자·리뷰어는 받은 작업으로 정하며 모델 이름으로 나누지 않습니다.

## 팀이 받는 것과 고정 버전

별도 공용 위키 checkout의 `tool/setup_agents.py`가 환경·버전·호스트 검사와 설치를 담당합니다.
프로젝트의 작은 진입점은 현재 checkout과 옵션을 공용 도구에 전달합니다.
submodule·패키지 배포·공용 hook 사본은 만들지 않습니다.

- 위키 저장소: [ai-coding-agent-wiki-public](https://github.com/LittleBitAI/ai-coding-agent-wiki-public).
- 위키 기준 커밋: `428a85d8e563f6d07e2a033b695474466f782b52`.
  기계가 읽는 기준은 [.wiki/wiki-revision](../.wiki/wiki-revision)입니다.
  설치 도구는 HEAD와 실행 코드·규칙의 미커밋 변경을 확인합니다.
  이 SHA는 공용 설치 도구와 checkout-local adapter 지원을 포함합니다.
  일반 설치에는 `--allow-dirty-wiki`가 필요하지 않습니다.
- 프로젝트 설치 도구는 [tools/setup_agents.py](../tools/setup_agents.py)입니다.
  `AGENTS.md` → `docs/`, Claude의 `CLAUDE.md` → `@AGENTS.md` 연결을 그대로 사용합니다.
- `.wiki/adapter.toml`은 프로젝트 슬롯 원본, `.wiki/project.md`와 `.wiki/plan-active.md`는
  짧은 규칙·문서 포인터입니다. 공용 코드·정책은 외부 checkout에서 읽습니다.
- 2026-09-16 사용자가 프로젝트 공개 push를 지시했습니다. 공개 대상은
  `https://github.com/LittleBitAI/ai-nara-shop`의 `main` 소스 스냅샷입니다.
  대용량 무라벨 공고 파일은 대회 배포본에서 별도로 받습니다([공개 작업 기록](tasks/public-push.md)).
- 2026-09-16 종료 전 사용자 지시로 공개 위키에 연결했습니다. 아래 두 URL을 사용합니다.
  공통 규칙은 공개 위키, 이 프로젝트의 작업·결정 이력은 프로젝트 `.wiki/decisions/`·`docs/tasks/`에 둡니다.
  [위키 유지보수 기록](tasks/wiki-maintenance.md)을 참조하세요.
  기존 미커밋 변경은 보존합니다. 테스트는 고정 SHA의 깨끗한 임시 clone을 사용하며,
  기존 허브 adapter·사용자 설정·실제 프로젝트 hook 파일을 쓰지 않습니다.

## 처음 받기 → 환경 준비

아래는 PowerShell 예입니다. 두 공개 저장소의 URL을 지정합니다.
이미 받은 저장소가 있으면 clone 단계를 건너뜁니다. 두 저장소의 폴더명은 자유이며 공백·한글도 지원합니다.
아래 폴더명은 예시입니다. 설치 때 `--wiki`로 실제 위키 checkout을 지정합니다.

```powershell
$env:SHOP_REPO_URL = 'https://github.com/LittleBitAI/ai-nara-shop.git'
$env:WIKI_REPO_URL = 'https://github.com/LittleBitAI/ai-coding-agent-wiki-public.git'
git clone -- "$env:SHOP_REPO_URL" ai-nara-shop
git clone -- "$env:WIKI_REPO_URL" ai-coding-agent-wiki-public
cd ai-nara-shop
$revision = (Get-Content -Raw -Encoding UTF8 .wiki/wiki-revision).Trim()
git -C ../ai-coding-agent-wiki-public checkout --detach $revision
```

checkout은 새로 받은 위키에서 수행합니다. 다른 작업에 쓰던 위키가 dirty이거나 버전이 다르면
작업을 버리지 말고 팀용 checkout을 별도로 준비합니다. 자동 pull·reset은 없습니다.

필수 환경은 Git, **Python 3.11 이상 + PyYAML**, 사용할 호스트의 CLI입니다.
Python 자체가 없으면 설치 스크립트도 실행할 수 없으므로 먼저 [Python](https://www.python.org/downloads/)을 준비합니다.
프로젝트 가상환경을 권장하며 대회 모델의 `requirements`를 설치할 필요는 없습니다.

```powershell
python --version
python -m venv .venv
.venv/Scripts/python.exe -m pip install PyYAML
.venv/Scripts/python.exe -c "import yaml, tomllib"
```

macOS/Linux에서는 `python3 -m venv .venv`와 `.venv/bin/python`을 사용합니다.
설치 도구는 실행 중인 Python의 절대 경로를 hook에 저장하므로 이후에도 이 환경을 유지합니다.
다운로드와 패키지 설치는 위의 명시적 준비 명령으로만 수행하며 설치 도구가 자동으로 하지는 않습니다.

호스트 준비:

- Claude Code: [공식 설치 안내](https://code.claude.com/docs/en/setup) 후 `claude --version`.
  현재 위키의 Windows Claude 명령은 Git Bash 형식입니다. **이 위키 조합에는 Git for Windows의 Git Bash가 필요**합니다.
  Claude 자체는 PowerShell만으로도 실행 가능하지만 위키의 명령 형식은 별개입니다.
  Git Bash를 찾지 못하면 `CLAUDE_CODE_GIT_BASH_PATH`를 실제 `bash.exe`로 지정하고
  같은 환경에서 설치와 Claude를 실행합니다. WSL의 `bash.exe`를 지정하지 않습니다.
- Codex: [공식 CLI 안내](https://learn.chatgpt.com/docs/cli) 후 `codex --version`, `codex features list`.
  Windows hook에는 PowerShell이 필요합니다. 지원 여부는 아래 실험 기능 절을 따릅니다.
- WSL을 사용한다면 Git·Python·위키·호스트를 모두 WSL 안에서 설치하고 실행합니다.
  Windows용으로 생성한 hook 경로를 그대로 WSL에 가져가지 않습니다.

## 한 명령으로 설치

공용화를 포함한 고정 SHA를 받은 뒤 프로젝트 루트에서 사용할 호스트의 명령 **하나**를 실행합니다.
`--wiki`는 필수이며 폴더명으로 위키 위치를 추측하지 않습니다.

```powershell
# Claude 사용자
.venv/Scripts/python.exe tools/setup_agents.py --wiki ../ai-coding-agent-wiki-public --agent claude

# Codex 사용자
.venv/Scripts/python.exe tools/setup_agents.py --wiki ../ai-coding-agent-wiki-public --agent codex

# 두 도구를 모두 사용
.venv/Scripts/python.exe tools/setup_agents.py --wiki ../ai-coding-agent-wiki-public --agent both
```

다른 위치의 위키는 `--wiki`로 지정합니다. 다음의 경로는 예시이며 자기 checkout으로 바꿉니다.

```powershell
.venv/Scripts/python.exe tools/setup_agents.py --agent both --wiki "D:/팀 작업/ai-coding-agent-wiki-public"
```

도구는 버전·의존성·CLI·셸을 확인하고 해당 checkout의 `.wiki/adapter.toml`을 직접 읽어,
선택한 호스트의 기존 `apply.py --write`와 `apply.py --check`를 호출합니다.
성공은 **종료 코드 0**, 실패는 **2**입니다. PowerShell에서는 `$LASTEXITCODE`로 확인합니다.
변경 없이 검사하려면 같은 명령에 `--check`를 붙입니다.

adapter는 허브에 복사하지 않습니다. 다른 프로젝트·동명 checkout과 슬롯을 공유하지 않습니다.
로컬 adapter가 있으면 과거 허브 adapter보다 우선하며, 파싱 실패 시 과거 값으로 우회하지 않습니다.
선택하거나 이미 설치한 호스트는 `.wiki/installed-agents.json`에 기록합니다.
이 PC별 기록은 Git에서 제외하며 공유 adapter의 `agents`·슬롯은 바꾸지 않습니다.
설정 전체가 없어져도 이 기록을 통해 검진이 누락을 찾습니다.
나중에 다른 호스트를 추가해도 앞서 설치한 hook은 남습니다. 이 명령은 제거 도구가 아닙니다.

기존 설정 병합은 공용 `apply.py`가 담당합니다. 선택하지 않은 호스트 설정, 사용자 `CODEX_HOME`,
사용자 Claude 설정, 다른 프로젝트는 쓰지 않습니다. 처리 중 실패하면 이번 명령이 쓰는 설치 호스트 목록·hook 파일을
실행 전 바이트로 되돌립니다. 같은 파일을 다른 세션에서 수정하는 중에는 설치하지 않습니다.
프로세스 강제 종료·전원 차단까지 복구하는 트랜잭션은 아니므로 그 경우 diff를 확인하고 재실행합니다.

기계별 결과인 `.claude/settings.json`, `.codex/hooks.json`, `.wiki/*.json(l)`은 Git에서 제외합니다.
과거 초안이 허브에 내보낸 adapter는 이 설치에서 사용하거나 덮어쓰거나 삭제하지 않습니다.
`.codex/config.toml`은 개인 경로가 없는 공통 기능 설정이며 설치 도구가 덮어쓰지 않습니다.

다른 프로젝트에서도 공용 진입점을 직접 사용할 수 있습니다. 프로젝트에는 `.wiki/adapter.toml`,
`.wiki/wiki-revision`과 사용할 호스트의 공통 설정을 준비합니다.

```powershell
python "D:/팀 도구/wiki/tool/setup_agents.py" --project "D:/팀 작업/프로젝트" --agent both
```

미커밋 공용화 개발 검증에만 `--allow-dirty-wiki`를 붙입니다. 이 옵션은 위키 실행 코드의 dirty 검사만
완화하며 HEAD와 `.wiki/wiki-revision` 일치는 계속 요구합니다. 출력에도 개발 검증임을 표시합니다.
팀 설치 성공이나 배포 버전 검증으로 기록하지 않습니다.

```powershell
python tools/setup_agents.py --wiki ../ai-coding-agent-wiki-public --agent both --allow-dirty-wiki
python tools/setup_agents.py --wiki ../ai-coding-agent-wiki-public --agent both --allow-dirty-wiki --check
```

## 새 세션과 신뢰

설치 성공은 설정 배선의 증거입니다. **호스트 자동 이벤트·실제 선택형 질문 UI 성공은 아닙니다.**

Claude 사용자:

1. 프로젝트 루트에서 `claude`로 대화형 세션을 시작합니다.
2. 폴더 경로·코드를 검토한 뒤 표시되는 workspace trust 대화상자에서 직접 신뢰를 선택합니다.
3. `/hooks`에서 네 이벤트(`SessionStart`, `UserPromptSubmit`, `PreToolUse`, `Stop`)의
   위키 명령과 자신의 기존 hook이 함께 있는지 확인합니다. 이 기준 위키의 Claude hook은 6개입니다.
4. 설정을 바꿨다면 세션을 종료하고 새로 시작한 뒤 아래 이벤트 확인을 수행합니다.

Claude의 대화형 workspace trust 전에는 hook이 보류됩니다.
[공식 hook 신뢰 설명](https://code.claude.com/docs/en/hooks#workspace-trust)을 따르며,
비대화형 `claude -p` 실행으로 신뢰 절차를 대체하지 않습니다.

Codex 사용자:

1. 프로젝트 루트에서 `codex`를 시작하고 프로젝트 신뢰 질문의 경로를 확인한 뒤 직접 신뢰합니다.
2. 프로젝트 설정을 계속 건너뛴다면 현재 호스트의 사용자 `config.toml`에서 해당 프로젝트 항목을 확인합니다.
   직접 검토할 설정은 `[projects.'<절대 프로젝트 경로>']` 아래 `trust_level = "trusted"`입니다.
   기존 항목을 수정하며 중복 표를 만들지 않습니다. `CODEX_HOME`이 있으면 그 호스트의 설정 위치를 사용합니다.
   이 개인 경로를 프로젝트 저장소에 커밋하지 않습니다.
3. `/hooks`를 열어 네 이벤트의 위키 hook 5개를 검토하고 직접 신뢰합니다.
   다른 사용자·플러그인 hook을 비활성화하거나 초기화하지 않습니다.
4. 신뢰 후 완전히 새 세션을 시작해 `SessionStart`부터 확인합니다.
   hook 명령이 바뀌면 `/hooks`에서 다시 검토합니다.

프로젝트 신뢰와 hook 정의의 신뢰는 별개입니다.
[Codex hook 정책](https://learn.chatgpt.com/docs/hooks#review-and-trust-hooks),
[프로젝트 설정 신뢰](https://learn.chatgpt.com/docs/config-file/config-reference)를 참고합니다.
도구는 신뢰 hash나 사용자 설정을 자동으로 쓰지 않으며 신뢰 우회 옵션을 사용하지 않습니다.

## 실제 동작 확인

새 세션에서 “프로젝트 작업을 진행하기 전에 적용된 규칙과 문서 포인터를 확인해 주세요”라고 입력합니다.

- 호스트의 세션·hook 출력에서 `SessionStart`의 문서 목록과 `docs/tasks.md`·`docs/roadmap.md` 포인터를 확인합니다.
- 발화 주입 결과에 `.wiki/project`, `docs/workflow.md`, “두 역할 모두 Claude 또는 Codex” 계약이 있는지 확인합니다.
- `.wiki/trajectory.jsonl`의 새 줄을 실제 세션 ID·발화·시각과 대조합니다.
  이 파일은 주입기 호출 기록일 뿐 실행 주체를 식별하지 않습니다. 수동 호출·화면용 재생만으로 자동 이벤트를 증명하지 않습니다.
- `git status` 같은 읽기 전용 작업에서 PreToolUse가 전달됐는지 호스트 실행 기록을 확인합니다.
  파괴적 명령을 시험 삼아 실행하지 않습니다.
- 종료 시 Stop hook의 실행 기록과 `.wiki/corpus.json`의 문서 목록을 확인합니다.
  sync는 갱신 간격이 있으므로 매번 파일이 바뀌어야 하는 것은 아닙니다.
- 질문 UI는 별도로 확인합니다. Claude는 `AskUserQuestion`, Codex는 실제 세션에 제공된
  `request_user_input`으로 선택지를 요청하고 화면에서 직접 골라 봅니다.

호스트 로그에 해당 이벤트 전달이 없거나 주입문이 비어 있으면 자동 실행 확인을 완료로 표시하지 않습니다.
AI가 “규칙을 읽었다”고 답한 것만으로도 충분하지 않습니다.

## Codex 실험 기능과 호스트 차이

프로젝트 공통 설정은 다음과 같습니다.

```toml
[features]
hooks = true
default_mode_request_user_input = true
```

2026-09-16 로컬 **Codex CLI 0.154.0**에서 프로젝트 루트의 `codex features list`는
`hooks stable true`, `default_mode_request_user_input under development true`를 출력했습니다.
후자는 개발 중 기능이며 현재 [공식 설정 참조](https://learn.chatgpt.com/docs/config-file/config-reference)에
안정된 지원 계약으로 나와 있지 않습니다. CLI 목록·설정 값은 UI 성공을 증명하지 않습니다.

이번 2026-09-16 세션에서는 **첫 도구 호출을 `functions.request_user_input`으로 실행했고**,
Default 모드에서 두 선택지 중 “설치 도구까지 공용화” 응답이 반환됐습니다.
이는 이 세션의 실제 동기 질문 호출·선택 반환 증거입니다. 모든 팀원 PC·호스트의 UI나 키 동작을 증명하지 않습니다.

설치 도구는 hooks 기능이 없는 CLI에서는 실패합니다. 질문 플래그가 없거나 Default mode에서 도구가 제공되지 않으면
현재 호스트 명세에 따라 지원되는 Plan mode로 전환하거나 **텍스트 선택지**로 질문합니다.
IDE·앱·Orca 등 별도 호스트에는 같은 CLI 기능이 노출된다고 보장하지 않습니다.
위키는 `request_user_input_async`와 `functions.request_user_input_async` 호출을 차단합니다.
이 도구로 우회하지 않으며 무응답을 승인으로 해석하지 않습니다.

권한·작업 절차는 같지만 기술적 차단 범위가 완전히 같은 것은 아닙니다.
Claude는 permissions.deny와 한국어·diff hooks를 사용하고,
Codex는 `codex_pretool.py`의 지원 도구명·직접 명령 패턴을 검사합니다.
이는 Claude permissions 전체의 이식이나 완전한 보안 경계가 아닙니다.

## 업데이트·이동·흔한 실패

위키를 갱신할 때 관리자는 후보 커밋의 설치 검증을 별도 checkout에서 수행하고,
통과한 SHA로 `.wiki/wiki-revision`과 이 안내의 검증 기록을 함께 갱신합니다.
미검증 HEAD나 브랜치 최신값을 자동으로 받아 쓰지 않습니다.
팀원은 변경된 프로젝트 파일과 해당 위키 커밋을 받은 뒤 같은 설치 명령을 다시 실행합니다.

프로젝트 폴더명·위키 위치·Python 환경이 바뀌면 새 경로·Python으로 재설치하고 `--check` 후 새 세션에서 신뢰를 검토합니다.
이동 후에는 설치되어 있던 모든 호스트를 다시 설치합니다. 둘 다 사용했다면 `--agent both`를 사용합니다.
폴더 이름이 같은 별도 checkout도 각각 설치합니다. 각자의 adapter와 설치 호스트 기록을 읽으므로 서로 덮어쓰지 않습니다.
공용 코드를 절대 경로로 읽으므로 같은 위치의 위키 내용을 바꾸면 hook 신뢰 hash가 바뀌지 않아도 행동은 바뀔 수 있습니다.
다른 프로젝트가 쓰는 checkout은 그대로 두고 팀용 새 checkout을 지정하는 방식이 가장 단순합니다.

| 실패 | 해결 |
| --- | --- |
| Python 명령 없음·3.11 미만 | Python 준비 후 새 가상환경의 실행파일로 재실행 |
| `PyYAML` 없음 | 같은 가상환경의 `python -m pip install PyYAML`; 전역 설치 불필요 |
| 공용 설치 도구 없음 | `--wiki`가 공용화 변경을 포함한 checkout인지 확인 |
| 버전 불일치·실행 코드 dirty | 기존 변경을 보존하고 고정 커밋의 별도 checkout 사용 |
| adapter 슬롯 누락 | 해당 checkout의 `.wiki/adapter.toml` 수정 후 재설치; 허브 사본 불필요 |
| JSON/TOML 파싱 오류 | 메시지의 파일을 직접 수정; 초기화·전체 덮어쓰기 금지 |
| CLI·Git Bash·PowerShell 없음 | 해당 공식 도구를 준비하고 PATH·Git Bash 경로 확인 |
| 배선 검사 실패·제한 matcher | 출력의 기존 hook 설정을 검토; 설치 도구는 실패 시 원래 설정으로 복구 |
| 배선은 통과, 자동 주입 없음 | 프로젝트 신뢰·hook 신뢰·disableAllHooks·관리자 정책·호스트 지원·새 세션 확인 |
| 선택형 질문 도구 없음 | 지원 Plan mode 또는 텍스트 선택지. 실제 UI 성공으로 표시하지 않음 |
| 경로에 `$`·백틱·큰따옴표·줄바꿈 | 현재 위키의 셸 인용 지원 밖이므로 해당 문자 없는 경로 사용 |

## 팀원 완료 체크리스트

- [ ] 확인된 내부 URL에서 두 저장소와 고정 커밋을 받을 수 있다.
- [ ] Python·PyYAML·선택한 호스트 CLI·필요한 셸이 준비됐다.
- [ ] 설치 명령과 같은 옵션의 `--check`가 종료 코드 0이다.
- [ ] 기존 hook·사용자 설정이 보존됐고 기계별 결과가 Git 변경에 포함되지 않는다.
- [ ] 새 세션에서 프로젝트와 hooks를 직접 검토·신뢰했다.
- [ ] 네 이벤트의 실제 호스트 실행과 프로젝트 규칙·문서 포인터 주입을 확인했다.
- [ ] 선택형 질문 UI를 실제 확인했거나 사용한 대체 방법·호스트 제한을 기록했다.

설치 검사만 통과하면 셋째 항목까지의 근거입니다. 이후 항목을 자동 완료로 간주하지 않습니다.

## 재현 가능한 설치 검사

현재 공개 위키 고정 SHA의 설치 검사는 [종료 전 위키 검진](tasks/wiki-maintenance.md)의 결과를 따른다.
아래 2026-09-16 `15fc1fd` 수치는 공개본 전환 전 개인용 위키의 역사 기록이다.

```powershell
# 표준 라이브러리 테스트 러너. 고정 SHA의 임시 clone과 격리한 사용자 설정을 사용한다.
.venv/Scripts/python.exe tests/test_setup_agents.py --wiki ../ai-coding-agent-wiki-public

# 위키의 기존 검사를 그대로 재사용 (테스트 환경에 pytest가 있을 때)
python -X utf8 ../ai-coding-agent-wiki-public/tool/test_apply.py
python -X utf8 -m pytest -q ../ai-coding-agent-wiki-public/tool/test_codex_hooks.py
```

첫 검사는 `--allow-dirty-wiki` 없이 고정 커밋을 검사하며, 임시 실행 코드 변경을 심어 일반 설치가 거부하는지도 확인합니다.
두 CLI가 모두 설치된 Windows 환경에서 실행합니다.
Claude 명령은 Git Bash, Codex 명령은 PowerShell로 직접 실행하며 유료 세션·모델은 호출하지 않습니다.
각 팀원의 자동 이벤트와 macOS/Linux/WSL 호스트 동작은 별도 미검증입니다.
검사 범위·최종 결과는 [tasks.md의 team-setup](tasks.md#첫-작업-큐)에 기록합니다.

2026-09-16 최종 작업본 검사: 설치 시나리오 2개 OK (62.667초), 공용 게이트와 로컬 adapter 검사
13개 명령 통과 (7.43초), Codex 훅 회귀 검사 13 passed (23.27초).
설치·재설치·기존 설정 보존·폴더 이동·동명 checkout 격리·공백/한글 경로·실패 복구를 포함합니다.

로컬 커밋 후 위키 `15fc1fd`의 깨끗한 임시 clone에서도 같은 설치 시나리오 2개가 OK (57.521초)였습니다.
이 검사는 작업본 복사와 `--allow-dirty-wiki` 없이 수행했으며 현재 `.wiki/wiki-revision`의 검증 근거입니다.

처음 연결할 때 census는 이 프로젝트의 Claude 세션 로그가 없어 측정하지 못했습니다.
효과 개선 수치는 로그가 쌓인 뒤 측정합니다. sync의 개발 기록은 대회 제출물에 포함하지 않습니다.

## 기존 PC 설치의 검증 기록 (2026-09-16)

| 확인 | 결과 | 증명의 범위 |
| --- | --- | --- |
| Python | 로컬 Anaconda Python의 yaml·tomllib import 성공 | hook 인터프리터 준비 |
| Codex feature 목록 | hooks=true, default_mode_request_user_input=true | 프로젝트 설정의 유효 값 |
| 설치된 hook 직접 실행 | Claude 6개, Codex 5개 성공 | JSON 입력→명령 실행→출력·문서 주입·sync |
| Codex 질문 도구 검사 | async deny, sync allow | 가상 PreToolUse 입력에 대한 응답; 실제 UI 아님 |
| 위키 기존 통합 테스트 | `tool/test_codex_hooks.py`: 13 passed | 위키 구현의 설치·주입·차단·허용·갱신 회귀 검사 |
| 베이스라인 mock | 10건, 49열, 자가검증 PASS | 입출력만; 실제 모델 미실행 |

직접 실행 기록의 session ID는 `manual-setup-*`입니다. 자동 실행의 증거로 세지 않습니다.
실제 호스트의 새 세션·`/hooks` 신뢰 후 이벤트 전달은 아직 확인하지 않았습니다.
선택형 질문은 위의 이번 세션 기록으로 구분하며, 과거 직접 hook 실행 검사의 성공으로 간주하지 않습니다.
허브 lint는 설치 전 기존 프로젝트들 사이의 슬롯 값 차이 4건을 보고했습니다.
서로 다른 게이트·live 명령·종료 방법·임시 경로를 같게 만들지 않았습니다.

## 공개 위키 전환 검사 (2026-09-16 종료 전)

현재 고정 SHA `428a85d`의 임시 clone 설치 검사 2 tests OK (76.565초).
이 PC의 두 호스트 설치·읽기 전용 check도 통과했고 모든 훅 명령이 공개 checkout을 가리킨다.
hub lint·프로젝트 repo_lint 발견 0건, 문서 목록 20개·고립 0개다.
[세부 검사와 공유 기록](tasks/wiki-maintenance.md)을 따른다.
이전 개인용 버전 `15fc1fd` 검사와 구분하며 변경된 훅의 새 세션 신뢰는 각 사용자가 수행한다.
