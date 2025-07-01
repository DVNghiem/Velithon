# Response Types

## Built-in Response Types

```python
from velithon.responses import (
    JSONResponse,
    PlainTextResponse,
    HTMLResponse,
    RedirectResponse,
    FileResponse,
    StreamingResponse,
    SSEResponse
)

@app.get("/json")
async def json_response():
    return JSONResponse({"message": "Hello JSON"})

@app.get("/text")
async def text_response():
    return PlainTextResponse("Hello Text")

@app.get("/html")
async def html_response():
    return HTMLResponse("<h1>Hello HTML</h1>")

@app.get("/redirect")
async def redirect_response():
    return RedirectResponse("/json")

@app.get("/file")
async def file_response():
    return FileResponse("path/to/file.pdf")

@app.get("/stream")
async def streaming_response():
    def generate():
        for i in range(100):
            yield f"data chunk {i}\n"
    
    return StreamingResponse(generate(), media_type="text/plain")

@app.get("/events")
async def sse_response():
    async def generate():
        for i in range(10):
            yield {"data": f"Event {i}", "id": str(i), "event": "message"}
            await asyncio.sleep(1)  # Wait 1 second between events
    
    return SSEResponse(generate())
```

## Custom Response Status and Headers

```python
@app.get("/custom")
async def custom_response():
    return JSONResponse(
        content={"message": "Created"},
        status_code=201,
        headers={"X-Custom-Header": "value"}
    )
```

## Server-Sent Events (SSE)

Server-Sent Events provide a way to stream real-time data from server to client using a standardized format. SSE is perfect for applications that need to push updates like live notifications, real-time charts, or chat messages.

### Basic SSE Usage

```python
import asyncio
from velithon.responses import SSEResponse

@app.get("/live-updates")
async def live_updates():
    async def generate():
        counter = 0
        while counter < 10:
            yield f"Update #{counter}"
            counter += 1
            await asyncio.sleep(1)
    
    return SSEResponse(generate())
```

### Structured SSE Events

You can send structured events with additional SSE fields:

```python
@app.get("/structured-events")
async def structured_events():
    async def generate():
        yield {
            "data": "Welcome to the stream",
            "event": "welcome",
            "id": "1"
        }
        
        for i in range(5):
            yield {
                "data": {"count": i, "timestamp": time.time()},
                "event": "counter",
                "id": str(i + 2),
                "retry": 5000  # Client should retry after 5 seconds if disconnected
            }
            await asyncio.sleep(2)
    
    return SSEResponse(generate())
```

### SSE with Ping/Keep-Alive

To keep connections alive, you can send periodic ping events:

```python
@app.get("/events-with-ping")
async def events_with_ping():
    async def generate():
        for i in range(20):
            yield {"data": f"Data {i}", "event": "data"}
            await asyncio.sleep(5)  # Long delay between events
    
    # Send ping every 30 seconds to keep connection alive
    return SSEResponse(generate(), ping_interval=30)
```

### Real-time Chat Example

```python
@app.get("/chat-stream")
async def chat_stream():
    # In a real app, you'd connect to a message queue or database
    async def generate():
        messages = [
            {"user": "Alice", "message": "Hello everyone!"},
            {"user": "Bob", "message": "Hey Alice!"},
            {"user": "Charlie", "message": "Good morning!"},
        ]
        
        for msg in messages:
            yield {
                "data": msg,
                "event": "message",
                "id": str(hash(f"{msg['user']}{msg['message']}"))
            }
            await asyncio.sleep(1)
    
    return SSEResponse(generate())
```

### Client-Side JavaScript

To consume SSE on the client side:

```javascript
const eventSource = new EventSource('/events');

eventSource.onmessage = function(event) {
    console.log('Received:', event.data);
};

eventSource.addEventListener('message', function(event) {
    const data = JSON.parse(event.data);
    console.log('Message:', data);
});

eventSource.onerror = function(event) {
    console.error('SSE error:', event);
};

// Close connection when done
// eventSource.close();
```
