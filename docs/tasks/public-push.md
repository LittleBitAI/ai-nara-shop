# 공개 push와 하위 작업 공간 정리

- 사용자 지시: 하위 에이전트 정리 후 공개 push. 2026-09-16.
- 입력: T1/T2 병합 코드·문서, Git 이력, Orca 작업 공간, GitHub 로그인.
- 출력: `LittleBitAI/ai-nara-shop` 공개 `main`, 로컬 원본/이력/검증 자산 보존.
- 수정 범위: `.gitignore`, `README.md`, `docs/setup.md`, `docs/tasks.md`, 이 문서,
  `reports/publication.json`, Git 원격·공개 main 브랜치·병합된 T1 작업 공간.
- 통과 조건: 하위 에이전트/작업 공간 확인, 공개 파일 비밀정보 패턴·용량 검사,
  공개 checkout의 베이스라인 검사·패키징, 원격 공개 여부·커밋 일치.
- 규칙 판단: 사용자 공개 권한으로 진행. R3·R10·R13·R17 유지, 비공개 평가 입력 미보유/미공개.

## 정리 결과

실행 중인 하위 에이전트는 없었다. T1 하위 작업 공간은 커밋·병합·clean을 확인하고
Orca CLI로 제거했다. 거기에 있던 터미널은 에이전트가 아닌 빈 PowerShell 셸이었다.
독립 리뷰 셀이나 다른 저장소의 세션을 종료하지 않았다.
토크나이저와 mock 출력은 Git 제외 `artifacts/t1-worktree-archive/`로 옮겨 보존했다.
제출 ZIP은 `artifacts/baseline/submit.zip`에 유지한다.

## 공개 범위

`open/train_unlabeled.jsonl`은 790,790,220 bytes이며 GitHub 일반 파일 한도를 넘는다.
이 파일과 이를 포함한 기존 커밋 이력은 공개 push하지 않는다. 기존 로컬 브랜치/이력과
데이터는 보존하고, 현재 추적 파일에서 이 파일만 제외한 새 `main` 스냅샷을 공개한다.
`.wiki/decisions/`의 기존 미추적 파일과 Git 제외 검증 자산·기계별 설정은 추가하지 않는다.
소스 기준 커밋과 제외 목록은 `reports/publication.json`에 기록한다.

공개 clone에서 베이스라인은 제공 샘플·항목표·스키마로 실행된다. 자가 라벨링 전에 대회
배포 무라벨 파일을 `open/train_unlabeled.jsonl`에 배치한다. 제공 데이터의 출처는 대회 배포본이다.
공용 위키의 원격은 별도 과제이며 이 push에 포함하지 않는다.

## 재현성과 상태

공개 checkout에서 `tests/test_baseline.py`와 `tools/package.py`를 실행해 확인한다.
제출 ZIP은 기존과 동일 SHA-256이어야 한다. 공개 push를 실제 모델 실행·대회 제출 완료로 기록하지 않는다.
이전 개발 커밋을 가리키는 기록은 로컬 개발 이력의 출처이며 공개 저장소의 커밋이 아니다.
후속 변경은 공개 `main`에서 분기한다. 이전 대용량 이력 브랜치를 공개 main에 merge/push하지 않는다.
