# T2 / dev 채점기

- 담당 역할: 구현자 / Codex. 상태: done (구현·로컬 검증 완료). 산출물 승인 상태: draft.
- 목표: 공식 dev와 예측 CSV를 ID로 대응하고 24개 양성 F1을 단순 평균한다.
- 규칙: 로컬 검증 / A1 / R5·R18·R22, D4·D5, C1·C5. 모델 미사용, Q 확인 불필요.
- 입력: `open/dev_labels.csv`와 같은 ID 집합의 49열 예측 CSV, 작은 합성 CSV.
- 출력·수정 범위: `tools/score.py`, `tests/test_score.py`, 이 문서, `reports/<run-id>/`,
  `docs/tasks.md`의 T2 상태, 필요시 `artifacts/review/t2-request.md`.
- 통과 조건: 손계산, 공식 dev 자기 대조·전부 0·행 재배열, 잘못된 입력 거부,
  CLI 종료 코드, 결과 재읽기, UTF-8 without BOM·LF, 원본 SHA-256 보존.
- 선행·기준선: `c7b765a6a09826d2d2e45031df5e56f92fa55ca9`, 기존 채점기·호출자 없음.
  설치 작업과 분리한 Orca 작업 폴더 `feat-experiment-t2-score`에서 구현한다.
  기존 설치 코드·설정과 위키는 수정하지 않는다. 현재 위키 우선순위는 T1·T2로 로드맵과 일치한다.

## 설계와 필드

표준 라이브러리만 사용한다. CSV 바이트 로드·검증 → ID 대응 → 지표 계산 → 결과 저장 순서다.
원본 베이스라인의 CSV 계약을 따르되 추론 모듈을 import하지 않는다.
입력 바이트를 읽은 즉시 SHA-256을 계산해 채점한 내용과 기록이 일치하게 한다.
헤더·열 수·ID·v값·UTF-8/BOM·NFC와 원문 없이 확인 가능한 e 규약을 검사한다.
e의 500자 제한·금지 접두·v=0/부재탐지 빈칸을 확인하며 원문 부분문자열·의미 품질은 미검증이다.
ID를 정규화하지 않으며 공백뿐인 ID는 거부한다. 오류는 비정상 종료이며 점수를 저장하지 않는다.
기존 출력 디렉터리는 거부한다. 검증 후 같은 부모의 임시 디렉터리에 네 파일을 모두 쓴 뒤
새 출력 디렉터리로 옮겨 이전 실행과 섞이지 않게 한다. 재실행에는 새 run ID를 사용한다.

- `metrics.json`: `macro_f1`, `items.v1`~`v24`의 `tp`, `fp`, `fn`, `precision`,
  `recall`, `f1`, `support`; `truth_count`, `pred_count`, `ids_match`, `error_count`.
- `errors.csv`: `id,item,true,pred,cause,evidence_location,owner,note`.
  ID 문자열 오름차순 → 항목 번호순. 미분석 세 필드는 빈 값, note는 `미분류`.
- `manifest.json`: C1 메타, `run_id`, `baseline_run`, `sources`의 역할·경로·SHA-256,
  `generator`의 코드 경로·SHA-256·명령 argv·PowerShell 재실행 명령·설정,
  `environment`, `mode=local_scoring`, `model=null`, `prompt_hash=null`, `seed=null`,
  `parents=[]`, 사람 검토 필드 null. 완료한 파일 묶음은 `execution_status=complete`, 승인 상태는 draft.
- `result.md`: 점수·오답 수·재실행법·검증 범위·소요 시간. 모델 성능 검증 여부는 예측 출처에
  달려 있으며 자기 대조·합성 예측은 채점기 검사임을 명시한다. 모델 추론·토큰·GPU 수치는 해당 없음.

## 실행 증거

환경: Windows 11 (10.0.26200), Python 3.13.9. 아래 명령은 T2 작업 폴더 루트에서 실행했다.
모두 모델·GPU·유료 API·서버 제출 없이 수행했다.

| 명령·검사 | 실제 결과 |
| --- | --- |
| `python -X utf8 tests/test_score.py ScoreTests.test_hand_calculation_and_order` (구현 전) | FAIL. `tools/score.py`가 없어 CLI 종료 코드 2; 예상 정상 코드 0과 달라 실패 |
| `python -X utf8 tests/test_score.py` (최종) | 4 tests, 7.843초, OK. 양쪽 입력 오류, CLI 종료, 결과 재읽기·해시·인코딩, 입력/기존 결과 보존 포함 |
| 손계산 사례 | v1 TP=2, FP=1, FN=1, precision=recall=F1=2/3, support=3. 나머지 F1=0, Macro F1=1/36 |
| 공식 dev 자기 대조 | 200건, Macro F1=1, 24항목 F1=1, 오답 0행 |
| 공식 dev ID를 유지한 전부 0 | Macro F1=0, 오답 153행 전부 FN, 모든 항목의 FN=support |
| 전부 0 예측 행 역순 | `metrics.json`, `errors.csv`가 순서 변경 전과 바이트 단위 일치 |
| `python -m ruff check tools/score.py tests/test_score.py` | All checks passed |
| `git diff --check` 및 텍스트 검사 | 통과. 작성 파일 UTF-8 without BOM·LF, 원본 dev SHA-256 보존 |

공식 dev 항목별 support(v1~v24):
`7,7,8,6,7,6,7,6,6,7,6,6,6,8,6,6,6,7,6,5,6,5,5,8` (합 153).

입력 `open/dev_labels.csv` SHA-256:
`84c79302ac190b45b2487ec8e02aab73e59071ee745828e813a7db96d3a97a35`.
실행한 `tools/score.py` SHA-256:
`4e8ef1a2284364fdb26cbab4dc53af8d9eac57d2d85f6651279ea3e1dc5f1c57`.

보존 결과: [자기 대조](../../reports/t2-self-check/result.md),
[전부 0](../../reports/t2-zero-check/result.md),
[역순](../../reports/t2-zero-shuffled/result.md).
각 디렉터리는 metrics·errors·manifest·result 4개 파일을 포함한다.
채점·저장 준비 시간은 각각 0.072946초, 0.073176초, 0.079794초이며
마지막 manifest/result 저장·디렉터리 게시 시간은 제외한다. 모델 추론 시간으로 해석하지 않는다.

## 재실행

기존 출력 디렉터리는 거부하므로 아래 `-rerun` 경로도 이미 있다면 새 이름을 쓴다.

```powershell
python -X utf8 tests/test_score.py
python -X utf8 tools/score.py --truth open/dev_labels.csv --pred open/dev_labels.csv --output-dir reports/t2-self-check-rerun
```

전부 0·역순 검사의 생성 파일은 임시 경로에만 두었다. 기존 manifest의 임시 예측 경로는 이미
삭제됐으므로 아래 전체 명령으로 재생성한다. 같은 생성 규칙·바이트의 SHA-256을 대조할 수 있다.
최초 실행은 아래 출력 경로에서 `-rerun`을 뺀 이름을 사용했다.

```powershell
@'
import csv
from pathlib import Path
import subprocess
import sys
import tempfile

truth = Path('open/dev_labels.csv')
with truth.open(encoding='utf-8', newline='') as f:
    rows = list(csv.reader(f))
with tempfile.TemporaryDirectory(prefix='t2-zero-') as tmp:
    pred = Path(tmp) / 'zero.csv'
    for name, records in [('t2-zero-check-rerun', rows[1:]),
                          ('t2-zero-shuffled-rerun', list(reversed(rows[1:])) )]:
        with pred.open('w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, lineterminator='\n')
            writer.writerow(rows[0])
            writer.writerows([r[0]] + ['0'] * 24 + [''] * 24 for r in records)
        subprocess.run([sys.executable, '-X', 'utf8', 'tools/score.py',
                        '--truth', str(truth), '--pred', str(pred),
                        '--output-dir', 'reports/' + name], check=True)
for name in ['metrics.json', 'errors.csv']:
    assert (Path('reports/t2-zero-check-rerun') / name).read_bytes() == (
        Path('reports/t2-zero-shuffled-rerun') / name).read_bytes()
print('zero and shuffled metrics/errors: byte-identical')
'@ | python -X utf8 -
```

## 남은 범위와 리뷰

근거 원문/의미 품질·모델 성능·서버 제출은 검증하지 않았다. CSV의 e 형식 검사와 별개다.
ID는 문자열 그대로 비교한다. 순서는 ID 사전순·항목 번호순이다.
이 채점기는 모든 입력을 메모리에 읽는 dev용 구현이며 대규모 스트리밍 처리는 추가하지 않았다.
새 의존성·대시보드 없이 표준 라이브러리 CLI로 필요한 범위를 충족했다.

사용자 지시에 따라 이번 T2의 별도 독립 리뷰는 진행하지 않으며 완료 조건으로 두지 않는다.
손계산·공식 dev 대조·입력 경계 테스트의 실행 증거로 구현·로컬 검증 완료를 기록한다.
준비했던 `artifacts/review/t2-request.md`는 미전달 상태에서 철회했다(Git 제외 경로).
독립 리뷰·산출물 사람 승인·push·PR은 수행하지 않았다. 자체 검사는 독립 리뷰가 아니다.
사용자의 커밋·머지 요청에 따라 `90228e3`에 구현·검증 기록을 커밋하고,
`chore/team-agent-setup`에 fast-forward 머지된 것을 확인했다.
머지 뒤 임시 지시서 `t2.md`, T2 작업 트리와 철회한 리뷰 요청·캐시를 정리했다.
원격 저장소가 없어 fetch·pull·원격 브랜치 정리는 해당 없음이다.
원래 작업 폴더의 다른 미추적 기록은 보존했다. 이 작업에서 추론 서버는 시작하지 않았다.
