# Examples

## Complete REST API Example

```python
from velithon import Velithon
from velithon.endpoint import HTTPEndpoint
from velithon.responses import JSONResponse
from velithon.requests import Request
from velithon.di import ServiceContainer, SingletonProvider, inject, Provide
from velithon.middleware import Middleware
from velithon.middleware.cors import CORSMiddleware
from velithon.middleware.logging import LoggingMiddleware
from pydantic import BaseModel
from typing import List, Optional

# Models
class User(BaseModel):
    id: Optional[int] = None
    name: str
    email: str

# Services
class UserService:
    def __init__(self):
        self.users = []
        self.next_id = 1
    
    async def create_user(self, user_data: dict) -> User:
        user = User(id=self.next_id, **user_data)
        self.users.append(user)
        self.next_id += 1
        return user
    
    async def get_user(self, user_id: int) -> Optional[User]:
        return next((u for u in self.users if u.id == user_id), None)
    
    async def get_all_users(self) -> List[User]:
        return self.users
    
    async def update_user(self, user_id: int, user_data: dict) -> Optional[User]:
        user = await self.get_user(user_id)
        if user:
            for key, value in user_data.items():
                setattr(user, key, value)
        return user
    
    async def delete_user(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        if user:
            self.users.remove(user)
            return True
        return False

# Container
class Container(ServiceContainer):
    user_service = SingletonProvider(UserService)

container = Container()

# Endpoints
class UserEndpoint(HTTPEndpoint):
    @inject
    async def get(self, request: Request, user_service: UserService = Provide[container.user_service]):
        """Get all users"""
        users = await user_service.get_all_users()
        return JSONResponse([user.dict() for user in users])
    
    @inject
    async def post(self, request: Request, user_service: UserService = Provide[container.user_service]):
        """Create a new user"""
        user_data = await request.json()
        user = await user_service.create_user(user_data)
        return JSONResponse(user.dict(), status_code=201)

class UserDetailEndpoint(HTTPEndpoint):
    @inject
    async def get(self, request: Request, user_service: UserService = Provide[container.user_service]):
        """Get user by ID"""
        user_id = int(request.path_params["user_id"])
        user = await user_service.get_user(user_id)
        
        if not user:
            return JSONResponse({"error": "User not found"}, status_code=404)
        
        return JSONResponse(user.dict())
    
    @inject
    async def put(self, request: Request, user_service: UserService = Provide[container.user_service]):
        """Update user"""
        user_id = int(request.path_params["user_id"])
        user_data = await request.json()
        user = await user_service.update_user(user_id, user_data)
        
        if not user:
            return JSONResponse({"error": "User not found"}, status_code=404)
        
        return JSONResponse(user.dict())
    
    @inject
    async def delete(self, request: Request, user_service: UserService = Provide[container.user_service]):
        """Delete user"""
        user_id = int(request.path_params["user_id"])
        success = await user_service.delete_user(user_id)
        
        if not success:
            return JSONResponse({"error": "User not found"}, status_code=404)
        
        return JSONResponse({"message": "User deleted"})

# Application
app = Velithon(
    title="User API",
    description="A simple user management API",
    version="1.0.0",
    middleware=[
        Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"]),
        Middleware(LoggingMiddleware)
    ]
)

# Register container
app.register_container(container)

# Routes
app.add_route("/users", UserEndpoint, methods=["GET", "POST"])
app.add_route("/users/{user_id}", UserDetailEndpoint, methods=["GET", "PUT", "DELETE"])

@app.get("/health")
async def health_check():
    return JSONResponse({"status": "healthy"})
```

## WebSocket Chat Example

```python
from velithon import Velithon, WebSocket
from velithon.websocket import WebSocketDisconnect, WebSocketEndpoint
from velithon.responses import HTMLResponse
import json
from typing import List

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                self.disconnect(connection)

manager = ConnectionManager()

app = Velithon()

class ChatEndpoint(WebSocketEndpoint):
    async def on_connect(self, websocket: WebSocket):
        await manager.connect(websocket)
        await manager.broadcast(json.dumps({
            "type": "user_joined",
            "message": f"User {websocket.client} joined the chat"
        }))
    
    async def on_receive(self, websocket: WebSocket, data: str):
        message_data = json.loads(data)
        response = {
            "type": "message",
            "user": str(websocket.client),
            "message": message_data.get("message", "")
        }
        await manager.broadcast(json.dumps(response))
    
    async def on_disconnect(self, websocket: WebSocket):
        manager.disconnect(websocket)
        await manager.broadcast(json.dumps({
            "type": "user_left",
            "message": f"User {websocket.client} left the chat"
        }))

app.add_websocket_route("/ws/chat", ChatEndpoint)

@app.get("/")
async def chat_page():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Velithon Chat</title>
    </head>
    <body>
        <div id="messages"></div>
        <input type="text" id="messageInput" placeholder="Type a message...">
        <button onclick="sendMessage()">Send</button>
        
        <script>
            const ws = new WebSocket("ws://localhost:8000/ws/chat");
            const messages = document.getElementById("messages");
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                const div = document.createElement("div");
                div.innerHTML = `<strong>${data.type}:</strong> ${data.message}`;
                messages.appendChild(div);
            };
            
            function sendMessage() {
                const input = document.getElementById("messageInput");
                ws.send(JSON.stringify({message: input.value}));
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
    """)
```

## File Upload and Processing Service

```python
from velithon import Velithon
from velithon.params import File, Form
from velithon.datastructures import UploadFile
from velithon.responses import JSONResponse, HTMLResponse
from velithon.background import BackgroundTasks
from velithon.middleware import Middleware
from velithon.middleware.cors import CORSMiddleware
from pathlib import Path
import uuid
import asyncio
from typing import List

app = Velithon(
    middleware=[
        Middleware(CORSMiddleware, allow_origins=["*"])
    ]
)

# Create upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Background task functions
def process_image(file_path: str, processing_type: str):
    """Simulate image processing (resize, compress, etc.)"""
    print(f"Processing {file_path} with {processing_type}")
    # Simulate processing time
    import time
    time.sleep(2)
    print(f"Finished processing {file_path}")

def send_notification(email: str, filename: str):
    """Simulate sending email notification"""
    print(f"Sending notification to {email} about {filename}")

async def log_upload(filename: str, size: int, user_id: str):
    """Async logging function"""
    await asyncio.sleep(0.1)  # Simulate async database write
    print(f"Logged upload: {filename} ({size} bytes) by user {user_id}")

# Routes
@app.get("/")
async def upload_form():
    """Upload form page"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>File Upload Service</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            form { margin: 20px 0; }
            input, select { margin: 10px 0; display: block; }
            button { background: #007cba; color: white; padding: 10px; border: none; cursor: pointer; }
        </style>
    </head>
    <body>
        <h1>File Upload Service</h1>
        
        <h2>Single File Upload</h2>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="text" name="user_email" placeholder="Your email" required>
            <input type="text" name="user_id" placeholder="User ID" required>
            <select name="processing_type">
                <option value="resize">Resize</option>
                <option value="compress">Compress</option>
                <option value="thumbnail">Create Thumbnail</option>
            </select>
            <input type="file" name="file" required>
            <button type="submit">Upload File</button>
        </form>
        
        <h2>Multiple Files Upload</h2>
        <form action="/upload-multiple" method="post" enctype="multipart/form-data">
            <input type="text" name="user_email" placeholder="Your email" required>
            <input type="text" name="user_id" placeholder="User ID" required>
            <input type="file" name="files" multiple required>
            <button type="submit">Upload Files</button>
        </form>
    </body>
    </html>
    """)

@app.post("/upload")
async def upload_file(
    user_email: str = Form(...),
    user_id: str = Form(...),
    processing_type: str = Form("resize"),
    file: UploadFile = File(...)
):
    """Handle single file upload with background processing"""
    
    # Validate file
    if not file.filename:
        return JSONResponse({"error": "No file provided"}, status_code=400)
    
    # Validate file size (max 10MB)
    if file.size > 10 * 1024 * 1024:
        return JSONResponse({"error": "File too large (max 10MB)"}, status_code=400)
    
    # Generate secure filename
    file_extension = Path(file.filename).suffix
    secure_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = UPLOAD_DIR / secure_filename
    
    # Save file
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Set up background tasks
    background_tasks = BackgroundTasks(max_concurrent=3)
    background_tasks.add_task(process_image, str(file_path), processing_type)
    background_tasks.add_task(send_notification, user_email, file.filename)
    background_tasks.add_task(log_upload, file.filename, file.size, user_id)
    
    # Execute background tasks
    await background_tasks(continue_on_error=True)
    
    return JSONResponse({
        "message": "File uploaded successfully",
        "filename": secure_filename,
        "original_name": file.filename,
        "size": file.size,
        "processing_type": processing_type,
        "status": "processing_started"
    })

@app.post("/upload-multiple")
async def upload_multiple_files(
    user_email: str = Form(...),
    user_id: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """Handle multiple file uploads with batch processing"""
    
    if not files:
        return JSONResponse({"error": "No files provided"}, status_code=400)
    
    uploaded_files = []
    background_tasks = BackgroundTasks(max_concurrent=5)
    
    for file in files:
        # Validate each file
        if file.size > 10 * 1024 * 1024:
            continue  # Skip files that are too large
        
        # Generate secure filename
        file_extension = Path(file.filename).suffix
        secure_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = UPLOAD_DIR / secure_filename
        
        # Save file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Add to background processing
        background_tasks.add_task(process_image, str(file_path), "batch_resize")
        background_tasks.add_task(log_upload, file.filename, file.size, user_id)
        
        uploaded_files.append({
            "filename": secure_filename,
            "original_name": file.filename,
            "size": file.size
        })
    
    # Send single notification for batch upload
    background_tasks.add_task(
        send_notification, 
        user_email, 
        f"Batch upload of {len(uploaded_files)} files"
    )
    
    # Execute all background tasks
    await background_tasks(continue_on_error=True)
    
    return JSONResponse({
        "message": f"Uploaded {len(uploaded_files)} files successfully",
        "files": uploaded_files,
        "status": "batch_processing_started"
    })

@app.get("/status/{filename}")
async def get_processing_status(filename: str):
    """Check if a file exists (simple status check)"""
    file_path = UPLOAD_DIR / filename
    
    if file_path.exists():
        return JSONResponse({
            "filename": filename,
            "status": "completed",
            "size": file_path.stat().st_size
        })
    else:
        return JSONResponse({
            "filename": filename,
            "status": "not_found"
        }, status_code=404)

if __name__ == "__main__":
    print("Starting File Upload Service...")
    print("Upload directory:", UPLOAD_DIR.absolute())
```
