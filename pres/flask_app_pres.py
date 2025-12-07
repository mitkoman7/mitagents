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

# Only Gmail and Databricks for presentation
MCP_GOOGLE_URL = os.getenv("MCP_GOOGLE_URL", "http://localhost:8082")
MCP_DATABRICKS_URL = os.getenv("MCP_DATABRICKS_URL", "http://localhost:8100" \
"")

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

# Session management for memory
user_agents = {}

# HTML Template for Presentation
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Assistant - Presentation</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 32px;
        }
        .memory-badge {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
            margin-left: 10px;
        }
        .status-panel {
            background: #f5f5f5;
            padding: 15px;
            border-radius: 10px;
            margin: 20px 0;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .status-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px;
            background: white;
            border-radius: 5px;
        }
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
        }
        .status-dot.connected { background: #4CAF50; }
        .status-dot.disconnected { background: #f44336; }
        .chat-box {
            height: 400px;
            overflow-y: auto;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            background: #fafafa;
        }
        .message {
            margin: 10px 0;
            padding: 12px;
            border-radius: 10px;
            max-width: 80%;
            word-wrap: break-word;
        }
        .user-message {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin-left: auto;
            text-align: right;
        }
        .assistant-message {
            background: #e3f2fd;
            color: #333;
        }
        .input-area {
            display: flex;
            gap: 10px;
        }
        input[type="text"] {
            flex: 1;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
        }
        button {
            padding: 12px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
        }
        button:hover {
            opacity: 0.9;
        }
        .examples {
            margin-top: 20px;
        }
        .examples h3 {
            color: #666;
            font-size: 16px;
            margin-bottom: 10px;
        }
        .example-queries {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .example-query {
            padding: 10px;
            background: #f0f0f0;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 13px;
        }
        .example-query:hover {
            background: #e0e0e0;
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
        .tag-databricks { background: #ff3621; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 AI Assistant - Presentation
            {% if langchain_connected %}
            <span class="memory-badge">🧠 With Memory</span>
            {% endif %}
        </h1>

        <div class="status-panel">
            <div class="status-item">
                <span><span class="status-dot" id="gmailDot"></span>📧 Gmail</span>
                <span id="gmailStatus">Checking...</span>
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
            <h3>Try these examples:</h3>
            <div class="example-queries">
                <div class="example-query" onclick="setQuery(this.textContent)">
                    <span class="service-tag tag-databricks">📊</span>
                    Show me a 3 month attendance report
                </div>
                <div class="example-query" onclick="setQuery(this.textContent)">
                    <span class="service-tag tag-databricks">📊</span>
                    List all my Databricks databases
                </div>
                <div class="example-query" onclick="setQuery(this.textContent)">
                    <span class="service-tag tag-databricks">📊</span>
                    Count employees by department
                </div>
                <div class="example-query" onclick="setQuery(this.textContent)">
                    <span class="service-tag tag-gmail">📧</span>
                    Email me that report
                </div>
                <div class="example-query" onclick="setQuery(this.textContent)">
                    <span class="service-tag tag-databricks">📊</span>
                    List tables in default database
                </div>
                <div class="example-query" onclick="setQuery(this.textContent)">
                    <span class="service-tag tag-databricks">📊</span>
                    List all my clusters
                </div>
            </div>
        </div>
    </div>
    <script>
        let messageCount = 0;

        checkStatus();

        async function checkStatus() {
            try {
                const response = await fetch('/status');
                const data = await response.json();

                if (data.gmail_ok) {
                    document.getElementById('gmailDot').classList.add('connected');
                    document.getElementById('gmailStatus').textContent = '✓ Connected';
                } else {
                    document.getElementById('gmailDot').classList.add('disconnected');
                    document.getElementById('gmailStatus').textContent = '✗ Not running';
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
            const cleanText = text.replace(/<span[^>]*>.*?<\\/span>/g, '').trim();
            document.getElementById('userInput').value = cleanText;
        }

        async function sendMessage() {
            const input = document.getElementById('userInput');
            const message = input.value.trim();
            if (!message) return;

            addMessage(message, 'user');
            input.value = '';
            messageCount++;

            const thinkingId = addMessage('Thinking...', 'assistant');

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message })
                });

                const data = await response.json();
                document.getElementById(thinkingId).remove();

                if (data.response) {
                    addMessage(data.response, 'assistant');
                } else if (data.error) {
                    addMessage('Error: ' + data.error, 'assistant');
                }
            } catch (error) {
                document.getElementById(thinkingId).remove();
                addMessage('Error: ' + error.message, 'assistant');
            }
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

# Helper function for tool execution
def execute_tool_direct(tool_name, arguments):
    """Execute tool on appropriate MCP server"""
    google_tools = ["send_email", "send_email_with_data", "email_me"]
    databricks_tools = ["natural_language_query", "execute_sql", "list_databases", "list_tables",
                       "get_table_schema", "run_notebook", "list_clusters", "get_cluster_status",
                       "start_cluster", "list_jobs", "run_job", "get_job_run_status", "create_cluster"]

    if tool_name in google_tools:
        server_url = MCP_GOOGLE_URL
    elif tool_name in databricks_tools:
        server_url = MCP_DATABRICKS_URL
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

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
        # Email tools
        def email_me_func(subject: str, data: str, message: str = "Here is the data you requested:"):
            """Send data to user's own email (mitkoman@gmail.com)"""
            if not subject or not data:
                return json.dumps({"error": "subject and data are required"})
            return execute_tool_direct("email_me", {"subject": subject, "data": data, "message": message})

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

        def list_databases_func(catalog: str = "dbrmitko"):
            """List all databases/schemas in a Databricks catalog"""
            return execute_tool_direct("list_databases", {"catalog": catalog})

        def list_tables_func(catalog: str = "dbrmitko", db_schema: str = "default"):
            """List all tables in a Databricks database/schema"""
            return execute_tool_direct("list_tables", {"catalog": catalog, "schema": db_schema})

        def get_table_schema_func(table_name: str, catalog: str = "dbrmitko", db_schema: str = "default"):
            """Get schema/columns of a Databricks table"""
            if not table_name:
                return json.dumps({"error": "table_name is required"})
            return execute_tool_direct("get_table_schema", {"table_name": table_name, "catalog": catalog, "schema": db_schema})

        def list_clusters_func():
            """List all Databricks clusters"""
            return execute_tool_direct("list_clusters", {})

        def get_cluster_status_func(cluster_id: str):
            """Get status of a Databricks cluster"""
            if not cluster_id:
                return json.dumps({"error": "cluster_id is required"})
            return execute_tool_direct("get_cluster_status", {"cluster_id": cluster_id})

        def create_cluster_func(cluster_name: str, node_type: str = "Standard_D4ds_v5", num_workers: int = 0,
                               spark_version: str = "16.4.x-cpu-ml-scala2.12", autotermination_minutes: int = 120):
            """Create a new Databricks cluster"""
            if not cluster_name:
                return json.dumps({"error": "cluster_name is required"})
            return execute_tool_direct("create_cluster", {
                "cluster_name": cluster_name,
                "node_type": node_type,
                "num_workers": num_workers,
                "spark_version": spark_version,
                "autotermination_minutes": autotermination_minutes
            })

        # Create StructuredTools
        tools = [
            StructuredTool.from_function(
                func=email_me_func,
                name="email_me",
                description="Send data or information to your email (mitkoman@gmail.com). Use this when user wants to receive results via email."
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
                func=list_clusters_func,
                name="list_clusters",
                description="List all available Databricks clusters with their status and configuration."
            ),
            StructuredTool.from_function(
                func=get_cluster_status_func,
                name="get_cluster_status",
                description="Get the current status of a specific Databricks cluster by its ID."
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
                ("system", """You are a helpful AI assistant for a presentation demo. You remember the conversation history.

You have access to:
- Gmail: Send emails to mitkoman@gmail.com
- Databricks: Execute SQL queries, natural language to SQL translation, manage clusters, explore databases and tables

Key Features to Demonstrate:
1. Natural Language to SQL: Users can ask questions like "3 month attendance report" and you'll translate to SQL
2. Email Integration: Can send query results via email
3. Cluster Management: List, create, and manage Databricks clusters
4. Memory: You remember the conversation context

Be conversational and helpful. When users ask for reports or data, offer to email them the results."""),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])

            # Create memory
            memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

            # Create agent
            agent = create_openai_functions_agent(llm, tools, prompt)
            agent_executor = AgentExecutor(agent=agent, tools=tools, memory=memory, verbose=True)

            AGENT_INITIALIZED = True
            print("✅ LangChain Agent with Memory initialized! (9 tools)")

    except Exception as e:
        print(f"⚠️  Agent initialization failed: {e}")
        import traceback
        traceback.print_exc()

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, langchain_connected=LANGCHAIN_CONNECTED)

@app.route('/status')
def status():
    gmail_ok = False
    databricks_ok = False

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{MCP_GOOGLE_URL}/health")
            gmail_ok = response.status_code == 200
    except:
        pass

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{MCP_DATABRICKS_URL}/health")
            databricks_ok = response.status_code == 200
    except:
        pass

    return jsonify({
        "gmail_ok": gmail_ok,
        "databricks_ok": databricks_ok,
        "langchain_ok": LANGCHAIN_CONNECTED,
        "agent_ok": AGENT_INITIALIZED
    })

@app.route('/chat', methods=['POST'])
def chat():
    if not AGENT_INITIALIZED:
        return jsonify({"error": "Agent not initialized"}), 500

    data = request.json
    user_message = data.get('message', '')

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # Get or create session ID
    session_id = flask_session.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        flask_session['session_id'] = session_id

    # Get or create agent for this session
    if session_id not in user_agents:
        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful AI assistant for a presentation demo. You remember the conversation history.

You have access to:
- Gmail: Send emails to mitkoman@gmail.com
- Databricks: Execute SQL queries, natural language to SQL translation, manage clusters, explore databases and tables

Key Features to Demonstrate:
1. Natural Language to SQL: Users can ask questions like "3 month attendance report" and you'll translate to SQL
2. Email Integration: Can send query results via email
3. Cluster Management: List, create, and manage Databricks clusters
4. Memory: You remember the conversation context

Be conversational and helpful. When users ask for reports or data, offer to email them the results."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # Email tools
        def email_me_func(subject: str, data: str, message: str = "Here is the data you requested:"):
            if not subject or not data:
                return json.dumps({"error": "subject and data are required"})
            return execute_tool_direct("email_me", {"subject": subject, "data": data, "message": message})

        # Databricks tools
        def natural_language_query_func(question: str, table_name: str = ""):
            if not question:
                return json.dumps({"error": "question is required"})
            return execute_tool_direct("natural_language_query", {"question": question, "table_name": table_name})

        def execute_sql_func(query: str, warehouse_id: str = ""):
            if not query:
                return json.dumps({"error": "query is required"})
            return execute_tool_direct("execute_sql", {"query": query, "warehouse_id": warehouse_id})

        def list_databases_func(catalog: str = "dbrmitko"):
            return execute_tool_direct("list_databases", {"catalog": catalog})

        def list_tables_func(catalog: str = "dbrmitko", db_schema: str = "default"):
            return execute_tool_direct("list_tables", {"catalog": catalog, "schema": db_schema})

        def get_table_schema_func(table_name: str, catalog: str = "dbrmitko", db_schema: str = "default"):
            if not table_name:
                return json.dumps({"error": "table_name is required"})
            return execute_tool_direct("get_table_schema", {"table_name": table_name, "catalog": catalog, "schema": db_schema})

        def list_clusters_func():
            return execute_tool_direct("list_clusters", {})

        def get_cluster_status_func(cluster_id: str):
            if not cluster_id:
                return json.dumps({"error": "cluster_id is required"})
            return execute_tool_direct("get_cluster_status", {"cluster_id": cluster_id})

        def create_cluster_func(cluster_name: str, node_type: str = "Standard_D4ds_v5", num_workers: int = 0,
                               spark_version: str = "16.4.x-cpu-ml-scala2.12", autotermination_minutes: int = 120):
            if not cluster_name:
                return json.dumps({"error": "cluster_name is required"})
            return execute_tool_direct("create_cluster", {
                "cluster_name": cluster_name,
                "node_type": node_type,
                "num_workers": num_workers,
                "spark_version": spark_version,
                "autotermination_minutes": autotermination_minutes
            })

        tools = [
            StructuredTool.from_function(func=email_me_func, name="email_me",
                description="Send data or information to your email (mitkoman@gmail.com)."),
            StructuredTool.from_function(func=natural_language_query_func, name="natural_language_query",
                description="Convert natural language questions to SQL and execute on Databricks."),
            StructuredTool.from_function(func=execute_sql_func, name="execute_sql",
                description="Execute raw SQL query on Databricks."),
            StructuredTool.from_function(func=list_databases_func, name="list_databases",
                description="List all databases in Databricks catalog."),
            StructuredTool.from_function(func=list_tables_func, name="list_tables",
                description="List all tables in a Databricks database."),
            StructuredTool.from_function(func=get_table_schema_func, name="get_table_schema",
                description="Get schema/columns of a Databricks table."),
            StructuredTool.from_function(func=list_clusters_func, name="list_clusters",
                description="List all Databricks clusters."),
            StructuredTool.from_function(func=get_cluster_status_func, name="get_cluster_status",
                description="Get status of a Databricks cluster."),
            StructuredTool.from_function(func=create_cluster_func, name="create_cluster",
                description="Create a new Databricks cluster.")
        ]

        agent = create_openai_functions_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, memory=memory, verbose=True)
        user_agents[session_id] = agent_executor

    try:
        result = user_agents[session_id].invoke({"input": user_message})
        return jsonify({"response": result['output']})
    except Exception as e:
        print(f"❌ Error in agent execution: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🎯 AI Assistant - PRESENTATION MODE")
    print("=" * 60)
    print(f"📍 Gmail MCP:       {MCP_GOOGLE_URL}")
    print(f"📍 Databricks MCP:  {MCP_DATABRICKS_URL}")
    print(f"🌐 Web App:         http://localhost:5007")
    print()
    print("System Status:")
    print(f"  {'✅' if LANGCHAIN_CONNECTED else '❌'} LangChain:  {'Connected' if LANGCHAIN_CONNECTED else 'Not Connected'}")
    print(f"  {'✅' if AGENT_INITIALIZED else '❌'} Agent+Memory: {'Ready' if AGENT_INITIALIZED else 'Not Ready'}")
    print()
    if LANGCHAIN_CONNECTED and AGENT_INITIALIZED:
        print("✨ MEMORY ENABLED - Conversation history tracked!")
        print(f"🛠️  9 tools available (Gmail + Databricks)")
        print(f"📊 Databricks: Natural language to SQL, queries, clusters")
        print(f"📧 Gmail: Send reports via email")
    print("=" * 60)
    app.run(debug=True, port=5008, use_reloader=False)
