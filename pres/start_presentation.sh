#!/bin/bash

echo "=========================================="
echo "🎯 Starting AI Assistant - Presentation"
echo "=========================================="
echo ""

# Create logs directory if it doesn't exist
mkdir -p logs

# Kill any existing processes
echo "🧹 Cleaning up existing processes..."
pkill -f gmail_mcp_server
pkill -f databricks_mcp_server
pkill -f flask_app_pres
sleep 2

# Navigate to the pres directory
cd "$(dirname "$0")"

# Start Gmail MCP Server
echo "📧 Starting Gmail MCP Server on port 8082..."
../venv/bin/python3 gmail_mcp_server.py > logs/gmail_server.log 2>&1 &
sleep 2

# Start Databricks MCP Server
echo "📊 Starting Databricks MCP Server on port 8085..."
../venv/bin/python3 databricks_mcp_server.py > logs/databricks_server.log 2>&1 &
sleep 3

# Start Flask App
echo "🌐 Starting Flask Presentation App on port 5007..."
../venv/bin/python3 flask_app_pres.py > logs/flask_app.log 2>&1 &
sleep 3

echo ""
echo "=========================================="
echo "✅ All services started!"
echo "=========================================="
echo ""
echo "📧 Gmail MCP:       http://localhost:8082"
echo "📊 Databricks MCP:  http://localhost:8085"
echo "🌐 Web App:         http://localhost:5007"
echo ""
echo "Logs are in: pres/logs/"
echo ""
echo "To stop all services, run: pkill -f gmail_mcp_server && pkill -f databricks_mcp_server && pkill -f flask_app_pres"
echo ""
