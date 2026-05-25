import { useState } from 'react'
import api from '../api'

export default function CommandInput({ value, onChange, onResponse, inputRef }) {
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    const cmd = value.trim()
    if (!cmd) return
    setLoading(true)
    try {
      const res = await api.post('/console/command', { command: cmd })
      onResponse({ success: true, text: res.data.response })
      onChange('')
    } catch (err) {
      console.error('Command failed:', err)
      onResponse({
        success: false,
        text: err.response?.data?.error || 'Failed to send command',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <form className="command-input-form" onSubmit={handleSubmit}>
      <span className="command-prompt">&gt;</span>
      <input
        ref={inputRef}
        type="text"
        className="command-input"
        placeholder="Enter server command…"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={loading}
        autoComplete="off"
        spellCheck={false}
      />
      <button
        type="submit"
        className="btn btn-primary btn-sm"
        disabled={loading || !value.trim()}
      >
        {loading ? 'Sending...' : 'Send'}
      </button>
    </form>
  )
}
