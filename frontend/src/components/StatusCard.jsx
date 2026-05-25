import { useState, useEffect, useCallback } from 'react'
import api from '../api'

const STATUS_META = {
  active:       { label: 'Online',     cls: 'status-active' },
  activating:   { label: 'Starting…',  cls: 'status-activating' },
  deactivating: { label: 'Stopping…',  cls: 'status-activating' },
  inactive:     { label: 'Offline',    cls: 'status-inactive' },
  failed:       { label: 'Failed',     cls: 'status-failed' },
}

export default function StatusCard() {
  const [status, setStatus] = useState('unknown')
  const [pendingAction, setPendingAction] = useState('')

  const fetchStatus = useCallback(async () => {
    try {
      const res = await api.get('/server/status')
      setStatus(res.data.status)
    } catch {
      setStatus('unknown')
    }
  }, [])

  // Poll every 10 s
  useEffect(() => {
    fetchStatus()
    const id = setInterval(fetchStatus, 10000)
    return () => clearInterval(id)
  }, [fetchStatus])

  const handleAction = async (action) => {
    setPendingAction(action)
    try {
      await api.post(`/server/${action}`)
      // Give systemd a moment then poll twice
      setTimeout(fetchStatus, 1500)
      setTimeout(fetchStatus, 4000)
    } catch (err) {
      console.error('Server action failed:', err)
    } finally {
      setPendingAction('')
    }
  }

  const meta = STATUS_META[status] ?? { label: status, cls: 'status-unknown' }
  const busy = !!pendingAction

  return (
    <div className="card">
      <div className="card-header">
        <h2>Server Control</h2>
        <span className={`status-badge ${meta.cls}`}>{meta.label}</span>
      </div>
      <div className="card-body btn-group">
        <button
          className="btn btn-success"
          onClick={() => handleAction('start')}
          disabled={busy || status === 'active'}
        >
          {pendingAction === 'start' ? '…' : '▶ Start'}
        </button>
        <button
          className="btn btn-danger"
          onClick={() => handleAction('stop')}
          disabled={busy || status === 'inactive'}
        >
          {pendingAction === 'stop' ? '…' : '■ Stop'}
        </button>
        <button
          className="btn btn-warning"
          onClick={() => handleAction('restart')}
          disabled={busy}
        >
          {pendingAction === 'restart' ? '…' : '↺ Restart'}
        </button>
      </div>
    </div>
  )
}
