import { useState } from 'react'
import ExerciseDetail from './ExerciseDetail'
import ExerciseForm from './ExerciseForm'
import MuscleGroupForm from './MuscleGroupForm'
import Modal from '../Modal'

const countLabel = (n) => (n === 1 ? '1 exercise' : `${n} exercises`)

export default function Exercises({ groups, exercises, onChanged }) {
  const [adding, setAdding] = useState(null) // group id for the "new exercise" popup
  const [addingGroup, setAddingGroup] = useState(false) // "new muscle group" popup
  const [editingGroupId, setEditingGroupId] = useState(null) // group for the "edit muscle group" popup
  const [editingExerciseId, setEditingExerciseId] = useState(null) // exercise for the form opened from a group
  const [openId, setOpenId] = useState(null) // exercise whose detail view is open

  const opened = openId === null ? null : exercises.find((e) => e.id === openId) ?? null
  const addingTo = groups.find((g) => g.id === adding) ?? null
  const editingGroup = groups.find((g) => g.id === editingGroupId) ?? null
  const editingExercise = exercises.find((e) => e.id === editingExerciseId) ?? null

  return (
    <div className="ex-page">
      <button className="primary ex-new-group" onClick={() => setAddingGroup(true)}>
        + New muscle group
      </button>

      {groups.map((g) => {
        const items = exercises.filter((e) => e.muscle_group_id === g.id)
        return (
          <section key={g.id} className="ex-group">
            <header className="ex-group-head">
              <div>
                <h2 className="ex-group-title">{g.name}</h2>
                <p className="muted small">{countLabel(items.length)}</p>
              </div>
              <div className="ex-group-actions">
                <button className="pill" onClick={() => setEditingGroupId(g.id)}>
                  Edit
                </button>
                <button className="pill pill-solid" onClick={() => setAdding(g.id)}>
                  + Add
                </button>
              </div>
            </header>

            {items.length === 0 ? (
              <p className="muted small ex-empty">No exercises yet. Tap + Add to create one.</p>
            ) : (
              <ul className="ex-list">
                {items.map((ex) => (
                  <li key={ex.id}>
                    <button className="ex-row" onClick={() => setOpenId(ex.id)}>
                      <span>{ex.name}</span>
                      <span className="ex-chevron" aria-hidden="true">
                        ›
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )
      })}

      {addingTo && (
        <Modal open title="New exercise" subtitle={addingTo.name} onClose={() => setAdding(null)}>
          <ExerciseForm
            groups={groups}
            defaultGroupId={addingTo.id}
            onChanged={onChanged}
            onDone={() => setAdding(null)}
          />
        </Modal>
      )}

      {editingGroup && (
        <Modal open title="Edit muscle group" onClose={() => setEditingGroupId(null)}>
          <MuscleGroupForm group={editingGroup} onChanged={onChanged} onDone={() => setEditingGroupId(null)} />

          <h3 className="section-title">Exercises in this group</h3>
          {exercises.filter((e) => e.muscle_group_id === editingGroup.id).length === 0 ? (
            <p className="muted small">None yet.</p>
          ) : (
            <ul className="ex-list">
              {exercises
                .filter((e) => e.muscle_group_id === editingGroup.id)
                .map((ex) => (
                  <li key={ex.id}>
                    <button className="ex-row" onClick={() => setEditingExerciseId(ex.id)}>
                      <span>{ex.name}</span>
                      <span className="ex-chevron" aria-hidden="true">
                        ›
                      </span>
                    </button>
                  </li>
                ))}
            </ul>
          )}
        </Modal>
      )}

      {editingExercise && (
        // Opened from the group popup; stacks on top of it
        <Modal open title="Edit exercise" subtitle={editingGroup?.name} onClose={() => setEditingExerciseId(null)}>
          <ExerciseForm
            groups={groups}
            exercise={editingExercise}
            onChanged={onChanged}
            onDone={() => setEditingExerciseId(null)}
          />
        </Modal>
      )}

      {addingGroup && (
        <Modal open title="New muscle group" onClose={() => setAddingGroup(false)}>
          <MuscleGroupForm onChanged={onChanged} onDone={() => setAddingGroup(false)} />
        </Modal>
      )}

      {opened && (
        <ExerciseDetail
          key={opened.id}
          exercise={opened}
          groups={groups}
          groupName={groups.find((g) => g.id === opened.muscle_group_id)?.name}
          onChanged={onChanged}
          onClose={() => setOpenId(null)}
        />
      )}
    </div>
  )
}
