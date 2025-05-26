from __future__ import annotations

import typing
from enum import IntEnum

from velithon.datastructures import Headers, Protocol, Scope
from velithon.status import WS_1000_NORMAL_CLOSURE


class WebSocketState(IntEnum):
    CONNECTING = 0
    CONNECTED = 1
    DISCONNECTED = 2


class WebSocketDisconnect(Exception):
    """Raised when WebSocket connection is disconnected."""
    
    def __init__(self, code: int = WS_1000_NORMAL_CLOSURE, reason: str = "") -> None:
        self.code = code
        self.reason = reason
        super().__init__(f"WebSocket disconnected with code {code}: {reason}")


class WebSocket:
    """WebSocket connection class for handling WebSocket communications."""
    
    def __init__(self, scope: Scope, protocol: Protocol) -> None:
        assert scope.proto == "websocket"
        self.scope = scope
        self.protocol = protocol
        self.client_state = WebSocketState.CONNECTING
        self.application_state = WebSocketState.CONNECTING

    @property
    def url(self) -> str:
        """Get the WebSocket URL."""
        return str(self.scope.url)

    @property
    def headers(self) -> Headers:
        """Get WebSocket headers."""
        if not hasattr(self, "_headers"):
            self._headers = Headers(headers=self.scope.headers.items())
        return self._headers

    @property
    def query_params(self) -> dict[str, str]:
        """Get query parameters from WebSocket URL."""
        if not hasattr(self, "_query_params"):
            self._query_params = dict(self.scope.query_params)
        return self._query_params

    @property
    def path_params(self) -> dict[str, typing.Any]:
        """Get path parameters from WebSocket URL."""
        return getattr(self.scope, "_path_params", {})

    @property
    def client(self) -> tuple[str, int] | None:
        """Get client address (host, port)."""
        if hasattr(self.scope, "client") and self.scope.client:
            host_port = self.scope.client.split(":")
            if len(host_port) == 2:
                return (host_port[0], int(host_port[1]))
        return None

    async def accept(
        self, 
        subprotocol: str | None = None, 
        headers: typing.Sequence[tuple[str, str]] | None = None
    ) -> None:
        """Accept the WebSocket connection."""
        if self.client_state == WebSocketState.CONNECTING:
            # Accept the connection
            message = {
                "type": "websocket.accept",
                "subprotocol": subprotocol,
                "headers": headers or [],
            }
            await self._send_message(message)
            self.client_state = WebSocketState.CONNECTED
        else:
            raise RuntimeError(
                f"WebSocket connection cannot be accepted in state {self.client_state}"
            )

    async def receive_text(self) -> str:
        """Receive text message from WebSocket."""
        if self.application_state != WebSocketState.CONNECTED:
            raise RuntimeError("WebSocket is not connected")
        
        message = await self._receive_message()
        if message["type"] == "websocket.receive":
            if "text" in message:
                return message["text"]
            elif "bytes" in message:
                return message["bytes"].decode("utf-8")
        elif message["type"] == "websocket.disconnect":
            raise WebSocketDisconnect(message.get("code", WS_1000_NORMAL_CLOSURE))
        
        raise RuntimeError(f"Unexpected message type: {message['type']}")

    async def receive_bytes(self) -> bytes:
        """Receive bytes message from WebSocket."""
        if self.application_state != WebSocketState.CONNECTED:
            raise RuntimeError("WebSocket is not connected")
        
        message = await self._receive_message()
        if message["type"] == "websocket.receive":
            if "bytes" in message:
                return message["bytes"]
            elif "text" in message:
                return message["text"].encode("utf-8")
        elif message["type"] == "websocket.disconnect":
            raise WebSocketDisconnect(message.get("code", WS_1000_NORMAL_CLOSURE))
        
        raise RuntimeError(f"Unexpected message type: {message['type']}")

    async def receive_json(self) -> typing.Any:
        """Receive JSON message from WebSocket."""
        import orjson
        text = await self.receive_text()
        return orjson.loads(text)

    async def send_text(self, data: str) -> None:
        """Send text message to WebSocket."""
        if self.application_state != WebSocketState.CONNECTED:
            raise RuntimeError("WebSocket is not connected")
        
        message = {"type": "websocket.send", "text": data}
        await self._send_message(message)

    async def send_bytes(self, data: bytes) -> None:
        """Send bytes message to WebSocket."""
        if self.application_state != WebSocketState.CONNECTED:
            raise RuntimeError("WebSocket is not connected")
        
        message = {"type": "websocket.send", "bytes": data}
        await self._send_message(message)

    async def send_json(self, data: typing.Any) -> None:
        """Send JSON message to WebSocket."""
        import orjson
        text = orjson.dumps(data).decode("utf-8")
        await self.send_text(text)

    async def close(
        self, 
        code: int = WS_1000_NORMAL_CLOSURE, 
        reason: str = ""
    ) -> None:
        """Close the WebSocket connection."""
        if self.application_state in (WebSocketState.CONNECTING, WebSocketState.CONNECTED):
            message = {
                "type": "websocket.close",
                "code": code,
                "reason": reason,
            }
            await self._send_message(message)
            self.application_state = WebSocketState.DISCONNECTED

    async def _send_message(self, message: dict[str, typing.Any]) -> None:
        """Send a message through the protocol."""
        # This is a placeholder - in practice, this would interface with Granian's WebSocket protocol
        # For now, we'll assume the protocol handles WebSocket messages
        pass

    async def _receive_message(self) -> dict[str, typing.Any]:
        """Receive a message from the protocol."""
        # This is a placeholder - in practice, this would interface with Granian's WebSocket protocol
        # For now, we'll return a dummy message
        return {"type": "websocket.receive", "text": ""}

    async def __aenter__(self) -> WebSocket:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self.application_state != WebSocketState.DISCONNECTED:
            await self.close()
