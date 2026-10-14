async function request(path, options = {}) {
    const res = await fetch(`/api${path}`, { credentials: 'same-origin', ...options })
  
    if (res.status === 401) {
      window.dispatchEvent(new Event('unauthorized'))
    }
  
    if (!res.ok) {
      let detail = res.statusText
      try {
        detail = (await res.json()).detail ?? detail
      } catch {
        // response had no JSON body
      }
      const err = new Error(typeof detail === 'string' ? detail : 'Request failed')
      err.status = res.status
      throw err
    }
  
    if (res.status === 204) return null
    return res.json()
  }
  
  const json = (method, body) => ({
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  
  export const login = (token) => request('/login', json('POST', { token }))
  export const logout = () => request('/logout', { method: 'POST' })
  export const listSessions = () => request('/sessions')
  export const createSession = (data) => request('/sessions', json('POST', data))
  export const deleteSession = (id) => request(`/sessions/${id}`, { method: 'DELETE' })
  export const getMuscleGroups = () => request('/muscle-groups')
  export const createMuscleGroup = (data) => request('/muscle-groups', json('POST', data))
  export const updateMuscleGroup = (id, data) => request(`/muscle-groups/${id}`, json('PATCH', data))
  export const deleteMuscleGroup = (id) => request(`/muscle-groups/${id}`, { method: 'DELETE' })
  export const listExercises = () => request('/exercises')
  export const createExercise = (data) => request('/exercises', json('POST', data))
  export const updateExercise = (id, data) => request(`/exercises/${id}`, json('PATCH', data))
  export const archiveExercise = (id) => request(`/exercises/${id}/archive`, { method: 'POST' })
  export const deleteExercise = (id) => request(`/exercises/${id}`, { method: 'DELETE' })
  export const getPlan = () => request('/plan')
  export const savePlan = (data) => request('/plan', json('PUT', data))
  export const logSets = (exerciseId, data) => request(`/exercises/${exerciseId}/sets`, json('POST', data))
  export const getRecords = (exerciseId) => request(`/exercises/${exerciseId}/records`)
  export const updateSet = (setId, data) => request(`/sets/${setId}`, json('PATCH', data))
  export const deleteSet = (setId) => request(`/sets/${setId}`, { method: 'DELETE' })
  export const getLastSets = (exerciseIds) => request(`/exercises/last-sets?exercise_ids=${exerciseIds.join(',')}`)
  export const createWorkout = (data) => request('/workouts', json('POST', data))
  export const getWeights = () => request('/weights')
  export const getProfile = () => request('/profile')
  export const saveProfile = (data) => request('/profile', json('PUT', data))
  
  export function uploadPhoto(sessionId, angle, file) {
    const form = new FormData()
    form.append('file', file)
    return request(`/sessions/${sessionId}/photos/${angle}`, { method: 'POST', body: form })
  }
  
  export const photoUrl = (sessionId, angle, thumb = false) =>
    `/api/sessions/${sessionId}/photos/${angle}${thumb ? '?thumb=true' : ''}`