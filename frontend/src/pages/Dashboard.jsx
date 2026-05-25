import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import StatusCard from '../components/StatusCard'
import ConsolePanel from '../components/ConsolePanel'
import ModManager from '../components/ModManager'

const TABS = [
  { id: 'server', label: 'Server Control' },
  { id: 'mods', label: 'Mod Manager' },
  { id: 'console', label: 'Console' },
]

export default function Dashboard() {
  const { logout } = useAuth()
  const [activeTab, setActiveTab] = useState('server')

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
          <StatusCard />
        </div>
        <div style={{ display: activeTab === 'mods' ? 'block' : 'none' }}>
          <ModManager />
        </div>
        <div style={{ display: activeTab === 'console' ? 'block' : 'none' }}>
          <ConsolePanel />
        </div>
      </main>
    </div>
  )
}
