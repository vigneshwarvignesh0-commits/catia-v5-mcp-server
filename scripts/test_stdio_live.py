"""Test STDIO transport backward compatibility.

Launches the original `python -m catia_mcp.server` over STDIO,
sends JSON-RPC initialize, and reads the response from stdout.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

PYTHON_EXE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".venv", "Scripts", "python.exe")

def test_stdio():
    print("Testing STDIO entry point: python -m catia_mcp.server...")
    proc = subprocess.Popen(
        [PYTHON_EXE, "-m", "catia_mcp.server"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    init_msg = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-stdio", "version": "1.0"}
        }
    }) + "\n"

    try:
        proc.stdin.write(init_msg)
        proc.stdin.flush()

        # Read line from stdout
        response_line = proc.stdout.readline()
        print(f"  STDIO Response: {response_line[:120]}...")
        data = json.loads(response_line)
        assert data.get("jsonrpc") == "2.0"
        assert data.get("id") == 1
        assert "result" in data
        assert data["result"]["serverInfo"]["name"] == "catia-v5-mcp"
        print("  PASS: STDIO server responded with valid initialize response!")
        return 0
    except Exception as e:
        print(f"  FAIL: STDIO error: {e}")
        return 1
    finally:
        proc.terminate()
        try:
            proc.wait(3)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    sys.exit(test_stdio())
