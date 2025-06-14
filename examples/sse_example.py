"""
Example application demonstrating Server-Sent Events (SSE) functionality.

This example shows various SSE use cases:
- Basic event streaming
- Structured events with metadata
- Real-time data simulation
- Chat-like messaging
- Keep-alive with ping intervals
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, List

from velithon import Velithon
from velithon.responses import HTMLResponse, SSEResponse

app = Velithon()

# Simulate some data sources
chat_messages: List[Dict] = []
user_count = 0


@app.get("/")
async def index():
    """Serve the main HTML page with SSE examples."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Velithon SSE Examples</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .event-box { 
                border: 1px solid #ccc; 
                padding: 10px; 
                margin: 10px 0; 
                border-radius: 5px;
                background: #f9f9f9;
            }
            .event-log { 
                height: 200px; 
                overflow-y: auto; 
                border: 1px solid #ddd; 
                padding: 10px; 
                background: white;
                font-family: monospace;
                font-size: 12px;
            }
            button { 
                padding: 10px 20px; 
                margin: 5px; 
                background: #007bff; 
                color: white; 
                border: none; 
                border-radius: 3px; 
                cursor: pointer;
            }
            button:hover { background: #0056b3; }
            .status { 
                padding: 5px 10px; 
                border-radius: 3px; 
                margin: 5px 0;
            }
            .connected { background: #d4edda; color: #155724; }
            .disconnected { background: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Velithon Server-Sent Events Examples</h1>
            
            <div class="event-box">
                <h3>1. Basic Counter Stream</h3>
                <div id="counter-status" class="status disconnected">Disconnected</div>
                <button onclick="startCounter()">Start Counter</button>
                <button onclick="stopCounter()">Stop Counter</button>
                <div id="counter-log" class="event-log"></div>
            </div>
            
            <div class="event-box">
                <h3>2. Real-time Data Stream</h3>
                <div id="data-status" class="status disconnected">Disconnected</div>
                <button onclick="startDataStream()">Start Data Stream</button>
                <button onclick="stopDataStream()">Stop Data Stream</button>
                <div id="data-log" class="event-log"></div>
            </div>
            
            <div class="event-box">
                <h3>3. Chat Messages</h3>
                <div id="chat-status" class="status disconnected">Disconnected</div>
                <button onclick="startChat()">Start Chat Stream</button>
                <button onclick="stopChat()">Stop Chat</button>
                <button onclick="sendMessage()">Send Test Message</button>
                <div id="chat-log" class="event-log"></div>
            </div>
            
            <div class="event-box">
                <h3>4. Structured Events</h3>
                <div id="structured-status" class="status disconnected">Disconnected</div>
                <button onclick="startStructured()">Start Structured Events</button>
                <button onclick="stopStructured()">Stop Structured</button>
                <div id="structured-log" class="event-log"></div>
            </div>
        </div>

        <script>
            let connections = {};
            
            function updateStatus(type, connected) {
                const statusEl = document.getElementById(type + '-status');
                statusEl.textContent = connected ? 'Connected' : 'Disconnected';
                statusEl.className = 'status ' + (connected ? 'connected' : 'disconnected');
            }
            
            function addLog(type, message) {
                const logEl = document.getElementById(type + '-log');
                const time = new Date().toLocaleTimeString();
                logEl.innerHTML += `[${time}] ${message}<br>`;
                logEl.scrollTop = logEl.scrollHeight;
            }
            
            function startCounter() {
                if (connections.counter) return;
                
                const eventSource = new EventSource('/sse/counter');
                connections.counter = eventSource;
                
                eventSource.onopen = () => {
                    updateStatus('counter', true);
                    addLog('counter', '<strong>Connected to counter stream</strong>');
                };
                
                eventSource.onmessage = (event) => {
                    addLog('counter', `Counter: ${event.data}`);
                };
                
                eventSource.onerror = () => {
                    updateStatus('counter', false);
                    addLog('counter', '<strong style="color: red;">Connection error</strong>');
                };
            }
            
            function stopCounter() {
                if (connections.counter) {
                    connections.counter.close();
                    connections.counter = null;
                    updateStatus('counter', false);
                    addLog('counter', '<strong>Disconnected</strong>');
                }
            }
            
            function startDataStream() {
                if (connections.data) return;
                
                const eventSource = new EventSource('/sse/data');
                connections.data = eventSource;
                
                eventSource.onopen = () => {
                    updateStatus('data', true);
                    addLog('data', '<strong>Connected to data stream</strong>');
                };
                
                eventSource.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    addLog('data', `Temperature: ${data.temperature}°C, Humidity: ${data.humidity}%`);
                };
                
                eventSource.onerror = () => {
                    updateStatus('data', false);
                    addLog('data', '<strong style="color: red;">Connection error</strong>');
                };
            }
            
            function stopDataStream() {
                if (connections.data) {
                    connections.data.close();
                    connections.data = null;
                    updateStatus('data', false);
                    addLog('data', '<strong>Disconnected</strong>');
                }
            }
            
            function startChat() {
                if (connections.chat) return;
                
                const eventSource = new EventSource('/sse/chat');
                connections.chat = eventSource;
                
                eventSource.onopen = () => {
                    updateStatus('chat', true);
                    addLog('chat', '<strong>Connected to chat stream</strong>');
                };
                
                eventSource.addEventListener('message', (event) => {
                    const data = JSON.parse(event.data);
                    addLog('chat', `<strong>${data.user}:</strong> ${data.message}`);
                });
                
                eventSource.addEventListener('join', (event) => {
                    addLog('chat', `<em style="color: green;">${event.data} joined the chat</em>`);
                });
                
                eventSource.addEventListener('leave', (event) => {
                    addLog('chat', `<em style="color: red;">${event.data} left the chat</em>`);
                });
                
                eventSource.onerror = () => {
                    updateStatus('chat', false);
                    addLog('chat', '<strong style="color: red;">Connection error</strong>');
                };
            }
            
            function stopChat() {
                if (connections.chat) {
                    connections.chat.close();
                    connections.chat = null;
                    updateStatus('chat', false);
                    addLog('chat', '<strong>Disconnected</strong>');
                }
            }
            
            function sendMessage() {
                fetch('/api/send-message', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        user: 'You',
                        message: 'Hello from the web interface!'
                    })
                });
            }
            
            function startStructured() {
                if (connections.structured) return;
                
                const eventSource = new EventSource('/sse/structured');
                connections.structured = eventSource;
                
                eventSource.onopen = () => {
                    updateStatus('structured', true);
                    addLog('structured', '<strong>Connected to structured events</strong>');
                };
                
                eventSource.addEventListener('welcome', (event) => {
                    addLog('structured', `<strong>Welcome:</strong> ${event.data}`);
                });
                
                eventSource.addEventListener('status', (event) => {
                    const data = JSON.parse(event.data);
                    addLog('structured', `<strong>Status:</strong> ${data.status} (ID: ${event.lastEventId})`);
                });
                
                eventSource.addEventListener('data', (event) => {
                    const data = JSON.parse(event.data);
                    addLog('structured', `<strong>Data:</strong> ${JSON.stringify(data)}`);
                });
                
                eventSource.onerror = () => {
                    updateStatus('structured', false);
                    addLog('structured', '<strong style="color: red;">Connection error</strong>');
                };
            }
            
            function stopStructured() {
                if (connections.structured) {
                    connections.structured.close();
                    connections.structured = null;
                    updateStatus('structured', false);
                    addLog('structured', '<strong>Disconnected</strong>');
                }
            }
            
            // Clean up connections when page is unloaded
            window.addEventListener('beforeunload', () => {
                Object.values(connections).forEach(conn => {
                    if (conn) conn.close();
                });
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html_content)


@app.get("/sse/counter")
async def counter_stream():
    """Stream basic counter events."""
    async def generate():
        counter = 0
        while counter < 20:
            yield f"Count: {counter}"
            counter += 1
            await asyncio.sleep(1)
    
    return SSEResponse(generate())


@app.get("/sse/data")
async def data_stream():
    """Simulate real-time sensor data."""
    async def generate():
        import random
        base_temp = 20.0
        base_humidity = 50.0
        
        for _ in range(30):
            # Simulate sensor readings with some variation
            temperature = round(base_temp + random.uniform(-2, 2), 1)
            humidity = round(base_humidity + random.uniform(-5, 5), 1)
            
            yield {
                "temperature": temperature,
                "humidity": humidity,
                "timestamp": datetime.now().isoformat()
            }
            await asyncio.sleep(2)
    
    return SSEResponse(generate(), ping_interval=15)


@app.get("/sse/chat")
async def chat_stream():
    """Stream chat messages."""
    async def generate():
        global user_count
        user_count += 1
        user_id = f"User{user_count}"
        
        # Send join notification
        yield {
            "data": user_id,
            "event": "join",
            "id": f"join-{user_id}"
        }
        
        # Send existing messages
        for i, msg in enumerate(chat_messages[-10:]):  # Last 10 messages
            yield {
                "data": msg,
                "event": "message",
                "id": f"msg-{i}"
            }
        
        # Keep connection alive and send new messages
        last_message_count = len(chat_messages)
        try:
            while True:
                await asyncio.sleep(1)
                
                # Send new messages
                if len(chat_messages) > last_message_count:
                    for msg in chat_messages[last_message_count:]:
                        yield {
                            "data": msg,
                            "event": "message",
                            "id": f"msg-{len(chat_messages)}"
                        }
                    last_message_count = len(chat_messages)
                
        except Exception:
            # Send leave notification
            yield {
                "data": user_id,
                "event": "leave",
                "id": f"leave-{user_id}"
            }
    
    return SSEResponse(generate(), ping_interval=30)


@app.get("/sse/structured")
async def structured_events():
    """Stream structured events with different event types."""
    async def generate():
        # Welcome event
        yield {
            "data": "Welcome to the structured event stream",
            "event": "welcome",
            "id": "welcome-1"
        }
        
        await asyncio.sleep(1)
        
        # Status events
        for i in range(5):
            yield {
                "data": {"status": f"Processing step {i+1}", "progress": (i+1) * 20},
                "event": "status",
                "id": f"status-{i+1}",
                "retry": 3000
            }
            await asyncio.sleep(2)
        
        # Data events
        for i in range(3):
            yield {
                "data": {
                    "batch": i+1,
                    "items": [f"item-{j}" for j in range(1, 4)],
                    "timestamp": time.time()
                },
                "event": "data",
                "id": f"data-{i+1}"
            }
            await asyncio.sleep(3)
        
        # Final status
        yield {
            "data": {"status": "Complete", "progress": 100},
            "event": "status",
            "id": "status-final"
        }
    
    return SSEResponse(generate())


@app.post("/api/send-message")
async def send_message(request):
    """Handle API endpoint to send a chat message."""
    data = await request.json()
    message = {
        "user": data.get("user", "Anonymous"),
        "message": data.get("message", ""),
        "timestamp": datetime.now().isoformat()
    }
    chat_messages.append(message)
    
    # Keep only last 50 messages
    if len(chat_messages) > 50:
        chat_messages.pop(0)
    
    return {"status": "sent", "message": message}


if __name__ == "__main__":
    import uvicorn
    print("Starting SSE example server...")
    print("Visit http://localhost:8000 to see the examples")
    uvicorn.run(app, host="0.0.0.0", port=8000)
