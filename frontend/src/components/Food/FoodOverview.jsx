import { useEffect, useState } from 'react'
import { getFoodOverview } from '../../api'
import { WEEKDAY_NAMES, formatTimeLeft, localDay, weekdayIndex } from '../../dates'

const PACE_LABEL = {
  mild: 'Mild',
  moderate: 'Moderate',
  aggressive: 'Aggressive',
  extreme: 'Extreme',
}

const WEIGHT_SOURCE = {
  checkin: 'latest check-in',
  profile_start: 'start weight',
}

const INTAKE = {
  less: 'Eating less than your target',
  on_deficit: 'On your deficit',
  more: 'Eating more than your target',
}

// A number from the backend, or "N/A" when it depends on something missing from the profile
const show = (value, suffix = '') => (value == null ? 'N/A' : `${Math.round(value).toLocaleString()}${suffix}`)

// One line of the goal card: a label on the left, the value on the right
function Fact({ label, children }) {
  return (
    <div className="food-fact">
      <dt className="muted small">{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}

export default function FoodOverview() {
  const [o, setO] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getFoodOverview(weekdayIndex(localDay()))
      .then(setO)
      .catch((err) => setError(err.message))
  }, [])

  if (error) return <p className="status error">{error}</p>
  if (!o) return <p className="muted center">Loading…</p>

  const deficitNegative = o.deficit != null && o.deficit < 0
  const weightNow = o.weight_used != null ? `${Math.round(o.weight_used * 10) / 10} kg` : 'N/A'

  return (
    <>
      {o.missing.length > 0 && (
        <p className="food-note">N/A (missing: {o.missing.join(', ')}). Set it in Profile to see these numbers.</p>
      )}

      <section className="card">
        <h2 className="section-title">Energy</h2>
        <div className="stat-grid">
          <div className="stat">
            <span className="muted small">BMR</span>
            <span className="value">{show(o.bmr)}</span>
          </div>
          <div className="stat">
            <span className="muted small">TDEE</span>
            <span className="value">{show(o.tdee)}</span>
          </div>
          <div className="stat">
            <span className="muted small">Goal</span>
            <span className="value">{show(o.goal_kcal, ' kcal')}</span>
          </div>
          <div className={`stat food-deficit ${deficitNegative ? 'negative' : ''}`}>
            <span className="muted small">Deficit</span>
            <span className="value">{show(o.deficit)}</span>
          </div>
        </div>
      </section>

      <section className="card">
        <h2 className="section-title">Goal</h2>
        <dl className="food-facts">
          <Fact label="Weight now">
            {weightNow}
            {o.weight_source && <span className="muted small"> · {WEIGHT_SOURCE[o.weight_source]}</span>}
          </Fact>
          <Fact label="Goal weight">{o.goal_weight_kg != null ? `${o.goal_weight_kg} kg` : 'N/A'}</Fact>
          <Fact label="Pace">
            {o.weight_loss_pace ? `${PACE_LABEL[o.weight_loss_pace]} · ${o.weekly_loss_kg} kg a week` : 'Not set'}
          </Fact>
          <Fact label="Time to goal">
            {o.weeks_to_goal == null
              ? 'N/A'
              : o.weeks_to_goal === 0
                ? 'Already there'
                : formatTimeLeft(o.weeks_to_goal)}
          </Fact>
          <Fact label="Training days">{`${o.training_days_per_week} a week`}</Fact>
        </dl>
      </section>

      <section className="card">
        <h2 className="section-title">This week</h2>
        {o.intake_status ? (
          <>
            <p className={`food-intake ${o.intake_status}`}>{INTAKE[o.intake_status]}</p>
            <p className="muted small">
              Average {Math.round(o.week_kcal_avg).toLocaleString()} kcal a day against a goal of {show(o.goal_kcal)} kcal
              ({o.intake_vs_goal > 0 ? '+' : ''}
              {o.intake_vs_goal} kcal)
            </p>
          </>
        ) : (
          <p className="muted small">Needs a meal plan on every day of the week to compare with your goal.</p>
        )}
        {o.week_days && (
          <ul className="week-days">
            {o.week_days.map((d) => (
              <li key={d.weekday} className={d.below_average ? 'below' : ''}>
                <span className="week-days-name">{WEEKDAY_NAMES[d.weekday]}</span>
                <span className="week-days-kcal">{d.kcal.toLocaleString()} kcal</span>
                {d.below_average && <span className="week-days-flag">below average</span>}
              </li>
            ))}
          </ul>
        )}
      </section>

      <h2 className="section-title">Today's meals{o.plan_name ? ` · ${o.plan_name}` : ''}</h2>
      <FoodMeals meals={o.planned_meals} total={o.day_kcal} />
    </>
  )
}

export function FoodMeals({ meals, total }) {
  if (meals.length === 0) {
    return <p className="muted small">No meals planned yet. Set them up in the Plan tab.</p>
  }
  return (
    <section className="card">
      <ul className="food-meal-list">
        {meals.map((m) => (
          <li key={m.id}>
            <div className="food-meal-line">
              <span>{m.name}</span>
              <strong>{Math.round(m.kcal)} kcal</strong>
            </div>
            <p className="muted small">{m.items.map((i) => i.food_name).join(', ') || 'Nothing yet'}</p>
          </li>
        ))}
      </ul>
      <div className="food-day-total">
        <span className="muted">Day total</span>
        <strong>{Math.round(total)} kcal</strong>
      </div>
    </section>
  )
}
