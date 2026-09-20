import { useEffect, useMemo, useRef, useState } from 'react'
import {
  KIND, KIND_ORDER, TN, FN, FP, TP, ITEMS, quoteInDoc, docText, tally, macroF1, labelGaps,
} from './data.js'

const fmt = (n) => n.toFixed(3)
const shortId = (id) => id.replace(/^PPS-DEV-/, '')
const won = (n) => (typeof n === 'number' ? `${(n / 1e8).toFixed(2)}억` : '—')

/** 왼쪽 기둥. 24항목이 F1 막대를 겸한다 — 목록과 그래프를 따로 둘 이유가 없다. */
export function ItemList({ rows, items, selected, onSelect, sort, onSort, delta }) {
  const ordered = useMemo(
    () => [...rows].sort(sort === 'f1' ? (a, b) => a.f1 - b.f1 || a.item.localeCompare(b.item)
                                        : (a, b) => ITEMS.indexOf(a.item) - ITEMS.indexOf(b.item)),
    [rows, sort],
  )
  return (
    <nav className="items" aria-label="24항목">
      <div className="itemshead">
        <span>항목 24</span>
        <button className="linkish" onClick={() => onSort(sort === 'f1' ? 'id' : 'f1')}>
          {sort === 'f1' ? 'F1 낮은 순' : '번호 순'}
        </button>
      </div>
      <ol>
        {ordered.map((row) => {
          const change = delta?.[row.item]
          return (
            <li key={row.item}>
              <button
                className={`item${selected === row.item ? ' on' : ''}`}
                onClick={() => onSelect(row.item)}
                aria-current={selected === row.item}
              >
                <span className="tag">{row.item}</span>
                <span className="track" aria-hidden="true">
                  <i style={{ width: `${Math.max(row.f1 * 100, row.f1 > 0 ? 2 : 0)}%` }} />
                </span>
                <span className="num">{fmt(row.f1)}</span>
                {change != null && Math.abs(change) > 1e-9 && (
                  <span className={`delta ${change > 0 ? 'up' : 'down'}`}>
                    {change > 0 ? '▲' : '▼'}{Math.abs(change).toFixed(2).slice(1)}
                  </span>
                )}
                <span className="label">
                  {items[row.item]?.name ?? ''}
                  {items[row.item]?.absence && <b className="badge">부재</b>}
                </span>
              </button>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}

/** 한 항목의 200칸. 볼 것(FN·FP·TP)만 크게 두고 TN 180칸 안팎은 접어 둔다. */
export function Strip({ run, item, ids, picked, onPick, flipped }) {
  const index = ITEMS.indexOf(item)
  const groups = KIND_ORDER.map((kind) => [kind, ids.filter((id) => run.grid[id][index] === kind)])
  return (
    <div className="strip">
      {groups.map(([kind, list]) => {
        if (!list.length) return null
        const cells = (
          <div className="cells">
            {list.map((id) => (
              <button
                key={id}
                className={`cell ${KIND[kind].key}${picked === id ? ' on' : ''}${
                  flipped?.has(`${id}|${item}`) ? ' flip' : ''}`}
                onClick={() => onPick(id)}
                title={`${id} · ${KIND[kind].label}`}
              >
                {shortId(id)}
              </button>
            ))}
          </div>
        )
        if (kind !== TN) {
          return (
            <section key={kind} className="group">
              <h4>
                <i className={`swatch ${KIND[kind].key}`} aria-hidden="true" />
                {KIND[kind].mark} {KIND[kind].label} <b>{list.length}</b>
                <span className="dim"> — {KIND[kind].help}</span>
              </h4>
              {cells}
            </section>
          )
        }
        return (
          <details key={kind} className="group tnfold">
            <summary>
              <i className={`swatch ${KIND[kind].key}`} aria-hidden="true" />
              {KIND[kind].label} <b>{list.length}</b>건
              <span className="dim"> — 정답도 0, 예측도 0. 여기서 볼 것은 없다</span>
            </summary>
            {cells}
          </details>
        )
      })}
    </div>
  )
}

/** 여러 조각을 한 본문에 칠한다. 겹치면 먼저 온 조각이 이긴다. */
function mark(text, pieces) {
  const spans = []
  for (const { needle, cls } of pieces) {
    if (!needle) continue
    let from = 0
    for (;;) {
      const at = text.indexOf(needle, from)
      if (at < 0) break
      spans.push({ at, to: at + needle.length, cls })
      from = at + Math.max(1, needle.length)
    }
  }
  spans.sort((a, b) => a.at - b.at)
  const out = []
  let cursor = 0
  for (const span of spans) {
    if (span.at < cursor) continue
    if (span.at > cursor) out.push(text.slice(cursor, span.at))
    out.push(<mark key={`${span.at}-${span.cls}`} className={span.cls}>{text.slice(span.at, span.to)}</mark>)
    cursor = span.to
  }
  out.push(text.slice(cursor))
  return out
}

function Quote({ title, text, verdict }) {
  return (
    <div className="quote">
      <span className="qh">
        {title}
        {verdict === true && <b className="ok">✓ 원문에 있음</b>}
        {verdict === false && <b className="no">✘ 원문에 없음 — 모델이 다듬었다</b>}
      </span>
      {text ? <q>{text}</q> : <span className="dim">없음</span>}
    </div>
  )
}

const META_KEYS = ['적용계약법', '계약방법', '낙찰방법', '소관구분', '지역제한여부', '업종제한여부',
                   '조항호내용', '세부품명번호목록', '정보화사업여부', '긴급공고여부']

/** 한 칸을 눌렀을 때의 모든 것. 원문·근거·모델 판정이 한 자리에 선다. */
export function Detail({ run, corpus, item, id, absence }) {
  const [find, setFind] = useState('')
  const [tab, setTab] = useState(null)
  const boxRef = useRef(null)
  useEffect(() => { setTab(null); setFind(''); boxRef.current?.scrollTo(0, 0) }, [id, item])

  const row = corpus.docs[id]
  if (!row) return <p className="dim pad">{id} 의 원문이 dev.jsonl 에 없다.</p>

  const index = ITEMS.indexOf(item)
  const kind = run.grid[id][index]
  const predQuote = run.evidence?.[id]?.[item] ?? ''
  const truthQuote = corpus.truth[id]?.evidence?.[item] ?? ''
  const truthPositive = corpus.truth[id]?.values[index] === 1
  const gaps = labelGaps(corpus)

  // 근거가 든 문서를 먼저 편다. 검증은 문서 전체를 보는데 칠하기는 보이는 탭만 보므로,
  // 공고문을 고정으로 열면 `원문에 있음` 이라고 해 놓고 아무 데도 안 칠해진 화면이 나온다.
  const holds = row.docs.map((d) => [predQuote, truthQuote].some((q) => q && d.text.includes(q)))
  const active = tab ?? Math.max(0, holds.indexOf(true))
  const doc = row.docs[active]
  const trace = run.trace?.[id] ?? {}
  const debug = trace.debug ?? null // 별도 추론의 원응답. dev 통계와 섞지 않는다

  // 둘이 같은 문자열이면 한 조각만 남는다. 그때 `truth` 로만 칠하면 모델이
  // 정확히 맞혔다는 사실이 화면에서 사라지므로 합친 표시를 쓴다.
  const same = predQuote && predQuote === truthQuote
  const pieces = [
    { needle: same ? predQuote : truthQuote, cls: same ? 'both' : 'truth' },
    { needle: same ? '' : predQuote, cls: 'pred' },
    { needle: find.trim(), cls: 'find' },
  ]
  const hits = find.trim() ? docText(row).split(find.trim()).length - 1 : null

  return (
    <div className="detail">
      <header className="dhead">
        <b className="mono">{id}</b>
        <span className={`pill ${KIND[kind].key}`}>{KIND[kind].mark} {KIND[kind].label}</span>
        <span className="dim">
          정답 {corpus.truth[id]?.values[index]} / 예측 {run.grid[id][index] === TP || run.grid[id][index] === FP ? 1 : 0}
        </span>
        {absence && <span className="badge">부재탐지 — e열은 규약상 빈칸</span>}
      </header>

      <div className="chips">
        <span className="chip">배정예산 <b>{won(row.meta?.배정예산금액)}</b></span>
        <span className="chip">추정가격 <b>{won(row.meta?.입찰추정가격)}</b></span>
        <span className={`chip${row.input_completeness?.완전관측 ? '' : ' warn'}`}>
          완전관측 <b>{row.input_completeness?.완전관측 ? '예' : '아니요'}</b>
        </span>
        {META_KEYS.map((key) => {
          const value = row.meta?.[key]
          if (value == null || value === '' || value === '미입력') return null
          return <span key={key} className="chip">{key} <b>{String(value)}</b></span>
        })}
      </div>

      {absence ? (
        <p className="note">
          이 항목은 <b>없는 것</b>이 위반이라 인용할 문장이 없다. 위 등록값과 아래 원문에서
          <b> 있었어야 할 제한</b>이 정말 빠졌는지 본다.
        </p>
      ) : (
        <>
          <Quote title="제출 근거 (e열)" text={predQuote}
                 verdict={predQuote ? quoteInDoc(predQuote, row) : undefined} />
          {truthPositive && <Quote title="정답 근거" text={truthQuote} />}
          {/* 정답이 0인 칸(TN·FP)에는 애초에 근거가 없는 게 맞다. 안내는 정답이 1일 때만.
              수치는 박지 않고 라벨에서 센다 — 전에 적힌 "153칸 중 68칸"은 밑이 섞인 말이었다. */}
          {truthPositive && !truthQuote && (
            <p className="note dim">
              정답 라벨에 근거가 없는 칸이다 (부재탐지 제외 양성 {gaps.positives}칸 중 {gaps.missing}칸).
              아래에서 직접 찾는다.
            </p>
          )}
        </>
      )}

      <div className="findrow">
        <input
          type="search"
          value={find}
          placeholder="원문에서 찾기 — 예: 소기업, 지역, 실적"
          onChange={(event) => setFind(event.target.value)}
          aria-label="원문에서 찾기"
        />
        {hits != null && <span className="dim mono">{hits}곳</span>}
        <span className="spacer" />
        <div className="tabs" role="tablist">
          {row.docs.map((d, i) => (
            <button key={d.doc_id} role="tab" aria-selected={active === i}
                    className={active === i ? 'on' : ''} onClick={() => setTab(i)}
                    title={holds[i] ? '이 문서에 근거 문구가 있다' : undefined}>
              {d.type}
              {holds[i] && <i className="dotmark" aria-label="근거 있음" />}
            </button>
          ))}
        </div>
      </div>

      <div className="marklegend">
        {same ? (
          <span className="lg"><i className="swatch mk both" aria-hidden="true" />제출 근거 = 정답 근거</span>
        ) : (
          <>
            {predQuote && <span className="lg"><i className="swatch mk pred" aria-hidden="true" />제출 근거</span>}
            {truthQuote && <span className="lg"><i className="swatch mk truth" aria-hidden="true" />정답 근거</span>}
          </>
        )}
        {find.trim() && <span className="lg"><i className="swatch mk find" aria-hidden="true" />찾는 말</span>}
        <span className="dim">{doc.doc_id} · {doc.text.length.toLocaleString()}자</span>
      </div>
      <div className="doc" ref={boxRef} tabIndex={0}>{mark(doc.text, pieces)}</div>

      <details className="model">
        <summary>모델 판정 <span className="dim">— 채점된 이 회차(dev)의 흔적</span></summary>
        {trace.company_size && (
          <pre>company_size_verified {JSON.stringify(trace.company_size, null, 1)}</pre>
        )}
        {trace.sme && <pre>sme_verified {JSON.stringify(trace.sme, null, 1)}</pre>}
        {trace.responses?.map((r, i) => (
          <p key={i} className="dim mono">
            {r.phase} · {r.status} · {r.response_chars}자 · {r.output_tokens}토큰 · {r.finish_reason}
          </p>
        ))}
        {!trace.company_size && !trace.sme && !trace.responses && (
          <p className="dim">이 회차의 diagnostics 에 이 건의 흔적이 없다.</p>
        )}
      </details>

      {/* 원응답은 dev-debug 의 것이고 그건 별도 추론이다. 49열이 같아도 응답 길이가 다른
          경우가 있어(451개 중 31개) 위 통계와 한 묶음으로 두면 같은 실행처럼 읽힌다. */}
      <details className="model debug">
        <summary>
          dev-debug 원응답
          {debug
            ? <span className="dim"> — <b>별도 추론</b>이다. 49열 출력만 이 회차와 같다</span>
            : <span className="dim"> — {run.raw_note ?? '이 회차엔 보관된 원응답이 없다'}</span>}
        </summary>
        {debug?.responses?.map((r, i) => (
          <p key={i} className="dim mono">
            {r.phase} · {r.status} · {r.response_chars}자 · {r.output_tokens}토큰 · {r.finish_reason}
            <span className="warn-inline"> (dev-debug 측정값)</span>
          </p>
        ))}
        {debug?.raw.map((r, i) => (
          <pre key={i} className="raw">{r.phase}{'\n'}{r.text}</pre>
        ))}
      </details>
    </div>
  )
}

/** 제출 근거가 원문의 연속 부분문자열이 아닌 것만. 리더보드엔 안 보이고 2차에서 터진다.
 *
 *  분모는 `evidence` 에 실린 것이 아니라 **grid 의 부재탐지 아닌 양성 예측 전부**다.
 *  실린 것만 세면 e열을 아예 안 낸 칸이 검사 대상에서 통째로 빠져, 최신 회차에서 빈 45칸이
 *  없는 것처럼 보였다(181 중 136 만 셌다). 빈 e열은 통과가 아니라 실패다. */
export function EvidenceAudit({ run, corpus, ids, onOpen }) {
  const audit = useMemo(() => {
    const missing = []
    const wrong = []
    let checked = 0
    for (const id of ids) {
      for (const [index, cell] of [...run.grid[id]].entries()) {
        const item = ITEMS[index]
        if (cell !== TP && cell !== FP) continue
        if (corpus.items[item]?.absence) continue // 규약상 e가 빈칸이다
        checked += 1
        const quote = run.evidence?.[id]?.[item] ?? ''
        if (!quote) missing.push({ id, item, quote: '', why: '빈칸' })
        else if (!quoteInDoc(quote, corpus.docs[id])) wrong.push({ id, item, quote, why: '원문에 없음' })
      }
    }
    return { checked, missing, wrong, bad: [...missing, ...wrong] }
  }, [run, corpus, ids])

  return (
    <figure className="chart">
      <figcaption>
        근거 검증 <span className="dim">— 제출 e열이 공고 원문의 연속 부분문자열인가</span>
      </figcaption>
      <p className="auditline">
        <b className="ok">✓ {audit.checked - audit.bad.length}</b>
        <b className={audit.missing.length ? 'no' : 'ok'}>빈칸 {audit.missing.length}</b>
        <b className={audit.wrong.length ? 'no' : 'ok'}>원문에 없음 {audit.wrong.length}</b>
        <span className="dim">
          부재탐지 제외 양성 예측 {audit.checked}칸 중. score.py 는 이걸 미검증으로 둔다
        </span>
      </p>
      {audit.bad.length > 0 && (
        <ul className="auditlist">
          {audit.bad.slice(0, 40).map((miss) => (
            <li key={`${miss.id}${miss.item}`}>
              <button className="linkish mono" onClick={() => onOpen(miss.item, miss.id)}>
                {shortId(miss.id)} {miss.item}
              </button>
              <span className="no">{miss.why}</span>
              <q>{miss.quote.slice(0, 80)}</q>
            </li>
          ))}
        </ul>
      )}
    </figure>
  )
}

/** 점수가 낮은 게 판단 탓인지 입력이 잘려서인지. 필터를 두 번 걸지 않고 한 줄로 가른다. */
export function InputSplit({ run, corpus, ids }) {
  const split = useMemo(() => {
    const full = ids.filter((id) => corpus.docs[id]?.input_completeness?.완전관측 === true)
    const partial = ids.filter((id) => corpus.docs[id]?.input_completeness?.완전관측 !== true)
    return [
      { label: '완전관측', ids: full, help: '문서가 다 들어왔다' },
      { label: '결손', ids: partial, help: '규격서·제안요청서가 탈락했거나 추출이 실패했다' },
    ].map((band) => ({
      ...band,
      count: band.ids.length,
      macro: band.ids.length ? macroF1(tally(run, band.ids)) : null,
    }))
  }, [run, corpus, ids])

  return (
    <figure className="chart">
      <figcaption>
        입력 결손 대비 <span className="dim">— 판단이 틀린 것과 문서가 안 들어온 것은 다른 고침이다</span>
      </figcaption>
      <div className="stack">
        {split.map((band) => (
          <div key={band.label} className="stackrow" style={{ cursor: 'default' }}>
            <span className="tag">{band.label}</span>
            <span className="barwrap">
              <span className="bars" style={{ width: `${(band.macro ?? 0) * 100}%` }}>
                <i className="seg tp" style={{ flexGrow: 1 }} />
              </span>
              <span className="num dim">{band.macro == null ? '—' : band.macro.toFixed(3)}</span>
            </span>
            <span className="label">{band.count}건 · {band.help}</span>
          </div>
        ))}
      </div>
    </figure>
  )
}

/** 부재탐지 5항목만. 없는 것을 찾는 과제라 오랫동안 같이 막혀 있었다. */
export function AbsencePanel({ rows, items, onSelect }) {
  const only = rows.filter((row) => items[row.item]?.absence)
  const standing = only.filter((row) => row.tp > 0).length
  return (
    <figure className="chart">
      <figcaption>
        부재탐지 5항목 <span className="dim">— e열이 규약상 빈칸인 항목들. 지금 {standing}/5 가 서 있다</span>
      </figcaption>
      <div className="stack">
        {only.map((row) => (
          <button key={row.item} className="stackrow" onClick={() => onSelect(row.item)}>
            <span className="tag">{row.item}</span>
            <span className="barwrap">
              <span className="bars" style={{ width: `${Math.max(row.f1 * 100, 2)}%` }}>
                <i className={`seg ${row.tp ? 'tp' : 'fn'}`} style={{ flexGrow: 1 }} />
              </span>
              <span className="num dim">{row.f1.toFixed(3)} · {row.tp}/{row.fp}/{row.fn}</span>
            </span>
            <span className="label">{items[row.item]?.name}</span>
          </button>
        ))}
      </div>
    </figure>
  )
}

/** 점수가 낮은 게 판단 탓인지 응답이 잘린 탓인지. finish_reason 이 그걸 안다. */
export function ResponseHealth({ run, ids }) {
  const stats = useMemo(() => {
    const finish = {}
    const status = {}
    let total = 0
    let retried = 0
    let missing = 0
    for (const id of ids) {
      const responses = run.trace?.[id]?.responses
      if (!responses?.length) { missing += 1; continue }
      for (const response of responses) {
        total += 1
        finish[response.finish_reason ?? '—'] = (finish[response.finish_reason ?? '—'] ?? 0) + 1
        status[response.status ?? '—'] = (status[response.status ?? '—'] ?? 0) + 1
        if ((response.attempt ?? 1) > 1) retried += 1
      }
    }
    return { finish, status, total, retried, missing }
  }, [run, ids])

  if (!stats.total) return null
  const cut = stats.finish['length'] ?? 0 // finish_reason 이 'length' 면 한도에서 잘린 응답이다
  return (
    <figure className="chart">
      <figcaption>
        원응답 품질 <span className="dim">— 판단이 틀린 것과 출력이 잘린 것은 다른 고침이다</span>
      </figcaption>
      <p className="auditline">
        <b>{stats.total}</b><span className="dim">응답</span>
        <b className={cut ? 'no' : 'ok'}>{cut}</b>
        <span className="dim">길이 한도에서 잘림(finish_reason=length)</span>
        <b className={stats.retried ? 'no' : 'ok'}>{stats.retried}</b><span className="dim">재시도</span>
        {stats.missing > 0 && <span className="dim">· 흔적 없는 공고 {stats.missing}건</span>}
      </p>
      <div className="chips">
        {Object.entries(stats.status).map(([name, count]) => (
          <span key={name} className={`chip${name === 'valid' ? '' : ' warn'}`}>
            status {name} <b>{count}</b>
          </span>
        ))}
        {Object.entries(stats.finish).map(([name, count]) => (
          <span key={name} className={`chip${name === 'length' ? ' warn' : ''}`}>
            finish {name} <b>{count}</b>
          </span>
        ))}
      </div>
    </figure>
  )
}

export { FN, FP, TP, TN }
