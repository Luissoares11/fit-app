import { useEffect, useState } from 'react'
import { getMuscleGroups, getPlan, listExercises } from '../../api'
import Exercises from './Exercises'
import Plan from './Plan'
import Today from './Today'

const SECTIONS = [
  { id: 'today', label: 'Today' },
  { id: 'plan', label: 'Plan' },
  { id: 'exercises', label: 'Exercises' },
]

export default function Gym() {
  const [section, setSection] = useState('today')
  const [data, setData] = useState(null) // { groups, exercises, plan }
  const [error, setError] = useState('')

  function load() {
    return Promise.all([getMuscleGroups(), listExercises(), getPlan()]).then(([groups, exercises, plan]) =>
      setData({ groups, exercises, plan }),
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

      {section === 'today' && <Today groups={data.groups} exercises={data.exercises} plan={data.plan} onChanged={load} />}
      {section === 'plan' && <Plan groups={data.groups} plan={data.plan} onSaved={load} />}
      {section === 'exercises' && (
        <Exercises groups={data.groups} exercises={data.exercises} onChanged={load} />
      )}
    </>
  )
}
