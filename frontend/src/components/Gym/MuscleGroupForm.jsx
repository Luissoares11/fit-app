import { useState } from 'react'
import { createMuscleGroup, deleteMuscleGroup, updateMuscleGroup } from '../../api'

// Add (no group) or edit (rename, delete) a muscle group.
// The server refuses to delete a group that still has exercises or is in the plan; its message is shown here.
export default function MuscleGroupForm({ group, onChanged, onDone }) {
  const [name, setName] = useState(group?.name ?? '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      if (group) await updateMuscleGroup(group.id, { name })
      else await createMuscleGroup({ name })
      await onChanged()
      onDone()
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  async function remove() {
    if (!window.confirm(`Delete the muscle group "${group.name}"?`)) return
    setBusy(true)
    setError('')
    try {
      await deleteMuscleGroup(group.id)
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
        <span>Muscle group name</span>
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} required maxLength={40} />
      </label>

      <button className="primary" disabled={busy}>
        {group ? 'Save' : 'Add muscle group'}
      </button>

      <div className="form-actions">
        <button type="button" className="link" onClick={onDone}>
          Cancel
        </button>
        {group && (
          <button type="button" className="link danger" onClick={remove} disabled={busy}>
            Delete
          </button>
        )}
      </div>

      {error && <p className="status error">{error}</p>}
    </form>
  )
}
