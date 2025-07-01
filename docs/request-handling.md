# Request Handling

## Request Object

```python
from velithon.requests import Request

@app.post("/users")
async def create_user(request: Request):
    # Get JSON body
    body = await request.json()
    
    # Get form data
    form = await request.form()
    
    # Get query parameters
    page = request.query_params.get("page", "1")
    
    # Get path parameters
    user_id = request.path_params.get("user_id")
    
    # Get headers
    auth_header = request.headers.get("authorization")
    
    # Get cookies
    session_id = request.cookies.get("session_id")
    
    return JSONResponse({"message": "User created"})
```

## Parameter Injection

Use type hints and parameter annotations for automatic injection:

```python
from typing import Annotated
from velithon.params import Query, Path, Body
from pydantic import BaseModel

class User(BaseModel):
    name: str
    email: str
    age: int

class UserEndpoint(HTTPEndpoint):
    async def get(self, user_id: Annotated[int, Path()], 
                  page: Annotated[int, Query()] = 1):
        return JSONResponse({"user_id": user_id, "page": page})
    
    async def post(self, user: Annotated[User, Body()]):
        return JSONResponse({"message": "User created", "user": user.dict()})

app.add_route("/users/{user_id}", UserEndpoint, methods=["GET", "POST"])
```

## Headers and Request Context

```python
from velithon.datastructures import Headers

class UserEndpoint(HTTPEndpoint):
    async def get(self, request: Request, headers: Headers):
        user_agent = headers.get("user-agent")
        return JSONResponse({"user_agent": user_agent})
```
