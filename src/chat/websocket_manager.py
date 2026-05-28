from collections import defaultdict

from fastapi import WebSocket


class ChatWebSocketManager:
    def __init__(self):
        self.chat_connections: dict[int, dict[int, set[WebSocket]]] = defaultdict(
            lambda: defaultdict(set)
        )
        self.user_connections: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(
        self,
        chat_id: int,
        user_id: int,
        websocket: WebSocket,
    ) -> None:
        await websocket.accept()

        self.chat_connections[chat_id][user_id].add(websocket)
        self.user_connections[user_id].add(websocket)

    def disconnect(
        self,
        chat_id: int,
        user_id: int,
        websocket: WebSocket,
    ) -> None:
        if chat_id in self.chat_connections:
            if user_id in self.chat_connections[chat_id]:
                self.chat_connections[chat_id][user_id].discard(websocket)

                if not self.chat_connections[chat_id][user_id]:
                    del self.chat_connections[chat_id][user_id]

            if not self.chat_connections[chat_id]:
                del self.chat_connections[chat_id]

        if user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)

            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

    def is_user_online(self, user_id: int) -> bool:
        return user_id in self.user_connections and bool(self.user_connections[user_id])

    async def broadcast_to_chat(
        self,
        chat_id: int,
        payload: dict,
    ) -> None:
        if chat_id not in self.chat_connections:
            return

        dead_connections: list[tuple[int, WebSocket]] = []

        for user_id, sockets in self.chat_connections[chat_id].items():
            for websocket in list(sockets):
                try:
                    await websocket.send_json(payload)
                except Exception:
                    dead_connections.append((user_id, websocket))

        for user_id, websocket in dead_connections:
            self.disconnect(chat_id, user_id, websocket)


chat_ws_manager = ChatWebSocketManager()