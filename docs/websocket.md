# WebSocket Support in Velithon

Velithon provides comprehensive WebSocket support for real-time communication in web applications.

## Features

- **Function-based WebSocket handlers**: Simple functions that handle WebSocket connections
- **Class-based WebSocket endpoints**: Object-oriented approach with lifecycle methods
- **Automatic connection management**: Built-in connection state handling
- **Type safety**: Full type annotations for better development experience
- **Integration with routing**: WebSocket routes work seamlessly with HTTP routes
- **Error handling**: Comprehensive error handling and disconnection management

## Quick Start

### Function-based WebSocket Handler

```python
from velithon import Velithon, WebSocket
from velithon.websocket import WebSocketDisconnect

app = Velithon()

@app.websocket("/echo")
async def echo_handler(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            await websocket.send_text(f"Echo: {message}")
    except WebSocketDisconnect:
        print("Client disconnected")
```

### Class-based WebSocket Endpoint

```python
from velithon.websocket import WebSocketEndpoint

class ChatEndpoint(WebSocketEndpoint):
    async def on_connect(self, websocket: WebSocket):
        print(f"Client connected: {websocket.client}")
    
    async def on_receive(self, websocket: WebSocket, data: str):
        # Echo the message back
        await websocket.send_text(f"You said: {data}")
    
    async def on_disconnect(self, websocket: WebSocket):
        print(f"Client disconnected: {websocket.client}")

app.add_websocket_route("/chat", ChatEndpoint)
```

## WebSocket Class

The `WebSocket` class provides methods for managing WebSocket connections:

### Connection Management

```python
# Accept the WebSocket connection
await websocket.accept()

# Accept with subprotocol and headers
await websocket.accept(
    subprotocol="chat",
    headers=[("x-custom-header", "value")]
)

# Close the connection
await websocket.close(code=1000, reason="Normal closure")
```

### Sending Messages

```python
# Send text message
await websocket.send_text("Hello, client!")

# Send binary message
await websocket.send_bytes(b"Binary data")

# Send JSON message
await websocket.send_json({"type": "message", "data": "Hello"})
```

### Receiving Messages

```python
# Receive text message
message = await websocket.receive_text()

# Receive binary message
data = await websocket.receive_bytes()

# Receive JSON message
json_data = await websocket.receive_json()
```

### Properties

```python
# Get WebSocket URL
url = websocket.url

# Get client address
client = websocket.client  # Returns (host, port) tuple

# Get headers
headers = websocket.headers

# Get query parameters
params = websocket.query_params

# Get path parameters
path_params = websocket.path_params
```

## WebSocketEndpoint Class

The `WebSocketEndpoint` class provides a structured way to handle WebSocket connections with lifecycle methods:

### Lifecycle Methods

```python
class MyEndpoint(WebSocketEndpoint):
    async def on_connect(self, websocket: WebSocket):
        """Called when a client connects (before accept)."""
        pass
    
    async def on_connect_complete(self, websocket: WebSocket):
        """Called after the connection is accepted."""
        pass
    
    async def on_receive(self, websocket: WebSocket, data: str):
        """Called when a message is received."""
        pass
    
    async def on_disconnect(self, websocket: WebSocket):
        """Called when the connection is closed."""
        pass
    
    async def on_error(self, websocket: WebSocket, error: Exception):
        """Called when an error occurs."""
        pass
```

## Error Handling

### WebSocketDisconnect Exception

```python
from velithon.websocket import WebSocketDisconnect

try:
    message = await websocket.receive_text()
except WebSocketDisconnect as exc:
    print(f"WebSocket disconnected with code {exc.code}: {exc.reason}")
```

### Connection States

```python
from velithon.websocket import WebSocketState

# Check connection state
if websocket.client_state == WebSocketState.CONNECTED:
    await websocket.send_text("Connected!")
```

## Advanced Usage

### WebSocket with Path Parameters

```python
@app.websocket("/chat/{room_id}")
async def chat_room(websocket: WebSocket):
    room_id = websocket.path_params["room_id"]
    await websocket.accept()
    # Handle room-specific chat logic
```

### WebSocket with Query Parameters

```python
@app.websocket("/ws")
async def websocket_handler(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return
    
    await websocket.accept()
    # Handle authenticated connection
```

### Broadcasting to Multiple Clients

```python
class BroadcastEndpoint(WebSocketEndpoint):
    connected_clients = set()
    
    async def on_connect_complete(self, websocket: WebSocket):
        self.connected_clients.add(websocket)
    
    async def on_disconnect(self, websocket: WebSocket):
        self.connected_clients.discard(websocket)
    
    async def broadcast(self, message: str):
        """Broadcast message to all connected clients."""
        disconnected = set()
        for client in self.connected_clients:
            try:
                await client.send_text(message)
            except Exception:
                disconnected.add(client)
        
        # Remove disconnected clients
        self.connected_clients -= disconnected
```

## Example Application

See `examples/websocket_demo.py` for a complete example that demonstrates:

- Echo WebSocket handler
- Chat room with multiple clients
- Status updates with periodic messages
- HTML client interface

## Running the Example

```bash
python examples/websocket_demo.py
```

Then open http://localhost:8000 in your browser to interact with the WebSocket endpoints.

## WebSocket Status Codes

Common WebSocket close codes are available in `velithon.status`:

```python
from velithon.status import (
    WS_1000_NORMAL_CLOSURE,
    WS_1001_GOING_AWAY,
    WS_1002_PROTOCOL_ERROR,
    WS_1003_UNSUPPORTED_DATA,
    WS_1008_POLICY_VIOLATION,
    WS_1009_MESSAGE_TOO_BIG,
    WS_1011_INTERNAL_ERROR,
)

await websocket.close(code=WS_1008_POLICY_VIOLATION, reason="Invalid auth token")
```

## Integration with Middleware

WebSocket connections work with Velithon's middleware system. Middleware that operates on the scope and protocol level will also affect WebSocket connections.

## Best Practices

1. **Always handle WebSocketDisconnect**: Clients can disconnect at any time
2. **Use try/except blocks**: Wrap WebSocket operations in appropriate error handling
3. **Clean up resources**: Remove disconnected clients from any collections
4. **Validate messages**: Always validate incoming data before processing
5. **Use appropriate close codes**: Use meaningful close codes when closing connections
6. **Handle connection limits**: Implement limits for concurrent connections if needed

## Limitations

- WebSocket message handling is currently simplified and may need integration with the underlying RSGI server for full production use
- Binary message handling is basic and may need enhancement for complex use cases
- No built-in support for WebSocket extensions or subprotocols beyond basic acceptance
