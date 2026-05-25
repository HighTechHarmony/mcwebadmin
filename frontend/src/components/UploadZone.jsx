import { useState, useRef } from 'react'
import api from '../api'

export default function UploadZone({ onUpload }) {
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState(null)
  const inputRef = useRef(null)

  const uploadFile = async (file) => {
    if (!file.name.endsWith('.jar')) {
      setMessage({ type: 'error', text: 'Only .jar files are allowed' })
      return
    }
    setUploading(true)
    setMessage(null)
    const formData = new FormData()
    formData.append('file', file)
    try {
      await api.post('/mods/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setMessage({ type: 'success', text: `Uploaded ${file.name}` })
      onUpload()
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.response?.data?.error ?? 'Upload failed',
      })
    } finally {
      setUploading(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) uploadFile(file)
  }

  const handleChange = (e) => {
    const file = e.target.files[0]
    if (file) uploadFile(file)
    e.target.value = ''
  }

  return (
    <div
      className={`upload-zone${dragging ? ' dragging' : ''}${uploading ? ' uploading' : ''}`}
      onClick={() => !uploading && inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".jar"
        onChange={handleChange}
        hidden
      />
      <span>{uploading ? 'Uploading…' : '↑ Drop a .jar here or click to browse'}</span>
      {message && (
        <div className={`upload-message ${message.type}`}>{message.text}</div>
      )}
    </div>
  )
}
