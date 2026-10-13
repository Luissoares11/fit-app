import { useState } from 'react'
import { login } from '../api'

export default function Login({ onSuccess }) {
  const [token, setToken] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await login(token)
      onSuccess()
    } catch {
      setError('Wrong token')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="screen login" onSubmit={submit}>
      <h1>Fitness tracker</h1>
      <label className="field">
        <span>Token</span>
        <input
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          autoComplete="current-password"
          required
        />
      </label>
      <button className="primary" disabled={busy}>
        {busy ? 'Checking…' : 'Log in'}
      </button>
      {error && <p className="status error">{error}</p>}
    </form>
  )
}