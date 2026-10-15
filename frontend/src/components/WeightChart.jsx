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

// Short label for the x-axis under each point: "13/10", or "start" for the start weight
const shortLabel = (p) => {
  if (!p.date) return 'start'
  const d = toDay(p.date)
  return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`
}

// points: [{ date: 'YYYY-MM-DD', weight_kg }] sorted oldest first.
// Points are evenly spaced, one per logged weight, so the x-axis is the order of logs, not elapsed time.
// A point with date null is the start weight and reads "start".
export default function WeightChart({ points }) {
  const [active, setActive] = useState(null) // index of the hovered or focused point
  const kgs = points.map((p) => p.weight_kg)
  const { lo, hi, ticks } = scale(Math.min(...kgs), Math.max(...kgs))

  const label = (p) => (p.date ? formatDay(toDay(p.date)) : 'start')
  const last = points.length - 1

  const x = (i) => (last === 0 ? PAD.left + PLOT_W / 2 : PAD.left + (i / last) * PLOT_W)
  const y = (kg) => PAD.top + (1 - (kg - lo) / (hi - lo)) * PLOT_H

  const pts = points.map((p, i) => ({ cx: x(i), cy: y(p.weight_kg) }))
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
        aria-label={`Weight from ${label(points[0])} to ${label(points[last])}. Use the arrow keys to read values.`}
        tabIndex={0}
        onPointerDown={onPointerMove}
        onPointerMove={onPointerMove}
        // Touch has no hover: keep the tapped point's tooltip until the next tap
        onPointerLeave={(e) => e.pointerType === 'mouse' && setActive(null)}
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

        {points.map((p, i) => (
          <text
            key={i}
            className="axis"
            x={pts[i].cx}
            y={H - 6}
            // Edge labels hug their edge so they don't run into the y-axis or the chart's right side
            textAnchor={i === 0 && last > 0 ? 'start' : i === last && last > 0 ? 'end' : 'middle'}
          >
            {shortLabel(p)}
          </text>
        ))}

        <path className="area" d={area} />
        <path className="series" d={line} />

        {pts.map((p, i) => (
          <circle key={i} className="point" cx={p.cx} cy={p.cy} r={3.5} />
        ))}
        {hover && <line className="crosshair" x1={hover.cx} x2={hover.cx} y1={PAD.top} y2={base} />}
        {hover && <circle className="dot" cx={hover.cx} cy={hover.cy} r={5} />}
        {!hover && (
          <text className="value" x={pts[last].cx} y={pts[last].cy - 10} textAnchor="end">
            {points[last].weight_kg}
          </text>
        )}
      </svg>

      {hover && (
        <div className="tooltip" style={{ left: `${Math.min(82, Math.max(18, (hover.cx / W) * 100))}%` }}>
          <strong>{hoverPoint.weight_kg} kg</strong> · {label(hoverPoint)}
        </div>
      )}
    </div>
  )
}
