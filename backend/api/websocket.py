"""WebSocket handler for real-time chat streaming."""
from __future__ import annotations

import logging
from fastapi import WebSocket, WebSocketDisconnect

from backend.services import ServiceContainer, chat

logger = logging.getLogger(__name__)


async def chat_websocket(websocket: WebSocket):
    """WebSocket endpoint for streaming chat responses."""
    await websocket.accept()

    container: ServiceContainer | None = getattr(websocket.app.state, "container", None)
    if container is None:
        await websocket.send_json({"type": "error", "content": "Service not initialized"})
        await websocket.close()
        return

    try:
        while True:
            data = await websocket.receive_text()

            try:
                response = chat(container, data)
                await websocket.send_json({
                    "type": "response",
                    "content": response,
                })
            except Exception as e:
                logger.exception("WebSocket chat error")
                await websocket.send_json({
                    "type": "error",
                    "content": str(e),
                })

    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected")
