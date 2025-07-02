# Server-Sent Events (SSE)

Server-Sent Events (SSE) provide a standardized way to stream real-time data from server to client over HTTP. Velithon's high-performance SSE implementation is built with Rust for maximum efficiency and supports all SSE standard features.

## Overview

SSE is perfect for:
- Real-time notifications and alerts
- Live data feeds (stock prices, sensor data)
- Chat applications and messaging
- Progress updates for long-running operations
- Live dashboards and monitoring

## Basic SSE Usage

### Simple Event Stream

```python
import asyncio
from velithon import Velithon
from velithon.responses import SSEResponse

app = Velithon()

@app.get("/live-counter")
async def live_counter():
    async def generate():
        counter = 0
        while counter < 10:
            yield f"Count: {counter}"
            counter += 1
            await asyncio.sleep(1)
    
    return SSEResponse(generate())
```

### JSON Data Streaming

```python
import time
import random
from datetime import datetime

@app.get("/live-data")
async def live_data():
    async def generate():
        for _ in range(20):
            data = {
                "temperature": round(20 + random.uniform(-2, 2), 1),
                "humidity": round(50 + random.uniform(-5, 5), 1),
                "timestamp": datetime.now().isoformat()
            }
            yield data
            await asyncio.sleep(2)
    
    return SSEResponse(generate())
```

## Structured SSE Events

SSE supports additional metadata fields beyond just data:

```python
@app.get("/structured-events")
async def structured_events():
    async def generate():
        # Welcome event with custom event type
        yield {
            "data": "Welcome to the stream",
            "event": "welcome",
            "id": "welcome-1"
        }
        
        await asyncio.sleep(1)
        
        # Status updates with retry information
        for i in range(5):
            yield {
                "data": {
                    "status": f"Processing step {i+1}",
                    "progress": (i+1) * 20
                },
                "event": "status",
                "id": f"status-{i+1}",
                "retry": 3000  # Client should retry after 3 seconds
            }
            await asyncio.sleep(2)
        
        # Final completion event
        yield {
            "data": {"status": "Complete", "progress": 100},
            "event": "complete",
            "id": "final"
        }
    
    return SSEResponse(generate())
```

### SSE Event Fields

- **data**: The actual content to send (required)
- **event**: Custom event type for client-side filtering
- **id**: Unique identifier for event replay
- **retry**: Suggested retry time in milliseconds

## Keep-Alive with Ping

For long-running streams, use ping intervals to keep connections alive:

```python
@app.get("/long-stream")
async def long_stream():
    async def generate():
        for i in range(20):
            yield {
                "data": f"Update {i}",
                "event": "data",
                "id": str(i)
            }
            await asyncio.sleep(10)  # Long delay between events
    
    # Send ping every 30 seconds to prevent timeouts
    return SSEResponse(generate(), ping_interval=30)
```

## Real-Time Chat Example

```python
from typing import List, Dict

# Global message store (use Redis in production)
chat_messages: List[Dict] = []
user_count = 0

@app.get("/chat-stream")
async def chat_stream():
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
        
        # Send recent message history
        for i, msg in enumerate(chat_messages[-10:]):
            yield {
                "data": msg,
                "event": "message",
                "id": f"msg-{i}"
            }
        
        # Listen for new messages
        last_message_count = len(chat_messages)
        try:
            while True:
                await asyncio.sleep(1)
                
                # Check for new messages
                if len(chat_messages) > last_message_count:
                    for msg in chat_messages[last_message_count:]:
                        yield {
                            "data": msg,
                            "event": "message",
                            "id": f"msg-{len(chat_messages)}"
                        }
                    last_message_count = len(chat_messages)
        except Exception:
            # Send leave notification on disconnect
            yield {
                "data": user_id,
                "event": "leave",
                "id": f"leave-{user_id}"
            }
    
    return SSEResponse(generate(), ping_interval=30)

@app.post("/send-message")
async def send_message(data: dict):
    """Endpoint to add new chat messages"""
    message = {
        "user": data.get("user", "Anonymous"),
        "message": data.get("message", ""),
        "timestamp": datetime.now().isoformat()
    }
    chat_messages.append(message)
    return {"status": "sent"}
```

## Client-Side JavaScript

### Basic Event Listening

```javascript
const eventSource = new EventSource('/live-counter');

eventSource.onmessage = function(event) {
    console.log('Received:', event.data);
    document.getElementById('output').innerHTML += event.data + '<br>';
};

eventSource.onerror = function(event) {
    console.error('SSE error:', event);
};

// Close connection when done
// eventSource.close();
```

### Handling Custom Events

```javascript
const eventSource = new EventSource('/structured-events');

// Handle default messages
eventSource.onmessage = function(event) {
    console.log('Default message:', event.data);
};

// Handle custom event types
eventSource.addEventListener('welcome', function(event) {
    console.log('Welcome message:', event.data);
});

eventSource.addEventListener('status', function(event) {
    const data = JSON.parse(event.data);
    console.log(`Progress: ${data.progress}%`);
});

eventSource.addEventListener('complete', function(event) {
    console.log('Process completed!');
    eventSource.close();
});
```

### Chat Client Example

```javascript
const chatSource = new EventSource('/chat-stream');

chatSource.addEventListener('join', function(event) {
    addMessage(`${event.data} joined the chat`, 'system');
});

chatSource.addEventListener('leave', function(event) {
    addMessage(`${event.data} left the chat`, 'system');
});

chatSource.addEventListener('message', function(event) {
    const msg = JSON.parse(event.data);
    addMessage(`${msg.user}: ${msg.message}`, 'user');
});

function addMessage(text, type) {
    const div = document.createElement('div');
    div.className = type;
    div.textContent = text;
    document.getElementById('messages').appendChild(div);
}
```

## Advanced Features

### Error Handling

```python
@app.get("/resilient-stream")
async def resilient_stream():
    async def generate():
        try:
            for i in range(100):
                # Simulate potential data source errors
                if random.random() < 0.05:  # 5% error rate
                    yield {
                        "data": {"error": "Temporary data unavailable"},
                        "event": "error",
                        "id": f"error-{i}"
                    }
                else:
                    yield {
                        "data": {"value": i, "status": "ok"},
                        "event": "data",
                        "id": str(i)
                    }
                await asyncio.sleep(1)
        except Exception as e:
            # Send error event before closing
            yield {
                "data": {"error": str(e)},
                "event": "fatal_error",
                "id": "fatal"
            }
    
    return SSEResponse(generate(), ping_interval=10)
```

### Conditional Streaming

```python
@app.get("/user-specific-stream/{user_id}")
async def user_stream(user_id: int):
    async def generate():
        # Personalize stream based on user
        user_preferences = get_user_preferences(user_id)
        
        while True:
            # Get data relevant to this user
            updates = get_user_updates(user_id, user_preferences)
            
            for update in updates:
                yield {
                    "data": update,
                    "event": "update",
                    "id": f"user-{user_id}-{update['id']}"
                }
            
            await asyncio.sleep(5)
    
    return SSEResponse(generate(), ping_interval=30)
```

## Performance Best Practices

### Memory Management

```python
@app.get("/memory-efficient-stream")
async def memory_efficient_stream():
    async def generate():
        # Process data in chunks to avoid memory buildup
        async for chunk in get_large_dataset_chunks():
            for item in chunk:
                yield {
                    "data": item,
                    "event": "data",
                    "id": item["id"]
                }
            # Allow other tasks to run
            await asyncio.sleep(0)
    
    return SSEResponse(generate())
```

### Connection Management

```python
from velithon.background import BackgroundTask

@app.get("/managed-stream")
async def managed_stream():
    connection_id = str(uuid.uuid4())
    
    async def generate():
        try:
            # Register connection
            active_connections.add(connection_id)
            
            yield {
                "data": {"connection_id": connection_id},
                "event": "connected",
                "id": "connect"
            }
            
            # Main streaming loop
            while connection_id in active_connections:
                data = await get_next_data()
                yield {
                    "data": data,
                    "event": "data",
                    "id": data["id"]
                }
                await asyncio.sleep(1)
                
        finally:
            # Cleanup on disconnect
            active_connections.discard(connection_id)
    
    async def cleanup():
        """Background cleanup task"""
        active_connections.discard(connection_id)
    
    return SSEResponse(generate(), background=BackgroundTask(cleanup))
```

## Testing SSE Endpoints

### Unit Testing

```python
import pytest
from velithon.testing import TestClient

@pytest.mark.asyncio
async def test_sse_endpoint():
    client = TestClient(app)
    
    # Test SSE endpoint
    with client.stream("GET", "/live-counter") as response:
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"
        
        # Read first few events
        events = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                events.append(line[6:])  # Remove "data: " prefix
                if len(events) >= 3:
                    break
        
        assert len(events) >= 3
        assert "Count: 0" in events[0]
```

### Integration Testing

```python
import asyncio
import aiohttp

async def test_sse_integration():
    async with aiohttp.ClientSession() as session:
        async with session.get('http://localhost:8000/live-data') as response:
            assert response.status == 200
            
            event_count = 0
            async for line in response.content:
                line = line.decode().strip()
                if line.startswith('data: '):
                    event_count += 1
                    if event_count >= 5:
                        break
            
            assert event_count >= 5
```

## Security Considerations

### Rate Limiting

```python
from collections import defaultdict
import time

# Simple rate limiting (use Redis in production)
connection_counts = defaultdict(int)
last_cleanup = time.time()

@app.get("/rate-limited-stream")
async def rate_limited_stream(request: Request):
    client_ip = request.client.host
    
    # Cleanup old entries periodically
    current_time = time.time()
    if current_time - last_cleanup > 60:
        connection_counts.clear()
        last_cleanup = current_time
    
    # Check rate limit
    if connection_counts[client_ip] >= 5:
        raise HTTPException(429, "Too many connections")
    
    async def generate():
        try:
            connection_counts[client_ip] += 1
            
            for i in range(100):
                yield f"Data: {i}"
                await asyncio.sleep(1)
                
        finally:
            connection_counts[client_ip] -= 1
    
    return SSEResponse(generate())
```

### Authentication

```python
from velithon.security import verify_token

@app.get("/authenticated-stream")
async def authenticated_stream(request: Request):
    # Verify authentication
    auth_header = request.headers.get("authorization")
    if not auth_header or not verify_token(auth_header):
        raise HTTPException(401, "Authentication required")
    
    async def generate():
        yield {"data": "Authenticated stream", "event": "auth"}
        
        # Continue with protected data...
        while True:
            protected_data = get_protected_data()
            yield {"data": protected_data, "event": "data"}
            await asyncio.sleep(1)
    
    return SSEResponse(generate())
```

## Production Deployment

### Nginx Configuration

```nginx
location /sse/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
    
    # SSE specific settings
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 86400;
}
```

### Monitoring

```python
import time
from collections import defaultdict

# Metrics collection
sse_metrics = {
    "active_connections": 0,
    "total_events_sent": 0,
    "errors": 0
}

@app.get("/sse-metrics")
async def get_sse_metrics():
    return JSONResponse(sse_metrics)

# Add metrics to your SSE endpoints
@app.get("/monitored-stream")
async def monitored_stream():
    async def generate():
        try:
            sse_metrics["active_connections"] += 1
            
            for i in range(100):
                yield f"Event {i}"
                sse_metrics["total_events_sent"] += 1
                await asyncio.sleep(1)
                
        except Exception:
            sse_metrics["errors"] += 1
            raise
        finally:
            sse_metrics["active_connections"] -= 1
    
    return SSEResponse(generate())
```

Velithon's SSE implementation provides a robust, high-performance solution for real-time web applications. The Rust-powered backend ensures excellent performance even with thousands of concurrent connections, while the Python API remains simple and intuitive.
