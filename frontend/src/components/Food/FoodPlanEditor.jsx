import { useState } from 'react'
import { getFoodPlanDetail, saveFoodPlanMeals } from '../../api'
import Modal from '../Modal'
import FoodPlanForm from './FoodPlanForm'

const MAX_MEALS = 10
const DEFAULT_GRAMS = '100'

// Draft meals as the form holds them: grams as typed text, food null until one is picked
const toDraft = (plan) =>
  plan.meals.map((m) => ({
    id: m.id,
    name: m.name,
    items: m.items.map((i) => ({ id: i.id, food_id: i.food_id, grams: String(i.grams) })),
  }))

const parseGrams = (text) => {
  const value = Number(text.trim().replace(',', '.'))
  return text.trim() === '' || Number.isNaN(value) || value <= 0 ? null : value
}

const fmt = (kcal) => (kcal == null ? '—' : `${Math.round(kcal)} kcal`)

// One plan's meals. Each change is saved straight away, and the kcal shown are the backend's numbers.
// Shown inside a dialog. The parent loads the plan before opening it, so it arrives complete.
export default function FoodPlanEditor({ initialPlan, foods, weekdayCount, onDeleted, onChanged }) {
  const [plan, setPlan] = useState(initialPlan)
  const [draft, setDraft] = useState(() => toDraft(initialPlan))
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(false)

  // Re-read the plan after a rename, so its name is current
  function load() {
    return getFoodPlanDetail(plan.id).then((p) => {
      setPlan(p)
      setDraft(toDraft(p))
    })
  }

  // Saved kcal for an item or meal, looked up by id so unsaved rows show a dash
  const savedItemKcal = (itemId) => plan.meals.flatMap((m) => m.items).find((i) => i.id === itemId)?.kcal ?? null
  const savedMealKcal = (mealId) => plan.meals.find((m) => m.id === mealId)?.kcal ?? null

  async function persist(next) {
    setDraft(next)
    const body = { meals: [] }
    for (const [index, meal] of next.entries()) {
      const items = []
      for (const item of meal.items) {
        const grams = parseGrams(item.grams)
        if (item.food_id == null) return setError('Pick a food for every item')
        if (grams === null) return setError('Enter grams for every item')
        items.push({ food_id: item.food_id, grams })
      }
      body.meals.push({ name: meal.name.trim() || `Meal ${index + 1}`, items })
    }
    try {
      const saved = await saveFoodPlanMeals(plan.id, body)
      setPlan(saved)
      setDraft(toDraft(saved))
      setError('')
      await onChanged()
    } catch (err) {
      setError(err.message)
    }
  }

  const updateMeal = (index, change) => persist(draft.map((m, i) => (i === index ? { ...m, ...change } : m)))
  const updateItem = (mealIndex, itemIndex, change) =>
    updateMeal(mealIndex, {
      items: draft[mealIndex].items.map((it, i) => (i === itemIndex ? { ...it, ...change } : it)),
    })

  function setMealCount(count) {
    if (count < 1 || count > MAX_MEALS) return
    const next = draft.slice(0, count)
    while (next.length < count) next.push({ name: `Meal ${next.length + 1}`, items: [] })
    persist(next)
  }

  function addItem(mealIndex) {
    if (foods.length === 0) return setError('Add a food in the Meals tab first')
    updateMeal(mealIndex, { items: [...draft[mealIndex].items, { food_id: foods[0].id, grams: DEFAULT_GRAMS }] })
  }

  function removeItem(mealIndex, itemIndex) {
    updateMeal(mealIndex, { items: draft[mealIndex].items.filter((_, i) => i !== itemIndex) })
  }

  return (
    <div className="food-plan">
      <header className="food-editor-head">
        <button className="link" onClick={() => setEditing(true)}>
          Rename or delete
        </button>
      </header>

      <div className="food-stepper">
        <span className="muted small">Meals per day</span>
        <div className="food-stepper-controls">
          <button className="pill" onClick={() => setMealCount(draft.length - 1)} disabled={draft.length <= 1} aria-label="Fewer meals">
            −
          </button>
          <strong>{draft.length}</strong>
          <button className="pill" onClick={() => setMealCount(draft.length + 1)} disabled={draft.length >= MAX_MEALS} aria-label="More meals">
            +
          </button>
        </div>
      </div>

      <div className="food-day-total food-day-total-top">
        <span className="muted">Day total</span>
        <strong>{fmt(plan.kcal)}</strong>
      </div>

      {draft.map((meal, mealIndex) => (
        <section key={mealIndex} className="card food-meal">
          <div className="food-meal-head">
            <input
              type="text"
              aria-label={`Meal ${mealIndex + 1} name`}
              className="food-meal-name"
              value={meal.name}
              onChange={(e) => setDraft(draft.map((m, i) => (i === mealIndex ? { ...m, name: e.target.value } : m)))}
              onBlur={() => persist(draft)}
              maxLength={40}
            />
            <strong className="food-meal-kcal">{fmt(meal.id ? savedMealKcal(meal.id) : null)}</strong>
          </div>

          {meal.items.length === 0 && <p className="muted small">Nothing in this meal yet.</p>}

          {meal.items.map((item, itemIndex) => (
            <div key={itemIndex} className="food-item">
              <select
                aria-label="Food"
                value={item.food_id ?? ''}
                onChange={(e) => updateItem(mealIndex, itemIndex, { food_id: Number(e.target.value) })}
              >
                {foods.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name}
                  </option>
                ))}
              </select>
              <div className="food-grams-wrap">
                <input
                  type="text"
                  inputMode="decimal"
                  aria-label="Grams"
                  className="food-grams"
                  value={item.grams}
                  onChange={(e) =>
                    setDraft(
                      draft.map((m, mi) =>
                        mi !== mealIndex
                          ? m
                          : { ...m, items: m.items.map((it, ii) => (ii === itemIndex ? { ...it, grams: e.target.value } : it)) },
                      ),
                    )
                  }
                  onBlur={() => persist(draft)}
                />
                <span className="food-grams-unit" aria-hidden="true">
                  g
                </span>
              </div>
              <span className="food-item-kcal muted small">{fmt(item.id ? savedItemKcal(item.id) : null)}</span>
              <button className="link danger" onClick={() => removeItem(mealIndex, itemIndex)} aria-label="Remove item">
                ×
              </button>
            </div>
          ))}

          <button className="link food-add" onClick={() => addItem(mealIndex)}>
            + Add food
          </button>
        </section>
      ))}

      {error && <p className="status error">{error}</p>}

      {editing && (
        <Modal open title="Rename or delete" subtitle={plan.name} onClose={() => setEditing(false)}>
          <FoodPlanForm
            plan={plan}
            weekdayCount={weekdayCount}
            onChanged={async () => {
              await load()
              await onChanged()
            }}
            onDeleted={onDeleted}
            onDone={() => setEditing(false)}
          />
        </Modal>
      )}
    </div>
  )
}
