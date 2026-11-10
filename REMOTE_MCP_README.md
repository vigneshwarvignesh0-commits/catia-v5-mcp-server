# CATIA V5 Remote MCP Server – Architecture, Deployment & Client Guide

This document describes the **Dual-Transport Architecture** of the CATIA V5 MCP Server, providing:
1. **Local STDIO Transport** (existing, fully backward-compatible, default for local tools).
2. **Streamable HTTP Transport** (new, remote-accessible, authenticated, single-writer serialized).
3. **HTTPS Secure Tunnel / Proxy** (Cloudflare Tunnel, Tailscale, or Reverse Proxy).

---

## 1. System Architecture

```
AI Clients (Antigravity / OpenCode / OpenWork / Claude / Gemini API)
                         │
                         │ HTTPS (TLS 1.3)
                         ▼
        ┌──────────────────────────────────┐
        │  Cloudflare Tunnel / Tailscale    │
        │  (Public or Mesh Secure Ingress) │
        └────────────────┬─────────────────┘
                         │ HTTP (localhost only)
                         ▼
        ┌──────────────────────────────────┐
        │  catia_mcp/http_server.py        │
        │  Port: 8765                      │
        │                                  │
        │  1. BearerAuthMiddleware         │ ← Checks Authorization: Bearer <token>
        │  2. Unauthenticated /health      │ ← Health check & monitoring
        │  3. StreamableHTTPSessionManager │ ← Official MCP Python SDK transport
        └────────────────┬─────────────────┘
                         │
                         ▼
        ┌──────────────────────────────────┐
        │  catia_mcp/execution_queue.py    │
        │  (Process-Global Execution Lock) │ ← Serialises all tool calls, prevents
        └────────────────┬─────────────────┘   concurrent CAD corruption, handles timeouts
                         │
                         ▼
        ┌──────────────────────────────────┐
        │  catia_mcp/server.py             │
        │  CATIAMCPServer (92 CAD Tools)   │ ← 100% Shared tool definitions & logic
        └────────────────┬─────────────────┘
                         │ COM Automation (win32com)
                         ▼
        ┌──────────────────────────────────┐
        │  Dassault Systèmes CATIA V5      │
        │  (Runs on Windows PC)            │
        └──────────────────────────────────┘
```

---

## 2. Security Model & Safeguards

> [!CAUTION]
> Exposing CAD automation to the internet without proper controls is high-risk. The following multi-layer security protections are enforced:

1. **Bearer Token Authentication**:
   - Every request to `/mcp` requires a valid `Authorization: Bearer <token>` header.
   - Missing, malformed, or incorrect tokens are immediately rejected with HTTP `401 Unauthorized`.
   - Constant-time SHA-256 digest comparison protects against timing attacks.
   - Tokens are read strictly from environment variables (`.env`) and never logged.

2. **Single-Writer Execution Lock**:
   - CATIA V5 uses a Single Thread Apartment (STA) COM interface. Simultaneous calls from multiple clients (or mixed STDIO and HTTP) would cause COM RPC failures or geometry corruption.
   - All tool calls pass through `catia_mcp.execution_queue.run_with_lock()`, ensuring strictly serial execution.

3. **Execution Timeouts**:
   - Configurable per-call timeout (`MCP_TOOL_TIMEOUT`, default: 120s) prevents hanging or frozen CAD sessions from locking the server indefinitely.

4. **Health Probe Isolation**:
   - The `/health` endpoint is unauthenticated for load balancers and tunnel monitoring, but exposes **only** server status, tool count, and call statistics. It never reveals tool schemas, environment secrets, or file paths.

---

## 3. Configuration & Environment Variables

Copy `.env.example` to `.env` in the project root:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `MCP_AUTH_TOKEN` | *Generated* | Primary secret token for bearer authentication. |
| `MCP_AUTH_TOKENS` | *None* | Optional comma-separated list of tokens for multiple clients. |
| `MCP_HOST` | `127.0.0.1` | Local IP to bind. Keep `127.0.0.1` when using a tunnel. |
| `MCP_PORT` | `8765` | Local TCP port for the Streamable HTTP server. |
| `MCP_ENDPOINT` | `/mcp` | MCP endpoint path (supports `/mcp` and `/mcp/`). |
| `MCP_TOOL_TIMEOUT` | `120` | Max seconds per tool call before TimeoutError. |
| `MCP_SESSION_IDLE_TIMEOUT` | `1800` | Idle session expiry (seconds). |
| `MCP_LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `CATIA_CONNECT_ON_START` | `false` | If true, auto-connects to CATIA on server boot. |

---

## 4. Running the Server

### Option A: Local STDIO Server (Unchanged)

Existing workflows using STDIO continue to operate with zero modification:

```cmd
cd F:\Openwork\catia-v5-mcp-server
.venv\Scripts\python.exe -m catia_mcp.server
```

Or via pip entry point:
```cmd
catia-mcp
```

### Option B: Remote Streamable HTTP Server

To start the HTTP server:

```cmd
cd F:\Openwork\catia-v5-mcp-server
scripts\start_remote_server.bat
```

Or directly via python:
```cmd
.venv\Scripts\python.exe -m catia_mcp.http_server
```

### Stopping the HTTP Server

```cmd
scripts\stop_remote_server.bat
```

### Health Check

Verify the server is running and responsive:

```cmd
.venv\Scripts\python.exe scripts\health_check.py 127.0.0.1 8765
```

---

## 5. Secure Remote Access (HTTPS Deployment)

### Recommended: Cloudflare Tunnel (Free & Production-Ready)

Cloudflare Tunnel (`cloudflared`) connects your local HTTP server (`127.0.0.1:8765`) to Cloudflare's edge network via outbound HTTPS. **No open ports, no port forwarding, and automatic TLS certification.**

#### Step 1: Install `cloudflared` on Windows
Download `cloudflared-windows-amd64.exe` from Cloudflare and place it on your `PATH`, or use winget:
```cmd
winget install Cloudflare.cloudflared
```

#### Step 2: Quick Ephemeral Tunnel (For Testing)
```cmd
cloudflared tunnel --url http://localhost:8765
```
Cloudflare will assign an ephemeral public URL:
`https://random-subdomain.trycloudflare.com`

Your remote MCP endpoint will be:
`https://random-subdomain.trycloudflare.com/mcp`

#### Step 3: Permanent Named Tunnel (For Production)
1. Log in to Cloudflare:
   ```cmd
   cloudflared tunnel login
   ```
2. Create the tunnel:
   ```cmd
   cloudflared tunnel create catia-mcp-tunnel
   ```
3. Configure `config.yml`:
   ```yaml
   tunnel: <TUNNEL_ID>
   credentials-file: C:\Users\vig\.cloudflared\<TUNNEL_ID>.json

   ingress:
     - hostname: catia.yourdomain.com
       service: http://localhost:8765
     - service: http_status:404
   ```
4. Start tunnel:
   ```cmd
   cloudflared tunnel run catia-mcp-tunnel
   ```

### Alternative: Tailscale (Private Mesh VPN)

If you only want access from devices you own:
1. Install Tailscale on the CATIA Windows PC and on your remote client.
2. The remote client connects directly to the Windows machine's Tailscale IP or MagicDNS name:
   `http://my-catia-pc.tailnet-name.ts.net:8765/mcp`
3. Optional: Enable Tailscale HTTPS (`tailscale serve https / http://127.0.0.1:8765`) for automatic Let's Encrypt TLS.

---

## 6. Client Configuration Matrix

### 6.1 Google Antigravity

Antigravity supports both local STDIO and remote HTTP transports.

#### Local STDIO Configuration:
In Antigravity's MCP configuration (`mcp_config.json` or plugin settings):
```json
{
  "catia-v5": {
    "command": "F:\\Openwork\\catia-v5-mcp-server\\.venv\\Scripts\\python.exe",
    "args": ["-m", "catia_mcp.server"]
  }
}
```

#### Remote HTTP Configuration:
```json
{
  "catia-v5-remote": {
    "url": "https://catia.yourdomain.com/mcp",
    "headers": {
      "Authorization": "Bearer catia-mcp-secret-key-2026-prod"
    }
  }
}
```

---

### 6.2 OpenWork (v0.18.62+)

OpenWork supports both local STDIO commands and remote MCP endpoints.

#### Local Connection (Workspace `.opencode/openwork.json` or App Settings):
```json
{
  "mcp": {
    "catia-v5-local": {
      "command": "F:\\Openwork\\catia-v5-mcp-server\\.venv\\Scripts\\python.exe",
      "args": ["-m", "catia_mcp.server"]
    }
  }
}
```

#### Remote Connection:
Add to `runtime-opencode-config.json` or via OpenWork UI Settings → MCP Servers:
```json
{
  "mcp": {
    "catia-v5-remote": {
      "type": "remote",
      "url": "https://catia.yourdomain.com/mcp",
      "headers": {
        "Authorization": "Bearer catia-mcp-secret-key-2026-prod"
      },
      "enabled": true,
      "oauth": false
    }
  }
}
```

---

### 6.3 OpenCode

OpenCode reads MCP configurations from `.opencode/mcp.json` or `~/.config/opencode/mcp.json`.

#### Local STDIO:
```json
{
  "mcpServers": {
    "catia-local": {
      "command": "F:\\Openwork\\catia-v5-mcp-server\\.venv\\Scripts\\python.exe",
      "args": ["-m", "catia_mcp.server"]
    }
  }
}
```

#### Remote HTTP:
```json
{
  "mcpServers": {
    "catia-remote": {
      "url": "https://catia.yourdomain.com/mcp",
      "headers": {
        "Authorization": "Bearer catia-mcp-secret-key-2026-prod"
      }
    }
  }
}
```

---

### 6.4 Claude Desktop & Claude Code

#### Claude Desktop (`%APPDATA%\Claude\claude_desktop_config.json`):

**Local STDIO:**
```json
{
  "mcpServers": {
    "catia-v5": {
      "command": "F:\\Openwork\\catia-v5-mcp-server\\.venv\\Scripts\\python.exe",
      "args": ["-m", "catia_mcp.server"]
    }
  }
}
```

**Remote HTTP (Streamable HTTP):**
```json
{
  "mcpServers": {
    "catia-v5-remote": {
      "url": "https://catia.yourdomain.com/mcp",
      "headers": {
        "Authorization": "Bearer catia-mcp-secret-key-2026-prod"
      }
    }
  }
}
```

#### Claude Code (CLI):
```bash
claude mcp add catia-remote https://catia.yourdomain.com/mcp --header "Authorization: Bearer catia-mcp-secret-key-2026-prod"
```

---

### 6.5 Gemini API (Programmatic via Python SDK)

> [!NOTE]
> **Gemini Web App vs Gemini API:**
> - The **Gemini web app** (`gemini.google.com`) does NOT currently support arbitrary custom remote MCP server connections.
> - The **Gemini API** supports remote MCP servers programmatically via the `google-genai` SDK or Vertex AI agent workflows.

#### Python Example with `google-genai` SDK:
```python
import os
from google import genai
from google.genai import types

client = genai.Client()

# Connect to the remote CATIA MCP server
catia_mcp_url = "https://catia.yourdomain.com/mcp"
auth_token = os.environ.get("CATIA_MCP_TOKEN", "catia-mcp-secret-key-2026-prod")

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Connect to CATIA, create a new Part named 'WingBracket', and create a pad of 50mm.",
    config=types.GenerateContentConfig(
        tools=[
            types.Tool(
                # Remote MCP endpoint tool declaration
                mcp_server={
                    "url": catia_mcp_url,
                    "headers": {"Authorization": f"Bearer {auth_token}"}
                }
            )
        ]
    )
)

print(response.text)
```

---

## 7. Verification Test Suite

All tests can be executed locally on Windows:

1. **Unit & Integrity Tests** (validates imports, tool parity, auth, execution lock):
   ```cmd
   .venv\Scripts\python.exe tests\verify_imports.py
   ```

2. **Live STDIO Handshake Test**:
   ```cmd
   .venv\Scripts\python.exe scripts\test_stdio_live.py
   ```

3. **Live Remote HTTP Integration Test**:
   ```cmd
   .venv\Scripts\python.exe scripts\test_server_live.py
   ```

4. **Live Tool Discovery Handshake**:
   ```cmd
   .venv\Scripts\python.exe scripts\test_tool_discovery_live.py
   ```

---

## 8. Rollback Instructions

If you ever wish to revert all changes and return to the original codebase:
1. Stop the HTTP server if running (`scripts\stop_remote_server.bat`).
2. An exact backup was taken prior to implementation at:
   `backup_20261107_194832\`
3. To restore, copy the backup files over the project:
   ```cmd
   xcopy /E /Y backup_20261107_194832\catia_mcp catia_mcp\
   copy /Y backup_20261107_194832\pyproject.toml pyproject.toml
   ```
4. Even without rolling back, the original STDIO server remains 100% active and untouched at `python -m catia_mcp.server`.
