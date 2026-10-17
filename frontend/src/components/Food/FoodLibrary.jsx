import { useState } from 'react'
import Modal from '../Modal'
import FoodForm from './FoodForm'

// The Meals tab: the library of foods the user eats, used to build the plan
export default function FoodLibrary({ foods, onChanged }) {
  const [editing, setEditing] = useState(null) // 'new', a food, or null

  return (
    <div className="ex-page">
      <button className="primary ex-new-group" onClick={() => setEditing('new')}>
        + New food
      </button>

      {foods.length === 0 ? (
        <p className="muted center">No foods yet. Add the ones you usually eat.</p>
      ) : (
        <section className="ex-group">
          <ul className="ex-list">
            {foods.map((f) => (
              <li key={f.id}>
                <button className="ex-row" onClick={() => setEditing(f)}>
                  <span>
                    <strong>{f.name}</strong>
                    <span className="muted small food-meta">
                      {Math.round(f.kcal_per_100g)} kcal / 100 g
                      {f.plan_uses > 0 && ` · in ${f.plan_uses} plan ${f.plan_uses === 1 ? 'entry' : 'entries'}`}
                    </span>
                  </span>
                  <span className="ex-chevron" aria-hidden="true">
                    ›
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {editing && (
        <Modal
          open
          title={editing === 'new' ? 'New food' : 'Edit food'}
          subtitle={editing === 'new' ? undefined : editing.name}
          onClose={() => setEditing(null)}
        >
          <FoodForm food={editing === 'new' ? null : editing} onChanged={onChanged} onDone={() => setEditing(null)} />
        </Modal>
      )}
    </div>
  )
}
