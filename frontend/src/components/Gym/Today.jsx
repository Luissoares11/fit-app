import { useEffect, useState } from 'react'
import { getRecords } from '../../api'
import { WEEKDAY_NAMES, formatDay, localDay, toDay, weekdayIndex } from '../../dates'
import { kg } from './format'
import ExerciseDetail from './ExerciseDetail'

// Read-only: today's planned exercises with each one's PR
export default function Today({ groups, exercises, plan, onChanged }) {
  const todayIndex = weekdayIndex(localDay())
  const plannedGroupIds = plan.days.find((d) => d.weekday === todayIndex)?.muscle_group_ids ?? []
  const planned = groups.filter((g) => plannedGroupIds.includes(g.id))

  const [records, setRecords] = useState(null) // exercise id -> records
  const [error, setError] = useState('')
  const [openId, setOpenId] = useState(null) // exercise open for logging

  const idsKey = exercises
    .filter((e) => plannedGroupIds.includes(e.muscle_group_id))
    .map((e) => e.id)
    .join(',')

  useEffect(() => {
    const ids = idsKey ? idsKey.split(',').map(Number) : []
    Promise.all(ids.map((id) => getRecords(id).then((r) => [id, r])))
      .then((pairs) => setRecords(Object.fromEntries(pairs)))
      .catch((err) => setError(err.message))
  }, [idsKey])

  const opened = openId === null ? null : exercises.find((e) => e.id === openId) ?? null
  if (opened) {
    const group = groups.find((g) => g.id === opened.muscle_group_id)
    return (
      <ExerciseDetail
        key={opened.id}
        exercise={opened}
        groups={groups}
        groupName={group?.name}
        onChanged={onChanged}
        onBack={() => setOpenId(null)}
        backLabel="Today"
      />
    )
  }

  if (error) return <p className="status error">{error}</p>

  if (planned.length === 0) {
    return (
      <section className="card countdown">
        <p className="muted">{WEEKDAY_NAMES[todayIndex]}</p>
        <p className="hero">Rest day</p>
      </section>
    )
  }

  return (
    <>
      <h2 className="today-day">{WEEKDAY_NAMES[todayIndex]}</h2>
      {planned.map((g) => {
        const items = exercises.filter((e) => e.muscle_group_id === g.id)
        return (
          <section key={g.id} className="group">
            <h3 className="today-group">{g.name}</h3>
            {items.length === 0 && <p className="muted hint">No exercises in this group yet.</p>}
            {items.map((e) => (
              <button key={e.id} className="today-exercise" onClick={() => setOpenId(e.id)}>
                <span className="today-name">{e.name}</span>
                <PrLine rec={records?.[e.id]} />
              </button>
            ))}
          </section>
        )
      })}
    </>
  )
}

function PrLine({ rec }) {
  if (!rec) return <p className="muted small">…</p>

  if (rec.heaviest) {
    return (
      <p className="small">
        PR <strong>{kg(rec.heaviest.weight_kg)} kg × {rec.heaviest.reps}</strong>{' '}
        <span className="muted">· {formatDay(toDay(rec.heaviest.date))}</span>
        {rec.best_e1rm && <span className="muted"> · est. 1RM {kg(rec.best_e1rm.value)} kg</span>}
      </p>
    )
  }

  if (rec.most_reps !== null) {
    return (
      <p className="small">
        PR <strong>{rec.most_reps} reps</strong> <span className="muted">(bodyweight)</span>
      </p>
    )
  }

  return <p className="muted small">No PR yet</p>
}
