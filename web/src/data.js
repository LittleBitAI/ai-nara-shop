// 화면이 읽는 것은 넷이다.
//   web/public/runs/*.json   tools/build_report.py 가 score.py 로 채점한 결과
//   web/public/items.json    docs/items.md 의 24항목 공식 이름·부재탐지
//   /open/dev.jsonl          공고 원문과 나라장터 등록값 (저장소 원본, 사본 없음)
//   /open/dev_labels.csv     정답 200건. e열은 양성 153칸 중 54칸만 차 있다.
// 여기서 점수를 새로 매기지 않는다. 필터가 걸렸을 때만 grid 를 다시 세어 부분집합 F1 을 낸다.

export const ITEMS = Array.from({ length: 24 }, (_, i) => `v${i + 1}`)
export const TP = 'T'
export const FP = 'P'
export const FN = 'N'
export const TN = '.'

export const KIND = {
  [FN]: { key: 'fn', label: '놓침', mark: '▲', help: '정답 1인데 0으로 냈다 (미탐)' },
  [FP]: { key: 'fp', label: '헛짚음', mark: '✕', help: '정답 0인데 1로 냈다 (과탐)' },
  [TP]: { key: 'tp', label: '잡음', mark: '●', help: '정답 1을 1로 냈다' },
  [TN]: { key: 'tn', label: '맞게 0', mark: '▪', help: '정답 0을 0으로 냈다' },
}
// 왼쪽부터 볼 것이 먼저다. TN 은 항목당 180칸 안팎이라 접어 둔다.
export const KIND_ORDER = [FN, FP, TP, TN]

const json = async (url) => {
  const response = await fetch(url)
  if (!response.ok) throw new Error(`${url}: ${response.status}`)
  return response.json()
}

/** RFC4180. 정답 e열에 줄바꿈이 든 인용이 있어서 split('\n') 으로는 못 읽는다. */
function parseCsv(text) {
  const rows = []
  let row = []
  let cell = ''
  let quoted = false
  for (let i = 0; i < text.length; i += 1) {
    const c = text[i]
    if (quoted) {
      if (c !== '"') cell += c
      else if (text[i + 1] === '"') { cell += '"'; i += 1 }
      else quoted = false
    } else if (c === '"') quoted = true
    else if (c === ',') { row.push(cell); cell = '' }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i += 1
      row.push(cell); rows.push(row); row = []; cell = ''
    } else cell += c
  }
  if (cell || row.length) { row.push(cell); rows.push(row) }
  return rows.filter((r) => r.length > 1)
}

/** 한 번만 받아서 계속 쓴다. dev.jsonl 은 8MB 이고 회차를 바꿔도 안 바뀐다. */
let corpusPromise = null
export function loadCorpus() {
  corpusPromise ??= (async () => {
    const [devText, labelText, index] = await Promise.all([
      fetch('/open/dev.jsonl').then((r) => r.text()),
      fetch('/open/dev_labels.csv').then((r) => r.text()),
      json('/items.json'),
    ])
    const { items, bands } = index
    const docs = {}
    for (const line of devText.split('\n')) {
      if (!line.trim()) continue
      const row = JSON.parse(line)
      docs[row.id] = row
    }
    const [, ...rows] = parseCsv(labelText)
    const truth = {}
    for (const row of rows) {
      truth[row[0]] = {
        values: row.slice(1, 25).map(Number),
        evidence: Object.fromEntries(
          row.slice(25, 49).map((q, i) => [ITEMS[i], q]).filter(([, q]) => q),
        ),
      }
    }
    return { docs, truth, items, bands }
  })()
  return corpusPromise
}

export const loadIndex = () => json('/runs/index.json')
export const loadRun = (runId) => json(`/runs/${encodeURIComponent(runId)}.json`)

export const f1 = (tp, fp, fn) => (2 * tp + fp + fn ? (2 * tp) / (2 * tp + fp + fn) : 0)

/** 필터가 걸린 ID 집합에서 항목별 tp/fp/fn/f1 을 다시 센다. */
export function tally(run, ids) {
  return ITEMS.map((item, index) => {
    const counts = { tp: 0, fp: 0, fn: 0, tn: 0 }
    for (const id of ids) counts[KIND[run.grid[id][index]].key] += 1
    return {
      item,
      ...counts,
      support: counts.tp + counts.fn,
      f1: f1(counts.tp, counts.fp, counts.fn),
    }
  })
}

export const macroF1 = (rows) => rows.reduce((sum, r) => sum + r.f1, 0) / rows.length

export const docText = (row) => (row?.docs ?? []).map((d) => d.text).join('\n')

/** 제출 근거가 공고 원문의 연속 부분문자열인가. score.py 는 이걸 미검증으로 둔다. */
export function quoteInDoc(quote, row) {
  if (!quote) return null
  return docText(row).normalize('NFC').includes(quote.normalize('NFC'))
}

/** 경계는 script.py 의 상수가 소유한다. bands 는 items.json 을 거쳐 온 그 값이다.
 *  국가계약 기준 고시금액이다 — 지방은 조문상 다르므로 이 구간은 눈금이지 판정이 아니다. */
export const filters = ({ notice, sme_floor: floor }) => [
  {
    key: 'budget',
    label: '금액 구간',
    help: `배정예산금액. v2·v4~v7·v14~v18 이 금액 경계 항목이다. 고시금액 ${(notice / 1e8).toFixed(1)}억(국가 기준)`,
    options: [
      ['lt1', '1억 미만', (m) => m.배정예산금액 < floor],
      ['mid', '1억~고시금액', (m) => m.배정예산금액 >= floor && m.배정예산금액 < notice],
      ['gte', '고시금액 이상', (m) => m.배정예산금액 >= notice],
    ],
  },
  {
    key: 'law',
    label: '적용계약법',
    help: 'v23 은 지방계약에만 적용된다',
    options: [
      ['nat', '국가', (m) => m.적용계약법?.startsWith('국가')],
      ['loc', '지방', (m) => m.적용계약법?.startsWith('지방')],
    ],
  },
  {
    key: 'input',
    label: '입력',
    help: '프롬프트 탓과 입력 결손 탓을 가르는 축이다',
    options: [
      ['full', '완전관측', (m, row) => row.input_completeness?.완전관측 === true],
      ['partial', '결손', (m, row) => row.input_completeness?.완전관측 !== true],
    ],
  },
  {
    key: 'deal',
    label: '계약방법',
    help: 'v22 는 협상계약에만, v23 은 협상이면서 지방일 때만 적용된다',
    options: [
      ['nego', '협상', (m) => (m.낙찰방법 ?? '').includes('협상')],
      ['other', '협상 아님', (m) => !(m.낙찰방법 ?? '').includes('협상')],
    ],
  },
]

export function applyFilters(ids, docs, picked, groups) {
  const active = groups.flatMap((group) => {
    const chosen = picked[group.key]
    const option = group.options.find(([key]) => key === chosen)
    return option ? [option[2]] : []
  })
  if (!active.length) return ids
  return ids.filter((id) => {
    const row = docs[id]
    return row && active.every((test) => test(row.meta ?? {}, row))
  })
}

// reports/runs/reproducibility.md 의 실측 churn. tools/compare_runs.py 와 같은 값이다.
// 코드가 같은 두 회차에서 관측된 범위이므로, 이 안에 들면 개선이라고 말할 수 없다.
export const CHURN = { minCells: 17, maxCells: 45, maxDelta: 0.010087517153 }
