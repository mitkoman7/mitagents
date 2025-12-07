#!/bin/bash

# Stop All MCP Servers

echo "=========================================="
echo "🛑 Stopping All MCP Servers"
echo "=========================================="

# Kill processes on each port
ports=(8081 8082 8083 8084 8085)
names=("Soccer" "Gmail" "Google Maps" "TomTom" "Databricks")

for i in "${!ports[@]}"; do
    port=${ports[$i]}
    name=${names[$i]}

    pid=$(lsof -ti:$port 2>/dev/null)

    if [ -n "$pid" ]; then
        echo "🛑 Stopping $name server (port $port, PID: $pid)..."
        kill -9 $pid 2>/dev/null
        echo "   ✅ Stopped"
    else
        echo "ℹ️  $name server (port $port) not running"
    fi
done

echo ""
echo "=========================================="
echo "✅ All servers stopped"
echo "=========================================="
