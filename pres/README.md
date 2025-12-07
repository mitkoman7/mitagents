# AI Assistant - Presentation Demo

This folder contains a streamlined version of the AI Assistant focused on **Gmail** and **Databricks** integration for presentation purposes.

## 📁 Contents

- **flask_app_pres.py** - Simplified Flask web app (9 tools: Gmail + Databricks)
- **gmail_mcp_server.py** - Gmail MCP server for email functionality
- **databricks_mcp_server.py** - Databricks MCP server with natural language to SQL
- **.env** - Environment configuration (API keys, credentials)
- **start_presentation.sh** - One-click startup script

## 🚀 Quick Start

### Option 1: Use the Startup Script
```bash
cd pres
./start_presentation.sh
```

### Option 2: Manual Start
```bash
cd pres

# Start Gmail MCP Server
../venv/bin/python3 gmail_mcp_server.py > logs/gmail_server.log 2>&1 &

# Start Databricks MCP Server
../venv/bin/python3 databricks_mcp_server.py > logs/databricks_server.log 2>&1 &

# Start Flask App
../venv/bin/python3 flask_app_pres.py > logs/flask_app.log 2>&1 &
```

## 🌐 Access Points

- **Web Interface**: http://localhost:5007
- **Gmail MCP**: http://localhost:8082
- **Databricks MCP**: http://localhost:8085

## ✨ Key Features

### 1. Natural Language to SQL
Ask questions in plain English and get SQL queries executed automatically:
- "Show me a 3 month attendance report"
- "Count employees by department"
- "List all databases"

### 2. Email Integration
Send query results directly to your email:
- "Email me that report"
- Automatically formats data for email

### 3. Cluster Management
- List all Databricks clusters
- Check cluster status
- Create new clusters

### 4. Conversational Memory
- Remembers your conversation history
- Can reference previous queries and results
- Maintains context across the session

## 🛠️ Available Tools (9 Total)

### Gmail Tools (1)
- **email_me** - Send data to mitkoman@gmail.com

### Databricks Tools (8)
- **natural_language_query** - Convert questions to SQL and execute
- **execute_sql** - Run raw SQL queries
- **list_databases** - Show all databases
- **list_tables** - Show tables in a database
- **get_table_schema** - Get table structure
- **list_clusters** - List all clusters
- **get_cluster_status** - Check cluster status
- **create_cluster** - Create new cluster

## 📊 Sample Queries

Try these in the web interface:

1. **Data Exploration**:
   - "List all my Databricks databases"
   - "Show tables in the default database"
   - "What's the schema of hr_attendance_dummy table?"

2. **Natural Language Queries**:
   - "Show me a 3 month attendance report"
   - "Count employees by department"
   - "Show attendance for IT department"

3. **Email Integration**:
   - "Email me the attendance report"
   - "Send the results to my email"

4. **Cluster Management**:
   - "List all my clusters"
   - "What's the status of analytics-cluster1?"

## 🔧 Configuration

All configuration is in the `.env` file:

- **Azure OpenAI**: For the AI agent (GPT-4)
- **Gmail**: SMTP credentials for sending emails
- **Databricks**: Host, token, cluster ID

## 📝 Logs

All service logs are stored in `pres/logs/`:
- `flask_app.log` - Web application logs
- `gmail_server.log` - Gmail MCP server logs
- `databricks_server.log` - Databricks MCP server logs

## 🛑 Stop Services

```bash
pkill -f gmail_mcp_server && pkill -f databricks_mcp_server && pkill -f flask_app_pres
```

## 🎯 Presentation Talking Points

1. **Natural Language Interface**: No SQL knowledge required
2. **Multi-Agent Architecture**: Separate MCP servers for each service
3. **Conversational Memory**: Context-aware interactions
4. **Email Integration**: Instant result delivery
5. **Cluster Fallback**: Automatic fallback from warehouse to cluster

## 💡 Demo Flow

1. Start with "List all my Databricks databases" - Shows data exploration
2. "Show me a 3 month attendance report" - Demonstrates natural language to SQL
3. "Email me that report" - Shows email integration
4. "List all my clusters" - Demonstrates cluster management
5. Ask a follow-up question using context - Shows memory capability
