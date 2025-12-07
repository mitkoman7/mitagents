from flask import Flask, render_template_string, request, jsonify, session
import httpx
from openai import AzureOpenAI
import os
import json
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your-secret-key-change-in-production")

# Azure OpenAI Configuration
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

MCP_SOCCER_URL = os.getenv("MCP_SOCCER_URL", "http://localhost:8081")
MCP_GOOGLE_URL = os.getenv("MCP_GOOGLE_URL", "http://localhost:8082")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Assistant with Google & Soccer</title>
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
        .auth-section {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .auth-status {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #dc3545;
        }
        .status-dot.connected {
            background: #28a745;
        }
        .auth-btn {
            padding: 8px 16px;
            background: #4285f4;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            text-decoration: none;
            font-size: 14px;
        }
        .auth-btn:hover {
            background: #357ae8;
        }
        .chat-box { 
            border: 1px solid #ddd; 
            padding: 20px; 
            height: 450px; 
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
        .tag-drive { background: #34a853; color: white; }
        .tag-calendar { background: #4285f4; color: white; }
        .tag-soccer { background: #fbbc04; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 AI Assistant</h1>
        <p class="subtitle">Powered by Azure OpenAI with Google Services & Soccer Data</p>
        
        <div class="auth-section">
            <div class="auth-status">
                <span class="status-dot" id="authDot"></span>
                <span id="authStatus">Checking authentication...</span>
            </div>
            <a href="{{ google_auth_url }}" class="auth-btn" target="_blank">🔐 Sign in with Google</a>
        </div>
        
        <div class="chat-box" id="chatBox"></div>
        
        <div class="input-area">
            <input type="text" id="userInput" placeholder="Ask me anything..." onkeypress="if(event.key==='Enter') sendMessage()">
            <button onclick="sendMessage()">Send</button>
        </div>
        
        <div class="examples">
            <h3>💡 Try these examples:</h3>
            <div class="example-grid">
                <div class="example-query" onclick="setQuery(this.innerText)">
                    <span class="service-tag tag-gmail">📧 Gmail</span>
                    Search my emails from last week
                </div>
                <div class="example-query" onclick="setQuery(this.innerText)">
                    <span class="service-tag tag-gmail">📧 Gmail</span>
                    Send an email summary of today's tasks
                </div>
                <div class="example-query" onclick="setQuery(this.innerText)">
                    <span class="service-tag tag-drive">📁 Drive</span>
                    Find my Q4 report in Drive
                </div>
                <div class="example-query" onclick="setQuery(this.innerText)">
                    <span class="service-tag tag-calendar">📅 Calendar</span>
                    What's on my calendar this week?
                </div>
                <div class="example-query" onclick="setQuery(this.innerText)">
                    <span class="service-tag tag-soccer">⚽ Soccer</span>
                    What were the latest Premier League results?
                </div>
                <div class="example-query" onclick="setQuery(this.innerText)">
                    <span class="service-tag tag-soccer">⚽ Soccer</span>
                    Show me Liverpool's recent matches
                </div>
                <div class="example-query" onclick="setQuery(this.innerText)">
                    <span class="service-tag tag-gmail">📧 Gmail</span>
                    Email me the Premier League standings
                </div>
                <div class="example-query" onclick="setQuery(this.innerText)">
                    <span class="service-tag tag-calendar">📅 Calendar</span>
                    Send my calendar to my email
                </div>
            </div>
        </div>
    </div>
    <script>
        let sessionToken = localStorage.getItem('google_session_token') || '';
        
        // Check auth status on load
        checkAuthStatus();
        
        async function checkAuthStatus() {
            try {
                const response = await fetch('/api/auth/status');
                const data = await response.json();
                updateAuthUI(data.authenticated);
            } catch (error) {
                updateAuthUI(false);
            }
        }
        
        function updateAuthUI(authenticated) {
            const dot = document.getElementById('authDot');
            const status = document.getElementById('authStatus');
            
            if (authenticated) {
                dot.classList.add('connected');
                status.textContent = '✓ Connected to Google';
            } else {
                dot.classList.remove('connected');
                status.textContent = '⚠ Not authenticated - Click to sign in';
            }
        }
        
        // Check for session token in URL (after OAuth redirect)
        const urlParams = new URLSearchParams(window.location.search);
        const token = urlParams.get('token');
        if (token) {
            localStorage.setItem('google_session_token', token);
            sessionToken = token;
            window.history.replaceState({}, document.title, window.location.pathname);
            checkAuthStatus();
        }
        
        function setQuery(text) { 
            // Remove the service tag from the text
            const cleanText = text.replace(/<span[^>]*>.*?<\/span>/g, '').trim();
            document.getElementById('userInput').value = cleanText; 
        }
        
        async function sendMessage() {
            const input = document.getElementById('userInput');
            const message = input.value.trim();
            if (!message) return;
            
            addMessage(message, 'user');
            input.value = '';
            
            const loadingId = addMessage('🤔 Thinking...', 'assistant');
            
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ 
                        message: message,
                        session_token: sessionToken
                    })
                });
                
                const data = await response.json();
                document.getElementById(loadingId).remove();
                addMessage(data.response, 'assistant');
            } catch (error) {
                document.getElementById(loadingId).remove();
                addMessage('❌ Error: ' + error.message, 'assistant');
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

def get_all_tools():
    """Get tools from all MCP servers"""
    all_tools = []
    
    try:
        # Get Soccer tools
        with httpx.Client(timeout=10.0) as http_client:
            response = http_client.get(f"{MCP_SOCCER_URL}/tools")
            soccer_tools = response.json()
            all_tools.extend(soccer_tools)
    except Exception as e:
        print(f"Error getting soccer tools: {e}")
    
    try:
        # Get Google tools
        with httpx.Client(timeout=10.0) as http_client:
            response = http_client.get(f"{MCP_GOOGLE_URL}/tools")
            google_tools = response.json()
            all_tools.extend(google_tools)
    except Exception as e:
        print(f"Error getting Google tools: {e}")
    
    return all_tools

def execute_tool(tool_name, arguments, session_token=None):
    """Execute tool from appropriate MCP server"""
    # Determine which server based on tool name
    google_tools = ["send_email", "search_gmail", "search_drive", "get_calendar_events", "get_email_content"]
    
    if tool_name in google_tools:
        server_url = MCP_GOOGLE_URL
        payload = {
            "tool_name": tool_name,
            "arguments": arguments,
            "session_token": session_token
        }
    else:
        server_url = MCP_SOCCER_URL
        payload = {
            "tool_name": tool_name,
            "arguments": arguments
        }
    
    try:
        with httpx.Client(timeout=30.0) as http_client:
            response = http_client.post(
                f"{server_url}/execute",
                json=payload
            )
            return response.json()["result"]
    except Exception as e:
        print(f"Error executing tool: {e}")
        return json.dumps({"error": str(e)})

def chat_with_openai(user_message, session_token=None):
    """Chat with OpenAI using all available tools"""
    try:
        # Get all tools
        tools_data = get_all_tools()
        if not tools_data:
            return "Error: Cannot connect to MCP servers."
        
        # Convert to OpenAI format
        tools = [{
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["inputSchema"]
            }
        } for tool in tools_data]
        
        # System message
        system_message = """You are a helpful AI assistant with access to:
1. Google Services (Gmail, Drive, Calendar) - requires authentication
2. Soccer/Football data from major leagues

When users ask about emails, calendar, or drive, use the Google tools.
When users ask about soccer/football, use the soccer tools.
You can combine data from different sources - for example, you can get soccer data and email it to the user.

If a Google tool returns an authentication error, politely inform the user they need to sign in with Google using the button at the top of the page."""
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        # Call OpenAI
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        # Handle tool calls - max 10 iterations
        for iteration in range(10):
            if response.choices[0].finish_reason != "tool_calls":
                break
            
            tool_calls = response.choices[0].message.tool_calls
            if not tool_calls:
                break
            
            # Add assistant message
            messages.append({
                "role": "assistant",
                "content": response.choices[0].message.content or ""
            })
            
            # Execute each tool
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                print(f"🔧 [{iteration+1}] Executing: {function_name}")
                result = execute_tool(function_name, function_args, session_token)
                
                # Add tool result
                messages.append({
                    "role": "user",
                    "content": f"Tool {function_name} result: {result}"
                })
            
            # Get next response
            response = client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Error in chat: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}"

@app.route('/')
def index():
    google_auth_url = f"{MCP_GOOGLE_URL}/auth/login"
    return render_template_string(HTML_TEMPLATE, google_auth_url=google_auth_url)

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        session_token = data.get('session_token')
        
        response_text = chat_with_openai(user_message, session_token)
        
        return jsonify({'response': response_text})
        
    except Exception as e:
        print(f"Error in endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'response': f"Error: {str(e)}"})

@app.route('/api/auth/status')
def auth_status():
    """Check Google authentication status"""
    try:
        session_token = request.args.get('session_token') or \
                       request.headers.get('X-Session-Token')
        
        with httpx.Client(timeout=10.0) as http_client:
            response = http_client.get(
                f"{MCP_GOOGLE_URL}/auth/status",
                params={"session_token": session_token} if session_token else {}
            )
            return jsonify(response.json())
    except Exception as e:
        return jsonify({"authenticated": False, "error": str(e)})

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "soccer_mcp": MCP_SOCCER_URL,
        "google_mcp": MCP_GOOGLE_URL
    })

if __name__ == '__main__':
    print("🚀 Starting AI Assistant...")
    print(f"📍 Soccer MCP: {MCP_SOCCER_URL}")
    print(f"📍 Google MCP: {MCP_GOOGLE_URL}")
    print(f"🌐 Web App: http://localhost:5000")
    print("\n⚠️  Make sure both MCP servers are running!")
    app.run(debug=True, port=5000, use_reloader=False)
