# Self-Evolving Databricks AI Agent — Architecture

An AI-powered terminal bot that dynamically discovers and adds new Databricks API capabilities at runtime, persisting evolved tools across sessions.

---

## System Overview

```
┌──────────┐     ┌──────────────┐     ┌────────────────┐     ┌─────────────┐
│          │     │              │     │                │     │             │
│   User   │────▶│   app.py     │────▶│ mcp_server.py  │────▶│ Databricks  │
│ Terminal  │◀────│ LangChain +  │◀────│ FastAPI :8099  │◀────│ SQL Warehouse│
│          │     │ Azure OpenAI │     │ Tool Registry  │     │ REST API    │
└──────────┘     └──────────────┘     └───────┬────────┘     └─────────────┘
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │ evolved_tools.json│
                                    │  Persistent Memory│
                                    └──────────────────┘
```

---

## Files

### `app.py` — Terminal Bot & AI Agent Client

| Aspect | Detail |
|--------|--------|
| **Role** | User-facing terminal REPL |
| **LLM** | Azure OpenAI GPT-4o via LangChain |
| **Tools** | 23+ built-in `StructuredTool` instances |
| **Pydantic** | Uses `pydantic.v1` for LangChain compatibility |

**Key functions:**

| Function | Purpose |
|----------|---------|
| `main()` | REPL loop — reads input, invokes agent |
| `call_mcp_tool()` | HTTP POST to MCP `/execute` endpoint |
| `refresh_tools()` | Hot-loads new evolved tools into the agent |
| `create_pydantic_model_from_schema()` | Builds Pydantic v1 models from JSON `inputSchema` |
| `load_dynamic_tools_on_startup()` | Loads persisted evolved tools at boot |
| `create_dynamic_tool_wrapper()` | Creates callable wrapper for evolved tools |

---

### `mcp_server.py` — MCP Server & Self-Evolution Engine

| Aspect | Detail |
|--------|--------|
| **Role** | Backend tool server & evolution engine |
| **Framework** | FastAPI on Uvicorn (port 8099) |
| **Static tools** | 23 built-in tools |
| **Dynamic tools** | Unlimited, auto-generated from API catalog |
| **API Catalog** | 7 categories, 30+ Databricks endpoints |

**Key functions:**

| Function | Purpose |
|----------|---------|
| `execute_sql()` | SQL Warehouse first (Unity Catalog), cluster fallback |
| `execute_sql_on_cluster()` | Legacy cluster SQL via Commands API 1.2 |
| `auto_generate_tool()` | Creates tool definition from API catalog entry |
| `execute_dynamic_tool()` | Runs any evolved tool against Databricks REST API |
| `save_evolved_tools()` | Persists `DYNAMIC_TOOLS` dict to JSON |
| `load_evolved_tools()` | Restores tools from JSON on startup |
| `list_databases()` | Lists catalogs + schemas (Unity Catalog aware) |
| `list_tables()` | Lists tables, supports `catalog.schema` format |

**REST Endpoints:**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/tools` | List all available tools (static + dynamic) |
| POST | `/execute` | Execute any tool by name |
| GET | `/health` | Health check with Databricks connectivity |
| POST | `/evolve/discover` | Auto-discover and register new tools |
| GET | `/evolve/tools` | List dynamically evolved tools |
| POST | `/evolve/add_custom` | Add a custom tool definition |
| POST | `/evolve/reload` | Reload tools from JSON file |
| DELETE | `/evolve/clear` | Clear all evolved tools |

---

### `.env` — Configuration & Credentials

| Variable | Purpose |
|----------|---------|
| `AZURE_OPENAI_API_KEY` | Azure OpenAI authentication |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | GPT-4o deployment |
| `AZURE_OPENAI_API_VERSION` | API version |
| `DATABRICKS_HOST` | Workspace URL |
| `DATABRICKS_TOKEN` | Personal access token |
| `DATABRICKS_CLUSTER_ID` | Default cluster (fallback SQL) |
| `DATABRICKS_WAREHOUSE_ID` | SQL Warehouse for Unity Catalog |
| `MCP_DATABRICKS_URL` | MCP server address (localhost:8099) |

---

### `evolved_tools.json` — Persistent Tool Memory

Auto-generated file that stores all dynamically discovered tools. Survives server restarts.

```json
{
  "tools": {
    "cluster_create": { "name": "...", "api_path": "...", "inputSchema": {...} },
    "dbfs_list":      { "name": "...", "api_path": "...", "inputSchema": {...} }
  },
  "last_updated": "2026-02-16T...",
  "count": 30
}
```

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│  PRESENTATION    Terminal REPL (app.py main loop)           │
├─────────────────────────────────────────────────────────────┤
│  AI AGENT        LangChain AgentExecutor + Azure OpenAI     │
│                  GPT-4o · ConversationBufferMemory          │
│                  StructuredTool · Pydantic v1 schemas       │
├─────────────────────────────────────────────────────────────┤
│  MCP SERVER      FastAPI :8099                              │
│                  /tools · /execute · /health                │
│                  /evolve/discover · /evolve/tools            │
├─────────────────────────────────────────────────────────────┤
│  DATABRICKS      SQL Statements API (warehouse)             │
│                  Commands API 1.2 (cluster fallback)        │
│                  REST API 2.0/2.1 (clusters, jobs, etc.)    │
├─────────────────────────────────────────────────────────────┤
│  PERSISTENCE     evolved_tools.json · .env · chat memory    │
└─────────────────────────────────────────────────────────────┘
```

---

## Request Flow

Example: *"Show me tables in dbrmitko.default"*

| Step | Component | Action |
|------|-----------|--------|
| 1 | **User** | Types query in terminal |
| 2 | **LangChain Agent** | GPT-4o selects `list_tables` tool, sets `schema="dbrmitko.default"` |
| 3 | **app.py** | `call_mcp_tool("list_tables", {"schema": "dbrmitko.default"})` → HTTP POST to MCP |
| 4 | **mcp_server.py** | Builds SQL: `SHOW TABLES IN dbrmitko.default` (detects `.` → Unity Catalog) |
| 5 | **Databricks** | SQL Warehouse executes query via `/api/2.0/sql/statements` |
| 6 | **mcp_server.py** | Parses response: `manifest.schema.columns` + `result.data_array` |
| 7 | **LangChain Agent** | GPT-4o formats: *"The schema contains 1 table: hr_attendance_dummy"* |

---

## SQL Execution Strategy

```
execute_sql(query)
    │
    ├── DATABRICKS_WAREHOUSE_ID set?
    │       │
    │       ├── YES ──▶ POST /api/2.0/sql/statements
    │       │              warehouse_id = adc04bc39671c64d
    │       │              ├── SUCCEEDED → parse manifest + data_array
    │       │              └── FAILED → return error
    │       │
    │       └── NO ───▶ execute_sql_on_cluster()
    │                      POST /api/1.2/contexts/create
    │                      POST /api/1.2/commands/execute
    │                      GET  /api/1.2/commands/status (poll)
    │
    └── Returns: { status, columns, rows, total_rows }
```

---

## Self-Evolution System

When the agent encounters an unknown capability, it calls `evolve_discover` to scan the API catalog and auto-generate new tools.

### API Discovery Catalog

| Category | Endpoints | API Path |
|----------|-----------|----------|
| **Clusters** | create, edit, resize, restart, delete, list_node_types, spark_versions | `/api/2.0/clusters/*` |
| **Workspace** | import, export, delete, mkdirs, get_status | `/api/2.0/workspace/*` |
| **DBFS** | list, read, delete, mkdirs | `/api/2.0/dbfs/*` |
| **Secrets** | list_scopes, list_secrets | `/api/2.0/secrets/*` |
| **Repos** | list, get, update | `/api/2.0/repos/*` |
| **Pipelines** | list, get, start, stop | `/api/2.0/pipelines/*` |
| **MLflow** | list_experiments, list_models, search_runs | `/api/2.0/mlflow/*` |
| **Serving** | list_endpoints, get_endpoint | `/api/2.0/serving-endpoints/*` |

### Evolution Flow

```
User asks: "Create a cluster"
    │
    ▼
Agent: No cluster_create tool → calls evolve_discover
    │
    ▼
MCP Server: Scans DATABRICKS_API_CATALOG
    ├── Generates cluster_create tool definition
    ├── Registers in DYNAMIC_TOOLS dict
    └── Saves to evolved_tools.json
    │
    ▼
Agent: refresh_tools() loads new tools into LangChain
    │
    ▼
Agent: Calls cluster_create with user's parameters
    │
    ▼
MCP Server: execute_dynamic_tool() → POST /api/2.0/clusters/create
```

---

## Pydantic v1/v2 Bridge

LangChain internally uses **Pydantic v1** for tool argument schemas, but the project installs **Pydantic v2**.

```python
# app.py - compatibility imports
from pydantic.v1 import BaseModel, Field, create_model

def create_pydantic_model_from_schema(tool_name, input_schema):
    """JSON inputSchema → Pydantic v1 model for LangChain StructuredTool"""
    # Maps: "string"→str, "integer"→int, "boolean"→bool, etc.
    # Required fields get Field(description=...)
    # Optional fields get Field(default=..., description=...)
    return create_model(ModelName, __base__=BaseModel, **fields)
```

This allows each evolved tool's `inputSchema` (JSON) to become a typed Pydantic model that LangChain's `StructuredTool` can validate at runtime.

---

## Built-in Tools (23)

| # | Tool | Description |
|---|------|-------------|
| 1 | `execute_sql` | Execute SQL query on Databricks |
| 2 | `list_databases` | List all databases/schemas |
| 3 | `list_tables` | List tables in a schema |
| 4 | `get_table_schema` | Get columns of a table |
| 5 | `list_clusters` | List all clusters |
| 6 | `get_cluster_status` | Get cluster state |
| 7 | `start_cluster` | Start a stopped cluster |
| 8 | `stop_cluster` | Stop a running cluster |
| 9 | `list_jobs` | List all jobs |
| 10 | `run_job` | Trigger a job run |
| 11 | `get_job_run_status` | Check job run status |
| 12 | `cancel_job_run` | Cancel a running job |
| 13 | `list_notebooks` | List items in workspace path |
| 14 | `find_notebooks` | Recursively find notebooks |
| 15 | `run_notebook` | Run a notebook |
| 16 | `get_table_preview` | Preview first N rows |
| 17 | `get_table_stats` | Get row count and size |
| 18 | `list_catalogs` | List Unity Catalog catalogs |
| 19 | `search_tables` | Search tables by pattern |
| 20 | `get_cluster_logs` | Get cluster event logs |
| 21 | `list_workspace_folders` | List workspace directories |
| 22 | `evolve_discover` | Trigger self-evolution |
| 23 | `evolve_list` | List evolved tools |

---

## Technology Stack

| Technology | Role |
|-----------|------|
| Python 3.9+ | Runtime |
| FastAPI | MCP Server framework |
| Uvicorn | ASGI server |
| LangChain | Agent framework |
| Azure OpenAI | GPT-4o LLM |
| Pydantic v1/v2 | Schema validation |
| HTTPX | Async HTTP client |
| python-dotenv | Environment config |
| Databricks API | Data platform |
| Unity Catalog | Data governance |

---

## How to Run

```bash
# 1. Activate virtual environment
cd databricks
source .venv/bin/activate

# 2. Start MCP server (terminal 1)
python mcp_server.py

# 3. Start terminal bot (terminal 2)
python app.py
```

---

*Self-Evolving Databricks AI Agent — Architecture Documentation — 2026*
