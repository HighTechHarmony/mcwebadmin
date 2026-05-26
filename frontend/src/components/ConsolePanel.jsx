import { useState, useRef, useEffect } from 'react'
import Convert from 'ansi-to-html'
import LogViewer from './LogViewer'
import CommandInput from './CommandInput'

const converter = new Convert({ escapeXML: true })

const COMMAND_SHORTCUTS = ['help', 'list', 'op']

export default function ConsolePanel({ forceSubTab = null }) {
  const [activeSubTab, setActiveSubTab] = useState('console')
  const [command, setCommand] = useState('')
  const [lastResponse, setLastResponse] = useState(null)
  const inputRef = useRef(null)

  // allow parent to force the active sub-tab (e.g. focus console)
  // `forceSubTab` is expected as { tab: 'console'|'output', token: number }
  useEffect(() => {
    if (forceSubTab && forceSubTab.token) {
      setActiveSubTab(forceSubTab.tab)
    }
  }, [forceSubTab && forceSubTab.token])

  const handleShortcut = (cmd) => {
    setCommand(cmd + ' ')
    inputRef.current?.focus()
  }

  const handleResponse = (resp) => {
    setLastResponse(resp)
    setActiveSubTab('output')
  }

  return (
    <div className="card console-card">
      <div className="sub-tab-bar">
        <button
          className={`sub-tab-btn${activeSubTab === 'console' ? ' active' : ''}`}
          onClick={() => setActiveSubTab('console')}
        >
          Console
        </button>
        <button
          className={`sub-tab-btn${activeSubTab === 'output' ? ' active' : ''}`}
          onClick={() => setActiveSubTab('output')}
        >
          Command Output
        </button>
      </div>

      {/* LogViewer stays mounted to preserve the WebSocket connection */}
      <div style={{ display: activeSubTab === 'console' ? 'block' : 'none' }}>
        <LogViewer forceFetchToken={forceSubTab} />
      </div>

      <div
        className="output-panel"
        style={{ display: activeSubTab === 'output' ? 'block' : 'none' }}
      >
        {lastResponse ? (
          <pre
            className={`output-pre${lastResponse.success ? '' : ' error'}`}
            dangerouslySetInnerHTML={{
              __html: lastResponse.text
                ? converter.toHtml(lastResponse.text)
                : '(No response)',
            }}
          />
        ) : (
          <div className="output-empty">No command output yet.</div>
        )}
      </div>

      <div className="shortcuts-bar">
        <span className="shortcuts-label">Shortcuts:</span>
        {COMMAND_SHORTCUTS.map((cmd) => (
          <button
            key={cmd}
            type="button"
            className="shortcut-btn"
            onClick={() => handleShortcut(cmd)}
          >
            {cmd}
          </button>
        ))}
      </div>

      <CommandInput
        value={command}
        onChange={setCommand}
        onResponse={handleResponse}
        inputRef={inputRef}
      />
    </div>
  )
}
