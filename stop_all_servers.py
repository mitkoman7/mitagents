#!/usr/bin/env python3
"""
Stop All MCP Servers
"""

import subprocess
import os
import signal

def kill_port(port, name):
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
            print(f"🛑 Stopped {name:20} (port {port}, PID: {pid})")
            return True
        else:
            print(f"ℹ️  {name:20} (port {port}) not running")
            return False
    except Exception as e:
        print(f"❌ Error stopping {name}: {e}")
        return False

def stop_servers():
    """Stop all MCP servers"""
    print("=" * 60)
    print("🛑 Stopping All MCP Servers")
    print("=" * 60)
    print()

    servers = [
        ("Soccer", 8081),
        ("Gmail", 8082),
        ("Google Maps", 8083),
        ("TomTom", 8084),
        ("Databricks", 8085),
    ]

    stopped_count = 0
    for name, port in servers:
        if kill_port(port, name):
            stopped_count += 1

    print()
    print("=" * 60)
    if stopped_count > 0:
        print(f"✅ Stopped {stopped_count} server(s)")
    else:
        print("ℹ️  No servers were running")
    print("=" * 60)

    # Clean up PID file
    if os.path.exists(".server_pids"):
        os.remove(".server_pids")

if __name__ == "__main__":
    stop_servers()
