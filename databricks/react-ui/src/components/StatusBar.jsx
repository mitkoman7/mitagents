export default function StatusBar({ connected }) {
  const state = connected === null ? 'checking' : connected ? 'connected' : 'disconnected'
  const labels = { checking: 'CHECKING', connected: 'MCP ONLINE', disconnected: 'MCP OFFLINE' }

  return (
    <div className="status-wrapper">
      <span className={`status-dot ${state}`} />
      <span className={`status-text ${state}`}>{labels[state]}</span>
    </div>
  )
}
