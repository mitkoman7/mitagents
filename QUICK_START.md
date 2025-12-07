# Quick Start Guide - MCP Servers & Agents

## 🚀 Start All Servers at Once

### Option 1: Python Script (Recommended)
```bash
python3 start_all_servers.py
```

This will:
- Kill any existing servers on ports 8081-8085
- Start all 5 MCP servers in the background
- Check their health status
- Show you server logs location
- Keep running (Ctrl+C to stop all servers)

### Option 2: Bash Script
```bash
./start_all_servers.sh
```

Starts servers as background processes (use `./stop_all_servers.sh` to stop)

## 🛑 Stop All Servers

### Python
```bash
python3 stop_all_servers.py
```

### Bash
```bash
./stop_all_servers.sh
```

## 📊 Check Server Status

```bash
# Check all servers
curl http://localhost:8081/health  # Soccer
curl http://localhost:8082/health  # Gmail
curl http://localhost:8083/health  # Google Maps
curl http://localhost:8084/health  # TomTom
curl http://localhost:8085/health  # Databricks
```

## 📋 View Server Logs

```bash
# All logs
tail -f logs/*.log

# Specific server
tail -f logs/soccer_server.log
tail -f logs/tomtom_server.log
tail -f logs/databricks_server.log
```

## 🤖 Run Agents (from Claude Code)

Once servers are running, ask Claude Code to run agents:

### Sports Intelligence
```
"Get Manchester United's recent results"
"Analyze Liverpool's performance"
```

### Location Intelligence
```
"Find pizza restaurants in New York"
"Check traffic conditions in Times Square"
```

### Data Analysis (requires Databricks setup)
```
"List all tables in my Databricks database"
"Run SQL query: SELECT * FROM sales LIMIT 10"
```

### ETL Orchestration (requires Databricks)
```
"Run my ETL notebook at /Users/me/pipeline"
"Check status of cluster xyz-123"
```

## 🎯 Available Agents

1. **DataAnalystAgent** - Queries and analyzes Databricks data
2. **SportsIntelligenceAgent** - Analyzes team performance and standings
3. **LocationIntelligenceAgent** - Location search with traffic analysis
4. **ETLOrchestratorAgent** - Manages Databricks ETL pipelines
5. **MultiServiceResearchAgent** - Combines all services for research

## 📁 Project Structure

```
/Users/dimitargrigorov/soccer/
├── start_all_servers.py       # Start all servers (Python)
├── stop_all_servers.py        # Stop all servers (Python)
├── start_all_servers.sh       # Start all servers (Bash)
├── stop_all_servers.sh        # Stop all servers (Bash)
├── portal_agents.py           # Agent definitions
├── logs/                      # Server logs
│   ├── soccer_server.log
│   ├── gmail_server.log
│   ├── maps_server.log
│   ├── tomtom_server.log
│   └── databricks_server.log
├── MCP Servers:
│   ├── map_server.py         # Soccer data (port 8081)
│   ├── google_mcp_server_simple.py  # Gmail (port 8082)
│   ├── google_maps_mcp_server.py    # Google Maps (port 8083)
│   ├── tomtom_mcp_server.py         # TomTom Maps (port 8084)
│   └── databricks_mcp_server.py     # Databricks (port 8085)
└── flask_app_simple.py       # Web UI with all agents
```

## 🔧 Troubleshooting

### Port already in use
```bash
# Kill specific port
lsof -ti:8081 | xargs kill -9

# Or stop all servers
python3 stop_all_servers.py
```

### Server won't start
1. Check logs: `tail -f logs/[server]_server.log`
2. Verify .env configuration
3. Check API keys are configured

### Agent not working
1. Ensure all required servers are running
2. Check server health endpoints
3. View server logs for errors

## ⚙️ Configuration

Edit `.env` file for:
- API keys (TomTom, Google Maps, Football API)
- Databricks credentials
- Email settings
- Server URLs

## 🎓 Examples

### Full Workflow Example
```bash
# 1. Start all servers
python3 start_all_servers.py

# 2. In Claude Code, say:
"Run the sports intelligence agent for Arsenal"

# 3. Agent will:
#    - Get Arsenal's recent matches
#    - Get Premier League standings
#    - Get latest PL results
#    - Email you a comprehensive report

# 4. Stop servers when done
# Press Ctrl+C (if using Python script)
# Or: python3 stop_all_servers.py
```

## 📚 Documentation

- [Databricks Setup](DATABRICKS_SETUP.md)
- [Agent Networking Guide](AGENT_NETWORKING_COMPLETE_GUIDE.md)
- [Gmail Setup](SIMPLE_GMAIL_SETUP.md)

---

**Happy Agent Running!** 🤖🚀
