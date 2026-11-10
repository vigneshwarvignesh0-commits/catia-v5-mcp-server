@echo off
REM ============================================================
REM  CATIA V5 MCP Server – Stop Remote (Streamable HTTP) Server
REM  
REM  Finds and terminates the Python process running the HTTP server
REM  on the configured port (default 8765).
REM ============================================================

SETLOCAL

SET MCP_PORT=8765
IF NOT "%1"=="" SET MCP_PORT=%1

echo  Stopping CATIA MCP HTTP server on port %MCP_PORT%...

REM Find the PID using netstat
FOR /F "tokens=5" %%P IN ('netstat -ano ^| findstr ":%MCP_PORT% " ^| findstr "LISTENING"') DO (
    echo  Found process PID: %%P
    taskkill /PID %%P /F
    IF ERRORLEVEL 1 (
        echo  Could not terminate PID %%P – may need Administrator.
    ) ELSE (
        echo  Server stopped successfully.
    )
    GOTO :done
)

echo  No process found listening on port %MCP_PORT%.
echo  The server may not be running.

:done
ENDLOCAL
