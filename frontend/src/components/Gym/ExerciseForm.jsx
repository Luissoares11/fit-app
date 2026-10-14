import { useState } from 'react'
import { archiveExercise, createExercise, deleteExercise, updateExercise } from '../../api'

// Add (no exercise) or edit (rename, move, archive, delete) an exercise.
// Delete is only offered when the exercise has no logged sets (canDelete).
export default function ExerciseForm({ groups, exercise, defaultGroupId, canDelete = false, onChanged, onDone, onError }) {
  const [name, setName] = useState(exercise?.name ?? '')
  const [groupId, setGroupId] = useState(exercise?.muscle_group_id ?? defaultGroupId)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

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

  async function archive() {
    if (!window.confirm(`Archive "${exercise.name}"? It will be hidden from the list.`)) return
    setBusy(true)
    try {
      await archiveExercise(exercise.id)
      await onChanged()
      onDone()
    } catch (err) {
      onError(err.message)
      setBusy(false)
    }
  }

  async function remove() {
    if (!window.confirm(`Delete "${exercise.name}"? This cannot be undone.`)) return
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

      <button className="primary" disabled={busy}>
        {exercise ? 'Save' : 'Add exercise'}
      </button>

      {exercise && (
        <div className="form-actions">
          <button type="button" className="link" onClick={onDone}>
            Cancel
          </button>
          <button type="button" className="link" onClick={archive} disabled={busy}>
            Archive
          </button>
          {canDelete && (
            <button type="button" className="link danger" onClick={remove} disabled={busy}>
              Delete
            </button>
          )}
        </div>
      )}

      {error && <p className="status error">{error}</p>}
    </form>
  )
}
