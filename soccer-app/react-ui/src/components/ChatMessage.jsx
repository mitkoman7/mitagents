import { useState } from 'react'

function parsePrediction(text) {
  const bet  = text.match(/🎯 \*\*BEST BET:\*\*\s*(.+)/)?.[1]?.trim()
  const prob = text.match(/📊 \*\*Estimated probability:\*\*\s*(.+)/)?.[1]?.trim()
  const conf = text.match(/💪 \*\*Confidence:\*\*\s*(.+)/)?.[1]?.trim()
  return bet ? { best_bet: bet, probability: prob || '', confidence: conf || '' } : null
}

export default function ChatMessage({ message, question }) {
  const isUser = message.role === 'user'
  const [saved, setSaved] = useState(false)
  const prediction = !isUser ? parsePrediction(message.text || '') : null

  async function savePrediction() {
    if (saved || !prediction) return
    await fetch('/api/predictions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...prediction, reply: message.text, question: question || '' }),
    })
    setSaved(true)
  }

  return (
    <div className={`msg-row ${isUser ? 'user' : 'assistant'}`}>
      <div className={`bubble ${isUser ? 'user-bubble' : 'assistant-bubble'}`}>
        {message.text}
      </div>

      {!isUser && (
        <div className="msg-footer">
          {message.activities?.length > 0 && (
            <div className="activity-tags">
              {message.activities.map((q, i) => (
                <span key={i} className="activity-tag">🔍 {q}</span>
              ))}
            </div>
          )}
          {prediction && (
            <button
              className={`save-pred-btn ${saved ? 'saved' : ''}`}
              onClick={savePrediction}
              title={saved ? 'Saved to tracker' : 'Save prediction'}
            >
              {saved ? '✓ Saved' : '💾 Save'}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
