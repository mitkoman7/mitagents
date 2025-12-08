"""
COMPLETE CODE FLOW EXAMPLE
==========================
This file demonstrates the complete flow from user input to MCP server execution
for the query: "Create a storage account called mystore123"

This is a DEMONSTRATION file showing how the code flows through the system.
"""

# ============================================================================
# STEP 1: User sends message via web interface
# ============================================================================
# File: templates/index.html (frontend)
# User types in chat: "Create a storage account called mystore123"
# JavaScript sends POST request:

"""
fetch('/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        message: "Create a storage account called mystore123"
    })
})
"""

# ============================================================================
# STEP 2: Flask receives request at /chat endpoint
# ============================================================================
# File: flask_app_simple.py

from flask import Flask, request, jsonify
import os
import json
import httpx
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import StructuredTool
from langchain_openai import AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from pydantic import BaseModel, Field

# Environment variables
AZURE_OPENAI_API_KEY = "CqVxT0bl2IHaT6AblSNI85V2M7Y5pyteYUFLw7c12mEEFbrpH8BFJQQJ99BCACYeBjFXJ3w3AAABACOGYrX7"
AZURE_OPENAI_ENDPOINT = "https://openmit.openai.azure.com/"
AZURE_OPENAI_DEPLOYMENT_NAME = "gpt-4o"
MCP_AZURE_URL = "http://localhost:8086"

app = Flask(__name__)

# ============================================================================
# STEP 3: Tool routing configuration
# ============================================================================

# List of Azure tools for routing
azure_tools = [
    "list_resource_groups", "list_vms", "get_vm_status", "start_vm",
    "stop_vm", "restart_vm", "list_storage_accounts", "list_databases_azure",
    "get_subscription_info", "list_resources", "create_storage_account"  # ← Our tool
]

# ============================================================================
# STEP 4: execute_tool_direct() - HTTP router to MCP servers
# ============================================================================

def execute_tool_direct(tool_name, arguments):
    """
    Routes tool execution to the appropriate MCP server via HTTP
    This is the bridge between Flask and MCP servers
    """
    print(f"🔀 STEP 4: execute_tool_direct() called")
    print(f"   Tool name: {tool_name}")
    print(f"   Arguments: {arguments}")

    # Determine which MCP server to route to
    if tool_name in azure_tools:
        server_url = MCP_AZURE_URL  # http://localhost:8086
        print(f"   ✅ Matched azure_tools list → routing to {server_url}")

        # Handle tool name transformation if needed
        if tool_name == "list_databases_azure":
            tool_name = "list_databases"  # Avoid conflict with Databricks
            print(f"   🔄 Transformed tool name to: {tool_name}")

    # Make HTTP POST request to MCP server
    print(f"   📡 Sending HTTP POST to {server_url}/execute")

    with httpx.Client(timeout=30.0) as http_client:
        response = http_client.post(
            f"{server_url}/execute",
            json={
                "tool_name": tool_name,
                "arguments": arguments
            }
        )
        result = response.json()["result"]
        print(f"   ✅ Received response from MCP server")
        return result

# ============================================================================
# STEP 5: Tool wrapper function
# ============================================================================

def create_storage_account_func(
    storage_account_name: str,
    resource_group: str = "",
    location: str = "eastus",
    sku: str = "Standard_LRS",
    kind: str = "StorageV2"
):
    """Create a new Azure storage account"""
    # ← GPT-4 reads this description!

    print(f"🔧 STEP 5: create_storage_account_func() called")
    print(f"   Parameters received:")
    print(f"   - storage_account_name: {storage_account_name}")
    print(f"   - resource_group: {resource_group}")
    print(f"   - location: {location}")
    print(f"   - sku: {sku}")
    print(f"   - kind: {kind}")

    if not storage_account_name:
        return json.dumps({"error": "storage_account_name is required"})

    # Call the HTTP router
    return execute_tool_direct("create_storage_account", {
        "storage_account_name": storage_account_name,
        "resource_group": resource_group,
        "location": location,
        "sku": sku,
        "kind": kind
    })

# ============================================================================
# STEP 6: Pydantic schema for parameter validation
# ============================================================================

class CreateStorageAccountInput(BaseModel):
    """Input schema for create_storage_account tool"""
    storage_account_name: str = Field(
        description="Storage account name (must be globally unique, 3-24 lowercase letters and numbers)"
    )
    resource_group: str = Field(
        default="",
        description="Resource group name (uses default if not specified)"
    )
    location: str = Field(
        default="eastus",
        description="Azure region (e.g., 'eastus', 'westus2')"
    )
    sku: str = Field(
        default="Standard_LRS",
        description="Storage SKU: Standard_LRS, Standard_GRS, etc."
    )
    kind: str = Field(
        default="StorageV2",
        description="Storage kind: StorageV2, Storage, BlobStorage"
    )

# ============================================================================
# STEP 7: StructuredTool registration - GPT-4 sees this!
# ============================================================================

create_storage_account_tool = StructuredTool(
    name="create_storage_account",  # ← Tool identifier
    description="Create a new Azure storage account",  # ← GPT-4 reads this to decide when to use!
    func=create_storage_account_func,  # ← Function to execute
    args_schema=CreateStorageAccountInput  # ← Parameter schema
)

print("📝 STEP 7: StructuredTool registered")
print(f"   Name: {create_storage_account_tool.name}")
print(f"   Description: {create_storage_account_tool.description}")
print(f"   This metadata is sent to GPT-4 for tool selection!")

# ============================================================================
# STEP 8: LangChain Agent setup with ALL 37 tools
# ============================================================================

# Initialize GPT-4 via Azure OpenAI
llm = AzureChatOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    azure_deployment=AZURE_OPENAI_DEPLOYMENT_NAME,
    api_version="2024-02-15-preview",
    temperature=0
)

# All 37 tools (showing just Azure tools for brevity)
all_tools = [
    create_storage_account_tool,
    # ... 36 other tools from Soccer, Gmail, Maps, TomTom, Databricks, Azure
]

# System prompt
system_prompt = """
You are ADDOF (AI-Driven Data Operations Framework), an intelligent assistant.
You have access to 37 tools across 6 services:
- Soccer (6 tools)
- Gmail (3 tools)
- Google Maps (5 tools)
- TomTom (5 tools)
- Databricks (13 tools)
- Azure (11 tools)

Use the appropriate tool based on user requests.
"""

# Create prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

# Create conversation memory
memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)

# Create OpenAI Functions Agent (uses OpenAI function calling)
agent = create_openai_functions_agent(
    llm=llm,
    tools=all_tools,
    prompt=prompt
)

# Create AgentExecutor
agent_executor = AgentExecutor(
    agent=agent,
    tools=all_tools,
    memory=memory,
    verbose=True
)

print("🧠 STEP 8: LangChain agent initialized with 37 tools")

# ============================================================================
# STEP 9: Flask /chat endpoint
# ============================================================================

@app.route('/chat', methods=['POST'])
def chat():
    """Main chat endpoint"""
    data = request.json
    user_message = data.get('message', '')

    print("=" * 80)
    print("🌐 STEP 1: User message received via /chat endpoint")
    print(f"   Message: {user_message}")
    print("=" * 80)

    # ============================================================================
    # STEP 10: Agent processes the request - GPT-4 FUNCTION CALLING HAPPENS HERE
    # ============================================================================

    print("\n🧠 STEP 10: Invoking LangChain agent with GPT-4...")
    print("   GPT-4 will now:")
    print("   1. Read user message: 'Create a storage account called mystore123'")
    print("   2. Analyze ALL 37 tool descriptions")
    print("   3. Find best match: 'Create a new Azure storage account' ✅")
    print("   4. Extract parameter: storage_account_name='mystore123'")
    print("   5. Return function_call decision\n")

    # This is where the magic happens!
    # GPT-4 receives the message + all 37 tool descriptions
    # It decides which tool to call based on semantic matching
    response = agent_executor.invoke({"input": user_message})

    print("\n✅ STEP 15: Agent execution complete!")
    print(f"   Final response: {response['output'][:100]}...")

    return jsonify({
        "response": response["output"]
    })

# ============================================================================
# DEMONSTRATION: What GPT-4 receives for function calling
# ============================================================================

print("\n" + "=" * 80)
print("📊 WHAT GPT-4 RECEIVES (OpenAI Function Calling Format)")
print("=" * 80)

# This is the format sent to OpenAI API
openai_function_format = {
    "model": "gpt-4o",
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Create a storage account called mystore123"}
    ],
    "functions": [
        {
            "name": "create_storage_account",
            "description": "Create a new Azure storage account",
            "parameters": {
                "type": "object",
                "properties": {
                    "storage_account_name": {
                        "type": "string",
                        "description": "Storage account name (must be globally unique, 3-24 lowercase letters and numbers)"
                    },
                    "resource_group": {
                        "type": "string",
                        "description": "Resource group name (uses default if not specified)"
                    },
                    "location": {
                        "type": "string",
                        "description": "Azure region (e.g., 'eastus', 'westus2')"
                    },
                    "sku": {
                        "type": "string",
                        "description": "Storage SKU: Standard_LRS, Standard_GRS, etc."
                    },
                    "kind": {
                        "type": "string",
                        "description": "Storage kind: StorageV2, Storage, BlobStorage"
                    }
                },
                "required": ["storage_account_name"]
            }
        }
        # ... 36 other functions
    ],
    "function_call": "auto"  # ← GPT-4 decides which function to call
}

print(json.dumps(openai_function_format, indent=2))

print("\n" + "=" * 80)
print("🎯 GPT-4'S RESPONSE (Function Call Decision)")
print("=" * 80)

gpt4_response = {
    "role": "assistant",
    "content": None,
    "function_call": {  # ← GPT-4's decision!
        "name": "create_storage_account",
        "arguments": json.dumps({
            "storage_account_name": "mystore123",
            "resource_group": "",
            "location": "eastus",
            "sku": "Standard_LRS",
            "kind": "StorageV2"
        })
    }
}

print(json.dumps(gpt4_response, indent=2))
print("\nGPT-4 chose 'create_storage_account' based on semantic matching!")
print("Keywords matched: 'Create' + 'storage account' → tool description")

# ============================================================================
# Now let's trace through the Azure MCP Server side
# ============================================================================

print("\n" + "=" * 80)
print("☁️  AZURE MCP SERVER SIDE (azure_mcp_server.py)")
print("=" * 80)

# File: azure_mcp_server.py
from fastapi import FastAPI
from pydantic import BaseModel
import requests

# Azure configuration
AZURE_SUBSCRIPTION_ID = "1fa44ca8-b012-44b3-9618-da63389b9733"
AZURE_TENANT_ID = "93f33571-550f-43cf-b09f-cd331338d086"
AZURE_CLIENT_ID = "4914e649-7619-4ce6-b008-924f5a66c064"
AZURE_CLIENT_SECRET = "lx78Q~RYu5AIKE~gO5iSAnRdKinfYKwZKlRSpdy."
AZURE_RESOURCE_GROUP = "ai"

app_mcp = FastAPI()

class ToolRequest(BaseModel):
    tool_name: str
    arguments: dict

# ============================================================================
# STEP 11: Azure MCP receives HTTP POST request
# ============================================================================

@app_mcp.post("/execute")
async def execute_tool(request: ToolRequest):
    """Execute an Azure tool"""

    print("\n☁️  STEP 11: Azure MCP server received request")
    print(f"   Tool name: {request.tool_name}")
    print(f"   Arguments: {request.arguments}")

    # ============================================================================
    # STEP 12: Get Azure OAuth token (Service Principal authentication)
    # ============================================================================

    print("\n🔐 STEP 12: Authenticating with Azure (Service Principal)")

    def get_azure_token():
        """Get OAuth token from Azure AD"""
        url = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token"
        data = {
            "client_id": AZURE_CLIENT_ID,
            "client_secret": AZURE_CLIENT_SECRET,
            "scope": "https://management.azure.com/.default",
            "grant_type": "client_credentials"
        }
        print(f"   Requesting token from: {url}")
        response = requests.post(url, data=data)
        token = response.json()["access_token"]
        print(f"   ✅ Token received: {token[:50]}...")
        return token

    token = get_azure_token()

    # ============================================================================
    # STEP 13: Call Azure Management API
    # ============================================================================

    if request.tool_name == "create_storage_account":
        print("\n🏗️  STEP 13: Creating storage account via Azure Management API")

        storage_account_name = request.arguments.get("storage_account_name")
        resource_group = request.arguments.get("resource_group", AZURE_RESOURCE_GROUP)
        location = request.arguments.get("location", "eastus")
        sku = request.arguments.get("sku", "Standard_LRS")
        kind = request.arguments.get("kind", "StorageV2")

        print(f"   Storage account name: {storage_account_name}")
        print(f"   Resource group: {resource_group}")
        print(f"   Location: {location}")

        # Validate storage account name
        if not storage_account_name.islower() or not storage_account_name.isalnum():
            return {"result": json.dumps({"error": "Invalid storage account name"})}
        if len(storage_account_name) < 3 or len(storage_account_name) > 24:
            return {"result": json.dumps({"error": "Name must be 3-24 characters"})}

        # Build Azure API endpoint
        endpoint = f"https://management.azure.com/subscriptions/{AZURE_SUBSCRIPTION_ID}/resourceGroups/{resource_group}/providers/Microsoft.Storage/storageAccounts/{storage_account_name}?api-version=2023-01-01"

        print(f"   Azure API endpoint: {endpoint}")

        # Build request body
        body = {
            "sku": {"name": sku},
            "kind": kind,
            "location": location,
            "properties": {
                "supportsHttpsTrafficOnly": True,
                "minimumTlsVersion": "TLS1_2",
                "allowBlobPublicAccess": False
            }
        }

        print(f"   Request body: {json.dumps(body, indent=2)}")

        # Make Azure API call
        print(f"   📡 Sending PUT request to Azure Management API...")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        azure_response = requests.put(endpoint, json=body, headers=headers)

        print(f"   ✅ Azure API responded: {azure_response.status_code}")

        # ============================================================================
        # STEP 14: Return response back through the chain
        # ============================================================================

        print("\n📤 STEP 14: Returning response to Flask")

        result = {
            "success": True,
            "storage_account_name": storage_account_name,
            "resource_group": resource_group,
            "location": location,
            "sku": sku,
            "kind": kind,
            "message": f"Storage account '{storage_account_name}' creation initiated",
            "note": "Storage account creation is asynchronous and may take a few minutes"
        }

        print(f"   Result: {json.dumps(result, indent=2)}")

        return {"result": json.dumps(result, indent=2)}

# ============================================================================
# COMPLETE FLOW SUMMARY
# ============================================================================

print("\n\n" + "=" * 80)
print("📋 COMPLETE FLOW SUMMARY")
print("=" * 80)

flow_summary = """
USER INPUT: "Create a storage account called mystore123"

STEP 1:  User types message in web interface → JavaScript fetch() to /chat
         File: templates/index.html

STEP 2:  Flask receives POST /chat
         File: flask_app_simple.py, line ~1164

STEP 3:  Message passed to agent_executor.invoke()
         File: flask_app_simple.py, line ~1173

STEP 10: LangChain sends request to GPT-4 with ALL 37 tool descriptions
         OpenAI API receives:
         - User message: "Create a storage account called mystore123"
         - 37 function definitions with descriptions

         GPT-4 ANALYZES:
         - Scans all tool descriptions
         - Matches: "Create a new Azure storage account" ✅
         - Extracts: storage_account_name="mystore123"

         GPT-4 RETURNS:
         {
           "function_call": {
             "name": "create_storage_account",
             "arguments": {"storage_account_name": "mystore123", ...}
           }
         }

STEP 5:  LangChain calls: create_storage_account_func(storage_account_name="mystore123")
         File: flask_app_simple.py, line ~707

STEP 4:  Function calls: execute_tool_direct("create_storage_account", {...})
         File: flask_app_simple.py, line ~712

         Router checks tool name:
         - "create_storage_account" in azure_tools? YES ✅
         - Route to: MCP_AZURE_URL (http://localhost:8086)

STEP 11: HTTP POST to http://localhost:8086/execute
         Body: {"tool_name": "create_storage_account", "arguments": {...}}
         File: azure_mcp_server.py, line ~319

STEP 12: Azure MCP authenticates with Service Principal
         - Calls: https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
         - Gets: OAuth access token
         File: azure_mcp_server.py, line ~128

STEP 13: Azure MCP calls Azure Management API
         - Endpoint: PUT /subscriptions/{id}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/mystore123
         - Headers: Authorization: Bearer {token}
         - Body: {sku, kind, location, properties}
         File: azure_mcp_server.py, line ~490

STEP 14: Azure API creates storage account
         - Returns: 201 Created (async operation)
         - Response flows back to Azure MCP → Flask → GPT-4

STEP 15: GPT-4 receives tool result, formats natural language response
         - Input: {"success": true, "storage_account_name": "mystore123", ...}
         - Output: "I've initiated the creation of storage account 'mystore123' in the 'ai' resource group in the eastus region..."

STEP 16: Flask returns JSON response to frontend
         File: flask_app_simple.py, line ~1178

STEP 17: JavaScript displays response in chat interface
         File: templates/index.html

TOTAL TIME: ~2-3 seconds
"""

print(flow_summary)

print("\n" + "=" * 80)
print("🔑 KEY CONCEPTS")
print("=" * 80)

key_concepts = """
1. SINGLE AGENT ARCHITECTURE
   - ONE LangChain agent with access to ALL 37 tools
   - NOT multiple agents - GPT-4 chooses the right tool

2. OPENAI FUNCTION CALLING
   - GPT-4 receives tool descriptions in OpenAI function format
   - Uses semantic matching to select the right tool
   - Returns function_call with tool name + extracted parameters

3. TOOL ROUTING (execute_tool_direct)
   - Checks tool name against predefined lists (azure_tools, google_tools, etc.)
   - Routes HTTP POST to appropriate MCP server URL
   - Handles tool name transformations if needed

4. MCP SERVER PATTERN
   - Independent FastAPI servers on different ports
   - Each server handles domain-specific tools
   - Communicate via HTTP/REST API

5. SERVICE PRINCIPAL AUTHENTICATION
   - Azure MCP uses OAuth 2.0 client credentials flow
   - Gets token from Azure AD
   - Uses token for Azure Management API calls

6. DESCRIPTION-DRIVEN SELECTION
   - Tool descriptions are CRITICAL for GPT-4's selection
   - "Create a new Azure storage account" → GPT-4 matches "create storage account"
   - Better descriptions = better tool selection accuracy
"""

print(key_concepts)

print("\n" + "=" * 80)
print("✅ DEMONSTRATION COMPLETE")
print("=" * 80)
print("\nThis file shows the COMPLETE code flow from user input to Azure API.")
print("Every step is traced with actual code from your ADDOF system.")
print("\nKey files involved:")
print("  - flask_app_simple.py (Steps 1-10, 15-17)")
print("  - azure_mcp_server.py (Steps 11-14)")
print("  - OpenAI API (Step 10 - GPT-4 function calling)")
print("  - Azure Management API (Step 13 - resource creation)")
