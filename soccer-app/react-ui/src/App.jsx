import { useState, useEffect, useRef } from 'react'
import ChatMessage from './components/ChatMessage'
import StatsPanel from './components/StatsPanel'
import './App.css'

const AGENT_ICONS = {
  orchestrator: '🧭',
  specialists:  '⚡',
  '1x2':        '⚽',
  goals:        '🎯',
  corners:      '🔺',
  cards:        '🃏',
  synthesizer:  '🧪',
}

const COMPETITIONS = [
  { label: 'Europa League', key: 'europa league' },
  { label: 'Champions League', key: 'champions league' },
  { label: 'Conference League', key: 'conference league' },
  { label: 'Premier League', key: 'premier league' },
  { label: 'La Liga', key: 'la liga' },
  { label: 'Bundesliga', key: 'bundesliga' },
]

export default function App() {
  const [messages, setMessages] = useState([
    {
      id: 1, role: 'assistant',
      text: "Hi! I'm your Soccer AI analyst. Ask me to predict matches, analyse team form, or tap a league below to see today's fixtures.",
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [mcpStatus, setMcpStatus] = useState(null)
  const [liveActivity, setLiveActivity] = useState(null)
  const [fixtures, setFixtures] = useState(null)
  const [fixturesLoading, setFixturesLoading] = useState(false)
  const [activeComp, setActiveComp] = useState(null)
  const [showStats, setShowStats] = useState(false)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)
  const lastQuestion = useRef('')

  useEffect(() => {
    checkHealth()
    const t = setInterval(checkHealth, 15000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading, liveActivity, fixtures])

  async function checkHealth() {
    try {
      const r = await fetch('/api/health')
      const d = await r.json()
      setMcpStatus(d.mcp_connected)
    } catch { setMcpStatus(false) }
  }

  async function loadFixtures(comp) {
    if (activeComp === comp) {
      setFixtures(null)
      setActiveComp(null)
      return
    }
    setActiveComp(comp)
    setFixturesLoading(true)
    setFixtures(null)
    try {
      const r = await fetch(`/api/fixtures?competition=${encodeURIComponent(comp)}`)
      const d = await r.json()
      setFixtures(d)
    } catch (e) {
      setFixtures({ matches: [], error: e.message })
    } finally {
      setFixturesLoading(false)
    }
  }

  async function sendMessage(text) {
    const msg = (text || input).trim()
    if (!msg || loading) return
    setFixtures(null)
    setActiveComp(null)
    lastQuestion.current = msg
    setMessages(prev => [...prev, { id: Date.now(), role: 'user', text: msg }])
    setInput('')
    setLoading(true)
    setLiveActivity(null)

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg }),
      })
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const parts = buf.split('\n\n')
        buf = parts.pop()

        for (const part of parts) {
          if (!part.startsWith('data: ')) continue
          const ev = JSON.parse(part.slice(6))
          if (ev.type === 'activity') setLiveActivity({ agent: ev.agent || '', query: ev.query || ev.tool || '' })
          else if (ev.type === 'activity_done') setLiveActivity(null)
          else if (ev.type === 'done' || ev.type === 'error') {
            setLiveActivity('')
            setMessages(prev => [...prev, {
              id: Date.now() + 1,
              role: 'assistant',
              text: ev.reply,
              activities: ev.activities || [],
              question: lastQuestion.current,
            }])
          }
        }
      }
    } catch (e) {
      setMessages(prev => [...prev, {
        id: Date.now() + 1, role: 'assistant',
        text: `Connection error: ${e.message}`, activities: [],
      }])
    } finally {
      setLoading(false)
      setLiveActivity(null)
      inputRef.current?.focus()
    }
  }

  async function clearChat() {
    await fetch('/api/clear', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) })
    setMessages([{ id: Date.now(), role: 'assistant', text: 'Chat cleared. Ready for kick-off!' }])
    setFixtures(null)
    setActiveComp(null)
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  const showSuggestions = messages.length <= 1 && !loading
  const statusClass = mcpStatus === true ? 'on' : mcpStatus === false ? 'off' : 'loading'
  const statusLabel = mcpStatus === true ? 'o4-mini' : mcpStatus === false ? 'Offline' : '...'

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-brand">
          <div className="brand-emblem">⚽</div>
          <div className="brand-wordmark">
            <div className="brand-name">Soccer AI</div>
            <div className="brand-tagline">Match predictions · Team analysis</div>
          </div>
        </div>
        <div className="header-right">
          <div className={`live-badge ${statusClass}`}>
            <span className="live-dot" />
            {statusLabel}
          </div>
          <button className="icon-btn" onClick={() => setShowStats(true)} title="Prediction tracker">
            <svg viewBox="0 0 24 24"><path d="M18 20V10M12 20V4M6 20v-6"/></svg>
          </button>
          <button className="icon-btn" onClick={clearChat} title="New chat">
            <svg viewBox="0 0 24 24"><path d="M3 12a9 9 0 1 0 9-9M3 3v6h6"/></svg>
          </button>
        </div>
      </header>

      <h1 className="welcome-head">
        Let's Analyse<br /><span>Your Match</span>
      </h1>

      {/* Competition tabs */}
      <div className="comp-tabs">
        {COMPETITIONS.map(c => (
          <button
            key={c.key}
            className={`comp-tab ${activeComp === c.key ? 'active' : ''}`}
            onClick={() => loadFixtures(c.key)}
          >
            {c.label}
          </button>
        ))}
      </div>

      {/* Fixtures panel */}
      {(fixturesLoading || fixtures) && (
        <div className="fixtures-panel">
          {fixturesLoading && <p className="fixtures-loading">Loading fixtures…</p>}
          {fixtures && fixtures.matches?.length === 0 && !fixtures.web_fallback && (
            <p className="fixtures-empty">No fixtures found today.</p>
          )}
          {fixtures?.web_fallback && fixtures.matches?.length === 0 && (
            <div className="fixtures-web-fallback">
              <p className="fixtures-fallback-label">Web search results:</p>
              <pre className="fixtures-fallback-text">{fixtures.web_fallback.slice(0, 800)}</pre>
            </div>
          )}
          {fixtures && fixtures.matches?.length > 0 && (
            <div className="fixtures-list">
              {fixtures.matches.map((m, i) => (
                <button
                  key={i}
                  className="fixture-row"
                  onClick={() => sendMessage(`Best bet for ${m.home} vs ${m.away} today?`)}
                >
                  <span className="fixture-row-teams">
                    <span className="fixture-team home">{m.home}</span>
                    <span className="fixture-row-vs">vs</span>
                    <span className="fixture-team away">{m.away}</span>
                  </span>
                  <span className="fixture-row-meta">
                    {m.time && <span className="fixture-time">{m.time.slice(11, 16) || m.time}</span>}
                    <span className="fixture-status">{m.status !== 'Scheduled' ? m.status : ''}</span>
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Messages */}
      <main className="messages">
        {showSuggestions && !fixtures && (
          <div className="suggestions-section">
            <p className="suggestions-label">Quick analysis</p>
            <div className="fixture-grid">
              {[
                { icon: '🎯', text: 'Best bet: CSKA Sofia vs Derry City today' },
                { icon: '📊', text: 'Best market: Real Madrid vs Bayern Munich' },
                { icon: '🏆', text: 'Best bet in Champions League tonight?' },
                { icon: '🔮', text: 'Corners or goals — Man City vs Tottenham?' },
              ].map(s => (
                <button key={s.text} className="fixture-card" onClick={() => sendMessage(s.text)}>
                  <div className="fixture-icon-wrap">{s.icon}</div>
                  <span className="fixture-text">{s.text}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map(msg => (
          <ChatMessage key={msg.id} message={msg} question={msg.question} />
        ))}

        {loading && (
          <div className="msg-row assistant">
            <div className="live-analysis">
              <span className="live-analysis-dot" />
              {liveActivity ? (
                <>
                  <span className={`live-agent-icon agent-${liveActivity.agent}`}>
                    {AGENT_ICONS[liveActivity.agent] || '🔍'}
                  </span>
                  <span className="live-tool-name">{liveActivity.query}</span>
                </>
              ) : (
                <>
                  <span className="live-analysis-text">Reasoning</span>
                  <span className="live-tool-name">multi-agent · analysing</span>
                </>
              )}
            </div>
            <div className="bubble assistant-bubble typing-bubble">
              <span /><span /><span />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </main>

      {/* Input */}
      <footer className="input-area">
        <div className="input-shell">
          <textarea
            ref={inputRef}
            className="chat-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask about a match, team form, prediction…"
            rows={1}
            disabled={loading}
          />
          <button className="send-btn" onClick={() => sendMessage()} disabled={loading || !input.trim()}>
            {loading ? <span className="spin">◌</span> : '↑'}
          </button>
        </div>
        <p className="input-hint">↵ send · ⇧↵ new line</p>
      </footer>

      {showStats && <StatsPanel onClose={() => setShowStats(false)} />}
    </div>
  )
}
