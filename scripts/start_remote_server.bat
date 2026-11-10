@echo off
REM ============================================================
REM  CATIA V5 MCP Server – Start Remote (Streamable HTTP) Server
REM  
REM  This script starts ONLY the HTTP transport.
REM  Your existing STDIO server continues to work unchanged.
REM  Both share the same CATIA tool implementations.
REM ============================================================

SETLOCAL

SET PROJECT_DIR=%~dp0..
SET VENV_PYTHON=%PROJECT_DIR%\.venv\Scripts\python.exe
SET ENV_FILE=%PROJECT_DIR%\.env
SET PID_FILE=%PROJECT_DIR%\catia_mcp_http.pid

echo.
echo  CATIA V5 MCP Server – Remote HTTP Transport
echo  ============================================
echo  Project  : %PROJECT_DIR%
echo  Python   : %VENV_PYTHON%
echo  Env file : %ENV_FILE%
echo.

REM Check that the venv exists
IF NOT EXIST "%VENV_PYTHON%" (
    echo  ERROR: Virtual environment not found at %VENV_PYTHON%
    echo  Run: python -m venv .venv ^&^& .venv\Scripts\pip install -e .
    pause
    EXIT /B 1
)

REM Check that .env exists (not just .env.example)
IF NOT EXIST "%ENV_FILE%" (
    echo  WARNING: .env file not found.
    echo  Copy .env.example to .env and set MCP_AUTH_TOKEN before exposing remotely.
    echo.
)

echo  Starting HTTP MCP server...
echo  Press Ctrl+C to stop.
echo.

REM Start the server (the PID file is written by Python)
"%VENV_PYTHON%" -m catia_mcp.http_server

ENDLOCAL
