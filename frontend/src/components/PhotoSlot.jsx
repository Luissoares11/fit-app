import { useEffect, useState } from 'react'

export default function PhotoSlot({ label, file, onChange }) {
  const [preview, setPreview] = useState(null)

  useEffect(() => {
    if (!file) {
      setPreview(null)
      return
    }
    const url = URL.createObjectURL(file)
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  return (
    <label className="slot">
      {preview ? <img src={preview} alt={label} /> : <span className="plus">+</span>}
      <small>{label}</small>
      <input
        type="file"
        accept="image/*"
        hidden
        onChange={(e) => {
          onChange(e.target.files[0] ?? null)
          e.target.value = '' // lets you pick the same file again
        }}
      />
    </label>
  )
}