# Real-time Updates Example

This example demonstrates how to implement real-time updates using Server-Sent Events (SSE) and WebSockets in Velithon applications.

## Server-Sent Events (SSE)

### Basic SSE Implementation

```python
from velithon import Velithon, Request
from velithon.responses import EventSourceResponse, HTMLResponse
import asyncio
import json
import time
from datetime import datetime

app = Velithon()

# Store active connections
active_connections = set()

@app.get("/")
async def index():
    """Serve the main page with SSE client."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Real-time Updates</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .update { margin: 10px 0; padding: 10px; background: #f0f0f0; border-radius: 5px; }
            .timestamp { color: #666; font-size: 0.9em; }
            #status { margin: 20px 0; padding: 10px; border-radius: 5px; }
            .connected { background: #d4edda; color: #155724; }
            .disconnected { background: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <h1>Real-time Updates Demo</h1>
        
        <div id="status" class="disconnected">Disconnected</div>
        
        <div>
            <button onclick="sendUpdate()">Send Update</button>
            <button onclick="sendNotification()">Send Notification</button>
        </div>
        
        <div id="updates"></div>

        <script>
            const updates = document.getElementById('updates');
            const status = document.getElementById('status');
            
            // Connect to SSE endpoint
            const eventSource = new EventSource('/events');
            
            eventSource.onopen = function() {
                status.textContent = 'Connected';
                status.className = 'connected';
            };
            
            eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);
                addUpdate(data.message, data.timestamp);
            };
            
            eventSource.addEventListener('notification', function(event) {
                const data = JSON.parse(event.data);
                addUpdate(`🔔 ${data.message}`, data.timestamp, 'notification');
            });
            
            eventSource.addEventListener('system', function(event) {
                const data = JSON.parse(event.data);
                addUpdate(`⚙️ ${data.message}`, data.timestamp, 'system');
            });
            
            eventSource.onerror = function() {
                status.textContent = 'Disconnected';
                status.className = 'disconnected';
            };
            
            function addUpdate(message, timestamp, type = 'default') {
                const div = document.createElement('div');
                div.className = `update ${type}`;
                div.innerHTML = `
                    <div>${message}</div>
                    <div class="timestamp">${new Date(timestamp).toLocaleString()}</div>
                `;
                updates.insertBefore(div, updates.firstChild);
                
                // Keep only last 20 updates
                while (updates.children.length > 20) {
                    updates.removeChild(updates.lastChild);
                }
            }
            
            async function sendUpdate() {
                try {
                    await fetch('/send-update', { method: 'POST' });
                } catch (error) {
                    console.error('Failed to send update:', error);
                }
            }
            
            async function sendNotification() {
                try {
                    await fetch('/send-notification', { method: 'POST' });
                } catch (error) {
                    console.error('Failed to send notification:', error);
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html_content)

@app.get("/events")
async def stream_events(request: Request):
    """SSE endpoint for real-time updates."""
    async def event_stream():
        connection_id = id(request)
        active_connections.add(connection_id)
        
        try:
            # Send initial connection message
            yield {
                "data": json.dumps({
                    "message": "Connected to real-time updates",
                    "timestamp": datetime.now().isoformat()
                })
            }
            
            # Keep connection alive and send periodic updates
            while True:
                # Send heartbeat every 30 seconds
                yield {
                    "event": "heartbeat",
                    "data": json.dumps({
                        "timestamp": datetime.now().isoformat()
                    })
                }
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            active_connections.discard(connection_id)
            raise
        finally:
            active_connections.discard(connection_id)
    
    return EventSourceResponse(event_stream())

@app.post("/send-update")
async def send_update(request: Request):
    """Trigger a custom update to all connected clients."""
    # In a real application, this would be called by your business logic
    # For demo purposes, we'll just send a test message
    message = {
        "message": f"Custom update #{int(time.time())}",
        "timestamp": datetime.now().isoformat()
    }
    
    # Here you would broadcast to all connections
    # This is a simplified example
    return {"status": "Update sent"}

@app.post("/send-notification")
async def send_notification(request: Request):
    """Send a notification to all connected clients."""
    message = {
        "message": f"Important notification at {datetime.now().strftime('%H:%M:%S')}",
        "timestamp": datetime.now().isoformat()
    }
    
    # Broadcast notification
    return {"status": "Notification sent"}

if __name__ == "__main__":
    import granian
    server = granian.Granian(
        target="__main__:app",
        address="0.0.0.0",
        port=8000,
        interface="rsgi",
        reload=True,
    )
    server.serve()
```

### Advanced SSE with Channels

```python
from velithon import Velithon, Request
from velithon.responses import EventSourceResponse, JSONResponse
import asyncio
import json
from datetime import datetime
from collections import defaultdict
import uuid

app = Velithon()

# Channel management
channels = defaultdict(set)  # channel_name -> set of connection_ids
connections = {}  # connection_id -> connection_info

class SSEManager:
    def __init__(self):
        self.channels = defaultdict(set)
        self.connections = {}
    
    def add_connection(self, connection_id, channel):
        self.connections[connection_id] = {
            "channel": channel,
            "connected_at": datetime.now()
        }
        self.channels[channel].add(connection_id)
    
    def remove_connection(self, connection_id):
        if connection_id in self.connections:
            channel = self.connections[connection_id]["channel"]
            self.channels[channel].discard(connection_id)
            del self.connections[connection_id]
    
    def get_channel_connections(self, channel):
        return self.channels[channel]
    
    def get_active_channels(self):
        return {
            channel: len(connections) 
            for channel, connections in self.channels.items()
            if connections
        }

sse_manager = SSEManager()

@app.get("/events/{channel}")
async def stream_channel_events(request: Request):
    """SSE endpoint for specific channel."""
    channel = request.path_params["channel"]
    connection_id = str(uuid.uuid4())
    
    async def event_stream():
        sse_manager.add_connection(connection_id, channel)
        
        try:
            # Send connection confirmation
            yield {
                "event": "connected",
                "data": json.dumps({
                    "channel": channel,
                    "connection_id": connection_id,
                    "timestamp": datetime.now().isoformat()
                })
            }
            
            # Keep connection alive
            while True:
                await asyncio.sleep(30)
                yield {
                    "event": "heartbeat",
                    "data": json.dumps({
                        "timestamp": datetime.now().isoformat()
                    })
                }
                
        except asyncio.CancelledError:
            sse_manager.remove_connection(connection_id)
            raise
        finally:
            sse_manager.remove_connection(connection_id)
    
    return EventSourceResponse(event_stream())

@app.post("/broadcast/{channel}")
async def broadcast_to_channel(request: Request):
    """Broadcast message to specific channel."""
    channel = request.path_params["channel"]
    data = await request.json()
    
    message = {
        "channel": channel,
        "message": data.get("message", ""),
        "timestamp": datetime.now().isoformat(),
        "sender": data.get("sender", "system")
    }
    
    # Get connections for channel
    connections = sse_manager.get_channel_connections(channel)
    
    return JSONResponse({
        "status": "Message broadcasted",
        "channel": channel,
        "connections": len(connections),
        "message": message
    })

@app.get("/channels/stats")
async def get_channel_stats():
    """Get statistics about active channels."""
    return JSONResponse({
        "active_channels": sse_manager.get_active_channels(),
        "total_connections": len(sse_manager.connections)
    })
```

## WebSocket Real-time Updates

```python
from velithon import Velithon, WebSocket
from velithon.responses import HTMLResponse
import json
from datetime import datetime
import asyncio

app = Velithon()

# WebSocket connection manager
class WebSocketManager:
    def __init__(self):
        self.connections = set()
        self.rooms = {}  # room_name -> set of websockets
    
    async def connect(self, websocket, room=None):
        """Connect a WebSocket."""
        await websocket.accept()
        self.connections.add(websocket)
        
        if room:
            if room not in self.rooms:
                self.rooms[room] = set()
            self.rooms[room].add(websocket)
    
    def disconnect(self, websocket, room=None):
        """Disconnect a WebSocket."""
        self.connections.discard(websocket)
        
        if room and room in self.rooms:
            self.rooms[room].discard(websocket)
            if not self.rooms[room]:
                del self.rooms[room]
    
    async def broadcast(self, message, room=None):
        """Broadcast message to all connections or specific room."""
        targets = self.rooms.get(room, set()) if room else self.connections
        
        disconnected = set()
        for websocket in targets:
            try:
                await websocket.send_text(json.dumps(message))
            except:
                disconnected.add(websocket)
        
        # Clean up disconnected WebSockets
        for websocket in disconnected:
            self.disconnect(websocket, room)

manager = WebSocketManager()

@app.get("/websocket-demo")
async def websocket_demo():
    """WebSocket demo page."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket Real-time Updates</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .message { margin: 10px 0; padding: 10px; background: #f0f0f0; border-radius: 5px; }
            .own-message { background: #007bff; color: white; }
            .system-message { background: #28a745; color: white; }
            #messages { height: 300px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; }
            #messageForm { margin: 20px 0; }
            #messageInput { width: 300px; padding: 10px; }
            button { padding: 10px 20px; margin: 5px; }
        </style>
    </head>
    <body>
        <h1>WebSocket Real-time Chat</h1>
        
        <div>
            <button onclick="connectWebSocket()">Connect</button>
            <button onclick="disconnectWebSocket()">Disconnect</button>
            <span id="status">Disconnected</span>
        </div>
        
        <div id="messages"></div>
        
        <form id="messageForm" onsubmit="sendMessage(event)">
            <input type="text" id="messageInput" placeholder="Type a message..." disabled>
            <button type="submit" disabled id="sendButton">Send</button>
        </form>

        <script>
            let ws = null;
            const messages = document.getElementById('messages');
            const status = document.getElementById('status');
            const messageInput = document.getElementById('messageInput');
            const sendButton = document.getElementById('sendButton');
            
            function connectWebSocket() {
                ws = new WebSocket('ws://localhost:8000/ws/general');
                
                ws.onopen = function() {
                    status.textContent = 'Connected';
                    status.style.color = 'green';
                    messageInput.disabled = false;
                    sendButton.disabled = false;
                };
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    addMessage(data);
                };
                
                ws.onclose = function() {
                    status.textContent = 'Disconnected';
                    status.style.color = 'red';
                    messageInput.disabled = true;
                    sendButton.disabled = true;
                };
                
                ws.onerror = function(error) {
                    console.error('WebSocket error:', error);
                };
            }
            
            function disconnectWebSocket() {
                if (ws) {
                    ws.close();
                    ws = null;
                }
            }
            
            function sendMessage(event) {
                event.preventDefault();
                const message = messageInput.value.trim();
                
                if (message && ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        type: 'message',
                        content: message,
                        sender: 'User'
                    }));
                    messageInput.value = '';
                }
            }
            
            function addMessage(data) {
                const div = document.createElement('div');
                div.className = `message ${data.type === 'system' ? 'system-message' : ''}`;
                div.innerHTML = `
                    <strong>${data.sender}:</strong> ${data.content}
                    <small style="float: right;">${new Date(data.timestamp).toLocaleTimeString()}</small>
                `;
                messages.appendChild(div);
                messages.scrollTop = messages.scrollHeight;
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html_content)

@app.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication."""
    room = websocket.path_params["room"]
    
    await manager.connect(websocket, room)
    
    # Send welcome message
    await manager.broadcast({
        "type": "system",
        "content": f"User joined room '{room}'",
        "sender": "System",
        "timestamp": datetime.now().isoformat()
    }, room)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Add timestamp and broadcast to room
            message_data["timestamp"] = datetime.now().isoformat()
            message_data["room"] = room
            
            await manager.broadcast(message_data, room)
            
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket, room)
        
        # Send leave message
        await manager.broadcast({
            "type": "system",
            "content": f"User left room '{room}'",
            "sender": "System",
            "timestamp": datetime.now().isoformat()
        }, room)

@app.post("/broadcast-ws/{room}")
async def broadcast_websocket_message(request: Request):
    """HTTP endpoint to broadcast to WebSocket room."""
    room = request.path_params["room"]
    data = await request.json()
    
    message = {
        "type": "broadcast",
        "content": data.get("message", ""),
        "sender": data.get("sender", "System"),
        "timestamp": datetime.now().isoformat()
    }
    
    await manager.broadcast(message, room)
    
    return JSONResponse({
        "status": "Message broadcasted",
        "room": room,
        "connections": len(manager.rooms.get(room, set()))
    })

if __name__ == "__main__":
    import granian
    server = granian.Granian(
        target="__main__:app",
        address="0.0.0.0",
        port=8000,
        interface="rsgi",
        reload=True,
    )
    server.serve()
```

## Real-time Dashboard Example

```python
from velithon import Velithon, Request
from velithon.responses import EventSourceResponse, HTMLResponse, JSONResponse
import asyncio
import json
import random
from datetime import datetime
import psutil

app = Velithon()

@app.get("/dashboard")
async def dashboard():
    """Real-time system monitoring dashboard."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Real-time Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .metric { 
                display: inline-block; 
                margin: 10px; 
                padding: 20px; 
                border: 1px solid #ccc; 
                border-radius: 10px; 
                min-width: 200px;
                text-align: center;
            }
            .metric-value { font-size: 2em; font-weight: bold; }
            .metric-label { color: #666; }
            #chart-container { margin: 20px 0; }
        </style>
    </head>
    <body>
        <h1>System Monitoring Dashboard</h1>
        
        <div id="metrics">
            <div class="metric">
                <div class="metric-value" id="cpu-usage">-</div>
                <div class="metric-label">CPU Usage (%)</div>
            </div>
            
            <div class="metric">
                <div class="metric-value" id="memory-usage">-</div>
                <div class="metric-label">Memory Usage (%)</div>
            </div>
            
            <div class="metric">
                <div class="metric-value" id="active-connections">-</div>
                <div class="metric-label">Active Connections</div>
            </div>
        </div>
        
        <div id="chart-container">
            <canvas id="metricsChart" width="800" height="400"></canvas>
        </div>

        <script>
            // Chart setup
            const ctx = document.getElementById('metricsChart').getContext('2d');
            const chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'CPU Usage',
                        data: [],
                        borderColor: 'rgb(255, 99, 132)',
                        tension: 0.1
                    }, {
                        label: 'Memory Usage',
                        data: [],
                        borderColor: 'rgb(54, 162, 235)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    }
                }
            });
            
            // Connect to SSE
            const eventSource = new EventSource('/dashboard/events');
            
            eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateMetrics(data);
                updateChart(data);
            };
            
            function updateMetrics(data) {
                document.getElementById('cpu-usage').textContent = data.cpu_usage.toFixed(1);
                document.getElementById('memory-usage').textContent = data.memory_usage.toFixed(1);
                document.getElementById('active-connections').textContent = data.active_connections;
            }
            
            function updateChart(data) {
                const now = new Date().toLocaleTimeString();
                
                // Add new data point
                chart.data.labels.push(now);
                chart.data.datasets[0].data.push(data.cpu_usage);
                chart.data.datasets[1].data.push(data.memory_usage);
                
                // Keep only last 20 points
                if (chart.data.labels.length > 20) {
                    chart.data.labels.shift();
                    chart.data.datasets[0].data.shift();
                    chart.data.datasets[1].data.shift();
                }
                
                chart.update('none');
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html_content)

@app.get("/dashboard/events")
async def dashboard_events(request: Request):
    """SSE endpoint for dashboard metrics."""
    async def metric_stream():
        while True:
            # Collect system metrics
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            metrics = {
                "cpu_usage": cpu_usage,
                "memory_usage": memory.percent,
                "active_connections": random.randint(10, 100),  # Mock data
                "timestamp": datetime.now().isoformat()
            }
            
            yield {
                "data": json.dumps(metrics)
            }
            
            await asyncio.sleep(2)  # Update every 2 seconds
    
    return EventSourceResponse(metric_stream())

if __name__ == "__main__":
    import granian
    server = granian.Granian(
        target="__main__:app",
        address="0.0.0.0",
        port=8000,
        interface="rsgi",
        reload=True,
    )
    server.serve()
```

## Testing Real-time Features

```python
import pytest
import httpx
import asyncio
import json
from velithon.testing import TestClient

@pytest.mark.asyncio
async def test_sse_connection():
    """Test SSE connection and data streaming."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        async with client.stream("GET", "/events") as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/plain; charset=utf-8"
            
            # Read first event
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    data = json.loads(line[5:])  # Remove "data:" prefix
                    assert "timestamp" in data
                    break

@pytest.mark.asyncio
async def test_websocket_communication():
    """Test WebSocket communication."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws/test") as websocket:
            # Send test message
            test_message = {
                "type": "message",
                "content": "Hello WebSocket!",
                "sender": "Test"
            }
            websocket.send_text(json.dumps(test_message))
            
            # Receive response
            data = websocket.receive_text()
            response = json.loads(data)
            
            assert response["content"] == "Hello WebSocket!"
            assert response["sender"] == "Test"
            assert "timestamp" in response

@pytest.mark.asyncio
async def test_broadcast_endpoint():
    """Test HTTP broadcast to WebSocket rooms."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/broadcast-ws/testroom",
            json={
                "message": "Test broadcast",
                "sender": "System"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "Message broadcasted"
        assert data["room"] == "testroom"
```

## Key Features

- **Server-Sent Events**: One-way real-time communication from server to client
- **WebSocket Support**: Bi-directional real-time communication
- **Channel/Room Management**: Organize connections into groups
- **Connection Management**: Handle connection lifecycle and cleanup
- **Broadcasting**: Send messages to all or specific groups of clients
- **Real-time Dashboard**: Live metrics and monitoring
- **Error Handling**: Robust error handling for network issues

## Best Practices

1. **Connection Management**: Always clean up connections properly
2. **Error Handling**: Handle network errors and disconnections gracefully
3. **Rate Limiting**: Prevent abuse of real-time endpoints
4. **Authentication**: Secure real-time connections
5. **Scalability**: Consider using Redis or message queues for multi-instance deployments
6. **Resource Management**: Monitor memory usage with many concurrent connections
7. **Heartbeat/Ping**: Keep connections alive and detect disconnections
