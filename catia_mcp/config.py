"""Configuration for CATIA V5 MCP Server – remote HTTP transport.

All secrets are loaded from environment variables or a .env file.
Never hardcode tokens or API keys here.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

# Load .env file from project root (if present) without requiring python-dotenv
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=_env_file, override=False)
    except ImportError:
        # dotenv not available; fall back to manual parse
        with open(_env_file, encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _, _v = _line.partition("=")
                    os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))


def _get_tokens() -> list[str]:
    """Return the list of valid bearer tokens from environment variables.

    Priority:
      MCP_AUTH_TOKENS  – comma-separated list of tokens (multiple clients)
      MCP_AUTH_TOKEN   – single token (backward compatible)

    If neither is set, a random 32-byte hex token is generated and printed
    to stderr so the operator can note it down. This prevents starting an
    unauthenticated server by mistake.
    """
    multi = os.environ.get("MCP_AUTH_TOKENS", "").strip()
    if multi:
        tokens = [t.strip() for t in multi.split(",") if t.strip()]
        if tokens:
            return tokens

    single = os.environ.get("MCP_AUTH_TOKEN", "").strip()
    if single:
        return [single]

    # Generate a random token and warn loudly
    generated = secrets.token_hex(32)
    import sys
    print(
        "\n[CATIA-MCP] WARNING: No MCP_AUTH_TOKEN set. Generated ephemeral token:\n"
        f"  {generated}\n"
        "Set MCP_AUTH_TOKEN in .env to make it permanent.\n",
        file=sys.stderr,
    )
    return [generated]


class ServerConfig:
    """Runtime configuration for the HTTP MCP server."""

    # ── HTTP binding ──────────────────────────────────────────────
    host: str = os.environ.get("MCP_HOST", "127.0.0.1")
    port: int = int(os.environ.get("MCP_PORT", "8765"))
    endpoint: str = os.environ.get("MCP_ENDPOINT", "/mcp")
    health_endpoint: str = "/health"

    # ── Authentication ────────────────────────────────────────────
    auth_tokens: list[str] = _get_tokens()

    # ── Execution queue ───────────────────────────────────────────
    tool_timeout_seconds: float = float(os.environ.get("MCP_TOOL_TIMEOUT", "120"))

    # ── Session management ────────────────────────────────────────
    session_idle_timeout: float = float(os.environ.get("MCP_SESSION_IDLE_TIMEOUT", "1800"))

    # ── Logging ───────────────────────────────────────────────────
    log_level: str = os.environ.get("MCP_LOG_LEVEL", "INFO").upper()
    log_file: str = os.environ.get(
        "MCP_LOG_FILE",
        str(Path(__file__).parent.parent / "catia_mcp_http.log"),
    )

    # ── CATIA ─────────────────────────────────────────────────────
    catia_connect_on_start: bool = (
        os.environ.get("CATIA_CONNECT_ON_START", "false").lower() == "true"
    )

    @classmethod
    def bind_address(cls) -> str:
        return f"{cls.host}:{cls.port}"

    @classmethod
    def mcp_url(cls) -> str:
        return f"http://{cls.host}:{cls.port}{cls.endpoint}"


# Module-level singleton (import and use directly)
config = ServerConfig()
