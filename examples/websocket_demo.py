"""
Example WebSocket application demonstrating Velithon WebSocket features.
"""
import asyncio
import json
from velithon import Velithon, WebSocket, WebSocketEndpoint
from velithon.websocket import WebSocketDisconnect, websocket_route


# Simple function-based WebSocket handler
@websocket_route("/echo")
async def echo_handler(websocket: WebSocket):
    """Simple echo WebSocket handler."""
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            await websocket.send_text(f"Echo: {message}")
    except WebSocketDisconnect:
        print("WebSocket disconnected")


# Class-based WebSocket endpoint
class ChatEndpoint(WebSocketEndpoint):
    """Chat room WebSocket endpoint."""
    
    # In a real application, this would be a proper storage solution
    connected_clients = set()
    
    async def on_connect(self, websocket: WebSocket):
        """Called when client connects."""
        print(f"Client connecting from {websocket.client}")
    
    async def on_connect_complete(self, websocket: WebSocket):
        """Called after WebSocket is accepted."""
        self.connected_clients.add(websocket)
        await self.broadcast_message({
            "type": "user_joined",
            "message": f"User from {websocket.client} joined the chat"
        })
    
    async def on_receive(self, websocket: WebSocket, data: str):
        """Handle received messages."""
        try:
            message = json.loads(data)
            if message.get("type") == "chat":
                await self.broadcast_message({
                    "type": "chat",
                    "user": str(websocket.client),
                    "message": message.get("message", "")
                })
        except json.JSONDecodeError:
            await websocket.send_json({
                "type": "error",
                "message": "Invalid JSON format"
            })
    
    async def on_disconnect(self, websocket: WebSocket):
        """Handle client disconnect."""
        self.connected_clients.discard(websocket)
        await self.broadcast_message({
            "type": "user_left",
            "message": f"User from {websocket.client} left the chat"
        })
    
    async def on_error(self, websocket: WebSocket, error: Exception):
        """Handle errors."""
        print(f"WebSocket error: {error}")
        await websocket.close(code=1011, reason="Internal error")
    
    async def broadcast_message(self, message: dict):
        """Broadcast message to all connected clients."""
        message_text = json.dumps(message)
        disconnected = set()
        
        for client in self.connected_clients:
            try:
                await client.send_text(message_text)
            except Exception:
                disconnected.add(client)
        
        # Remove disconnected clients
        self.connected_clients -= disconnected


# Create application
app = Velithon()

# Add WebSocket routes
app.add_websocket_route("/echo", echo_handler)
app.add_websocket_route("/chat", ChatEndpoint)

# You can also use decorators
@app.websocket("/status")
async def status_handler(websocket: WebSocket):
    """WebSocket status endpoint."""
    await websocket.accept()
    
    try:
        # Send periodic status updates
        counter = 0
        while True:
            await websocket.send_json({
                "type": "status",
                "counter": counter,
                "message": f"Status update #{counter}"
            })
            counter += 1
            await asyncio.sleep(5)  # Send update every 5 seconds
    except WebSocketDisconnect:
        print("Status WebSocket disconnected")


# Add regular HTTP routes for serving the client
@app.get("/")
async def home():
    """Serve a simple HTML page with WebSocket client."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Velithon WebSocket Demo</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 600px; margin: 0 auto; }
            .chat-box { border: 1px solid #ccc; height: 300px; overflow-y: scroll; padding: 10px; margin: 10px 0; }
            .message { margin: 5px 0; padding: 5px; background: #f5f5f5; border-radius: 3px; }
            input, button { padding: 8px; margin: 5px; }
            input[type="text"] { width: 300px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Velithon WebSocket Demo</h1>
            
            <h2>Echo Test</h2>
            <div>
                <input type="text" id="echoInput" placeholder="Type message to echo">
                <button onclick="sendEcho()">Send Echo</button>
            </div>
            <div id="echoResult"></div>
            
            <h2>Chat Room</h2>
            <div id="chatBox" class="chat-box"></div>
            <div>
                <input type="text" id="chatInput" placeholder="Type chat message">
                <button onclick="sendChat()">Send Chat</button>
            </div>
            
            <h2>Status Updates</h2>
            <div id="statusBox" class="chat-box"></div>
            <button onclick="connectStatus()">Connect to Status</button>
            <button onclick="disconnectStatus()">Disconnect</button>
        </div>

        <script>
            let echoWs = null;
            let chatWs = null;
            let statusWs = null;

            // Echo WebSocket
            function connectEcho() {
                if (echoWs) return;
                echoWs = new WebSocket('ws://localhost:8000/echo');
                echoWs.onmessage = function(event) {
                    document.getElementById('echoResult').innerHTML = 
                        '<div class="message">' + event.data + '</div>';
                };
                echoWs.onclose = function() {
                    echoWs = null;
                };
            }

            function sendEcho() {
                connectEcho();
                const input = document.getElementById('echoInput');
                if (echoWs && echoWs.readyState === WebSocket.OPEN) {
                    echoWs.send(input.value);
                    input.value = '';
                }
            }

            // Chat WebSocket
            function connectChat() {
                if (chatWs) return;
                chatWs = new WebSocket('ws://localhost:8000/chat');
                chatWs.onmessage = function(event) {
                    const message = JSON.parse(event.data);
                    const chatBox = document.getElementById('chatBox');
                    const div = document.createElement('div');
                    div.className = 'message';
                    div.innerHTML = `<strong>${message.type}:</strong> ${message.message}`;
                    chatBox.appendChild(div);
                    chatBox.scrollTop = chatBox.scrollHeight;
                };
                chatWs.onclose = function() {
                    chatWs = null;
                };
            }

            function sendChat() {
                connectChat();
                const input = document.getElementById('chatInput');
                if (chatWs && chatWs.readyState === WebSocket.OPEN) {
                    chatWs.send(JSON.stringify({
                        type: 'chat',
                        message: input.value
                    }));
                    input.value = '';
                }
            }

            // Status WebSocket
            function connectStatus() {
                if (statusWs) return;
                statusWs = new WebSocket('ws://localhost:8000/status');
                statusWs.onmessage = function(event) {
                    const message = JSON.parse(event.data);
                    const statusBox = document.getElementById('statusBox');
                    const div = document.createElement('div');
                    div.className = 'message';
                    div.innerHTML = `Counter: ${message.counter} - ${message.message}`;
                    statusBox.appendChild(div);
                    statusBox.scrollTop = statusBox.scrollHeight;
                };
                statusWs.onclose = function() {
                    statusWs = null;
                };
            }

            function disconnectStatus() {
                if (statusWs) {
                    statusWs.close();
                    statusWs = null;
                }
            }

            // Auto-connect to chat
            connectChat();
        </script>
    </body>
    </html>
    """


if __name__ == "__main__":
    print("Starting Velithon WebSocket Demo Server...")
    print("Open http://localhost:8000 to see the demo")
    app.run(host="127.0.0.1", port=8000)
