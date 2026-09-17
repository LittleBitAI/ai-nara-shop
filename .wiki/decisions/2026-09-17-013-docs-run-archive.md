---
scope: project
severity: preference
triggers: ["실행 기록", "run", "runs", "colab", "zip", "보관", "manifest", "재현"]
domain: 'run-archive'
title: "docs: 실행 결과 ZIP을 저장소에 풀어 보관하고 색인 한 장으로 연결"
branch: "docs/run-archive"
---

# docs: 실행 결과 ZIP을 저장소에 풀어 보관하고 색인 한 장으로 연결

무엇. 결과 ZIP을 사람마다 전달하던 경로를 없앴습니다. `reports/runs/<run-id>/`에 ZIP 내용을
텍스트로 풀어 넣고 `manifest.json`에 ZIP 해시·코드 커밋·GPU·입력 해시·로드/기본/추가/전체 시간·
실패와 선택 건수·원응답 포함 여부를 적습니다. 규약과 한 행 한 실행 색인은 `docs/runs.md`가
소유합니다. 첫 등록은 `colab-1789621345861123113`이며 `654c556`의 dev 200건 실행입니다.

왜. 이 실행은 `654c556` 코드가 A100 40GB에서 dev 200건을 완주해 Macro F1 0.2208을 냈다는 것만 증명하고 대회 서버 제출 성공이나 그 뒤 `693c695` 후보의 성능은 증명하지 않습니다.
정확한 값은 0.22078771129016228이며 sample 10건도 같은 실행에서 성공했습니다.
ZIP 바이너리를 커밋하지 않는 이유는 저장소가
공개이고 GitHub 파일 한도가 있기 때문이며, 같은 이유로 `open/train_unlabeled.jsonl`을 제외한
전례가 `reports/publication.json`에 있습니다. 원응답은 `debug_responses=false`로 실행해
애초에 로그에 없습니다. `diagnostics.jsonl`은 응답 길이·토큰 수·종료 사유만 남깁니다.
수치는 실행이 남긴 파일에서 옮겼고 다시 계산하지 않았습니다. 과거 5회는 점수만
`reports/team-score-audit/history.json`에 있어 색인에서 실행 환경·원응답을 `미보관`으로 둡니다.
검증: ZIP SHA-256 `335796bc…feec8` 일치, 코드 커밋 `654c556` 일치, 55개 파일 UTF-8 without BOM·LF,
최대 파일 210KB로 50MB 한도 아래, `tests.test_baseline`·`tests.test_package`·`tests.test_score` 통과.
`script.py`·`tests`·`open/`은 건드리지 않았습니다.

출처. `docs/runs.md` · `reports/runs/colab-1789621345861123113/manifest.json` · `docs/run-archive`
