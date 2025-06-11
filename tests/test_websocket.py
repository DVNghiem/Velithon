"""
Tests for WebSocket functionality in Velithon.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from velithon.status import WS_1000_NORMAL_CLOSURE, WS_1008_POLICY_VIOLATION
from velithon.websocket import (
    WebSocket,
    WebSocketDisconnect,
    WebSocketEndpoint,
    WebSocketRoute,
    WebSocketState,
    websocket_response,
    websocket_route,
)


class MockProtocol:
    """Mock protocol for testing."""
    
    def __init__(self):
        self.messages = []
        self.received_messages = []
    
    async def send_message(self, message):
        self.messages.append(message)
    
    async def receive_message(self):
        if self.received_messages:
            return self.received_messages.pop(0)
        return {"type": "websocket.receive", "text": "test message"}


@pytest.fixture
def mock_scope():
    """Create a mock WebSocket scope."""
    scope = MagicMock()
    scope.proto = "websocket"
    scope.path = "/ws"
    scope.url = "ws://localhost/ws"
    scope.headers = MagicMock()
    scope.headers.items.return_value = [("host", "localhost")]
    scope.query_params = {}
    scope.client = "127.0.0.1:8000"
    return scope


@pytest.fixture
def mock_protocol():
    """Create a mock protocol."""
    protocol = MagicMock()
    return protocol


class TestWebSocket:
    """Test WebSocket connection class."""
    
    def test_websocket_initialization(self, mock_scope, mock_protocol):
        """Test WebSocket initialization."""
        websocket = WebSocket(mock_scope, mock_protocol)
        
        assert websocket.scope == mock_scope
        assert websocket.protocol == mock_protocol
        assert websocket.client_state == WebSocketState.CONNECTING
        assert websocket.application_state == WebSocketState.CONNECTING
    
    def test_websocket_properties(self, mock_scope, mock_protocol):
        """Test WebSocket properties."""
        websocket = WebSocket(mock_scope, mock_protocol)
        
        assert websocket.url == "ws://localhost/ws"
        assert websocket.query_params == {}
        assert websocket.client == ("127.0.0.1", 8000)
    
    def test_websocket_path_params(self, mock_scope, mock_protocol):
        """Test WebSocket path parameters."""
        setattr(mock_scope, "_path_params", {"id": "123"})
        websocket = WebSocket(mock_scope, mock_protocol)
        
        assert websocket.path_params == {"id": "123"}
    
    @pytest.mark.asyncio
    async def test_websocket_accept(self, mock_scope, mock_protocol):
        """Test WebSocket accept."""
        websocket = WebSocket(mock_scope, mock_protocol)
        websocket._send_message = AsyncMock()
        
        await websocket.accept()
        
        assert websocket.client_state == WebSocketState.CONNECTED
        websocket._send_message.assert_called_once_with({
            "type": "websocket.accept",
            "subprotocol": None,
            "headers": [],
        })
    
    @pytest.mark.asyncio
    async def test_websocket_accept_with_subprotocol(self, mock_scope, mock_protocol):
        """Test WebSocket accept with subprotocol."""
        websocket = WebSocket(mock_scope, mock_protocol)
        websocket._send_message = AsyncMock()
        
        await websocket.accept(subprotocol="chat", headers=[("x-custom", "value")])
        
        websocket._send_message.assert_called_once_with({
            "type": "websocket.accept",
            "subprotocol": "chat",
            "headers": [("x-custom", "value")],
        })
    
    @pytest.mark.asyncio
    async def test_websocket_accept_already_connected(self, mock_scope, mock_protocol):
        """Test WebSocket accept when already connected."""
        websocket = WebSocket(mock_scope, mock_protocol)
        websocket.client_state = WebSocketState.CONNECTED
        
        with pytest.raises(RuntimeError, match="cannot be accepted"):
            await websocket.accept()
    
    @pytest.mark.asyncio
    async def test_websocket_close(self, mock_scope, mock_protocol):
        """Test WebSocket close."""
        websocket = WebSocket(mock_scope, mock_protocol)
        websocket._send_message = AsyncMock()
        
        await websocket.close(code=WS_1008_POLICY_VIOLATION, reason="Policy violation")
        
        assert websocket.application_state == WebSocketState.DISCONNECTED
        websocket._send_message.assert_called_once_with({
            "type": "websocket.close",
            "code": WS_1008_POLICY_VIOLATION,
            "reason": "Policy violation",
        })
    
    @pytest.mark.asyncio
    async def test_websocket_context_manager(self, mock_scope, mock_protocol):
        """Test WebSocket as context manager."""
        websocket = WebSocket(mock_scope, mock_protocol)
        websocket.close = AsyncMock()
        
        async with websocket as ws:
            assert ws == websocket
        
        websocket.close.assert_called_once()


class TestWebSocketEndpoint:
    """Test WebSocketEndpoint class."""
    
    def test_websocket_endpoint_initialization(self, mock_scope, mock_protocol):
        """Test WebSocketEndpoint initialization."""
        endpoint = WebSocketEndpoint(mock_scope, mock_protocol)
        
        assert endpoint.scope == mock_scope
        assert endpoint.protocol == mock_protocol
    
    @pytest.mark.asyncio
    async def test_websocket_endpoint_lifecycle(self, mock_scope, mock_protocol):
        """Test WebSocketEndpoint lifecycle methods."""
        
        class TestEndpoint(WebSocketEndpoint):
            def __init__(self, scope, protocol):
                super().__init__(scope, protocol)
                self.calls = []
            
            async def on_connect(self, websocket):
                self.calls.append("on_connect")
            
            async def on_connect_complete(self, websocket):
                self.calls.append("on_connect_complete")
            
            async def on_receive(self, websocket, data):
                self.calls.append(f"on_receive: {data}")
                if data == "disconnect":
                    raise WebSocketDisconnect()
            
            async def on_disconnect(self, websocket):
                self.calls.append("on_disconnect")
        
        endpoint = TestEndpoint(mock_scope, mock_protocol)
        websocket = WebSocket(mock_scope, mock_protocol)
        websocket.accept = AsyncMock()
        websocket.receive_text = AsyncMock(side_effect=[
            "hello",
            "disconnect"
        ])
        
        await endpoint(websocket)
        
        assert "on_connect" in endpoint.calls
        assert "on_connect_complete" in endpoint.calls
        assert "on_receive: hello" in endpoint.calls
        assert "on_disconnect" in endpoint.calls


class TestWebSocketRoute:
    """Test WebSocketRoute class."""
    
    def test_websocket_route_initialization(self):
        """Test WebSocketRoute initialization."""
        async def handler(websocket):
            pass
        
        route = WebSocketRoute("/ws", handler, name="test_ws")
        
        assert route.path == "/ws"
        assert route.endpoint == handler
        assert route.name == "test_ws"
    
    def test_websocket_route_matches(self, mock_scope):
        """Test WebSocketRoute matches."""
        async def handler(websocket):
            pass
        
        route = WebSocketRoute("/ws", handler)
        
        # Test matching
        match, scope = route.matches(mock_scope)
        assert int(match) > 0  # Should match
        
        # Test non-matching protocol
        mock_scope.proto = "http"
        match, scope = route.matches(mock_scope)
        assert int(match) == 0  # Should not match
    
    def test_websocket_route_with_class_endpoint(self, mock_scope, mock_protocol):
        """Test WebSocketRoute with class-based endpoint."""
        
        class TestEndpoint(WebSocketEndpoint):
            pass
        
        route = WebSocketRoute("/ws", TestEndpoint)
        
        assert route.endpoint == TestEndpoint
        assert route.name == "TestEndpoint"


class TestWebSocketDecorators:
    """Test WebSocket decorators."""
    
    def test_websocket_response_decorator(self):
        """Test websocket_response decorator."""
        @websocket_response
        async def handler(websocket):
            await websocket.send_text("Hello")
        
        # The decorator should return a function
        assert callable(handler)
    
    def test_websocket_route_decorator(self):
        """Test websocket_route decorator."""
        @websocket_route("/ws", name="test")
        async def handler(websocket):
            pass
        
        assert isinstance(handler, WebSocketRoute)
        assert handler.path == "/ws"
        assert handler.name == "test"


class TestWebSocketDisconnect:
    """Test WebSocketDisconnect exception."""
    
    def test_websocket_disconnect_default(self):
        """Test WebSocketDisconnect with default values."""
        exc = WebSocketDisconnect()
        
        assert exc.code == WS_1000_NORMAL_CLOSURE
        assert exc.reason == ""
        assert "1000" in str(exc)
    
    def test_websocket_disconnect_custom(self):
        """Test WebSocketDisconnect with custom values."""
        exc = WebSocketDisconnect(code=WS_1008_POLICY_VIOLATION, reason="Custom reason")
        
        assert exc.code == WS_1008_POLICY_VIOLATION
        assert exc.reason == "Custom reason"
        assert "1008" in str(exc)
        assert "Custom reason" in str(exc)


@pytest.mark.asyncio
async def test_websocket_integration():
    """Integration test for WebSocket functionality."""
    # Create a simple WebSocket handler
    messages = []
    
    async def echo_handler(websocket):
        await websocket.accept()
        try:
            while True:
                message = await websocket.receive_text()
                messages.append(message)
                await websocket.send_text(f"Echo: {message}")
        except WebSocketDisconnect:
            pass
    
    # Create route
    route = WebSocketRoute("/echo", echo_handler)
    
    # Test that route was created properly
    assert route.path == "/echo"
    assert route.name == "echo_handler"
    assert callable(route.app)
