import databricksLogo from '../assets/databricks-logo.png'

const TOOL_ICONS = {
  execute_sql: '🗄️', list_clusters: '🖥️', get_cluster_status: '🖥️',
  start_cluster: '▶️', stop_cluster: '⏹️', list_jobs: '⚙️', run_job: '▶️',
  list_notebooks: '📓', find_notebooks: '🔍', run_notebook: '▶️',
  list_databases: '🗄️', list_tables: '📋', get_table_schema: '📋',
  get_table_preview: '👁️', get_table_stats: '📊', list_catalogs: '📚',
  search_tables: '🔍', evolve_discover: '🧬', evolve_list: '🧬',
}

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user'
  const activities = message.activities || []

  return (
    <div className={`message ${message.role}`}>
      <div className="avatar">
        {isUser
          ? '👤'
          : <img src={databricksLogo} alt="Databricks" style={{ width: '100%', height: '100%', objectFit: 'contain', borderRadius: 6 }} />
        }
      </div>
      <div className="message-body">
        {!isUser && activities.length > 0 && (
          <div className="activity-bar">
            <span className="activity-label">Used:</span>
            {activities.map(tool => (
              <span key={tool} className="activity-tag">
                {TOOL_ICONS[tool] || '🔧'} {tool.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        )}
        <div className="bubble">{message.text}</div>
      </div>
    </div>
  )
}
