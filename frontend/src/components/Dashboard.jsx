import { useEffect, useState } from 'react'
import { getMuscleGroups, getPlan, getProfile, getWeights } from '../api'
import { WEEKDAY_NAMES, localDay, weekdayIndex } from '../dates'
import WeightChart from './WeightChart'

function GoalProgress({ profile, weights }) {
  const goal = profile.goal_weight_kg
  if (!goal) return <p className="muted">Set your goal weight in Profile to see progress.</p>

  const start = profile.start_weight_kg ?? weights[0].weight_kg
  const current = weights.at(-1).weight_kg
  const total = start - goal
  // Clamped so going the wrong way reads as 0%, not a negative bar
  const done = total === 0 ? 100 : Math.min(100, Math.max(0, ((start - current) / total) * 100))
  const reached = done >= 100

  return (
    <section className="card">
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
        <span>{reached ? 'Goal reached' : `${Math.abs(current - goal).toFixed(1)} kg to go`}</span>
      </div>
    </section>
  )
}

// Today's gym plan: the day and its muscle groups (display only)
function TodayPlan({ groups, plan }) {
  const todayIndex = weekdayIndex(localDay())
  const ids = plan.days.find((d) => d.weekday === todayIndex)?.muscle_group_ids ?? []

  return (
    <section className="card">
      <h2 className="today-day">{WEEKDAY_NAMES[todayIndex]}</h2>
      {ids.length === 0 && <p className="hero">Rest day</p>}
      {groups
        .filter((g) => ids.includes(g.id))
        .map((g) => (
          <h3 key={g.id} className="today-group">
            {g.name}
          </h3>
        ))}
    </section>
  )
}

export default function Dashboard() {
  const [profile, setProfile] = useState(null)
  const [weights, setWeights] = useState(null)
  const [gym, setGym] = useState(null) // { groups, plan }
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([getProfile(), getWeights(), getMuscleGroups(), getPlan()])
      .then(([p, w, groups, plan]) => {
        setProfile(p)
        setWeights(w)
        setGym({ groups, plan })
      })
      .catch((err) => setError(err.message))
  }, [])

  if (error) return <p className="status error">{error}</p>
  if (!profile || !weights || !gym) return <p className="muted center">Loading…</p>

  return (
    <>
      <TodayPlan groups={gym.groups} plan={gym.plan} />

      {weights.length === 0 ? (
        <p className="muted center">Log your first check-in to see your progress.</p>
      ) : (
        <>
          <GoalProgress profile={profile} weights={weights} />
          <section className="card">
            <WeightChart points={weights} />
          </section>
        </>
      )}
    </>
  )
}
