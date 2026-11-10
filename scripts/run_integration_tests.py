"""Integration test runner for CATIA V5 MCP HTTP Server.

Tests live HTTP endpoints:
  - GET /health (unauthenticated)
  - GET /mcp without token (must return 401)
  - GET /mcp with invalid token (must return 401)
  - POST /mcp with valid token (JSON-RPC initialize test)
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PORT = 8765
HOST = "127.0.0.1"
BASE_URL = f"http://{HOST}:{PORT}"
TOKEN = "catia-mcp-secret-key-2026-prod"
BAD_TOKEN = "invalid-token-12345"

passed = []
errors = []

def ok(name):
    passed.append(name)
    print(f"  PASS: {name}")

def fail(name, reason):
    errors.append(f"{name}: {reason}")
    print(f"  FAIL: {name} - {reason}")

def test_health():
    url = f"{BASE_URL}/health"
    print(f"\n1. Testing GET {url} (unauthenticated probe)...")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            status = resp.status
            body = json.loads(resp.read().decode("utf-8"))
            if status == 200 and body.get("status") == "ok":
                ok(f"/health returned 200 OK (server: {body.get('server')}, tools: {body.get('tool_count')})")
            else:
                fail("/health", f"Unexpected response: {status} {body}")
    except Exception as e:
        fail("/health", str(e))

def test_auth_rejection_no_header():
    url = f"{BASE_URL}/mcp"
    print(f"\n2. Testing GET {url} without Authorization header...")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            fail("no_auth_header", f"Expected 401, got {resp.status}")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            ok("Rejected unauthenticated request with HTTP 401")
        else:
            fail("no_auth_header", f"Expected 401, got {e.code}")
    except Exception as e:
        fail("no_auth_header", str(e))

def test_auth_rejection_bad_token():
    url = f"{BASE_URL}/mcp"
    print(f"\n3. Testing GET {url} with invalid token...")
    try:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {BAD_TOKEN}"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            fail("bad_token", f"Expected 401, got {resp.status}")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            ok("Rejected invalid token with HTTP 401")
        else:
            fail("bad_token", f"Expected 401, got {e.code}")
    except Exception as e:
        fail("bad_token", str(e))

def test_mcp_post_with_token():
    url = f"{BASE_URL}/mcp"
    print(f"\n4. Testing POST {url} with valid token (JSON-RPC initialize)...")
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "integration-test-client",
                "version": "1.0.0"
            }
        }
    }
    data = json.dumps(init_request).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read()
            if status in (200, 202):
                ok(f"MCP Initialize accepted: HTTP {status} (Content-Type: {content_type})")
            else:
                fail("mcp_initialize", f"Status: {status}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        # In Streamable HTTP, if session initialized or returned response:
        fail("mcp_initialize", f"HTTP {e.code}: {body}")
    except Exception as e:
        fail("mcp_initialize", str(e))

if __name__ == "__main__":
    test_health()
    test_auth_rejection_no_header()
    test_auth_rejection_bad_token()
    test_mcp_post_with_token()

    print("\n" + "=" * 50)
    print(f"Results: {len(passed)} PASSED, {len(errors)} FAILED")
    print("=" * 50)
    sys.exit(0 if not errors else 1)
