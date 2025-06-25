# Performance and Best Practices

## Application Structure

Organize your application for maintainability:

```
project/
├── main.py                 # Application entry point
├── config.py              # Configuration
├── containers.py          # Dependency injection containers
├── routes/
│   ├── __init__.py
│   ├── users.py           # User routes
│   └── products.py        # Product routes
├── endpoints/
│   ├── __init__.py
│   ├── users.py           # User endpoints
│   └── products.py        # Product endpoints
├── services/
│   ├── __init__.py
│   ├── user_service.py    # Business logic
│   └── email_service.py
├── models/
│   ├── __init__.py
│   └── user.py            # Pydantic models
└── middleware/
    ├── __init__.py
    └── auth.py            # Custom middleware
```

## Performance Tips

1. **Use Async/Await**: Always use async functions for I/O operations
2. **Connection Pooling**: Use connection pools for databases
3. **Caching**: Implement caching for frequently accessed data
4. **Dependency Injection**: Use singletons for expensive resources
5. **Streaming**: Use streaming responses for large data sets

```python
# Good: Async database operations
class UserService:
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    async def get_user(self, user_id: int):
        async with self.db_pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)

# Good: Streaming large responses
@app.get("/export/users")
async def export_users():
    async def generate_csv():
        yield "id,name,email\n"
        async for user in get_all_users():
            yield f"{user.id},{user.name},{user.email}\n"
    
    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users.csv"}
    )
```

## Security Best Practices

1. **Input Validation**: Always validate input data
2. **Authentication**: Implement proper authentication middleware
3. **HTTPS**: Use SSL/TLS in production
4. **CORS**: Configure CORS properly
5. **Rate Limiting**: Implement rate limiting for public APIs

```python
from pydantic import BaseModel, validator

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    
    @validator('email')
    def validate_email(cls, v):
        import re
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', v):
            raise ValueError('Invalid email format')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

@app.post("/users")
async def create_user(user: UserCreate):
    # User data is automatically validated
    return JSONResponse({"message": "User created", "email": user.email})
```

## File Upload Best Practices

1. **File Validation**: Always validate file types, sizes, and content
2. **Secure Storage**: Store files outside the web root directory
3. **Filename Sanitization**: Use UUID or secure naming schemes
4. **Memory Management**: Stream large files to avoid memory issues
5. **Cleanup**: Remove temporary files after processing

```python
import uuid
from pathlib import Path

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

async def validate_upload(file: UploadFile) -> bool:
    # Check file extension
    if Path(file.filename).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "File type not allowed")
    
    # Check file size
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large")
    
    # Optional: Check file content/magic bytes
    content_start = await file.read(1024)
    await file.seek(0)  # Reset file pointer
    
    return True
```

## Background Task Best Practices

1. **Task Scope**: Keep background tasks lightweight and focused
2. **Error Handling**: Always handle exceptions in background tasks
3. **Resource Limits**: Use concurrency limits to prevent system overload
4. **Monitoring**: Log background task execution and failures
5. **Idempotency**: Make tasks idempotent when possible

```python
import logging
from velithon.background import BackgroundTasks

logger = logging.getLogger(__name__)

def safe_background_task(func, *args, **kwargs):
    """Wrapper for safe background task execution"""
    try:
        result = func(*args, **kwargs)
        logger.info(f"Task {func.__name__} completed successfully")
        return result
    except Exception as e:
        logger.error(f"Task {func.__name__} failed: {str(e)}")
        # Don't re-raise to prevent stopping other tasks
        return None

@app.post("/process-order")
async def process_order(order_data: dict):
    background_tasks = BackgroundTasks(max_concurrent=3)
    
    # Wrap tasks for safe execution
    background_tasks.add_task(safe_background_task, send_email, order_data["email"])
    background_tasks.add_task(safe_background_task, update_inventory, order_data["items"])
    background_tasks.add_task(safe_background_task, log_order, order_data)
    
    await background_tasks(continue_on_error=True)
    
    return {"message": "Order processed"}
```
