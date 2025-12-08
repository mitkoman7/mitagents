#!/bin/bash

echo "=========================================="
echo "🚀 Starting ADDOF - Full System with Azure"
echo "=========================================="
echo ""

# Create logs directory if it doesn't exist
mkdir -p logs

# Kill any existing processes
echo "🧹 Cleaning up existing processes..."
pkill -f soccer_mcp_server
pkill -f gmail_mcp_server
pkill -f maps_mcp_server
pkill -f tomtom_mcp_server
pkill -f databricks_mcp_server
pkill -f azure_mcp_server
pkill -f flask_app_simple
sleep 2

# Start Soccer MCP Server
echo "⚽ Starting Soccer MCP Server on port 8081..."
./venv/bin/python3 soccer_mcp_server.py > logs/soccer_server.log 2>&1 &
sleep 2

# Start Gmail MCP Server
echo "📧 Starting Gmail MCP Server on port 8082..."
./venv/bin/python3 gmail_mcp_server.py > logs/gmail_server.log 2>&1 &
sleep 2

# Start Maps MCP Server
echo "🗺️  Starting Maps MCP Server on port 8083..."
./venv/bin/python3 maps_mcp_server.py > logs/maps_server.log 2>&1 &
sleep 2

# Start TomTom MCP Server
echo "🚗 Starting TomTom MCP Server on port 8084..."
./venv/bin/python3 tomtom_mcp_server.py > logs/tomtom_server.log 2>&1 &
sleep 2

# Start Databricks MCP Server
echo "📊 Starting Databricks MCP Server on port 8085..."
./venv/bin/python3 databricks_mcp_server.py > logs/databricks_server.log 2>&1 &
sleep 3

# Start Azure MCP Server
echo "☁️  Starting Azure MCP Server on port 8086..."
./venv/bin/python3 azure_mcp_server.py > logs/azure_server.log 2>&1 &
sleep 3

# Start Flask App
echo "🌐 Starting Flask App on port 5006..."
./venv/bin/python3 flask_app_simple.py > logs/flask_app.log 2>&1 &
sleep 3

echo ""
echo "=========================================="
echo "✅ All services started!"
echo "=========================================="
echo ""
echo "⚽ Soccer MCP:      http://localhost:8081"
echo "📧 Gmail MCP:       http://localhost:8082"
echo "🗺️  Maps MCP:        http://localhost:8083"
echo "🚗 TomTom MCP:      http://localhost:8084"
echo "📊 Databricks MCP:  http://localhost:8085"
echo "☁️  Azure MCP:       http://localhost:8086"
echo "🌐 Web App:         http://localhost:5006"
echo ""
echo "Logs are in: logs/"
echo ""
echo "To stop all services, run:"
echo "pkill -f soccer_mcp_server && pkill -f gmail_mcp_server && pkill -f maps_mcp_server && pkill -f tomtom_mcp_server && pkill -f databricks_mcp_server && pkill -f azure_mcp_server && pkill -f flask_app_simple"
echo ""
