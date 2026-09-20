---
name: 회차 진단 화면
scope: web/
colors:
  surface: '#fcfcfb'
  surface-dark: '#1a1a19'
  ink: '#0b0b0b'
  ink-dark: '#ffffff'
  tp: '#1baf7a'
  tp-dark: '#199e70'
  fp: '#eb6834'
  fp-dark: '#d95926'
  fn: '#4a3aa7'
  fn-dark: '#9085e9'
  tn: '#d9d7d0'
  tn-dark: '#3a3a36'
  sequential: '#2a78d6'
  sequential-dark: '#3987e5'
typography:
  sans: "Pretendard Variable, Segoe UI Variable Text, Malgun Gothic, system-ui"
  mono: "ui-monospace, Cascadia Mono, Consolas, D2Coding"
  steps: 8
spacing: [4, 6, 8, 10, 12, 14, 16, 24, 32, 48]
rounded: { lg: 10, md: 6, sm: 4 }
components: [ItemList, Strip, Detail, StackedBars, Trend, EvidenceAudit, InputSplit, AbsencePanel, ResponseHealth]
---

# 회차 진단 화면

## 누가, 무엇을 하러, 무엇이 보이면 끝인가

```
누가:        Colab 회차를 돌리고 온 팀원 4명
무엇을 하러: 어느 항목이 낮은지 보고, 그 항목에서 dev 문서를 어떻게 읽었는지 확인하러
성공:        낮은 항목을 짚고 → 틀린 공고를 눌러 → 원문의 어느 문장이 걸렸는지 본다
```

추론하는 화면이 아니다. **이미 나온 결과를 보는 화면**이다. 채점은
`tools/score.py` 가 하고, 이 화면은 그 결과를 그린다. 화면에서 점수를 다시
매기는 곳은 필터가 걸렸을 때 부분집합을 세는 한 곳(`data.js`의 `tally`)뿐이다.

## 색 — 역할로만 쓴다

TP·FP·FN 세 계열은 dataviz 검증기(`validate_palette.js`)를 **라이트·다크 양쪽,
전체쌍 모드**로 통과한 조합이다. 후보를 셋 만들어 둘은 떨어뜨렸다.

| 후보 | 결과 |
| --- | --- |
| 청록 / 주황 / 자주 | 양쪽 PASS. **채택** |
| 청록 / 주황 / 진홍 | FAIL — 진홍이 주황과 색각 ΔE 5.6, 정상시 7.1 (바닥 15) |
| 진초록 / 주황 / 자주 | FAIL — 진초록이 주황과 protan ΔE 3.2 |

배치는 **헛짚은 것(FP)이 제일 튀는 색**을 가져간다. 과탐이 한 덩어리로 터지는
항목(예: v24의 FP 32)을 먼저 찾게 하는 배치다.

`TN`은 계열이 **아니다.** 네 번째 범주색으로 넣으면 deutan에서 청록과 ΔE 2.9로
붙는다. 바탕에 가까운 연회색으로 빼고, 스트립에서는 접어 둔다.

라이트 모드에서 청록(`#1baf7a`)은 바탕 대비 2.74:1로 3:1 미만이다. 검증기가
요구하는 **구제 수단은 보이는 라벨**이며, 스트립의 모든 칸이 공고 번호를 칸
안에 달고 있고 오답 목록이 표로 따로 있으므로 충족한다.

## 타이포 — 여덟 단계, 쓰임이 안 겹친다

| 토큰 | 값 | 쓰임 |
| --- | --- | --- |
| `--t-h2` | 600 20px sans | 오른쪽 기둥 제목 |
| `--t-body` | 400 15px/1.75 sans | 공고 원문·인용 |
| `--t-label` | 500 13px sans | 차트 제목, 그룹 머리 |
| `--t-aux` | 400 13px sans | 항목 이름, 칩, 필터 |
| `--t-badge` | 600 11px sans | 부재 배지, 정오 알약 |
| `--m-lg` | 600 15px mono | Macro F1, 공고 ID |
| `--m-md` | 600 12px mono | 표 안 수치 |
| `--m-sm` | 600 10px mono | 막대 안 수치, 축 눈금 |

공고 원문은 **읽는 글**이라 고딕이다. 한글 등폭으로 깔면 5천~2만자를 못 읽는다.
등폭은 자리수가 세로로 맞아야 하는 수치에만 쓴다.

브라우저에서 잰 결과 정확히 8단계다(`getComputedStyle` 집계). 새 크기를 쓰기
전에 이 표에서 하나를 먼저 찾는다.

## 스크롤 — 페이지는 안 움직이고 칸이 움직인다

넓은 화면에서 문서 하나가 통째로 스크롤하면, 원문을 읽으려고 내린 순간 F1 막대·항목
헤더·스트립이 전부 위로 빠져나간다. 다음 칸을 누르려면 매번 되올라와야 한다.

그래서 바깥(`.app`)은 `height:100%; overflow:hidden` 이고 **네 곳이 각자 구른다.**

| 칸 | 구르는가 |
| --- | --- |
| 좌측 24항목 (`.items`) | 자기 안에서 |
| 우측 윗칸 (`.paneTop` — 제목·지표·스트립) | **안 움직인다.** 길면(v24 헛짚음 32칸) 그 안에서만, `max-height:46vh` |
| 우측 아랫칸 (`.paneScroll` — 드릴다운·추이선) | 자기 안에서 |
| 공고 원문 (`.doc`) | 자기 안에서, `max-height:52vh` |

원문을 바깥으로 풀면 1만 2천자 뒤에 있는 추이선까지 내내 내려야 하므로 상자를 유지한다.
격자 칸에 `min-height:0` 이 없으면 칸이 내용만큼 늘어나 넷 다 안 먹는다.
다른 항목·다른 공고를 열면 아랫칸은 맨 위로 되돌린다 — 앞의 것이 내려 둔 자리를 안 물려받는다.

좁은 화면(≤900px)에는 칸을 둘로 쪼갤 세로가 없다. 평소대로 페이지 하나가 구르고,
윗칸만 `position:sticky` 로 붙어 있되 거기서도 `40vh` 로 막는다.

## 배선 — 소유는 나중에 붙이는 층이 아니다

이 화면은 서버에 쓰지 않는다. 계정 경계는 없다. 남는 것은 **비동기 소유권**이다.

- 회차를 바꾸면 `generation` 이 올라가고, 늦게 도착한 회차 JSON은 자기 세대가
  아니면 상태를 안 건드리고 버린다. 늦은 응답을 잠그지 않는다.
- 공고 원문(8MB)은 한 번만 받아 모듈 수준에서 재사용한다. 회차를 바꿔도
  안 바뀌는 값이다.
- `localStorage` 접근은 전부 try/catch 다. 사생활 보호 창에서 화면이 안 죽는다.

## 원본을 베끼지 않는다

| 값 | 원본 | 화면이 읽는 법 |
| --- | --- | --- |
| 결과 ZIP 파일명 | `artifacts/inbox/` 의 실물 | 회차마다 바뀌므로 어디에도 안 적는다. `--latest` 가 고른다 |
| 24항목 이름·부재탐지 | `docs/items.md` | `build_report.py` 가 `items.json` 으로 옮긴다 |
| 고시금액·1억 경계 | `script.py` 의 상수 | 같은 파일에서 글자로 읽어 `items.json` 에 싣는다 |
| 공고 원문·나라장터 등록값 | `open/dev.jsonl` | Vite가 그 자리에서 서빙. 사본 없음 |
| 정답 라벨·정답 근거 | `open/dev_labels.csv` | 같음 |
| churn 실측 범위 | `reports/runs/reproducibility.md` | `tools/compare_runs.py` 와 같은 값을 `data.js` 에 둔다 |

## 안 하는 것

- 모션. 상태 전환에 120ms 색 전환만 있고 `prefers-reduced-motion` 을 따른다.
- 정적 배포. Vite가 `open/` 을 직결하므로 `npm run dev` 가 있어야 돈다.
  팀 공유는 `build_report.py --share` 가 뽑는 **원문 없는 요약 HTML** 로 한다.
