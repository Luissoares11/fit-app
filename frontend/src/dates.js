// Days are local-midnight Dates, never UTC, so a date never shifts by one
export const toDay = (iso) => {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}

export const localDay = () => {
  const now = new Date()
  return new Date(now.getFullYear(), now.getMonth(), now.getDate())
}

export const addDays = (day, n) => new Date(day.getFullYear(), day.getMonth(), day.getDate() + n)

export const daysBetween = (from, to) => Math.round((to - from) / 86_400_000)

// Day/month/year, the European way: "Tue 13/10/2026"
export const formatDay = (day) => {
  const dd = String(day.getDate()).padStart(2, '0')
  const mm = String(day.getMonth() + 1).padStart(2, '0')
  const weekday = day.toLocaleDateString('en-GB', { weekday: 'short' })
  return `${weekday} ${dd}/${mm}/${day.getFullYear()}`
}

// YYYY-MM-DD in local time (toISOString would use UTC and can be off by a day)
export const todayIso = () => new Date().toLocaleDateString('en-CA')

// Weekdays use 0 = Monday (same as Python's date.weekday()); JS getDay() starts on Sunday
export const WEEKDAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

export const weekdayIndex = (day) => (day.getDay() + 6) % 7

// First chosen weekday strictly after `from`, then pushed (everyWeeks - 1) weeks further
export function nextCheckIn(from, weekday, everyWeeks) {
  const ahead = (weekday - weekdayIndex(from) + 7) % 7 || 7
  return addDays(from, ahead + (everyWeeks - 1) * 7)
}

// dd/mm/yyyy text to YYYY-MM-DD, or null when it isn't a real date
export function parseDisplayDate(text) {
  const m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(text.trim())
  if (!m) return null
  const d = Number(m[1])
  const mo = Number(m[2])
  const y = Number(m[3])
  const day = new Date(y, mo - 1, d)
  if (day.getFullYear() !== y || day.getMonth() !== mo - 1 || day.getDate() !== d) return null
  return `${y}-${String(mo).padStart(2, '0')}-${String(d).padStart(2, '0')}`
}

// YYYY-MM-DD to dd/mm/yyyy
export const toDisplayDate = (iso) => {
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}
