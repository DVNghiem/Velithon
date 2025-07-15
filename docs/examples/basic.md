# Basic Examples

This page contains fundamental examples to get you started with Velithon.

## Hello World

The simplest Velithon application:

```python
from velithon import Velithon

app = Velithon()

@app.get("/")
async def hello():
    return {"message": "Hello, World!"}

if __name__ == "__main__":
    app.run()
```

## Path Parameters

Handle dynamic URL segments:

```python
from velithon import Velithon

app = Velithon()

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id, "name": f"User {user_id}"}

@app.get("/hello/{name}")
async def greet_user(name: str):
    return {"message": f"Hello, {name}!"}
```

## Query Parameters

Handle URL query parameters:

```python
from velithon import Velithon
from typing import Optional

app = Velithon()

@app.get("/items")
async def list_items(skip: int = 0, limit: int = 10, search: Optional[str] = None):
    response = {
        "skip": skip,
        "limit": limit,
        "search": search,
        "items": [f"Item {i}" for i in range(skip, skip + limit)]
    }
    return response
```

## Request Body

Handle JSON request bodies with Pydantic models:

```python
from velithon import Velithon
from pydantic import BaseModel

app = Velithon()

class User(BaseModel):
    name: str
    email: str
    age: int

@app.post("/users")
async def create_user(user: User):
    return {
        "message": "User created",
        "user": user.dict()
    }
```

## Response Types

Different ways to return responses:

```python
from velithon import Velithon
from velithon.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel

app = Velithon()

class ApiResponse(BaseModel):
    success: bool
    data: dict

@app.get("/json")
async def json_response():
    return JSONResponse({"message": "JSON response"})

@app.get("/html")
async def html_response():
    html_content = "<html><body><h1>Hello from Velithon!</h1></body></html>"
    return HTMLResponse(html_content)

@app.get("/model")
async def model_response():
    return ApiResponse(success=True, data={"message": "Pydantic model response"})
```

## Error Handling

Handle errors gracefully:

```python
from velithon import Velithon
from velithon.exceptions import HTTPException
from velithon.responses import JSONResponse

app = Velithon()

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    if user_id < 1:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    if user_id > 1000:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"user_id": user_id, "name": f"User {user_id}"}

@app.get("/divide/{a}/{b}")
async def divide(a: int, b: int):
    try:
        result = a / b
        return {"result": result}
    except ZeroDivisionError:
        return JSONResponse(
            content={"error": "Cannot divide by zero"},
            status_code=400
        )
```

## Next Steps

- Learn about [CRUD operations](crud-api.md)
- Explore [authentication examples](authentication.md)
- See [WebSocket examples](websocket-chat.md)
