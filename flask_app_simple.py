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
    <title>AI Assistant with Memory</title>
    <style>
        body { 
            font-family: 'Segoe UI', Arial, sans-serif; 
            max-width: 1000px; 
            margin: 50px auto; 
            padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
        }
        .container { 
            background: white; 
            padding: 30px; 
            border-radius: 15px; 
            box-shadow: 0 10px 40px rgba(0,0,0,0.2); 
        }
        h1 { 
            color: #333; 
            text-align: center; 
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 20px;
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
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
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
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .status-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
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
            padding: 20px; 
            height: 400px; 
            overflow-y: auto; 
            margin-bottom: 20px; 
            border-radius: 8px; 
            background: #fafafa; 
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
        }
        input { 
            flex: 1; 
            padding: 14px; 
            border: 2px solid #e0e0e0; 
            border-radius: 8px; 
            font-size: 14px; 
        }
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        button { 
            padding: 14px 30px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer; 
            font-weight: 600;
        }
        button:hover {
            opacity: 0.9;
        }
        .examples {
            margin-top: 20px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        .examples h3 {
            margin-top: 0;
            color: #333;
        }
        .example-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .example-query { 
            padding: 10px; 
            background: white; 
            border-radius: 5px; 
            cursor: pointer; 
            border: 1px solid #ddd;
            font-size: 13px;
            transition: all 0.2s;
        }
        .example-query:hover { 
            background: #e3f2fd;
            border-color: #667eea;
            transform: translateY(-2px);
        }
        .service-tag {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: 600;
            margin-right: 5px;
        }
        .tag-gmail { background: #ea4335; color: white; }
        .tag-soccer { background: #fbbc04; color: white; }
        .tag-databricks { background: #ff3621; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 AI Assistant 
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
        </div>
        
        <div class="chat-box" id="chatBox"></div>
        
        <div class="input-area">
            <input type="text" id="userInput" placeholder="Ask me anything (I'll remember!)..." onkeypress="if(event.key==='Enter') sendMessage()">
            <button onclick="sendMessage()">Send</button>
        </div>
        
        <div class="examples">
            <h3>💡 Try these (I'll remember context!):</h3>
            <div class="example-grid">
                <div class="example-query" onclick="setQuery(this.textContent)">
                    <span class="service-tag tag-soccer">⚽</span>
                    Latest Premier League results?
                </div>
                <div class="example-query" onclick="setQuery(this.textContent)">
                    Traffic to Times Square right now?
                </div>
                <div class="example-query" onclick="setQuery(this.textContent)">
                    <span class="service-tag tag-soccer">⚽</span>
                    Show me Liverpool's matches
                </div>
                <div class="example-query" onclick="setQuery(this.textContent)">
                    Find pizza restaurants near Central Park
                </div>
                <div class="example-query" onclick="setQuery(this.textContent)">
                    How long to drive to JFK Airport?
                </div>
                <div class="example-query" onclick="setQuery(this.textContent)">
                    Then: "Email me those directions"
                </div>
                <div class="example-query" onclick="setQuery(this.textContent)">
                    <span class="service-tag tag-databricks">📊</span>
                    Show me Databricks databases
                </div>
                <div class="example-query" onclick="setQuery(this.textContent)">
                    <span class="service-tag tag-databricks">📊</span>
                    List tables in default database
                </div>
                <div class="example-query" onclick="setQuery(this.textContent)">
                    <span class="service-tag tag-databricks">📊</span>
                    Create a cluster named test-cluster
                </div>
                <div class="example-query" onclick="setQuery(this.textContent)">
                    <span class="service-tag tag-databricks">📊</span>
                    List all my Databricks clusters
                </div>
            </div>
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

    if tool_name in google_tools:
        server_url = MCP_GOOGLE_URL
    elif tool_name in tomtom_tools:
        server_url = MCP_TOMTOM_URL
        # Remove _tomtom suffix for actual API call
        tool_name = tool_name.replace("_tomtom", "")
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

IMPORTANT: For traffic-related queries, ALWAYS use TomTom tools (get_traffic_info, get_directions_with_traffic, calculate_distance_with_traffic) as they provide real-time traffic data, delays, and congestion levels.

Be conversational and remember context. When combining services (like finding sports bars with traffic info, or querying soccer data from Databricks), use multiple tools together."""),
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
    soccer_ok = gmail_ok = maps_ok = tomtom_ok = databricks_ok = False

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

    return jsonify({
        "status": "healthy",
        "langchain_connected": LANGCHAIN_CONNECTED,
        "agent_initialized": AGENT_INITIALIZED,
        "soccer_ok": soccer_ok,
        "gmail_ok": gmail_ok,
        "maps_ok": maps_ok,
        "tomtom_ok": tomtom_ok,
        "databricks_ok": databricks_ok
    })

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Starting AI Assistant with LangChain Memory")
    print("=" * 60)
    print(f"📍 Soccer MCP:      {MCP_SOCCER_URL}")
    print(f"📍 Email MCP:       {MCP_GOOGLE_URL}")
    print(f"📍 Maps MCP:        {MCP_MAPS_URL}")
    print(f"📍 TomTom MCP:      {MCP_TOMTOM_URL} (FREE - Traffic)")
    print(f"📍 Databricks MCP:  {MCP_DATABRICKS_URL}")
    print(f"🌐 Web App:         http://localhost:5002")
    print()
    print("System Status:")
    print(f"  {'✅' if LANGCHAIN_CONNECTED else '❌'} LangChain:  {'Connected' if LANGCHAIN_CONNECTED else 'Not Connected'}")
    print(f"  {'✅' if AGENT_INITIALIZED else '❌'} Agent+Memory: {'Ready' if AGENT_INITIALIZED else 'Not Ready'}")
    print()
    if LANGCHAIN_CONNECTED and AGENT_INITIALIZED:
        print("✨ MEMORY ENABLED - I'll remember your conversation!")
        print(f"🛠️  26 tools available (Soccer, Email, Maps, TomTom, Databricks)")
        print(f"🚗 TomTom: Real-time traffic, 75,000 FREE requests/month")
        print(f"📊 Databricks: Natural language to SQL, queries, notebooks, clusters, jobs")
    print("=" * 60)
    app.run(debug=True, port=5006, use_reloader=False)