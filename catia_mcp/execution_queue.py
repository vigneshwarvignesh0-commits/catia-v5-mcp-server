"""Single-writer execution queue for CATIA V5 operations.

CATIA V5 is a single-threaded COM application.  When both a local STDIO
client and a remote HTTP client are connected simultaneously, they must
not issue conflicting COM calls at the same time.

This module provides a process-global asyncio Lock that serialises all
tool executions regardless of which transport triggered them.

Usage
-----
    from catia_mcp.execution_queue import catia_lock, run_with_lock

    async def my_handler(name, arguments):
        return await run_with_lock(name, some_sync_fn, name, arguments)
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable

from catia_mcp.config import config

logger = logging.getLogger("catia_mcp.queue")

# Process-global asyncio lock – shared by STDIO and HTTP transports.
# Created lazily within the active event loop to ensure proper binding.
_catia_lock: asyncio.Lock | None = None


def get_catia_lock() -> asyncio.Lock:
    """Return the global CATIA lock, creating it in the current loop if needed."""
    global _catia_lock
    if _catia_lock is None:
        _catia_lock = asyncio.Lock()
    return _catia_lock


# Deprecated attribute kept for backward compatibility with direct imports
class _LockProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_catia_lock(), name)

    async def __aenter__(self) -> Any:
        return await get_catia_lock().__aenter__()

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> Any:
        return await get_catia_lock().__aexit__(exc_type, exc, tb)


catia_lock: Any = _LockProxy()

# Statistics for the /health endpoint
_stats: dict[str, Any] = {
    "total_calls": 0,
    "failed_calls": 0,
    "rejected_timeout": 0,
    "last_tool": None,
    "last_call_at": None,
    "queue_wait_seconds_total": 0.0,
}


def get_stats() -> dict[str, Any]:
    """Return a copy of execution statistics for health reporting."""
    return dict(_stats)


async def run_with_lock(
    tool_name: str,
    sync_fn: Callable[..., str],
    *args: Any,
    timeout: float | None = None,
    **kwargs: Any,
) -> str:
    """Execute a synchronous CATIA tool function under the global lock.

    Parameters
    ----------
    tool_name:
        Human-readable name used in log messages.
    sync_fn:
        The synchronous function to call (module.execute style).
    *args, **kwargs:
        Forwarded to sync_fn.
    timeout:
        Maximum seconds to wait for the lock AND for the function to run.
        Defaults to config.tool_timeout_seconds.

    Returns
    -------
    str
        The result string from sync_fn.

    Raises
    ------
    asyncio.TimeoutError
        If the entire operation (lock acquisition + execution) exceeds timeout.
    Exception
        Re-raises any exception from sync_fn after logging it.
    """
    if timeout is None:
        timeout = config.tool_timeout_seconds

    _stats["total_calls"] += 1
    _stats["last_tool"] = tool_name
    _stats["last_call_at"] = time.time()

    wait_start = time.monotonic()

    try:
        async with asyncio.timeout(timeout):
            async with catia_lock:
                wait_time = time.monotonic() - wait_start
                _stats["queue_wait_seconds_total"] += wait_time
                if wait_time > 1.0:
                    logger.info(
                        "Tool '%s' waited %.2fs for CATIA lock", tool_name, wait_time
                    )

                logger.info("CATIA lock acquired for '%s'", tool_name)
                exec_start = time.monotonic()

                try:
                    # Run the synchronous CATIA call in the event loop thread.
                    # CATIA COM calls are synchronous and must stay on the main
                    # Windows thread (COM STA). Do NOT use run_in_executor here
                    # unless the CATIA connection is explicitly COM-initialised
                    # on that thread.
                    result = sync_fn(*args, **kwargs)
                    exec_time = time.monotonic() - exec_start
                    if exec_time > timeout:
                        raise TimeoutError(
                            f"CATIA tool '{tool_name}' exceeded timeout of {timeout}s (took {exec_time:.2f}s)"
                        )
                    logger.info(
                        "Tool '%s' completed in %.2fs", tool_name, exec_time
                    )
                    return result
                except Exception as exc:
                    _stats["failed_calls"] += 1
                    logger.error(
                        "Tool '%s' raised %s: %s",
                        tool_name, type(exc).__name__, exc,
                        exc_info=True,
                    )
                    raise

    except TimeoutError:
        _stats["rejected_timeout"] += 1
        logger.error(
            "Tool '%s' timed out after %.1fs (lock + execution)",
            tool_name, timeout,
        )
        raise TimeoutError(
            f"CATIA tool '{tool_name}' timed out after {timeout}s. "
            "CATIA may be busy or unresponsive. Try again later."
        )
