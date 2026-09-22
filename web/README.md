# 회차 진단 화면

Colab 결과를 넣으면 v1~v24 항목별 F1과, dev 200건 중 어디를 맞고 어디를 틀렸는지를
원문까지 열어서 보는 화면이다. 제출물이 아니다 — `tools/package.py`의 루트 allowlist는
`script.py`·`requirements.txt` 둘뿐이라 이 폴더는 제출 ZIP에 안 들어간다.

## 돌리는 법 — 결과 ZIP을 `artifacts/inbox/`에 넣고 런처를 실행한다

| OS | 무엇을 |
| --- | --- |
| Windows | 저장소 루트의 **`report.cmd`** 를 더블클릭 (또는 `cmd` 에서 `report.cmd`) |
| macOS | 저장소 루트의 **`report.command`** 를 Finder 에서 더블클릭 |
| 그 밖 | `./report.command` |

ZIP 파일명을 적을 곳은 없다. 런처가 `artifacts/inbox/` 에서 가장 최근
`colab-results-<숫자>.zip` 을 골라 채점하고 화면을 띄운다. 채점 → `npm install`(처음 한 번)
→ 브라우저 열기까지 한 번에 간다.

인자를 주면 그대로 `build_report.py` 로 넘어간다.

```
report.cmd --all              등록된 회차 전부 다시 만든다 (추이선 채우기)
report.cmd --run <run-id>     그 회차만
report.cmd --zip <경로>        ZIP을 직접 지정
```

macOS 에서 "확인되지 않은 개발자" 로 막히면 한 번만 `chmod +x report.command` 하거나
Finder 에서 우클릭 → 열기를 쓴다.

### 런처 없이 직접

```powershell
python -X utf8 tools/build_report.py --latest   # 또는 --all / --run <id> / --zip <경로>
cd web; npm install; npm run dev                # http://localhost:5310
```

`npm run dev` 상태에서만 돈다. Vite가 `open/dev.jsonl`·`open/dev_labels.csv`를
그 자리에서 서빙하기 때문이고, 사본을 만들지 않으려고 그렇게 했다.

### 런처 세 파일이 하는 일

| 파일 | 몫 |
| --- | --- |
| `report.cmd` | 파이썬을 찾는 것까지. 순수 ASCII·CRLF — cmd.exe 가 배치 파일을 바이트 오프셋으로 되읽어서, 한글이 섞이면 주석 조각이 명령으로 실행된다 |
| `report.command` | 파이썬을 찾는 것까지. LF·실행 비트. 이름만 잡히고 안 도는 파이썬(Store 별칭·끊긴 심 링크)을 한 번 돌려 본다 |
| `tools/report.py` | 순서 로직 전부. 런처 둘이 이걸 나눠 갖지 않는다 |

## 팀에 넘길 때

```powershell
python -X utf8 tools/build_report.py --run <run-id> --share
#   → reports/runs/<run-id>/share.html
```

요약 HTML에는 Macro F1·24항목 막대·TP/FP/FN·오답 목록·회차 추이만 들어간다.
공고 원문·근거 문구·모델 원응답은 빠진다. Slack에 그대로 던져도 열린다.

## 무엇을 어디서 읽는가

| | 원본 |
| --- | --- |
| 점수·정오 격자·제출 근거·모델 흔적 | `web/public/runs/<run-id>.json` (build_report.py) |
| 24항목 이름·부재탐지, 금액 경계 | `web/public/items.json` (`docs/items.md`·`script.py`에서) |
| 공고 원문·나라장터 등록값 | `open/dev.jsonl` |
| 정답 라벨·정답 근거 | `open/dev_labels.csv` |

색·타이포·배선 규칙은 [../DESIGN.md](../DESIGN.md)가 소유한다.
채점이 `score.py`와 어긋나지 않는지는 `tests/test_build_report.py`가 회차마다 대조한다.
