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
  }, [idsKey, openId]) // openId: refetch after the dialog closes so the PRs are current

  const opened = openId === null ? null : exercises.find((e) => e.id === openId) ?? null

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
          <section key={g.id} className="card today-section">
            <h3 className="today-section-title">{g.name}</h3>
            {items.length === 0 && <p className="muted small">No exercises in this group yet.</p>}
            <ul className="today-list">
              {items.map((e) => (
                <li key={e.id}>
                  <button className="today-row" onClick={() => setOpenId(e.id)}>
                    <span className="today-name">{e.name}</span>
                    <PrLine rec={records?.[e.id]} />
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )
      })}

      {opened && (
        <ExerciseDetail
          key={opened.id}
          exercise={opened}
          groups={groups}
          groupName={groups.find((g) => g.id === opened.muscle_group_id)?.name}
          onChanged={onChanged}
          onClose={() => setOpenId(null)}
        />
      )}
    </>
  )
}

// The PR, right-aligned on the exercise row: the weight and reps, then the day it was set
function PrLine({ rec }) {
  if (!rec) return <span className="today-pr muted small">…</span>

  if (rec.heaviest) {
    return (
      <span className="today-pr">
        <strong>{kg(rec.heaviest.weight_kg)} kg × {rec.heaviest.reps}</strong>
        <span className="muted small">{formatDay(toDay(rec.heaviest.date))}</span>
      </span>
    )
  }

  if (rec.most_reps !== null) {
    return (
      <span className="today-pr">
        <strong>{rec.most_reps} reps</strong>
        <span className="muted small">bodyweight</span>
      </span>
    )
  }

  return <span className="today-pr muted small">No PR yet</span>
}
