#!/usr/bin/env python3
"""Health check script for CATIA V5 MCP HTTP server.

Usage:
    python scripts/health_check.py [host] [port]

Examples:
    python scripts/health_check.py
    python scripts/health_check.py 127.0.0.1 8765
    python scripts/health_check.py my-tunnel.trycloudflare.com 443
"""

from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error

def check_health(host: str = "127.0.0.1", port: int = 8765) -> int:
    scheme = "https" if port == 443 else "http"
    url = f"{scheme}://{host}:{port}/health" if port not in (80, 443) else f"{scheme}://{host}/health"

    print(f"\nChecking CATIA MCP server health: {url}")
    print("-" * 50)

    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)

            print(f"  Status         : {data.get('status', '?')}")
            print(f"  Server         : {data.get('server', '?')} v{data.get('version', '?')}")
            print(f"  Transport      : {data.get('transport', '?')}")
            print(f"  MCP endpoint   : {data.get('endpoint', '?')}")

            catia = data.get("catia", {})
            print(f"  CATIA connected: {catia.get('connected', False)}")
            print(f"  CATIA version  : {catia.get('version', 'unknown')}")

            print(f"  Tools          : {data.get('tool_count', '?')} tools "
                  f"({data.get('tool_modules', '?')} modules)")

            exec_stats = data.get("execution", {})
            print(f"  Total calls    : {exec_stats.get('total_calls', 0)}")
            print(f"  Failed calls   : {exec_stats.get('failed_calls', 0)}")
            print(f"  Timed out      : {exec_stats.get('timeout_calls', 0)}")
            print(f"  Last tool      : {exec_stats.get('last_tool', 'none')}")

            print()
            if data.get("status") == "ok":
                print("  [OK] Server is healthy.")
                return 0
            else:
                print("  [!] Server returned non-ok status.")
                return 1

    except urllib.error.URLError as e:
        print(f"  [X] Could not connect: {e.reason}")
        print(f"      Is the server running? Start with: scripts\\start_remote_server.bat")
        return 2
    except json.JSONDecodeError:
        print("  [X] Server returned non-JSON response.")
        return 3
    except Exception as e:
        print(f"  [X] Unexpected error: {e}")
        return 4


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
    sys.exit(check_health(host, port))
