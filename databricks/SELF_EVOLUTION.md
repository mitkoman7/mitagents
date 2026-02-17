# Self-Evolution System — How It Works

This document explains how the Databricks AI Agent **automatically discovers, creates, and persists new tools** at runtime without any code changes.

---

## The Problem

A traditional AI agent has a **fixed set of tools** hardcoded at build time. When a user asks for something the agent can't do, it simply says *"I don't have that capability"*.

```
User: "Create a new cluster"
Agent: "Sorry, I don't have a tool for creating clusters."  ← dead end
```

Our agent **never hits a dead end**. Instead, it evolves.

---

## The Solution: 3-Phase Self-Evolution

```
Phase 1: DETECT           Phase 2: GENERATE           Phase 3: PERSIST
─────────────────        ──────────────────          ─────────────────
User asks for            Agent scans API             New tool saved to
something unknown   ──▶  catalog & builds    ──▶    JSON file & loaded
                         tool definition             into live agent

  "Create a               cluster_create             evolved_tools.json
   cluster"                tool generated             updated on disk
```

---

## Phase 1: Detection — "I Don't Have This Tool"

When the user asks for something, GPT-4o checks its available tools. If no tool matches, the agent's system prompt instructs it to **immediately call `evolve_discover`** instead of giving up.

### The Trigger Rule (from `app.py` system prompt)

```
MANDATORY SELF-EVOLUTION RULE:
If the user asks for ANY of these, you MUST call evolve_discover FIRST:
- Create/edit/resize/restart/delete cluster
- DBFS files (list, read, write, delete)
- MLflow (experiments, models, runs)
- Git repos
- Serving endpoints
- Pipelines/DLT
- Secrets
- Workspace import/export
```

### What Happens Internally

```
User: "Create me a new Spark cluster"
                │
                ▼
GPT-4o thinks: "I need cluster_create but I don't have it"
                │
                ▼
GPT-4o calls: evolve_discover()    ← automatic, no user action needed
```

---

## Phase 2: Generation — Building Tools from the API Catalog

### The API Catalog

Inside `mcp_server.py`, there is a dictionary called `DATABRICKS_API_CATALOG` that maps **every known Databricks API endpoint** to its metadata:

```python
DATABRICKS_API_CATALOG = {
    "cluster": {
        "create": {
            "method": "POST",
            "path": "/api/2.0/clusters/create",
            "description": "Create a new Databricks cluster",
            "params": {
                "cluster_name": {"type": "string", "description": "Name for the new cluster"},
                "spark_version": {"type": "string", "default": "13.3.x-scala2.12"},
                "node_type_id":  {"type": "string", "default": "Standard_DS3_v2"},
                "num_workers":   {"type": "integer", "default": 1}
            }
        },
        "restart": {
            "method": "POST",
            "path": "/api/2.0/clusters/restart",
            "params": {"cluster_id": {"type": "string"}}
        },
        ...
    },
    "dbfs": { ... },
    "workspace": { ... },
    "mlflow": { ... },
    "pipelines": { ... },
    "repos": { ... },
    "secrets": { ... },
    "serving": { ... }
}
```

This catalog contains **7 categories** and **30+ endpoints**. It is the agent's "genome" — the full list of capabilities it *can* evolve into.

### The auto_generate_tool() Function

When `evolve_discover` is called, it loops through every entry in the catalog and calls `auto_generate_tool()` for each one:

```python
async def auto_generate_tool(category, action, api_info):
    tool_name = f"{category}_{action}"        # e.g. "cluster_create"

    # 1. Extract path parameters like {repo_id} from URL
    path_params = re.findall(r'\{(\w+)\}', api_info["path"])

    # 2. Build inputSchema from params + path params
    properties = {}
    required = []
    for param in path_params:
        properties[param] = {"type": "string", "description": "..."}
        required.append(param)
    for name, definition in api_info.get("params", {}).items():
        properties[name] = definition
        if "default" not in definition:
            required.append(name)

    # 3. Create full tool definition
    tool_def = {
        "name": tool_name,
        "description": api_info["description"],
        "api_path": api_info["path"],           # e.g. "/api/2.0/clusters/create"
        "api_method": api_info["method"],        # e.g. "POST"
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required
        },
        "auto_generated": True
    }

    # 4. Register in memory
    DYNAMIC_TOOLS[tool_name] = tool_def

    # 5. Persist to disk
    save_evolved_tools()

    return tool_def
```

### What Gets Generated

For `cluster_create`, the generated tool looks like:

```json
{
  "name": "cluster_create",
  "description": "Create a new Databricks cluster",
  "api_path": "/api/2.0/clusters/create",
  "api_method": "POST",
  "inputSchema": {
    "type": "object",
    "properties": {
      "cluster_name": {"type": "string", "description": "Name for the new cluster"},
      "spark_version": {"type": "string", "description": "Spark version", "default": "13.3.x-scala2.12"},
      "node_type_id":  {"type": "string", "description": "Node type", "default": "Standard_DS3_v2"},
      "num_workers":   {"type": "integer", "description": "Number of worker nodes", "default": 1}
    },
    "required": ["cluster_name"]
  },
  "auto_generated": true
}
```

---

## Phase 3: Persistence — Surviving Restarts

### Saving to Disk

Every time a new tool is generated, `save_evolved_tools()` writes the entire `DYNAMIC_TOOLS` dictionary to `evolved_tools.json`:

```python
def save_evolved_tools():
    with open("evolved_tools.json", 'w') as f:
        json.dump({
            "tools": DYNAMIC_TOOLS,
            "last_updated": datetime.now().isoformat(),
            "count": len(DYNAMIC_TOOLS)
        }, f, indent=2)
```

### Loading on Startup

When the MCP server starts, it immediately loads any previously saved tools:

```python
def load_evolved_tools():
    if EVOLVED_TOOLS_FILE.exists():
        with open(EVOLVED_TOOLS_FILE, 'r') as f:
            data = json.load(f)
            DYNAMIC_TOOLS = data.get("tools", {})
```

This means the agent **never forgets** what it learned. Kill the server, restart it — all 30 evolved tools are back instantly.

### The File Structure

```json
{
  "tools": {
    "cluster_create":       { "name": "...", "api_path": "...", "inputSchema": {...} },
    "cluster_restart":      { "name": "...", "api_path": "...", "inputSchema": {...} },
    "dbfs_list":            { "name": "...", "api_path": "...", "inputSchema": {...} },
    "workspace_import":     { "name": "...", "api_path": "...", "inputSchema": {...} },
    "mlflow_list_models":   { "name": "...", "api_path": "...", "inputSchema": {...} },
    "...": "... 25 more tools ..."
  },
  "last_updated": "2026-02-16T14:30:00.000000",
  "count": 30
}
```

---

## How Evolved Tools Execute

Once a tool exists in `DYNAMIC_TOOLS`, the `execute_dynamic_tool()` function handles running it against the real Databricks API:

```
Agent calls: cluster_create(cluster_name="my-cluster", num_workers=2)
                │
                ▼
execute_dynamic_tool("cluster_create", {"cluster_name": "my-cluster", "num_workers": 2})
                │
                ├── 1. Look up tool_def in DYNAMIC_TOOLS
                │       api_path = "/api/2.0/clusters/create"
                │       method   = "POST"
                │
                ├── 2. Separate path params from body params
                │       path_params: {}  (no {placeholders} in this URL)
                │       body_params: {"cluster_name": "my-cluster", "num_workers": 2}
                │
                ├── 3. Build full URL
                │       url = "https://adb-xxx.azuredatabricks.net/api/2.0/clusters/create"
                │
                ├── 4. Send HTTP request
                │       POST url with JSON body + Bearer token
                │
                └── 5. Return response
                        {"cluster_id": "0217-123456-abcdef", "message": "Cluster created!"}
```

### Path Parameter Handling

Some APIs have URL parameters like `/api/2.0/repos/{repo_id}`. The function handles this automatically:

```
Tool: repos_get(repo_id="12345")
                │
                ▼
api_path = "/api/2.0/repos/{repo_id}"
                │
                ▼
Replace: "/api/2.0/repos/12345"     ← {repo_id} → actual value
```

---

## Hot-Loading into the Live Agent

After evolution happens on the MCP server, the `app.py` client needs to know about the new tools. This happens via `refresh_tools()`:

```
MCP Server evolves 30 new tools
                │
                ▼
app.py calls refresh_tools()
                │
                ├── 1. GET /evolve/tools  → fetches all dynamic tool definitions
                │
                ├── 2. For each new tool:
                │       ├── Create wrapper function (HTTP caller)
                │       ├── Build Pydantic v1 model from inputSchema
                │       └── Create StructuredTool instance
                │
                ├── 3. Add to tools list
                │
                └── 4. Rebuild LangChain agent with new tools
                        agent = create_openai_functions_agent(llm, tools, prompt)
                        agent_executor = AgentExecutor(agent=agent, tools=tools, ...)
```

### The Pydantic Bridge

LangChain requires each tool to have a Pydantic model for argument validation. Since evolved tools only have a JSON `inputSchema`, we dynamically create Pydantic models:

```
JSON inputSchema                         Pydantic v1 Model
─────────────────                        ─────────────────
{                                        class ClusterCreateArgs(BaseModel):
  "properties": {                            cluster_name: str
    "cluster_name": {                        spark_version: Optional[str] = "13.3.x"
      "type": "string"                      node_type_id: Optional[str] = "Standard_DS3_v2"
    },                             ──▶      num_workers: Optional[int] = 1
    "spark_version": {
      "type": "string",
      "default": "13.3.x"
    }
  },
  "required": ["cluster_name"]
}
```

---

## Complete Flow — End to End

```
 ┌─────────────────────────────────────────────────────────────────────┐
 │  User: "Create me a cluster called analytics-prod with 4 workers"  │
 └──────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │  GPT-4o: "I don't have cluster_create... calling evolve"    │
 │  → calls evolve_discover()                                  │
 └──────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │  MCP Server: Scans DATABRICKS_API_CATALOG                   │
 │  → generates 30 tools (cluster_create, dbfs_list, etc.)     │
 │  → saves to evolved_tools.json                              │
 └──────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │  app.py: refresh_tools()                                    │
 │  → loads 30 new StructuredTool instances                    │
 │  → rebuilds LangChain agent                                 │
 └──────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │  GPT-4o: Now I have cluster_create!                         │
 │  → calls cluster_create(                                    │
 │      cluster_name="analytics-prod",                         │
 │      num_workers=4                                          │
 │    )                                                        │
 └──────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │  MCP Server: execute_dynamic_tool()                         │
 │  → POST https://adb-xxx.net/api/2.0/clusters/create         │
 │  → body: {"cluster_name":"analytics-prod","num_workers":4}  │
 └──────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │  Databricks: Cluster created!                               │
 │  → returns cluster_id: "0217-143022-xyz123"                 │
 └──────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │  Agent: "Cluster 'analytics-prod' created successfully!     │
 │          Cluster ID: 0217-143022-xyz123                     │
 │          Workers: 4, Spark: 13.3.x-scala2.12"              │
 └─────────────────────────────────────────────────────────────┘
```

---

## Missing Capability Logging

If a user asks for something that's not even in the API catalog, the system logs it for future expansion:

```python
MISSING_CAPABILITY_LOG.append({
    "capability": "some_unknown_action",
    "context": "user wanted to do X",
    "timestamp": "2026-02-16T..."
})
```

You can check what's been requested but not available:

```
GET /evolve/missing    → shows all logged gaps
```

This lets you **extend the API catalog** with new entries over time.

---

## Custom Tool Addition

Beyond auto-discovery, you can manually add tools:

```
POST /evolve/add_custom
{
    "name": "my_custom_tool",
    "description": "Does something special",
    "api_path": "/api/2.0/some/endpoint",
    "api_method": "POST",
    "input_schema": {
        "type": "object",
        "properties": {
            "param1": {"type": "string"}
        },
        "required": ["param1"]
    }
}
```

Custom tools are also persisted to `evolved_tools.json` and survive restarts.

---

## Management Commands

| Command | What It Does |
|---------|-------------|
| `POST /evolve/discover` | Scan catalog, generate all missing tools |
| `GET /evolve/tools` | List all currently evolved tools |
| `POST /evolve/add_custom` | Add a hand-crafted tool |
| `POST /evolve/reload` | Reload tools from JSON file |
| `DELETE /evolve/clear` | Wipe all evolved tools (memory + disk) |
| `GET /evolve/missing` | See what users asked for but wasn't available |

In the terminal bot, the user can also type:

| Command | Effect |
|---------|--------|
| `evolve` | Triggers discovery + loads new tools |
| `tools` | Shows all tools (built-in + evolved) |

---

## Summary

| Concept | Implementation |
|---------|---------------|
| **Knowledge base** | `DATABRICKS_API_CATALOG` dict in `mcp_server.py` |
| **Tool generation** | `auto_generate_tool()` — builds definition from catalog |
| **Tool storage** | `DYNAMIC_TOOLS` dict (in-memory) + `evolved_tools.json` (disk) |
| **Tool execution** | `execute_dynamic_tool()` — HTTP to Databricks API |
| **Client loading** | `refresh_tools()` — builds Pydantic models + StructuredTools |
| **Persistence** | `save_evolved_tools()` / `load_evolved_tools()` — JSON read/write |
| **Trigger** | GPT-4o system prompt mandates calling `evolve_discover` on unknown requests |

The agent starts with 23 built-in tools. After one `evolve_discover` call, it has **53 tools**. After a restart, it still has 53 tools. It never forgets, and it never says "I can't do that."

---

*Self-Evolving Databricks AI Agent — Evolution Deep Dive — 2026*
