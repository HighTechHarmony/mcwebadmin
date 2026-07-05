import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import StatusCard from '../components/StatusCard'
import ConsolePanel from '../components/ConsolePanel'
import ModManager from '../components/ModManager'
import WorldManager from '../components/WorldManager'

const TABS = [
  { id: 'server', label: 'Server Control' },
  { id: 'mods', label: 'Mod Manager' },
  { id: 'worlds', label: 'World Manager' },
  { id: 'console', label: 'Console' },
  { id: 'about', label: 'About' },
]

export default function Dashboard() {
  const { logout } = useAuth()
  const [activeTab, setActiveTab] = useState('server')
  // small token-based signal to force ConsolePanel's sub-tab even if same value
  const [consoleFocusToken, setConsoleFocusToken] = useState(0)

  const focusConsole = () => {
    setActiveTab('console')
    setConsoleFocusToken((t) => t + 1)
  }

  return (
    <div className="app-layout">
      <header className="app-header">
        <span className="header-title">⛏ mcwebadmin</span>
        <button className="btn btn-ghost btn-sm" onClick={logout}>
          Sign out
        </button>
      </header>
      <main className="app-main">
        <div className="tab-bar">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={`tab-btn${activeTab === tab.id ? ' active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* All panels stay mounted to preserve WebSocket + polling */}
        <div style={{ display: activeTab === 'server' ? 'block' : 'none' }}>
          <StatusCard focusConsole={focusConsole} />
        </div>
        <div style={{ display: activeTab === 'mods' ? 'block' : 'none' }}>
          <ModManager />
        </div>
        <div style={{ display: activeTab === 'worlds' ? 'block' : 'none' }}>
          <WorldManager />
        </div>
        <div style={{ display: activeTab === 'console' ? 'block' : 'none' }}>
          <ConsolePanel forceSubTab={{ tab: 'console', token: consoleFocusToken }} />
        </div>
        <div style={{ display: activeTab === 'about' ? 'block' : 'none' }}>
          <div className="card">
            <div className="card-header">
              <h2>About</h2>
            </div>
            <div className="card-body">
              <p style={{ marginTop: 0 }}>
                mcwebadmin — lightweight web-based Minecraft server administration.
              </p>
              <ul style={{ paddingLeft: 18 }}>
                <li><strong>Version:</strong> v1.0.0 (2026-05-25)</li>
                <li>
                  <strong>Developer:</strong> Scott McGrath —
                  <a href="mailto:scott@smcgrath.com">scott@smcgrath.com</a>
                </li>
                <li>
                  <strong>Source:</strong>{' '}
                  <a href="https://github.com/HighTechHarmony/mcwebadmin" target="_blank" rel="noreferrer">
                    https://github.com/HighTechHarmony/mcwebadmin
                  </a>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
