import json
import uuid
from collections import defaultdict
from typing import Dict, List

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        self._connections: Dict[str, List[WebSocket]] = defaultdict(list)

    async def connect(self, tenant_id: uuid.UUID, websocket: WebSocket):
        await websocket.accept()
        self._connections[str(tenant_id)].append(websocket)

    def disconnect(self, tenant_id: uuid.UUID, websocket: WebSocket):
        key = str(tenant_id)
        if websocket in self._connections[key]:
            self._connections[key].remove(websocket)

    async def broadcast_to_tenant(self, tenant_id: uuid.UUID, message: dict):
        key = str(tenant_id)
        dead = []
        for ws in self._connections.get(key, []):
            try:
                await ws.send_text(json.dumps(message, default=str))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections[key].remove(ws)

    async def send_personal(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception:
            pass


ws_manager = WebSocketManager()
