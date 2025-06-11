"""
Integration test for HTTP route decorators
"""
from velithon import Velithon
from velithon.requests import Request
from velithon.responses import JSONResponse


def test_route_decorator_integration():
    """Test HTTP method decorators in integrated application."""
    # Disable OpenAPI routes for cleaner testing
    app = Velithon(openapi_url=None, docs_url=None)
    
    @app.get("/api")
    async def get_api(request: Request):
        return JSONResponse({"message": "GET API"})
    
    @app.post("/api")
    async def post_api(request: Request):
        return JSONResponse({"message": "POST API"})
    
    @app.put("/api/{id}")
    async def put_api(request: Request):
        id = request.path_params.get("id")
        return JSONResponse({"message": f"PUT API with ID {id}"})
    
    @app.delete("/api/{id}")
    async def delete_api(request: Request):
        id = request.path_params.get("id")
        return JSONResponse({"message": f"DELETE API with ID {id}"})
    
    @app.patch("/api/{id}")
    async def patch_api(request: Request):
        id = request.path_params.get("id")
        return JSONResponse({"message": f"PATCH API with ID {id}"})
    
    @app.options("/api/options")
    async def options_api(request: Request):
        return JSONResponse({"message": "OPTIONS API"})
    
    # Check that routes were added correctly
    assert len(app.router.routes) == 6
    
    # Check path and method for each route
    paths = {"/api": {"GET", "POST"}, "/api/{id}": {"PUT", "DELETE", "PATCH"}, "/api/options": {"OPTIONS"}}
    
    for route in app.router.routes:
        path = route.path
        method = next(iter(route.methods - {"HEAD"} if "HEAD" in route.methods else route.methods))
        assert path in paths
        assert method in paths[path]
