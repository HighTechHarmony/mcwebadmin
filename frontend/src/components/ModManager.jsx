import { useState, useEffect, useCallback } from 'react'
import api from '../api'
import ModPane from './ModPane'
import UploadZone from './UploadZone'

export default function ModManager() {
  const [installed, setInstalled] = useState([])
  const [stash, setStash] = useState([])
  const [loading, setLoading] = useState(false)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const [instRes, stashRes] = await Promise.all([
        api.get('/mods/installed'),
        api.get('/mods/stash'),
      ])
      setInstalled(instRes.data)
      setStash(stashRes.data)
    } catch (err) {
      console.error('Failed to load mods:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const moveToStash = async (filename) => {
    await api.post('/mods/move_to_stash', { filename })
    await refresh()
  }

  const moveToInstalled = async (filename) => {
    await api.post('/mods/move_to_installed', { filename })
    await refresh()
  }

  const deleteFromStash = async (filename) => {
    await api.delete(`/mods/stash/${encodeURIComponent(filename)}`)
    await refresh()
  }

  return (
    <div className="card">
      <div className="card-header">
        <h2>Mod Manager</h2>
        <button
          className="btn btn-ghost btn-sm"
          onClick={refresh}
          disabled={loading}
        >
          {loading ? 'Loading…' : '↺ Refresh'}
        </button>
      </div>
      <div className="mod-manager-body">
        <ModPane
          title="Installed"
          description="/opt/fabric/mods/"
          mods={installed}
          actionLabel="→ Stash"
          onAction={moveToStash}
        />
        <div className="mod-stash-column">
          <ModPane
            title="Stash"
            description="/opt/fabric/mod_stash/"
            mods={stash}
            actionLabel="← Install"
            secondaryActionLabel="Delete"
            onAction={moveToInstalled}
            onSecondaryAction={deleteFromStash}
          />
          <UploadZone onUpload={refresh} />
        </div>
      </div>
    </div>
  )
}
