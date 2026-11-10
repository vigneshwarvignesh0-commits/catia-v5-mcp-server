"""CATIA V5 MCP Server – Streamable HTTP transport entry point.

This module adds a remote-accessible HTTP endpoint to the existing CATIA V5 MCP
server WITHOUT modifying the STDIO entry point or any tool implementations.

Architecture
------------
  AI Client (remote)
      │  HTTPS (terminated at Cloudflare Tunnel / Tailscale / nginx)
      │
  localhost:8765/mcp
      │
  BearerAuthMiddleware  ← catia_mcp/auth.py
      │
  StreamableHTTPSessionManager  ← mcp.server.streamable_http_manager
      │
  CATIAMCPServerHTTP  ← subclass of CATIAMCPServer with execution lock
      │  same 8 tool modules, same CATIAConnection, same tool schemas
      │
  catia_lock (asyncio)  ← catia_mcp/execution_queue.py
      │
  CATIA V5 COM

Usage
-----
  # Activate the venv first, then:
  python -m catia_mcp.http_server

  # Or via the installed console script:
  catia-mcp-http

  # Or via the batch file:
  scripts\\start_remote_server.bat
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import sys
import time
from typing import Any

import uvicorn
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import TextContent, Tool
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import Receive, Scope, Send

from catia_mcp.auth import BearerAuthMiddleware
from catia_mcp.config import config
from catia_mcp.execution_queue import get_stats, run_with_lock
from catia_mcp.server import CATIAMCPServer

# ── Logging setup ─────────────────────────────────────────────────────────────

_log_handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
if config.log_file:
    try:
        _fh = logging.FileHandler(config.log_file, encoding="utf-8")
        _log_handlers.append(_fh)
    except Exception:
        pass

logging.basicConfig(
    level=getattr(logging, config.log_level, logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=_log_handlers,
)
logger = logging.getLogger("catia_mcp.http")


# ── Lock-aware MCP server ─────────────────────────────────────────────────────

class CATIAMCPServerHTTP(CATIAMCPServer):
    """CATIAMCPServer variant whose call_tool handler uses the global CATIA lock.

    All tool schemas, tool names, and CATIA COM logic are inherited unchanged
    from the parent class.  Only the tool-call dispatch path is overridden to
    serialize concurrent remote requests through the global asyncio lock.

    The lock is shared with the STDIO server if both are running in the same
    process, ensuring no two transports issue simultaneous COM calls.
    """

    def _setup_handlers(self) -> None:
        """Register MCP protocol handlers – with execution lock on call_tool."""

        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            tools = []
            for module in self._tool_modules:
                for tool_def in module.get_tool_definitions():
                    tools.append(
                        Tool(
                            name=tool_def["name"],
                            description=tool_def["description"],
                            inputSchema=tool_def["inputSchema"],
                        )
                    )
            logger.info("[HTTP] Listed %d tools", len(tools))
            return tools

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: dict[str, Any] | None
        ) -> list[TextContent]:
            arguments = arguments or {}
            logger.info("[HTTP] Tool call: %s(%s)", name, arguments)

            module = self._tool_router.get(name)
            if module is None:
                return [TextContent(
                    type="text",
                    text=f"Unknown tool: '{name}'. Use list_tools to see available tools.",
                )]

            # Auto-connect for non-connect tools
            if name not in ("catia_connect", "catia_disconnect"):
                if not self.connection.is_connected:
                    try:
                        connect_msg = await run_with_lock(
                            "catia_connect(auto)",
                            self.connection.connect,
                        )
                        logger.info("[HTTP] Auto-connected: %s", connect_msg)
                    except TimeoutError as te:
                        return [TextContent(type="text", text=str(te))]
                    except Exception as conn_exc:
                        return [TextContent(
                            type="text",
                            text=f"CATIA not available: {conn_exc}",
                        )]

            try:
                result = await run_with_lock(name, module.execute, name, arguments)
                logger.info(
                    "[HTTP] Tool result: %s",
                    result[:200] if len(result) > 200 else result,
                )
                return [TextContent(type="text", text=result)]
            except TimeoutError as te:
                return [TextContent(type="text", text=str(te))]
            except Exception as exc:
                error_msg = f"Error in {name}: {exc}"
                logger.error("[HTTP] %s", error_msg, exc_info=True)
                return [TextContent(type="text", text=error_msg)]


# ── Shared server instance ────────────────────────────────────────────────────

_catia_http_server = CATIAMCPServerHTTP()
_mcp_server = _catia_http_server.server


# ── Health endpoint ───────────────────────────────────────────────────────────

async def health_handler(request: Request) -> JSONResponse:
    """Unauthenticated health probe.

    Returns basic server status and execution statistics.
    Does NOT expose tool schemas, authentication details, or token values.
    """
    stats = get_stats()
    catia_connected = False
    catia_version = "unknown"
    try:
        catia_connected = _catia_http_server.connection.is_connected
        if catia_connected:
            catia_version = _catia_http_server.connection._get_version()
    except Exception:
        pass

    return JSONResponse({
        "status": "ok",
        "server": "catia-v5-mcp",
        "version": "0.2.0",
        "transport": "streamable-http",
        "endpoint": config.endpoint,
        "catia": {
            "connected": catia_connected,
            "version": catia_version,
        },
        "execution": {
            "total_calls": stats["total_calls"],
            "failed_calls": stats["failed_calls"],
            "timeout_calls": stats["rejected_timeout"],
            "last_tool": stats["last_tool"],
        },
        "tool_modules": len(_catia_http_server._tool_modules),
        "tool_count": len(_catia_http_server._tool_router),
        "timestamp": time.time(),
    })


# ── ASGI application factory ──────────────────────────────────────────────────

session_manager = StreamableHTTPSessionManager(
    app=_mcp_server,
    stateless=False,
    json_response=False,
    session_idle_timeout=config.session_idle_timeout,
)


class CATIAMCPApp:
    """Core ASGI application dispatching health and MCP endpoints without redirects."""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    logger.info("Starting StreamableHTTP session manager...")
                    # We enter the session_manager context
                    self._lifespan_ctx = session_manager.run()
                    await self._lifespan_ctx.__aenter__()
                    logger.info(
                        "CATIA V5 MCP HTTP Server ready on http://%s%s",
                        config.bind_address(), config.endpoint,
                    )
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    logger.info("Stopping StreamableHTTP session manager...")
                    if hasattr(self, "_lifespan_ctx"):
                        await self._lifespan_ctx.__aexit__(None, None, None)
                    logger.info("CATIA V5 MCP HTTP Server stopped.")
                    await send({"type": "lifespan.shutdown.complete"})
                    break
            return

        if scope["type"] not in ("http", "websocket"):
            return

        path = scope.get("path", "")

        # Unauthenticated health probe
        if path == config.health_endpoint:
            req = Request(scope, receive)
            resp = await health_handler(req)
            await resp(scope, receive, send)
            return

        # MCP endpoint (accepts both /mcp and /mcp/ without redirect)
        clean_endpoint = config.endpoint.rstrip("/")
        if path in (clean_endpoint, clean_endpoint + "/"):
            await session_manager.asgi_app(scope, receive, send)
            return

        # 404 for any other path
        resp = JSONResponse(
            {"error": "Not Found", "endpoint": config.endpoint, "health": config.health_endpoint},
            status_code=404,
        )
        await resp(scope, receive, send)


def build_app() -> BearerAuthMiddleware:
    """Build and return the wrapped Starlette ASGI application."""
    core_app = CATIAMCPApp()
    return BearerAuthMiddleware(core_app, exempt_paths=(config.health_endpoint,))


application = build_app()  # ASGI entry point for uvicorn


# ── Main entry point ──────────────────────────────────────────────────────────

def main() -> None:
    """Start the CATIA V5 MCP HTTP server."""
    logger.info("=" * 60)
    logger.info("CATIA V5 MCP Server – Streamable HTTP Transport")
    logger.info("Endpoint : http://%s%s", config.bind_address(), config.endpoint)
    logger.info("Health   : http://%s%s", config.bind_address(), config.health_endpoint)
    logger.info("Timeout  : %.0f seconds per tool call", config.tool_timeout_seconds)
    logger.info("=" * 60)
    logger.info("STDIO server is UNCHANGED and runs independently.")
    logger.info("Both transports share the same CATIA tool implementations.")
    logger.info("Concurrent access is serialised via the CATIA execution lock.")

    uvicorn.run(
        "catia_mcp.http_server:application",
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower(),
        workers=1,  # CATIA COM requires single-process access
    )


if __name__ == "__main__":
    main()
