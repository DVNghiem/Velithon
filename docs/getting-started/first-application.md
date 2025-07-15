# First Application

Now that you've mastered the basics, let's build a more comprehensive Velithon application that demonstrates real-world features like routers, middleware, dependency injection, and more advanced capabilities.

## 🎯 What We'll Build

In this tutorial, we'll create a **Task Management API** with:

- **Structured routing** with routers and prefixes
- **Dependency injection** for database connections
- **Middleware** for authentication and logging
- **WebSocket support** for real-time updates
- **File uploads** for task attachments
- **Background tasks** for async processing
- **OpenAPI documentation** generation

## 📁 Project Structure

Let's organize our application properly:

```
my-velithon-app/
├── app/
│   ├── __init__.py
│   ├── main.py              # Application entry point
│   ├── models/              # Pydantic models
│   │   ├── __init__.py
│   │   └── tasks.py
│   ├── routers/             # Route handlers
│   │   ├── __init__.py
│   │   ├── tasks.py
│   │   └── users.py
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   │   └── database.py
│   └── middleware/          # Custom middleware
│       ├── __init__.py
│       └── auth.py
├── uploads/                 # File storage
└── requirements.txt
```

## 🏗️ Step 1: Setup Project Structure

Create the project directories:

```bash
mkdir -p my-velithon-app/app/{models,routers,services,middleware}
mkdir -p my-velithon-app/uploads
cd my-velithon-app
touch app/__init__.py app/models/__init__.py app/routers/__init__.py
touch app/services/__init__.py app/middleware/__init__.py
```

## 📋 Step 2: Define Data Models

Create the Pydantic models for our Task Management API:

```python title="app/models/tasks.py"
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None

class Task(TaskBase):
    id: int
    status: TaskStatus = TaskStatus.TODO
    created_at: datetime
    updated_at: datetime
    assignee_id: Optional[int] = None
    attachment_path: Optional[str] = None

    class Config:
        from_attributes = True

class User(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    is_active: bool = True
    created_at: datetime

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    full_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8)
```

## 🗄️ Step 3: Database Service with Dependency Injection

Create a simple in-memory database service that we'll inject into our endpoints using Velithon's dependency injection system:

```python title="app/services/database.py"
from datetime import datetime
from typing import Dict, List, Optional
from app.models.tasks import Task, TaskCreate, TaskUpdate, User, UserCreate, TaskStatus

class DatabaseService:
    def __init__(self):
        self.tasks: Dict[int, Task] = {}
        self.users: Dict[int, User] = {}
        self.next_task_id = 1
        self.next_user_id = 1
        
        # Initialize with some sample data
        self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        """Initialize with sample users and tasks."""
        # Create sample users
        sample_users = [
            UserCreate(username="admin", email="admin@example.com", 
                      full_name="Administrator", password="admin123"),
            UserCreate(username="john", email="john@example.com",
                      full_name="John Doe", password="john123"),
        ]
        
        for user_data in sample_users:
            self.create_user(user_data)
        
        # Create sample tasks
        sample_tasks = [
            TaskCreate(title="Setup project structure", 
                      description="Initialize the Velithon project"),
            TaskCreate(title="Implement authentication",
                      description="Add JWT authentication"),
        ]
        
        for task_data in sample_tasks:
            self.create_task(task_data, assignee_id=1)
    
    # User operations
    def create_user(self, user_data: UserCreate) -> User:
        user = User(
            id=self.next_user_id,
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            created_at=datetime.now()
        )
        self.users[self.next_user_id] = user
        self.next_user_id += 1
        return user
    
    def get_user(self, user_id: int) -> Optional[User]:
        return self.users.get(user_id)
    
    def get_users(self) -> List[User]:
        return list(self.users.values())
    
    # Task operations
    def create_task(self, task_data: TaskCreate, assignee_id: Optional[int] = None) -> Task:
        task = Task(
            id=self.next_task_id,
            title=task_data.title,
            description=task_data.description,
            priority=task_data.priority,
            due_date=task_data.due_date,
            tags=task_data.tags,
            assignee_id=assignee_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.tasks[self.next_task_id] = task
        self.next_task_id += 1
        return task
    
    def get_task(self, task_id: int) -> Optional[Task]:
        return self.tasks.get(task_id)
    
    def get_tasks(self, status: Optional[TaskStatus] = None, assignee_id: Optional[int] = None) -> List[Task]:
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        if assignee_id:
            tasks = [t for t in tasks if t.assignee_id == assignee_id]
        return tasks
    
    def update_task(self, task_id: int, task_data: TaskUpdate) -> Optional[Task]:
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        # Update only provided fields
        update_data = task_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)
        
        task.updated_at = datetime.now()
        return task
    
    def delete_task(self, task_id: int) -> bool:
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False

# Create dependency injection container
from velithon.di import ServiceContainer, SingletonProvider

class AppContainer(ServiceContainer):
    database = SingletonProvider(DatabaseService)

# Create container instance
container = AppContainer()
```

**Note**: Velithon uses a powerful dependency injection system with `ServiceContainer` and providers. The `@inject` decorator automatically resolves dependencies marked with `Provide[container.service]`. This is more robust than global instances and provides better testability and modularity.

## 🛡️ Step 4: Custom Authentication Middleware

Create custom middleware for authentication:

```python title="app/middleware/auth.py"
from velithon.middleware import Middleware
from velithon.requests import Request
from velithon.responses import JSONResponse

class AuthenticationMiddleware(Middleware):
    """Simple token-based authentication middleware."""
    
    async def __call__(self, request: Request, call_next):
        # Skip auth for public endpoints
        public_paths = ["/", "/docs", "/health", "/login"]
        if request.url.path in public_paths:
            return await call_next(request)
        
        # Check for Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                content={"error": "Missing or invalid authorization header"},
                status_code=401
            )
        
        token = auth_header.split(" ")[1]
        
        # Simple token validation (use JWT in production)
        if token != "valid-token-123":
            return JSONResponse(
                content={"error": "Invalid token"},
                status_code=401
            )
        
        # Add user info to request state
        request.state.user_id = 1  # Simulate authenticated user
        return await call_next(request)
```

## 🛣️ Step 5: Task Router

Create the tasks router with full CRUD operations using Velithon's dependency injection:

```python title="app/routers/tasks.py"
from typing import List, Optional
from velithon.routing import Router
from velithon.requests import Request
from velithon.responses import JSONResponse
from velithon.di import inject, Provide
from app.models.tasks import Task, TaskCreate, TaskUpdate, TaskStatus
from app.services.database import DatabaseService, container

router = Router(path="/tasks")

@router.get("/")
@inject
async def get_tasks(
    request: Request,
    status: Optional[TaskStatus] = None,
    assignee_id: Optional[int] = None,
    db: DatabaseService = Provide[container.database]
) -> JSONResponse:
    """Get all tasks with optional filtering."""
    tasks = db.get_tasks(status=status, assignee_id=assignee_id)
    return JSONResponse({
        "tasks": [task.dict() for task in tasks],
        "count": len(tasks)
    })

@router.get("/{task_id}")
@inject
async def get_task(
    task_id: int,
    db: DatabaseService = Provide[container.database]
) -> JSONResponse:
    """Get a specific task by ID."""
    task = db.get_task(task_id)
    if not task:
        return JSONResponse(
            content={"error": "Task not found"},
            status_code=404
        )
    return JSONResponse(task.dict())

@router.post("/")
@inject
async def create_task(
    task_data: TaskCreate,
    request: Request,
    db: DatabaseService = Provide[container.database]
) -> JSONResponse:
    """Create a new task."""
    # Get assignee from authenticated user or request
    assignee_id = getattr(request.state, 'user_id', None)
    
    task = db.create_task(task_data, assignee_id=assignee_id)
    return JSONResponse(task.dict(), status_code=201)

@router.put("/{task_id}")
@inject
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: DatabaseService = Provide[container.database]
) -> JSONResponse:
    """Update a task."""
    task = db.update_task(task_id, task_data)
    if not task:
        return JSONResponse(
            content={"error": "Task not found"},
            status_code=404
        )
    return JSONResponse(task.dict())

@router.delete("/{task_id}")
@inject
async def delete_task(
    task_id: int,
    db: DatabaseService = Provide[container.database]
) -> JSONResponse:
    """Delete a task."""
    if not db.delete_task(task_id):
        return JSONResponse(
            content={"error": "Task not found"},
            status_code=404
        )
    return JSONResponse({"message": "Task deleted successfully"})
```

## 👥 Step 6: Users Router

Create the users router:

```python title="app/routers/users.py"
from typing import List
from velithon.routing import Router
from velithon.responses import JSONResponse
from velithon.di import inject, Provide
from app.models.tasks import User, UserCreate
from app.services.database import DatabaseService, container

router = Router(path="/users")

@router.get("/")
@inject
async def get_users(
    db: DatabaseService = Provide[container.database]
) -> JSONResponse:
    """Get all users."""
    users = db.get_users()
    return JSONResponse({
        "users": [user.dict() for user in users],
        "count": len(users)
    })

@router.get("/{user_id}")
@inject
async def get_user(
    user_id: int,
    db: DatabaseService = Provide[container.database]
) -> JSONResponse:
    """Get a specific user by ID."""
    user = db.get_user(user_id)
    if not user:
        return JSONResponse(
            content={"error": "User not found"},
            status_code=404
        )
    return JSONResponse(user.dict())

@router.post("/")
@inject
async def create_user(
    user_data: UserCreate,
    db: DatabaseService = Provide[container.database]
) -> JSONResponse:
    """Create a new user."""
    user = db.create_user(user_data)
    return JSONResponse(user.dict(), status_code=201)
```

## 🚀 Step 7: Main Application

Now let's put it all together in the main application:

```python title="app/main.py"
from velithon import Velithon
from velithon.middleware.logging import LoggingMiddleware
from velithon.middleware.cors import CORSMiddleware
from velithon.responses import JSONResponse
from app.routers import tasks, users
from app.middleware.auth import AuthenticationMiddleware
from app.services.database import container

# Create the Velithon application
app = Velithon(
    title="Task Management API",
    description="A comprehensive task management system built with Velithon RSGI",
    version="1.0.0",
    middleware=[
        LoggingMiddleware(),
        CORSMiddleware(
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"]
        ),
        AuthenticationMiddleware(),
    ]
)

# Register the dependency injection container
app.register_container(container)

# Include routers
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")

# Root endpoints
@app.get("/")
async def root():
    """API Welcome endpoint."""
    return JSONResponse({
        "message": "Welcome to Task Management API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "tasks": "/api/v1/tasks",
            "users": "/api/v1/users",
            "health": "/health"
        }
    })

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse({
        "status": "healthy",
        "service": "task-management-api",
        "version": "1.0.0"
    })

@app.post("/login")
async def login():
    """Simple login endpoint for demo."""
    return JSONResponse({
        "access_token": "valid-token-123",
        "token_type": "bearer",
        "message": "Use this token in Authorization header: Bearer valid-token-123"
    })

if __name__ == "__main__":
    app._serve(
        app="main:app",
        host="0.0.0.0", 
        port=8000,
        workers=1,
        log_level="INFO"
    )
```

## 🔧 Step 8: Run the Application

Create a requirements file:

```txt title="requirements.txt"
velithon>=0.4.3
```

Install dependencies and run:

```bash
pip install -r requirements.txt
velithon run --app app.main:app --reload --log-level DEBUG
```

## 🧪 Step 9: Test the API

### 1. Get Authentication Token

```bash
curl -X POST http://localhost:8000/login
```

### 2. Create a Task (with authentication)

```bash
curl -X POST "http://localhost:8000/api/v1/tasks" \
  -H "Authorization: Bearer valid-token-123" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Learn Velithon",
    "description": "Master the Velithon RSGI framework",
    "priority": "high",
    "tags": ["learning", "framework"]
  }'
```

### 3. Get All Tasks

```bash
curl -H "Authorization: Bearer valid-token-123" \
  http://localhost:8000/api/v1/tasks
```

### 4. Update a Task

```bash
curl -X PUT "http://localhost:8000/api/v1/tasks/1" \
  -H "Authorization: Bearer valid-token-123" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "completed"
  }'
```

## 📚 What You've Learned

Congratulations! You've built a comprehensive Velithon application with:

- ✅ **Structured routing** with routers and path prefixes
- ✅ **Dependency injection** for services
- ✅ **Custom middleware** for authentication and CORS
- ✅ **Pydantic models** for request/response validation
- ✅ **Error handling** and proper HTTP status codes
- ✅ **OpenAPI documentation** (available at `/docs`)
- ✅ **RSGI performance** with Granian server

## 🔄 What's Next?

Now you're ready to explore advanced features:

- **[WebSocket Support](../user-guide/websocket.md)** - Real-time communication
- **[File Uploads](../user-guide/file-uploads.md)** - Handle file attachments  
- **[Background Tasks](../user-guide/background-tasks.md)** - Async processing
- **[Authentication](../security/authentication.md)** - JWT and OAuth2
- **[Performance Optimization](../advanced/json-optimization.md)** - Advanced optimizations

**[Explore Core Concepts →](../user-guide/core-concepts.md)**
