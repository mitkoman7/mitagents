#!/usr/bin/env python3
"""
Start All MCP Servers
Run this to start all MCP servers at once
"""

import subprocess
import time
import os
import signal
import sys
import httpx

# Server configurations
SERVERS = [
    {"name": "Soccer", "file": "map_server.py", "port": 8081},
    {"name": "Gmail", "file": "google_mcp_server_simple.py", "port": 8082},
    {"name": "Google Maps", "file": "google_maps_mcp_server.py", "port": 8083},
    {"name": "TomTom", "file": "tomtom_mcp_server.py", "port": 8084},
    {"name": "Databricks", "file": "databricks_mcp_server.py", "port": 8085},
]

processes = []

def kill_port(port):
    """Kill process running on a specific port"""
    try:
        # Find process on port
        result = subprocess.run(
            f"lsof -ti:{port}",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            pid = result.stdout.strip()
            os.kill(int(pid), signal.SIGKILL)
            print(f"   Killed existing process on port {port}")
            time.sleep(0.5)
    except:
        pass

def check_server(port, timeout=2):
    """Check if server is responding"""
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(f"http://localhost:{port}/health")
            return response.status_code == 200
    except:
        return False

def start_servers():
    """Start all MCP servers"""
    print("=" * 60)
    print("🚀 Starting All MCP Servers")
    print("=" * 60)
    print()

    # Clean up existing processes
    print("🧹 Cleaning up existing servers...")
    for server in SERVERS:
        kill_port(server["port"])
    print()

    # Create logs directory
    os.makedirs("logs", exist_ok=True)

    # Start each server
    for server in SERVERS:
        if not os.path.exists(server["file"]):
            print(f"⚠️  {server['name']} server ({server['file']}) not found - skipping")
            continue

        print(f"{'⚽' if 'Soccer' in server['name'] else '📧' if 'Gmail' in server['name'] else '🗺️' if 'Maps' in server['name'] else '🚗' if 'TomTom' in server['name'] else '📊'} Starting {server['name']} MCP Server on port {server['port']}...")

        # Open log file
        log_file = open(f"logs/{server['name'].lower().replace(' ', '_')}_server.log", "w")

        # Start the process using venv python
        python_path = "./venv/bin/python3" if os.path.exists("./venv/bin/python3") else sys.executable
        process = subprocess.Popen(
            [python_path, server["file"]],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid if sys.platform != "win32" else None
        )

        processes.append({
            "process": process,
            "name": server["name"],
            "port": server["port"],
            "log_file": log_file
        })

        print(f"   PID: {process.pid}")
        time.sleep(1)

    print()
    print("⏳ Waiting for servers to start...")
    time.sleep(5)

    # Check server status
    print()
    print("=" * 60)
    print("✅ Server Status Check")
    print("=" * 60)

    all_running = True
    for server in SERVERS:
        if check_server(server["port"]):
            print(f"✅ {server['name']:20} (port {server['port']}): Running")
        else:
            print(f"❌ {server['name']:20} (port {server['port']}): Not responding")
            all_running = False

    print()
    print("=" * 60)
    print("📋 Useful Commands")
    print("=" * 60)
    print("Stop all servers:    python3 stop_all_servers.py")
    print("View server logs:    tail -f logs/*.log")
    print("Check specific log:  tail -f logs/soccer_server.log")
    print()

    if all_running:
        print("🤖 All servers ready! You can now run agents.")
    else:
        print("⚠️  Some servers failed to start. Check logs for details.")

    print("=" * 60)

    # Save PIDs to file for easy stopping
    with open(".server_pids", "w") as f:
        for p in processes:
            f.write(f"{p['process'].pid},{p['name']},{p['port']}\n")

    print()
    print("Press Ctrl+C to stop all servers...")
    print()

    try:
        # Keep script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping all servers...")
        for p in processes:
            try:
                os.killpg(os.getpgid(p["process"].pid), signal.SIGTERM)
                p["log_file"].close()
                print(f"   Stopped {p['name']}")
            except:
                pass
        print("✅ All servers stopped")

if __name__ == "__main__":
    try:
        start_servers()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
