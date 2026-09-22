# 공개 push와 하위 작업 공간 정리

- 사용자 지시: 하위 에이전트 정리 후 공개 push. 2026-09-16.
- 상태: done. 공개 저장소 생성·첫 push·원격 확인 완료.
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

## 실행 증거

- 공개 URL: https://github.com/LittleBitAI/ai-nara-shop, visibility `PUBLIC`, 기본 브랜치 `main`.
- 첫 공개 커밋: `5506ca02c11b7a9a8be01f729623c92dd8921aab`; 로컬 출처 `01d2124`.
- 공개 스냅샷의 추적 소스 94개는 제외 파일 외 원본 Git 바이트와 일치.
- 공개 checkout 베이스라인 7 tests OK, 패키징·압축 해제 mock PASS.
- 제출 ZIP SHA-256: `d3d6622e5171cb368adc4f9e5618f9f20f90442a5d3dc64e362a6766c36a9b6a`로 기존과 일치.
- Git 이력 5개 커밋·107개 고유 blob의 주요 비밀키 패턴 검사: 발견 0개.
- 로컬도 `main`으로 전환해 `origin/main`을 추적한다. 기존 개발 브랜치·대용량 데이터와
  `.wiki/decisions/`의 기존 미추적 파일을 보존했다.

## 2026-09-17 후속 — 공개 전 이력을 대용량 파일만 빼고 공개한다

사용자 판단으로 위 "이 파일과 이를 포함한 기존 커밋 이력은 공개 push하지 않는다"를 갱신한다.
막던 것은 이력이 아니라 이력 안의 790MB blob이므로, 그 blob만 제거한 사본 이력을 공개한다.
`main`은 그대로 두고 별도 브랜치로만 올린다. 대용량 이력 브랜치를 `main`에 merge하지 않는다는
위 결정은 유지한다.

- 새 브랜치: `chore/pre-public-history`, tip `2d5afad`. 6커밋.
  `git filter-branch --index-filter`로 `open/train_unlabeled.jsonl`만 이력에서 제거했다.
- 원본 `chore/team-agent-setup`(`01d2124`)과 `master`(`4816cf6`)는 로컬에 그대로 둔다.
  790MB blob의 유일한 Git 사본이며 push하지 않는다.
- 확인: `2d5afad`와 원본 `01d2124`의 차이는 제거한 그 파일 하나뿐이다.
  `2d5afad`와 공개 첫 커밋 `5506ca02`의 차이는 `reports/publication.json` 하나뿐이다.
  남은 최대 blob은 `open/dev.jsonl` 8.3MB로 GitHub 한도 아래다.
- 공개 전 검사: 이력 6커밋·고유 blob 111개 중 텍스트 107개를 비밀키·개인 절대경로 패턴으로
  검사했다. 새로 노출되는 것은 없다. 적중한 blob 7개는 모두 현재 공개 `main`에 있는 것과
  같은 OID다. `docs/sources.md`의 `sk-` 적중은 `ask-with-arrow-key-options`의 부분문자열이다.
- 남은 문제: `reports/t2-*/manifest.json`의 개인 절대경로는 이 push 이전부터 공개 `main`에
  있다. 이번 작업으로 생긴 것이 아니며 별도로 판단한다.

## 2026-09-19 후속 — `chore/pre-public-history`를 지운다

사용자 판단으로 위 "별도 브랜치로만 올린다"를 갱신한다. 원격 브랜치를 `main` 하나로
줄이기로 했고, 그 이력은 로컬에 온전히 남으므로 공개 브랜치를 유지할 이유가 없어졌다.

- 원격·로컬 `chore/pre-public-history`(`2d5afad`)를 지웠다. 이제 원격 브랜치는 `main` 하나다.
- 잃은 것은 GitHub의 off-machine 백업 하나뿐이다. 같은 6커밋이 로컬
  `chore/team-agent-setup`(`01d2124`)에 그대로 있고, 지우기 전 `git diff --stat`으로
  두 브랜치의 차이가 `open/train_unlabeled.jsonl` 하나뿐임을 확인했다.
  `master`(`4816cf6`)는 그 브랜치의 조상이다. 둘 다 사용자 지시로 로컬에 남긴다.
- 다시 만들려면 `chore/team-agent-setup`에서 같은 `git filter-branch --index-filter`로
  그 파일만 빼면 된다. 위 2026-09-17 절이 그 절차를 그대로 적고 있다.
- 이 PC가 사라지면 공개 전 이력도 사라진다. 그것을 알고 내린 결정이다.
