"""WebSocket handler for real-time chat streaming."""
from __future__ import annotations

from fastapi import WebSocket, WebSocketDisconnect

from backend.config import load_config
from backend.db.database import init_db
from backend.chat.agent import ChatAgent
from backend.signals.scanner import SignalScanner


async def chat_websocket(websocket: WebSocket):
    """WebSocket endpoint for streaming chat responses."""
    await websocket.accept()

    config = load_config()
    init_db(config.db_path)
    agent = ChatAgent(config)

    # Try to get signal context once at connection
    signal_summary = ""
    try:
        scanner = SignalScanner(config)
        signals = scanner.scan_all()
        signal_summary = signals.to_summary()
    except Exception:
        pass

    try:
        while True:
            data = await websocket.receive_text()

            try:
                response = agent.chat(data, signal_summary=signal_summary)
                await websocket.send_json({
                    "type": "response",
                    "content": response,
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "content": str(e),
                })

    except WebSocketDisconnect:
        pass
