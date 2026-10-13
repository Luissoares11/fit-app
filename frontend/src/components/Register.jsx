import { useEffect, useState } from 'react'
import { createSession, getProfile, listSessions, uploadPhoto } from '../api'
import { addDays, daysBetween, formatDay, localDay, toDay, todayIso } from '../dates'
import PhotoSlot from './PhotoSlot'

const ANGLES = ['front', 'back', 'side']

export default function Register() {
  const [profile, setProfile] = useState(null)
  const [sessions, setSessions] = useState(null)
  const [override, setOverride] = useState(false)
  const [error, setError] = useState('')

  function load() {
    return Promise.all([getProfile(), listSessions()]).then(([p, s]) => {
      setProfile(p)
      setSessions(s)
    })
  }

  useEffect(() => {
    load().catch((err) => setError(err.message))
  }, [])

  if (error) return <p className="status error">{error}</p>
  if (!profile || !sessions) return <p className="muted center">Loading…</p>

  // sessions come newest first; with no check-in yet, one is due today
  const today = localDay()
  const due = sessions[0] ? addDays(toDay(sessions[0].date), profile.checkin_every_days) : today
  const daysLeft = daysBetween(today, due)

  if (daysLeft > 0 && !override) {
    return (
      <section className="card countdown">
        <p className="muted">Next weight check-in</p>
        <p className="hero">{daysLeft === 1 ? 'Tomorrow' : `in ${daysLeft} days`}</p>
        <p className="muted">{formatDay(due)}</p>
        <button className="primary" onClick={() => setOverride(true)}>
          Log now
        </button>
      </section>
    )
  }

  return (
    <WeightForm
      early={daysLeft > 0}
      onSaved={() => {
        setOverride(false)
        return load()
      }}
    />
  )
}

function WeightForm({ early, onSaved }) {
  const [date, setDate] = useState(todayIso())
  const [weight, setWeight] = useState('')
  const [note, setNote] = useState('')
  const [files, setFiles] = useState({})
  const [status, setStatus] = useState({ type: 'idle', message: '' })

  const busy = status.type === 'busy'

  async function save(e) {
    e.preventDefault()

    // Phone keyboards in Portugal type 80,5 so accept both separators
    const weightKg = parseFloat(weight.replace(',', '.'))
    if (Number.isNaN(weightKg)) {
      setStatus({ type: 'error', message: 'Enter a valid weight' })
      return
    }

    setStatus({ type: 'busy', message: 'Saving…' })
    try {
      let id
      try {
        const created = await createSession({ date, weight_kg: weightKg, note: note || null })
        id = created.id
      } catch (err) {
        if (err.status !== 409) throw err
        // Date already exists (for example a half-finished upload), so reuse that session
        const all = await listSessions()
        id = all.find((s) => s.date === date).id
      }

      for (const angle of ANGLES) {
        if (files[angle]) {
          setStatus({ type: 'busy', message: `Uploading ${angle}…` })
          await uploadPhoto(id, angle, files[angle])
        }
      }

      setStatus({ type: 'ok', message: 'Saved' })
      setWeight('')
      setNote('')
      setFiles({})
      await onSaved()
    } catch (err) {
      setStatus({ type: 'error', message: err.message })
    }
  }

  return (
    <form onSubmit={save}>
      {early && <p className="muted">Not due yet, logging early.</p>}

      <label className="field">
        <span>Date</span>
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
      </label>

      <label className="field">
        <span>Weight (kg)</span>
        <input
          type="text"
          inputMode="decimal"
          placeholder="80.5"
          value={weight}
          onChange={(e) => setWeight(e.target.value)}
          required
        />
      </label>

      <div className="slots">
        {ANGLES.map((angle) => (
          <PhotoSlot
            key={angle}
            label={angle}
            file={files[angle] ?? null}
            onChange={(f) => setFiles((prev) => ({ ...prev, [angle]: f }))}
          />
        ))}
      </div>

      <label className="field">
        <span>Note (optional)</span>
        <input type="text" value={note} onChange={(e) => setNote(e.target.value)} />
      </label>

      <button className="primary" disabled={busy}>
        {busy ? status.message : 'Save check-in'}
      </button>

      {status.type === 'ok' && <p className="status ok">{status.message}</p>}
      {status.type === 'error' && <p className="status error">{status.message}</p>}
    </form>
  )
}
