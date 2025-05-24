# HTTP Endpoints

## Class-Based Endpoints

Create reusable endpoint classes:

```python
from velithon.endpoint import HTTPEndpoint
from velithon.responses import JSONResponse, PlainTextResponse
from velithon.requests import Request

class UserEndpoint(HTTPEndpoint):
    async def get(self, request: Request):
        """Get all users"""
        return JSONResponse({"users": []})
    
    async def post(self, request: Request):
        """Create a new user"""
        body = await request.json()
        return JSONResponse({"message": "User created", "data": body})
    
    async def put(self, request: Request):
        """Update a user"""
        return JSONResponse({"message": "User updated"})
    
    async def delete(self, request: Request):
        """Delete a user"""
        return PlainTextResponse("User deleted")

# Register the endpoint
app.add_route("/users", UserEndpoint, methods=["GET", "POST", "PUT", "DELETE"])
```

## Method-Specific Endpoints

```python
class ProductEndpoint(HTTPEndpoint):
    async def get(self, request: Request):
        product_id = request.path_params.get("product_id")
        return JSONResponse({"product_id": product_id})

app.add_route("/products/{product_id}", ProductEndpoint, methods=["GET"])
```
