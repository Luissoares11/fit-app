import { useState } from 'react'
import { parseDisplayDate, toDisplayDate } from '../dates'

// Digits only, with the slashes added as you type: 1310 2026 -> 13/10/2026.
// The number pad has no "/" key on phones, so the slashes can't be typed by hand.
function formatAsTyped(raw) {
  const digits = raw.replace(/\D/g, '').slice(0, 8)
  let out = digits.slice(0, 2)
  if (digits.length > 2) out += `/${digits.slice(2, 4)}`
  if (digits.length > 4) out += `/${digits.slice(4)}`
  return out
}

// Typed day/month/year, the same on every device. Reports YYYY-MM-DD, or null while incomplete or invalid.
export default function DateInput({ defaultValue, onChange }) {
  const [text, setText] = useState(() => (defaultValue ? toDisplayDate(defaultValue) : ''))

  function handle(e) {
    const raw = e.target.value
    // Backspace over a slash removes just the slash; without this it would be put straight back
    const onlySlashRemoved = raw.length < text.length && raw.replace(/\D/g, '') === text.replace(/\D/g, '')
    const next = onlySlashRemoved ? raw : formatAsTyped(raw)
    setText(next)
    onChange(parseDisplayDate(next))
  }

  return (
    <input
      type="text"
      inputMode="numeric"
      placeholder="dd/mm/yyyy"
      aria-label="Date"
      value={text}
      onChange={handle}
    />
  )
}
