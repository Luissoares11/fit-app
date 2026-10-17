import { useEffect, useState } from 'react'
import { listFoodPlans, getWeekdays, listFoods } from '../../api'
import FoodLibrary from './FoodLibrary'
import FoodOverview from './FoodOverview'
import FoodPlans from './FoodPlans'

const SECTIONS = [
  { id: 'overview', label: 'Overview' },
  { id: 'plan', label: 'Plan' },
  { id: 'meals', label: 'Meals' },
]

export default function Food() {
  const [section, setSection] = useState('overview')
  const [data, setData] = useState(null) // { foods, plans, weekdays }
  const [error, setError] = useState('')

  function load() {
    return Promise.all([listFoods(), listFoodPlans(), getWeekdays()]).then(([foods, plans, week]) =>
      setData({ foods, plans, weekdays: week.days }),
    )
  }

  useEffect(() => {
    load().catch((err) => setError(err.message))
  }, [])

  if (error) return <p className="status error">{error}</p>
  if (!data) return <p className="muted center">Loading…</p>

  return (
    <>
      <div className="segmented">
        {SECTIONS.map((s) => (
          <button
            key={s.id}
            className={s.id === section ? 'active' : ''}
            aria-pressed={s.id === section}
            onClick={() => setSection(s.id)}
          >
            {s.label}
          </button>
        ))}
      </div>

      {section === 'overview' && <FoodOverview />}
      {section === 'plan' && <FoodPlans foods={data.foods} plans={data.plans} weekdays={data.weekdays} onChanged={load} />}
      {section === 'meals' && <FoodLibrary foods={data.foods} onChanged={load} />}
    </>
  )
}
