# Databricks MCP Server Setup Guide

## Overview
The Databricks MCP Server allows your AI assistant to interact with Databricks workspaces for data analytics, SQL queries, notebook execution, and cluster management.

## Features
- ✅ Execute SQL queries on Databricks SQL warehouses
- ✅ List tables and get table schemas
- ✅ Run Databricks notebooks with parameters
- ✅ Manage clusters (list, start, check status)
- ✅ Manage jobs (list, run, check status)
- ✅ Access Delta Lake data
- ✅ Run data pipelines and ETL jobs

## Setup Instructions

### 1. Get Databricks Credentials

#### Get your Databricks Host URL:
1. Log into your Databricks workspace
2. Copy the URL from your browser (e.g., `https://adb-1234567890123456.7.azuredatabricks.net`)

#### Create a Personal Access Token:
1. In Databricks workspace, click your profile icon (top-right)
2. Go to **User Settings** → **Developer** → **Access Tokens**
3. Click **Generate New Token**
4. Give it a name (e.g., "MCP Server")
5. Set expiration (or leave blank for no expiration)
6. Click **Generate**
7. **Copy the token immediately** (you won't see it again!)

#### (Optional) Get Cluster ID:
1. Go to **Compute** in the left sidebar
2. Click on your cluster
3. Copy the **Cluster ID** from the URL or cluster details

#### (Optional) Get SQL Warehouse ID:
1. Go to **SQL Warehouses** in the left sidebar
2. Click on your warehouse
3. Copy the **Warehouse ID** from the URL or details

### 2. Configure Environment Variables

Add these to your `.env` file:

```bash
# Databricks API Configuration
DATABRICKS_HOST=https://adb-xxxx.azuredatabricks.net
DATABRICKS_TOKEN=dapi1234567890abcdef
DATABRICKS_CLUSTER_ID=1234-567890-abcdef12  # Optional - for running notebooks
DATABRICKS_WAREHOUSE_ID=abc123def456        # Optional - for SQL queries
MCP_DATABRICKS_URL=http://localhost:8085
```

### 3. Start the Databricks MCP Server

```bash
# Activate your virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the Databricks server
python databricks_mcp_server.py
```

The server will start on port **8085**.

### 4. Verify Setup

Test the server health endpoint:
```bash
curl http://localhost:8085/health
```

You should see:
```json
{
  "status": "healthy",
  "api_configured": true,
  "api_working": true,
  "databricks_host": "https://adb-xxxx.azuredatabricks.net",
  "available_tools": [...]
}
```

## Available Tools

### SQL & Data Tools
- **execute_sql** - Run SQL queries on data warehouses
- **list_tables** - List tables in a catalog/schema
- **get_table_schema** - Get column definitions for a table

### Notebook Tools
- **run_notebook** - Execute notebooks with parameters
- **get_job_run_status** - Check notebook execution status

### Cluster Management
- **list_clusters** - List all compute clusters
- **get_cluster_status** - Check if cluster is running
- **start_cluster** - Start a stopped cluster

### Job Management
- **list_jobs** - List all scheduled/on-demand jobs
- **run_job** - Trigger a job execution
- **get_job_run_status** - Check job run status

## Example Usage

### Query Data:
```
"Show me the first 10 rows from the sales table"
"What tables are available in the default database?"
"What's the schema of the customers table?"
```

### Run Notebooks:
```
"Run the ETL notebook at /Users/me/data_pipeline"
"Execute the ML training notebook with parameter epochs=10"
```

### Manage Clusters:
```
"List all my Databricks clusters"
"What's the status of my main cluster?"
"Start cluster 1234-567890-abcdef12"
```

### Manage Jobs:
```
"Show me all my Databricks jobs"
"Run job 123"
"What's the status of run 456?"
```

## Security Notes

⚠️ **Important Security Considerations:**

1. **Never commit your `.env` file** - It contains sensitive credentials
2. **Use personal access tokens** - Don't share your credentials
3. **Set token expiration** - Use short-lived tokens when possible
4. **Limit token permissions** - Create tokens with minimal required permissions
5. **Rotate tokens regularly** - Generate new tokens periodically

## Troubleshooting

### "api_configured": false
- Check that `DATABRICKS_HOST` and `DATABRICKS_TOKEN` are set in `.env`
- Verify the environment variables are loaded

### "api_working": false
- Verify your token is valid and not expired
- Check that your Databricks workspace URL is correct
- Ensure network connectivity to Databricks

### SQL queries fail
- Check that `DATABRICKS_WAREHOUSE_ID` is set
- Verify the warehouse is running (SQL warehouses auto-stop)
- Ensure you have permissions to query the data

### Notebooks won't run
- Check that `DATABRICKS_CLUSTER_ID` is set
- Verify the cluster is running (use `get_cluster_status`)
- Use `start_cluster` if the cluster is stopped
- Ensure the notebook path is correct (starts with `/`)

## Integration with Flask App

Once the Databricks server is running, the Flask app will automatically:
1. Detect it via health checks
2. Register all 10 Databricks tools with the agent
3. Allow conversational queries like "query my sales data" or "run my ETL job"

The agent will intelligently route Databricks-related requests to the appropriate tools.

## Documentation

- [Databricks REST API Docs](https://docs.databricks.com/dev-tools/api/latest/index.html)
- [Personal Access Tokens](https://docs.databricks.com/dev-tools/auth.html#databricks-personal-access-tokens)
- [SQL Statement Execution API](https://docs.databricks.com/sql/api/sql-execution.html)
- [Jobs API](https://docs.databricks.com/dev-tools/api/latest/jobs.html)
- [Clusters API](https://docs.databricks.com/dev-tools/api/latest/clusters.html)

## Support

If you encounter issues:
1. Check the server logs for error messages
2. Verify your credentials are correct
3. Test API access using `curl` or Postman
4. Check Databricks workspace permissions

---

**Ready to analyze data with AI!** 📊🤖
