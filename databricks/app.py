#!/usr/bin/env python3
"""
Databricks Terminal Bot
AI-powered terminal interface for Databricks using MCP
"""

import os
import sys
import json
import time
import subprocess
import webbrowser
import httpx
from typing import Optional, Any
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import StructuredTool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
# Use pydantic v1 for LangChain compatibility
from pydantic.v1 import BaseModel as BaseModelV1, Field as FieldV1, create_model as create_model_v1

load_dotenv()

# Configuration
MCP_SERVER_URL = os.getenv("MCP_DATABRICKS_URL", "http://localhost:8099")

# Initialize Azure OpenAI
llm = AzureChatOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    temperature=0
)

def call_mcp_tool(tool_name: str, arguments: dict) -> str:
    """Call MCP server tool"""
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{MCP_SERVER_URL}/execute",
                json={"tool_name": tool_name, "arguments": arguments}
            )
            response.raise_for_status()
            result = response.json()
            return result.get("result", json.dumps(result))
    except Exception as e:
        return json.dumps({"error": str(e)})

def get_dynamic_tools():
    """Fetch dynamically evolved tools from MCP server"""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{MCP_SERVER_URL}/evolve/tools")
            if response.status_code == 200:
                data = response.json()
                return data.get("dynamic_tools", [])
    except:
        pass
    return []

def create_dynamic_tool_wrapper(tool_name: str):
    """Create a wrapper function for a dynamic tool"""
    def wrapper(**kwargs) -> str:
        return call_mcp_tool(tool_name, kwargs)
    wrapper.__name__ = tool_name
    return wrapper

def create_pydantic_model_from_schema(tool_name: str, input_schema: dict) -> type:
    """Create a Pydantic v1 model dynamically from inputSchema (required by LangChain)"""
    properties = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))

    field_definitions = {}
    for prop_name, prop_def in properties.items():
        prop_type = prop_def.get("type", "string")
        description = prop_def.get("description", "")
        default = prop_def.get("default", None)

        # Map JSON schema types to Python types
        type_mapping = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        python_type = type_mapping.get(prop_type, str)

        # If required, no default; otherwise use provided default or None
        # Use pydantic v1 Field for LangChain compatibility
        if prop_name in required:
            field_definitions[prop_name] = (python_type, FieldV1(description=description))
        else:
            field_definitions[prop_name] = (Optional[python_type], FieldV1(default=default, description=description))

    # Create dynamic model using pydantic v1 create_model
    model_name = f"{tool_name.title().replace('_', '')}Args"
    return create_model_v1(model_name, __base__=BaseModelV1, **field_definitions)

def refresh_tools():
    """Refresh tool list with any newly evolved tools"""
    global tools, agent, agent_executor, prompt, memory

    # Skip if tools list doesn't exist yet
    try:
        _ = tools
        _ = prompt
        _ = memory
    except NameError:
        return 0

    dynamic_tool_defs = get_dynamic_tools()
    if not dynamic_tool_defs:
        return 0

    new_tools = list(tools)  # Copy existing static tools
    existing_names = {t.name for t in tools}
    added_count = 0

    for tool_def in dynamic_tool_defs:
        if tool_def["name"] not in existing_names:
            wrapper = create_dynamic_tool_wrapper(tool_def["name"])

            # Create Pydantic model from inputSchema for proper arg handling
            input_schema = tool_def.get("inputSchema", {})
            args_schema = create_pydantic_model_from_schema(tool_def["name"], input_schema)

            new_tool = StructuredTool.from_function(
                func=wrapper,
                name=tool_def["name"],
                description=tool_def.get("description", "") + " [EVOLVED]",
                args_schema=args_schema
            )
            new_tools.append(new_tool)
            existing_names.add(tool_def["name"])
            added_count += 1

    if added_count > 0:
        tools = new_tools
        agent = create_openai_functions_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, memory=memory, verbose=True, handle_parsing_errors=True)
        return added_count
    return 0

# Tool wrapper functions
def execute_sql_func(query: str) -> str:
    """Execute SQL query on Databricks"""
    return call_mcp_tool("execute_sql", {"query": query})

def evolve_discover_func() -> str:
    """Discover and add new Databricks API capabilities. Use this when you can't find the right tool."""
    result = call_mcp_tool("evolve_discover", {})

    # Immediately refresh tools so they're available in this session
    try:
        new_count = refresh_tools()
        if new_count > 0:
            return f"{result}\n\n✓ SUCCESS: {new_count} new tools added! Use evolve_list to see them, then use the appropriate tool."
    except:
        pass

    return f"{result}\n\nNew tools discovered! Use evolve_list to see available tools, then use the appropriate one."

def evolve_list_func() -> str:
    """List all dynamically evolved tools"""
    return call_mcp_tool("evolve_list", {})

def list_databases_func() -> str:
    """List all databases in Databricks"""
    return call_mcp_tool("list_databases", {})

def list_tables_func(database_schema: str = "default") -> str:
    """List all tables in a database schema"""
    return call_mcp_tool("list_tables", {"schema": database_schema})

def get_table_schema_func(table_name: str, database_schema: str = "default") -> str:
    """Get columns of a table"""
    return call_mcp_tool("get_table_schema", {"table_name": table_name, "schema": database_schema})

def list_clusters_func() -> str:
    """List all Databricks clusters"""
    return call_mcp_tool("list_clusters", {})

def get_cluster_status_func(cluster_id: str = "") -> str:
    """Get status of a cluster"""
    return call_mcp_tool("get_cluster_status", {"cluster_id": cluster_id})

def start_cluster_func(cluster_id: str = "") -> str:
    """Start a stopped cluster"""
    return call_mcp_tool("start_cluster", {"cluster_id": cluster_id})

def list_jobs_func(limit: int = 25) -> str:
    """List all Databricks jobs"""
    return call_mcp_tool("list_jobs", {"limit": limit})

def run_job_func(job_id: int) -> str:
    """Run a Databricks job"""
    return call_mcp_tool("run_job", {"job_id": job_id})

def run_notebook_func(notebook_path: str) -> str:
    """Run a Databricks notebook"""
    return call_mcp_tool("run_notebook", {"notebook_path": notebook_path})

def stop_cluster_func(cluster_id: str = "") -> str:
    """Stop a running cluster"""
    return call_mcp_tool("stop_cluster", {"cluster_id": cluster_id})

def get_job_run_status_func(run_id: int) -> str:
    """Get status of a job run"""
    return call_mcp_tool("get_job_run_status", {"run_id": run_id})

def cancel_job_run_func(run_id: int) -> str:
    """Cancel a running job"""
    return call_mcp_tool("cancel_job_run", {"run_id": run_id})

def list_notebooks_func(path: str = "/") -> str:
    """List notebooks in workspace"""
    return call_mcp_tool("list_notebooks", {"path": path})

def get_table_preview_func(table_name: str, limit: int = 10) -> str:
    """Preview first N rows of a table"""
    return call_mcp_tool("get_table_preview", {"table_name": table_name, "limit": limit})

def get_table_stats_func(table_name: str) -> str:
    """Get table statistics"""
    return call_mcp_tool("get_table_stats", {"table_name": table_name})

def list_catalogs_func() -> str:
    """List Unity Catalog catalogs"""
    return call_mcp_tool("list_catalogs", {})

def search_tables_func(pattern: str) -> str:
    """Search tables by name pattern"""
    return call_mcp_tool("search_tables", {"pattern": pattern})

def get_cluster_logs_func(cluster_id: str = "") -> str:
    """Get cluster event logs"""
    return call_mcp_tool("get_cluster_logs", {"cluster_id": cluster_id})

def list_workspace_folders_func(path: str = "/") -> str:
    """List folders in workspace path"""
    return call_mcp_tool("list_workspace_folders", {"path": path})

def find_notebooks_func(path: str = "/") -> str:
    """Find all notebooks recursively in a path"""
    return call_mcp_tool("find_notebooks", {"path": path})

# Create tools
tools = [
    StructuredTool.from_function(
        func=execute_sql_func,
        name="execute_sql",
        description="Execute SQL query on Databricks. Use this for any data queries, SELECT, SHOW, etc."
    ),
    StructuredTool.from_function(
        func=list_databases_func,
        name="list_databases",
        description="List all databases/schemas in Databricks"
    ),
    StructuredTool.from_function(
        func=list_tables_func,
        name="list_tables",
        description="List all tables in a database/schema"
    ),
    StructuredTool.from_function(
        func=get_table_schema_func,
        name="get_table_schema",
        description="Get schema/columns of a table"
    ),
    StructuredTool.from_function(
        func=list_clusters_func,
        name="list_clusters",
        description="List all available Databricks clusters"
    ),
    StructuredTool.from_function(
        func=get_cluster_status_func,
        name="get_cluster_status",
        description="Get status of a cluster"
    ),
    StructuredTool.from_function(
        func=start_cluster_func,
        name="start_cluster",
        description="Start a stopped cluster"
    ),
    StructuredTool.from_function(
        func=list_jobs_func,
        name="list_jobs",
        description="List all Databricks jobs"
    ),
    StructuredTool.from_function(
        func=run_job_func,
        name="run_job",
        description="Run a Databricks job by ID"
    ),
    StructuredTool.from_function(
        func=run_notebook_func,
        name="run_notebook",
        description="Run a Databricks notebook"
    ),
    StructuredTool.from_function(
        func=stop_cluster_func,
        name="stop_cluster",
        description="Stop a running cluster"
    ),
    StructuredTool.from_function(
        func=get_job_run_status_func,
        name="get_job_run_status",
        description="Get status of a job run by run_id"
    ),
    StructuredTool.from_function(
        func=cancel_job_run_func,
        name="cancel_job_run",
        description="Cancel a running job by run_id"
    ),
    StructuredTool.from_function(
        func=list_notebooks_func,
        name="list_notebooks",
        description="List all items (folders and notebooks) in a specific workspace path - does NOT search recursively"
    ),
    StructuredTool.from_function(
        func=get_table_preview_func,
        name="get_table_preview",
        description="Preview first N rows of a table"
    ),
    StructuredTool.from_function(
        func=get_table_stats_func,
        name="get_table_stats",
        description="Get table statistics (row count, size)"
    ),
    StructuredTool.from_function(
        func=list_catalogs_func,
        name="list_catalogs",
        description="List all Unity Catalog catalogs"
    ),
    StructuredTool.from_function(
        func=search_tables_func,
        name="search_tables",
        description="Search for tables by name pattern (e.g., 'sales*')"
    ),
    StructuredTool.from_function(
        func=get_cluster_logs_func,
        name="get_cluster_logs",
        description="Get recent event logs from a cluster"
    ),
    StructuredTool.from_function(
        func=list_workspace_folders_func,
        name="list_workspace_folders",
        description="List folders/directories in a workspace path"
    ),
    StructuredTool.from_function(
        func=find_notebooks_func,
        name="find_notebooks",
        description="Find and list all NOTEBOOKS with their names by searching recursively. Use this when user asks to 'list notebooks', 'show notebooks', 'find notebooks' or 'what notebooks exist'"
    ),
    # Self-evolution tools
    StructuredTool.from_function(
        func=evolve_discover_func,
        name="evolve_discover",
        description="SELF-EVOLVE: Discover and add NEW Databricks API capabilities. Use this when you can't find the right tool for a task, or when user asks for something you don't have a tool for. This will scan for new APIs and add them as tools."
    ),
    StructuredTool.from_function(
        func=evolve_list_func,
        name="evolve_list",
        description="List all dynamically evolved/discovered tools"
    )
]

# Load any previously evolved dynamic tools on startup
def load_dynamic_tools_on_startup():
    """Load evolved tools that were saved from previous sessions"""
    dynamic_tool_defs = get_dynamic_tools()
    if not dynamic_tool_defs:
        return 0

    existing_names = {t.name for t in tools}
    added_count = 0

    for tool_def in dynamic_tool_defs:
        if tool_def["name"] not in existing_names:
            wrapper = create_dynamic_tool_wrapper(tool_def["name"])

            # Create Pydantic model from inputSchema for proper arg handling
            input_schema = tool_def.get("inputSchema", {})
            args_schema = create_pydantic_model_from_schema(tool_def["name"], input_schema)

            new_tool = StructuredTool.from_function(
                func=wrapper,
                name=tool_def["name"],
                description=tool_def.get("description", "") + " [EVOLVED]",
                args_schema=args_schema
            )
            tools.append(new_tool)
            existing_names.add(tool_def["name"])
            added_count += 1

    if added_count > 0:
        print(f"  Loaded {added_count} evolved tools from server")
    return added_count

# Try to load dynamic tools (may fail if server not running yet)
try:
    load_dynamic_tools_on_startup()
except:
    pass

# Create agent prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a SELF-EVOLVING Databricks assistant with automatic capability discovery.

CURRENT TOOLS (built-in):
- execute_sql, list_databases, list_tables, get_table_schema
- list_clusters, get_cluster_status, start_cluster, stop_cluster
- list_jobs, run_job, get_job_run_status, cancel_job_run
- list_notebooks, find_notebooks, run_notebook
- search_tables, get_table_preview, get_table_stats, list_catalogs
- evolve_discover (CRITICAL - adds new capabilities)
- evolve_list (see evolved tools)

MANDATORY SELF-EVOLUTION RULE:
If the user asks for ANY of these, you MUST call evolve_discover FIRST:
- Create/edit/resize/restart/delete cluster → evolve for cluster_create, cluster_edit, etc.
- DBFS files (list, read, write, delete) → evolve for dbfs_list, dbfs_read, etc.
- MLflow (experiments, models, runs) → evolve for mlflow_* tools
- Git repos → evolve for repos_* tools
- Serving endpoints → evolve for serving_* tools
- Pipelines/DLT → evolve for pipelines_* tools
- Secrets → evolve for secrets_* tools
- Workspace import/export → evolve for workspace_* tools
- Node types, Spark versions → evolve for cluster_list_node_types, cluster_spark_versions

WORKFLOW - ALWAYS FOLLOW:
1. User asks for something
2. Check: Do I have the exact tool?
3. If NO → IMMEDIATELY call evolve_discover
4. Then call evolve_list to see new tools
5. Use the appropriate tool (it will now exist!)
6. Return results to user

NEVER say "I don't have that capability" without calling evolve_discover first!
NEVER suggest using the UI when you can evolve and do it!

After evolution, new tools are available like:
- cluster_create: Create new cluster
- cluster_restart: Restart cluster
- dbfs_list: List DBFS files
- mlflow_list_experiments: List MLflow experiments
- serving_list_endpoints: List model endpoints
- And many more...

Always provide clear, formatted responses with the results."""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

# Create memory and agent
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
agent = create_openai_functions_agent(llm, tools, prompt)
# Set verbose=True to see tool calls for debugging
agent_executor = AgentExecutor(agent=agent, tools=tools, memory=memory, verbose=True, handle_parsing_errors=True)

def check_mcp_server():
    """Check if MCP server is running"""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{MCP_SERVER_URL}/health")
            return response.status_code == 200
    except:
        return False

def main():
    """Main terminal interface"""
    print("=" * 60)
    print("  Databricks Terminal Bot - SELF-EVOLVING")
    print("=" * 60)
    print()

    # Check MCP server
    if check_mcp_server():
        print("  MCP Server: Connected")
    else:
        print("  MCP Server: Not running!")
        print()
        print("  Start the MCP server first:")
        print("    python mcp_server.py")
        print()
        return

    print()
    print("  Commands:")
    print("    Type your question or command")
    print("    'evolve' - Trigger self-evolution to add new capabilities")
    print("    'tools' - List all available tools")
    print("    'quit' or 'exit' to quit")
    print("    'clear' to clear conversation history")
    print()
    print("=" * 60)
    print()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break

            if user_input.lower() == 'clear':
                memory.clear()
                print("\nConversation cleared.\n")
                continue

            if user_input.lower() == 'evolve':
                print("\nBot: Initiating self-evolution...")
                result = call_mcp_tool("evolve_discover", {})
                print(f"Evolution result: {result}")
                new_count = refresh_tools()
                if new_count > 0:
                    print(f"Added {new_count} new tools to the agent!")
                print(f"Total tools available: {len(tools)}\n")
                continue

            if user_input.lower() == 'tools':
                print("\nBot: Available tools:")
                for i, tool in enumerate(tools, 1):
                    evolved = " [EVOLVED]" if "[EVOLVED]" in tool.description or "[AUTO-EVOLVED]" in tool.description else ""
                    print(f"  {i}. {tool.name}{evolved}")
                print()
                continue

            print()
            print("Bot: ", end="", flush=True)

            try:
                # Pre-check for any new tools before processing
                pre_refresh = refresh_tools()
                if pre_refresh > 0:
                    print(f"[Loaded {pre_refresh} evolved tools]")

                response = agent_executor.invoke({"input": user_input})
                output = response.get("output", "No response")
                print(output)

                # Post-check: refresh tools after interaction in case evolve was called
                post_refresh = refresh_tools()
                if post_refresh > 0:
                    print(f"\n[System: +{post_refresh} new tools added via evolution]")
                    print("[System: You can now use these new capabilities!]")

            except Exception as e:
                error_msg = str(e)
                print(f"Error: {error_msg}")
                # If error might be related to missing capability, suggest evolving
                if "tool" in error_msg.lower() or "function" in error_msg.lower():
                    print("\nTip: Try typing 'evolve' to add new capabilities")

            print()

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except EOFError:
            print("\n\nGoodbye!")
            break

def start_ui():
    """Start MCP server + Flask UI and open browser."""
    base = os.path.dirname(os.path.abspath(__file__))

    print("=" * 50)
    print("  DXC Databricks Assistant - Web UI Mode")
    print("=" * 50)

    # Start MCP server if not already running
    if not check_mcp_server():
        print("  Starting MCP server...")
        subprocess.Popen(
            [sys.executable, os.path.join(base, "mcp_server.py")],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Wait up to 10s for it to come up
        for _ in range(20):
            time.sleep(0.5)
            if check_mcp_server():
                print("  MCP Server: Ready")
                break
        else:
            print("  MCP Server: Failed to start (continuing anyway)")
    else:
        print("  MCP Server: Already running")

    port = int(os.getenv("PORT", 5055))
    print(f"  Opening http://localhost:{port} ...")
    print("=" * 50)

    # Only open browser in local mode (not in Docker/Azure)
    if not os.getenv("WEBSITE_INSTANCE_ID"):  # Azure sets this
        webbrowser.open(f"http://localhost:{port}")

    # Start Flask
    from ui import app as flask_app
    port = int(os.getenv("PORT", 5055))
    flask_app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    if "--ui" in sys.argv:
        start_ui()
    else:
        main()
