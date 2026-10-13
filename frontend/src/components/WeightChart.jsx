import { useState } from 'react'
import { formatDay, toDay } from '../dates'

const W = 320
const H = 200
const PAD = { top: 16, right: 12, bottom: 26, left: 40 }
const PLOT_W = W - PAD.left - PAD.right
const PLOT_H = H - PAD.top - PAD.bottom

// Round step so the y-axis covers the data with about 2-4 ticks
function scale(min, max) {
  const raw = (max - min || 1) / 3
  const mag = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= raw)
  const lo = Math.floor(min / step) * step
  const hi = Math.max(Math.ceil(max / step) * step, lo + step)
  const ticks = []
  for (let i = 0; lo + i * step <= hi + step / 2; i++) ticks.push(+(lo + i * step).toFixed(2))
  return { lo, hi, ticks }
}

// points: [{ date: 'YYYY-MM-DD', weight_kg }] sorted oldest first
export default function WeightChart({ points }) {
  const [active, setActive] = useState(null) // index of the hovered or focused point
  const kgs = points.map((p) => p.weight_kg)
  const { lo, hi, ticks } = scale(Math.min(...kgs), Math.max(...kgs))

  const t0 = toDay(points[0].date).getTime()
  const span = toDay(points.at(-1).date).getTime() - t0
  const last = points.length - 1

  const x = (p) =>
    span === 0 ? PAD.left + PLOT_W / 2 : PAD.left + ((toDay(p.date).getTime() - t0) / span) * PLOT_W
  const y = (kg) => PAD.top + (1 - (kg - lo) / (hi - lo)) * PLOT_H

  const pts = points.map((p) => ({ cx: x(p), cy: y(p.weight_kg) }))
  const line = pts.map(({ cx, cy }, i) => `${i ? 'L' : 'M'}${cx} ${cy}`).join(' ')
  const base = PAD.top + PLOT_H
  const area = `${line} L${pts[last].cx} ${base} L${pts[0].cx} ${base} Z`

  // Crosshair snaps to the nearest logged date, so the reader aims at a day, not a line
  function nearest(vx) {
    let best = 0
    pts.forEach((p, i) => {
      if (Math.abs(p.cx - vx) < Math.abs(pts[best].cx - vx)) best = i
    })
    return best
  }

  function onPointerMove(e) {
    const box = e.currentTarget.getBoundingClientRect()
    setActive(nearest(((e.clientX - box.left) / box.width) * W))
  }

  function onKeyDown(e) {
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return
    e.preventDefault()
    const step = e.key === 'ArrowLeft' ? -1 : 1
    setActive((cur) => Math.min(last, Math.max(0, (cur ?? last) + step)))
  }

  const hover = active === null ? null : pts[active]
  const hoverPoint = active === null ? null : points[active]

  return (
    <div className="chart">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Weight from ${formatDay(toDay(points[0].date))} to ${formatDay(toDay(points[last].date))}. Use the arrow keys to read values.`}
        tabIndex={0}
        onPointerMove={onPointerMove}
        onPointerLeave={() => setActive(null)}
        onFocus={() => setActive(last)}
        onBlur={() => setActive(null)}
        onKeyDown={onKeyDown}
      >
        {ticks.map((v) => (
          <g key={v}>
            <line className="grid" x1={PAD.left} x2={W - PAD.right} y1={y(v)} y2={y(v)} />
            <text className="axis" x={PAD.left - 6} y={y(v)} textAnchor="end" dominantBaseline="middle">
              {v}
            </text>
          </g>
        ))}

        <text className="axis" x={PAD.left} y={H - 6}>
          {formatDay(toDay(points[0].date))}
        </text>
        {last > 0 && (
          <text className="axis" x={W - PAD.right} y={H - 6} textAnchor="end">
            {formatDay(toDay(points[last].date))}
          </text>
        )}

        <path className="area" d={area} />
        <path className="series" d={line} />

        {hover && <line className="crosshair" x1={hover.cx} x2={hover.cx} y1={PAD.top} y2={base} />}
        {hover && <circle className="dot" cx={hover.cx} cy={hover.cy} r={5} />}
        {!hover && <circle className="dot" cx={pts[last].cx} cy={pts[last].cy} r={4} />}
        {!hover && (
          <text className="value" x={pts[last].cx} y={pts[last].cy - 10} textAnchor="end">
            {points[last].weight_kg}
          </text>
        )}
      </svg>

      {hover && (
        <div className="tooltip" style={{ left: `${Math.min(82, Math.max(18, (hover.cx / W) * 100))}%` }}>
          <strong>{hoverPoint.weight_kg} kg</strong> · {formatDay(toDay(hoverPoint.date))}
        </div>
      )}
    </div>
  )
}
