import { useEffect, useRef, useState } from 'react'

// A dialog over the page. Escape, the Close button and a tap outside the box all play the exit
// animation first, then close the dialog and call onClose.
export default function Modal({ open, title, subtitle, actions, onClose, children }) {
  const ref = useRef(null)
  const [closing, setClosing] = useState(false)

  useEffect(() => {
    const dialog = ref.current
    if (open && !dialog.open) {
      dialog.showModal()
      // showModal focuses the first button (Edit), which iOS outlines in a box. Start on the dialog instead.
      dialog.focus({ preventScroll: true })
    }
    if (!open && dialog.open) dialog.close()
  }, [open])

  function requestClose() {
    if (!closing) setClosing(true)
  }

  return (
    <dialog
      ref={ref}
      tabIndex={-1}
      className={closing ? 'modal closing' : 'modal'}
      onClose={() => {
        setClosing(false)
        onClose()
      }}
      onCancel={(e) => {
        // Escape: take over so the exit animation runs before the dialog closes
        e.preventDefault()
        requestClose()
      }}
      onAnimationEnd={(e) => {
        // Only the dialog's own exit animation, not the animations of its children
        if (e.target === ref.current && closing) ref.current.close()
      }}
      onClick={(e) => {
        // A click on the dialog itself (not its content) is a click on the backdrop
        if (e.target === ref.current) requestClose()
      }}
    >
      <div className="modal-head">
        <div>
          <h2 className="modal-title">{title}</h2>
          {subtitle && <p className="muted small">{subtitle}</p>}
        </div>
        <div className="modal-actions">
          {actions}
          <button className="link" onClick={requestClose}>
            Close
          </button>
        </div>
      </div>
      <div className="modal-content">{children}</div>
    </dialog>
  )
}
