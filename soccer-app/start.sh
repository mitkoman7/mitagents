#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate

# Clear any stale processes on these ports
lsof -ti :8087 | xargs kill -9 2>/dev/null
lsof -ti :5010 | xargs kill -9 2>/dev/null

echo "⚽ Starting Soccer MCP Server on port 8087..."
python mcp_server.py &
MCP_PID=$!

sleep 2

echo "⚽ Starting Soccer AI Flask app on port 5010..."
python app.py &
FLASK_PID=$!

echo ""
echo "✅ Soccer AI Analyst running at http://localhost:5010"
echo "   MCP PID: $MCP_PID | Flask PID: $FLASK_PID"
echo ""
echo "Press Ctrl+C to stop both servers."

trap "kill $MCP_PID $FLASK_PID 2>/dev/null; echo 'Stopped.'" EXIT
wait
