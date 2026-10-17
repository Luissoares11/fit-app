import { useEffect, useState } from 'react'
import { getFoodPlanDetail } from '../../api'
import { saveWeekdays } from '../../api'
import { WEEKDAY_NAMES } from '../../dates'
import Modal from '../Modal'
import FoodPlanEditor from './FoodPlanEditor'
import FoodPlanForm from './FoodPlanForm'

const SHORT = WEEKDAY_NAMES.map((d) => d.slice(0, 3))

// The Plan tab: a weekly schedule that picks a plan for each day, then one box per plan.
// Tapping a box opens its meals.
export default function FoodPlans({ foods, plans, weekdays, onChanged }) {
  const [openId, setOpenId] = useState(null) // plan open in the dialog
  const [openPlan, setOpenPlan] = useState(null) // its meals, loaded before the dialog opens
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (openId === null) return
    let current = true
    getFoodPlanDetail(openId)
      .then((p) => current && setOpenPlan(p))
      .catch((err) => current && setError(err.message))
    return () => {
      current = false
    }
  }, [openId])

  function close() {
    setOpenId(null)
    setOpenPlan(null)
  }

  async function setDay(weekday, planId) {
    const days = weekdays.map((d) => (d.weekday === weekday ? { weekday, plan_id: planId } : { weekday: d.weekday, plan_id: d.plan_id }))
    try {
      await saveWeekdays(days)
      setError('')
      await onChanged()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="food-plans">
      <section className="card food-week">
        <h2 className="section-title">Week</h2>
        <ul className="food-week-list">
          {weekdays.map((d) => (
            <li key={d.weekday}>
              <span className="food-week-day">{SHORT[d.weekday]}</span>
              <select
                aria-label={`${WEEKDAY_NAMES[d.weekday]} plan`}
                value={d.plan_id ?? ''}
                onChange={(e) => setDay(d.weekday, e.target.value ? Number(e.target.value) : null)}
              >
                <option value="">No plan</option>
                {plans.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </li>
          ))}
        </ul>
        {error && <p className="status error">{error}</p>}
      </section>

      <button className="primary ex-new-group" onClick={() => setCreating(true)}>
        + New plan
      </button>

      {plans.length === 0 ? (
        <p className="muted center">No plans yet. Create one, for example "Training day" or "Rest day".</p>
      ) : (
        <div className="food-plan-boxes">
          {plans.map((p) => (
            <button key={p.id} className="card food-plan-box" onClick={() => setOpenId(p.id)}>
              <span className="food-plan-box-name">{p.name}</span>
              <span className="muted small">
                {p.meal_count} {p.meal_count === 1 ? 'meal' : 'meals'} · {Math.round(p.kcal)} kcal a day
              </span>
              <span className="food-plan-box-days">
                {p.weekdays.length === 0
                  ? 'Not on any day'
                  : p.weekdays.map((w) => SHORT[w]).join(' · ')}
              </span>
            </button>
          ))}
        </div>
      )}

      {openId !== null && (
        <Modal
          open={openPlan !== null}
          title={openPlan?.name ?? 'Plan'}
          subtitle={openPlan ? `${openPlan.meals.length} ${openPlan.meals.length === 1 ? 'meal' : 'meals'} · ${Math.round(openPlan.kcal)} kcal a day` : undefined}
          onClose={close}
        >
          {openPlan && (
            <FoodPlanEditor
              key={openPlan.id}
              initialPlan={openPlan}
              foods={foods}
              weekdayCount={plans.find((p) => p.id === openId)?.weekdays.length ?? 0}
              onDeleted={close}
              onChanged={async () => {
                await onChanged()
                setOpenPlan(await getFoodPlanDetail(openId)) // keeps the dialog subtitle current
              }}
            />
          )}
        </Modal>
      )}

      {creating && (
        <Modal open title="New plan" onClose={() => setCreating(false)}>
          <FoodPlanForm
            onChanged={onChanged}
            onCreated={async (id) => {
              await onChanged()
              setOpenId(id)
            }}
            onDone={() => setCreating(false)}
          />
        </Modal>
      )}
    </div>
  )
}
