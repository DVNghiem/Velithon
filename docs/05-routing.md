# Routing

## Route Decorators

Use decorators to define routes:

```python
@app.get("/users")
async def get_users():
    return JSONResponse({"users": []})

@app.post("/users")
async def create_user():
    return JSONResponse({"message": "User created"})

@app.put("/users/{user_id}")
async def update_user(user_id: int):
    return JSONResponse({"user_id": user_id, "message": "Updated"})

@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    return JSONResponse({"message": "User deleted"})
```

## Path Parameters

Define path parameters with type hints:

```python
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return JSONResponse({"user_id": user_id})

@app.get("/users/{user_id}/posts/{post_id}")
async def get_user_post(user_id: int, post_id: str):
    return JSONResponse({"user_id": user_id, "post_id": post_id})
```

## Adding Routes Programmatically

```python
from velithon.routing import Router

router = Router()

async def user_handler(request):
    return JSONResponse({"message": "User handler"})

router.add_route("/users", user_handler, methods=["GET"])
app = Velithon(routes=router.routes)
```
