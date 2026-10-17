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
  export const deleteExercise = (id) => request(`/exercises/${id}`, { method: 'DELETE' })
  export const listFoods = () => request('/food/foods')
  export const createFood = (data) => request('/food/foods', json('POST', data))
  export const updateFood = (id, data) => request(`/food/foods/${id}`, json('PATCH', data))
  export const deleteFood = (id) => request(`/food/foods/${id}`, { method: 'DELETE' })
  export const listFoodPlans = () => request('/food/plans')
  export const createFoodPlan = (data) => request('/food/plans', json('POST', data))
  export const getFoodPlanDetail = (id) => request(`/food/plans/${id}`)
  export const renameFoodPlan = (id, data) => request(`/food/plans/${id}`, json('PATCH', data))
  export const deleteFoodPlan = (id) => request(`/food/plans/${id}`, { method: 'DELETE' })
  export const saveFoodPlanMeals = (id, data) => request(`/food/plans/${id}/meals`, json('PUT', data))
  export const getWeekdays = () => request('/food/weekdays')
  export const saveWeekdays = (days) => request('/food/weekdays', json('PUT', { days }))
  export const getTodayPlan = (weekday) => request(`/food/today?weekday=${weekday}`)
  export const getFoodOverview = (weekday) => request(`/food/overview?weekday=${weekday}`)
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