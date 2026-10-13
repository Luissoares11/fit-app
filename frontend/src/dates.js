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

export const formatDay = (day) =>
  day.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' })

// YYYY-MM-DD in local time (toISOString would use UTC and can be off by a day)
export const todayIso = () => new Date().toLocaleDateString('en-CA')
