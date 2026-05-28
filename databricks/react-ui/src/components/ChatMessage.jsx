import ReactMarkdown from 'react-markdown'
import MermaidDiagram from './MermaidDiagram'
import databricksLogo from '../assets/databricks-logo.png'

const TOOL_ICONS = {
  execute_sql: '⬡', list_clusters: '◈', get_cluster_status: '◈',
  start_cluster: '▷', stop_cluster: '□', list_jobs: '⊞',
  run_job: '▷', list_notebooks: '▤', find_notebooks: '◎',
  run_notebook: '▷', list_databases: '⬡', list_tables: '▦',
  get_table_schema: '▦', get_table_preview: '◉', get_table_stats: '◈',
  list_catalogs: '⊟', search_tables: '◎', evolve_discover: '⟡',
  evolve_list: '⟡', generate_schema: '◇',
}

function extractMermaid(text) {
  const parts = []
  const regex = /```mermaid\n([\s\S]*?)```/g
  let last = 0, match
  while ((match = regex.exec(text)) !== null) {
    if (match.index > last) parts.push({ type: 'text', content: text.slice(last, match.index) })
    parts.push({ type: 'mermaid', content: match[1].trim() })
    last = match.index + match[0].length
  }
  if (last < text.length) parts.push({ type: 'text', content: text.slice(last) })
  return parts
}

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user'
  const activities = message.activities || []
  const parts = isUser ? null : extractMermaid(message.text)

  return (
    <div className={`msg-row ${message.role}`}>
      <div className={`avatar ${isUser ? 'user-avatar' : 'assistant-avatar'}`}>
        {isUser
          ? '⬡'
          : <img src={databricksLogo} alt="Databricks" />
        }
      </div>
      <div className="msg-body">
        {!isUser && activities.length > 0 && (
          <div className="activity-bar">
            <span className="activity-label">used</span>
            {activities.map(tool => (
              <span key={tool} className="activity-tag">
                {TOOL_ICONS[tool] || '◆'} {tool.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        )}
        <div className={`bubble ${isUser ? 'user-bubble' : 'assistant-bubble'}`}>
          {isUser ? message.text : parts.map((p, i) =>
            p.type === 'mermaid'
              ? <MermaidDiagram key={i} code={p.content} />
              : p.content.trim()
                ? <ReactMarkdown key={i}>{p.content}</ReactMarkdown>
                : null
          )}
        </div>
      </div>
    </div>
  )
}
