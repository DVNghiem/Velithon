# WebSocket Chat Example

A real-time chat application using WebSockets with Velithon.

## Overview

This example demonstrates how to build a real-time chat application using Velithon's WebSocket support.

## Complete Chat Application

```python
from velithon import Velithon
from velithon.websocket import WebSocket, WebSocketDisconnect
from velithon.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, Set, List
import json
import datetime
import asyncio

app = Velithon()

# Data models
class Message(BaseModel):
    id: str
    username: str
    content: str
    timestamp: datetime.datetime
    message_type: str = "message"

class UserJoinedMessage(BaseModel):
    username: str
    message_type: str = "user_joined"
    timestamp: datetime.datetime

class UserLeftMessage(BaseModel):
    username: str
    message_type: str = "user_left"
    timestamp: datetime.datetime

# In-memory storage
connected_clients: Dict[str, WebSocket] = {}
chat_rooms: Dict[str, Set[str]] = {}
message_history: Dict[str, List[Message]] = {}

class ChatManager:
    def __init__(self):
        self.rooms = chat_rooms
        self.clients = connected_clients
        self.history = message_history
    
    async def connect_user(self, websocket: WebSocket, username: str, room: str):
        """Connect a user to a chat room"""
        # Accept the WebSocket connection
        await websocket.accept()
        
        # Add user to room
        client_id = f"{username}_{room}"
        self.clients[client_id] = websocket
        
        if room not in self.rooms:
            self.rooms[room] = set()
            self.history[room] = []
        
        self.rooms[room].add(username)
        
        # Send chat history to the new user
        for message in self.history[room][-50:]:  # Last 50 messages
            await websocket.send_text(json.dumps(message.dict()))
        
        # Notify other users
        join_message = UserJoinedMessage(
            username=username,
            timestamp=datetime.datetime.now()
        )
        await self.broadcast_to_room(room, join_message.dict(), exclude=username)
    
    async def disconnect_user(self, username: str, room: str):
        """Disconnect a user from a chat room"""
        client_id = f"{username}_{room}"
        
        # Remove from clients
        if client_id in self.clients:
            del self.clients[client_id]
        
        # Remove from room
        if room in self.rooms and username in self.rooms[room]:
            self.rooms[room].remove(username)
            
            # Clean up empty rooms
            if not self.rooms[room]:
                del self.rooms[room]
                del self.history[room]
            else:
                # Notify other users
                leave_message = UserLeftMessage(
                    username=username,
                    timestamp=datetime.datetime.now()
                )
                await self.broadcast_to_room(room, leave_message.dict())
    
    async def send_message(self, username: str, room: str, content: str):
        """Send a message to a chat room"""
        message = Message(
            id=f"{username}_{int(datetime.datetime.now().timestamp())}",
            username=username,
            content=content,
            timestamp=datetime.datetime.now()
        )
        
        # Store message in history
        if room in self.history:
            self.history[room].append(message)
            
            # Keep only last 1000 messages
            if len(self.history[room]) > 1000:
                self.history[room] = self.history[room][-1000:]
        
        # Broadcast to all users in the room
        await self.broadcast_to_room(room, message.dict())
    
    async def broadcast_to_room(self, room: str, message: dict, exclude: str = None):
        """Broadcast a message to all users in a room"""
        if room not in self.rooms:
            return
        
        message_text = json.dumps(message)
        disconnected_clients = []
        
        for username in self.rooms[room]:
            if exclude and username == exclude:
                continue
                
            client_id = f"{username}_{room}"
            if client_id in self.clients:
                try:
                    await self.clients[client_id].send_text(message_text)
                except:
                    # Mark for cleanup
                    disconnected_clients.append(username)
        
        # Clean up disconnected clients
        for username in disconnected_clients:
            await self.disconnect_user(username, room)
    
    def get_room_users(self, room: str) -> List[str]:
        """Get list of users in a room"""
        return list(self.rooms.get(room, set()))
    
    def get_active_rooms(self) -> List[str]:
        """Get list of active rooms"""
        return list(self.rooms.keys())

chat_manager = ChatManager()

# WebSocket endpoint
@app.websocket("/ws/{room}/{username}")
async def websocket_endpoint(websocket: WebSocket, room: str, username: str):
    """WebSocket endpoint for chat"""
    try:
        await chat_manager.connect_user(websocket, username, room)
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "message":
                content = message_data.get("content", "").strip()
                if content:
                    await chat_manager.send_message(username, room, content)
            
    except WebSocketDisconnect:
        await chat_manager.disconnect_user(username, room)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await chat_manager.disconnect_user(username, room)

# HTTP endpoints
@app.get("/")
async def chat_page():
    """Serve the chat interface"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Velithon Chat</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
            .chat-container { max-width: 800px; margin: 0 auto; }
            .messages { border: 1px solid #ccc; height: 400px; overflow-y: auto; padding: 10px; margin-bottom: 10px; }
            .message { margin-bottom: 10px; }
            .username { font-weight: bold; color: #007bff; }
            .timestamp { font-size: 0.8em; color: #666; }
            .system-message { color: #28a745; font-style: italic; }
            .input-area { display: flex; gap: 10px; }
            .input-area input { flex: 1; padding: 10px; }
            .input-area button { padding: 10px 20px; }
            .room-info { background: #f8f9fa; padding: 10px; margin-bottom: 10px; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <h1>Velithon Chat</h1>
            
            <div class="room-info">
                <strong>Room:</strong> <span id="room-name">general</span><br>
                <strong>Username:</strong> <span id="username-display">Anonymous</span><br>
                <strong>Users online:</strong> <span id="users-count">0</span>
            </div>
            
            <div id="messages" class="messages"></div>
            
            <div class="input-area">
                <input type="text" id="message-input" placeholder="Type your message..." />
                <button onclick="sendMessage()">Send</button>
            </div>
            
            <div style="margin-top: 10px;">
                <input type="text" id="room-input" placeholder="Room name" value="general" />
                <input type="text" id="username-input" placeholder="Your username" value="Anonymous" />
                <button onclick="connectToChat()">Connect</button>
                <button onclick="disconnectFromChat()">Disconnect</button>
            </div>
        </div>

        <script>
            let ws = null;
            let currentRoom = 'general';
            let currentUsername = 'Anonymous';

            function connectToChat() {
                const room = document.getElementById('room-input').value || 'general';
                const username = document.getElementById('username-input').value || 'Anonymous';
                
                if (ws) {
                    ws.close();
                }
                
                currentRoom = room;
                currentUsername = username;
                
                document.getElementById('room-name').textContent = room;
                document.getElementById('username-display').textContent = username;
                
                const wsUrl = `ws://localhost:8000/ws/${room}/${username}`;
                ws = new WebSocket(wsUrl);
                
                ws.onopen = function(event) {
                    addSystemMessage('Connected to chat');
                };
                
                ws.onmessage = function(event) {
                    const message = JSON.parse(event.data);
                    displayMessage(message);
                };
                
                ws.onclose = function(event) {
                    addSystemMessage('Disconnected from chat');
                };
                
                ws.onerror = function(error) {
                    addSystemMessage('Connection error: ' + error);
                };
            }

            function disconnectFromChat() {
                if (ws) {
                    ws.close();
                    ws = null;
                }
            }

            function sendMessage() {
                const input = document.getElementById('message-input');
                const content = input.value.trim();
                
                if (content && ws && ws.readyState === WebSocket.OPEN) {
                    const message = {
                        type: 'message',
                        content: content
                    };
                    ws.send(JSON.stringify(message));
                    input.value = '';
                }
            }

            function displayMessage(message) {
                const messagesDiv = document.getElementById('messages');
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message';
                
                const timestamp = new Date(message.timestamp).toLocaleTimeString();
                
                if (message.message_type === 'message') {
                    messageDiv.innerHTML = `
                        <span class="username">${message.username}:</span>
                        ${message.content}
                        <span class="timestamp">(${timestamp})</span>
                    `;
                } else if (message.message_type === 'user_joined') {
                    messageDiv.innerHTML = `<span class="system-message">${message.username} joined the chat (${timestamp})</span>`;
                } else if (message.message_type === 'user_left') {
                    messageDiv.innerHTML = `<span class="system-message">${message.username} left the chat (${timestamp})</span>`;
                }
                
                messagesDiv.appendChild(messageDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }

            function addSystemMessage(text) {
                const messagesDiv = document.getElementById('messages');
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message';
                messageDiv.innerHTML = `<span class="system-message">${text}</span>`;
                messagesDiv.appendChild(messageDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }

            // Enter key to send message
            document.getElementById('message-input').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    sendMessage();
                }
            });

            // Auto-connect on page load
            window.onload = function() {
                connectToChat();
            };
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html_content)

@app.get("/api/rooms", tags=["chat"])
async def get_active_rooms():
    """Get list of active chat rooms"""
    rooms = chat_manager.get_active_rooms()
    return JSONResponse({"rooms": rooms})

@app.get("/api/rooms/{room}/users", tags=["chat"])
async def get_room_users(room: str):
    """Get list of users in a specific room"""
    users = chat_manager.get_room_users(room)
    return JSONResponse({"room": room, "users": users})

@app.get("/api/rooms/{room}/messages", tags=["chat"])
async def get_room_messages(room: str, limit: int = 50):
    """Get recent messages from a room"""
    messages = chat_manager.history.get(room, [])
    recent_messages = messages[-limit:] if messages else []
    return JSONResponse({
        "room": room,
        "messages": [msg.dict() for msg in recent_messages]
    })

if __name__ == "__main__":
    print("Starting Velithon Chat Server...")
    print("Open http://localhost:8000 in your browser")
    app.run(debug=True)
```

## Usage Examples

### Connect to Chat

Open your browser and go to `http://localhost:8000`

### Using the WebSocket API directly

```javascript
// Connect to a room
const ws = new WebSocket('ws://localhost:8000/ws/general/john');

// Send a message
ws.send(JSON.stringify({
    type: 'message',
    content: 'Hello everyone!'
}));

// Receive messages
ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    console.log('Received:', message);
};
```

### REST API Endpoints

```bash
# Get active rooms
curl http://localhost:8000/api/rooms

# Get users in a room
curl http://localhost:8000/api/rooms/general/users

# Get recent messages
curl http://localhost:8000/api/rooms/general/messages?limit=20
```

## Key Features Demonstrated

- **Real-time Communication**: Bidirectional WebSocket communication
- **Multiple Rooms**: Support for different chat rooms
- **User Management**: Track connected users per room
- **Message History**: Store and retrieve chat history
- **System Messages**: User join/leave notifications
- **Error Handling**: Graceful WebSocket disconnection handling
- **Web Interface**: Complete HTML/CSS/JavaScript chat UI
- **REST API**: HTTP endpoints for chat data

## Enhancements

You can extend this example by adding:

### 1. User Authentication
```python
from typing import Annotated
from velithon.security import HTTPBearer

bearer_scheme = HTTPBearer()

async def get_current_user_from_token(request):
    """Extract and verify user from token."""
    token = await bearer_scheme(request)
    # Verify token and return user
    return verify_token(token)

@app.websocket("/ws/{room}")
async def authenticated_websocket(
    websocket: WebSocket, 
    room: str,
    current_user: Annotated[User, get_current_user_from_token]
):
    await chat_manager.connect_user(websocket, current_user.username, room)
```

### 2. Message Persistence
```python
import aiofiles
import json

async def save_message_to_file(room: str, message: Message):
    async with aiofiles.open(f"chat_logs/{room}.jsonl", "a") as f:
        await f.write(json.dumps(message.dict()) + "\n")
```

### 3. Rate Limiting
```python
from collections import defaultdict
import time

class RateLimiter:
    def __init__(self, max_messages: int = 10, window: int = 60):
        self.max_messages = max_messages
        self.window = window
        self.user_messages = defaultdict(list)
    
    def is_allowed(self, username: str) -> bool:
        now = time.time()
        user_msgs = self.user_messages[username]
        
        # Remove old messages
        self.user_messages[username] = [
            msg_time for msg_time in user_msgs 
            if now - msg_time < self.window
        ]
        
        # Check limit
        if len(self.user_messages[username]) >= self.max_messages:
            return False
        
        self.user_messages[username].append(now)
        return True
```

### 4. Private Messages
```python
async def send_private_message(from_user: str, to_user: str, content: str):
    """Send a private message between users"""
    private_message = {
        "type": "private_message",
        "from": from_user,
        "to": to_user,
        "content": content,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    # Find target user's WebSocket connection
    for client_id, websocket in chat_manager.clients.items():
        if client_id.startswith(f"{to_user}_"):
            await websocket.send_text(json.dumps(private_message))
            break
```

## Testing

```python
import pytest
import asyncio
from velithon.testing import WebSocketTestSession

@pytest.mark.asyncio
async def test_chat_connection():
    async with WebSocketTestSession(app) as client:
        websocket = await client.websocket_connect("/ws/test_room/test_user")
        
        # Send a message
        await websocket.send_json({
            "type": "message",
            "content": "Hello test!"
        })
        
        # Receive the message back
        data = await websocket.receive_json()
        assert data["content"] == "Hello test!"
        assert data["username"] == "test_user"
```

## Production Considerations

1. **Database Storage**: Use Redis or PostgreSQL for message persistence
2. **Scaling**: Implement Redis pub/sub for multi-server deployments
3. **Security**: Add authentication and authorization
4. **Rate Limiting**: Prevent spam and abuse
5. **Monitoring**: Add logging and metrics
6. **Content Moderation**: Filter inappropriate content
7. **File Sharing**: Support image/file uploads
8. **Mobile Support**: Optimize for mobile devices

This example provides a solid foundation for building real-time chat applications with Velithon's WebSocket support.
