---
scope: project
severity: contract
triggers: ["절대 경로", "개인 경로", "manifest", "산출물", "기록", "score.py", "portable", "cwd"]
domain: 'artifacts'
title: "fix: 커밋하는 산출물에 절대 경로를 남기지 않는다"
branch: "fix/portable-paths-in-records"
---

# fix: 커밋하는 산출물에 절대 경로를 남기지 않는다

무엇. `tools/score.py`가 manifest·result에 적던 경로를 저장소 기준 상대 경로로 바꿉니다.
저장소 밖이면 `<외부>/<파일명>`, 작업 폴더는 `.`, 인터프리터는 `python`입니다. 이미 커밋돼
있던 `reports/t2-self-check`·`t2-zero-check`·`t2-zero-shuffled`의 14줄에서 사용자 이름이 든
경로를 같은 형태로 지웠습니다. 규칙은 `docs/workflow.md` W3가 소유합니다.

왜. 이 경로는 보안 문제라기보다 위키가 그것을 사실로 읽어 다른 PC에서 그대로 따라 하는 것이 문제이며, 이 변경은 저장소가 만드는 기록만 고칠 뿐 실행 로그 원본에는 손대지 않습니다.
Colab 로그의 `/content/...`는 실행이 만든 바이트라 [실행 기록](../../docs/runs.md) 규약대로
그대로 둡니다. 남은 자리는 `script.py`의 `run_report.json`·`diagnostics.jsonl`이며 그 파일은
제출물이자 B 소유라 이번 범위에 넣지 않았습니다. 팀원이 자기 PC에서 돌리면 그 기록에는
여전히 개인 경로가 들어갑니다.

검증: 수정 전 `tools/score.py`를 그대로 돌려 manifest·result 양쪽에서 `C:/`가 잡히는 것을
재현했고, 수정 후 같은 검사에서 0건입니다. `tests/test_score.py`에 회귀 검사
`test_records_keep_no_absolute_path`를 넣어 절대 경로·인터프리터 경로가 나오면 실패합니다.
`tests.test_baseline`·`test_package`·`test_score` 28건 OK, Ruff 통과.
저장소 전수 재검사에서 남은 적중은 대회 데이터 `open/dev.jsonl`의 `\n` 이스케이프,
docker 볼륨 매핑, 보관한 Colab 로그의 컨테이너 경로뿐입니다.

출처. `docs/workflow.md` W3 · `tools/score.py` `portable()` · `tests/test_score.py`
