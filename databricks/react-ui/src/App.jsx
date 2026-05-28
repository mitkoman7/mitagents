import { useState, useEffect, useRef } from 'react'
import ChatMessage from './components/ChatMessage'
import StatusBar from './components/StatusBar'
import databricksLogo from './assets/databricks-logo.png'
import './App.css'

export default function App() {
  const [messages, setMessages] = useState([
    { id: 1, role: 'assistant', text: "Hello! I'm your Databricks AI Assistant. Ask me about clusters, jobs, SQL queries, or notebooks." }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [mcpStatus, setMcpStatus] = useState(null)
  const [liveActivity, setLiveActivity] = useState('')
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    checkHealth()
    const interval = setInterval(checkHealth, 15000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading, liveActivity])

  async function checkHealth() {
    try {
      const res = await fetch('/api/health')
      const data = await res.json()
      setMcpStatus(data.mcp_connected)
    } catch {
      setMcpStatus(false)
    }
  }

  async function sendMessage() {
    const text = input.trim()
    if (!text || loading) return

    setMessages(prev => [...prev, { id: Date.now(), role: 'user', text }])
    setInput('')
    setLoading(true)
    setLiveActivity('')

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      })

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop()

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const event = JSON.parse(line.slice(6))

          if (event.type === 'activity') {
            setLiveActivity(event.tool.replace(/_/g, ' '))
          } else if (event.type === 'activity_done') {
            setLiveActivity('')
          } else if (event.type === 'done' || event.type === 'error') {
            setLiveActivity('')
            setMessages(prev => [...prev, {
              id: Date.now() + 1,
              role: 'assistant',
              text: event.reply,
              activities: event.activities || [],
            }])
          }
        }
      }
    } catch (e) {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        text: `Connection error: ${e.message}`,
        activities: [],
      }])
    } finally {
      setLoading(false)
      setLiveActivity('')
      inputRef.current?.focus()
    }
  }

  async function clearChat() {
    await fetch('/api/clear', { method: 'POST' })
    setMessages([{ id: Date.now(), role: 'assistant', text: 'Conversation cleared. How can I help you?' }])
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <div className="header-logo">
            <img src={databricksLogo} alt="Databricks" />
          </div>
          <div className="header-wordmark">
            <div className="header-title">DATABRICKS ASSISTANT</div>
            <div className="header-subtitle">Self-Evolving · Azure OpenAI · MCP</div>
          </div>
        </div>
        <div className="header-right">
          <StatusBar connected={mcpStatus} />
          <button className="clear-btn" onClick={clearChat} title="Clear conversation">⌫</button>
        </div>
      </header>

      <main className="messages">
        {messages.map(msg => (
          <ChatMessage key={msg.id} message={msg} />
        ))}

        {loading && (
          <div className="msg-row assistant">
            <div className="avatar assistant-avatar">
              <img src={databricksLogo} alt="Databricks" />
            </div>
            <div className="msg-body">
              {liveActivity && (
                <div className="live-activity">
                  <span className="live-dot" />
                  <span>executing</span>
                  <strong>{liveActivity}</strong>
                </div>
              )}
              <div className="bubble assistant-bubble typing">
                <span /><span /><span />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </main>

      <footer className="input-area">
        <div className="input-wrapper">
          <textarea
            ref={inputRef}
            className="chat-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about clusters, jobs, SQL queries, notebooks..."
            rows={1}
            disabled={loading}
          />
          <button className="send-btn" onClick={sendMessage} disabled={loading || !input.trim()}>
            {loading ? '◌' : '↑'}
          </button>
        </div>
        <div className="input-hint">↵ send &nbsp;·&nbsp; ⇧↵ new line</div>
      </footer>
    </div>
  )
}
