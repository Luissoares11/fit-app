import { useEffect, useState } from 'react'
import { getProfile, getWeights } from '../api'
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

export default function Dashboard() {
  const [profile, setProfile] = useState(null)
  const [weights, setWeights] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([getProfile(), getWeights()])
      .then(([p, w]) => {
        setProfile(p)
        setWeights(w)
      })
      .catch((err) => setError(err.message))
  }, [])

  if (error) return <p className="status error">{error}</p>
  if (!profile || !weights) return <p className="muted center">Loading…</p>
  if (weights.length === 0) {
    return <p className="muted center">Log your first check-in to see your progress.</p>
  }

  return (
    <>
      <GoalProgress profile={profile} weights={weights} />
      <section className="card">
        <WeightChart points={weights} />
      </section>
    </>
  )
}
