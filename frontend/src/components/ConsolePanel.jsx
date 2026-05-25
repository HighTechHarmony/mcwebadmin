import LogViewer from './LogViewer'
import CommandInput from './CommandInput'

export default function ConsolePanel() {
  return (
    <div className="card console-card">
      <div className="card-header">
        <h2>Console</h2>
      </div>
      <div className="console-body">
        <LogViewer />
        <CommandInput />
      </div>
    </div>
  )
}
