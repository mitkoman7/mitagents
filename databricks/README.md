# Databricks Terminal Bot

A standalone terminal-based AI bot for interacting with Databricks using MCP (Model Context Protocol).

## Setup

1. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure `.env` file with your credentials (already populated)

## Usage

### Start MCP Server (Terminal 1):
```bash
python mcp_server.py
```

### Start Bot (Terminal 2):
```bash
python app.py
```

## Available Commands

- **SQL Queries**: "Show me all tables", "SELECT * FROM my_table LIMIT 10"
- **Clusters**: "List clusters", "What's the cluster status?", "Start the cluster"
- **Jobs**: "List jobs", "Run job 123"
- **Notebooks**: "Run notebook /Users/me/MyNotebook"

## Files

- `mcp_server.py` - MCP server (port 8085)
- `app.py` - Terminal bot interface
- `.env` - Configuration
- `requirements.txt` - Dependencies
