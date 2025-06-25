# WebSocket Support

## Function-Based WebSocket Handlers

```python
from velithon import WebSocket
from velithon.websocket import WebSocketDisconnect

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

## Class-Based WebSocket Endpoints

```python
from velithon.websocket import WebSocketEndpoint

class ChatEndpoint(WebSocketEndpoint):
    async def on_connect(self, websocket: WebSocket):
        print(f"Client connected: {websocket.client}")
        await websocket.accept()
    
    async def on_receive(self, websocket: WebSocket, data: str):
        # Echo the message back
        await websocket.send_text(f"You said: {data}")
    
    async def on_disconnect(self, websocket: WebSocket):
        print(f"Client disconnected: {websocket.client}")

app.add_websocket_route("/chat", ChatEndpoint)
```

## WebSocket with Path Parameters

```python
@app.websocket("/chat/{room_id}")
async def chat_room(websocket: WebSocket):
    room_id = websocket.path_params["room_id"]
    await websocket.accept()
    
    try:
        while True:
            message = await websocket.receive_text()
            # Broadcast to room
            await websocket.send_text(f"[Room {room_id}] {message}")
    except WebSocketDisconnect:
        pass
```
