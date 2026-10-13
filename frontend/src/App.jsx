import { useEffect, useState } from 'react'
import { listSessions, logout } from './api'
import Login from './components/Login'
import Dashboard from './components/Dashboard'
import Register from './components/Register'
import Progress from './components/Progress'
import Profile from './components/Profile'

const TABS = [
  { id: 'dashboard', label: 'Dashboard', Page: Dashboard },
  { id: 'register', label: 'Register', Page: Register },
  { id: 'progress', label: 'Progress', Page: Progress },
  { id: 'profile', label: 'Profile', Page: Profile },
]

export default function App() {
  const [authed, setAuthed] = useState(null) // null while checking
  const [tab, setTab] = useState('dashboard')
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    listSessions()
      .then(() => setAuthed(true))
      .catch(() => setAuthed(false))

    const onUnauthorized = () => setAuthed(false)
    window.addEventListener('unauthorized', onUnauthorized)
    return () => window.removeEventListener('unauthorized', onUnauthorized)
  }, [])

  useEffect(() => {
    if (!menuOpen) return
    const onKey = (e) => e.key === 'Escape' && setMenuOpen(false)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [menuOpen])

  if (authed === null) return <p className="muted center">Loading…</p>
  if (!authed) return <Login onSuccess={() => setAuthed(true)} />

  const current = TABS.find((t) => t.id === tab)

  function pick(id) {
    setTab(id)
    setMenuOpen(false)
  }

  return (
    <div className="app">
      <main className="screen">
        <header className="topbar">
          <div className="topbar-title">
            <button className="icon-btn" aria-label="Open menu" onClick={() => setMenuOpen(true)}>
              ☰
            </button>
            <h1>{current.label}</h1>
          </div>
          <button className="link" onClick={() => logout().finally(() => setAuthed(false))}>
            Log out
          </button>
        </header>

        <current.Page />
      </main>

      <div
        className={menuOpen ? 'drawer-backdrop open' : 'drawer-backdrop'}
        onClick={() => setMenuOpen(false)}
      />

      <nav className={menuOpen ? 'drawer open' : 'drawer'} aria-label="Pages" inert={!menuOpen}>
        {TABS.map((t) => (
          <button key={t.id} className={t.id === tab ? 'active' : ''} onClick={() => pick(t.id)}>
            {t.label}
          </button>
        ))}
      </nav>
    </div>
  )
}
