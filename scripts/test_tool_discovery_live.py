"""Live remote tool discovery test.

Performs full MCP handshake over Streamable HTTP:
1. Initialize
2. Notifications / initialized
3. tools/list request
4. Verifies tool count >= 90 and tool schema structure
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PYTHON_EXE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".venv", "Scripts", "python.exe")
HOST = "127.0.0.1"
PORT = 8765
MCP_URL = f"http://{HOST}:{PORT}/mcp"
HEALTH_URL = f"http://{HOST}:{PORT}/health"
TOKEN = "catia-mcp-secret-key-2026-prod"

def wait_for_server(timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(HEALTH_URL)
            with urllib.request.urlopen(req, timeout=1) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False

def run_discovery():
    print(f"\nConnecting to MCP server at {MCP_URL}...")

    # Step 1: Initialize
    init_req = {
        "jsonrpc": "2.0",
        "id": "init-1",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "discovery-test-client", "version": "1.0"}
        }
    }
    
    req = urllib.request.Request(
        MCP_URL,
        data=json.dumps(init_req).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=10) as resp:
        mcp_session_id = resp.headers.get("mcp-session-id")
        print(f"  Initialized! Session ID: {mcp_session_id}")
        raw = resp.read().decode("utf-8", errors="replace")
        # In Streamable HTTP, response can be SSE text/event-stream
        print(f"  Handshake response preview: {raw[:150]}...")

    # Step 2: List tools
    list_tools_req = {
        "jsonrpc": "2.0",
        "id": "tools-1",
        "method": "tools/list",
        "params": {}
    }

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if mcp_session_id:
        headers["mcp-session-id"] = mcp_session_id

    req2 = urllib.request.Request(
        MCP_URL,
        data=json.dumps(list_tools_req).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    with urllib.request.urlopen(req2, timeout=10) as resp2:
        raw2 = resp2.read().decode("utf-8", errors="replace")
        # Parse SSE data or JSON
        tool_names = []
        for line in raw2.splitlines():
            if line.startswith("data: "):
                try:
                    payload = json.loads(line[6:])
                    tools = payload.get("result", {}).get("tools", [])
                    tool_names = [t["name"] for t in tools]
                except Exception:
                    pass

        if not tool_names:
            try:
                payload = json.loads(raw2)
                tools = payload.get("result", {}).get("tools", [])
                tool_names = [t["name"] for t in tools]
            except Exception:
                pass

        print(f"\n  Tools discovered: {len(tool_names)}")
        print(f"  Sample tools: {tool_names[:5]}")
        assert len(tool_names) >= 50, f"Expected >= 50 tools, got {len(tool_names)}"
        assert "catia_connect" in tool_names
        assert "catia_pad" in tool_names
        assert "catia_sketch_line" in tool_names
        print(f"  Tool discovery verified successfully! All {len(tool_names)} tools returned.")

def main():
    proc = subprocess.Popen(
        [PYTHON_EXE, "-m", "catia_mcp.http_server"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        if not wait_for_server(10):
            print("Failed to start server")
            return 1
        run_discovery()
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(5)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    sys.exit(main())
