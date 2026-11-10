"""Quick verification script – runs without pytest, no CATIA needed.

Usage:
    .venv\\Scripts\\python.exe tests\\verify_imports.py
"""
from __future__ import annotations
import asyncio
import hashlib
import os
import sys
import time

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up safe test env before any config import
os.environ.setdefault("MCP_AUTH_TOKEN", "test-token-verification-run")
os.environ.setdefault("MCP_PORT", "8766")
os.environ.setdefault("MCP_LOG_LEVEL", "WARNING")

TEST_TOKEN = "test-token-verification-run"
BAD_TOKEN = "wrong-token"

passed: list[str] = []
errors: list[str] = []


def ok(msg: str) -> None:
    passed.append(msg)
    print(f"  PASS  {msg}")


def fail(msg: str) -> None:
    errors.append(msg)
    print(f"  FAIL  {msg}")


# ── Test 1: STDIO server imports ─────────────────────────────
print("\nTest Group 1 – STDIO server integrity")
try:
    from catia_mcp.server import CATIAMCPServer, main as stdio_main
    ok("server.py imports cleanly")
except Exception as e:
    fail(f"server.py import: {e}")

try:
    s = CATIAMCPServer()
    assert len(s._tool_modules) == 8, f"Expected 8 modules, got {len(s._tool_modules)}"
    assert len(s._tool_router) >= 50, f"Expected >=50 tools, got {len(s._tool_router)}"
    assert "catia_connect" in s._tool_router
    assert "catia_pad" in s._tool_router
    assert "catia_sketch_line" in s._tool_router
    ok(f"CATIAMCPServer: {len(s._tool_router)} tools across {len(s._tool_modules)} modules")
except Exception as e:
    fail(f"CATIAMCPServer instantiation: {e}")

try:
    assert callable(stdio_main)
    assert callable(s.run)
    ok("STDIO entry points present (main, run)")
except Exception as e:
    fail(f"STDIO entry points: {e}")

# ── Test 2: Config ───────────────────────────────────────────
print("\nTest Group 2 – Configuration")
try:
    from catia_mcp.config import config, ServerConfig, _get_tokens
    tokens = _get_tokens()
    assert TEST_TOKEN in tokens, f"Token not found in {tokens}"
    ok(f"config.py: token loaded, host={ServerConfig.host}, port={ServerConfig.port}")
except Exception as e:
    fail(f"config.py: {e}")

# ── Test 3: Auth ─────────────────────────────────────────────
print("\nTest Group 3 – Authentication middleware")
try:
    import catia_mcp.auth as auth_module
    from catia_mcp.auth import _verify_token, BearerAuthMiddleware
    # Inject our test token digest
    auth_module._TOKEN_DIGESTS = frozenset([hashlib.sha256(TEST_TOKEN.encode()).digest()])
    assert _verify_token(TEST_TOKEN) is True, "Valid token rejected"
    assert _verify_token(BAD_TOKEN) is False, "Invalid token accepted"
    assert _verify_token("") is False, "Empty token accepted"
    assert _verify_token(TEST_TOKEN.upper()) is False, "Case-insensitive match (should be case-sensitive)"
    ok("auth.py: token verification correct")
except Exception as e:
    fail(f"auth.py: {e}")

# ── Test 4: Execution queue ───────────────────────────────────
print("\nTest Group 4 – Execution queue")
try:
    from catia_mcp.execution_queue import catia_lock, run_with_lock, get_stats

    async def test_basic_lock():
        def mock_tool(name, args):
            return f"result-{name}"
        result = await run_with_lock("unit_test", mock_tool, "unit_test", {})
        assert result == "result-unit_test"

    asyncio.run(test_basic_lock())
    ok("run_with_lock: basic call works")
except Exception as e:
    fail(f"run_with_lock basic: {e}")

try:
    async def test_timeout():
        def slow(n, a):
            time.sleep(0.3)
            return "too-late"
        try:
            await run_with_lock("slow", slow, "slow", {}, timeout=0.1)
            return False  # Should have raised
        except (TimeoutError, asyncio.TimeoutError):
            return True
    result = asyncio.run(test_timeout())
    assert result, "Timeout not raised"
    ok("run_with_lock: timeout raises correctly")
except Exception as e:
    fail(f"run_with_lock timeout: {e}")

try:
    order: list[str] = []

    async def test_serialisation():
        def tool(n, a):
            order.append(n + "-start")
            time.sleep(0.05)
            order.append(n + "-end")
            return n
        await asyncio.gather(
            run_with_lock("A", tool, "A", {}),
            run_with_lock("B", tool, "B", {}),
        )

    asyncio.run(test_serialisation())
    # Verify serial execution
    a_end = order.index("A-end")
    b_start = order.index("B-start")
    a_start_idx = order.index("A-start")
    b_end = order.index("B-end")
    serialised = (a_end < b_start) or (b_end < a_start_idx)
    assert serialised, f"Calls interleaved: {order}"
    ok(f"Execution lock serialises concurrent calls: {order}")
except Exception as e:
    fail(f"run_with_lock serialisation: {e}")

# ── Test 5: HTTP server ───────────────────────────────────────
print("\nTest Group 5 – HTTP server")
try:
    from catia_mcp.http_server import (
        CATIAMCPServerHTTP, application, session_manager, main as http_main,
        build_app,
    )
    ok("http_server.py imports cleanly")
except Exception as e:
    fail(f"http_server.py import: {e}")

try:
    http = CATIAMCPServerHTTP()
    stdio = CATIAMCPServer()
    stdio_names = {d["name"] for m in stdio._tool_modules for d in m.get_tool_definitions()}
    http_names = {d["name"] for m in http._tool_modules for d in m.get_tool_definitions()}
    only_stdio = stdio_names - http_names
    only_http = http_names - stdio_names
    assert not only_stdio and not only_http, (
        f"Tool mismatch! STDIO-only: {only_stdio}, HTTP-only: {only_http}"
    )
    ok(f"Tool parity: STDIO={len(stdio_names)} == HTTP={len(http_names)} [MATCH]")
except Exception as e:
    fail(f"Tool parity: {e}")

try:
    assert application is not None
    assert session_manager is not None
    assert callable(http_main)
    ok("HTTP application, session_manager, main() all present")
except Exception as e:
    fail(f"HTTP objects: {e}")

# ── Summary ───────────────────────────────────────────────────
print()
print("=" * 60)
print(f"RESULTS: {len(passed)} PASSED  |  {len(errors)} FAILED")
print("=" * 60)
if errors:
    print("\nFailed tests:")
    for e in errors:
        print(f"  [X] {e}")
    print()
    sys.exit(1)
else:
    print("\nAll checks passed. Ready for HTTP transport and integration testing.")
    print()
    sys.exit(0)
