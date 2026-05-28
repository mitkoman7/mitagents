export default function StatusBar({ connected }) {
  const label = connected === null ? 'Checking...' : connected ? 'MCP Connected' : 'MCP Offline'
  const color = connected === null ? '#8892aa' : connected ? '#22c55e' : '#ef4444'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color }}>
      <span style={{
        width: 8, height: 8, borderRadius: '50%', background: color,
        boxShadow: connected ? `0 0 6px ${color}` : 'none',
        animation: connected ? 'pulse 2s infinite' : 'none'
      }} />
      {label}
      <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.5} }`}</style>
    </div>
  )
}
