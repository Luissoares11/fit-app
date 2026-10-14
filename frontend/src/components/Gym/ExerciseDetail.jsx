import { useEffect, useRef, useState } from 'react'
import { deleteSet, getRecords, logSets, updateSet } from '../../api'
import { formatDay, toDay, todayIso } from '../../dates'
import DateInput from '../DateInput'
import { kg, parseKg, parseReps, prText } from './format'
import ExerciseForm from './ExerciseForm'

export default function ExerciseDetail({ exercise, groups, groupName, onChanged, onBack, backLabel = 'Exercises' }) {
  const [records, setRecords] = useState(null)
  const [editingExercise, setEditingExercise] = useState(false)
  const [date, setDate] = useState(todayIso())
  const [weight, setWeight] = useState('')
  const [reps, setReps] = useState('')
  const [logged, setLogged] = useState([]) // sets saved during this visit
  const [prs, setPrs] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [editingSet, setEditingSet] = useState(null) // { id, weight, reps }
  const repsRef = useRef(null)

  function load() {
    return getRecords(exercise.id).then(setRecords)
  }

  useEffect(() => {
    getRecords(exercise.id)
      .then(setRecords)
      .catch((err) => setError(err.message))
  }, [exercise.id])

  async function logSet(e) {
    e.preventDefault()
    setError('')
    setPrs([])

    const kgValue = parseKg(weight)
    if (kgValue === null || kgValue < 0 || kgValue > 1000) {
      setError('Enter a weight between 0 and 1000 kg (0 for bodyweight)')
      return
    }
    const repsValue = parseReps(reps)
    if (repsValue === null || repsValue < 1 || repsValue > 200) {
      setError('Enter whole reps between 1 and 200')
      return
    }
    if (!date) {
      setError('Enter a valid date (dd/mm/yyyy)')
      return
    }
    if (date > todayIso()) {
      setError('The date cannot be in the future')
      return
    }

    setBusy(true)
    try {
      const res = await logSets(exercise.id, { date, sets: [{ weight_kg: kgValue, reps: repsValue }] })
      setLogged((list) => [...list, { weight_kg: kgValue, reps: repsValue }])
      setPrs(res.new_prs)
      // Same weight is common between sets, so keep date and weight and go straight to reps
      setReps('')
      repsRef.current?.focus()
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function saveSetEdit(e) {
    e.preventDefault()
    const kgValue = parseKg(editingSet.weight)
    const repsValue = parseReps(editingSet.reps)
    if (kgValue === null || kgValue < 0 || kgValue > 1000 || repsValue === null || repsValue < 1 || repsValue > 200) {
      setError('Check the weight and reps of that set')
      return
    }
    try {
      await updateSet(editingSet.id, { weight_kg: kgValue, reps: repsValue })
      setEditingSet(null)
      setError('')
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  async function removeSet(s) {
    if (!window.confirm(`Delete ${kg(s.weight_kg)} kg × ${s.reps}?`)) return
    try {
      await deleteSet(s.id)
      setError('')
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  const hasSets = records && records.history.length > 0

  return (
    <div className="detail">
      <header className="detail-head">
        <button className="link" onClick={onBack}>
          ← {backLabel}
        </button>
        <button className="link" onClick={() => setEditingExercise((v) => !v)}>
          {editingExercise ? 'Close' : 'Edit'}
        </button>
      </header>

      <h2 className="detail-title">{exercise.name}</h2>
      <p className="muted">{groupName}</p>

      {editingExercise && (
        <ExerciseForm
          groups={groups}
          exercise={exercise}
          canDelete={records !== null && !hasSets}
          onChanged={onChanged}
          onDone={() => setEditingExercise(false)}
          onError={setError}
        />
      )}

      <section className="card">
        <h2 className="section-title">Log a set</h2>
        <form onSubmit={logSet}>
          <label className="field">
            <span>Date</span>
            <DateInput defaultValue={date} onChange={setDate} />
          </label>

          <div className="row-2">
            <label className="field">
              <span>Weight (kg)</span>
              <input
                type="text"
                inputMode="decimal"
                placeholder="80.5"
                value={weight}
                onChange={(e) => setWeight(e.target.value)}
              />
            </label>
            <label className="field">
              <span>Reps</span>
              <input
                ref={repsRef}
                type="text"
                inputMode="numeric"
                value={reps}
                onChange={(e) => setReps(e.target.value)}
              />
            </label>
          </div>
          <p className="muted small">0 for bodyweight</p>

          <button className="primary" disabled={busy}>
            {busy ? 'Saving…' : 'Log set'}
          </button>
        </form>

        {error && <p className="status error">{error}</p>}

        {prs.length > 0 && (
          <div className="pr-banner">
            <strong>New PR</strong>
            {prs.map((pr, i) => (
              <p key={i}>{prText(pr)}</p>
            ))}
          </div>
        )}

        {logged.length > 0 && (
          <div className="logged-now">
            <h3 className="day-title">Logged now</h3>
            <ul className="set-list">
              {logged.map((s, i) => (
                <li key={i}>
                  <span>
                    {kg(s.weight_kg)} kg × {s.reps}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      <section className="card">
        <h2 className="section-title">Records</h2>
        {!hasSets ? (
          <p className="muted">No sets logged yet</p>
        ) : (
          <>
            <div className="stat-grid">
              <div className="stat">
                <span className="muted">Heaviest</span>
                <span className="value">
                  {records.heaviest ? `${kg(records.heaviest.weight_kg)} × ${records.heaviest.reps}` : '—'}
                </span>
                {records.heaviest && <span className="muted small">{formatDay(toDay(records.heaviest.date))}</span>}
              </div>
              <div className="stat">
                <span className="muted">Est. 1RM</span>
                <span className="value">{records.best_e1rm ? `${kg(records.best_e1rm.value)} kg` : '—'}</span>
                {records.best_e1rm && (
                  <span className="muted small">
                    {kg(records.best_e1rm.weight_kg)} × {records.best_e1rm.reps}
                  </span>
                )}
              </div>
            </div>

            {records.by_reps.length > 0 && (
              <table className="records-table">
                <thead>
                  <tr>
                    <th>Reps</th>
                    <th>Best</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {records.by_reps.map((r) => (
                    <tr key={r.reps}>
                      <td>{r.reps}</td>
                      <td>{kg(r.weight_kg)} kg</td>
                      <td>{formatDay(toDay(r.date))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {records.most_reps !== null && <p className="muted small">Most reps (bodyweight): {records.most_reps}</p>}
          </>
        )}
      </section>

      <section>
        <h2 className="section-title">History</h2>
        {!hasSets && <p className="muted">Nothing logged yet.</p>}
        {records?.history.map((day) => (
          <div key={day.date} className="history-day">
            <h3 className="day-title">{formatDay(toDay(day.date))}</h3>
            <ul className="set-list">
              {day.sets.map((s) =>
                editingSet?.id === s.id ? (
                  <li key={s.id}>
                    <form className="set-edit" onSubmit={saveSetEdit}>
                      <input
                        type="text"
                        inputMode="decimal"
                        aria-label="Weight (kg)"
                        value={editingSet.weight}
                        onChange={(e) => setEditingSet({ ...editingSet, weight: e.target.value })}
                      />
                      <input
                        type="text"
                        inputMode="numeric"
                        aria-label="Reps"
                        value={editingSet.reps}
                        onChange={(e) => setEditingSet({ ...editingSet, reps: e.target.value })}
                      />
                      <button className="link">Save</button>
                      <button type="button" className="link" onClick={() => setEditingSet(null)}>
                        Cancel
                      </button>
                    </form>
                  </li>
                ) : (
                  <li key={s.id}>
                    <span>
                      {kg(s.weight_kg)} kg × {s.reps}
                    </span>
                    <span className="set-actions">
                      <button
                        className="link"
                        onClick={() => setEditingSet({ id: s.id, weight: kg(s.weight_kg), reps: String(s.reps) })}
                      >
                        Edit
                      </button>
                      <button className="link danger" onClick={() => removeSet(s)}>
                        Delete
                      </button>
                    </span>
                  </li>
                ),
              )}
            </ul>
          </div>
        ))}
      </section>
    </div>
  )
}
