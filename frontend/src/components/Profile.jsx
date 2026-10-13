import { useEffect, useState } from 'react'
import { getProfile, saveProfile } from '../api'
import { WEEKDAY_NAMES } from '../dates'

const WEEKDAY_OPTIONS = WEEKDAY_NAMES.map((name, i) => ({ value: i, label: name }))

const REPEAT_OPTIONS = [
  { value: 1, label: 'Every week' },
  { value: 2, label: 'Every 2 weeks' },
  { value: 3, label: 'Every 3 weeks' },
  { value: 4, label: 'Every 4 weeks' },
]

const FIELDS = [
  { key: 'name', label: 'Name', mode: 'text' },
  { key: 'age', label: 'Age', mode: 'numeric', integer: true },
  { key: 'height_cm', label: 'Height (cm)', mode: 'decimal' },
  { key: 'start_weight_kg', label: 'Start weight (kg)', mode: 'decimal' },
  { key: 'goal_weight_kg', label: 'Goal weight (kg)', mode: 'decimal' },
  { key: 'checkin_weekday', label: 'Check-in day', integer: true, options: WEEKDAY_OPTIONS },
  { key: 'checkin_every_weeks', label: 'Check-in repeats', integer: true, options: REPEAT_OPTIONS },
]

// Form holds text so half-typed values survive; null means not set
const toForm = (p) => Object.fromEntries(FIELDS.map(({ key }) => [key, String(p[key] ?? '')]))

function parse(text, integer) {
  if (text.trim() === '') return null
  return integer ? parseInt(text, 10) : parseFloat(text.replace(',', '.'))
}

export default function Profile() {
  const [form, setForm] = useState(null)
  const [status, setStatus] = useState({ type: 'idle', message: '' })

  useEffect(() => {
    getProfile()
      .then((p) => setForm(toForm(p)))
      .catch((err) => setStatus({ type: 'error', message: err.message }))
  }, [])

  if (!form) {
    return status.type === 'error' ? (
      <p className="status error">{status.message}</p>
    ) : (
      <p className="muted center">Loading…</p>
    )
  }

  async function save(e) {
    e.preventDefault()
    setStatus({ type: 'busy', message: 'Saving…' })
    try {
      const body = {}
      for (const { key, integer } of FIELDS) {
        body[key] = key === 'name' ? form.name.trim() || null : parse(form[key], integer)
      }
      if (Object.values(body).some((v) => Number.isNaN(v))) {
        throw new Error('Check the numbers')
      }

      setForm(toForm(await saveProfile(body)))
      setStatus({ type: 'ok', message: 'Saved' })
    } catch (err) {
      setStatus({ type: 'error', message: err.message })
    }
  }

  return (
    <form onSubmit={save}>
      {FIELDS.map(({ key, label, mode, options }) => (
        <label className="field" key={key}>
          <span>{label}</span>
          {options ? (
            <select value={form[key]} onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}>
              {options.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          ) : (
            <input
              type="text"
              inputMode={mode}
              value={form[key]}
              onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
            />
          )}
        </label>
      ))}

      <button className="primary" disabled={status.type === 'busy'}>
        {status.type === 'busy' ? status.message : 'Save profile'}
      </button>

      {status.type === 'ok' && <p className="status ok">{status.message}</p>}
      {status.type === 'error' && <p className="status error">{status.message}</p>}
    </form>
  )
}
