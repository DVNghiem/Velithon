# Error Handling

## HTTP Exceptions

```python
from velithon.exceptions import HTTPException

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    if user_id < 1:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    # Simulate user not found
    if user_id == 999:
        raise HTTPException(status_code=404, detail="User not found")
    
    return JSONResponse({"user_id": user_id})
```

## Custom Exception Handlers

```python
from velithon.requests import Request
from velithon.responses import JSONResponse

async def custom_404_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        content={"error": "Resource not found", "path": request.url.path},
        status_code=404
    )

# Register exception handler
app.add_exception_handler(404, custom_404_handler)
```

## Global Exception Handling

```python
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        content={"error": "Internal server error", "type": type(exc).__name__},
        status_code=500
    )

app.add_exception_handler(Exception, global_exception_handler)
```
