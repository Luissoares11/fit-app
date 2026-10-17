import { useState } from 'react'
import { createFoodPlan, deleteFoodPlan, renameFoodPlan } from '../../api'

// Create a plan (no plan), or rename and delete an existing one
export default function FoodPlanForm({ plan, weekdayCount = 0, onChanged, onDeleted, onCreated, onDone }) {
  const [name, setName] = useState(plan?.name ?? '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      if (plan) {
        await renameFoodPlan(plan.id, { name: name.trim() })
        await onChanged()
        onDone()
      } else {
        const created = await createFoodPlan({ name: name.trim() })
        await onCreated?.(created.id)
        onDone()
      }
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  async function remove() {
    const days = weekdayCount ? ` It is used on ${weekdayCount} ${weekdayCount === 1 ? 'day' : 'days'} and those days will have no plan.` : ''
    if (!window.confirm(`Delete "${plan.name}" and its meals?${days}`)) return
    setBusy(true)
    try {
      await deleteFoodPlan(plan.id)
      await onDeleted?.()
      onDone()
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <form className="inline-form" onSubmit={submit}>
      <label className="field">
        <span>Plan name</span>
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} required maxLength={40} placeholder="e.g. Training day" />
      </label>

      <button className="primary" disabled={busy}>
        {plan ? 'Save' : 'Create plan'}
      </button>

      {plan && (
        <button type="button" className="delete-link" onClick={remove} disabled={busy}>
          Delete plan
        </button>
      )}

      {error && <p className="status error">{error}</p>}
    </form>
  )
}
