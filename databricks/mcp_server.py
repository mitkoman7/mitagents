"""
Databricks MCP Server - Data Analytics & ML Platform
Execute SQL queries, run notebooks, manage clusters, and access Delta Lake
Self-evolving: Can dynamically discover and add new Databricks API capabilities
"""

from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import json
import os
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path

load_dotenv()

app = FastAPI(title="Databricks MCP Server - Self-Evolving")

# File path for persisting evolved tools
EVOLVED_TOOLS_FILE = Path(__file__).parent / "evolved_tools.json"

# Dynamic tool registry for self-evolution
DYNAMIC_TOOLS: Dict[str, Dict[str, Any]] = {}
TOOL_EXECUTION_LOG: List[Dict[str, Any]] = []
MISSING_CAPABILITY_LOG: List[Dict[str, Any]] = []

def save_evolved_tools():
    """Save evolved tools to JSON file"""
    try:
        with open(EVOLVED_TOOLS_FILE, 'w') as f:
            json.dump({
                "tools": DYNAMIC_TOOLS,
                "last_updated": datetime.now().isoformat(),
                "count": len(DYNAMIC_TOOLS)
            }, f, indent=2)
        print(f"[Evolution] Saved {len(DYNAMIC_TOOLS)} tools to {EVOLVED_TOOLS_FILE}")
    except Exception as e:
        print(f"[Evolution] Error saving tools: {e}")

def load_evolved_tools():
    """Load evolved tools from JSON file on startup"""
    global DYNAMIC_TOOLS
    try:
        if EVOLVED_TOOLS_FILE.exists():
            with open(EVOLVED_TOOLS_FILE, 'r') as f:
                data = json.load(f)
                DYNAMIC_TOOLS = data.get("tools", {})
                print(f"[Evolution] Loaded {len(DYNAMIC_TOOLS)} tools from {EVOLVED_TOOLS_FILE}")
                print(f"[Evolution] Last updated: {data.get('last_updated', 'unknown')}")
                return len(DYNAMIC_TOOLS)
    except Exception as e:
        print(f"[Evolution] Error loading tools: {e}")
    return 0

# Load tools on module import
load_evolved_tools()

# Databricks API configuration
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_CLUSTER_ID = os.getenv("DATABRICKS_CLUSTER_ID", "")

class ToolRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]

class Tool(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]

def get_headers():
    """Get authorization headers for Databricks API"""
    return {
        "Authorization": f"Bearer {DATABRICKS_TOKEN}",
        "Content-Type": "application/json"
    }

@app.get("/")
async def root():
    return {
        "message": "Databricks MCP Server",
        "endpoints": {"/tools": "List tools", "/execute": "Execute tool", "/health": "Health check"}
    }

@app.get("/tools")
async def list_tools() -> List[Tool]:
    """List all available tools (static + dynamically evolved)"""
    static_tools = [
        Tool(
            name="execute_sql",
            description="Execute SQL query on Databricks",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SQL query to execute"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="list_databases",
            description="List all databases/schemas in Databricks",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="list_tables",
            description="List all tables in a database/schema",
            inputSchema={
                "type": "object",
                "properties": {
                    "schema": {"type": "string", "description": "Schema name", "default": "default"}
                },
                "required": []
            }
        ),
        Tool(
            name="get_table_schema",
            description="Get schema/columns of a table",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {"type": "string", "description": "Table name"},
                    "schema": {"type": "string", "description": "Schema name", "default": "default"}
                },
                "required": ["table_name"]
            }
        ),
        Tool(
            name="list_clusters",
            description="List all available Databricks clusters",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="get_cluster_status",
            description="Get status of a cluster",
            inputSchema={
                "type": "object",
                "properties": {
                    "cluster_id": {"type": "string", "description": "Cluster ID"}
                },
                "required": []
            }
        ),
        Tool(
            name="start_cluster",
            description="Start a stopped cluster",
            inputSchema={
                "type": "object",
                "properties": {
                    "cluster_id": {"type": "string", "description": "Cluster ID"}
                },
                "required": []
            }
        ),
        Tool(
            name="list_jobs",
            description="List all Databricks jobs",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Number of jobs", "default": 25}
                },
                "required": []
            }
        ),
        Tool(
            name="run_job",
            description="Trigger a job run",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_id": {"type": "integer", "description": "Job ID to run"}
                },
                "required": ["job_id"]
            }
        ),
        Tool(
            name="run_notebook",
            description="Run a Databricks notebook",
            inputSchema={
                "type": "object",
                "properties": {
                    "notebook_path": {"type": "string", "description": "Path to notebook"}
                },
                "required": ["notebook_path"]
            }
        ),
        Tool(
            name="stop_cluster",
            description="Stop a running cluster",
            inputSchema={
                "type": "object",
                "properties": {
                    "cluster_id": {"type": "string", "description": "Cluster ID to stop"}
                },
                "required": []
            }
        ),
        Tool(
            name="get_job_run_status",
            description="Get status of a job run",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "integer", "description": "Run ID to check"}
                },
                "required": ["run_id"]
            }
        ),
        Tool(
            name="cancel_job_run",
            description="Cancel a running job",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "integer", "description": "Run ID to cancel"}
                },
                "required": ["run_id"]
            }
        ),
        Tool(
            name="list_notebooks",
            description="List notebooks in a workspace path",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Workspace path", "default": "/"}
                },
                "required": []
            }
        ),
        Tool(
            name="get_table_preview",
            description="Preview first N rows of a table",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {"type": "string", "description": "Table name"},
                    "limit": {"type": "integer", "description": "Number of rows", "default": 10}
                },
                "required": ["table_name"]
            }
        ),
        Tool(
            name="get_table_stats",
            description="Get table statistics (row count, size)",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {"type": "string", "description": "Table name"}
                },
                "required": ["table_name"]
            }
        ),
        Tool(
            name="list_catalogs",
            description="List all Unity Catalog catalogs",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="search_tables",
            description="Search for tables by name pattern",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Search pattern (e.g., 'sales*')"}
                },
                "required": ["pattern"]
            }
        ),
        Tool(
            name="get_cluster_logs",
            description="Get recent logs from a cluster",
            inputSchema={
                "type": "object",
                "properties": {
                    "cluster_id": {"type": "string", "description": "Cluster ID"}
                },
                "required": []
            }
        ),
        Tool(
            name="list_workspace_folders",
            description="List folders/directories in a workspace path",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Workspace path", "default": "/"}
                },
                "required": []
            }
        ),
        Tool(
            name="find_notebooks",
            description="Find all notebooks in a path (searches recursively)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Workspace path to search", "default": "/"}
                },
                "required": []
            }
        ),
        # Evolution tools
        Tool(
            name="evolve_discover",
            description="Discover and add new Databricks API capabilities. Use this to evolve the agent with new tools.",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="evolve_list",
            description="List all dynamically evolved tools",
            inputSchema={"type": "object", "properties": {}, "required": []}
        )
    ]

    # Add dynamically evolved tools
    for tool_name, tool_def in DYNAMIC_TOOLS.items():
        static_tools.append(Tool(
            name=tool_name,
            description=tool_def["description"] + " [AUTO-EVOLVED]",
            inputSchema=tool_def["inputSchema"]
        ))

    return static_tools

async def execute_sql_on_cluster(query: str, cluster_id: str = None):
    """Execute SQL on a cluster using context API"""
    if not cluster_id:
        cluster_id = DATABRICKS_CLUSTER_ID

    if not cluster_id:
        return {"error": "No cluster configured"}

    try:
        # Create execution context
        context_url = f"{DATABRICKS_HOST}/api/1.2/contexts/create"
        context_payload = {"clusterId": cluster_id, "language": "sql"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            context_response = await client.post(context_url, headers=get_headers(), json=context_payload)
            context_response.raise_for_status()
            context_id = context_response.json().get("id")

            # Execute command
            command_url = f"{DATABRICKS_HOST}/api/1.2/commands/execute"
            command_payload = {
                "clusterId": cluster_id,
                "contextId": context_id,
                "language": "sql",
                "command": query
            }

            command_response = await client.post(command_url, headers=get_headers(), json=command_payload)
            command_response.raise_for_status()
            command_id = command_response.json().get("id")

            # Poll for results
            status_url = f"{DATABRICKS_HOST}/api/1.2/commands/status"
            for _ in range(30):
                await asyncio.sleep(1)
                status_response = await client.get(
                    f"{status_url}?clusterId={cluster_id}&contextId={context_id}&commandId={command_id}",
                    headers=get_headers()
                )
                status_data = status_response.json()

                if status_data.get("status") == "Finished":
                    results = status_data.get("results", {})
                    data = results.get("data", [])
                    schema = results.get("schema", [])
                    columns = [col.get("name", f"col_{i}") for i, col in enumerate(schema)]

                    return {
                        "status": "success",
                        "columns": columns,
                        "rows": data if data else [],
                        "total_rows": len(data) if data else 0
                    }
                elif status_data.get("status") in ["Error", "Cancelled"]:
                    return {"error": status_data.get("results", {}).get("cause", "Command failed")}

            return {"error": "Command timed out"}

    except Exception as e:
        return {"error": str(e)}

async def execute_sql(query: str):
    """Execute SQL query - prefers SQL Warehouse for Unity Catalog support"""
    if not DATABRICKS_HOST or not DATABRICKS_TOKEN:
        return {"error": "Databricks credentials not configured"}

    warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID", "")

    if warehouse_id:
        try:
            url = f"{DATABRICKS_HOST}/api/2.0/sql/statements"
            payload = {
                "statement": query,
                "warehouse_id": warehouse_id,
                "wait_timeout": "30s"
            }
            print(f"[SQL] Executing via warehouse {warehouse_id}: {query}")

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=get_headers(), json=payload)
                data = response.json()
                print(f"[SQL] Response status: {response.status_code}, state: {data.get('status', {}).get('state')}")

                if response.status_code == 200:
                    state = data.get("status", {}).get("state")

                    if state == "SUCCEEDED":
                        # Columns come from manifest.schema.columns
                        manifest = data.get("manifest", {})
                        schema = manifest.get("schema", {})
                        columns = [col["name"] for col in schema.get("columns", [])]

                        # Rows come from result.data_array
                        result = data.get("result", {})
                        rows = result.get("data_array", [])

                        print(f"[SQL] Success: {len(columns)} columns, {len(rows)} rows")
                        return {
                            "status": "success",
                            "columns": columns,
                            "rows": rows[:100],
                            "total_rows": len(rows)
                        }
                    elif state == "FAILED":
                        error_msg = data.get("status", {}).get("error", {}).get("message", "SQL execution failed")
                        print(f"[SQL] Warehouse error: {error_msg}")
                        return {"error": error_msg}
                else:
                    print(f"[SQL] Warehouse HTTP error: {response.status_code} - {response.text[:200]}")

        except Exception as e:
            print(f"[SQL] Warehouse exception: {e}")

    # Fall back to cluster only if warehouse is not configured
    print(f"[SQL] Falling back to cluster execution")
    return await execute_sql_on_cluster(query)

async def list_databases():
    """List databases/schemas - supports Unity Catalog"""
    # First try to list catalogs (Unity Catalog)
    catalogs_result = await execute_sql("SHOW CATALOGS")

    all_schemas = []
    catalogs = []

    if "error" not in catalogs_result:
        for row in catalogs_result.get("rows", []):
            catalog = row[0] if isinstance(row, list) else row
            if catalog and not catalog.startswith("__"):  # Skip internal catalogs
                catalogs.append(catalog)
                # Get schemas in each catalog
                schemas_result = await execute_sql(f"SHOW SCHEMAS IN {catalog}")
                if "error" not in schemas_result:
                    for schema_row in schemas_result.get("rows", []):
                        schema = schema_row[0] if isinstance(schema_row, list) else schema_row
                        if schema and schema not in ["information_schema"]:
                            all_schemas.append(f"{catalog}.{schema}")

    # Also try legacy SHOW DATABASES
    legacy_result = await execute_sql("SHOW DATABASES")
    if "error" not in legacy_result:
        for row in legacy_result.get("rows", []):
            db = row[0] if isinstance(row, list) else row
            if db and db not in all_schemas:
                all_schemas.append(db)

    return {
        "catalogs": catalogs,
        "schemas": all_schemas,
        "count": len(all_schemas),
        "hint": "Use 'catalog.schema' format for Unity Catalog tables"
    }

async def list_tables(schema: str = "default"):
    """List tables in schema - supports Unity Catalog format (catalog.schema)"""
    # Handle Unity Catalog format: catalog.schema
    if "." in schema:
        query = f"SHOW TABLES IN {schema}"
    else:
        # Try with default catalog first
        query = f"SHOW TABLES IN {schema}"

    result = await execute_sql(query)

    if "error" in result:
        return result

    tables = []
    for row in result.get("rows", []):
        if isinstance(row, list):
            # Unity Catalog returns [database, tableName, isTemporary]
            if len(row) > 1:
                table_name = row[1]
                tables.append(table_name)
            elif len(row) == 1:
                tables.append(row[0])

    return {"schema": schema, "tables": tables, "count": len(tables)}

async def get_table_schema(table_name: str, schema: str = "default"):
    """Get table schema"""
    query = f"DESCRIBE TABLE {schema}.{table_name}"
    result = await execute_sql(query)

    if "error" in result:
        return result

    columns = []
    for row in result.get("rows", []):
        if row[0] and not row[0].startswith("#"):
            columns.append({"name": row[0], "type": row[1]})

    return {"table": table_name, "columns": columns, "count": len(columns)}

async def list_clusters():
    """List clusters"""
    if not DATABRICKS_HOST or not DATABRICKS_TOKEN:
        return {"error": "Databricks credentials not configured"}

    try:
        url = f"{DATABRICKS_HOST}/api/2.0/clusters/list"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=get_headers())
            response.raise_for_status()
            data = response.json()

        clusters = []
        for cluster in data.get("clusters", []):
            clusters.append({
                "cluster_id": cluster.get("cluster_id"),
                "cluster_name": cluster.get("cluster_name"),
                "state": cluster.get("state")
            })

        return {"clusters": clusters, "count": len(clusters)}

    except Exception as e:
        return {"error": str(e)}

async def get_cluster_status(cluster_id: str = ""):
    """Get cluster status"""
    cluster_id = cluster_id or DATABRICKS_CLUSTER_ID
    if not cluster_id:
        return {"error": "No cluster_id provided"}

    try:
        url = f"{DATABRICKS_HOST}/api/2.0/clusters/get"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=get_headers(), params={"cluster_id": cluster_id})
            response.raise_for_status()
            data = response.json()

        return {
            "cluster_id": data.get("cluster_id"),
            "cluster_name": data.get("cluster_name"),
            "state": data.get("state"),
            "state_message": data.get("state_message", "")
        }

    except Exception as e:
        return {"error": str(e)}

async def start_cluster(cluster_id: str = ""):
    """Start cluster"""
    cluster_id = cluster_id or DATABRICKS_CLUSTER_ID
    if not cluster_id:
        return {"error": "No cluster_id provided"}

    try:
        url = f"{DATABRICKS_HOST}/api/2.0/clusters/start"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=get_headers(), json={"cluster_id": cluster_id})
            response.raise_for_status()

        return {"status": "starting", "cluster_id": cluster_id}

    except Exception as e:
        return {"error": str(e)}

async def list_jobs(limit: int = 25):
    """List jobs"""
    try:
        url = f"{DATABRICKS_HOST}/api/2.1/jobs/list"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=get_headers(), params={"limit": limit})
            response.raise_for_status()
            data = response.json()

        jobs = []
        for job in data.get("jobs", []):
            jobs.append({
                "job_id": job.get("job_id"),
                "name": job.get("settings", {}).get("name", "Unnamed")
            })

        return {"jobs": jobs, "count": len(jobs)}

    except Exception as e:
        return {"error": str(e)}

async def run_job(job_id: int):
    """Run job"""
    try:
        url = f"{DATABRICKS_HOST}/api/2.1/jobs/run-now"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=get_headers(), json={"job_id": job_id})
            response.raise_for_status()
            data = response.json()

        return {"status": "running", "job_id": job_id, "run_id": data.get("run_id")}

    except Exception as e:
        return {"error": str(e)}

async def run_notebook(notebook_path: str):
    """Run notebook"""
    try:
        url = f"{DATABRICKS_HOST}/api/2.1/jobs/runs/submit"
        payload = {
            "run_name": f"MCP Run: {notebook_path}",
            "tasks": [{
                "task_key": "notebook_task",
                "notebook_task": {"notebook_path": notebook_path},
                "existing_cluster_id": DATABRICKS_CLUSTER_ID
            }]
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=get_headers(), json=payload)
            response.raise_for_status()
            data = response.json()

        return {"status": "submitted", "run_id": data.get("run_id"), "notebook_path": notebook_path}

    except Exception as e:
        return {"error": str(e)}

async def stop_cluster(cluster_id: str = ""):
    """Stop a running cluster"""
    cluster_id = cluster_id or DATABRICKS_CLUSTER_ID
    if not cluster_id:
        return {"error": "No cluster_id provided"}

    try:
        url = f"{DATABRICKS_HOST}/api/2.0/clusters/delete"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=get_headers(), json={"cluster_id": cluster_id})
            response.raise_for_status()

        return {"status": "terminating", "cluster_id": cluster_id}

    except Exception as e:
        return {"error": str(e)}

async def get_job_run_status(run_id: int):
    """Get job run status"""
    try:
        url = f"{DATABRICKS_HOST}/api/2.1/jobs/runs/get"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=get_headers(), params={"run_id": run_id})
            response.raise_for_status()
            data = response.json()

        return {
            "run_id": data.get("run_id"),
            "state": data.get("state", {}).get("life_cycle_state"),
            "result_state": data.get("state", {}).get("result_state"),
            "start_time": data.get("start_time"),
            "end_time": data.get("end_time")
        }

    except Exception as e:
        return {"error": str(e)}

async def cancel_job_run(run_id: int):
    """Cancel a running job"""
    try:
        url = f"{DATABRICKS_HOST}/api/2.1/jobs/runs/cancel"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=get_headers(), json={"run_id": run_id})
            response.raise_for_status()

        return {"status": "cancelled", "run_id": run_id}

    except Exception as e:
        return {"error": str(e)}

async def list_notebooks(path: str = "/"):
    """List items in workspace path"""
    try:
        url = f"{DATABRICKS_HOST}/api/2.0/workspace/list"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=get_headers(), params={"path": path})
            response.raise_for_status()
            data = response.json()

        items = []
        for obj in data.get("objects", []):
            items.append({
                "path": obj.get("path"),
                "type": obj.get("object_type"),
                "language": obj.get("language", "")
            })

        return {"path": path, "items": items, "count": len(items)}

    except Exception as e:
        return {"error": str(e)}

async def list_workspace_folders(path: str = "/"):
    """List only folders in workspace path"""
    try:
        url = f"{DATABRICKS_HOST}/api/2.0/workspace/list"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=get_headers(), params={"path": path})
            response.raise_for_status()
            data = response.json()

        folders = []
        for obj in data.get("objects", []):
            if obj.get("object_type") == "DIRECTORY":
                folders.append(obj.get("path"))

        return {"path": path, "folders": folders, "count": len(folders)}

    except Exception as e:
        return {"error": str(e)}

async def find_notebooks(path: str = "/", max_depth: int = 3):
    """Find all notebooks recursively"""
    notebooks = []

    async def search_path(current_path: str, depth: int):
        if depth > max_depth:
            return

        try:
            url = f"{DATABRICKS_HOST}/api/2.0/workspace/list"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=get_headers(), params={"path": current_path})
                if response.status_code != 200:
                    return
                data = response.json()

            for obj in data.get("objects", []):
                obj_type = obj.get("object_type")
                obj_path = obj.get("path")

                if obj_type == "NOTEBOOK":
                    notebooks.append({
                        "path": obj_path,
                        "language": obj.get("language", ""),
                        "name": obj_path.split("/")[-1]
                    })
                elif obj_type == "DIRECTORY":
                    await search_path(obj_path, depth + 1)
        except:
            pass

    await search_path(path, 0)
    return {"search_path": path, "notebooks": notebooks, "count": len(notebooks)}

async def get_table_preview(table_name: str, limit: int = 10):
    """Preview table data"""
    query = f"SELECT * FROM {table_name} LIMIT {limit}"
    result = await execute_sql(query)

    if "error" in result:
        return result

    return {
        "table": table_name,
        "columns": result.get("columns", []),
        "rows": result.get("rows", []),
        "preview_count": len(result.get("rows", []))
    }

async def get_table_stats(table_name: str):
    """Get table statistics"""
    try:
        # Get row count
        count_result = await execute_sql(f"SELECT COUNT(*) as count FROM {table_name}")
        row_count = 0
        if "rows" in count_result and count_result["rows"]:
            row_count = count_result["rows"][0][0] if isinstance(count_result["rows"][0], list) else count_result["rows"][0]

        # Get table details
        describe_result = await execute_sql(f"DESCRIBE DETAIL {table_name}")

        stats = {
            "table": table_name,
            "row_count": row_count
        }

        if "rows" in describe_result and describe_result["rows"]:
            row = describe_result["rows"][0]
            if isinstance(row, list) and len(row) > 5:
                stats["format"] = row[0] if row[0] else "unknown"
                stats["location"] = row[3] if len(row) > 3 else ""

        return stats

    except Exception as e:
        return {"error": str(e)}

async def list_catalogs():
    """List Unity Catalog catalogs"""
    query = "SHOW CATALOGS"
    result = await execute_sql(query)

    if "error" in result:
        return result

    catalogs = [row[0] if isinstance(row, list) else row for row in result.get("rows", [])]
    return {"catalogs": catalogs, "count": len(catalogs)}

async def search_tables(pattern: str):
    """Search tables by pattern"""
    query = f"SHOW TABLES LIKE '{pattern}'"
    result = await execute_sql(query)

    if "error" in result:
        return result

    tables = []
    for row in result.get("rows", []):
        if isinstance(row, list) and len(row) > 1:
            tables.append({"database": row[0], "table": row[1]})

    return {"pattern": pattern, "tables": tables, "count": len(tables)}

async def get_cluster_logs(cluster_id: str = ""):
    """Get cluster event logs"""
    cluster_id = cluster_id or DATABRICKS_CLUSTER_ID
    if not cluster_id:
        return {"error": "No cluster_id provided"}

    try:
        url = f"{DATABRICKS_HOST}/api/2.0/clusters/events"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=get_headers(), json={
                "cluster_id": cluster_id,
                "limit": 10
            })
            response.raise_for_status()
            data = response.json()

        events = []
        for event in data.get("events", []):
            events.append({
                "timestamp": event.get("timestamp"),
                "type": event.get("type"),
                "details": event.get("details", {}).get("reason", {}).get("message", "")
            })

        return {"cluster_id": cluster_id, "events": events, "count": len(events)}

    except Exception as e:
        return {"error": str(e)}

@app.post("/execute")
async def execute_tool(request: ToolRequest):
    """Execute a tool - supports both static and dynamically evolved tools"""
    try:
        # Log execution for learning
        TOOL_EXECUTION_LOG.append({
            "tool": request.tool_name,
            "arguments": request.arguments,
            "timestamp": datetime.now().isoformat()
        })

        # Static tools (built-in)
        if request.tool_name == "execute_sql":
            result = await execute_sql(request.arguments.get("query", ""))
        elif request.tool_name == "list_databases":
            result = await list_databases()
        elif request.tool_name == "list_tables":
            result = await list_tables(request.arguments.get("schema", "default"))
        elif request.tool_name == "get_table_schema":
            result = await get_table_schema(
                request.arguments.get("table_name", ""),
                request.arguments.get("schema", "default")
            )
        elif request.tool_name == "list_clusters":
            result = await list_clusters()
        elif request.tool_name == "get_cluster_status":
            result = await get_cluster_status(request.arguments.get("cluster_id", ""))
        elif request.tool_name == "start_cluster":
            result = await start_cluster(request.arguments.get("cluster_id", ""))
        elif request.tool_name == "list_jobs":
            result = await list_jobs(request.arguments.get("limit", 25))
        elif request.tool_name == "run_job":
            result = await run_job(request.arguments.get("job_id"))
        elif request.tool_name == "run_notebook":
            result = await run_notebook(request.arguments.get("notebook_path", ""))
        elif request.tool_name == "stop_cluster":
            result = await stop_cluster(request.arguments.get("cluster_id", ""))
        elif request.tool_name == "get_job_run_status":
            result = await get_job_run_status(request.arguments.get("run_id"))
        elif request.tool_name == "cancel_job_run":
            result = await cancel_job_run(request.arguments.get("run_id"))
        elif request.tool_name == "list_notebooks":
            result = await list_notebooks(request.arguments.get("path", "/"))
        elif request.tool_name == "get_table_preview":
            result = await get_table_preview(
                request.arguments.get("table_name", ""),
                request.arguments.get("limit", 10)
            )
        elif request.tool_name == "get_table_stats":
            result = await get_table_stats(request.arguments.get("table_name", ""))
        elif request.tool_name == "list_catalogs":
            result = await list_catalogs()
        elif request.tool_name == "search_tables":
            result = await search_tables(request.arguments.get("pattern", "*"))
        elif request.tool_name == "get_cluster_logs":
            result = await get_cluster_logs(request.arguments.get("cluster_id", ""))
        elif request.tool_name == "list_workspace_folders":
            result = await list_workspace_folders(request.arguments.get("path", "/"))
        elif request.tool_name == "find_notebooks":
            result = await find_notebooks(request.arguments.get("path", "/"))
        # Evolution tools
        elif request.tool_name == "evolve_discover":
            # Trigger self-evolution
            discovered = []
            for category, actions in DATABRICKS_API_CATALOG.items():
                for action, api_info in actions.items():
                    tool_name = f"{category}_{action}"
                    if tool_name not in DYNAMIC_TOOLS:
                        tool_def = await auto_generate_tool(category, action, api_info)
                        discovered.append(tool_def["name"])
            result = {
                "status": "evolved",
                "new_tools": discovered,
                "total_dynamic_tools": len(DYNAMIC_TOOLS),
                "message": f"Agent evolved with {len(discovered)} new capabilities!"
            }
        elif request.tool_name == "evolve_list":
            result = {
                "dynamic_tools": [{"name": t["name"], "description": t["description"]} for t in DYNAMIC_TOOLS.values()],
                "count": len(DYNAMIC_TOOLS)
            }
        # Check dynamic tools (self-evolved)
        elif request.tool_name in DYNAMIC_TOOLS:
            result = await execute_dynamic_tool(request.tool_name, request.arguments)
        else:
            # Log missing capability for future evolution
            MISSING_CAPABILITY_LOG.append({
                "capability": request.tool_name,
                "context": str(request.arguments),
                "timestamp": datetime.now().isoformat()
            })
            result = {
                "error": f"Unknown tool: {request.tool_name}",
                "hint": "Use POST /evolve/discover to add new capabilities"
            }

        return {"result": json.dumps(result, indent=2)}

    except Exception as e:
        return {"result": json.dumps({"error": str(e)})}

@app.get("/health")
async def health():
    """Health check with Databricks connectivity test"""
    db_status = "unknown"
    db_error = None

    if DATABRICKS_HOST and DATABRICKS_TOKEN:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{DATABRICKS_HOST}/api/2.0/clusters/list",
                    headers=get_headers()
                )
                if response.status_code == 200:
                    db_status = "connected"
                else:
                    db_status = f"error ({response.status_code})"
                    db_error = response.text[:100]
        except Exception as e:
            db_status = "connection_failed"
            db_error = str(e)

    return {
        "status": "healthy",
        "databricks_host": DATABRICKS_HOST if DATABRICKS_HOST else "Not configured",
        "databricks_status": db_status,
        "databricks_error": db_error,
        "cluster_id": DATABRICKS_CLUSTER_ID if DATABRICKS_CLUSTER_ID else "Not set",
        "dynamic_tools_count": len(DYNAMIC_TOOLS)
    }

# ============== SELF-EVOLUTION SYSTEM ==============

# Known Databricks API endpoints that can be auto-discovered
DATABRICKS_API_CATALOG = {
    "cluster": {
        "create": {"method": "POST", "path": "/api/2.0/clusters/create", "description": "Create a new Databricks cluster",
                   "params": {
                       "cluster_name": {"type": "string", "description": "Name for the new cluster"},
                       "spark_version": {"type": "string", "description": "Spark version (e.g., '13.3.x-scala2.12')", "default": "13.3.x-scala2.12"},
                       "node_type_id": {"type": "string", "description": "Node type (e.g., 'Standard_DS3_v2')", "default": "Standard_DS3_v2"},
                       "num_workers": {"type": "integer", "description": "Number of worker nodes", "default": 1}
                   }},
        "edit": {"method": "POST", "path": "/api/2.0/clusters/edit", "description": "Edit an existing cluster configuration"},
        "resize": {"method": "POST", "path": "/api/2.0/clusters/resize", "description": "Resize a cluster"},
        "restart": {"method": "POST", "path": "/api/2.0/clusters/restart", "description": "Restart a cluster",
                    "params": {"cluster_id": {"type": "string", "description": "Cluster ID to restart"}}},
        "permanent_delete": {"method": "POST", "path": "/api/2.0/clusters/permanent-delete", "description": "Permanently delete a cluster"},
        "list_node_types": {"method": "GET", "path": "/api/2.0/clusters/list-node-types", "description": "List available node types for clusters"},
        "spark_versions": {"method": "GET", "path": "/api/2.0/clusters/spark-versions", "description": "List available Spark versions"},
    },
    "workspace": {
        "import": {"method": "POST", "path": "/api/2.0/workspace/import", "description": "Import/create a notebook. Use format=SOURCE and language=PYTHON/SQL/SCALA/R",
                   "params": {
                       "path": {"type": "string", "description": "Workspace path for the notebook (e.g., /Users/user@email.com/notebook_name)"},
                       "language": {"type": "string", "description": "Language: PYTHON, SQL, SCALA, or R", "default": "PYTHON"},
                       "content": {"type": "string", "description": "Base64 encoded notebook content (optional, empty for new notebook)"},
                       "format": {"type": "string", "description": "Format: SOURCE, HTML, JUPYTER, DBC", "default": "SOURCE"},
                       "overwrite": {"type": "boolean", "description": "Overwrite existing notebook", "default": False}
                   }},
        "export": {"method": "GET", "path": "/api/2.0/workspace/export", "description": "Export a notebook or file"},
        "delete": {"method": "POST", "path": "/api/2.0/workspace/delete", "description": "Delete workspace object"},
        "mkdirs": {"method": "POST", "path": "/api/2.0/workspace/mkdirs", "description": "Create directory in workspace"},
        "get_status": {"method": "GET", "path": "/api/2.0/workspace/get-status", "description": "Get workspace object status"},
    },
    "dbfs": {
        "list": {"method": "GET", "path": "/api/2.0/dbfs/list", "description": "List files in DBFS", "params": {"path": {"type": "string", "description": "DBFS path to list (e.g., /FileStore)", "default": "/"}}},
        "read": {"method": "GET", "path": "/api/2.0/dbfs/read", "description": "Read file from DBFS", "params": {"path": {"type": "string", "description": "DBFS file path to read"}}},
        "delete": {"method": "POST", "path": "/api/2.0/dbfs/delete", "description": "Delete file from DBFS", "params": {"path": {"type": "string", "description": "DBFS path to delete"}}},
        "mkdirs": {"method": "POST", "path": "/api/2.0/dbfs/mkdirs", "description": "Create directory in DBFS", "params": {"path": {"type": "string", "description": "DBFS path to create"}}},
    },
    "secrets": {
        "list_scopes": {"method": "GET", "path": "/api/2.0/secrets/scopes/list", "description": "List secret scopes"},
        "list_secrets": {"method": "GET", "path": "/api/2.0/secrets/list", "description": "List secrets in a scope"},
    },
    "repos": {
        "list": {"method": "GET", "path": "/api/2.0/repos", "description": "List Git repos"},
        "get": {"method": "GET", "path": "/api/2.0/repos/{repo_id}", "description": "Get repo details"},
        "update": {"method": "PATCH", "path": "/api/2.0/repos/{repo_id}", "description": "Update/pull repo"},
    },
    "pipelines": {
        "list": {"method": "GET", "path": "/api/2.0/pipelines", "description": "List Delta Live Tables pipelines"},
        "get": {"method": "GET", "path": "/api/2.0/pipelines/{pipeline_id}", "description": "Get pipeline details"},
        "start": {"method": "POST", "path": "/api/2.0/pipelines/{pipeline_id}/updates", "description": "Start pipeline"},
        "stop": {"method": "POST", "path": "/api/2.0/pipelines/{pipeline_id}/stop", "description": "Stop pipeline"},
    },
    "mlflow": {
        "list_experiments": {"method": "GET", "path": "/api/2.0/mlflow/experiments/list", "description": "List MLflow experiments"},
        "list_models": {"method": "GET", "path": "/api/2.0/mlflow/registered-models/list", "description": "List registered models"},
        "search_runs": {"method": "POST", "path": "/api/2.0/mlflow/runs/search", "description": "Search MLflow runs"},
    },
    "serving": {
        "list_endpoints": {"method": "GET", "path": "/api/2.0/serving-endpoints", "description": "List model serving endpoints"},
        "get_endpoint": {"method": "GET", "path": "/api/2.0/serving-endpoints/{name}", "description": "Get serving endpoint details"},
    }
}

async def auto_generate_tool(category: str, action: str, api_info: dict) -> dict:
    """Auto-generate a new tool from API catalog"""
    tool_name = f"{category}_{action}"

    # Build input schema based on path parameters
    properties = {}
    required = []
    path = api_info["path"]

    # Extract path parameters like {repo_id}
    import re
    params = re.findall(r'\{(\w+)\}', path)
    for param in params:
        properties[param] = {"type": "string", "description": f"{param.replace('_', ' ').title()}"}
        required.append(param)

    # Add custom parameters from API catalog if defined
    if "params" in api_info:
        for param_name, param_def in api_info["params"].items():
            properties[param_name] = param_def
            if "default" not in param_def:
                required.append(param_name)

    tool_def = {
        "name": tool_name,
        "description": api_info["description"],
        "api_path": path,
        "api_method": api_info["method"],
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required
        },
        "auto_generated": True
    }

    DYNAMIC_TOOLS[tool_name] = tool_def
    save_evolved_tools()  # Persist after adding new tool
    return tool_def

async def execute_dynamic_tool(tool_name: str, arguments: dict) -> dict:
    """Execute a dynamically generated tool"""
    if tool_name not in DYNAMIC_TOOLS:
        return {"error": f"Dynamic tool '{tool_name}' not found"}

    tool_def = DYNAMIC_TOOLS[tool_name]
    api_path = tool_def["api_path"]
    method = tool_def["api_method"]

    # Separate path parameters from query/body parameters
    import re
    path_params = set(re.findall(r'\{(\w+)\}', api_path))
    body_params = {k: v for k, v in arguments.items() if k not in path_params}

    # Replace path parameters
    for key, value in arguments.items():
        if key in path_params:
            api_path = api_path.replace(f"{{{key}}}", str(value))

    url = f"{DATABRICKS_HOST}{api_path}"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if method == "GET":
                # Special handling for specific GET tools that need path param
                if tool_name == "dbfs_list":
                    params = {"path": arguments.get("path", "/")}
                    response = await client.get(url, headers=get_headers(), params=params)
                elif tool_name == "dbfs_read":
                    params = {"path": arguments.get("path", "")}
                    response = await client.get(url, headers=get_headers(), params=params)
                elif tool_name == "workspace_export":
                    params = {"path": arguments.get("path", ""), "format": arguments.get("format", "SOURCE")}
                    response = await client.get(url, headers=get_headers(), params=params)
                elif tool_name == "workspace_get_status":
                    params = {"path": arguments.get("path", "")}
                    response = await client.get(url, headers=get_headers(), params=params)
                else:
                    # Default: pass non-path params as query params
                    response = await client.get(url, headers=get_headers(), params=body_params if body_params else None)
            elif method == "POST":
                # For POST, pass as JSON body
                # Special handling for specific tools
                if tool_name == "cluster_create":
                    payload = {
                        "cluster_name": arguments.get("cluster_name", "MCP-Created-Cluster"),
                        "spark_version": arguments.get("spark_version", "13.3.x-scala2.12"),
                        "node_type_id": arguments.get("node_type_id", "Standard_DS3_v2"),
                        "num_workers": arguments.get("num_workers", 1),
                        "autotermination_minutes": 60
                    }
                    response = await client.post(url, headers=get_headers(), json=payload)
                elif tool_name == "cluster_restart":
                    payload = {"cluster_id": arguments.get("cluster_id", "")}
                    response = await client.post(url, headers=get_headers(), json=payload)
                elif tool_name in ["workspace_mkdirs", "dbfs_mkdirs"]:
                    # These require 'path' in body
                    payload = {"path": arguments.get("path", "/")}
                    response = await client.post(url, headers=get_headers(), json=payload)
                elif tool_name == "workspace_delete":
                    payload = {"path": arguments.get("path", ""), "recursive": arguments.get("recursive", False)}
                    response = await client.post(url, headers=get_headers(), json=payload)
                elif tool_name == "dbfs_delete":
                    payload = {"path": arguments.get("path", ""), "recursive": arguments.get("recursive", False)}
                    response = await client.post(url, headers=get_headers(), json=payload)
                elif tool_name == "workspace_import":
                    # Create/import notebook
                    import base64
                    print(f"[DEBUG workspace_import] arguments received: {arguments}")
                    content = arguments.get("content", "")
                    path = arguments.get("path", "")
                    print(f"[DEBUG workspace_import] path extracted: '{path}'")
                    if not content:
                        # Empty notebook with a comment
                        language = arguments.get("language", "PYTHON").upper()
                        if language == "PYTHON":
                            content = "# Databricks notebook source\n# Created via MCP"
                        elif language == "SQL":
                            content = "-- Databricks notebook source\n-- Created via MCP"
                        elif language == "SCALA":
                            content = "// Databricks notebook source\n// Created via MCP"
                        elif language == "R":
                            content = "# Databricks notebook source\n# Created via MCP"
                        else:
                            content = "# Created via MCP"
                    # Base64 encode the content
                    encoded_content = base64.b64encode(content.encode()).decode()
                    payload = {
                        "path": path,
                        "language": arguments.get("language", "PYTHON").upper(),
                        "content": encoded_content,
                        "format": arguments.get("format", "SOURCE"),
                        "overwrite": arguments.get("overwrite", False)
                    }
                    print(f"[DEBUG workspace_import] payload: {payload}")
                    response = await client.post(url, headers=get_headers(), json=payload)
                else:
                    # Default: pass all body params as JSON
                    response = await client.post(url, headers=get_headers(), json=body_params if body_params else {})
            elif method == "PATCH":
                response = await client.patch(url, headers=get_headers(), json=body_params if body_params else {})
            else:
                return {"error": f"Unsupported method: {method}"}

            response.raise_for_status()

            # Handle empty responses
            if response.status_code == 200 and not response.text:
                return {"status": "success", "message": f"{tool_name} completed successfully"}

            result = response.json()

            # Add helpful messages
            if tool_name == "cluster_create" and "cluster_id" in result:
                result["message"] = f"Cluster created successfully! ID: {result['cluster_id']}"
            elif tool_name in ["workspace_mkdirs", "dbfs_mkdirs"]:
                result = {"status": "success", "message": f"Directory created: {arguments.get('path')}"}
            elif tool_name == "workspace_import":
                result = {"status": "success", "message": f"Notebook created: {arguments.get('path')}", "language": arguments.get("language", "PYTHON")}

            return result
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/evolve/discover")
async def discover_capabilities():
    """Discover and register new API capabilities"""
    discovered = []

    for category, actions in DATABRICKS_API_CATALOG.items():
        for action, api_info in actions.items():
            tool_name = f"{category}_{action}"
            if tool_name not in DYNAMIC_TOOLS:
                tool_def = await auto_generate_tool(category, action, api_info)
                discovered.append(tool_def)

    # Save all discovered tools to JSON file
    if discovered:
        save_evolved_tools()

    return {
        "status": "success",
        "discovered_count": len(discovered),
        "new_tools": [t["name"] for t in discovered],
        "total_dynamic_tools": len(DYNAMIC_TOOLS),
        "persisted_to": str(EVOLVED_TOOLS_FILE)
    }

@app.get("/evolve/tools")
async def list_dynamic_tools():
    """List all dynamically generated tools"""
    return {
        "dynamic_tools": list(DYNAMIC_TOOLS.values()),
        "count": len(DYNAMIC_TOOLS)
    }

@app.post("/evolve/log_missing")
async def log_missing_capability(request: dict):
    """Log when a capability is missing - helps the agent learn what to add"""
    capability = request.get("capability", "")
    context = request.get("context", "")

    MISSING_CAPABILITY_LOG.append({
        "capability": capability,
        "context": context,
        "timestamp": datetime.now().isoformat()
    })

    # Try to auto-suggest from catalog
    suggestions = []
    for category, actions in DATABRICKS_API_CATALOG.items():
        for action, api_info in actions.items():
            if capability.lower() in action.lower() or capability.lower() in api_info["description"].lower():
                suggestions.append(f"{category}_{action}")

    return {
        "logged": True,
        "suggestions": suggestions,
        "message": f"Capability '{capability}' logged. Use /evolve/discover to add suggested tools."
    }

@app.get("/evolve/missing")
async def get_missing_capabilities():
    """Get log of missing capabilities"""
    return {"missing_capabilities": MISSING_CAPABILITY_LOG}

@app.post("/evolve/add_custom")
async def add_custom_tool(request: dict):
    """Add a completely custom tool definition"""
    name = request.get("name")
    description = request.get("description")
    api_path = request.get("api_path")
    api_method = request.get("api_method", "GET")
    input_schema = request.get("input_schema", {"type": "object", "properties": {}, "required": []})

    if not all([name, description, api_path]):
        return {"error": "Missing required fields: name, description, api_path"}

    tool_def = {
        "name": name,
        "description": description,
        "api_path": api_path,
        "api_method": api_method,
        "inputSchema": input_schema,
        "auto_generated": False,
        "custom": True
    }

    DYNAMIC_TOOLS[name] = tool_def
    save_evolved_tools()  # Persist custom tool
    return {"status": "success", "tool": tool_def}

@app.post("/evolve/reload")
async def reload_tools():
    """Reload evolved tools from JSON file"""
    count = load_evolved_tools()
    return {
        "status": "success",
        "loaded_count": count,
        "file": str(EVOLVED_TOOLS_FILE)
    }

@app.delete("/evolve/clear")
async def clear_evolved_tools():
    """Clear all evolved tools (both memory and file)"""
    global DYNAMIC_TOOLS
    DYNAMIC_TOOLS = {}
    if EVOLVED_TOOLS_FILE.exists():
        EVOLVED_TOOLS_FILE.unlink()
    return {"status": "success", "message": "All evolved tools cleared"}

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  Databricks MCP Server - SELF-EVOLVING + PERSISTENT")
    print("=" * 60)
    print(f"  Host: {DATABRICKS_HOST or 'Not configured'}")
    print(f"  Token: {'Configured' if DATABRICKS_TOKEN else 'Missing'}")
    print(f"  Cluster: {DATABRICKS_CLUSTER_ID or 'Not set'}")
    print()
    print(f"  Evolved Tools File: {EVOLVED_TOOLS_FILE}")
    print(f"  Pre-loaded Tools: {len(DYNAMIC_TOOLS)}")
    print("=" * 60)
    print("  Evolution Endpoints:")
    print("    POST /evolve/discover - Auto-discover new tools")
    print("    GET  /evolve/tools    - List dynamic tools")
    print("    POST /evolve/add_custom - Add custom tool")
    print("    POST /evolve/reload   - Reload from JSON file")
    print("    DELETE /evolve/clear  - Clear all evolved tools")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8099)
