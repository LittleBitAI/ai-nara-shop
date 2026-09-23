// 법령 화면. 회차 진단과 다른 질문에 답한다 — "이 항목의 근거가 법령의 어디인가".
//
// 항목 하나가 법령 하나에 안 들어간다. v1 은 국가·지방 시행령 네 조문이고, 시행령 제21조
// 하나는 항목 열 개가 나눠 쓴다. 주소는 `experiments/law_index.py` 가 항목표에서 풀어
// `laws.json` 에 자리(오프셋)까지 실어 둔 것이고, 전문은 `open/` 의 원본을 그 자리에서 읽는다.
// 화면은 조문을 다시 찾지도, 요약하지도 않는다 — 실린 자리에 색만 칠한다.
import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import { ITEMS, loadLaws, loadLawText } from './data.js'

// 긴 정식 명칭은 왼쪽 기둥과 격자에 안 들어간다. 줄인 이름은 보기용이고 전체 이름은
// title 과 문서 머리에 그대로 남는다 — 화면에서 법령 이름을 고쳐 쓰지 않는다.
const SHORT_LAW = [
  ['국가를 당사자로 하는 계약에 관한 법률', '국가계약법'],
  ['지방자치단체를 당사자로 하는 계약에 관한 법률', '지방계약법'],
  ['중소기업제품 구매촉진 및 판로지원에 관한 법률', '판로지원법'],
  ['중소기업자간 경쟁제품 및 공사용자재 직접구매 대상 품목 지정 내역', '직접구매 품목 지정 내역'],
  ['중소 소프트웨어사업자의 사업 참여 지원에 관한 지침', '중소SW 참여지원 지침'],
  ['(계약예규) ', ''],
]
export const shortLaw = (name) => SHORT_LAW.reduce((out, [long, s]) => out.replace(long, s), name)
const axisMark = (axes) => [...axes].sort().map((axis) => axis[0]).join('')   // 국 → 지

/** laws.json 을 화면이 묻는 모양으로 한 번만 돌려 둔다. 법령별 인용, 조각별 주인. */
export function useLawMap() {
  const [map, setMap] = useState(null)
  const [fail, setFail] = useState(null)
  useEffect(() => { loadLaws().then(setMap).catch((cause) => setFail(cause.message)) }, [])

  const view = useMemo(() => {
    if (!map) return null
    const rows = new Map()                            // 법령 → { name, chars, segs, cells }
    const owners = map.segments.map(() => new Map())  // 조각 → 항목 → 축 집합
    map.segments.forEach((segment, index) => {
      const row = rows.get(segment.law) ?? {
        name: segment.law, chars: map.laws[segment.law]?.chars ?? 0, segs: [], cells: new Map(),
      }
      row.segs.push(index)
      rows.set(segment.law, row)
    })
    for (const [item, axes] of Object.entries(map.cites)) {
      for (const [axis, entry] of Object.entries(axes)) {
        for (const index of entry.segs) {
          const row = rows.get(map.segments[index].law)
          if (!row.cells.has(item)) row.cells.set(item, new Set())
          row.cells.get(item).add(axis)
          if (!owners[index].has(item)) owners[index].set(item, new Set())
          owners[index].get(item).add(axis)
        }
      }
    }
    for (const row of rows.values()) row.segs.sort((a, b) => map.segments[a].at - map.segments[b].at)
    // 항목별로 걸친 법령. 왼쪽 기둥이 "v1 → 법령 2개" 를 여기서 읽는다.
    const byItem = Object.fromEntries(ITEMS.map((item) => {
      const segs = Object.values(map.cites[item] ?? {}).flatMap((entry) => entry.segs)
      const laws = [...new Set(segs.map((index) => map.segments[index].law))]
      return [item, { segs: new Set(segs), laws }]
    }))
    const cited = [...rows.values()].sort((a, b) => b.cells.size - a.cells.size
                                                 || a.name.localeCompare(b.name))
    return { rows, cited, byItem, owners, quiet: Object.keys(map.laws).filter((n) => !rows.has(n)) }
  }, [map])

  return { map, view, fail }
}

/** 전문에 인용 구간을 칠한다.
 *
 *  구간은 **겹치고 품는다** — 지방 집행기준의 `제1장`(70,290자) 안에 `제1장 7.`(4,203자)이 있다.
 *  앞의 것이 이긴다는 규칙으로는 안쪽이 통째로 사라지므로 글자마다 세기를 매겨 합친다.
 *  0 안 쓰임 · 1 인용됨 · 2 고른 항목의 인용. 420,768자 한 번 도는 값이다.
 */
function paint(text, spans) {
  const level = new Uint8Array(text.length)
  const cuts = new Set([0, text.length])
  for (const span of spans) {
    const to = Math.min(span.to, text.length)
    for (let i = Math.max(span.at, 0); i < to; i += 1) {
      if (level[i] < span.rank) level[i] = span.rank
    }
    cuts.add(span.at)                     // 조문 머리를 항상 토막 경계로 둔다. 점프가 그 자리를 잡는다
    cuts.add(to)
  }
  const out = []
  let start = 0
  for (let i = 1; i <= text.length; i += 1) {
    if (i < text.length && level[i] === level[start] && !cuts.has(i)) continue
    const chunk = text.slice(start, i)
    if (level[start] === 0) out.push(chunk)
    else {
      out.push(
        <mark key={start} data-at={start} className={level[start] === 2 ? 'mine' : ''}>{chunk}</mark>,
      )
    }
    start = i
  }
  return out
}

/** 인용된 조문 하나만. 본문은 `laws.json` 에 실린 원문 부분문자열 그대로다 —
 *  발췌만 볼 때는 법령 전문(최대 420,768자)을 아예 안 받는다. */
function LawCut({ segment, cited, mine }) {
  return (
    <article className={`lawcut${mine ? ' mine' : ''}`} data-at={segment.at}>
      <h4>
        <b className="mono">{segment.path.join(' ') || '문서 전체'}</b>
        <span className="dim mono">
          {segment.at.toLocaleString()}자 지점 · {segment.chars.toLocaleString()}자
        </span>
        <span className="segcites">
          {cited.map(([item, axes]) => (
            <span key={item} className="chip">{item} <b>{axisMark(axes)}</b></span>
          ))}
        </span>
      </h4>
      <div className="cuttext">{segment.text}</div>
    </article>
  )
}

/** 왼쪽 기둥. 위는 24항목, 아래는 인용된 법령. 어느 쪽으로도 들어갈 수 있다. */
function LawRail({ items, view, focus, law, onItem, onLaw }) {
  return (
    <nav className="items" aria-label="항목과 법령">
      <div className="itemshead"><span>항목 24 — 누르면 그 항목의 근거 조문이 전문에서 열린다</span></div>
      <ol>
        {ITEMS.map((item) => {
          const mine = view.byItem[item]
          return (
            <li key={item}>
              <button className={`lawitem${focus === item ? ' on' : ''}`} onClick={() => onItem(item)}
                      aria-current={focus === item}>
                <span className="tag">{item}</span>
                <span className="label">{items[item]?.name ?? ''}</span>
                <span className="num dim">
                  {mine.segs.size ? `${mine.laws.length}·${mine.segs.size}` : '—'}
                </span>
              </button>
            </li>
          )
        })}
      </ol>
      <div className="itemshead"><span>법령 {view.cited.length} — 인용된 것만</span></div>
      <ol>
        {view.cited.map((row) => (
          <li key={row.name}>
            <button className={`lawitem${law === row.name ? ' on' : ''}`} title={row.name}
                    onClick={() => onLaw(row.name)} aria-current={law === row.name}>
              <span className="label wide">{shortLaw(row.name)}</span>
              <span className="num dim">{row.segs.length}곳</span>
            </button>
          </li>
        ))}
      </ol>
      <p className="note dim">
        인용이 하나도 없는 제공 법령 {view.quiet.length}개: {view.quiet.map(shortLaw).join(' · ')}
      </p>
    </nav>
  )
}

/** 법령 × 항목 격자. 아무것도 안 골랐을 때의 첫 화면이다. */
function LawGrid({ items, view, focus, onItem, onLaw }) {
  return (
    <figure className="chart lawmap">
      <figcaption>
        법령 × 항목 <span className="dim">
          — 국=국가계약 근거, 지=지방계약 근거. 칸을 누르면 그 항목의 조문이 전문에서 열린다
        </span>
      </figcaption>
      <div className="lawgrid">
        <span className="lawcorner" />
        {ITEMS.map((item) => (
          <button key={item} className={`lawcol${focus === item ? ' on' : ''}`}
                  onClick={() => onItem(item)} title={`${item} ${items[item]?.name ?? ''}`}>
            {item.slice(1)}
          </button>
        ))}
        {view.cited.map((row) => (
          <Fragment key={row.name}>
            <button className="lawname" title={`${row.name} · ${row.chars.toLocaleString()}자`}
                    onClick={() => onLaw(row.name)}>
              {shortLaw(row.name)}
            </button>
            {ITEMS.map((item) => {
              const cell = row.cells.get(item)
              if (!cell) return <span key={item} className="lawcell" />
              return (
                <button key={item} className={`lawcell on${focus === item ? ' mine' : ''}`}
                        onClick={() => onItem(item)}
                        title={`${item} ${items[item]?.name ?? ''} — ${row.name} (${[...cell].join('·')})`}>
                  {axisMark(cell)}
                </button>
              )
            })}
          </Fragment>
        ))}
      </div>
    </figure>
  )
}

/** 법령 하나의 전문. 인용된 조문에 색이 있고, 고른 항목의 것은 진하다. */
export function LawView({ items, focus, onFocus }) {
  const { map, view, fail } = useLawMap()
  // 고른 법령은 담고, **보이는 법령은 렌더에서 끌어낸다.** effect 로 뒤늦게 맞추면
  // 항목을 바꾼 직후 한 렌더가 새 항목의 머리글 아래 옛 법령의 본문을 세운다 —
  // v24 의 지속 오류를 고쳐도 항목↔법령 사이에는 그 한 렌더가 그대로 남는다.
  const [picked, setPicked] = useState(null)
  // 전문은 **어느 법령의 것인지와 함께** 담는다. 글자만 담으면 법령을 바꾼 직후 한 번의
  // 렌더에서 옛 법령의 전문이 새 법령의 오프셋으로 칠해져 새 이름표 아래 선다.
  // 세대 카운터는 늦게 온 응답만 막고, 이미 담긴 글자의 주인은 안 본다.
  const [text, setText] = useState(null)
  const [loading, setLoading] = useState(false)
  // 기본은 발췌다. 인용은 150,515자 중 네 곳이고, 그 네 곳을 보려고 전문을 스크롤하는 것이
  // 이 화면의 요점이 아니다. 앞뒤 문맥이 필요할 때만 전문으로 넘어간다.
  const [mode, setMode] = useState('cut')
  const body = useRef(null)
  const asked = useRef(0)

  // 항목을 고르면 그 항목이 쓰는 법령만 연다. 보던 법령이 그 안에 있으면 그대로,
  // 없으면 첫 법령으로, 쓰는 법령이 없으면(v24) 닫는다. 값 하나로 끝나므로 어긋난 중간 상태가 없다.
  const usable = focus && view ? view.byItem[focus].laws : null
  const law = usable ? (usable.includes(picked) ? picked : (usable[0] ?? null)) : picked

  // 법령을 직접 고르면 그 법령을 연다. 고른 법령이 지금 항목의 것이 아니면 항목 선택을 푼다 —
  // 같은 처리 안에서 둘을 같이 바꾸므로 한 렌더도 어긋나지 않는다.
  const openLaw = (name) => {
    setPicked(name)
    if (focus && !view.byItem[focus].laws.includes(name)) onFocus(null)
  }

  useEffect(() => {
    if (!law || mode !== 'full') { setText(null); return }
    const mine = (asked.current += 1)
    setLoading(true)
    loadLawText(law)
      .then((loaded) => {
        if (mine === asked.current) { setText({ law, text: loaded }); setLoading(false) }
      })
      // 실패도 그 법령의 결과다. null 로 지우면 아래가 영영 "읽는 중" 으로 남는다.
      .catch(() => { if (mine === asked.current) { setText({ law, text: null }); setLoading(false) } })
  }, [law, mode])

  const row = view?.rows.get(law)
  const mine = focus ? view?.byItem[focus].segs : null

  const landed = text?.law === law                    // 이 법령의 결과가 왔는가
  const full = landed ? text.text : null             // 다른 법령의 글자는 안 쓴다
  const painted = useMemo(() => {
    if (!full || !row) return null
    return paint(full, row.segs.map((index) => ({
      at: map.segments[index].at,
      to: map.segments[index].at + map.segments[index].chars,
      rank: mine?.has(index) ? 2 : 1,
    })))
  }, [full, row, mine, map])

  // 연 조문으로 내려 둔다. 340,000자 문서에서 손으로 찾으라고 하면 이 화면이 없는 것과 같다.
  const jump = (at) => {
    const box = body.current
    const target = box?.querySelector(`[data-at="${at}"]`)
    if (!box || !target) return
    box.scrollTop = target.offsetTop - box.offsetTop - 12
  }
  // 고른 항목의 조문이 이 법령에 있으면 거기로, 없으면 이 법령의 첫 인용으로 내린다.
  // 아무 데도 안 내리면 앞 문서에서 내려 둔 자리를 그대로 물려받아 엉뚱한 데가 펼쳐진다.
  const here = row && mine ? row.segs.filter((index) => mine.has(index)) : []
  const first = row && (here[0] ?? row.segs[0])
  useEffect(() => {
    if (mode === 'full' && painted && first != null) jump(map.segments[first].at)
    else if (mode === 'cut') body.current?.scrollTo(0, 0)
  }, [mode, painted, first])                            // eslint-disable-line react-hooks/exhaustive-deps

  if (fail) {
    return (
      <p className="pad">
        법령 지도를 못 읽었다: {fail}<br />
        <code>python -X utf8 tools/build_report.py --all</code> 을 먼저 돌린다.
      </p>
    )
  }
  if (!view) return <p className="pad dim">법령 지도 읽는 중…</p>

  const axes = focus ? map.cites[focus] : null

  return (
    <main className="split">
      <LawRail items={items} view={view} focus={focus} law={law}
               onItem={onFocus} onLaw={openLaw} />

      <section className="pane">
        <div className="paneTop">
          <div className="panehead">
            {focus ? (
              <>
                <button className="linkish" onClick={() => onFocus(null)}>← 전체</button>
                <h2>{focus} {items[focus]?.name}</h2>
                <span className="dim">
                  {view.byItem[focus].segs.size
                    ? `근거 ${view.byItem[focus].laws.length}개 법령 · 조문 ${view.byItem[focus].segs.size}곳`
                    : '연결된 조문이 없는 항목이다'}
                </span>
              </>
            ) : (
              <>
                {law && (
                  <button className="linkish" onClick={() => setPicked(null)}>← 법령 × 항목</button>
                )}
                <h2>{law ? shortLaw(law) : '법령'}</h2>
                <span className="dim">{law || '왼쪽에서 항목이나 법령을 고른다'}</span>
              </>
            )}
          </div>

          {/* 한 항목의 근거는 국가·지방 두 갈래로 갈리고 법령도 여럿이다.
              여기서 건너뛰지 못하면 왼쪽 기둥에서 법령 이름을 다시 찾아야 한다. */}
          {focus && view.byItem[focus].laws.length > 0 && (
            <div className="lawjump">
              {view.byItem[focus].laws.map((name) => (
                <button key={name} className={`lawhit${name === law ? ' mine' : ''}`}
                        title={name} onClick={() => setPicked(name)}>
                  {shortLaw(name)}
                  <span className="dim"> {[...view.byItem[focus].segs]
                    .filter((index) => map.segments[index].law === name).length}곳</span>
                </button>
              ))}
            </div>
          )}

          {focus && (
            <div className="lawcite">
              {Object.entries(axes).map(([axis, entry]) => (
                <p key={axis}>
                  <span className="tag">{axis}</span>
                  <q>{entry.citation || '항목표에 빈칸'}</q>
                  {entry.error && <b className="no">주소를 못 풀었다: {entry.error}</b>}
                </p>
              ))}
            </div>
          )}

          {row && (
            <>
              <div className="lawjump">
                <span className="lawbar" title={`${row.chars.toLocaleString()}자 중 인용 ${row.segs.length}곳`}>
                  {row.segs.map((index) => (
                    <i key={index} className={mine && !mine.has(index) ? 'off' : ''}
                       style={{
                         left: `${(map.segments[index].at / row.chars) * 100}%`,
                         // 340,000자 문서의 300자 조각은 0.09% 라 안 보인다. 최소 너비를 준다
                         width: `${Math.max((map.segments[index].chars / row.chars) * 100, 0.7)}%`,
                       }} />
                  ))}
                </span>
                {row.segs.map((index) => {
                  const segment = map.segments[index]
                  return (
                    <button key={index} onClick={() => jump(segment.at)}
                            className={`lawhit${mine && mine.has(index) ? ' mine' : ''}`}
                            title={[...view.owners[index]].map(([v, a]) => `${v} ${axisMark(a)}`).join(' · ')}>
                      {segment.path.join(' ') || '문서 전체'}
                      <span className="dim"> {segment.chars.toLocaleString()}자</span>
                    </button>
                  )
                })}
              </div>
              <p className="lawhead dim">
                <span className="screens">
                  {[['cut', `발췌 ${row.segs.length}곳`], ['full', `전문 ${row.chars.toLocaleString()}자`]]
                    .map(([key, label]) => (
                      <button key={key} className={mode === key ? 'on' : ''}
                              onClick={() => setMode(key)}>{label}</button>
                    ))}
                </span>
                {law}
                {focus && (here.length
                  ? ` · 진한 곳 ${here.length}곳이 ${focus} 의 근거다`
                  : ` · ${focus} 의 근거는 이 법령에 없다. 나머지는 다른 항목의 인용이다`)}
              </p>
            </>
          )}
        </div>

        <div className={`paneScroll${mode === 'full' ? ' lawfull' : ''}`} ref={body} tabIndex={0}>
          {law ? (
            mode === 'cut' ? row.segs.map((index) => (
              <LawCut key={index} segment={map.segments[index]} mine={mine?.has(index)}
                      cited={[...view.owners[index]].sort(
                        (a, b) => ITEMS.indexOf(a[0]) - ITEMS.indexOf(b[0]))} />
            ))
            : painted ? painted
            : landed && !full
              ? <p className="dim">전문을 못 읽었다. <code>npm run dev</code> 상태인지 본다.</p>
              : <p className="dim">전문 읽는 중… ({row?.chars.toLocaleString()}자)</p>
          ) : (
            <LawGrid items={items} view={view} focus={focus} onItem={onFocus} onLaw={openLaw} />
          )}
        </div>
      </section>
    </main>
  )
}
