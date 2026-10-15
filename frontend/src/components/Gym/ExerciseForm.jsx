import { useEffect, useState } from 'react'
import { createExercise, deleteExercise, getRecords, updateExercise } from '../../api'

// Add (no exercise) or edit (rename, move, delete) an exercise.
// Deleting an exercise also deletes its logged sets, so the form warns when it has any.
// Total logged sets across all days in an exercise's records
const countSets = (rec) => rec.history.reduce((n, day) => n + day.sets.length, 0)

export default function ExerciseForm({ groups, exercise, defaultGroupId, onChanged, onDone }) {
  const [name, setName] = useState(exercise?.name ?? '')
  const [groupId, setGroupId] = useState(exercise?.muscle_group_id ?? defaultGroupId)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [logCount, setLogCount] = useState(0)

  useEffect(() => {
    if (!exercise) return
    getRecords(exercise.id)
      .then((rec) => setLogCount(countSets(rec)))
      .catch(() => {}) // no warning if the count can't be read; the delete confirmation still shows it
  }, [exercise])

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const data = { name: name.trim(), muscle_group_id: Number(groupId) }
      if (exercise) await updateExercise(exercise.id, data)
      else await createExercise(data)
      await onChanged()
      onDone()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function remove() {
    // Read the count fresh, so the confirmation is right even if the warning above was not loaded
    let count = logCount
    try {
      count = countSets(await getRecords(exercise.id))
    } catch {
      // keep the count from the warning
    }
    const message = count
      ? `Delete "${exercise.name}" and its ${count} logged ${count === 1 ? 'set' : 'sets'}? This cannot be undone.`
      : `Delete "${exercise.name}"? This cannot be undone.`
    if (!window.confirm(message)) return
    setBusy(true)
    try {
      await deleteExercise(exercise.id)
      await onChanged()
      onDone()
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <form className="inline-form" onSubmit={submit}>
      <label className="field">
        <span>Name</span>
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} required maxLength={80} />
      </label>

      <label className="field">
        <span>Muscle group</span>
        <select value={groupId} onChange={(e) => setGroupId(e.target.value)}>
          {groups.map((g) => (
            <option key={g.id} value={g.id}>
              {g.name}
            </option>
          ))}
        </select>
      </label>

      {exercise && logCount > 0 && (
        <div className="logs-warning" role="note">
          <span className="logs-warning-icon" aria-hidden="true">
            !
          </span>
          <div>
            <p className="logs-warning-title">
              {logCount} logged {logCount === 1 ? 'set' : 'sets'}
            </p>
            <p className="logs-warning-text">Deleting this exercise removes them too.</p>
          </div>
        </div>
      )}

      <button className="primary" disabled={busy}>
        {exercise ? 'Save' : 'Add exercise'}
      </button>

      {exercise && (
        <button type="button" className="delete-link" onClick={remove} disabled={busy}>
          Delete exercise
        </button>
      )}

      {error && <p className="status error">{error}</p>}
    </form>
  )
}
