"""
Simple Session Example

Basic demonstration of session functionality in Velithon.
"""

from velithon import Velithon
from velithon.middleware import Middleware
from velithon.middleware.session import SessionMiddleware
from velithon.requests import Request
from velithon.responses import JSONResponse

# Create app with session middleware
app = Velithon(
    middleware=[
        Middleware(
            SessionMiddleware,
            secret_key="my-secret-key"
        )
    ]
)

@app.get("/")
async def home(request: Request):
    """Show current session status."""
    return JSONResponse({
        "message": "Session Example",
        "endpoints": {
            "GET /visit": "Increment visit counter",
            "GET /session": "View session data", 
            "POST /set": "Set session value (key, value in JSON)",
            "POST /clear": "Clear session"
        }
    })

@app.get("/visit")
async def visit_counter(request: Request):
    """Increment visit counter in session."""
    visits = request.session.get("visits", 0)
    visits += 1
    request.session["visits"] = visits
    request.session["last_visit"] = "2025-05-24T10:30:00Z"
    
    return JSONResponse({
        "visits": visits,
        "message": f"You have visited {visits} times"
    })

@app.get("/session") 
async def view_session(request: Request):
    """View current session data."""
    return JSONResponse({
        "session_id": getattr(request.session, "session_id", "unknown"),
        "data": dict(request.session),
        "modified": getattr(request.session, "modified", False)
    })

@app.post("/set")
async def set_value(request: Request):
    """Set a value in session."""
    data = await request.json()
    key = data.get("key")
    value = data.get("value")
    
    if not key:
        return JSONResponse({"error": "Key required"}, status_code=400)
        
    request.session[key] = value
    
    return JSONResponse({
        "message": f"Set {key} = {value}",
        "session": dict(request.session)
    })

@app.post("/clear")
async def clear_session(request: Request):
    """Clear all session data."""
    request.session.clear()
    
    return JSONResponse({
        "message": "Session cleared"
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
