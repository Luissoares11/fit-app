import { useState } from 'react'
import { savePlan } from '../../api'
import { WEEKDAY_NAMES } from '../../dates'

// One entry per weekday, Monday first: null = rest day, array = training day with its group ids
function toDraft(plan) {
  const byDay = Object.fromEntries(plan.days.map((d) => [d.weekday, d.muscle_group_ids]))
  return WEEKDAY_NAMES.map((_, i) => byDay[i] ?? null)
}

export default function Plan({ groups, plan, onSaved }) {
  const [draft, setDraft] = useState(() => toDraft(plan))
  const [status, setStatus] = useState({ type: 'idle', message: '' })

  const busy = status.type === 'busy'
  const trainingDays = draft.filter((d) => d !== null).length

  function toggleDay(i) {
    setDraft((d) => d.map((v, j) => (j === i ? (v === null ? [] : null) : v)))
  }

  function toggleGroup(i, groupId) {
    setDraft((d) =>
      d.map((v, j) => {
        if (j !== i) return v
        const selected = new Set(v ?? [])
        if (selected.has(groupId)) selected.delete(groupId)
        else selected.add(groupId)
        // Keep chips in library order so the saved plan is stable
        return groups.filter((g) => selected.has(g.id)).map((g) => g.id)
      }),
    )
  }

  async function save() {
    const empty = draft.findIndex((d) => d !== null && d.length === 0)
    if (empty !== -1) {
      setStatus({ type: 'error', message: `Pick at least one muscle group for ${WEEKDAY_NAMES[empty]}` })
      return
    }

    const days = draft
      .map((ids, weekday) => (ids === null ? null : { weekday, muscle_group_ids: ids }))
      .filter(Boolean)

    setStatus({ type: 'busy', message: 'Saving…' })
    try {
      await savePlan({ days })
      await onSaved()
      setStatus({ type: 'ok', message: 'Plan saved' })
    } catch (err) {
      setStatus({ type: 'error', message: err.message })
    }
  }

  return (
    <>
      <p className="muted">
        {trainingDays} training {trainingDays === 1 ? 'day' : 'days'} per week
      </p>

      <ul className="plan-days">
        {WEEKDAY_NAMES.map((name, i) => {
          const ids = draft[i]
          const training = ids !== null
          return (
            <li key={name} className="plan-day">
              <button
                className="plan-toggle"
                aria-pressed={training}
                onClick={() => toggleDay(i)}
              >
                <span>{name}</span>
                <span className="muted">{training ? 'Training' : 'Rest'}</span>
              </button>

              {training && (
                <div className="chips">
                  {groups.map((g) => {
                    const on = ids.includes(g.id)
                    return (
                      <button
                        key={g.id}
                        className={on ? 'chip on' : 'chip'}
                        aria-pressed={on}
                        onClick={() => toggleGroup(i, g.id)}
                      >
                        {g.name}
                      </button>
                    )
                  })}
                </div>
              )}
            </li>
          )
        })}
      </ul>

      <button className="primary" onClick={save} disabled={busy}>
        {busy ? status.message : 'Save plan'}
      </button>

      {status.type === 'ok' && <p className="status ok">{status.message}</p>}
      {status.type === 'error' && <p className="status error">{status.message}</p>}
    </>
  )
}
