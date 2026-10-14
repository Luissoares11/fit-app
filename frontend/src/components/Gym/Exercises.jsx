import { useState } from 'react'
import ExerciseDetail from './ExerciseDetail'
import ExerciseForm from './ExerciseForm'
import MuscleGroupForm from './MuscleGroupForm'

export default function Exercises({ groups, exercises, onChanged }) {
  const [adding, setAdding] = useState(null) // group id whose add form is open
  const [addingGroup, setAddingGroup] = useState(false) // add-muscle-group form open
  const [editingGroupId, setEditingGroupId] = useState(null) // group whose rename/delete form is open
  const [openId, setOpenId] = useState(null) // exercise whose detail view is open
  const [error, setError] = useState('')

  const opened = openId === null ? null : exercises.find((e) => e.id === openId) ?? null
  if (opened) {
    const group = groups.find((g) => g.id === opened.muscle_group_id)
    return (
      <ExerciseDetail
        key={opened.id}
        exercise={opened}
        groups={groups}
        groupName={group?.name}
        onChanged={onChanged}
        onBack={() => setOpenId(null)}
      />
    )
  }

  return (
    <>
      {error && <p className="status error">{error}</p>}

      {groups.map((g) => {
        const items = exercises.filter((e) => e.muscle_group_id === g.id)
        return (
          <section key={g.id} className="group">
            <div className="group-head">
              <h2 className="group-name">{g.name}</h2>
              <span>
                <button
                  className="link"
                  onClick={() => setEditingGroupId(editingGroupId === g.id ? null : g.id)}
                >
                  {editingGroupId === g.id ? 'Cancel' : 'Edit'}
                </button>{' '}
                <button className="link" onClick={() => setAdding(adding === g.id ? null : g.id)}>
                  {adding === g.id ? 'Cancel' : '+ Add'}
                </button>
              </span>
            </div>

            {editingGroupId === g.id && (
              <MuscleGroupForm
                group={g}
                onChanged={onChanged}
                onDone={() => setEditingGroupId(null)}
              />
            )}

            {adding === g.id && (
              <ExerciseForm
                groups={groups}
                defaultGroupId={g.id}
                onChanged={onChanged}
                onDone={() => setAdding(null)}
                onError={setError}
              />
            )}

            {items.length === 0 && adding !== g.id && (
              <p className="muted hint">No exercises yet. Tap + Add to create one.</p>
            )}

            <ul className="exercise-list">
              {items.map((ex) => (
                <li key={ex.id}>
                  <button
                    className="exercise-row"
                    onClick={() => {
                      setAdding(null)
                      setOpenId(ex.id)
                    }}
                  >
                    {ex.name}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )
      })}

      <section className="group">
        <div className="group-head">
          <button className="link" onClick={() => setAddingGroup((v) => !v)}>
            {addingGroup ? 'Cancel' : '+ Add muscle group'}
          </button>
        </div>
        {addingGroup && (
          <MuscleGroupForm
            onChanged={onChanged}
            onDone={() => setAddingGroup(false)}
          />
        )}
      </section>
    </>
  )
}
