import { useEffect, useState } from 'react'
import { getFoodOverview, getMuscleGroups, getPlan, getProfile, getTodayPlan, getWeights } from '../api'
import { WEEKDAY_NAMES, daysBetween, formatDay, formatTimeLeft, localDay, toDay, weekdayIndex } from '../dates'
import WeightChart from './WeightChart'
import { FoodMeals } from './Food/FoodOverview'

// Week 1 is the first seven days from the start date. Null when the date is not set or in the future.
function weekSince(startDate) {
  if (!startDate) return null
  const days = daysBetween(toDay(startDate), localDay())
  return days < 0 ? null : Math.floor(days / 7) + 1
}

function Greeting({ profile }) {
  const first = profile.name?.trim().split(/\s+/)[0]
  const week = weekSince(profile.start_date)

  return (
    <header className="dash-hello">
      <h1 className="dash-greeting">Hi{first ? `, ${first}` : ' there'}</h1>
      {week !== null && (
        <p className="dash-week">
          <span className="dash-week-num">Week {week}</span>
          <span className="muted small">since {formatDay(toDay(profile.start_date))}</span>
        </p>
      )}
    </header>
  )
}

// points: the start weight (if set) followed by the logged weights, oldest first
// weeklyLoss: the pace from Profile in kg a week, or null when no pace is set
function GoalProgress({ profile, points, weeklyLoss, onOpen }) {
  const goal = profile.goal_weight_kg
  if (!goal) return <p className="muted">Set your goal weight in Profile to see progress.</p>

  const start = profile.start_weight_kg ?? points[0].weight_kg
  const current = points.at(-1).weight_kg
  const total = start - goal
  // Clamped so going the wrong way reads as 0%, not a negative bar
  const done = total === 0 ? 100 : Math.min(100, Math.max(0, ((start - current) / total) * 100))
  const reached = done >= 100

  return (
    <section
      className="card dash-tap"
      role="button"
      tabIndex={0}
      aria-label="Open progress"
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onOpen()
        }
      }}
    >
      <div className="goal-line">
        <strong>{current.toFixed(1)} kg</strong>
        <span className="muted">goal {goal} kg</span>
      </div>
      <div
        className="bar"
        role="progressbar"
        aria-label="Progress to goal weight"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(done)}
      >
        <div className="bar-fill" style={{ width: `${done}%` }} />
      </div>
      <div className="goal-foot">
        <span className="muted">start {start.toFixed(1)} kg</span>
        <span>
          {reached
            ? 'Goal reached'
            : weeklyLoss
              ? `${formatTimeLeft((current - goal) / weeklyLoss)} to go`
              : `${Math.abs(current - goal).toFixed(1)} kg to go`}
        </span>
      </div>
    </section>
  )
}

// Today's gym plan: the day and its muscle groups (display only)
function TodayPlan({ groups, plan, onOpen }) {
  const todayIndex = weekdayIndex(localDay())
  const ids = plan.days.find((d) => d.weekday === todayIndex)?.muscle_group_ids ?? []
  const planned = groups.filter((g) => ids.includes(g.id))

  return (
    <section
      className="dash-today"
      role="button"
      tabIndex={0}
      aria-label="Open today's training"
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onOpen()
        }
      }}
    >
      <div className="dash-today-head">
        <p className="dash-today-label">Today</p>
        <span className="dash-today-go" aria-hidden="true">
          ›
        </span>
      </div>
      <h2 className="dash-today-day">{WEEKDAY_NAMES[todayIndex]}</h2>
      {planned.length === 0 ? (
        <p className="dash-rest">Rest day. Recover well.</p>
      ) : (
        <ul className="dash-chips">
          {planned.map((g) => (
            <li key={g.id} className="dash-chip">
              {g.name}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export default function Dashboard({ onOpenGym, onOpenProgress, onOpenFood }) {
  const [profile, setProfile] = useState(null)
  const [weights, setWeights] = useState(null)
  const [gym, setGym] = useState(null) // { groups, plan }
  const [foodPlan, setFoodPlan] = useState(null) // { meals, kcal }
  const [nutrition, setNutrition] = useState(null) // overview: the pace in kg a week
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([getProfile(), getWeights(), getMuscleGroups(), getPlan(), getTodayPlan(weekdayIndex(localDay())), getFoodOverview(weekdayIndex(localDay()))])
      .then(([p, w, groups, plan, food, overview]) => {
        setProfile(p)
        setWeights(w)
        setGym({ groups, plan })
        setFoodPlan(food)
        setNutrition(overview)
      })
      .catch((err) => setError(err.message))
  }, [])

  if (error) return <p className="status error">{error}</p>
  if (!profile || !weights || !gym || !foodPlan || !nutrition) return <p className="muted center">Loading…</p>

  // The start weight from Profile counts as the first register, even before any check-in
  const points = profile.start_weight_kg
    ? [{ date: null, weight_kg: profile.start_weight_kg }, ...weights]
    : weights

  return (
    <>
      <Greeting profile={profile} />

      <TodayPlan groups={gym.groups} plan={gym.plan} onOpen={onOpenGym} />

      <div
        className="dash-tap"
        role="button"
        tabIndex={0}
        aria-label="Open nutrition"
        onClick={onOpenFood}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            onOpenFood()
          }
        }}
      >
        <h2 className="section-title">Today's Meals{foodPlan.plan_name ? ` · ${foodPlan.plan_name}` : ''}</h2>
        <FoodMeals meals={foodPlan.meals} total={foodPlan.kcal} />
      </div>

      {points.length === 0 ? (
        <p className="muted center">Log your first check-in to see your progress.</p>
      ) : (
        <>
          <GoalProgress profile={profile} points={points} weeklyLoss={nutrition.weekly_loss_kg} onOpen={onOpenProgress} />
          <section className="card">
            <WeightChart points={points.slice(-5)} />
          </section>
        </>
      )}
    </>
  )
}
