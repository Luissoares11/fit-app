import { useState } from 'react'
import { importCsv } from '../api'

// Import a library from a CSV: choose a file, preview what will change, then confirm.
// Nothing is saved until the confirm step, which sends the file again.
export default function ImportCsv({ path, templateUrl, templateName, instructions, onImported, onDone }) {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function review(chosen) {
    setFile(chosen)
    setPreview(null)
    setError('')
    if (!chosen) return
    setBusy(true)
    try {
      setPreview(await importCsv(path, chosen, false))
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function confirm() {
    setBusy(true)
    try {
      setResult(await importCsv(path, file, true))
      await onImported()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (result) {
    return (
      <div className="import">
        <section className="card">
          <h2 className="section-title">Import finished</h2>
          <div className="import-stats">
            <Stat label="Added" value={result.added} />
            <Stat label="Skipped" value={result.skipped} />
            <Stat label="Invalid" value={result.invalid} bad={result.invalid > 0} />
          </div>
          {result.new_muscle_groups?.length > 0 && (
            <p className="muted small import-note">New muscle groups: {result.new_muscle_groups.join(', ')}</p>
          )}
        </section>
        <button className="primary" onClick={onDone}>
          Done
        </button>
      </div>
    )
  }

  return (
    <div className="import">
      <section className="card">
        <h2 className="section-title">Start</h2>
        <p className="import-instructions">{instructions}</p>
        <a className="pill import-template" href={templateUrl} download={templateName}>
          Download template
        </a>
      </section>

      <section className="card">
        <h2 className="section-title">Your file</h2>
        <label className="field">
          <span>CSV file, up to 1 MB</span>
          <input type="file" accept=".csv,text/csv" onChange={(e) => review(e.target.files[0] ?? null)} />
        </label>
        {busy && <p className="muted small">Reading the file…</p>}
        {error && <p className="status error">{error}</p>}
      </section>

      {preview && (
        <>
          <section className="card">
            <h2 className="section-title">Preview</h2>
            <div className="import-stats">
              <Stat label="To add" value={preview.to_add} />
              <Stat label="Skipped" value={preview.skipped.length} />
              <Stat label="Invalid" value={preview.invalid.length} bad={preview.invalid.length > 0} />
            </div>
          </section>

          {preview.new_muscle_groups?.length > 0 && (
            <section className="card">
              <h2 className="section-title">New muscle groups</h2>
              <div className="import-chips">
                {preview.new_muscle_groups.map((g) => (
                  <span key={g} className="import-chip">
                    {g}
                  </span>
                ))}
              </div>
              <p className="muted small">Created when you import. Check the spelling, since a typo creates a new group.</p>
            </section>
          )}

          {preview.warnings?.length > 0 && <Rows title="Check these" tone="warn" items={preview.warnings} />}
          {preview.invalid.length > 0 && <Rows title="Skipped as invalid" tone="bad" items={preview.invalid} />}
          {preview.skipped.length > 0 && <Rows title="Already there" items={preview.skipped} />}

          <button className="primary" onClick={confirm} disabled={busy || preview.to_add === 0}>
            {preview.to_add === 0 ? 'Nothing new to import' : `Import ${preview.to_add} ${preview.to_add === 1 ? 'row' : 'rows'}`}
          </button>
        </>
      )}
    </div>
  )
}

function Stat({ label, value, bad }) {
  return (
    <div className={`stat import-stat ${bad ? 'bad' : ''}`}>
      <span className="muted small">{label}</span>
      <span className="value">{value}</span>
    </div>
  )
}

function Rows({ title, items, tone }) {
  return (
    <section className={`card import-rows-card ${tone ?? ''}`}>
      <details>
        <summary className="import-summary">
          {title} <span className="muted">({items.length})</span>
        </summary>
        <ul className="import-rows">
          {items.map((i, idx) => (
            <li key={idx}>
              <span className="import-row-name">{i.name ?? `Line ${i.line}`}</span>
              <span className="muted small">
                {i.name && i.line ? `Line ${i.line} · ` : ''}
                {i.reason}
              </span>
            </li>
          ))}
        </ul>
      </details>
    </section>
  )
}
