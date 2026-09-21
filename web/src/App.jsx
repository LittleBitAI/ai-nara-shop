import { useEffect, useMemo, useRef, useState } from 'react'
import {
  ITEMS, KIND, TP, FP, FN, CHURN, loadCorpus, loadIndex, loadRun,
  tally, macroF1, applyFilters, filters as buildFilters,
} from './data.js'
import { StackedBars, Trend, Legend } from './charts.jsx'
import {
  ItemList, Strip, Detail, EvidenceAudit, InputSplit, AbsencePanel, ResponseHealth,
} from './panels.jsx'

const fmt = (n) => n.toFixed(3)
// 파일럿은 `<run-id>.<군>-<소비자>` 라 뒤 7글자만 자르면 `ol-head` 같은 것이 남는다.
// 회차 꼬리와 변이 이름을 같이 보여야 네 항목이 서로 갈린다.
const shortRun = (id) => {
  const at = id.indexOf('.')
  if (at < 0) return id.replace(/^colab-/, '').slice(-7)
  return `${id.slice(0, at).slice(-7)}·${id.slice(at + 1)}`
}

function useTheme() {
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem('theme') ?? 'auto' } catch { return 'auto' }
  })
  useEffect(() => {
    if (theme === 'auto') delete document.documentElement.dataset.theme
    else document.documentElement.dataset.theme = theme
    try {
      if (theme === 'auto') localStorage.removeItem('theme')
      else localStorage.setItem('theme', theme)
    } catch { /* 사생활 보호 창에서는 못 적는다. 화면은 그대로 돈다 */ }
  }, [theme])
  return [theme, setTheme]
}

export default function App() {
  const [corpus, setCorpus] = useState(null)
  const [history, setHistory] = useState(null)
  const [runId, setRunId] = useState(null)
  const [run, setRun] = useState(null)
  const [compareId, setCompareId] = useState('')
  const [compareRun, setCompareRun] = useState(null)
  const [item, setItem] = useState(null)
  const [picked, setPicked] = useState(null)
  const [sort, setSort] = useState('f1')
  const [picks, setPicks] = useState({})
  const [error, setError] = useState(null)
  const [theme, setTheme] = useTheme()

  // 늦게 온 결과가 아직 이 화면의 것인가. 회차를 바꾸면 세대가 올라가고 옛 응답은 버린다.
  // 현재 회차와 비교 회차는 **세대를 따로 센다.** 하나로 묶으면 비교를 부르는 중에 현재를
  // 바꿨을 때 비교 응답이 버려지는데 compareId 는 새 값인 채 다시 안 불러, 옛 회차를
  // 새 회차 이름표로 비교하게 된다. 반대 순서에서는 run 이 계속 null 로 남는다.
  const runGen = useRef(0)
  const compareGen = useRef(0)
  // 다른 항목·다른 공고를 열면 아래 칸은 맨 위부터 읽는다. 앞의 것이 내려 둔 자리를 물려받지 않는다.
  const paneScroll = useRef(null)
  useEffect(() => { paneScroll.current?.scrollTo(0, 0) }, [item, picked, runId])

  useEffect(() => {
    Promise.all([loadCorpus(), loadIndex()])
      .then(([loaded, index]) => {
        setCorpus(loaded)
        setHistory(index.runs)
        setRunId(index.runs.at(-1)?.run_id ?? null)
      })
      .catch((cause) => setError(cause.message))
  }, [])

  useEffect(() => {
    if (!runId) return
    const mine = (runGen.current += 1)
    setRun(null)
    loadRun(runId)
      .then((loaded) => { if (mine === runGen.current) setRun(loaded) })
      .catch((cause) => { if (mine === runGen.current) setError(cause.message) })
  }, [runId])

  useEffect(() => {
    const mine = (compareGen.current += 1)
    if (!compareId) { setCompareRun(null); return }
    // 부르는 동안에는 옛 비교 회차를 남기지 않는다. 남기면 새 이름표로 옛 값을 본다.
    setCompareRun(null)
    loadRun(compareId)
      .then((loaded) => { if (mine === compareGen.current) setCompareRun(loaded) })
      .catch(() => { if (mine === compareGen.current) setCompareRun(null) })
  }, [compareId])

  const groups = useMemo(() => (corpus ? buildFilters(corpus.bands) : []), [corpus])
  const ids = useMemo(
    () => (run && corpus ? applyFilters(run.ids, corpus.docs, picks, groups) : []),
    [run, corpus, picks, groups],
  )
  const filtered = ids.length !== run?.ids.length
  const rows = useMemo(() => (run ? tally(run, ids) : []), [run, ids])

  // 연 공고가 필터 밖으로 나가면 닫는다. 안 닫으면 위는 부분집합인데 아래 드릴다운만
  // 필터에 안 걸린 공고를 계속 보여 준다.
  // `ids.length` 로 0건을 빼 두면 안 된다 — 0건을 내는 조합이 실제로 셋 있고(예:
  // 1억~고시금액 + 지방 + 결손), 하필 그때가 위는 0건인데 아래만 남는 그 상태다.
  useEffect(() => {
    if (picked && !ids.includes(picked)) setPicked(null)
  }, [ids, picked])
  const byItem = useMemo(() => Object.fromEntries(rows.map((r) => [r.item, r])), [rows])

  const diff = useMemo(() => {
    if (!run || !compareRun) return null
    const flipped = new Set()
    const delta = {}
    let fixed = 0
    let broken = 0
    for (const id of ids) {
      const now = run.grid[id]
      const was = compareRun.grid[id]
      if (!was) continue
      for (let i = 0; i < ITEMS.length; i += 1) {
        if (now[i] === was[i]) continue
        flipped.add(`${id}|${ITEMS[i]}`)
        const wasWrong = was[i] === FP || was[i] === FN
        const nowWrong = now[i] === FP || now[i] === FN
        if (wasWrong && !nowWrong) fixed += 1
        else if (!wasWrong && nowWrong) broken += 1
      }
    }
    const before = tally(compareRun, ids)
    for (const row of before) delta[row.item] = (byItem[row.item]?.f1 ?? 0) - row.f1
    return {
      flipped, fixed, broken, delta,
      deltaMacro: macroF1(rows) - macroF1(before),
      cells: flipped.size,
    }
  }, [run, compareRun, ids, rows, byItem])

  if (error) return <p className="pad">데이터를 못 읽었다: {error}<br /><code>python -X utf8 tools/build_report.py --all</code> 을 먼저 돌린다.</p>
  if (!corpus || !history || !run) return <p className="pad dim">읽는 중… (dev.jsonl 8MB)</p>

  const current = byItem[item]
  const absence = corpus.items[item]?.absence

  const open = (nextItem, nextId) => { setItem(nextItem); setPicked(nextId) }

  return (
    <div className="app">
      <header className="top">
        <label className="pickrun">
          회차
          <select value={runId} onChange={(e) => { setRunId(e.target.value); setPicked(null) }}>
            {[...history].reverse().map((r) => (
              <option key={r.run_id} value={r.run_id}>
                {shortRun(r.run_id)} · {fmt(r.macro_f1)}
                {r.kind === 'gpu-pilot' ? ' (파일럿·부분 GPU)' : r.has_raw ? '' : ' (원응답 없음)'}
              </option>
            ))}
          </select>
        </label>
        <strong className="macro">
          Macro F1 <b>{macroF1(rows).toFixed(6)}</b>
          {filtered && <span className="dim"> · {ids.length}건만</span>}
        </strong>
        <label className="pickrun">
          비교
          <select value={compareId} onChange={(e) => setCompareId(e.target.value)}>
            <option value="">없음</option>
            {[...history].reverse().filter((r) => r.run_id !== runId).map((r) => (
              <option key={r.run_id} value={r.run_id}>{shortRun(r.run_id)} · {fmt(r.macro_f1)}</option>
            ))}
          </select>
        </label>
        <span className="spacer" />
        <button className="linkish" onClick={() => setTheme(theme === 'dark' ? 'light' : theme === 'light' ? 'auto' : 'dark')}>
          {{ auto: '☯ 시스템', light: '☀ 밝게', dark: '☾ 어둡게' }[theme]}
        </button>
      </header>

      <div className="filters">
        {groups.map((group) => (
          <label key={group.key} title={group.help}>
            {group.label}
            <select
              value={picks[group.key] ?? ''}
              onChange={(e) => setPicks({ ...picks, [group.key]: e.target.value })}
            >
              <option value="">전부</option>
              {group.options.map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
          </label>
        ))}
        {filtered && (
          <button className="linkish" onClick={() => setPicks({})}>
            필터 끄기 — {run.ids.length}건 중 {ids.length}건
          </button>
        )}
      </div>

      {diff && <DiffBar diff={diff} compareId={compareId} />}

      <main className="split">
        <ItemList rows={rows} items={corpus.items} selected={item} onSelect={(next) => open(next, null)}
                  sort={sort} onSort={setSort} delta={diff?.delta} />

        {/* 위쪽(제목·스트립)은 안 움직이고 아래쪽만 스크롤한다. 원문을 읽으려고 휠을
            내렸다가 다음 칸을 누르러 다시 올라오지 않게 하는 것이 이 두 칸의 전부다. */}
        <section className="pane">
          <div className="paneTop">
            {!item ? (
              <div className="panehead">
                <h2>개요</h2>
                <span className="dim">왼쪽에서 항목을 고르면 그 항목의 200건으로 들어간다</span>
              </div>
            ) : (
              <>
                <div className="panehead">
                  <button className="linkish" onClick={() => open(null, null)}>← 개요</button>
                  <h2>
                    {item} {corpus.items[item]?.name}
                    {absence && <b className="badge">부재탐지</b>}
                  </h2>
                  <span className="mono dim">
                    TP {current.tp} · FP {current.fp} · FN {current.fn} · 지지 {current.support} · F1 {fmt(current.f1)}
                  </span>
                </div>
                {ids.length ? (
                  <Strip run={run} item={item} ids={ids} picked={picked} onPick={setPicked}
                         flipped={diff?.flipped} />
                ) : (
                  <p className="note">
                    이 필터에 걸리는 공고가 <b>한 건도 없다.</b> 필터를 풀거나 다른 조합을 고른다.
                  </p>
                )}
              </>
            )}
          </div>

          <div className="paneScroll" ref={paneScroll}>
            {!item ? (
              <>
                <StackedBars rows={[...rows].sort((a, b) => a.f1 - b.f1)} items={corpus.items}
                             selected={item} onSelect={(next) => open(next, null)} />
                <Trend history={history} item={null} current={runId} compare={compareId}
                       onPick={setRunId} />
                <AbsencePanel rows={rows} items={corpus.items} onSelect={(next) => open(next, null)} />
                <EvidenceAudit run={run} corpus={corpus} ids={ids} onOpen={open} />
                <InputSplit run={run} corpus={corpus} ids={ids} />
                <ResponseHealth run={run} ids={ids} />
              </>
            ) : (
              <>
                {picked ? (
                  <Detail run={run} corpus={corpus} item={item} id={picked} absence={absence} />
                ) : (
                  <p className="note dim">위에서 한 칸을 고르면 그 공고의 원문·근거·모델 판정이 여기 선다.</p>
                )}
                <Trend history={history} item={item} itemName={corpus.items[item]?.name}
                       current={runId} compare={compareId} onPick={setRunId} />
              </>
            )}
          </div>
        </section>
      </main>
    </div>
  )
}

/** 뒤집힌 셀이 실측 churn 범위 안이면 개선이라고 말할 수 없다. 그 선을 화면에 긋는다. */
function DiffBar({ diff, compareId }) {
  const inChurn = diff.cells <= CHURN.maxCells && Math.abs(diff.deltaMacro) <= CHURN.maxDelta
  return (
    <div className={`diffbar${inChurn ? ' churn' : ''}`}>
      <span className="mono">{shortRun(compareId)} → 지금</span>
      <span>뒤집힘 <b>{diff.cells}</b>셀</span>
      <span className={diff.deltaMacro >= 0 ? 'ok' : 'no'}>
        ΔMacro {diff.deltaMacro >= 0 ? '+' : ''}{diff.deltaMacro.toFixed(6)}
      </span>
      <span className="ok">고쳐짐 {diff.fixed}</span>
      <span className="no">망가짐 {diff.broken}</span>
      <span className="churnnote">
        {inChurn
          ? `실측 churn 범위(${CHURN.minCells}~${CHURN.maxCells}셀 · ≤${CHURN.maxDelta.toFixed(4)}) 안이다 — 같은 코드에서도 이만큼 흔들린다`
          : `실측 churn 범위(${CHURN.maxCells}셀 · ${CHURN.maxDelta.toFixed(4)}) 밖이다`}
      </span>
    </div>
  )
}
