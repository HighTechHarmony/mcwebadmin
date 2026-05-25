import { useAuth } from '../context/AuthContext'
import StatusCard from '../components/StatusCard'
import ConsolePanel from '../components/ConsolePanel'
import ModManager from '../components/ModManager'

export default function Dashboard() {
  const { logout } = useAuth()

  return (
    <div className="app-layout">
      <header className="app-header">
        <span className="header-title">⛏ mcwebadmin</span>
        <button className="btn btn-ghost btn-sm" onClick={logout}>
          Sign out
        </button>
      </header>
      <main className="app-main">
        <StatusCard />
        <ModManager />
        <ConsolePanel />
      </main>
    </div>
  )
}
