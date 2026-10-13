// Weights show without a trailing .0 (80 not 80.0)
export const kg = (w) => String(Math.round(w * 100) / 100)

// Accepts 80.5 and 80,5; null when empty or not a number
export function parseKg(text) {
  const t = text.trim()
  if (t === '') return null
  const n = Number(t.replace(',', '.'))
  return Number.isFinite(n) ? n : null
}

export const parseReps = (text) => (/^\d+$/.test(text.trim()) ? Number(text.trim()) : null)

export function prText(pr) {
  if (pr.type === 'heaviest') return `Heaviest: ${kg(pr.weight_kg)} kg x ${pr.reps}`
  if (pr.type === 'rep_best') return `Best at ${pr.reps} reps: ${kg(pr.weight_kg)} kg`
  if (pr.type === 'e1rm') return `Estimated 1RM: ${kg(pr.value)} kg`
  return `Most reps (bodyweight): ${pr.reps}`
}
