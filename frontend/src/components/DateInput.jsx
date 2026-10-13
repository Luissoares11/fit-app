import { useState } from 'react'
import { parseDisplayDate, toDisplayDate } from '../dates'

// Typed day/month/year, the same on every device. Reports YYYY-MM-DD, or null while incomplete or invalid.
export default function DateInput({ defaultValue, onChange }) {
  const [text, setText] = useState(() => toDisplayDate(defaultValue))

  function handle(e) {
    setText(e.target.value)
    onChange(parseDisplayDate(e.target.value))
  }

  return (
    <input
      type="text"
      inputMode="numeric"
      placeholder="dd/mm/yyyy"
      maxLength={10}
      aria-label="Date"
      value={text}
      onChange={handle}
    />
  )
}
