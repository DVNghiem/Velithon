# Examples

This section provides comprehensive examples demonstrating Velithon's capabilities across different use cases and application patterns.

## Overview

Learn Velithon through practical examples ranging from simple APIs to complex microservices architectures.

## Quick Examples

### Hello World API

```python
from velithon import Velithon
from velithon.responses import OptimizedJSONResponse

app = Velithon()

@app.get("/")
async def hello():
    return OptimizedJSONResponse({"message": "Hello, World!"})

@app.get("/hello/{name}")
async def hello_name(name: str):
    return OptimizedJSONResponse({"message": f"Hello, {name}!"})

if __name__ == "__main__":
    app.run()
```

### Simple REST API

```python
from velithon import Velithon
from velithon.responses import OptimizedJSONResponse
from pydantic import BaseModel
from typing import List, Optional

app = Velithon()

class Item(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float
    in_stock: bool = True

# In-memory storage
items: List[Item] = []
next_id = 1

@app.get("/items", response_model=List[Item])
async def get_items():
    return OptimizedJSONResponse([item.dict() for item in items])

@app.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: int):
    for item in items:
        if item.id == item_id:
            return OptimizedJSONResponse(item.dict())
    return OptimizedJSONResponse({"error": "Item not found"}, status_code=404)

@app.post("/items", response_model=Item, status_code=201)
async def create_item(item: Item):
    global next_id
    item.id = next_id
    next_id += 1
    items.append(item)
    return OptimizedJSONResponse(item.dict())

@app.put("/items/{item_id}", response_model=Item)
async def update_item(item_id: int, updated_item: Item):
    for i, item in enumerate(items):
        if item.id == item_id:
            updated_item.id = item_id
            items[i] = updated_item
            return OptimizedJSONResponse(updated_item.dict())
    return OptimizedJSONResponse({"error": "Item not found"}, status_code=404)

@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    global items
    items = [item for item in items if item.id != item_id]
    return OptimizedJSONResponse({"message": "Item deleted"})
```

## Authentication Example

### JWT Authentication System

```python
from velithon import Velithon
from velithon.middleware import Middleware
from velithon.middleware.auth import JWTAuthenticationMiddleware
from velithon.dependencies import Depends
from velithon.responses import OptimizedJSONResponse
from velithon.exceptions import UnauthorizedException
from pydantic import BaseModel
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict

app = Velithon()

# Configuration
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Models
class User(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool = True

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# Mock database
users_db: Dict[str, Dict] = {}

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends()) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise UnauthorizedException("Invalid token")
    except jwt.PyJWTError:
        raise UnauthorizedException("Invalid token")
    
    user = users_db.get(username)
    if user is None:
        raise UnauthorizedException("User not found")
    
    return User(**user)

# Routes
@app.post("/register", response_model=User)
async def register(user: UserCreate):
    if user.username in users_db:
        return OptimizedJSONResponse(
            {"error": "Username already exists"}, 
            status_code=400
        )
    
    hashed_password = hash_password(user.password)
    user_id = len(users_db) + 1
    
    users_db[user.username] = {
        "id": user_id,
        "username": user.username,
        "email": user.email,
        "password": hashed_password,
        "is_active": True
    }
    
    return OptimizedJSONResponse({
        "id": user_id,
        "username": user.username,
        "email": user.email,
        "is_active": True
    })

@app.post("/login", response_model=Token)
async def login(user_credentials: UserLogin):
    user = users_db.get(user_credentials.username)
    if not user or not verify_password(user_credentials.password, user["password"]):
        raise UnauthorizedException("Invalid credentials")
    
    access_token = create_access_token(data={"sub": user["username"]})
    return OptimizedJSONResponse({
        "access_token": access_token,
        "token_type": "bearer"
    })

@app.get("/profile", response_model=User)
async def get_profile(current_user: User = Depends(get_current_user)):
    return OptimizedJSONResponse(current_user.dict())

@app.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    return OptimizedJSONResponse({
        "message": f"Hello {current_user.username}, this is a protected route!"
    })
```

## Database Integration Example

### PostgreSQL with AsyncPG

```python
from velithon import Velithon
from velithon.responses import OptimizedJSONResponse
from pydantic import BaseModel
import asyncpg
from typing import List, Optional
import os

app = Velithon()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/mydb")

# Models
class User(BaseModel):
    id: Optional[int] = None
    name: str
    email: str
    age: Optional[int] = None

class UserCreate(BaseModel):
    name: str
    email: str
    age: Optional[int] = None

# Database connection
async def get_db_pool():
    return await asyncpg.create_pool(DATABASE_URL)

db_pool = None

@app.on_event("startup")
async def startup():
    global db_pool
    db_pool = await get_db_pool()
    
    # Create table if not exists
    async with db_pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                age INTEGER
            )
        ''')

@app.on_event("shutdown")
async def shutdown():
    if db_pool:
        await db_pool.close()

# Routes
@app.get("/users", response_model=List[User])
async def get_users():
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM users")
        return OptimizedJSONResponse([dict(row) for row in rows])

@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: int):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        if row:
            return OptimizedJSONResponse(dict(row))
        return OptimizedJSONResponse({"error": "User not found"}, status_code=404)

@app.post("/users", response_model=User, status_code=201)
async def create_user(user: UserCreate):
    async with db_pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                "INSERT INTO users (name, email, age) VALUES ($1, $2, $3) RETURNING *",
                user.name, user.email, user.age
            )
            return OptimizedJSONResponse(dict(row))
        except asyncpg.UniqueViolationError:
            return OptimizedJSONResponse(
                {"error": "Email already exists"}, 
                status_code=400
            )

@app.put("/users/{user_id}", response_model=User)
async def update_user(user_id: int, user: UserCreate):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE users SET name = $1, email = $2, age = $3 WHERE id = $4 RETURNING *",
            user.name, user.email, user.age, user_id
        )
        if row:
            return OptimizedJSONResponse(dict(row))
        return OptimizedJSONResponse({"error": "User not found"}, status_code=404)

@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    async with db_pool.acquire() as conn:
        result = await conn.execute("DELETE FROM users WHERE id = $1", user_id)
        if result == "DELETE 1":
            return OptimizedJSONResponse({"message": "User deleted"})
        return OptimizedJSONResponse({"error": "User not found"}, status_code=404)
```

## WebSocket Chat Example

### Real-time Chat Application

```python
from velithon import Velithon
from velithon.websocket import WebSocket
from velithon.responses import HTMLResponse, OptimizedJSONResponse
from typing import Dict, Set
import json
from datetime import datetime

app = Velithon()

# Store active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.user_connections: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, room: str, username: str):
        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = set()
        self.active_connections[room].add(websocket)
        self.user_connections[websocket] = username
        
        # Notify room about new user
        await self.broadcast_to_room(room, {
            "type": "user_joined",
            "username": username,
            "timestamp": datetime.now().isoformat()
        })

    def disconnect(self, websocket: WebSocket, room: str):
        username = self.user_connections.get(websocket)
        if room in self.active_connections:
            self.active_connections[room].discard(websocket)
        if websocket in self.user_connections:
            del self.user_connections[websocket]
        return username

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_to_room(self, room: str, message: dict):
        if room in self.active_connections:
            message_str = json.dumps(message)
            for connection in self.active_connections[room].copy():
                try:
                    await connection.send_text(message_str)
                except:
                    self.active_connections[room].discard(connection)

manager = ConnectionManager()

# HTML page for chat interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Velithon Chat</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        #messages { border: 1px solid #ccc; height: 400px; overflow-y: scroll; padding: 10px; }
        .message { margin: 5px 0; }
        .system { color: #888; font-style: italic; }
        .user-message { color: #333; }
        .username { font-weight: bold; color: #0066cc; }
        input, button { padding: 8px; margin: 5px; }
        #messageInput { width: 300px; }
    </style>
</head>
<body>
    <h1>Chat Room: {room}</h1>
    <div id="messages"></div>
    <div>
        <input type="text" id="messageInput" placeholder="Type your message..." onkeypress="handleKeyPress(event)">
        <button onclick="sendMessage()">Send</button>
    </div>

    <script>
        const room = "{room}";
        const username = prompt("Enter your username:");
        const ws = new WebSocket(`ws://localhost:8000/ws/${room}/${username}`);
        
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            const messages = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message';
            
            if (data.type === 'user_joined') {
                messageDiv.innerHTML = `<span class="system">${data.username} joined the room</span>`;
            } else if (data.type === 'user_left') {
                messageDiv.innerHTML = `<span class="system">${data.username} left the room</span>`;
            } else if (data.type === 'message') {
                messageDiv.innerHTML = `<span class="username">${data.username}:</span> <span class="user-message">${data.message}</span>`;
            }
            
            messages.appendChild(messageDiv);
            messages.scrollTop = messages.scrollHeight;
        };
        
        function sendMessage() {
            const input = document.getElementById('messageInput');
            if (input.value.trim()) {
                ws.send(JSON.stringify({
                    type: 'message',
                    message: input.value
                }));
                input.value = '';
            }
        }
        
        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }
    </script>
</body>
</html>
"""

@app.get("/")
async def homepage():
    return HTMLResponse("<h1>Velithon Chat</h1><p><a href='/chat/general'>Join General Chat</a></p>")

@app.get("/chat/{room}")
async def chat_room(room: str):
    return HTMLResponse(HTML_TEMPLATE.format(room=room))

@app.websocket("/ws/{room}/{username}")
async def websocket_endpoint(websocket: WebSocket, room: str, username: str):
    await manager.connect(websocket, room, username)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data["type"] == "message":
                await manager.broadcast_to_room(room, {
                    "type": "message",
                    "username": username,
                    "message": message_data["message"],
                    "timestamp": datetime.now().isoformat()
                })
    except Exception as e:
        username = manager.disconnect(websocket, room)
        if username:
            await manager.broadcast_to_room(room, {
                "type": "user_left",
                "username": username,
                "timestamp": datetime.now().isoformat()
            })

@app.get("/api/rooms")
async def get_active_rooms():
    rooms = list(manager.active_connections.keys())
    room_info = {}
    for room in rooms:
        room_info[room] = len(manager.active_connections[room])
    return OptimizedJSONResponse(room_info)
```

## File Upload Example

### Image Upload and Processing

```python
from velithon import Velithon
from velithon.responses import OptimizedJSONResponse, FileResponse
from velithon.middleware import Middleware
from velithon.middleware.files import FileUploadMiddleware
import os
import shutil
from pathlib import Path
from PIL import Image
import uuid

app = Velithon(middleware=[
    Middleware(FileUploadMiddleware, max_size=10*1024*1024)  # 10MB limit
])

# Create upload directories
UPLOAD_DIR = Path("uploads")
THUMBNAILS_DIR = UPLOAD_DIR / "thumbnails"
UPLOAD_DIR.mkdir(exist_ok=True)
THUMBNAILS_DIR.mkdir(exist_ok=True)

def create_thumbnail(image_path: Path, thumbnail_path: Path, size: tuple = (200, 200)):
    """Create a thumbnail from an image"""
    with Image.open(image_path) as img:
        img.thumbnail(size, Image.Resampling.LANCZOS)
        img.save(thumbnail_path, optimize=True, quality=85)

@app.post("/upload")
async def upload_file(request):
    form = await request.form()
    file = form.get("file")
    
    if not file or not file.filename:
        return OptimizedJSONResponse(
            {"error": "No file provided"}, 
            status_code=400
        )
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix.lower()
    filename = f"{file_id}{file_extension}"
    file_path = UPLOAD_DIR / filename
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Create thumbnail for images
    thumbnail_path = None
    if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
        thumbnail_filename = f"thumb_{filename}"
        thumbnail_path = THUMBNAILS_DIR / thumbnail_filename
        try:
            create_thumbnail(file_path, thumbnail_path)
        except Exception as e:
            print(f"Failed to create thumbnail: {e}")
    
    return OptimizedJSONResponse({
        "file_id": file_id,
        "filename": file.filename,
        "size": file_path.stat().st_size,
        "download_url": f"/download/{file_id}",
        "thumbnail_url": f"/thumbnail/{file_id}" if thumbnail_path else None
    })

@app.get("/download/{file_id}")
async def download_file(file_id: str):
    # Find file with this ID
    for file_path in UPLOAD_DIR.glob(f"{file_id}.*"):
        if file_path.is_file():
            return FileResponse(
                file_path,
                filename=file_path.name,
                media_type="application/octet-stream"
            )
    
    return OptimizedJSONResponse(
        {"error": "File not found"}, 
        status_code=404
    )

@app.get("/thumbnail/{file_id}")
async def get_thumbnail(file_id: str):
    # Find thumbnail with this ID
    for thumb_path in THUMBNAILS_DIR.glob(f"thumb_{file_id}.*"):
        if thumb_path.is_file():
            return FileResponse(
                thumb_path,
                media_type="image/jpeg"
            )
    
    return OptimizedJSONResponse(
        {"error": "Thumbnail not found"}, 
        status_code=404
    )

@app.get("/files")
async def list_files():
    files = []
    for file_path in UPLOAD_DIR.glob("*"):
        if file_path.is_file() and not file_path.name.startswith("thumb_"):
            file_id = file_path.stem
            stat = file_path.stat()
            files.append({
                "file_id": file_id,
                "filename": file_path.name,
                "size": stat.st_size,
                "created": stat.st_ctime,
                "download_url": f"/download/{file_id}",
                "thumbnail_url": f"/thumbnail/{file_id}"
            })
    
    return OptimizedJSONResponse(files)

@app.delete("/files/{file_id}")
async def delete_file(file_id: str):
    deleted = False
    
    # Delete main file
    for file_path in UPLOAD_DIR.glob(f"{file_id}.*"):
        if file_path.is_file():
            file_path.unlink()
            deleted = True
    
    # Delete thumbnail
    for thumb_path in THUMBNAILS_DIR.glob(f"thumb_{file_id}.*"):
        if thumb_path.is_file():
            thumb_path.unlink()
    
    if deleted:
        return OptimizedJSONResponse({"message": "File deleted"})
    else:
        return OptimizedJSONResponse(
            {"error": "File not found"}, 
            status_code=404
        )
```

## Microservices Example

### Service Discovery and Communication

```python
from velithon import Velithon
from velithon.responses import OptimizedJSONResponse
from velithon.middleware import Middleware
from velithon.middleware.proxy import ProxyMiddleware
import httpx
import asyncio
from typing import Dict, List
import consul

# Service Registry
class ServiceRegistry:
    def __init__(self):
        self.consul = consul.Consul()
        self.services: Dict[str, List[str]] = {}
    
    async def register_service(self, name: str, host: str, port: int):
        self.consul.agent.service.register(
            name=name,
            service_id=f"{name}-{host}-{port}",
            address=host,
            port=port,
            check=consul.Check.http(f"http://{host}:{port}/health", interval="10s")
        )
    
    async def discover_service(self, name: str) -> List[str]:
        services = self.consul.health.service(name, passing=True)[1]
        return [f"http://{s['Service']['Address']}:{s['Service']['Port']}" 
                for s in services]

# User Service
user_app = Velithon()
registry = ServiceRegistry()

@user_app.on_event("startup")
async def startup_user_service():
    await registry.register_service("user-service", "localhost", 8001)

@user_app.get("/health")
async def user_health():
    return OptimizedJSONResponse({"status": "healthy", "service": "user-service"})

@user_app.get("/users/{user_id}")
async def get_user(user_id: int):
    # Mock user data
    return OptimizedJSONResponse({
        "id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com"
    })

@user_app.get("/users")
async def get_users():
    return OptimizedJSONResponse([
        {"id": 1, "name": "User 1", "email": "user1@example.com"},
        {"id": 2, "name": "User 2", "email": "user2@example.com"}
    ])

# Order Service
order_app = Velithon()

@order_app.on_event("startup")
async def startup_order_service():
    await registry.register_service("order-service", "localhost", 8002)

@order_app.get("/health")
async def order_health():
    return OptimizedJSONResponse({"status": "healthy", "service": "order-service"})

@order_app.get("/orders/{order_id}")
async def get_order(order_id: int):
    # Get user info from user service
    user_services = await registry.discover_service("user-service")
    if user_services:
        async with httpx.AsyncClient() as client:
            user_response = await client.get(f"{user_services[0]}/users/1")
            user_data = user_response.json()
    else:
        user_data = {"id": 1, "name": "Unknown User"}
    
    return OptimizedJSONResponse({
        "id": order_id,
        "user": user_data,
        "items": ["Item 1", "Item 2"],
        "total": 99.99
    })

# API Gateway
gateway_app = Velithon(middleware=[
    Middleware(ProxyMiddleware)
])

@gateway_app.get("/health")
async def gateway_health():
    return OptimizedJSONResponse({"status": "healthy", "service": "api-gateway"})

@gateway_app.get("/api/users/{path:path}")
async def proxy_to_user_service(request):
    user_services = await registry.discover_service("user-service")
    if not user_services:
        return OptimizedJSONResponse(
            {"error": "User service unavailable"}, 
            status_code=503
        )
    
    # Simple load balancing (round-robin)
    service_url = user_services[0]
    path = request.path_params["path"]
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{service_url}/users/{path}")
        return OptimizedJSONResponse(response.json(), status_code=response.status_code)

@gateway_app.get("/api/orders/{path:path}")
async def proxy_to_order_service(request):
    order_services = await registry.discover_service("order-service")
    if not order_services:
        return OptimizedJSONResponse(
            {"error": "Order service unavailable"}, 
            status_code=503
        )
    
    service_url = order_services[0]
    path = request.path_params["path"]
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{service_url}/orders/{path}")
        return OptimizedJSONResponse(response.json(), status_code=response.status_code)

# Circuit Breaker Pattern
class CircuitBreaker:
    def __init__(self, failure_threshold=5, reset_timeout=60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time >= self.reset_timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.reset()
            return result
        except Exception as e:
            self.record_failure()
            raise e
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
    
    def reset(self):
        self.failure_count = 0
        self.state = "CLOSED"
        self.last_failure_time = None

# Run services (in separate processes in real deployment)
if __name__ == "__main__":
    import multiprocessing
    
    def run_user_service():
        user_app.run(host="localhost", port=8001)
    
    def run_order_service():
        order_app.run(host="localhost", port=8002)
    
    def run_gateway():
        gateway_app.run(host="localhost", port=8000)
    
    # Start services
    user_process = multiprocessing.Process(target=run_user_service)
    order_process = multiprocessing.Process(target=run_order_service)
    
    user_process.start()
    order_process.start()
    
    # Run gateway in main process
    run_gateway()
```

## Next Steps

Explore more advanced examples:

- [CRUD API →](crud-api.md)
- [Authentication Systems →](authentication.md)
- [WebSocket Applications →](websocket-chat.md)
- [Microservices Architecture →](microservices.md)
- [File Upload Systems →](file-upload.md)
- [Real-time Updates →](real-time.md)
