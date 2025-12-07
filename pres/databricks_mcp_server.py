"""
Databricks MCP Server - Data Analytics & ML Platform
Execute SQL queries, run notebooks, manage clusters, and access Delta Lake
"""

from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import json
import os
import asyncio
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import base64

load_dotenv()

app = FastAPI(title="Databricks MCP Server")

# Databricks API configuration
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")  # e.g., https://adb-1234567890123456.7.azuredatabricks.net
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")  # Personal access token
DATABRICKS_CLUSTER_ID = os.getenv("DATABRICKS_CLUSTER_ID", "")  # Default cluster ID

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
        "note": "Execute SQL queries, run notebooks, manage clusters",
        "setup": "Set DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_CLUSTER_ID in .env",
        "get_token": "https://docs.databricks.com/dev-tools/auth.html#databricks-personal-access-tokens",
        "endpoints": {
            "tools": "/tools",
            "execute": "/execute",
            "health": "/health"
        }
    }

@app.get("/tools")
async def list_tools() -> List[Tool]:
    """List all available tools"""
    return [
        Tool(
            name="execute_sql",
            description="Execute SQL query on Databricks. Args: query (str), warehouse_id (str: optional)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL query to execute"
                    },
                    "warehouse_id": {
                        "type": "string",
                        "description": "SQL warehouse ID (optional, uses default if not provided)",
                        "default": ""
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="natural_language_query",
            description="Convert natural language question to SQL query and execute it. Args: question (str), table_name (str: optional)",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Natural language question (e.g., 'show 3 month attendance report', 'count employees by department')"
                    },
                    "table_name": {
                        "type": "string",
                        "description": "Table name to query (optional, will auto-detect if not provided)",
                        "default": ""
                    }
                },
                "required": ["question"]
            }
        ),
        Tool(
            name="list_databases",
            description="List all databases/schemas in a catalog. Args: catalog (str: optional)",
            inputSchema={
                "type": "object",
                "properties": {
                    "catalog": {
                        "type": "string",
                        "description": "Catalog name (default: hive_metastore)",
                        "default": "hive_metastore"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="list_tables",
            description="List all tables in a database/schema. Args: catalog (str: optional), schema (str: optional)",
            inputSchema={
                "type": "object",
                "properties": {
                    "catalog": {
                        "type": "string",
                        "description": "Catalog name (default: hive_metastore)",
                        "default": "hive_metastore"
                    },
                    "schema": {
                        "type": "string",
                        "description": "Schema/database name (default: default)",
                        "default": "default"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_table_schema",
            description="Get schema/columns of a table. Args: table_name (str), catalog (str: optional), schema (str: optional)",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Table name"
                    },
                    "catalog": {
                        "type": "string",
                        "description": "Catalog name",
                        "default": "hive_metastore"
                    },
                    "schema": {
                        "type": "string",
                        "description": "Schema/database name",
                        "default": "default"
                    }
                },
                "required": ["table_name"]
            }
        ),
        Tool(
            name="run_notebook",
            description="Run a Databricks notebook. Args: notebook_path (str), parameters (dict: optional)",
            inputSchema={
                "type": "object",
                "properties": {
                    "notebook_path": {
                        "type": "string",
                        "description": "Path to notebook (e.g., /Users/user@example.com/MyNotebook)"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Notebook parameters as key-value pairs",
                        "default": {}
                    },
                    "cluster_id": {
                        "type": "string",
                        "description": "Cluster ID to run on",
                        "default": ""
                    }
                },
                "required": ["notebook_path"]
            }
        ),
        Tool(
            name="list_clusters",
            description="List all available Databricks clusters. No arguments required.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_cluster_status",
            description="Get status of a cluster. Args: cluster_id (str: optional, uses default if not provided)",
            inputSchema={
                "type": "object",
                "properties": {
                    "cluster_id": {
                        "type": "string",
                        "description": "Cluster ID",
                        "default": ""
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="start_cluster",
            description="Start a stopped cluster. Args: cluster_id (str: optional, uses default if not provided)",
            inputSchema={
                "type": "object",
                "properties": {
                    "cluster_id": {
                        "type": "string",
                        "description": "Cluster ID to start",
                        "default": ""
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="create_cluster",
            description="Create a new Databricks cluster (Personal Compute policy). Args: cluster_name (str), node_type (str: optional), spark_version (str: optional), autotermination_minutes (int: optional)",
            inputSchema={
                "type": "object",
                "properties": {
                    "cluster_name": {
                        "type": "string",
                        "description": "Name for the new cluster"
                    },
                    "node_type": {
                        "type": "string",
                        "description": "Node type - allowed: Standard_D4ds_v5, Standard_D8ds_v5, Standard_D16ds_v5, Standard_DS3_v2, etc.",
                        "default": "Standard_D4ds_v5"
                    },
                    "num_workers": {
                        "type": "integer",
                        "description": "Number of workers (always 0 for Personal Compute policy)",
                        "default": 0
                    },
                    "spark_version": {
                        "type": "string",
                        "description": "Spark version (e.g., 16.4.x-cpu-ml-scala2.12, 13.3.x-scala2.12)",
                        "default": "16.4.x-cpu-ml-scala2.12"
                    },
                    "autotermination_minutes": {
                        "type": "integer",
                        "description": "Auto-terminate after N minutes of inactivity",
                        "default": 120
                    }
                },
                "required": ["cluster_name"]
            }
        ),
        Tool(
            name="list_jobs",
            description="List all Databricks jobs. Args: limit (int: optional, default 25)",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of jobs to return",
                        "default": 25
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="run_job",
            description="Trigger a job run. Args: job_id (int), parameters (dict: optional)",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "integer",
                        "description": "Job ID to run"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Job parameters",
                        "default": {}
                    }
                },
                "required": ["job_id"]
            }
        ),
        Tool(
            name="get_job_run_status",
            description="Get status of a job run. Args: run_id (int)",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "integer",
                        "description": "Run ID to check"
                    }
                },
                "required": ["run_id"]
            }
        )
    ]

async def natural_language_query(question: str, table_name: str = ""):
    """Convert natural language to SQL and execute it"""
    if not DATABRICKS_HOST or not DATABRICKS_TOKEN:
        return {"error": "Databricks credentials not configured"}

    try:
        print(f"🤖 Translating natural language to SQL...")
        print(f"Question: {question}")

        # If no table specified, try to detect from available tables
        if not table_name:
            tables_result = await list_tables()
            available_tables = tables_result.get("tables", [])
            if available_tables:
                table_name = available_tables[0]  # Use first table
                print(f"📋 Auto-detected table: {table_name}")

        # Get table schema to help with SQL generation
        schema_result = await get_table_schema(table_name)
        columns = schema_result.get("columns", [])
        column_info = ", ".join([f"{col['name']} ({col['type']})" for col in columns])

        # Build SQL based on common patterns
        question_lower = question.lower()

        # Pattern: 3 month report / attendance report
        if "month" in question_lower and ("report" in question_lower or "attendance" in question_lower):
            # Extract number of months
            import re
            months_match = re.search(r'(\d+)\s*month', question_lower)
            months = int(months_match.group(1)) if months_match else 3

            sql = f"""
SELECT
    DATE_TRUNC('month', date) as month,
    department,
    status,
    COUNT(*) as count,
    COUNT(DISTINCT employee_id) as unique_employees
FROM {table_name}
WHERE date >= DATE_SUB(CURRENT_DATE(), {months * 30})
GROUP BY DATE_TRUNC('month', date), department, status
ORDER BY month DESC, department, status
"""

        # Pattern: count by department
        elif "count" in question_lower and "department" in question_lower:
            sql = f"SELECT department, COUNT(*) as count FROM {table_name} GROUP BY department ORDER BY count DESC"

        # Pattern: show/list all
        elif any(word in question_lower for word in ["show", "list", "all", "select"]):
            limit = 100
            if "limit" in question_lower:
                limit_match = re.search(r'limit\s+(\d+)', question_lower)
                if limit_match:
                    limit = int(limit_match.group(1))
            sql = f"SELECT * FROM {table_name} LIMIT {limit}"

        # Pattern: filter by employee
        elif "employee" in question_lower:
            # Extract employee name if present
            import re
            name_match = re.search(r'employee[_\s]+(\w+)', question_lower)
            if name_match:
                name = name_match.group(1).title()
                sql = f"SELECT * FROM {table_name} WHERE employee_name LIKE '%{name}%' ORDER BY date DESC"
            else:
                sql = f"SELECT employee_name, COUNT(*) as records FROM {table_name} GROUP BY employee_name"

        # Pattern: summary/stats
        elif "summary" in question_lower or "stats" in question_lower or "statistics" in question_lower:
            sql = f"""
SELECT
    COUNT(*) as total_records,
    COUNT(DISTINCT employee_id) as total_employees,
    COUNT(DISTINCT department) as total_departments,
    MIN(date) as earliest_date,
    MAX(date) as latest_date
FROM {table_name}
"""

        # Default: simple select
        else:
            sql = f"SELECT * FROM {table_name} LIMIT 10"

        print(f"📝 Generated SQL: {sql.strip()}")

        # Execute the SQL
        result = await execute_sql(sql.strip())

        # Add the generated SQL to the result
        if isinstance(result, dict):
            result["generated_sql"] = sql.strip()
            result["question"] = question

        return result

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}

async def execute_sql(query: str, warehouse_id: str = ""):
    """Execute SQL query on Databricks SQL warehouse"""
    if not DATABRICKS_HOST or not DATABRICKS_TOKEN:
        return {"error": "Databricks credentials not configured"}

    try:
        print(f"📊 Executing SQL query...")
        print(f"Query: {query[:100]}...")

        url = f"{DATABRICKS_HOST}/api/2.0/sql/statements"

        payload = {
            "statement": query,
            "warehouse_id": warehouse_id or os.getenv("DATABRICKS_WAREHOUSE_ID", ""),
            "wait_timeout": "30s"
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=get_headers(), json=payload)
            response.raise_for_status()
            data = response.json()

        # Parse results
        if data.get("status", {}).get("state") == "SUCCEEDED":
            result = data.get("result", {})
            columns = [col["name"] for col in result.get("data_array", [])]
            rows = result.get("data_array", [])

            print(f"✅ Query executed: {len(rows)} rows")
            return {
                "status": "success",
                "columns": columns,
                "rows": rows[:100],  # Limit to 100 rows
                "total_rows": len(rows),
                "execution_time": data.get("status", {}).get("execution_time_ms", 0)
            }
        else:
            error = data.get("status", {}).get("error", {})
            return {
                "error": f"Query failed: {error.get('message', 'Unknown error')}"
            }

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")

        # Try using cluster if warehouse fails
        print("⚠️  SQL warehouse not available, trying cluster for query...")
        try:
            result = await execute_sql_on_cluster(query)
            if "error" not in result:
                return result
        except Exception as cluster_error:
            print(f"❌ Cluster execution also failed: {cluster_error}")

        return {"error": error_msg}

async def execute_sql_on_cluster(query: str, cluster_id: str = None):
    """Execute SQL on a cluster using context API"""
    if not cluster_id:
        cluster_id = DATABRICKS_CLUSTER_ID or os.getenv("DATABRICKS_CLUSTER_ID", "")

    if not cluster_id or cluster_id == "your-cluster-id-optional":
        return {"error": "No cluster configured"}

    try:
        # Create execution context
        context_url = f"{DATABRICKS_HOST}/api/1.2/contexts/create"
        context_payload = {
            "clusterId": cluster_id,
            "language": "sql"
        }

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
            for _ in range(30):  # Poll for up to 30 seconds
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

                    # Extract column names from schema
                    columns = [col.get("name", f"col_{i}") for i, col in enumerate(schema)]

                    # Return in execute_sql compatible format
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

async def list_databases(catalog: str = "dbrmitko"):
    """List databases/schemas in a catalog"""
    if not DATABRICKS_HOST or not DATABRICKS_TOKEN:
        return {"error": "Databricks credentials not configured"}

    try:
        print(f"📋 Listing databases in {catalog}")

        # Try SQL warehouse first
        query = f"SHOW DATABASES"
        result = await execute_sql(query)

        if "error" in result:
            # Try using cluster if warehouse fails
            print("⚠️  SQL warehouse not available, trying cluster...")
            result = await execute_sql_on_cluster(query)

            if "error" in result:
                # If both fail, provide common database names
                print("⚠️  Both warehouse and cluster unavailable")
                return {
                    "catalog": catalog,
                    "databases": ["default"],
                    "count": 1,
                    "note": "Configure DATABRICKS_WAREHOUSE_ID or ensure cluster is running to see all databases"
                }

        # Parse results
        if isinstance(result, dict) and "rows" in result:
            databases = [row[0] if isinstance(row, list) else row.get("databaseName", row.get("namespace", ""))
                        for row in result.get("rows", [])]
        else:
            databases = ["default"]

        databases = [db for db in databases if db]  # Filter empty strings

        print(f"✅ Found {len(databases)} databases")
        return {
            "catalog": catalog,
            "databases": databases,
            "count": len(databases)
        }

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}

async def list_tables(catalog: str = "dbrmitko", schema: str = "default"):
    """List tables in a schema"""
    if not DATABRICKS_HOST or not DATABRICKS_TOKEN:
        return {"error": "Databricks credentials not configured"}

    try:
        print(f"📋 Listing tables in {catalog}.{schema}")

        # Try SQL warehouse first
        query = f"USE CATALOG {catalog}; SHOW TABLES IN {schema}"
        result = await execute_sql(query)

        if "error" in result:
            # Try using cluster if warehouse fails
            print("⚠️  SQL warehouse not available, trying cluster...")
            result = await execute_sql_on_cluster(query)

            if "error" in result:
                # If both fail, provide helpful message
                print("⚠️  Both warehouse and cluster unavailable")
                return {
                    "catalog": catalog,
                    "schema": schema,
                    "tables": [],
                    "count": 0,
                    "note": "Configure DATABRICKS_WAREHOUSE_ID or ensure cluster is running to list tables"
                }

        # Parse results
        if isinstance(result, dict) and "rows" in result:
            # Table name is usually second column in SHOW TABLES result
            tables = []
            for row in result.get("rows", []):
                if isinstance(row, list) and len(row) > 1:
                    tables.append(row[1])  # Second column is table name
                elif isinstance(row, dict):
                    tables.append(row.get("tableName", ""))
        else:
            tables = []

        tables = [t for t in tables if t]  # Filter empty strings

        print(f"✅ Found {len(tables)} tables")
        return {
            "catalog": catalog,
            "schema": schema,
            "tables": tables,
            "count": len(tables)
        }

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}

async def get_table_schema(table_name: str, catalog: str = "dbrmitko", schema: str = "default"):
    """Get table schema/columns"""
    if not DATABRICKS_HOST or not DATABRICKS_TOKEN:
        return {"error": "Databricks credentials not configured"}

    try:
        print(f"📋 Getting schema for {catalog}.{schema}.{table_name}")

        # Use schema.table_name format (not catalog.schema.table)
        query = f"DESCRIBE TABLE {schema}.{table_name}"
        result = await execute_sql(query)

        if "error" in result:
            return result

        columns = []
        for row in result.get("rows", []):
            if row[0] and not row[0].startswith("#"):  # Skip comments
                columns.append({
                    "name": row[0],
                    "type": row[1],
                    "comment": row[2] if len(row) > 2 else ""
                })

        print(f"✅ Found {len(columns)} columns")
        return {
            "catalog": catalog,
            "schema": schema,
            "table": table_name,
            "columns": columns,
            "count": len(columns)
        }

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}

async def run_notebook(notebook_path: str, parameters: dict = None, cluster_id: str = ""):
    """Run a Databricks notebook"""
    if not DATABRICKS_HOST or not DATABRICKS_TOKEN:
        return {"error": "Databricks credentials not configured"}

    try:
        print(f"📓 Running notebook: {notebook_path}")

        url = f"{DATABRICKS_HOST}/api/2.1/jobs/runs/submit"

        payload = {
            "run_name": f"MCP Run: {notebook_path}",
            "tasks": [{
                "task_key": "notebook_task",
                "notebook_task": {
                    "notebook_path": notebook_path,
                    "base_parameters": parameters or {}
                },
                "existing_cluster_id": cluster_id or DATABRICKS_CLUSTER_ID
            }]
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=get_headers(), json=payload)
            response.raise_for_status()
            data = response.json()

        run_id = data.get("run_id")

        print(f"✅ Notebook run submitted: Run ID {run_id}")
        return {
            "status": "submitted",
            "run_id": run_id,
            "notebook_path": notebook_path,
            "parameters": parameters or {},
            "message": f"Use get_job_run_status with run_id={run_id} to check status"
        }

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}

async def list_clusters():
    """List all clusters"""
    if not DATABRICKS_HOST or not DATABRICKS_TOKEN:
        return {"error": "Databricks credentials not configured"}

    try:
        print(f"🖥️  Listing clusters...")

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
                "state": cluster.get("state"),
                "spark_version": cluster.get("spark_version"),
                "node_type": cluster.get("node_type_id")
            })

        print(f"✅ Found {len(clusters)} clusters")
        return {
            "clusters": clusters,
            "count": len(clusters)
        }

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}

async def get_cluster_status(cluster_id: str = ""):
    """Get cluster status"""
    if not DATABRICKS_HOST or not DATABRICKS_TOKEN:
        return {"error": "Databricks credentials not configured"}

    cluster_id = cluster_id or DATABRICKS_CLUSTER_ID
    if not cluster_id:
        return {"error": "No cluster_id provided and DATABRICKS_CLUSTER_ID not set"}

    try:
        print(f"🖥️  Getting cluster status: {cluster_id}")

        url = f"{DATABRICKS_HOST}/api/2.0/clusters/get"
        params = {"cluster_id": cluster_id}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=get_headers(), params=params)
            response.raise_for_status()
            data = response.json()

        result = {
            "cluster_id": data.get("cluster_id"),
            "cluster_name": data.get("cluster_name"),
            "state": data.get("state"),
            "state_message": data.get("state_message", ""),
            "spark_version": data.get("spark_version"),
            "driver": data.get("driver", {}).get("node_id", ""),
            "num_workers": data.get("num_workers", 0)
        }

        print(f"✅ Cluster state: {result['state']}")
        return result

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}

async def start_cluster(cluster_id: str = ""):
    """Start a cluster"""
    if not DATABRICKS_HOST or not DATABRICKS_TOKEN:
        return {"error": "Databricks credentials not configured"}

    cluster_id = cluster_id or DATABRICKS_CLUSTER_ID
    if not cluster_id:
        return {"error": "No cluster_id provided and DATABRICKS_CLUSTER_ID not set"}

    try:
        print(f"🖥️  Starting cluster: {cluster_id}")

        url = f"{DATABRICKS_HOST}/api/2.0/clusters/start"
        payload = {"cluster_id": cluster_id}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=get_headers(), json=payload)
            response.raise_for_status()

        print(f"✅ Cluster start initiated")
        return {
            "status": "starting",
            "cluster_id": cluster_id,
            "message": "Cluster is starting. Use get_cluster_status to check progress."
        }

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}

async def create_cluster(cluster_name: str, node_type: str = "Standard_D4ds_v5", num_workers: int = 0, spark_version: str = "16.4.x-cpu-ml-scala2.12", autotermination_minutes: int = 120):
    """Create a new Databricks cluster compliant with workspace policies"""
    if not DATABRICKS_HOST or not DATABRICKS_TOKEN:
        return {"error": "Databricks credentials not configured"}

    try:
        print(f"🖥️  Creating cluster: {cluster_name}")

        url = f"{DATABRICKS_HOST}/api/2.0/clusters/create"

        # Build payload using Personal Compute policy (policy_id: 001616F1A8A68D72)
        payload = {
            "cluster_name": cluster_name,
            "policy_id": "001616F1A8A68D72",  # Personal Compute policy
            "spark_version": spark_version,
            "node_type_id": node_type,  # Required even with policy
            "data_security_mode": "SINGLE_USER"  # Required by Personal Compute policy
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=get_headers(), json=payload)
            response.raise_for_status()
            data = response.json()

        cluster_id = data.get("cluster_id")

        print(f"✅ Cluster created: {cluster_id}")
        return {
            "status": "created",
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
            "node_type": node_type,
            "num_workers": num_workers,
            "spark_version": spark_version,
            "autotermination_minutes": autotermination_minutes,
            "message": f"Cluster created successfully! ID: {cluster_id}"
        }

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}

async def list_jobs(limit: int = 25):
    """List Databricks jobs"""
    if not DATABRICKS_HOST or not DATABRICKS_TOKEN:
        return {"error": "Databricks credentials not configured"}

    try:
        print(f"📋 Listing jobs...")

        url = f"{DATABRICKS_HOST}/api/2.1/jobs/list"
        params = {"limit": limit}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=get_headers(), params=params)
            response.raise_for_status()
            data = response.json()

        jobs = []
        for job in data.get("jobs", []):
            jobs.append({
                "job_id": job.get("job_id"),
                "name": job.get("settings", {}).get("name", "Unnamed"),
                "created_time": job.get("created_time"),
                "creator": job.get("creator_user_name", "")
            })

        print(f"✅ Found {len(jobs)} jobs")
        return {
            "jobs": jobs,
            "count": len(jobs)
        }

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}

async def run_job(job_id: int, parameters: dict = None):
    """Run a Databricks job"""
    if not DATABRICKS_HOST or not DATABRICKS_TOKEN:
        return {"error": "Databricks credentials not configured"}

    try:
        print(f"🚀 Running job: {job_id}")

        url = f"{DATABRICKS_HOST}/api/2.1/jobs/run-now"
        payload = {
            "job_id": job_id,
            "notebook_params": parameters or {}
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=get_headers(), json=payload)
            response.raise_for_status()
            data = response.json()

        run_id = data.get("run_id")

        print(f"✅ Job run started: Run ID {run_id}")
        return {
            "status": "running",
            "job_id": job_id,
            "run_id": run_id,
            "message": f"Use get_job_run_status with run_id={run_id} to check status"
        }

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}

async def get_job_run_status(run_id: int):
    """Get job run status"""
    if not DATABRICKS_HOST or not DATABRICKS_TOKEN:
        return {"error": "Databricks credentials not configured"}

    try:
        print(f"📊 Checking run status: {run_id}")

        url = f"{DATABRICKS_HOST}/api/2.1/jobs/runs/get"
        params = {"run_id": run_id}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=get_headers(), params=params)
            response.raise_for_status()
            data = response.json()

        result = {
            "run_id": data.get("run_id"),
            "run_name": data.get("run_name"),
            "state": data.get("state", {}).get("life_cycle_state"),
            "result_state": data.get("state", {}).get("result_state"),
            "state_message": data.get("state", {}).get("state_message", ""),
            "start_time": data.get("start_time"),
            "end_time": data.get("end_time")
        }

        print(f"✅ Run state: {result['state']}")
        return result

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}

@app.post("/execute")
async def execute_tool(request: ToolRequest):
    """Execute a tool"""
    try:
        print(f"📊 Executing: {request.tool_name}")
        print(f"📦 Arguments: {request.arguments}")

        if request.tool_name == "natural_language_query":
            question = request.arguments.get("question")
            table_name = request.arguments.get("table_name", "")

            if not question:
                return {"result": json.dumps({"error": "Missing required field: question"})}

            result = await natural_language_query(question, table_name)

        elif request.tool_name == "execute_sql":
            query = request.arguments.get("query")
            warehouse_id = request.arguments.get("warehouse_id", "")

            if not query:
                return {"result": json.dumps({"error": "Missing required field: query"})}

            result = await execute_sql(query, warehouse_id)

        elif request.tool_name == "list_databases":
            catalog = request.arguments.get("catalog", "dbrmitko")
            result = await list_databases(catalog)

        elif request.tool_name == "list_tables":
            catalog = request.arguments.get("catalog", "dbrmitko")
            schema = request.arguments.get("schema", "default")
            result = await list_tables(catalog, schema)

        elif request.tool_name == "get_table_schema":
            table_name = request.arguments.get("table_name")
            catalog = request.arguments.get("catalog", "dbrmitko")
            schema = request.arguments.get("schema", "default")

            if not table_name:
                return {"result": json.dumps({"error": "Missing required field: table_name"})}

            result = await get_table_schema(table_name, catalog, schema)

        elif request.tool_name == "run_notebook":
            notebook_path = request.arguments.get("notebook_path")
            parameters = request.arguments.get("parameters", {})
            cluster_id = request.arguments.get("cluster_id", "")

            if not notebook_path:
                return {"result": json.dumps({"error": "Missing required field: notebook_path"})}

            result = await run_notebook(notebook_path, parameters, cluster_id)

        elif request.tool_name == "list_clusters":
            result = await list_clusters()

        elif request.tool_name == "get_cluster_status":
            cluster_id = request.arguments.get("cluster_id", "")
            result = await get_cluster_status(cluster_id)

        elif request.tool_name == "start_cluster":
            cluster_id = request.arguments.get("cluster_id", "")
            result = await start_cluster(cluster_id)

        elif request.tool_name == "create_cluster":
            cluster_name = request.arguments.get("cluster_name")
            node_type = request.arguments.get("node_type", "Standard_DS3_v2")
            num_workers = request.arguments.get("num_workers", 0)
            spark_version = request.arguments.get("spark_version", "13.3.x-scala2.12")
            autotermination_minutes = request.arguments.get("autotermination_minutes", 120)

            if not cluster_name:
                return {"result": json.dumps({"error": "Missing required field: cluster_name"})}

            result = await create_cluster(cluster_name, node_type, num_workers, spark_version, autotermination_minutes)

        elif request.tool_name == "list_jobs":
            limit = request.arguments.get("limit", 25)
            result = await list_jobs(limit)

        elif request.tool_name == "run_job":
            job_id = request.arguments.get("job_id")
            parameters = request.arguments.get("parameters", {})

            if not job_id:
                return {"result": json.dumps({"error": "Missing required field: job_id"})}

            result = await run_job(job_id, parameters)

        elif request.tool_name == "get_job_run_status":
            run_id = request.arguments.get("run_id")

            if not run_id:
                return {"result": json.dumps({"error": "Missing required field: run_id"})}

            result = await get_job_run_status(run_id)

        else:
            error_msg = f"Unknown tool: {request.tool_name}"
            print(f"❌ {error_msg}")
            return {"result": json.dumps({"error": error_msg})}

        print(f"✅ Execution complete")
        return {"result": json.dumps(result, indent=2)}

    except Exception as e:
        error_msg = f"Error executing {request.tool_name}: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return {"result": json.dumps({"error": error_msg})}

@app.get("/health")
async def health():
    """Health check"""
    api_configured = bool(DATABRICKS_HOST and DATABRICKS_TOKEN)

    # Test API if configured
    api_working = False
    if api_configured:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{DATABRICKS_HOST}/api/2.0/clusters/list",
                    headers=get_headers(),
                    timeout=5.0
                )
                api_working = response.status_code == 200
        except:
            pass

    return {
        "status": "healthy",
        "api_configured": api_configured,
        "api_working": api_working,
        "databricks_host": DATABRICKS_HOST if DATABRICKS_HOST else "Not configured",
        "default_cluster": DATABRICKS_CLUSTER_ID if DATABRICKS_CLUSTER_ID else "Not set",
        "available_tools": [
            "execute_sql", "list_tables", "get_table_schema",
            "run_notebook", "list_clusters", "get_cluster_status",
            "start_cluster", "list_jobs", "run_job", "get_job_run_status"
        ]
    }

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("📊 Starting Databricks MCP Server")
    print("=" * 60)
    print(f"Host: {DATABRICKS_HOST if DATABRICKS_HOST else '❌ Not configured'}")
    print(f"Token: {'✅ Configured' if DATABRICKS_TOKEN else '❌ Missing'}")
    print(f"Cluster: {DATABRICKS_CLUSTER_ID if DATABRICKS_CLUSTER_ID else '❌ Not set'}")
    print(f"Port: 8085")
    print("=" * 60)

    if not DATABRICKS_HOST or not DATABRICKS_TOKEN:
        print("\n⚠️  WARNING: Databricks credentials not configured")
        print("\nSetup Instructions:")
        print("1. Get your Databricks workspace URL")
        print("2. Create a personal access token:")
        print("   - User Settings → Developer → Access Tokens → Generate New Token")
        print("3. (Optional) Get a cluster ID from your workspace")
        print("\n4. Add to .env file:")
        print("   DATABRICKS_HOST=https://adb-xxxx.azuredatabricks.net")
        print("   DATABRICKS_TOKEN=your-token-here")
        print("   DATABRICKS_CLUSTER_ID=your-cluster-id  # Optional")
        print("   DATABRICKS_WAREHOUSE_ID=your-warehouse-id  # Optional for SQL")
        print("\nDocs: https://docs.databricks.com/dev-tools/auth.html")

    uvicorn.run(app, host="0.0.0.0", port=8100)
