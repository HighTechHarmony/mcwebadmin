import { useState } from 'react'
import api from '../api'

export default function CommandInput() {
  const [command, setCommand] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    const cmd = command.trim()
    if (!cmd) return
    setLoading(true)
    try {
      await api.post('/console/command', { command: cmd })
      setCommand('')
    } catch (err) {
      console.error('Command failed:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form className="command-input-form" onSubmit={handleSubmit}>
      <span className="command-prompt">&gt;</span>
      <input
        type="text"
        className="command-input"
        placeholder="Enter server command…"
        value={command}
        onChange={(e) => setCommand(e.target.value)}
        disabled={loading}
        autoComplete="off"
        spellCheck={false}
      />
      <button
        type="submit"
        className="btn btn-primary btn-sm"
        disabled={loading || !command.trim()}
      >
        Send
      </button>
    </form>
  )
}
