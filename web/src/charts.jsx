import { useState } from 'react'
import { KIND, TP, FP, FN } from './data.js'

const fmt = (n) => n.toFixed(3)

/** 항목별 TP/FP/FN 누적 막대. 같은 F1 0.000 이라도 전부 놓친 것과 마구 잡은 것은 다르다. */
export function StackedBars({ rows, items, selected, onSelect }) {
  const widest = Math.max(1, ...rows.map((r) => r.tp + r.fp + r.fn))
  return (
    <figure className="chart">
      <figcaption>
        항목별 오답 구성 <span className="dim">— 가로 길이는 TP+FP+FN 건수</span>
      </figcaption>
      <Legend kinds={[TP, FP, FN]} />
      <div className="stack" role="list">
        {rows.map((row) => {
          const total = row.tp + row.fp + row.fn
          return (
            <button
              key={row.item}
              role="listitem"
              className={`stackrow${selected === row.item ? ' on' : ''}`}
              onClick={() => onSelect(row.item)}
              title={`${row.item} ${items[row.item]?.name ?? ''}`}
            >
              <span className="tag">{row.item}</span>
              {/* 수치는 막대 끝에 붙인다. 오른쪽 끝에 세우면 1600px 화면에서 둘이 멀어진다 */}
              <span className="barwrap">
                <span className="bars" style={{ width: `${(total / widest) * 100}%` }}>
                  {[TP, FP, FN].map((kind) => {
                    const value = row[KIND[kind].key]
                    if (!value) return null
                    return (
                      <i
                        key={kind}
                        className={`seg ${KIND[kind].key}`}
                        style={{ flexGrow: value }}
                        aria-label={`${KIND[kind].label} ${value}`}
                      >
                        {value >= 3 ? value : ''}
                      </i>
                    )
                  })}
                </span>
                <span className="num dim">{total ? `${row.tp}/${row.fp}/${row.fn}` : '—'}</span>
              </span>
              <span className="label">{items[row.item]?.name ?? ''}</span>
            </button>
          )
        })}
      </div>
    </figure>
  )
}

export function Legend({ kinds, extra }) {
  return (
    <div className="legend">
      {kinds.map((kind) => (
        <span key={kind} className="lg" title={KIND[kind].help}>
          <i className={`swatch ${KIND[kind].key}`} aria-hidden="true" />
          {KIND[kind].label}
        </span>
      ))}
      {extra}
    </div>
  )
}

const W = 720
const H = 190
const PAD = { l: 42, r: 58, t: 14, b: 24 }

/** 회차별 F1 추이. Macro 와 고른 항목 둘만 그린다 — 24줄은 실타래가 된다. */
export function Trend({ history, item, itemName, current, compare, onPick }) {
  const [hover, setHover] = useState(null)
  if (history.length < 2) return null

  const x = (i) => PAD.l + (i * (W - PAD.l - PAD.r)) / (history.length - 1)
  const y = (v) => PAD.t + (1 - v) * (H - PAD.t - PAD.b)
  const line = (get) => history.map((run, i) => `${i ? 'L' : 'M'}${x(i)} ${y(get(run))}`).join(' ')

  const series = [
    { key: 'macro', label: 'Macro F1', get: (run) => run.macro_f1, cls: 'macro' },
    item && {
      key: item,
      label: `${item} ${itemName ?? ''}`.trim(),
      get: (run) => run.items_f1?.[item] ?? 0,
      // `item` 을 쓰면 왼쪽 목록의 `.item` 규칙이 차트 요소 21개에 걸린다. 실제로 범례가
      // padding 5px 6px 를 먹어 14×3 이어야 할 것이 14×10 이 됐다.
      cls: 'focus',
    },
  ].filter(Boolean)

  const near = hover == null ? null : history[hover]

  return (
    <figure className="chart">
      <figcaption>
        회차 추이 <span className="dim">— {history.length}회차, 점을 누르면 그 회차로 간다</span>
      </figcaption>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="trend"
        role="img"
        aria-label={`회차별 F1 추이 ${history.length}회차`}
        onMouseLeave={() => setHover(null)}
      >
        {[0, 0.25, 0.5, 0.75, 1].map((v) => (
          <g key={v}>
            <line className="grid" x1={PAD.l} x2={W - PAD.r} y1={y(v)} y2={y(v)} />
            <text className="tick" x={PAD.l - 8} y={y(v) + 4} textAnchor="end">{v.toFixed(2)}</text>
          </g>
        ))}
        {series.map((s) => (
          <path key={s.key} className={`trendline ${s.cls}`} d={line(s.get)} />
        ))}
        {series.map((s) => (
          <text
            key={s.key}
            className={`endlabel ${s.cls}`}
            x={W - PAD.r + 8}
            y={y(s.get(history.at(-1))) + 4}
          >
            {fmt(s.get(history.at(-1)))}
          </text>
        ))}
        {history.map((run, i) => {
          const isCurrent = run.run_id === current
          const isCompare = run.run_id === compare
          return (
            <g key={run.run_id}>
              {(isCurrent || isCompare) && (
                <line className={`mark ${isCurrent ? 'cur' : 'cmp'}`} x1={x(i)} x2={x(i)}
                      y1={PAD.t} y2={H - PAD.b} />
              )}
              {series.map((s) => (
                <circle key={s.key} className={`dot ${s.cls}${hover === i ? ' on' : ''}`}
                        cx={x(i)} cy={y(s.get(run))} r={hover === i ? 5 : 3} />
              ))}
              {/* 손가락으로 집는 자리는 점보다 넓다 */}
              <rect x={x(i) - 14} y={PAD.t} width="28" height={H - PAD.t - PAD.b}
                    fill="transparent" onMouseEnter={() => setHover(i)}
                    onClick={() => onPick(run.run_id)} style={{ cursor: 'pointer' }} />
            </g>
          )
        })}
      </svg>
      <div className="trendfoot">
        <Legend
          kinds={[]}
          extra={
            <>
              {series.map((s) => (
                <span key={s.key} className="lg">
                  <i className={`swatch ln ${s.cls}`} aria-hidden="true" />
                  {s.label}
                </span>
              ))}
            </>
          }
        />
        <span className="dim mono">
          {near
            ? `${near.run_id.slice(-6)} · Macro ${fmt(near.macro_f1)}${
                item ? ` · ${item} ${fmt(near.items_f1?.[item] ?? 0)}` : ''
              }`
            : '가리키면 그 회차 값'}
        </span>
      </div>
    </figure>
  )
}
