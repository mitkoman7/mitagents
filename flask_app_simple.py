from flask import Flask, render_template_string, request, jsonify, session as flask_session
import httpx
import os
import json
from dotenv import load_dotenv
import uuid

# LangChain imports
try:
    from langchain_openai import AzureChatOpenAI
    from langchain.agents import AgentExecutor, create_openai_functions_agent
    from langchain.tools import StructuredTool
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain.memory import ConversationBufferMemory
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  LangChain not available: {e}")
    LANGCHAIN_AVAILABLE = False

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your-secret-key-change-in-production")

MCP_SOCCER_URL = os.getenv("MCP_SOCCER_URL", "http://localhost:8081")
MCP_GOOGLE_URL = os.getenv("MCP_GOOGLE_URL", "http://localhost:8082")
MCP_MAPS_URL = os.getenv("MCP_MAPS_URL", "http://localhost:8083")
MCP_TOMTOM_URL = os.getenv("MCP_TOMTOM_URL", "http://localhost:8084")
MCP_DATABRICKS_URL = os.getenv("MCP_DATABRICKS_URL", "http://localhost:8085")
MCP_AZURE_URL = os.getenv("MCP_AZURE_URL", "http://localhost:8086")

# Initialize LangChain with Memory
LANGCHAIN_CONNECTED = False
AGENT_INITIALIZED = False

if LANGCHAIN_AVAILABLE:
    try:
        llm = AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            temperature=0
        )
        
        # Test connection
        llm.invoke("test")
        LANGCHAIN_CONNECTED = True
        print("✅ LangChain connected!")
    except Exception as e:
        print(f"⚠️  LangChain connection failed: {e}")

# Store memories per session
conversation_memories = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>ADDOF</title>
    <style>
        * {
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 0;
            height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            overflow: hidden;
        }
        .container {
            background: white;
            padding: 15px;
            height: 100vh;
            display: flex;
            flex-direction: column;
            box-shadow: none;
            max-width: 100%;
        }
        h1 {
            color: #333;
            text-align: center;
            margin: 0 0 8px 0;
            font-size: 1.5em;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin: 0 0 10px 0;
            font-size: 0.9em;
        }
        .memory-badge {
            display: inline-block;
            padding: 4px 12px;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 10px;
        }
        .memory-info {
            background: #e3f2fd;
            padding: 8px 12px;
            border-radius: 8px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-shrink: 0;
        }
        .memory-info-text {
            color: #1976d2;
            font-size: 14px;
        }
        .clear-memory-btn {
            padding: 6px 12px;
            background: #dc3545;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 12px;
        }
        .clear-memory-btn:hover {
            background: #c82333;
        }
        .status-section {
            background: #f8f9fa;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 10px;
            flex-shrink: 0;
            max-height: 150px;
            overflow-y: auto;
        }
        .status-item {
            display: flex;
            justify-content: space-between;
            padding: 4px 0;
            font-size: 0.85em;
        }
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
        }
        .status-dot.connected { background: #28a745; }
        .status-dot.disconnected { background: #dc3545; }
        .chat-box {
            border: 1px solid #ddd;
            padding: 15px;
            flex: 1;
            overflow-y: auto;
            margin-bottom: 10px;
            border-radius: 8px;
            background: #fafafa;
            min-height: 0;
        }
        .message { 
            margin: 12px 0; 
            padding: 12px 16px; 
            border-radius: 8px; 
            white-space: pre-wrap; 
            line-height: 1.5;
        }
        .user-message { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin-left: 20%;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .assistant-message { 
            background: white;
            border: 1px solid #e0e0e0;
            margin-right: 20%;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        .input-area {
            display: flex;
            gap: 10px;
            flex-shrink: 0;
            padding-bottom: 5px;
        }
        input {
            flex: 1;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            min-width: 0;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            white-space: nowrap;
        }
        button:hover {
            opacity: 0.9;
        }

        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            h1 {
                font-size: 1.2em;
            }
            .subtitle {
                font-size: 0.8em;
            }
            .status-item {
                font-size: 0.75em;
            }
            input {
                font-size: 12px;
                padding: 10px;
            }
            button {
                padding: 10px 20px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 ADDOF
            {% if langchain_connected %}
            <span class="memory-badge">🧠 With Memory</span>
            {% endif %}
        </h1>
        <p class="subtitle">Remembers your conversation context!</p>
        
        <div class="memory-info">
            <span class="memory-info-text">💬 <strong id="messageCount">0</strong> messages in memory</span>
            <button class="clear-memory-btn" onclick="clearMemory()">🗑️ Clear Memory</button>
        </div>
        
        <div class="status-section">
            <div class="status-item">
                <span><span class="status-dot {{ 'connected' if langchain_connected else 'disconnected' }}" id="langchainDot"></span>🦜 LangChain + Memory</span>
                <span id="langchainStatus">{{ '✓ Active' if langchain_connected else '✗ Not Active' }}</span>
            </div>
            <div class="status-item">
                <span><span class="status-dot" id="soccerDot"></span>⚽ Soccer Data</span>
                <span id="soccerStatus">Checking...</span>
            </div>
            <div class="status-item">
                <span><span class="status-dot" id="gmailDot"></span>📧 Gmail</span>
                <span id="gmailStatus">Checking...</span>
            </div>
            <div class="status-item">
                <span><span class="status-dot" id="tomtomDot"></span>🗺️ TomTom Maps (FREE)</span>
                <span id="tomtomStatus">Checking...</span>
            </div>
            <div class="status-item">
                <span><span class="status-dot" id="databricksDot"></span>📊 Databricks</span>
                <span id="databricksStatus">Checking...</span>
            </div>
            <div class="status-item">
                <span><span class="status-dot" id="azureDot"></span>☁️ Azure</span>
                <span id="azureStatus">Checking...</span>
            </div>
        </div>
        
        <div class="chat-box" id="chatBox"></div>
        
        <div class="input-area">
            <input type="text" id="userInput" placeholder="Ask me anything (I'll remember!)..." onkeypress="if(event.key==='Enter') sendMessage()">
            <button onclick="sendMessage()">Send</button>
        </div>
    </div>
    <script>
        let messageCount = 0;
        
        checkStatus();
        
        async function checkStatus() {
            try {
                const response = await fetch('/health');
                const data = await response.json();
                
                if (data.soccer_ok) {
                    document.getElementById('soccerDot').classList.add('connected');
                    document.getElementById('soccerStatus').textContent = '✓ Connected';
                } else {
                    document.getElementById('soccerDot').classList.add('disconnected');
                    document.getElementById('soccerStatus').textContent = '✗ Not running';
                }
                
                if (data.gmail_ok) {
                    document.getElementById('gmailDot').classList.add('connected');
                    document.getElementById('gmailStatus').textContent = '✓ Configured';
                } else {
                    document.getElementById('gmailDot').classList.add('disconnected');
                    document.getElementById('gmailStatus').textContent = '✗ Not configured';
                }
                
                if (data.tomtom_ok) {
                    document.getElementById('tomtomDot').classList.add('connected');
                    document.getElementById('tomtomStatus').textContent = '✓ Connected (FREE)';
                } else {
                    document.getElementById('tomtomDot').classList.add('disconnected');
                    document.getElementById('tomtomStatus').textContent = '✗ Not running';
                }

                if (data.databricks_ok) {
                    document.getElementById('databricksDot').classList.add('connected');
                    document.getElementById('databricksStatus').textContent = '✓ Connected';
                } else {
                    document.getElementById('databricksDot').classList.add('disconnected');
                    document.getElementById('databricksStatus').textContent = '✗ Not configured';
                }

                if (data.azure_ok) {
                    document.getElementById('azureDot').classList.add('connected');
                    document.getElementById('azureStatus').textContent = '✓ Connected';
                } else {
                    document.getElementById('azureDot').classList.add('disconnected');
                    document.getElementById('azureStatus').textContent = '✗ Not configured';
                }
            } catch (error) {
                console.error('Status check failed:', error);
            }
        }
        
        function setQuery(text) { 
            const cleanText = text.replace(/<span[^>]*>.*?<\/span>/g, '').trim();
            document.getElementById('userInput').value = cleanText; 
        }
        
        async function sendMessage() {
            const input = document.getElementById('userInput');
            const message = input.value.trim();
            if (!message) return;
            
            addMessage(message, 'user');
            input.value = '';
            messageCount++;
            updateMessageCount();
            
            const loadingId = addMessage('🤔 Thinking...', 'assistant');
            
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ message: message })
                });
                
                const data = await response.json();
                document.getElementById(loadingId).remove();
                addMessage(data.response, 'assistant');
                messageCount++;
                updateMessageCount();
            } catch (error) {
                document.getElementById(loadingId).remove();
                addMessage('❌ Error: ' + error.message, 'assistant');
            }
        }
        
        async function clearMemory() {
            if (confirm('Clear conversation memory?')) {
                try {
                    await fetch('/clear-memory', { method: 'POST' });
                    messageCount = 0;
                    updateMessageCount();
                    document.getElementById('chatBox').innerHTML = '';
                    addMessage('Memory cleared! Starting fresh conversation.', 'assistant');
                } catch (error) {
                    alert('Failed to clear memory');
                }
            }
        }
        
        function updateMessageCount() {
            document.getElementById('messageCount').textContent = messageCount;
        }
        
        function addMessage(text, sender) {
            const chatBox = document.getElementById('chatBox');
            const messageDiv = document.createElement('div');
            const id = 'msg-' + Date.now();
            messageDiv.id = id;
            messageDiv.className = `message ${sender}-message`;
            messageDiv.textContent = text;
            chatBox.appendChild(messageDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
            return id;
        }
    </script>
</body>
</html>
"""

# Helper function - keep your exact approach
def execute_tool_direct(tool_name, arguments):
    """Your original working approach - kept exactly the same"""
    google_tools = ["send_email", "send_email_with_data", "email_me"]
    maps_tools = ["search_places", "get_directions", "calculate_distance", "get_place_details", "nearby_search"]
    tomtom_tools = ["search_places_tomtom", "get_directions_tomtom", "calculate_distance_tomtom", "get_traffic_info", "nearby_search_tomtom"]
    databricks_tools = ["natural_language_query", "execute_sql", "list_databases", "list_tables", "get_table_schema", "run_notebook", "list_clusters", "get_cluster_status", "start_cluster", "list_jobs", "run_job", "get_job_run_status", "create_cluster"]
    azure_tools = ["list_resource_groups", "list_vms", "get_vm_status", "start_vm", "stop_vm", "restart_vm", "list_storage_accounts", "list_databases_azure", "get_subscription_info", "list_resources", "create_storage_account"]

    if tool_name in google_tools:
        server_url = MCP_GOOGLE_URL
    elif tool_name in tomtom_tools:
        server_url = MCP_TOMTOM_URL
        # Remove _tomtom suffix for actual API call
        tool_name = tool_name.replace("_tomtom", "")
    elif tool_name in azure_tools:
        server_url = MCP_AZURE_URL
        # Handle naming conflict with databricks list_databases
        if tool_name == "list_databases_azure":
            tool_name = "list_databases"
    elif tool_name in databricks_tools:
        server_url = MCP_DATABRICKS_URL
    elif tool_name in maps_tools:
        server_url = MCP_MAPS_URL
    else:
        server_url = MCP_SOCCER_URL
    
    try:
        print(f"🔧 Executing tool: {tool_name}")
        print(f"📦 Arguments: {arguments}")
        
        with httpx.Client(timeout=30.0) as http_client:
            response = http_client.post(
                f"{server_url}/execute",
                json={"tool_name": tool_name, "arguments": arguments}
            )
            result = response.json()["result"]
            print(f"✅ Tool result received")
            return result
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        return json.dumps({"error": error_msg})

# Initialize agent with memory
if LANGCHAIN_CONNECTED:
    try:
        # Create tools manually with explicit schemas
        tools = []
        
        # Soccer tools
        def get_latest_results_func(league: str = "PL", days: int = 3):
            """Get latest soccer match results"""
            return execute_tool_direct("get_latest_results", {"league": league, "days": days})
        
        def get_team_recent_matches_func(team_name: str):
            """Get recent matches for a specific team"""
            if not team_name:
                return json.dumps({"error": "team_name is required"})
            return execute_tool_direct("get_team_recent_matches", {"team_name": team_name})
        
        def get_league_standings_func(league: str = "PL"):
            """Get current league standings"""
            return execute_tool_direct("get_league_standings", {"league": league})
        
        # Email tool
        def email_me_func(subject: str, data: str, message: str = "Here is the data you requested:"):
            """Send data to user's own email (mitkoman@gmail.com)"""
            if not subject or not data:
                return json.dumps({"error": "subject and data are required"})
            return execute_tool_direct("email_me", {"subject": subject, "data": data, "message": message})
        
        def send_email_func(to: str, subject: str, body: str, is_html: bool = False):
            """Send email to any email address. Requires to, subject, and body parameters."""
            if not to or not subject or not body:
                return json.dumps({"error": "to, subject, and body are required"})
            return execute_tool_direct("send_email", {"to": to, "subject": subject, "body": body, "is_html": is_html})
        
        # Maps tools
        def search_places_func(query: str, radius: int = 5000):
            """Search for places like restaurants, hotels, shops"""
            if not query:
                return json.dumps({"error": "query is required"})
            return execute_tool_direct("search_places", {"query": query, "radius": radius})
        
        def get_directions_func(origin: str, destination: str, mode: str = "driving"):
            """Get turn-by-turn directions between two locations. Mode can be: driving, walking, bicycling, transit"""
            if not origin or not destination:
                return json.dumps({"error": "origin and destination are required"})
            return execute_tool_direct("get_directions", {"origin": origin, "destination": destination, "mode": mode})
        
        def calculate_distance_func(origin: str, destination: str, mode: str = "driving"):
            """Calculate distance and travel time between two locations"""
            if not origin or not destination:
                return json.dumps({"error": "origin and destination are required"})
            return execute_tool_direct("calculate_distance", {"origin": origin, "destination": destination, "mode": mode})
        
        def get_place_details_func(place_name: str):
            """Get detailed information about a place including hours, reviews, and ratings"""
            if not place_name:
                return json.dumps({"error": "place_name is required"})
            return execute_tool_direct("get_place_details", {"place_name": place_name})
        
        def nearby_search_func(location: str, type: str, radius: int = 5000):
            """Find places of a specific type near a location. Type examples: restaurant, cafe, hotel, gas_station, bar"""
            if not location or not type:
                return json.dumps({"error": "location and type are required"})
            return execute_tool_direct("nearby_search", {"location": location, "type": type, "radius": radius})
        
        # TomTom tools (traffic-aware routing - FREE!)
        def get_directions_tomtom_func(origin: str, destination: str, traffic: bool = True):
            """Get directions with real-time TRAFFIC data (TomTom - better for traffic). Shows traffic delays and fuel consumption."""
            if not origin or not destination:
                return json.dumps({"error": "origin and destination are required"})
            return execute_tool_direct("get_directions_tomtom", {"origin": origin, "destination": destination, "traffic": traffic})
        
        def calculate_distance_tomtom_func(origin: str, destination: str):
            """Calculate distance and ETA with real-time TRAFFIC delays (TomTom - shows traffic impact)"""
            if not origin or not destination:
                return json.dumps({"error": "origin and destination are required"})
            return execute_tool_direct("calculate_distance_tomtom", {"origin": origin, "destination": destination})
        
        def get_traffic_info_func(location: str):
            """Get real-time traffic conditions for a location (TomTom). Shows congestion levels, current speeds, and delays."""
            if not location:
                return json.dumps({"error": "location is required"})
            return execute_tool_direct("get_traffic_info", {"location": location})

        # Databricks tools
        def natural_language_query_func(question: str, table_name: str = ""):
            """Convert natural language question to SQL and execute it on Databricks"""
            if not question:
                return json.dumps({"error": "question is required"})
            return execute_tool_direct("natural_language_query", {"question": question, "table_name": table_name})

        def execute_sql_func(query: str, warehouse_id: str = ""):
            """Execute SQL query on Databricks"""
            if not query:
                return json.dumps({"error": "query is required"})
            return execute_tool_direct("execute_sql", {"query": query, "warehouse_id": warehouse_id})

        def list_databases_func(catalog: str = "hive_metastore"):
            """List all databases/schemas in a Databricks catalog"""
            return execute_tool_direct("list_databases", {"catalog": catalog})

        def list_tables_func(catalog: str = "hive_metastore", db_schema: str = "default"):
            """List all tables in a Databricks database/schema"""
            return execute_tool_direct("list_tables", {"catalog": catalog, "schema": db_schema})

        def get_table_schema_func(table_name: str, catalog: str = "hive_metastore", db_schema: str = "default"):
            """Get schema/columns of a Databricks table"""
            if not table_name:
                return json.dumps({"error": "table_name is required"})
            return execute_tool_direct("get_table_schema", {"table_name": table_name, "catalog": catalog, "schema": db_schema})

        def run_notebook_func(notebook_path: str, parameters: dict = None, cluster_id: str = ""):
            """Run a Databricks notebook"""
            if not notebook_path:
                return json.dumps({"error": "notebook_path is required"})
            return execute_tool_direct("run_notebook", {"notebook_path": notebook_path, "parameters": parameters or {}, "cluster_id": cluster_id})

        def list_clusters_func():
            """List all Databricks clusters"""
            return execute_tool_direct("list_clusters", {})

        def get_cluster_status_func(cluster_id: str = ""):
            """Get Databricks cluster status"""
            return execute_tool_direct("get_cluster_status", {"cluster_id": cluster_id})

        def start_cluster_func(cluster_id: str = ""):
            """Start a stopped Databricks cluster"""
            return execute_tool_direct("start_cluster", {"cluster_id": cluster_id})

        def list_jobs_func(limit: int = 25):
            """List Databricks jobs"""
            return execute_tool_direct("list_jobs", {"limit": limit})

        def run_job_func(job_id: int, parameters: dict = None):
            """Run a Databricks job"""
            if not job_id:
                return json.dumps({"error": "job_id is required"})
            return execute_tool_direct("run_job", {"job_id": job_id, "parameters": parameters or {}})

        def get_job_run_status_func(run_id: int):
            """Get Databricks job run status"""
            if not run_id:
                return json.dumps({"error": "run_id is required"})
            return execute_tool_direct("get_job_run_status", {"run_id": run_id})

        def create_cluster_func(cluster_name: str, node_type: str = "Standard_D4ds_v5", num_workers: int = 0, spark_version: str = "16.4.x-cpu-ml-scala2.12", autotermination_minutes: int = 120):
            """Create a new Databricks cluster (Personal Compute policy compliant)"""
            if not cluster_name:
                return json.dumps({"error": "cluster_name is required"})
            return execute_tool_direct("create_cluster", {"cluster_name": cluster_name, "node_type": node_type, "num_workers": num_workers, "spark_version": spark_version, "autotermination_minutes": autotermination_minutes})

        # Azure tools
        def list_resource_groups_func():
            """List all Azure resource groups in subscription"""
            return execute_tool_direct("list_resource_groups", {})

        def list_vms_func(resource_group: str = ""):
            """List all Azure virtual machines"""
            return execute_tool_direct("list_vms", {"resource_group": resource_group})

        def get_vm_status_func(vm_name: str, resource_group: str = ""):
            """Get Azure VM power state and status"""
            if not vm_name:
                return json.dumps({"error": "vm_name is required"})
            return execute_tool_direct("get_vm_status", {"vm_name": vm_name, "resource_group": resource_group})

        def start_vm_func(vm_name: str, resource_group: str = ""):
            """Start a stopped Azure virtual machine"""
            if not vm_name:
                return json.dumps({"error": "vm_name is required"})
            return execute_tool_direct("start_vm", {"vm_name": vm_name, "resource_group": resource_group})

        def stop_vm_func(vm_name: str, resource_group: str = ""):
            """Stop Azure VM and deallocate (saves costs)"""
            if not vm_name:
                return json.dumps({"error": "vm_name is required"})
            return execute_tool_direct("stop_vm", {"vm_name": vm_name, "resource_group": resource_group})

        def restart_vm_func(vm_name: str, resource_group: str = ""):
            """Restart an Azure virtual machine"""
            if not vm_name:
                return json.dumps({"error": "vm_name is required"})
            return execute_tool_direct("restart_vm", {"vm_name": vm_name, "resource_group": resource_group})

        def list_storage_accounts_func(resource_group: str = ""):
            """List all Azure storage accounts"""
            return execute_tool_direct("list_storage_accounts", {"resource_group": resource_group})

        def list_databases_azure_func(resource_group: str = ""):
            """List all Azure SQL servers"""
            return execute_tool_direct("list_databases_azure", {"resource_group": resource_group})

        def get_subscription_info_func():
            """Get Azure subscription information"""
            return execute_tool_direct("get_subscription_info", {})

        def list_resources_func(resource_group: str = "", resource_type: str = ""):
            """List all Azure resources in a resource group"""
            return execute_tool_direct("list_resources", {"resource_group": resource_group, "resource_type": resource_type})

        def create_storage_account_func(storage_account_name: str, resource_group: str = "", location: str = "eastus", sku: str = "Standard_LRS", kind: str = "StorageV2"):
            """Create a new Azure storage account"""
            if not storage_account_name:
                return json.dumps({"error": "storage_account_name is required"})
            return execute_tool_direct("create_storage_account", {
                "storage_account_name": storage_account_name,
                "resource_group": resource_group,
                "location": location,
                "sku": sku,
                "kind": kind
            })

        # Create StructuredTools
        tools = [
            StructuredTool.from_function(
                func=get_latest_results_func,
                name="get_latest_results",
                description="Get latest soccer/football match results from a league. Use league codes: PL (Premier League), PD (La Liga), BL1 (Bundesliga), SA (Serie A), FL1 (Ligue 1). Default is PL."
            ),
            StructuredTool.from_function(
                func=get_team_recent_matches_func,
                name="get_team_recent_matches",
                description="Get recent matches for a specific team. You MUST provide the team_name parameter with the full team name like 'Arsenal', 'Liverpool', 'Manchester United', 'Chelsea', etc."
            ),
            StructuredTool.from_function(
                func=get_league_standings_func,
                name="get_league_standings",
                description="Get current league standings/table. Use league codes: PL, PD, BL1, SA, FL1. Default is PL."
            ),
            StructuredTool.from_function(
                func=email_me_func,
                name="email_me",
                description="Send data to the user's own email address (mitkoman@gmail.com). Use this when user says 'email me', 'send to me', etc. Requires subject and data parameters."
            ),
            StructuredTool.from_function(
                func=send_email_func,
                name="send_email",
                description="Send email to any email address that the user specifies. Use this when user provides a specific email address. Requires to (email address), subject, and body parameters."
            ),
            StructuredTool.from_function(
                func=search_places_func,
                name="search_places",
                description="Search for places like restaurants, hotels, coffee shops, bars, etc. Provide a search query like 'pizza restaurants in Manhattan' or 'hotels near Central Park'."
            ),
            StructuredTool.from_function(
                func=get_directions_func,
                name="get_directions",
                description="Get turn-by-turn directions between two locations. Specify origin and destination, and optionally mode (driving, walking, bicycling, transit)."
            ),
            StructuredTool.from_function(
                func=calculate_distance_func,
                name="calculate_distance",
                description="Calculate the distance and travel time between two locations. Great for answering 'how far' or 'how long' questions."
            ),
            StructuredTool.from_function(
                func=get_place_details_func,
                name="get_place_details",
                description="Get detailed information about a specific place including address, phone number, hours, website, rating, and reviews."
            ),
            StructuredTool.from_function(
                func=nearby_search_func,
                name="nearby_search",
                description="Find places of a specific type near a location. Use types like: restaurant, cafe, bar, hotel, gas_station, parking, etc."
            ),
            StructuredTool.from_function(
                func=get_directions_tomtom_func,
                name="get_directions_with_traffic",
                description="Get driving directions with REAL-TIME TRAFFIC delays and fuel consumption. Use this when user asks about traffic, current conditions, or wants traffic-aware routing."
            ),
            StructuredTool.from_function(
                func=calculate_distance_tomtom_func,
                name="calculate_distance_with_traffic",
                description="Calculate distance and travel time with REAL-TIME TRAFFIC impact. Shows delays and fuel consumption. Use for 'how long' or 'how far' questions with traffic."
            ),
            StructuredTool.from_function(
                func=get_traffic_info_func,
                name="get_traffic_info",
                description="Get REAL-TIME TRAFFIC conditions for a specific location. Shows congestion level (light/moderate/heavy/severe), current speeds, and delays. Use for 'what's the traffic' or 'traffic conditions' questions."
            ),
            StructuredTool.from_function(
                func=natural_language_query_func,
                name="natural_language_query",
                description="Convert natural language questions to SQL and execute on Databricks. Perfect for questions like '3 month attendance report', 'count employees by department', 'show records for Alice'. Automatically translates to SQL."
            ),
            StructuredTool.from_function(
                func=execute_sql_func,
                name="execute_sql",
                description="Execute raw SQL query on Databricks data warehouse. Use this when you have a specific SQL query to run."
            ),
            StructuredTool.from_function(
                func=list_databases_func,
                name="list_databases",
                description="List all databases/schemas in a Databricks catalog. Use this to discover available databases."
            ),
            StructuredTool.from_function(
                func=list_tables_func,
                name="list_tables",
                description="List all tables in a Databricks database/schema. Useful for discovering available datasets."
            ),
            StructuredTool.from_function(
                func=get_table_schema_func,
                name="get_table_schema",
                description="Get the schema/columns of a Databricks table. Use this to understand table structure before querying."
            ),
            StructuredTool.from_function(
                func=run_notebook_func,
                name="run_notebook",
                description="Execute a Databricks notebook with optional parameters. Use for running ETL jobs, ML models, or data processing."
            ),
            StructuredTool.from_function(
                func=list_clusters_func,
                name="list_clusters",
                description="List all Databricks compute clusters. Shows cluster names, IDs, and states."
            ),
            StructuredTool.from_function(
                func=get_cluster_status_func,
                name="get_cluster_status",
                description="Get the status of a Databricks cluster (running, stopped, etc.)."
            ),
            StructuredTool.from_function(
                func=start_cluster_func,
                name="start_cluster",
                description="Start a stopped Databricks cluster to enable computation."
            ),
            StructuredTool.from_function(
                func=list_jobs_func,
                name="list_jobs",
                description="List all Databricks jobs. Shows scheduled and on-demand data pipelines."
            ),
            StructuredTool.from_function(
                func=run_job_func,
                name="run_job",
                description="Trigger a Databricks job execution with optional parameters."
            ),
            StructuredTool.from_function(
                func=get_job_run_status_func,
                name="get_job_run_status",
                description="Check the status of a running or completed Databricks job."
            ),
            StructuredTool.from_function(
                func=create_cluster_func,
                name="create_cluster",
                description="Create a new Databricks cluster with specified configuration. Single-node by default (num_workers=0)."
            ),
            StructuredTool.from_function(
                func=list_resource_groups_func,
                name="list_resource_groups",
                description="List all Azure resource groups in your subscription. Use this to discover available resource groups."
            ),
            StructuredTool.from_function(
                func=list_vms_func,
                name="list_vms",
                description="List all Azure virtual machines. Optionally filter by resource group."
            ),
            StructuredTool.from_function(
                func=get_vm_status_func,
                name="get_vm_status",
                description="Get the power state and status of a specific Azure VM. Shows if it's running, stopped, or deallocated."
            ),
            StructuredTool.from_function(
                func=start_vm_func,
                name="start_vm",
                description="Start a stopped Azure virtual machine. VM will begin running and incur compute costs."
            ),
            StructuredTool.from_function(
                func=stop_vm_func,
                name="stop_vm",
                description="Stop and deallocate an Azure VM to save costs. VM will not incur compute charges when deallocated."
            ),
            StructuredTool.from_function(
                func=restart_vm_func,
                name="restart_vm",
                description="Restart an Azure virtual machine. Useful for applying updates or resolving issues."
            ),
            StructuredTool.from_function(
                func=list_storage_accounts_func,
                name="list_storage_accounts",
                description="List all Azure storage accounts. Optionally filter by resource group."
            ),
            StructuredTool.from_function(
                func=list_databases_azure_func,
                name="list_databases_azure",
                description="List all Azure SQL servers. Optionally filter by resource group. Different from Databricks databases."
            ),
            StructuredTool.from_function(
                func=get_subscription_info_func,
                name="get_subscription_info",
                description="Get information about your Azure subscription including name, ID, and state."
            ),
            StructuredTool.from_function(
                func=list_resources_func,
                name="list_resources",
                description="List all Azure resources in a resource group. Optionally filter by resource type (e.g., 'Microsoft.Compute/virtualMachines')."
            ),
            StructuredTool.from_function(
                func=create_storage_account_func,
                name="create_storage_account",
                description="Create a new Azure storage account. Name must be globally unique, 3-24 lowercase letters/numbers. Default SKU is Standard_LRS (locally redundant). Use for storing data, blobs, files, etc."
            )
        ]
        
        if tools:
            # Create prompt with memory
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a helpful AI assistant with memory. You remember the conversation history.

When users refer to previous information (like "those results", "that team", "send it"), use the conversation history to understand what they mean.

You have access to:
- Soccer data: Match results, team info, league standings
- Email: Send to yourself (mitkoman@gmail.com) or to any email address
- Google Maps: Search places, get basic directions
- TomTom Maps (FREE): Real-time TRAFFIC data, traffic-aware routing, congestion levels, fuel consumption
- Databricks: Execute SQL queries, run notebooks, manage clusters, create clusters, list tables/jobs, run data pipelines
- Azure: Manage VMs (start/stop/restart), list resource groups, storage accounts, SQL servers, get subscription info

IMPORTANT: For traffic-related queries, ALWAYS use TomTom tools (get_traffic_info, get_directions_with_traffic, calculate_distance_with_traffic) as they provide real-time traffic data, delays, and congestion levels.

IMPORTANT: For Azure SQL databases use 'list_databases_azure'. For Databricks databases use 'list_databases'.

Be conversational and remember context. When combining services (like finding sports bars with traffic info, or managing Azure VMs and emailing status reports), use multiple tools together."""),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
            
            # Create agent
            agent = create_openai_functions_agent(llm, tools, prompt)
            
            AGENT_INITIALIZED = True
            print(f"✅ LangChain Agent with Memory initialized! ({len(tools)} tools)")
        else:
            print("⚠️  No tools available")
    except Exception as e:
        print(f"⚠️  Agent initialization failed: {e}")
        import traceback
        traceback.print_exc()

def get_memory(session_id):
    """Get or create memory for a session"""
    if session_id not in conversation_memories:
        conversation_memories[session_id] = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
    return conversation_memories[session_id]

def chat_with_memory(user_message: str, session_id: str):
    """Chat using LangChain agent with memory"""
    if not AGENT_INITIALIZED:
        return "Error: LangChain agent not initialized"
    
    try:
        memory = get_memory(session_id)
        
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            memory=memory,
            verbose=True,
            handle_parsing_errors=True
        )
        
        result = agent_executor.invoke({"input": user_message})
        return result["output"]
    except Exception as e:
        print(f"❌ Error in chat: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}"

@app.route('/')
def index():
    return render_template_string(
        HTML_TEMPLATE,
        langchain_connected=LANGCHAIN_CONNECTED and AGENT_INITIALIZED
    )

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        
        # Use Flask session ID as memory key
        if 'session_id' not in flask_session:
            flask_session['session_id'] = str(uuid.uuid4())
        
        session_id = flask_session['session_id']
        
        if LANGCHAIN_CONNECTED and AGENT_INITIALIZED:
            response_text = chat_with_memory(user_message, session_id)
        else:
            response_text = "Error: LangChain with memory not available. Please check configuration."
        
        return jsonify({'response': response_text})
        
    except Exception as e:
        print(f"❌ Error in endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'response': f"Error: {str(e)}"})

@app.route('/clear-memory', methods=['POST'])
def clear_memory():
    """Clear conversation memory"""
    try:
        if 'session_id' in flask_session:
            session_id = flask_session['session_id']
            if session_id in conversation_memories:
                del conversation_memories[session_id]
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/health')
def health():
    soccer_ok = gmail_ok = maps_ok = tomtom_ok = databricks_ok = azure_ok = False

    try:
        with httpx.Client(timeout=5.0) as client:
            soccer_ok = client.get(f"{MCP_SOCCER_URL}/health").status_code == 200
    except:
        pass

    try:
        with httpx.Client(timeout=5.0) as client:
            data = client.get(f"{MCP_GOOGLE_URL}/health").json()
            gmail_ok = data.get("gmail_configured", False)
    except:
        pass

    try:
        with httpx.Client(timeout=5.0) as client:
            data = client.get(f"{MCP_MAPS_URL}/health").json()
            maps_ok = data.get("api_configured", False)
    except:
        pass

    try:
        with httpx.Client(timeout=5.0) as client:
            data = client.get(f"{MCP_TOMTOM_URL}/health").json()
            tomtom_ok = data.get("api_configured", False)
    except:
        pass

    try:
        with httpx.Client(timeout=5.0) as client:
            data = client.get(f"{MCP_DATABRICKS_URL}/health").json()
            databricks_ok = data.get("api_configured", False)
    except:
        pass

    try:
        with httpx.Client(timeout=5.0) as client:
            data = client.get(f"{MCP_AZURE_URL}/health").json()
            azure_ok = data.get("status") == "healthy" or data.get("azure_auth") == "connected"
    except:
        pass

    return jsonify({
        "status": "healthy",
        "langchain_connected": LANGCHAIN_CONNECTED,
        "agent_initialized": AGENT_INITIALIZED,
        "soccer_ok": soccer_ok,
        "gmail_ok": gmail_ok,
        "maps_ok": maps_ok,
        "tomtom_ok": tomtom_ok,
        "databricks_ok": databricks_ok,
        "azure_ok": azure_ok
    })

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Starting ADDOF with LangChain Memory")
    print("=" * 60)
    print(f"📍 Soccer MCP:      {MCP_SOCCER_URL}")
    print(f"📍 Email MCP:       {MCP_GOOGLE_URL}")
    print(f"📍 Maps MCP:        {MCP_MAPS_URL}")
    print(f"📍 TomTom MCP:      {MCP_TOMTOM_URL} (FREE - Traffic)")
    print(f"📍 Databricks MCP:  {MCP_DATABRICKS_URL}")
    print(f"📍 Azure MCP:       {MCP_AZURE_URL}")
    print(f"🌐 Web App:         http://localhost:5002")
    print()
    print("System Status:")
    print(f"  {'✅' if LANGCHAIN_CONNECTED else '❌'} LangChain:  {'Connected' if LANGCHAIN_CONNECTED else 'Not Connected'}")
    print(f"  {'✅' if AGENT_INITIALIZED else '❌'} Agent+Memory: {'Ready' if AGENT_INITIALIZED else 'Not Ready'}")
    print()
    if LANGCHAIN_CONNECTED and AGENT_INITIALIZED:
        print("✨ MEMORY ENABLED - I'll remember your conversation!")
        print(f"🛠️  37 tools available (Soccer, Email, Maps, TomTom, Databricks, Azure)")
        print(f"🚗 TomTom: Real-time traffic, 75,000 FREE requests/month")
        print(f"📊 Databricks: Natural language to SQL, queries, notebooks, clusters, jobs")
        print(f"☁️  Azure: Manage VMs, resource groups, storage accounts (create/list), SQL servers")
    print("=" * 60)
    app.run(debug=True, port=5006, use_reloader=False)