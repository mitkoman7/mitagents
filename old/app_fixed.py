from flask import Flask, render_template_string, request, jsonify
import httpx
from openai import AzureOpenAI
import os
import json
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Azure OpenAI Configuration
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8081")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Soccer Results AI</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        .chat-box { border: 1px solid #ddd; padding: 20px; height: 400px; overflow-y: auto; margin-bottom: 20px; border-radius: 5px; background: #f9f9f9; }
        .message { margin: 10px 0; padding: 10px; border-radius: 5px; white-space: pre-wrap; }
        .user-message { background: #e3f2fd; text-align: right; }
        .assistant-message { background: #f1f8e9; }
        .input-area { display: flex; gap: 10px; }
        input { flex: 1; padding: 12px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; }
        button { padding: 12px 25px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer; }
        .status { padding: 10px; margin-bottom: 10px; border-radius: 5px; font-size: 12px; }
        .status.connected { background: #e8f5e9; color: #2e7d32; }
        .example-query { padding: 8px; margin: 5px 0; background: white; border-radius: 3px; cursor: pointer; border: 1px solid #ddd; }
        .example-query:hover { background: #e3f2fd; }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚽ Soccer Results AI</h1>
        <div class="status connected" id="status">✓ Ready</div>
        <div class="chat-box" id="chatBox"></div>
        <div class="input-area">
            <input type="text" id="userInput" placeholder="Ask about soccer..." onkeypress="if(event.key==='Enter') sendMessage()">
            <button onclick="sendMessage()">Send</button>
        </div>
        <div style="margin-top: 20px; padding: 15px; background: #f5f5f5; border-radius: 5px;">
            <h3 style="margin-top: 0;">Examples:</h3>
            <div class="example-query" onclick="setQuery(this.innerText)">What were the latest Premier League results?</div>
            <div class="example-query" onclick="setQuery(this.innerText)">Show me Premier League standings</div>
        </div>
    </div>
    <script>
        function setQuery(text) { document.getElementById('userInput').value = text; }
        async function sendMessage() {
            const input = document.getElementById('userInput');
            const message = input.value.trim();
            if (!message) return;
            addMessage(message, 'user');
            input.value = '';
            const loadingId = addMessage('Thinking...', 'assistant');
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ message: message })
                });
                const data = await response.json();
                document.getElementById(loadingId).remove();
                addMessage(data.response, 'assistant');
            } catch (error) {
                document.getElementById(loadingId).remove();
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

def get_mcp_tools():
    """Get tools from MCP server"""
    try:
        with httpx.Client(timeout=10.0) as http_client:
            response = http_client.get(f"{MCP_SERVER_URL}/tools")
            return response.json()
    except Exception as e:
        print(f"Error getting tools: {e}")
        return None

def execute_mcp_tool(tool_name, arguments):
    """Execute MCP tool"""
    try:
        with httpx.Client(timeout=30.0) as http_client:
            response = http_client.post(
                f"{MCP_SERVER_URL}/execute",
                json={"tool_name": tool_name, "arguments": arguments}
            )
            return response.json()["result"]
    except Exception as e:
        print(f"Error executing tool: {e}")
        return json.dumps({"error": str(e)})

def chat_with_openai(user_message):
    """Chat with OpenAI - simplified without history"""
    try:
        # Get tools
        tools_data = get_mcp_tools()
        if not tools_data:
            return "Error: Cannot connect to MCP server."
        
        # Convert to OpenAI format
        tools = [{
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["inputSchema"]
            }
        } for tool in tools_data]
        
        # Simple message list - no history for now
        messages = [{"role": "user", "content": user_message}]
        
        # Call OpenAI
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        # Handle tool calls - max 5 iterations
        for _ in range(5):
            if response.choices[0].finish_reason != "tool_calls":
                break
            
            # Get tool calls
            tool_calls = response.choices[0].message.tool_calls
            if not tool_calls:
                break
            
            # Add assistant message (without tool_calls object)
            messages.append({
                "role": "assistant",
                "content": response.choices[0].message.content or ""
            })
            
            # Execute each tool
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                print(f"🔧 Executing: {function_name}")
                result = execute_mcp_tool(function_name, function_args)
                
                # Add tool result
                messages.append({
                    "role": "user",  # Use 'user' role for tool results in simplified mode
                    "content": f"Tool {function_name} result: {result}"
                })
            
            # Get next response
            response = client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
        
        # Return final response
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Error in chat: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}"

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        
        response_text = chat_with_openai(user_message)
        
        return jsonify({'response': response_text})
        
    except Exception as e:
        print(f"Error in endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'response': f"Error: {str(e)}"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    print("🚀 Starting Soccer AI...")
    print(f"📍 MCP: {MCP_SERVER_URL}")
    print(f"🌐 App: http://localhost:5000")
    app.run(debug=True, port=5000, use_reloader=False)