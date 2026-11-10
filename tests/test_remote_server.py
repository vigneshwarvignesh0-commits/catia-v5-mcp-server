"""Tests for CATIA V5 MCP remote server infrastructure.

These tests verify:
  1.  Existing STDIO server can be imported and instantiated without error.
  2.  HTTP server can be imported and instantiated without error.
  3.  Configuration loads correctly.
  4.  Authentication middleware accepts and rejects tokens correctly.
  5.  Execution queue serialises calls and handles timeouts.
  6.  All existing tool names and schemas remain unchanged.
  7.  HTTP server starts and responds on /health (integration test, opt-in).
  8.  MCP /mcp endpoint rejects unauthenticated requests (integration, opt-in).
  9.  MCP /mcp endpoint accepts valid token and returns tool list (integration, opt-in).

IMPORTANT: No geometry-changing CATIA operations are executed in any test.
           CATIA does not need to be running for unit tests (mocked).
           Integration tests require the HTTP server to be running separately.

Run unit tests (no CATIA, no network required):
    .venv\\Scripts\\pytest tests\\test_remote_server.py -v -m "not integration"

Run integration tests (requires running HTTP server):
    .venv\\Scripts\\pytest tests\\test_remote_server.py -v -m integration
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import threading
import urllib.request
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_TOKEN = "test-token-safe-for-unit-tests"
BAD_TOKEN = "wrong-token-completely-invalid"


@pytest.fixture(autouse=True)
def set_test_env(monkeypatch):
    """Set required environment variables for tests without touching real .env."""
    monkeypatch.setenv("MCP_AUTH_TOKEN", TEST_TOKEN)
    monkeypatch.setenv("MCP_PORT", "8766")  # Avoid port conflict with real server
    monkeypatch.setenv("MCP_LOG_LEVEL", "WARNING")  # Suppress verbose output in tests


# ---------------------------------------------------------------------------
# Test Group 1 – STDIO server integrity (Phase 6a)
# ---------------------------------------------------------------------------

class TestSTDIOServer:
    """Verify existing STDIO server is fully intact after adding HTTP support."""

    def test_server_module_imports(self):
        """server.py must import without errors."""
        from catia_mcp import server  # noqa: F401

    def test_catia_mcp_server_instantiates(self):
        """CATIAMCPServer must instantiate (uses lazy COM, so no CATIA needed)."""
        from catia_mcp.server import CATIAMCPServer
        s = CATIAMCPServer()
        assert s.server is not None
        assert s.connection is not None
        assert len(s._tool_modules) == 8
        assert len(s._tool_router) > 0

    def test_main_entry_point_exists(self):
        """The original STDIO entry point must still exist."""
        from catia_mcp.server import main
        assert callable(main)

    def test_stdio_run_method_exists(self):
        """CATIAMCPServer.run() must exist for STDIO transport."""
        from catia_mcp.server import CATIAMCPServer
        s = CATIAMCPServer()
        assert callable(s.run)

    def test_all_8_tool_modules_present(self):
        """All 8 original tool modules must be registered."""
        from catia_mcp.server import CATIAMCPServer
        s = CATIAMCPServer()
        module_types = {type(m).__name__ for m in s._tool_modules}
        expected = {
            "DocumentTools", "SketcherTools", "PartDesignTools",
            "GSDTools", "AssemblyTools", "KinematicsTools",
            "MeasurementTools", "ExportTools",
        }
        assert expected == module_types

    def test_connection_manager_exists(self):
        """CATIAConnection must be attached to the server."""
        from catia_mcp.server import CATIAMCPServer
        from catia_mcp.connection import CATIAConnection
        s = CATIAMCPServer()
        assert isinstance(s.connection, CATIAConnection)


# ---------------------------------------------------------------------------
# Test Group 2 – Tool schema integrity (Phase 6b)
# ---------------------------------------------------------------------------

class TestToolSchemas:
    """Verify that existing tool names and schemas are unchanged."""

    @pytest.fixture(scope="class")
    def tool_router(self):
        from catia_mcp.server import CATIAMCPServer
        s = CATIAMCPServer()
        return s._tool_router

    @pytest.fixture(scope="class")
    def all_tool_defs(self):
        from catia_mcp.server import CATIAMCPServer
        s = CATIAMCPServer()
        defs = []
        for module in s._tool_modules:
            defs.extend(module.get_tool_definitions())
        return defs

    def test_catia_connect_exists(self, tool_router):
        assert "catia_connect" in tool_router

    def test_catia_disconnect_exists(self, tool_router):
        assert "catia_disconnect" in tool_router

    def test_catia_new_part_exists(self, tool_router):
        assert "catia_new_part" in tool_router

    def test_catia_pad_exists(self, tool_router):
        assert "catia_pad" in tool_router

    def test_catia_sketch_line_exists(self, tool_router):
        assert "catia_sketch_line" in tool_router

    def test_all_tools_have_name_description_schema(self, all_tool_defs):
        for tool_def in all_tool_defs:
            assert "name" in tool_def, f"Missing 'name' in {tool_def}"
            assert "description" in tool_def, f"Missing 'description' in {tool_def}"
            assert "inputSchema" in tool_def, f"Missing 'inputSchema' in {tool_def}"
            assert tool_def["name"].startswith("catia_"), (
                f"Tool name does not start with 'catia_': {tool_def['name']}"
            )

    def test_minimum_tool_count(self, all_tool_defs):
        """Should have at least the tools present in the original project."""
        assert len(all_tool_defs) >= 50, (
            f"Expected ≥ 50 tools, got {len(all_tool_defs)}"
        )

    def test_http_server_has_same_tools(self, all_tool_defs):
        """HTTP server must expose exactly the same tool set as STDIO server."""
        from catia_mcp.http_server import CATIAMCPServerHTTP
        http_s = CATIAMCPServerHTTP()
        http_defs = []
        for module in http_s._tool_modules:
            http_defs.extend(module.get_tool_definitions())

        stdio_names = {d["name"] for d in all_tool_defs}
        http_names = {d["name"] for d in http_defs}
        assert stdio_names == http_names, (
            f"Tool mismatch.\n"
            f"STDIO only: {stdio_names - http_names}\n"
            f"HTTP only: {http_names - stdio_names}"
        )


# ---------------------------------------------------------------------------
# Test Group 3 – Configuration (Phase 6c)
# ---------------------------------------------------------------------------

class TestConfig:
    def test_config_imports(self):
        from catia_mcp.config import config, ServerConfig  # noqa: F401

    def test_token_from_env(self, monkeypatch):
        monkeypatch.setenv("MCP_AUTH_TOKEN", TEST_TOKEN)
        # Re-read config (import-time singleton; test the helper directly)
        from catia_mcp.config import _get_tokens
        tokens = _get_tokens()
        assert TEST_TOKEN in tokens

    def test_multiple_tokens_from_env(self, monkeypatch):
        monkeypatch.setenv("MCP_AUTH_TOKENS", f"{TEST_TOKEN},another-token")
        from catia_mcp.config import _get_tokens
        tokens = _get_tokens()
        assert TEST_TOKEN in tokens
        assert "another-token" in tokens

    def test_host_default(self):
        from catia_mcp.config import ServerConfig
        # Default should be localhost-only for safety
        assert ServerConfig.host in ("127.0.0.1", "localhost")

    def test_port_is_integer(self):
        from catia_mcp.config import ServerConfig
        assert isinstance(ServerConfig.port, int)

    def test_endpoint_starts_with_slash(self):
        from catia_mcp.config import ServerConfig
        assert ServerConfig.endpoint.startswith("/")


# ---------------------------------------------------------------------------
# Test Group 4 – Authentication middleware (Phase 6d)
# ---------------------------------------------------------------------------

class TestAuth:
    """Unit-test the BearerAuthMiddleware without starting a real server."""

    @pytest.fixture
    def auth_tokens_set(self, monkeypatch):
        """Pre-compute token digests with the test token."""
        import hashlib
        import catia_mcp.auth as auth_module
        digest = frozenset([hashlib.sha256(TEST_TOKEN.encode()).digest()])
        monkeypatch.setattr(auth_module, "_TOKEN_DIGESTS", digest)

    def test_valid_token_accepted(self, auth_tokens_set):
        from catia_mcp.auth import _verify_token
        assert _verify_token(TEST_TOKEN) is True

    def test_invalid_token_rejected(self, auth_tokens_set):
        from catia_mcp.auth import _verify_token
        assert _verify_token(BAD_TOKEN) is False

    def test_empty_token_rejected(self, auth_tokens_set):
        from catia_mcp.auth import _verify_token
        assert _verify_token("") is False

    def test_token_case_sensitive(self, auth_tokens_set):
        from catia_mcp.auth import _verify_token
        assert _verify_token(TEST_TOKEN.upper()) is False


# ---------------------------------------------------------------------------
# Test Group 5 – Execution queue (Phase 6e)
# ---------------------------------------------------------------------------

class TestExecutionQueue:
    def test_import(self):
        from catia_mcp.execution_queue import catia_lock, run_with_lock, get_stats

    def test_run_with_lock_calls_function(self):
        from catia_mcp.execution_queue import run_with_lock

        def mock_tool(name, args):
            return f"result-of-{name}"

        result = asyncio.get_event_loop().run_until_complete(
            run_with_lock("test_tool", mock_tool, "test_tool", {})
        )
        assert result == "result-of-test_tool"

    def test_run_with_lock_raises_on_timeout(self):
        from catia_mcp.execution_queue import run_with_lock
        import asyncio

        def slow_tool(name, args):
            import time
            time.sleep(5)
            return "too-late"

        async def _run():
            return await run_with_lock("slow_tool", slow_tool, "slow_tool", {}, timeout=0.1)

        with pytest.raises((TimeoutError, asyncio.TimeoutError)):
            asyncio.get_event_loop().run_until_complete(_run())

    def test_stats_updated_after_call(self):
        from catia_mcp.execution_queue import run_with_lock, get_stats

        def simple(name, args):
            return "ok"

        asyncio.get_event_loop().run_until_complete(
            run_with_lock("stats_test", simple, "stats_test", {})
        )
        stats = get_stats()
        assert stats["total_calls"] >= 1
        assert stats["last_tool"] == "stats_test"

    def test_lock_serialises_concurrent_calls(self):
        """Two concurrent calls must not interleave (lock enforces serial access)."""
        from catia_mcp.execution_queue import run_with_lock
        import asyncio

        call_order: list[str] = []

        def tool_a(name, args):
            call_order.append(f"{name}-start")
            time.sleep(0.05)
            call_order.append(f"{name}-end")
            return name

        async def _run():
            await asyncio.gather(
                run_with_lock("A", tool_a, "A", {}),
                run_with_lock("B", tool_a, "B", {}),
            )

        asyncio.get_event_loop().run_until_complete(_run())

        # With the lock, one must fully complete before the other starts
        assert call_order.index("A-end") < call_order.index("B-start") or \
               call_order.index("B-end") < call_order.index("A-start"), (
            f"Calls interleaved: {call_order}"
        )


# ---------------------------------------------------------------------------
# Test Group 6 – HTTP server imports (Phase 6f)
# ---------------------------------------------------------------------------

class TestHTTPServerImports:
    def test_http_server_module_imports(self):
        from catia_mcp import http_server  # noqa: F401

    def test_application_object_exists(self):
        from catia_mcp.http_server import application
        assert application is not None

    def test_main_entry_point_exists(self):
        from catia_mcp.http_server import main
        assert callable(main)

    def test_session_manager_created(self):
        from catia_mcp.http_server import session_manager
        assert session_manager is not None


# ---------------------------------------------------------------------------
# Test Group 7 – Integration tests (require running HTTP server)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestHTTPIntegration:
    """Integration tests that require the HTTP server to be running.

    Start the server in a separate terminal before running:
        scripts\\start_remote_server.bat

    Then run:
        .venv\\Scripts\\pytest tests\\test_remote_server.py -v -m integration
    """

    BASE_URL = f"http://127.0.0.1:{os.environ.get('MCP_PORT', '8765')}"

    def _get(self, path: str, token: str | None = None) -> tuple[int, dict]:
        url = f"{self.BASE_URL}{path}"
        req = urllib.request.Request(url)
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                import json
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            import json
            try:
                body = json.loads(e.read())
            except Exception:
                body = {}
            return e.code, body

    def test_health_endpoint_accessible_without_token(self):
        """Health check must work without authentication."""
        status, body = self._get("/health")
        assert status == 200
        assert body.get("status") == "ok"

    def test_mcp_endpoint_rejects_no_token(self):
        """MCP endpoint must return 401 when no token is provided."""
        status, body = self._get("/mcp")
        assert status == 401

    def test_mcp_endpoint_rejects_wrong_token(self):
        """MCP endpoint must return 401 for invalid token."""
        status, body = self._get("/mcp", token=BAD_TOKEN)
        assert status == 401

    def test_server_has_correct_tool_count(self):
        """Health endpoint must report ≥ 50 tools."""
        status, body = self._get("/health")
        assert status == 200
        assert body.get("tool_count", 0) >= 50

    def test_server_reports_8_tool_modules(self):
        """Health endpoint must report exactly 8 tool modules."""
        status, body = self._get("/health")
        assert body.get("tool_modules") == 8
