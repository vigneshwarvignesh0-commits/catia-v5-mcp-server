"""Self-contained live server test runner.

Starts the Uvicorn server in a separate thread/process, runs integration tests against it,
and gracefully shuts down.
"""

from __future__ import annotations

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
HEALTH_URL = f"http://{HOST}:{PORT}/health"

def wait_for_server(timeout=15):
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

def main():
    print("Starting CATIA MCP HTTP server as subprocess...")
    proc = subprocess.Popen(
        [PYTHON_EXE, "-m", "catia_mcp.http_server"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        print(f"Waiting for server on {HEALTH_URL}...")
        if not wait_for_server(timeout=15):
            print("ERROR: Server failed to start within 15 seconds.")
            stderr = proc.stderr.read().decode("utf-8", errors="replace")
            print(f"Server stderr:\n{stderr}")
            return 1

        print("Server is up and responsive! Running integration tests...\n")
        # Run integration tests
        test_script = os.path.join(os.path.dirname(__file__), "run_integration_tests.py")
        res = subprocess.run([PYTHON_EXE, test_script])
        return res.returncode
    finally:
        print("\nShutting down server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("Server stopped cleanly.")

if __name__ == "__main__":
    sys.exit(main())
