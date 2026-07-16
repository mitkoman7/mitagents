import { useState, useEffect } from 'react'

function fmt(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) +
    ' ' + d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
}

export default function StatsPanel({ onClose }) {
  const [preds, setPreds] = useState([])
  const [expanded, setExpanded] = useState(null)

  useEffect(() => { load() }, [])

  async function load() {
    const r = await fetch('/api/predictions')
    setPreds(await r.json())
  }

  async function mark(id, result) {
    await fetch(`/api/predictions/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ result }),
    })
    load()
  }

  async function remove(id) {
    await fetch(`/api/predictions/${id}`, { method: 'DELETE' })
    load()
  }

  const won   = preds.filter(p => p.result === true).length
  const lost  = preds.filter(p => p.result === false).length
  const total = won + lost
  const rate  = total > 0 ? Math.round((won / total) * 100) : null
  const streak = (() => {
    let s = 0
    for (const p of preds) {
      if (p.result === true) s++
      else if (p.result === false) break
      else break
    }
    return s
  })()

  return (
    <div className="stats-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="stats-panel">
        {/* Header */}
        <div className="stats-header">
          <span className="stats-title">Prediction Tracker</span>
          <button className="stats-close" onClick={onClose}>✕</button>
        </div>

        {/* Balance bar */}
        <div className="stats-balance">
          <div className="balance-numbers">
            <span className="balance-won">{won}W</span>
            <span className="balance-sep"> · </span>
            <span className="balance-lost">{lost}L</span>
            {rate !== null && <span className="balance-rate">{rate}%</span>}
            {streak >= 2 && <span className="balance-streak">🔥 {streak} streak</span>}
          </div>
          {total > 0 && (
            <div className="balance-bar">
              <div className="balance-fill" style={{ width: `${rate}%` }} />
            </div>
          )}
          {preds.length === 0 && (
            <p className="stats-empty">No saved predictions yet.<br/>Tap 💾 after any AI response to save it.</p>
          )}
        </div>

        {/* List */}
        <div className="stats-list">
          {preds.map(p => (
            <div key={p.id} className={`pred-card ${p.result === true ? 'won' : p.result === false ? 'lost' : 'pending'}`}>
              <div className="pred-top" onClick={() => setExpanded(expanded === p.id ? null : p.id)}>
                <div className="pred-main">
                  <span className="pred-bet">{p.best_bet || 'Prediction'}</span>
                  <div className="pred-meta">
                    {p.probability && <span className="pred-prob">{p.probability}</span>}
                    {p.confidence && <span className="pred-conf">{p.confidence}</span>}
                  </div>
                </div>
                <div className="pred-right">
                  <span className="pred-date">{fmt(p.timestamp)}</span>
                  {p.result === true  && <span className="pred-badge won-badge">✓ Won</span>}
                  {p.result === false && <span className="pred-badge lost-badge">✗ Lost</span>}
                  {p.result === null  && <span className="pred-badge pend-badge">⏳</span>}
                </div>
              </div>

              {p.result === null && (
                <div className="pred-actions">
                  <button className="pred-btn won-btn" onClick={() => mark(p.id, true)}>✓ Won</button>
                  <button className="pred-btn lost-btn" onClick={() => mark(p.id, false)}>✗ Lost</button>
                  <button className="pred-btn del-btn" onClick={() => remove(p.id)}>🗑</button>
                </div>
              )}
              {p.result !== null && (
                <div className="pred-actions">
                  <button className="pred-btn reset-btn" onClick={() => mark(p.id, null)}>Reset</button>
                  <button className="pred-btn del-btn" onClick={() => remove(p.id)}>🗑</button>
                </div>
              )}

              {expanded === p.id && p.reply && (
                <div className="pred-expanded">
                  <p className="pred-question">Q: {p.question}</p>
                  <pre className="pred-reply">{p.reply}</pre>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
