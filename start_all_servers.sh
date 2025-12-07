#!/bin/bash

# Start All MCP Servers
# This script starts all MCP servers in the background

echo "=========================================="
echo "🚀 Starting All MCP Servers"
echo "=========================================="

# Activate virtual environment
source venv/bin/activate

# Kill any existing server processes on the ports
echo "🧹 Cleaning up existing servers..."
lsof -ti:8081 | xargs kill -9 2>/dev/null
lsof -ti:8082 | xargs kill -9 2>/dev/null
lsof -ti:8083 | xargs kill -9 2>/dev/null
lsof -ti:8084 | xargs kill -9 2>/dev/null
lsof -ti:8085 | xargs kill -9 2>/dev/null

sleep 2

# Start Soccer MCP Server (Port 8081)
if [ -f "map_server.py" ]; then
    echo "⚽ Starting Soccer MCP Server on port 8081..."
    nohup python3 map_server.py > logs/soccer_server.log 2>&1 &
    echo "   PID: $!"
else
    echo "⚠️  Soccer server (map_server.py) not found - skipping"
fi

sleep 1

# Start Google/Gmail MCP Server (Port 8082)
if [ -f "google_mcp_server_simple.py" ]; then
    echo "📧 Starting Gmail MCP Server on port 8082..."
    nohup python3 google_mcp_server_simple.py > logs/gmail_server.log 2>&1 &
    echo "   PID: $!"
else
    echo "⚠️  Gmail server not found - skipping"
fi

sleep 1

# Start Google Maps MCP Server (Port 8083)
if [ -f "google_maps_mcp_server.py" ]; then
    echo "🗺️  Starting Google Maps MCP Server on port 8083..."
    nohup python3 google_maps_mcp_server.py > logs/maps_server.log 2>&1 &
    echo "   PID: $!"
else
    echo "⚠️  Google Maps server not found - skipping"
fi

sleep 1

# Start TomTom MCP Server (Port 8084)
if [ -f "tomtom_mcp_server.py" ]; then
    echo "🚗 Starting TomTom MCP Server on port 8084..."
    nohup python3 tomtom_mcp_server.py > logs/tomtom_server.log 2>&1 &
    echo "   PID: $!"
else
    echo "⚠️  TomTom server not found - skipping"
fi

sleep 1

# Start Databricks MCP Server (Port 8085)
if [ -f "databricks_mcp_server.py" ]; then
    echo "📊 Starting Databricks MCP Server on port 8085..."
    nohup python3 databricks_mcp_server.py > logs/databricks_server.log 2>&1 &
    echo "   PID: $!"
else
    echo "⚠️  Databricks server not found - skipping"
fi

echo ""
echo "⏳ Waiting for servers to start..."
sleep 5

echo ""
echo "=========================================="
echo "✅ Server Status Check"
echo "=========================================="

# Check each server
check_server() {
    local port=$1
    local name=$2
    if curl -s http://localhost:$port/health > /dev/null 2>&1; then
        echo "✅ $name (port $port): Running"
    else
        echo "❌ $name (port $port): Not responding"
    fi
}

check_server 8081 "Soccer Server    "
check_server 8082 "Gmail Server     "
check_server 8083 "Google Maps      "
check_server 8084 "TomTom Maps      "
check_server 8085 "Databricks       "

echo ""
echo "=========================================="
echo "📋 Useful Commands"
echo "=========================================="
echo "Stop all servers:    ./stop_all_servers.sh"
echo "View server logs:    tail -f logs/*.log"
echo "Check processes:     ps aux | grep python"
echo ""
echo "🤖 Ready to run agents!"
echo "=========================================="
