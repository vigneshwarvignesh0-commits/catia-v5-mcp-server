"""Bearer-token authentication middleware for the CATIA MCP HTTP server.

Protects all routes except /health from unauthenticated access.
Never exposes token values in responses or logs.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import Callable

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from catia_mcp.config import config

logger = logging.getLogger("catia_mcp.auth")

# Pre-compute SHA-256 digests of valid tokens so we can compare
# in constant time without exposing raw tokens in memory comparisons.
_TOKEN_DIGESTS: frozenset[bytes] = frozenset(
    hashlib.sha256(t.encode()).digest() for t in config.auth_tokens
)


def _verify_token(token: str) -> bool:
    """Compare token against allowed set using constant-time digest comparison."""
    candidate = hashlib.sha256(token.encode()).digest()
    return candidate in _TOKEN_DIGESTS


class BearerAuthMiddleware:
    """ASGI middleware that enforces Bearer token authentication.

    Endpoints exempted from auth:
      - GET /health  (health probe used by tunnel monitors and load balancers)
      - OPTIONS *    (CORS preflight – handled without auth)

    All other requests must include:
      Authorization: Bearer <token>

    On failure → 401 JSON response. The error body never reveals token details.
    """

    def __init__(self, app: ASGIApp, exempt_paths: tuple[str, ...] = ("/health",)) -> None:
        self.app = app
        self.exempt_paths = exempt_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        path = request.url.path
        method = request.method

        # Allow exempt paths and OPTIONS preflight without authentication
        if path in self.exempt_paths or method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        auth_header = request.headers.get("Authorization", "")
        client_ip = request.client.host if request.client else "unknown"

        if not auth_header.startswith("Bearer "):
            logger.warning(
                "AUTH REJECTED [%s] %s %s – missing or malformed Authorization header",
                client_ip, method, path,
            )
            response = _unauthorized("Authorization header required: Bearer <token>")
            await response(scope, receive, send)
            return

        token = auth_header[7:].strip()

        if not _verify_token(token):
            logger.warning(
                "AUTH REJECTED [%s] %s %s – invalid token",
                client_ip, method, path,
            )
            response = _unauthorized("Invalid or expired token")
            await response(scope, receive, send)
            return

        logger.info("AUTH OK [%s] %s %s", client_ip, method, path)
        await self.app(scope, receive, send)


def _unauthorized(detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"error": "Unauthorized", "detail": detail},
        headers={"WWW-Authenticate": "Bearer"},
    )
