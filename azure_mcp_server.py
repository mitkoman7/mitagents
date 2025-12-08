"""
Azure Services MCP Server
Provides tools for Azure Resource Management, VMs, Storage, Databases, etc.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os
import json
from dotenv import load_dotenv
import httpx

load_dotenv()

app = FastAPI(title="Azure MCP Server")

# Azure Configuration
AZURE_SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
AZURE_RESOURCE_GROUP = os.getenv("AZURE_RESOURCE_GROUP", "")

# Azure Management API base URL
AZURE_MGMT_BASE = "https://management.azure.com"
AZURE_API_VERSION = "2023-07-01"

class ToolRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]

class Tool(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]

def get_azure_token():
    """Get Azure access token using service principal"""
    if not all([AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET]):
        return None

    token_url = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token"

    data = {
        "grant_type": "client_credentials",
        "client_id": AZURE_CLIENT_ID,
        "client_secret": AZURE_CLIENT_SECRET,
        "scope": "https://management.azure.com/.default"
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(token_url, data=data)
            response.raise_for_status()
            return response.json().get("access_token")
    except Exception as e:
        print(f"❌ Failed to get Azure token: {e}")
        return None

def azure_api_request(method: str, endpoint: str, data: dict = None):
    """Make authenticated request to Azure Management API"""
    token = get_azure_token()
    if not token:
        return {"error": "Azure authentication failed. Check credentials in .env file."}

    url = f"{AZURE_MGMT_BASE}{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            if method == "GET":
                response = client.get(url, headers=headers)
            elif method == "POST":
                response = client.post(url, headers=headers, json=data)
            elif method == "PUT":
                response = client.put(url, headers=headers, json=data)
            elif method == "DELETE":
                response = client.delete(url, headers=headers)
            else:
                return {"error": f"Unsupported HTTP method: {method}"}

            response.raise_for_status()

            # Some Azure APIs return 202 Accepted with no content
            if response.status_code == 202:
                return {"success": True, "status": "Accepted", "message": "Operation initiated"}

            # Some APIs return 204 No Content
            if response.status_code == 204:
                return {"success": True, "message": "Operation completed successfully"}

            return response.json() if response.text else {"success": True}

    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
async def root():
    return {
        "message": "Azure MCP Server",
        "configured": all([AZURE_SUBSCRIPTION_ID, AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET]),
        "endpoints": {
            "tools": "/tools",
            "execute": "/execute",
            "health": "/health"
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    configured = all([AZURE_SUBSCRIPTION_ID, AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET])

    if configured:
        # Test authentication
        token = get_azure_token()
        if token:
            return {"status": "healthy", "azure_auth": "connected"}
        else:
            return {"status": "degraded", "azure_auth": "failed"}
    else:
        return {"status": "not_configured", "message": "Azure credentials missing in .env"}

@app.get("/tools")
async def list_tools() -> List[Tool]:
    """List all available Azure tools"""
    return [
        Tool(
            name="list_resource_groups",
            description="List all resource groups in the Azure subscription",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="list_vms",
            description="List all virtual machines in a resource group or subscription",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_group": {
                        "type": "string",
                        "description": "Resource group name (optional, lists all VMs if not specified)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_vm_status",
            description="Get the power state and details of a specific virtual machine",
            inputSchema={
                "type": "object",
                "properties": {
                    "vm_name": {
                        "type": "string",
                        "description": "Virtual machine name"
                    },
                    "resource_group": {
                        "type": "string",
                        "description": "Resource group name (uses default if not specified)"
                    }
                },
                "required": ["vm_name"]
            }
        ),
        Tool(
            name="start_vm",
            description="Start a stopped virtual machine",
            inputSchema={
                "type": "object",
                "properties": {
                    "vm_name": {
                        "type": "string",
                        "description": "Virtual machine name"
                    },
                    "resource_group": {
                        "type": "string",
                        "description": "Resource group name (uses default if not specified)"
                    }
                },
                "required": ["vm_name"]
            }
        ),
        Tool(
            name="stop_vm",
            description="Stop a running virtual machine (deallocates to save costs)",
            inputSchema={
                "type": "object",
                "properties": {
                    "vm_name": {
                        "type": "string",
                        "description": "Virtual machine name"
                    },
                    "resource_group": {
                        "type": "string",
                        "description": "Resource group name (uses default if not specified)"
                    }
                },
                "required": ["vm_name"]
            }
        ),
        Tool(
            name="restart_vm",
            description="Restart a virtual machine",
            inputSchema={
                "type": "object",
                "properties": {
                    "vm_name": {
                        "type": "string",
                        "description": "Virtual machine name"
                    },
                    "resource_group": {
                        "type": "string",
                        "description": "Resource group name (uses default if not specified)"
                    }
                },
                "required": ["vm_name"]
            }
        ),
        Tool(
            name="list_storage_accounts",
            description="List all storage accounts in a resource group or subscription",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_group": {
                        "type": "string",
                        "description": "Resource group name (optional)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="list_databases",
            description="List all SQL databases in a resource group or subscription",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_group": {
                        "type": "string",
                        "description": "Resource group name (optional)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_subscription_info",
            description="Get information about the current Azure subscription",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="list_resources",
            description="List all resources in a resource group with filtering options",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_group": {
                        "type": "string",
                        "description": "Resource group name (uses default if not specified)"
                    },
                    "resource_type": {
                        "type": "string",
                        "description": "Filter by resource type (e.g., 'Microsoft.Compute/virtualMachines')"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="create_storage_account",
            description="Create a new Azure storage account",
            inputSchema={
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
                        "description": "Azure region (e.g., 'eastus', 'westus2')",
                        "default": "eastus"
                    },
                    "sku": {
                        "type": "string",
                        "description": "Storage SKU: Standard_LRS, Standard_GRS, Standard_RAGRS, Standard_ZRS, Premium_LRS",
                        "default": "Standard_LRS"
                    },
                    "kind": {
                        "type": "string",
                        "description": "Storage kind: StorageV2, Storage, BlobStorage",
                        "default": "StorageV2"
                    }
                },
                "required": ["storage_account_name"]
            }
        )
    ]

@app.post("/execute")
async def execute_tool(request: ToolRequest):
    """Execute an Azure tool"""
    try:
        print(f"☁️  Executing Azure tool: {request.tool_name}")
        print(f"📦 Arguments: {request.arguments}")

        if not AZURE_SUBSCRIPTION_ID:
            return {"result": json.dumps({"error": "AZURE_SUBSCRIPTION_ID not configured in .env"})}

        # List Resource Groups
        if request.tool_name == "list_resource_groups":
            endpoint = f"/subscriptions/{AZURE_SUBSCRIPTION_ID}/resourcegroups?api-version={AZURE_API_VERSION}"
            result = azure_api_request("GET", endpoint)

            if "value" in result:
                rgs = [{"name": rg["name"], "location": rg["location"], "id": rg["id"]} for rg in result["value"]]
                return {"result": json.dumps({"resource_groups": rgs, "count": len(rgs)}, indent=2)}

            return {"result": json.dumps(result, indent=2)}

        # List Virtual Machines
        elif request.tool_name == "list_vms":
            resource_group = request.arguments.get("resource_group", AZURE_RESOURCE_GROUP)

            if resource_group:
                endpoint = f"/subscriptions/{AZURE_SUBSCRIPTION_ID}/resourceGroups/{resource_group}/providers/Microsoft.Compute/virtualMachines?api-version=2023-03-01"
            else:
                endpoint = f"/subscriptions/{AZURE_SUBSCRIPTION_ID}/providers/Microsoft.Compute/virtualMachines?api-version=2023-03-01"

            result = azure_api_request("GET", endpoint)

            if "value" in result:
                vms = [{
                    "name": vm["name"],
                    "location": vm["location"],
                    "id": vm["id"],
                    "vmSize": vm.get("properties", {}).get("hardwareProfile", {}).get("vmSize")
                } for vm in result["value"]]
                return {"result": json.dumps({"virtual_machines": vms, "count": len(vms)}, indent=2)}

            return {"result": json.dumps(result, indent=2)}

        # Get VM Status
        elif request.tool_name == "get_vm_status":
            vm_name = request.arguments.get("vm_name")
            resource_group = request.arguments.get("resource_group", AZURE_RESOURCE_GROUP)

            if not vm_name:
                return {"result": json.dumps({"error": "vm_name is required"})}
            if not resource_group:
                return {"result": json.dumps({"error": "resource_group is required (set AZURE_RESOURCE_GROUP in .env or provide it)"})}

            endpoint = f"/subscriptions/{AZURE_SUBSCRIPTION_ID}/resourceGroups/{resource_group}/providers/Microsoft.Compute/virtualMachines/{vm_name}/instanceView?api-version=2023-03-01"
            result = azure_api_request("GET", endpoint)

            if "statuses" in result:
                statuses = result["statuses"]
                power_state = next((s["displayStatus"] for s in statuses if s["code"].startswith("PowerState/")), "Unknown")

                return {"result": json.dumps({
                    "vm_name": vm_name,
                    "power_state": power_state,
                    "statuses": statuses
                }, indent=2)}

            return {"result": json.dumps(result, indent=2)}

        # Start VM
        elif request.tool_name == "start_vm":
            vm_name = request.arguments.get("vm_name")
            resource_group = request.arguments.get("resource_group", AZURE_RESOURCE_GROUP)

            if not vm_name:
                return {"result": json.dumps({"error": "vm_name is required"})}
            if not resource_group:
                return {"result": json.dumps({"error": "resource_group is required"})}

            endpoint = f"/subscriptions/{AZURE_SUBSCRIPTION_ID}/resourceGroups/{resource_group}/providers/Microsoft.Compute/virtualMachines/{vm_name}/start?api-version=2023-03-01"
            result = azure_api_request("POST", endpoint)

            return {"result": json.dumps({"vm_name": vm_name, "action": "start", "result": result}, indent=2)}

        # Stop VM
        elif request.tool_name == "stop_vm":
            vm_name = request.arguments.get("vm_name")
            resource_group = request.arguments.get("resource_group", AZURE_RESOURCE_GROUP)

            if not vm_name:
                return {"result": json.dumps({"error": "vm_name is required"})}
            if not resource_group:
                return {"result": json.dumps({"error": "resource_group is required"})}

            endpoint = f"/subscriptions/{AZURE_SUBSCRIPTION_ID}/resourceGroups/{resource_group}/providers/Microsoft.Compute/virtualMachines/{vm_name}/deallocate?api-version=2023-03-01"
            result = azure_api_request("POST", endpoint)

            return {"result": json.dumps({"vm_name": vm_name, "action": "stop (deallocate)", "result": result}, indent=2)}

        # Restart VM
        elif request.tool_name == "restart_vm":
            vm_name = request.arguments.get("vm_name")
            resource_group = request.arguments.get("resource_group", AZURE_RESOURCE_GROUP)

            if not vm_name:
                return {"result": json.dumps({"error": "vm_name is required"})}
            if not resource_group:
                return {"result": json.dumps({"error": "resource_group is required"})}

            endpoint = f"/subscriptions/{AZURE_SUBSCRIPTION_ID}/resourceGroups/{resource_group}/providers/Microsoft.Compute/virtualMachines/{vm_name}/restart?api-version=2023-03-01"
            result = azure_api_request("POST", endpoint)

            return {"result": json.dumps({"vm_name": vm_name, "action": "restart", "result": result}, indent=2)}

        # List Storage Accounts
        elif request.tool_name == "list_storage_accounts":
            resource_group = request.arguments.get("resource_group")

            if resource_group:
                endpoint = f"/subscriptions/{AZURE_SUBSCRIPTION_ID}/resourceGroups/{resource_group}/providers/Microsoft.Storage/storageAccounts?api-version=2023-01-01"
            else:
                endpoint = f"/subscriptions/{AZURE_SUBSCRIPTION_ID}/providers/Microsoft.Storage/storageAccounts?api-version=2023-01-01"

            result = azure_api_request("GET", endpoint)

            if "value" in result:
                accounts = [{
                    "name": acc["name"],
                    "location": acc["location"],
                    "sku": acc.get("sku", {}).get("name"),
                    "kind": acc.get("kind")
                } for acc in result["value"]]
                return {"result": json.dumps({"storage_accounts": accounts, "count": len(accounts)}, indent=2)}

            return {"result": json.dumps(result, indent=2)}

        # List SQL Databases
        elif request.tool_name == "list_databases":
            resource_group = request.arguments.get("resource_group")

            if resource_group:
                endpoint = f"/subscriptions/{AZURE_SUBSCRIPTION_ID}/resourceGroups/{resource_group}/providers/Microsoft.Sql/servers?api-version=2021-11-01"
            else:
                endpoint = f"/subscriptions/{AZURE_SUBSCRIPTION_ID}/providers/Microsoft.Sql/servers?api-version=2021-11-01"

            result = azure_api_request("GET", endpoint)

            if "value" in result:
                servers = [{
                    "name": srv["name"],
                    "location": srv["location"],
                    "version": srv.get("properties", {}).get("version"),
                    "state": srv.get("properties", {}).get("state")
                } for srv in result["value"]]
                return {"result": json.dumps({"sql_servers": servers, "count": len(servers)}, indent=2)}

            return {"result": json.dumps(result, indent=2)}

        # Get Subscription Info
        elif request.tool_name == "get_subscription_info":
            endpoint = f"/subscriptions/{AZURE_SUBSCRIPTION_ID}?api-version={AZURE_API_VERSION}"
            result = azure_api_request("GET", endpoint)

            if "displayName" in result:
                info = {
                    "subscription_id": result.get("subscriptionId"),
                    "display_name": result.get("displayName"),
                    "state": result.get("state"),
                    "tenant_id": result.get("tenantId")
                }
                return {"result": json.dumps(info, indent=2)}

            return {"result": json.dumps(result, indent=2)}

        # List Resources
        elif request.tool_name == "list_resources":
            resource_group = request.arguments.get("resource_group", AZURE_RESOURCE_GROUP)
            resource_type = request.arguments.get("resource_type")

            if resource_group:
                endpoint = f"/subscriptions/{AZURE_SUBSCRIPTION_ID}/resourceGroups/{resource_group}/resources?api-version={AZURE_API_VERSION}"
            else:
                endpoint = f"/subscriptions/{AZURE_SUBSCRIPTION_ID}/resources?api-version={AZURE_API_VERSION}"

            result = azure_api_request("GET", endpoint)

            if "value" in result:
                resources = result["value"]

                # Filter by type if specified
                if resource_type:
                    resources = [r for r in resources if r.get("type") == resource_type]

                simplified = [{
                    "name": r["name"],
                    "type": r["type"],
                    "location": r["location"],
                    "id": r["id"]
                } for r in resources]

                return {"result": json.dumps({"resources": simplified, "count": len(simplified)}, indent=2)}

            return {"result": json.dumps(result, indent=2)}

        # Create Storage Account
        elif request.tool_name == "create_storage_account":
            storage_account_name = request.arguments.get("storage_account_name")
            resource_group = request.arguments.get("resource_group", AZURE_RESOURCE_GROUP)
            location = request.arguments.get("location", "eastus")
            sku = request.arguments.get("sku", "Standard_LRS")
            kind = request.arguments.get("kind", "StorageV2")

            if not storage_account_name:
                return {"result": json.dumps({"error": "storage_account_name is required"})}
            if not resource_group:
                return {"result": json.dumps({"error": "resource_group is required (set AZURE_RESOURCE_GROUP in .env or provide it)"})}

            # Validate storage account name
            if not storage_account_name.islower() or not storage_account_name.isalnum():
                return {"result": json.dumps({"error": "storage_account_name must contain only lowercase letters and numbers"})}
            if len(storage_account_name) < 3 or len(storage_account_name) > 24:
                return {"result": json.dumps({"error": "storage_account_name must be between 3 and 24 characters"})}

            endpoint = f"/subscriptions/{AZURE_SUBSCRIPTION_ID}/resourceGroups/{resource_group}/providers/Microsoft.Storage/storageAccounts/{storage_account_name}?api-version=2023-01-01"

            body = {
                "sku": {
                    "name": sku
                },
                "kind": kind,
                "location": location,
                "properties": {
                    "supportsHttpsTrafficOnly": True,
                    "minimumTlsVersion": "TLS1_2",
                    "allowBlobPublicAccess": False
                }
            }

            result = azure_api_request("PUT", endpoint, body)

            if "error" in result:
                return {"result": json.dumps(result, indent=2)}

            return {"result": json.dumps({
                "success": True,
                "storage_account_name": storage_account_name,
                "resource_group": resource_group,
                "location": location,
                "sku": sku,
                "kind": kind,
                "message": f"Storage account '{storage_account_name}' creation initiated",
                "note": "Storage account creation is asynchronous and may take a few minutes"
            }, indent=2)}

        else:
            return {"result": json.dumps({"error": f"Unknown tool: {request.tool_name}"})}

    except Exception as e:
        print(f"❌ Error executing {request.tool_name}: {e}")
        return {"result": json.dumps({"error": str(e)})}

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("☁️  Starting Azure MCP Server")
    print("=" * 60)
    print(f"🌐 Server: http://localhost:8086")
    print(f"📋 Tools: http://localhost:8086/tools")
    print(f"❤️  Health: http://localhost:8086/health")
    print()

    configured = all([AZURE_SUBSCRIPTION_ID, AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET])

    if configured:
        print("✅ Azure credentials configured")
        print(f"📊 Subscription ID: {AZURE_SUBSCRIPTION_ID[:8]}...")
        if AZURE_RESOURCE_GROUP:
            print(f"📁 Default Resource Group: {AZURE_RESOURCE_GROUP}")
    else:
        print("⚠️  Azure credentials not configured!")
        print()
        print("Required .env variables:")
        print("  - AZURE_SUBSCRIPTION_ID")
        print("  - AZURE_TENANT_ID")
        print("  - AZURE_CLIENT_ID")
        print("  - AZURE_CLIENT_SECRET")
        print("  - AZURE_RESOURCE_GROUP (optional, but recommended)")

    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8086)
