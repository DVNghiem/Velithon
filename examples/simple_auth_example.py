"""Simple Authentication Example for Velithon.

This example shows how to enable the built-in security middleware
and create a basic protected endpoint.
"""

from typing import Annotated

from velithon import Velithon
from velithon.requests import Request
from velithon.responses import JSONResponse
from velithon.security import HTTPBearer, AuthenticationError, User, JWTHandler


# JWT Configuration - Use environment variable in production
import os
SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-in-production")
jwt_handler = JWTHandler(secret_key=SECRET_KEY)
bearer_scheme = HTTPBearer()

# Simple user authentication
async def get_current_user(request) -> User:
    """Get current user from JWT token."""
    try:
        token = await bearer_scheme(request)
        payload = jwt_handler.decode_token(token)
        username = payload.get("sub")
        if not username:
            raise AuthenticationError("Invalid token")
        
        # In a real app, you'd fetch user from database
        return User(
            username=username,
            email=f"{username}@example.com",
            full_name=f"User {username}",
            disabled=False,
            roles=["user"],
            permissions=["read"],
        )
    except Exception as exc:
        raise AuthenticationError("Invalid or missing token") from exc


# Create app with security middleware enabled
app = Velithon(
    title="Simple Authentication Demo",
    description="A simple example showing Velithon's authentication features",
    # Security middleware is now safe for production use after SecurityProtocol fixes
    include_security_middleware=True,
)


@app.get("/")
async def public_endpoint():
    """Public endpoint - no authentication required."""
    return JSONResponse({
        "message": "Hello! This is a public endpoint.",
        "info": "To access protected endpoints, you need a JWT token.",
        "login_url": "/login",
    })


@app.post("/login")
async def login(request: Request):
    """Simple login endpoint that returns a JWT token."""
    # Parse request data (handle both JSON and form data)
    try:
        body = await request.body()
        if body:
            try:
                # Try JSON first
                import json
                data = json.loads(body.decode())
                username = data.get("username")
                password = data.get("password")
            except json.JSONDecodeError:
                # Fallback to form data
                form_data = {}
                for part in body.decode().split("&"):
                    if "=" in part:
                        key, value = part.split("=", 1)
                        form_data[key] = value
                username = form_data.get("username")
                password = form_data.get("password")
        else:
            return JSONResponse(
                {"error": "Missing username and password"},
                status_code=400
            )
        
        if not username or not password:
            return JSONResponse(
                {"error": "Missing username or password"},
                status_code=400
            )
        
        # In a real app, verify credentials against database
        if username == "admin" and password == "secret":
            token = jwt_handler.encode_token({"sub": username})
            return JSONResponse({
                "access_token": token,
                "token_type": "bearer",
                "message": "Login successful!",
            })
        else:
            return JSONResponse(
                {"error": "Invalid credentials"},
                status_code=401,
            )
            
    except Exception as e:
        return JSONResponse(
            {"error": f"Login failed: {e!s}"},
            status_code=500
        )


@app.get("/protected")
async def protected_endpoint(
    current_user: Annotated[User, get_current_user]
):
    """Protected endpoint - requires JWT authentication."""
    return JSONResponse({
        "message": f"Hello, {current_user.full_name}!",
        "username": current_user.username,
        "permissions": current_user.permissions,
        "info": "This is a protected endpoint",
    })


@app.get("/user/profile")
async def user_profile(
    current_user: Annotated[User, get_current_user]
):
    """Get user profile information."""
    return JSONResponse({
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "roles": current_user.roles,
        "permissions": current_user.permissions,
    })


if __name__ == "__main__":
    print("🚀 Starting Simple Authentication Demo")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🔓 Public endpoint: http://localhost:8000/")
    print("🔐 Login: POST /login with username=admin, password=secret")
    print("🔒 Protected endpoint: GET /protected (requires Bearer token)")
    
    # Use Granian server for RSGI
    import granian
    
    server = granian.Granian(
        target="examples.simple_auth_example:app",
        address="0.0.0.0",
        port=8000,
        interface="rsgi",
        reload=True,
    )
    server.serve()
