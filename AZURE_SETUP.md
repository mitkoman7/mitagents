# Azure MCP Server Setup Guide

## 🎯 Overview

The Azure MCP server provides tools to manage Azure resources including:
- Virtual Machines (start, stop, restart, status)
- Resource Groups
- Storage Accounts
- SQL Databases
- Subscription information
- General resource listing

## 📋 Prerequisites

You need an **Azure Service Principal** with appropriate permissions to manage resources.

## 🔧 Setup Steps

### Step 1: Create a Service Principal

Run these commands in Azure CLI:

```bash
# Login to Azure
az login

# Get your subscription ID
az account show --query id -o tsv

# Create a service principal (replace 'my-app-name' with your app name)
az ad sp create-for-rbac --name "my-azure-mcp-app" --role Contributor --scopes /subscriptions/{your-subscription-id}
```

This will output something like:

```json
{
  "appId": "xxxx-xxxx-xxxx-xxxx",
  "displayName": "my-azure-mcp-app",
  "password": "yyyy-yyyy-yyyy-yyyy",
  "tenant": "zzzz-zzzz-zzzz-zzzz"
}
```

### Step 2: Configure .env File

Update your `.env` file with the credentials:

```bash
# Azure Resource Management Configuration
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_TENANT_ID=tenant-from-above
AZURE_CLIENT_ID=appId-from-above
AZURE_CLIENT_SECRET=password-from-above
AZURE_RESOURCE_GROUP=your-default-resource-group-name
MCP_AZURE_URL=http://localhost:8086
```

**Important Notes:**
- `AZURE_CLIENT_ID` = `appId` from the output
- `AZURE_CLIENT_SECRET` = `password` from the output
- `AZURE_TENANT_ID` = `tenant` from the output
- `AZURE_RESOURCE_GROUP` is optional but recommended (saves you from specifying it in every call)

### Step 3: Start the Azure MCP Server

```bash
cd /Users/dimitargrigorov/soccer
./venv/bin/python3 azure_mcp_server.py
```

Or run in background:

```bash
./venv/bin/python3 azure_mcp_server.py > logs/azure_server.log 2>&1 &
```

### Step 4: Test the Server

```bash
# Check health
curl http://localhost:8086/health

# List available tools
curl http://localhost:8086/tools
```

## 🛠️ Available Tools

### Resource Management

1. **list_resource_groups** - List all resource groups in subscription
   ```json
   {"tool_name": "list_resource_groups", "arguments": {}}
   ```

2. **list_resources** - List all resources in a resource group
   ```json
   {"tool_name": "list_resources", "arguments": {"resource_group": "my-rg"}}
   ```

3. **get_subscription_info** - Get subscription details
   ```json
   {"tool_name": "get_subscription_info", "arguments": {}}
   ```

### Virtual Machines

4. **list_vms** - List all VMs
   ```json
   {"tool_name": "list_vms", "arguments": {"resource_group": "my-rg"}}
   ```

5. **get_vm_status** - Get VM power state
   ```json
   {"tool_name": "get_vm_status", "arguments": {"vm_name": "myVM", "resource_group": "my-rg"}}
   ```

6. **start_vm** - Start a stopped VM
   ```json
   {"tool_name": "start_vm", "arguments": {"vm_name": "myVM", "resource_group": "my-rg"}}
   ```

7. **stop_vm** - Stop and deallocate a VM (saves costs)
   ```json
   {"tool_name": "stop_vm", "arguments": {"vm_name": "myVM", "resource_group": "my-rg"}}
   ```

8. **restart_vm** - Restart a VM
   ```json
   {"tool_name": "restart_vm", "arguments": {"vm_name": "myVM", "resource_group": "my-rg"}}
   ```

### Storage & Databases

9. **list_storage_accounts** - List all storage accounts
   ```json
   {"tool_name": "list_storage_accounts", "arguments": {"resource_group": "my-rg"}}
   ```

10. **list_databases** - List all SQL servers
    ```json
    {"tool_name": "list_databases", "arguments": {"resource_group": "my-rg"}}
    ```

## 🎮 Example Queries (via Flask App)

Once integrated with Flask, you can ask:

```
"List all my Azure resource groups"
"What VMs do I have in production-rg?"
"What's the status of web-server-01?"
"Start the VM named web-server-01"
"Stop the dev-machine VM to save costs"
"List all my storage accounts"
"Show me all SQL servers"
"What resources are in my production-rg?"
```

## 🔐 Security Best Practices

1. **Least Privilege**: Create a service principal with only the permissions you need
   ```bash
   # Reader role (read-only)
   az ad sp create-for-rbac --name "azure-mcp-readonly" --role Reader --scopes /subscriptions/{sub-id}

   # Virtual Machine Contributor (only VM management)
   az ad sp create-for-rbac --name "azure-mcp-vm" --role "Virtual Machine Contributor" --scopes /subscriptions/{sub-id}
   ```

2. **Scope Limitation**: Limit to specific resource groups
   ```bash
   az ad sp create-for-rbac --name "azure-mcp-rg" --role Contributor --scopes /subscriptions/{sub-id}/resourceGroups/my-rg
   ```

3. **Credential Rotation**: Regularly rotate your client secret
   ```bash
   az ad sp credential reset --id {client-id}
   ```

4. **Environment Variables**: Never commit `.env` to version control (it's in `.gitignore`)

## 🚨 Troubleshooting

### "Azure authentication failed"
- Verify your credentials in `.env`
- Check if service principal exists: `az ad sp show --id {client-id}`
- Ensure service principal has proper role assignment

### "HTTP 403 Forbidden"
- Service principal doesn't have permissions
- Add role: `az role assignment create --assignee {client-id} --role Contributor --scope /subscriptions/{sub-id}`

### "Subscription not found"
- Verify subscription ID: `az account show`
- Check if service principal has access: `az role assignment list --assignee {client-id}`

### "Resource group not found"
- Verify resource group name: `az group list --output table`
- Update `AZURE_RESOURCE_GROUP` in `.env`

## 📊 Cost Considerations

- **Reading data** (list VMs, get status, etc.) has NO direct cost
- **Starting/stopping VMs** has no API cost, but running VMs incur compute costs
- **Stopped (deallocated) VMs** don't incur compute costs (only storage costs)
- Use `stop_vm` (deallocate) instead of just shutting down to save money

## 🔗 Integration with Flask

The Azure MCP server will automatically be integrated when you:
1. Update `flask_app_simple.py` to include Azure tools
2. Add Azure tool routing in `execute_tool_direct()`
3. Create LangChain tool wrappers for Azure functions

Would you like me to integrate this into your Flask app now?
