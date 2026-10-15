import { useEffect, useState } from 'react'
import { getMuscleGroups, getPlan, getProfile, getWeights } from '../api'
import { WEEKDAY_NAMES, daysBetween, formatDay, localDay, toDay, weekdayIndex } from '../dates'
import WeightChart from './WeightChart'

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
function GoalProgress({ profile, points, onOpen }) {
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
        <span>{reached ? 'Goal reached' : `${Math.abs(current - goal).toFixed(1)} kg to go`}</span>
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

export default function Dashboard({ onOpenGym, onOpenProgress }) {
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

  // The start weight from Profile counts as the first register, even before any check-in
  const points = profile.start_weight_kg
    ? [{ date: null, weight_kg: profile.start_weight_kg }, ...weights]
    : weights

  return (
    <>
      <Greeting profile={profile} />

      <TodayPlan groups={gym.groups} plan={gym.plan} onOpen={onOpenGym} />

      {points.length === 0 ? (
        <p className="muted center">Log your first check-in to see your progress.</p>
      ) : (
        <>
          <GoalProgress profile={profile} points={points} onOpen={onOpenProgress} />
          <section className="card">
            <WeightChart points={points.slice(-5)} />
          </section>
        </>
      )}
    </>
  )
}
