import { useState } from 'react'

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function ModPane({
  title,
  description,
  mods,
  actionLabel,
  secondaryActionLabel,
  onAction,
  onSecondaryAction,
}) {
  const [pending, setPending] = useState(null)

  const handle = async (filename, fn) => {
    setPending(filename)
    try {
      await fn(filename)
    } catch (err) {
      console.error(`Mod action failed for ${filename}:`, err)
    } finally {
      setPending(null)
    }
  }

  return (
    <div className="mod-pane">
      <div className="mod-pane-header">
        <h3>{title}</h3>
        <span className="mod-count">
          {mods.length} mod{mods.length !== 1 ? 's' : ''}
        </span>
      </div>
      {description && <div className="mod-path">{description}</div>}
      <div className="mod-list">
        {mods.length === 0 && <div className="mod-empty">No mods</div>}
        {mods.map((mod) => (
          <div key={mod.name} className="mod-item">
            <div className="mod-info">
              <span className="mod-name" title={mod.name}>
                {mod.name}
              </span>
              <span className="mod-size">{formatBytes(mod.size)}</span>
            </div>
            <div className="mod-actions">
              <button
                className="btn btn-sm btn-primary"
                onClick={() => handle(mod.name, onAction)}
                disabled={pending === mod.name}
              >
                {pending === mod.name ? '…' : actionLabel}
              </button>
              {onSecondaryAction && (
                <button
                  className="btn btn-sm btn-danger"
                  onClick={() => handle(mod.name, onSecondaryAction)}
                  disabled={pending === mod.name}
                >
                  {secondaryActionLabel ?? 'Delete'}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
