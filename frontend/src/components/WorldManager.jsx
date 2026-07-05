import { useState, useEffect, useCallback, useRef } from 'react'
import api from '../api'

function formatSize(mb) {
  if (mb < 1) return `${(mb * 1024).toFixed(0)} KB`
  if (mb < 1024) return `${mb.toFixed(1)} MB`
  return `${(mb / 1024).toFixed(1)} GB`
}

export default function WorldManager() {
  const [status, setStatus] = useState(null)
  const [activeContents, setActiveContents] = useState([])
  const [inactiveContents, setInactiveContents] = useState([])
  const [loading, setLoading] = useState(false)
  const [switching, setSwitching] = useState(false)
  const [downloading, setDownloading] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState(null)
  const [error, setError] = useState(null)
  const fileInputRef = useRef(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [statusRes, activeRes, inactiveRes] = await Promise.all([
        api.get('/worlds/status'),
        api.get('/worlds/contents/active').catch(() => ({ data: { entries: [] } })),
        api.get('/worlds/contents/inactive').catch(() => ({ data: { entries: [] } })),
      ])
      setStatus(statusRes.data)
      setActiveContents(activeRes.data.entries || [])
      setInactiveContents(inactiveRes.data.entries || [])
    } catch (err) {
      console.error('Failed to load world status:', err)
      setError('Failed to load world status')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const handleSwap = async () => {
    setSwitching(true)
    setError(null)
    try {
      await api.post('/worlds/switch')
      await refresh()
    } catch (err) {
      const msg = err.response?.data?.error || 'Swap failed'
      setError(msg)
      console.error('World swap failed:', err)
    } finally {
      setSwitching(false)
    }
  }

  const handleDownload = async (which) => {
    setDownloading(which)
    setError(null)
    try {
      const res = await api.get(`/worlds/download/${which}`, {
        responseType: 'blob',
      })

      const disposition = res.headers['content-disposition'] || ''
      const match = disposition.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i)
      const rawFilename = match?.[1] || match?.[2] || `${which}_world.zip`
      const filename = decodeURIComponent(rawFilename)

      const blobUrl = window.URL.createObjectURL(res.data)
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(blobUrl)
    } catch (err) {
      let msg = 'World download failed'
      const blob = err.response?.data
      if (blob instanceof Blob) {
        try {
          const text = await blob.text()
          const payload = JSON.parse(text)
          msg = payload.error || msg
        } catch {
          // Fall back to the default message when the error body is not JSON.
        }
      } else {
        msg = err.response?.data?.error || msg
      }
      setError(msg)
      console.error('World download failed:', err)
    } finally {
      setDownloading(null)
    }
  }

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    const inactiveHasFiles = inactiveContents.length > 0 || (status?.inactive_size_mb ?? 0) > 0
    if (
      inactiveHasFiles &&
      !window.confirm(
        'This will replace the world that is in the inactive world slot, ensure you have backed it up.',
      )
    ) {
      if (fileInputRef.current) fileInputRef.current.value = ''
      return
    }

    setUploading(true)
    setUploadMsg(null)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      await api.post('/worlds/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setUploadMsg({ type: 'success', text: `${file.name} uploaded and extracted` })
      await refresh()
    } catch (err) {
      const msg = err.response?.data?.error || 'Upload failed'
      setUploadMsg({ type: 'error', text: msg })
      console.error('World upload failed:', err)
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const serverRunning = status?.server_running ?? false
  const canSwap = !serverRunning && !switching

  const diskTotal = status?.disk_total_mb ?? 0
  const diskFree = status?.disk_free_mb ?? 0
  const diskUsed = status?.disk_used_mb ?? 0
  const worldUsed = (status?.active_size_mb ?? 0) + (status?.inactive_size_mb ?? 0)
  const diskPct = diskTotal > 0 ? Math.round((diskUsed / diskTotal) * 100) : 0
  const worldPct = diskTotal > 0 ? Math.round((worldUsed / diskTotal) * 100) : 0

  return (
    <div className="card">
      <div className="card-header">
        <h2>World Manager</h2>
        <button
          className="btn btn-ghost btn-sm"
          onClick={refresh}
          disabled={loading}
        >
          {loading ? 'Loading…' : '↺ Refresh'}
        </button>
      </div>

      {error && (
        <div className="world-error-banner">
          {error}
          <button className="btn btn-sm btn-ghost" onClick={() => setError(null)}>
            Dismiss
          </button>
        </div>
      )}

      {/* ── Disk usage bar ── */}
      {diskTotal > 0 && (
        <div className="world-disk-bar">
          <div className="world-disk-label">
            Server disk: <strong>{formatSize(diskFree)} free</strong> of {formatSize(diskTotal)}
          </div>
          <div className="world-disk-track">
            <div className="world-disk-fill" style={{ width: `${diskPct}%` }}>
              {diskPct > 8 && <span className="world-disk-pct">{diskPct}% used</span>}
            </div>
          </div>
          <div className="world-disk-detail">
            Worlds consume <strong>{formatSize(worldUsed)}</strong> ({worldPct}% of total)
          </div>
        </div>
      )}

      <div className="world-manager-body">
        {/* Active World Pane */}
        {renderPane({
          title: 'Active World',
          path: '/opt/fabric/world',
          which: 'active',
          exists: status?.active_exists,
          sizeMb: status?.active_size_mb,
          contents: activeContents,
          downloading,
          onDownload: handleDownload,
        })}

        {/* Swap Button Column */}
        <div className="world-swap-column">
          {serverRunning && (
            <div className="world-swap-hint">
              Stop the server before swapping worlds
            </div>
          )}
          <button
            className="btn world-swap-btn"
            disabled={!canSwap}
            onClick={handleSwap}
          >
            {switching ? '⟳ Swapping…' : '⇄ Swap Worlds'}
          </button>
        </div>

        {/* Inactive World Pane */}
        {renderPane({
          title: 'Inactive World',
          path: '/opt/fabric/world.inactive',
          which: 'inactive',
          exists: status?.inactive_exists,
          sizeMb: status?.inactive_size_mb,
          contents: inactiveContents,
          downloading,
          onDownload: handleDownload,
          extra: (
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept=".zip"
                style={{ display: 'none' }}
                onChange={handleUpload}
              />
              <button
                className="btn btn-sm"
                style={{ background: 'var(--primary)', color: '#fff' }}
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                title="Upload a zipped world"
              >
                {uploading ? '⟳ Extracting…' : '⬆ Upload ZIP'}
              </button>
              {uploadMsg && (
                <div className={`upload-message ${uploadMsg.type}`} style={{ fontSize: 11, marginTop: 6 }}>
                  {uploadMsg.text}
                </div>
              )}
            </>
          ),
        })}
      </div>
    </div>
  )
}

function renderPane({ title, path, which, exists, sizeMb, contents, downloading, onDownload, extra }) {
  const isDownloading = downloading === which

  return (
    <div className="world-pane">
      <div className="world-pane-header">
        <h3>{title}</h3>
        {exists && <span className="mod-count">{formatSize(sizeMb)}</span>}
      </div>
      <div className="mod-path">{path}</div>
      <div className="world-status-area">
        {exists ? (
          <span className="status-badge status-active">Present</span>
        ) : (
          <span className="status-badge status-inactive">Not found</span>
        )}
      </div>

      {/* Contents list */}
      {exists && contents.length > 0 && (
        <div className="world-contents">
          <div className="world-contents-header">
            Contents ({contents.length} items)
          </div>
          <div className="world-contents-list">
            {contents.map((entry) => (
              <div key={entry.name} className="world-contents-item">
                <span className="world-contents-icon">
                  {entry.is_dir ? '📁' : '📄'}
                </span>
                <span className="world-contents-name" title={entry.name}>
                  {entry.name}
                </span>
                <span className="world-contents-size">
                  {formatSize(entry.size_mb)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
      {exists && contents.length === 0 && (
        <div className="mod-empty" style={{ padding: '12px 0' }}>Empty</div>
      )}

      <div className="world-actions">
        <button
          className="btn btn-sm btn-primary"
          onClick={() => onDownload(which)}
          disabled={!exists || isDownloading}
        >
          {isDownloading ? '⟳ Zipping…' : 'Download ZIP'}
        </button>
        {extra}
      </div>
    </div>
  )
}
