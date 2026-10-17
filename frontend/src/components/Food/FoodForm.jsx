import { useState } from 'react'
import { createFood, deleteFood, updateFood } from '../../api'

// "12", "12.5" or "12,5" to a number; blank or invalid gives null
const parseNumber = (text) => {
  const value = Number(text.trim().replace(',', '.'))
  return text.trim() === '' || Number.isNaN(value) ? null : value
}

const optional = (text) => (text.trim() === '' ? null : parseNumber(text))

// Add (no food) or edit a food in the library. Editing also offers delete.
export default function FoodForm({ food, onChanged, onDone }) {
  const [name, setName] = useState(food?.name ?? '')
  const [kcal, setKcal] = useState(food ? String(food.kcal_per_100g) : '')
  const [protein, setProtein] = useState(food?.protein_per_100g != null ? String(food.protein_per_100g) : '')
  const [carbs, setCarbs] = useState(food?.carbs_per_100g != null ? String(food.carbs_per_100g) : '')
  const [fat, setFat] = useState(food?.fat_per_100g != null ? String(food.fat_per_100g) : '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(e) {
    e.preventDefault()
    const kcalValue = parseNumber(kcal)
    if (kcalValue === null) {
      setError('Enter the kcal per 100 g')
      return
    }
    setBusy(true)
    setError('')
    const body = {
      name: name.trim(),
      kcal_per_100g: kcalValue,
      protein_per_100g: optional(protein),
      carbs_per_100g: optional(carbs),
      fat_per_100g: optional(fat),
    }
    try {
      if (food) await updateFood(food.id, body)
      else await createFood(body)
      await onChanged()
      onDone()
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  async function remove() {
    const uses = food.plan_uses
    const message = uses
      ? `Delete "${food.name}"? It is in ${uses} plan ${uses === 1 ? 'entry' : 'entries'}, and it will be removed from ${uses === 1 ? 'it' : 'them'} too.`
      : `Delete "${food.name}"?`
    if (!window.confirm(message)) return
    setBusy(true)
    try {
      await deleteFood(food.id)
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
        <span>Kcal per 100 g</span>
        <input type="text" inputMode="decimal" value={kcal} onChange={(e) => setKcal(e.target.value)} required />
      </label>

      <div className="row-2">
        <label className="field">
          <span>Protein (g/100 g)</span>
          <input type="text" inputMode="decimal" value={protein} onChange={(e) => setProtein(e.target.value)} />
        </label>
        <label className="field">
          <span>Carbs (g/100 g)</span>
          <input type="text" inputMode="decimal" value={carbs} onChange={(e) => setCarbs(e.target.value)} />
        </label>
      </div>

      <label className="field">
        <span>Fat (g/100 g)</span>
        <input type="text" inputMode="decimal" value={fat} onChange={(e) => setFat(e.target.value)} />
      </label>

      <button className="primary" disabled={busy}>
        {food ? 'Save' : 'Add food'}
      </button>

      {food && (
        <button type="button" className="delete-link" onClick={remove} disabled={busy}>
          Delete food
        </button>
      )}

      {error && <p className="status error">{error}</p>}
    </form>
  )
}
