import { useEffect, useState } from 'react'
import { deleteSession, getProfile, listSessions, photoUrl } from '../api'
import { formatDay, toDay } from '../dates'

const ANGLES = ['front', 'back', 'side']

const bmi = (kg, heightCm) => (kg / (heightCm / 100) ** 2).toFixed(1)

function PhotoRow({ session, compact = false }) {
  return (
    <div className={compact ? 'photo-row compact' : 'photo-row'}>
      {ANGLES.filter((a) => session.angles.includes(a)).map((a) => (
        <img key={a} src={photoUrl(session.id, a, true)} alt={`${a}, ${session.date}`} loading="lazy" />
      ))}
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div className="stat">
      <span className="muted">{label}</span>
      <span className="value">{value}</span>
    </div>
  )
}

export default function Progress() {
  const [profile, setProfile] = useState(null)
  const [sessions, setSessions] = useState(null) // newest first
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  function load() {
    return Promise.all([getProfile(), listSessions()]).then(([p, s]) => {
      setProfile(p)
      setSessions(s)
    })
  }

  useEffect(() => {
    load().catch((err) => setError(err.message))
  }, [])

  async function remove(session) {
    const label = formatDay(toDay(session.date))
    if (!window.confirm(`Delete the ${label} log? Its weight and photos will be removed.`)) return
    setNotice('')
    try {
      await deleteSession(session.id)
      await load()
    } catch (err) {
      setNotice(err.message)
    }
  }

  if (error) return <p className="status error">{error}</p>
  if (!profile || !sessions) return <p className="muted center">Loading…</p>

  const withPhotos = sessions.filter((s) => s.angles.length > 0)
  const startPhotos = withPhotos.at(-1)
  const latestPhotos = withPhotos[0]
  // Latest check-in, or the start weight from Profile when nothing is logged yet
  const currentWeight = sessions[0]?.weight_kg ?? profile.start_weight_kg
  const height = profile.height_cm

  return (
    <>
      <section className="card stat-grid">
        <Stat
          label="Current BMI"
          value={currentWeight && height ? bmi(currentWeight, height) : '—'}
        />
        <Stat
          label="Goal BMI"
          value={profile.goal_weight_kg && height ? bmi(profile.goal_weight_kg, height) : '—'}
        />
      </section>
      {!height && <p className="muted">Add your height in Profile to see BMI.</p>}

      <h2 className="section-title">Starting photos</h2>
      {startPhotos ? (
        <>
          <p className="muted">{formatDay(toDay(startPhotos.date))}</p>
          <PhotoRow session={startPhotos} />
        </>
      ) : (
        <p className="muted">No photos yet.</p>
      )}

      <h2 className="section-title">Latest photos</h2>
      {latestPhotos ? (
        <>
          <p className="muted">{formatDay(toDay(latestPhotos.date))}</p>
          <PhotoRow session={latestPhotos} />
        </>
      ) : (
        <p className="muted">No photos yet.</p>
      )}

      <h2 className="section-title">History</h2>
      {notice && <p className="status error">{notice}</p>}
      <ul className="history">
        {sessions.map((s) => (
          <li key={s.id}>
            <div className="history-head">
              <span>{formatDay(toDay(s.date))}</span>
              <span className="history-actions">
                <strong>{s.weight_kg.toFixed(1)} kg</strong>
                <button className="link danger" onClick={() => remove(s)}>
                  Delete
                </button>
              </span>
            </div>
            {s.note && <p className="muted note">{s.note}</p>}
            {s.angles.length > 0 && <PhotoRow session={s} compact />}
          </li>
        ))}
      </ul>
    </>
  )
}
