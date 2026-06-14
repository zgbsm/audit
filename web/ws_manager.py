"""WebSocket connection manager — tracks connections per run_id."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

log = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections grouped by run_id.

    Clients connect to /ws/runs/{run_id} and receive a multiplexed stream
    of structured pipeline events and raw AI messages.

    ``broadcast()`` is synchronous so observers and stream forwarders can
    call it from any context — it schedules the actual sends as background
    tasks on the running event loop.
    """

    def __init__(self) -> None:
        # run_id → set of active WebSocket connections
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, run_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.setdefault(run_id, set()).add(ws)
        log.debug("ws connect run_id=%s (total=%d)", run_id, len(self._connections[run_id]))

    def disconnect(self, run_id: str, ws: WebSocket) -> None:
        conns = self._connections.get(run_id, set())
        conns.discard(ws)
        if not conns:
            self._connections.pop(run_id, None)
        log.debug("ws disconnect run_id=%s (remaining=%d)", run_id, len(conns))

    def broadcast(self, run_id: str, event: dict[str, Any]) -> None:
        """Schedule a JSON event send to every client subscribed to this run_id.

        Synchronous — safe to call from observer callbacks and stream
        forwarders without awaiting.
        """
        conns = list(self._connections.get(run_id, set()))
        if not conns:
            return
        for ws in conns:
            asyncio.create_task(self._send_safe(run_id, ws, event))

    def broadcast_all(self, event: dict[str, Any]) -> None:
        """Schedule a JSON event send to ALL connected clients."""
        for run_id in list(self._connections):
            self.broadcast(run_id, event)

    async def _send_safe(self, run_id: str, ws: WebSocket, event: dict[str, Any]) -> None:
        """Send one event and unregister the connection on failure."""
        try:
            await ws.send_json(event)
        except Exception:
            self.disconnect(run_id, ws)

    @property
    def active_runs(self) -> set[str]:
        return set(self._connections.keys())


# Singleton per process
ws_manager = ConnectionManager()
