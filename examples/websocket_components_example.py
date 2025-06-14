"""
Example demonstrating WebSocket Channel, Heartbeat, and Room functionality in Velithon.

This example shows how to use the new WebSocket components to build a chat application
with rooms, user management, and connection health monitoring.
"""

import json
from typing import Dict

from velithon import Velithon
from velithon.websocket import (
    HeartbeatManager,
    RoomManager,
    WebSocket,
    WebSocketEndpoint,
)


# Global managers
room_manager = RoomManager(max_rooms=100, default_max_users=50)
heartbeat_manager = HeartbeatManager(default_interval=30.0, default_timeout=10.0)

# Connection tracking
connections: Dict[str, WebSocket] = {}
user_connections: Dict[str, str] = {}  # user_id -> connection_id


class ChatEndpoint(WebSocketEndpoint):
    """WebSocket endpoint for chat functionality."""
    
    async def on_connect(self, websocket: WebSocket):
        """Handle new WebSocket connections."""
        try:
            await websocket.accept()
            print(f"New connection from {websocket.client}")
            
            # Generate connection ID
            connection_id = f"conn_{id(websocket)}"
            connections[connection_id] = websocket
            
            # Add heartbeat monitoring
            await heartbeat_manager.add_connection(
                websocket=websocket,
                connection_id=connection_id,
                auto_start=True,
            )
            
            # Send welcome message
            await websocket.send_json({
                "type": "welcome",
                "message": "Connected to chat server",
                "connection_id": connection_id,
            })
            
        except Exception as e:
            print(f"Error in on_connect: {e}")
            await websocket.close()
    
    async def on_receive(self, websocket: WebSocket, data: str):
        """Handle incoming messages."""
        try:
            message = json.loads(data)
            message_type = message.get("type")
            connection_id = f"conn_{id(websocket)}"
            
            # Handle heartbeat pong
            if message_type == "pong":
                await heartbeat_manager.handle_pong(
                    connection_id=connection_id,
                    data=message.get("data"),
                )
                return
            
            # Handle user authentication
            elif message_type == "auth":
                await self._handle_auth(websocket, connection_id, message)
            
            # Handle room operations
            elif message_type == "join_room":
                await self._handle_join_room(websocket, connection_id, message)
            
            elif message_type == "leave_room":
                await self._handle_leave_room(websocket, connection_id, message)
            
            elif message_type == "send_message":
                await self._handle_send_message(websocket, connection_id, message)
            
            elif message_type == "list_rooms":
                await self._handle_list_rooms(websocket)
            
            elif message_type == "room_info":
                await self._handle_room_info(websocket, message)
            
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}",
                })
        
        except json.JSONDecodeError:
            await websocket.send_json({
                "type": "error",
                "message": "Invalid JSON format",
            })
        except Exception as e:
            print(f"Error handling message: {e}")
            await websocket.send_json({
                "type": "error",
                "message": "Internal server error",
            })
    
    async def on_disconnect(self, websocket: WebSocket):
        """Handle WebSocket disconnections."""
        connection_id = f"conn_{id(websocket)}"
        print(f"Connection {connection_id} disconnected")
        
        # Remove from heartbeat monitoring
        await heartbeat_manager.remove_connection(connection_id)
        
        # Find user ID
        user_id = None
        for uid, cid in user_connections.items():
            if cid == connection_id:
                user_id = uid
                break
        
        # Remove from all rooms
        if user_id:
            await room_manager.leave_all_rooms(user_id)
            del user_connections[user_id]
        
        # Clean up connection
        connections.pop(connection_id, None)
    
    async def _handle_auth(self, websocket: WebSocket, connection_id: str, message: Dict):
        """Handle user authentication."""
        user_id = message.get("user_id")
        if not user_id:
            await websocket.send_json({
                "type": "auth_error",
                "message": "user_id is required",
            })
            return
        
        # Store user connection mapping
        user_connections[user_id] = connection_id
        
        await websocket.send_json({
            "type": "auth_success",
            "user_id": user_id,
            "message": "Authentication successful",
        })
    
    async def _handle_join_room(self, websocket: WebSocket, connection_id: str, message: Dict):
        """Handle joining a room."""
        room_id = message.get("room_id")
        user_id = self._get_user_id(connection_id)
        
        if not room_id or not user_id:
            await websocket.send_json({
                "type": "join_error",
                "message": "room_id and authenticated user required",
            })
            return
        
        # Get or create room
        room = room_manager.get_room(room_id)
        if not room:
            room = await room_manager.create_room(
                room_id=room_id,
                name=message.get("room_name", room_id),
                max_users=message.get("max_users", 50),
            )
        
        # Join room
        success = await room_manager.join_room(
            room_id=room_id,
            user_id=user_id,
            websocket=websocket,
            connection_id=connection_id,
            metadata=message.get("metadata", {}),
        )
        
        if success:
            await websocket.send_json({
                "type": "join_success",
                "room_id": room_id,
                "user_count": room.user_count,
                "message": f"Joined room {room_id}",
            })
        else:
            await websocket.send_json({
                "type": "join_error",
                "message": "Failed to join room",
            })
    
    async def _handle_leave_room(self, websocket: WebSocket, connection_id: str, message: Dict):
        """Handle leaving a room."""
        room_id = message.get("room_id")
        user_id = self._get_user_id(connection_id)
        
        if not room_id or not user_id:
            await websocket.send_json({
                "type": "leave_error",
                "message": "room_id and authenticated user required",
            })
            return
        
        success = await room_manager.leave_room(room_id, user_id)
        
        if success:
            await websocket.send_json({
                "type": "leave_success",
                "room_id": room_id,
                "message": f"Left room {room_id}",
            })
        else:
            await websocket.send_json({
                "type": "leave_error",
                "message": "Failed to leave room",
            })
    
    async def _handle_send_message(self, websocket: WebSocket, connection_id: str, message: Dict):
        """Handle sending a message to a room."""
        room_id = message.get("room_id")
        content = message.get("content")
        user_id = self._get_user_id(connection_id)
        
        if not room_id or not content or not user_id:
            await websocket.send_json({
                "type": "message_error",
                "message": "room_id, content, and authenticated user required",
            })
            return
        
        room = room_manager.get_room(room_id)
        if not room:
            await websocket.send_json({
                "type": "message_error",
                "message": "Room not found",
            })
            return
        
        success = await room.send_message(
            sender_id=user_id,
            content=content,
            message_type=message.get("message_type", "text"),
            metadata=message.get("metadata", {}),
        )
        
        if success:
            await websocket.send_json({
                "type": "message_sent",
                "room_id": room_id,
                "message": "Message sent successfully",
            })
        else:
            await websocket.send_json({
                "type": "message_error",
                "message": "Failed to send message",
            })
    
    async def _handle_list_rooms(self, websocket: WebSocket):
        """Handle listing available rooms."""
        rooms = room_manager.list_rooms()
        
        room_list = []
        for room in rooms:
            room_list.append({
                "room_id": room.room_id,
                "name": room.name,
                "user_count": room.user_count,
                "max_users": room.max_users,
                "state": room.state.value,
            })
        
        await websocket.send_json({
            "type": "room_list",
            "rooms": room_list,
        })
    
    async def _handle_room_info(self, websocket: WebSocket, message: Dict):
        """Handle getting room information."""
        room_id = message.get("room_id")
        if not room_id:
            await websocket.send_json({
                "type": "room_info_error",
                "message": "room_id is required",
            })
            return
        
        room = room_manager.get_room(room_id)
        if not room:
            await websocket.send_json({
                "type": "room_info_error",
                "message": "Room not found",
            })
            return
        
        users = [user.to_dict() for user in room.list_users()]
        history = room.get_message_history(limit=20)
        
        await websocket.send_json({
            "type": "room_info",
            "room_id": room_id,
            "name": room.name,
            "user_count": room.user_count,
            "max_users": room.max_users,
            "state": room.state.value,
            "users": users,
            "recent_messages": history,
            "stats": room.stats,
        })
    
    def _get_user_id(self, connection_id: str) -> str:
        """Get user ID for a connection."""
        for user_id, conn_id in user_connections.items():
            if conn_id == connection_id:
                return user_id
        return None


# Create Velithon app
app = Velithon()

# Add WebSocket route
app.add_websocket_route("/ws/chat", ChatEndpoint)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    manager_stats = room_manager.stats
    heartbeat_stats = heartbeat_manager.stats
    
    return {
        "status": "healthy",
        "connections": len(connections),
        "room_manager": manager_stats,
        "heartbeat_manager": heartbeat_stats,
    }


# Room management endpoints
@app.get("/api/rooms")
async def list_rooms():
    """List all rooms via HTTP API."""
    rooms = room_manager.list_rooms()
    
    return {
        "rooms": [
            {
                "room_id": room.room_id,
                "name": room.name,
                "user_count": room.user_count,
                "max_users": room.max_users,
                "state": room.state.value,
                "created_at": room.created_at.isoformat(),
            }
            for room in rooms
        ]
    }


@app.post("/api/rooms")
async def create_room_api(request):
    """Create a room via HTTP API."""
    data = await request.json()
    
    room_id = data.get("room_id")
    name = data.get("name", room_id)
    max_users = data.get("max_users", 50)
    
    if not room_id:
        return {"error": "room_id is required"}, 400
    
    try:
        room = await room_manager.create_room(
            room_id=room_id,
            name=name,
            max_users=max_users,
        )
        
        return {
            "room_id": room.room_id,
            "name": room.name,
            "max_users": room.max_users,
            "created_at": room.created_at.isoformat(),
        }
    
    except ValueError as e:
        return {"error": str(e)}, 400


@app.delete("/api/rooms/{room_id}")
async def delete_room_api(request):
    """Delete a room via HTTP API."""
    room_id = request.path_params["room_id"]
    
    success = await room_manager.delete_room(room_id)
    
    if success:
        return {"message": f"Room {room_id} deleted"}
    else:
        return {"error": "Room not found"}, 404


# Startup and shutdown events
@app.on_startup()
async def startup():
    """Start background services."""
    await room_manager.start()
    await heartbeat_manager.start()
    print("Chat server started")


@app.on_shutdown()
async def shutdown():
    """Stop background services."""
    await room_manager.stop()
    await heartbeat_manager.stop()
    print("Chat server stopped")


# Example HTML client
@app.get("/")
async def chat_client():
    """Serve a simple chat client."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Velithon Chat</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            #messages { border: 1px solid #ccc; height: 300px; overflow-y: scroll; padding: 10px; margin: 10px 0; }
            #input { width: 70%; padding: 5px; }
            #send { padding: 5px 10px; }
            .room-controls { margin: 10px 0; }
            .room-controls input { margin: 5px; padding: 5px; }
            .message { margin: 5px 0; padding: 5px; border-left: 3px solid #007cba; }
            .system { border-left-color: #999; color: #666; }
        </style>
    </head>
    <body>
        <h1>Velithon Chat Example</h1>
        
        <div class="room-controls">
            <input type="text" id="userId" placeholder="Enter your user ID" />
            <button onclick="authenticate()">Login</button>
            <span id="authStatus"></span>
        </div>
        
        <div class="room-controls">
            <input type="text" id="roomId" placeholder="Enter room ID" />
            <button onclick="joinRoom()">Join Room</button>
            <button onclick="leaveRoom()">Leave Room</button>
            <button onclick="listRooms()">List Rooms</button>
        </div>
        
        <div id="messages"></div>
        
        <div>
            <input type="text" id="messageInput" placeholder="Type a message..." />
            <button id="send" onclick="sendMessage()">Send</button>
        </div>
        
        <div id="status">Connecting...</div>
        
        <script>
            const ws = new WebSocket("ws://localhost:8000/ws/chat");
            const messages = document.getElementById("messages");
            const status = document.getElementById("status");
            let currentUser = null;
            let currentRoom = null;
            
            ws.onopen = function() {
                status.textContent = "Connected";
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                addMessage(data);
                
                // Handle ping requests
                if (data.type === "ping") {
                    ws.send(JSON.stringify({
                        type: "pong",
                        data: data.data
                    }));
                }
            };
            
            ws.onclose = function() {
                status.textContent = "Disconnected";
            };
            
            function addMessage(data) {
                const div = document.createElement("div");
                div.className = "message";
                
                if (data.type === "room.message") {
                    div.innerHTML = `<strong>${data.data.sender_id}:</strong> ${data.data.content}`;
                } else if (data.type === "room.system_message") {
                    div.className += " system";
                    div.innerHTML = `<em>System:</em> ${data.data.content}`;
                } else {
                    div.className += " system";
                    div.innerHTML = `<em>${data.type}:</em> ${data.message || JSON.stringify(data)}`;
                }
                
                messages.appendChild(div);
                messages.scrollTop = messages.scrollHeight;
            }
            
            function authenticate() {
                const userId = document.getElementById("userId").value.trim();
                if (!userId) {
                    alert("Please enter a user ID");
                    return;
                }
                
                ws.send(JSON.stringify({
                    type: "auth",
                    user_id: userId
                }));
                
                currentUser = userId;
                document.getElementById("authStatus").textContent = `Logged in as: ${userId}`;
            }
            
            function joinRoom() {
                const roomId = document.getElementById("roomId").value.trim();
                if (!roomId) {
                    alert("Please enter a room ID");
                    return;
                }
                
                if (!currentUser) {
                    alert("Please login first");
                    return;
                }
                
                ws.send(JSON.stringify({
                    type: "join_room",
                    room_id: roomId,
                    room_name: roomId
                }));
                
                currentRoom = roomId;
            }
            
            function leaveRoom() {
                if (!currentRoom) {
                    alert("You're not in a room");
                    return;
                }
                
                ws.send(JSON.stringify({
                    type: "leave_room",
                    room_id: currentRoom
                }));
                
                currentRoom = null;
            }
            
            function listRooms() {
                ws.send(JSON.stringify({
                    type: "list_rooms"
                }));
            }
            
            function sendMessage() {
                const input = document.getElementById("messageInput");
                const message = input.value.trim();
                
                if (!message || !currentRoom) {
                    alert("Please enter a message and join a room first");
                    return;
                }
                
                ws.send(JSON.stringify({
                    type: "send_message",
                    room_id: currentRoom,
                    content: message
                }));
                
                input.value = "";
            }
            
            document.getElementById("messageInput").addEventListener("keypress", function(e) {
                if (e.key === "Enter") {
                    sendMessage();
                }
            });
        </script>
    </body>
    </html>
    """


if __name__ == "__main__":
    # For testing purposes
    import granian
    
    server = granian.Granian(
        target="examples.websocket_components_example:app",
        address="127.0.0.1",
        port=8000,
        interface="rsgi"
    )
    server.serve()
