# ai-nara-shop

나라장터 공고의 법령 위반 24개 항목을 판정하는 대회 프로젝트입니다.
목표는 **유효한 제출 확보 → Macro F1 개선 → 근거 품질·재현성 확보**입니다.

## 시작

공개 저장소는 현재 소스의 `main` 스냅샷입니다. GitHub 파일 제한을 넘는
`open/train_unlabeled.jsonl`은 포함하지 않습니다. 자가 라벨링 작업 전 대회 배포본에서 받아
같은 경로에 배치하세요. 첫 베이스라인 실행·패키징에는 이 파일을 읽지 않습니다.
기존 개발 이력은 로컬 브랜치에 보존했습니다. [공개 작업 기록](docs/tasks/public-push.md)을 참조하세요.

Claude와 Codex 모두 [공통 작업 규칙](docs/workflow.md)을 따릅니다.
역할은 사용하는 AI가 아니라 맡은 작업으로 정합니다.

| 필요한 것 | 읽을 파일 |
| --- | --- |
| AI가 처음 들어왔을 때 | [AGENTS.md](AGENTS.md), [문서 지도](docs/README.md) |
| 대회 목적·평가 비중·진출·제출 운영 | [contest.md](docs/contest.md) |
| 대회에서 가능한 것·금지된 것 | [rules.md](docs/rules.md) |
| 입력·출력·근거 형식 | [data.md](docs/data.md) |
| v1~v24가 뜻하는 것·관련 조문 | [items.md](docs/items.md) |
| 모듈과 파일 소유권 | [design.md](docs/design.md) |
| 공정 사이에 넘길 산출물 | [contracts.md](docs/contracts.md) |
| 지금 할 일과 요청서 양식 | [roadmap.md](docs/roadmap.md), [tasks.md](docs/tasks.md) |
| Claude·Codex hooks 설치 | [setup.md](docs/setup.md) |
| PPTX 근거와 자료 간 차이 | [sources.md](docs/sources.md) |

## 지금 실행 가능한 명령

저장소 루트에서 실행합니다. Python 표준 라이브러리만 사용합니다.

```powershell
python -X utf8 script.py --mock --data-dir open/data --output-dir artifacts/smoke
```

결과: `artifacts/smoke/submission.csv`. 이것은 **입출력 검사**이며 모델 성능이나 제출 적격성을 증명하지 않습니다.
실제 제출에는 공고별 고정 LLM 정상 호출이 필요합니다.

```powershell
python -X utf8 tests/test_baseline.py
python -X utf8 tools/package.py
```

제출 후보: `artifacts/baseline/submit.zip`. ZIP 루트는 `script.py`, `requirements.txt` 두 파일입니다.
기존 출력은 덮어쓰지 않으므로 재실행에는 새 `--output-dir`/`--output` 경로를 사용합니다.
[T1 실행 기록·팀원 합류 기준](docs/tasks/t1-baseline.md), [고정 모델 조사](docs/gemma4.md)를 확인하세요.

## 현재 상태

- 작업 문서: `docs/`에 대회 안내·규칙·데이터·24항목을 주제별로 통합했습니다.
- 원문 보관: 기존 `대회/`는 `archive/contest/`로 이동했습니다. 보관본 없이도 작업 문서를 사용할 수 있습니다.
- 실제 입력·설계 자료: `open/`, 두 베이스라인 노트북, `로드맵.pptx`, `발표용.pptx`.
- T2 채점기: 구현·검증·로컬 머지 완료.
- T1: 제공 베이스라인의 실패 처리·문서 손실·출력 검증을 보완한 제출 후보와 모델 조사 문서.
- 아직 확인하지 않은 것: 실제 모델 평가·서버 제출 성공. 팀용 모듈 분리와 산출물 생성 공정은 후속 작업.
- 설계에 적힌 미래 경로를 구현된 기능으로 취급하지 않습니다.
- 원본 파일명은 출처 추적을 위해 유지합니다. 일상 작업에는 위의 짧은 영문 파일명을 사용합니다.
