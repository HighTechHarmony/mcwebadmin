import { useState } from 'react'
import api from '../api'
import Convert from 'ansi-to-html'

const converter = new Convert({ escapeXML: true })

export default function CommandInput() {
  const [command, setCommand] = useState('')
  const [loading, setLoading] = useState(false)
  const [lastResponse, setLastResponse] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    const cmd = command.trim()
    if (!cmd) return
    setLoading(true)
    setLastResponse(null)
    try {
      const res = await api.post('/console/command', { command: cmd })
      setLastResponse({ success: true, text: res.data.response })
      setCommand('')
    } catch (err) {
      console.error('Command failed:', err)
      setLastResponse({ 
        success: false, 
        text: err.response?.data?.error || 'Failed to send command' 
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="command-input-container">
      {lastResponse && (
        <div className={`command-feedback ${lastResponse.success ? 'success' : 'error'}`}>
          <div className="feedback-header">
            <span>Command Output</span>
            <button className="btn-close" onClick={() => setLastResponse(null)}>×</button>
          </div>
          <pre 
            dangerouslySetInnerHTML={{ 
              __html: lastResponse.text ? converter.toHtml(lastResponse.text) : '(No response)' 
            }}
          />
        </div>
      )}
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
          {loading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </div>
  )
}
