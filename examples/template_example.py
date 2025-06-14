"""
Velithon Template Engine Example.

This example demonstrates the high-performance template engine built in Rust
with Handlebars-style syntax integration.
"""

import datetime

from velithon import Velithon
from velithon.requests import Request
from velithon.responses import JSONResponse
from velithon.templates import TemplateEngine


# Create the Velithon app
app = Velithon(
    title="Template Engine Demo",
    description="Demonstrating Velithon's high-performance template engine",
    version="1.0.0"
)

# Initialize the template engine
template_engine = TemplateEngine(
    template_dir="examples/templates",
    auto_reload=True,  # Set to False in production
    cache_enabled=True,
    strict_mode=True,
)


@app.get("/")
async def home():
    """Home page showcasing template features."""
    context = {
        "title": "Velithon Template Engine Demo",
        "current_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "features": [
            "High-performance Rust implementation",
            "Handlebars-style syntax",
            "Template compilation and caching", 
            "Context variable injection",
            "XSS protection and security features",
            "Template inheritance and partials",
            "Built-in helpers (upper, lower, len, format_date)",
            "Integration with Velithon responses",
        ],
        "stats": {
            "templates_loaded": len(template_engine.get_template_names()),
            "render_time": 2.5,  # Example render time
        },
        "items": [
            {
                "name": "High Performance",
                "description": "Rust-powered template engine for maximum speed",
                "price": "Free"
            },
            {
                "name": "Security",
                "description": "Built-in XSS protection and path traversal prevention",
                "price": "Included"
            },
            {
                "name": "Easy Integration",
                "description": "Simple API that works seamlessly with Velithon",
                "price": "Built-in"
            }
        ]
    }
    
    return template_engine.render_response("index.html", context)


@app.get("/profile")
async def profile():
    """User profile page example."""
    context = {
        "title": "Velithon",
        "user": {
            "name": "Alice Johnson",
            "title": "Senior Software Engineer",
            "email": "alice@example.com",
            "location": "San Francisco, CA",
            "joined_date": "2023-01-15",
            "bio": "Passionate about building high-performance web applications with modern technologies. "
                   "Loves working with Rust, Python, and cutting-edge frameworks.",
            "skills": [
                "Python", "Rust", "JavaScript", "TypeScript", 
                "React", "FastAPI", "Velithon", "PostgreSQL",
                "Docker", "Kubernetes", "AWS"
            ],
            "projects": [
                {
                    "name": "Velithon Web Framework",
                    "description": "High-performance asynchronous web framework for Python",
                    "technologies": ["Rust", "Python", "PyO3"]
                },
                {
                    "name": "Template Engine",
                    "description": "Blazing-fast template engine with Handlebars syntax",
                    "technologies": ["Rust", "Handlebars", "Serde"]
                },
                {
                    "name": "API Gateway",
                    "description": "Microservices gateway with load balancing and service discovery",
                    "technologies": ["Rust", "Tokio", "gRPC"]
                }
            ]
        }
    }
    
    return template_engine.render_response("profile.html", context)


@app.get("/api/templates")
async def list_templates() -> JSONResponse:
    """List available templates."""
    return JSONResponse({
        "templates": template_engine.get_template_names(),
        "template_dir": str(template_engine.template_dir),
        "total_count": len(template_engine.get_template_names())
    })


@app.get("/api/template/{template_name}")
async def template_info(template_name: str) -> JSONResponse:
    """Get information about a specific template."""
    if not template_engine.is_template_registered(template_name):
        return JSONResponse(
            {"error": f"Template '{template_name}' not found"},
            status_code=404
        )
    
    return JSONResponse({
        "name": template_name,
        "registered": True,
        "path": str(template_engine.template_dir / template_name)
    })


@app.post("/api/render")
async def render_template_api(request: Request) -> JSONResponse:
    """Render templates with custom context."""
    try:
        body = await request.json()
        template_name = body.get("template")
        context = body.get("context", {})
        
        if not template_name:
            return JSONResponse(
                {"error": "template name is required"},
                status_code=400
            )
        
        html = template_engine.render(template_name, context)
        return JSONResponse({
            "html": html,
            "template": template_name,
            "success": True
        })
        
    except Exception as e:
        return JSONResponse(
            {"error": str(e), "success": False},
            status_code=500
        )


if __name__ == "__main__":
    print("Velithon Template Engine Example")
    print("================================")
    print()
    print("Available endpoints:")
    print("  GET  /          - Home page with template features")
    print("  GET  /profile   - User profile example")
    print("  GET  /api/templates - List available templates")
    print("  GET  /api/template/{name} - Template information")
    print("  POST /api/render - Render template with custom context")
    print()
    print("Template engine features:")
    print("  - High-performance Rust implementation")
    print("  - Handlebars-style syntax")
    print("  - Template compilation and caching")
    print("  - Built-in security features")
    print("  - Context variable injection")
    print("  - Template inheritance support")
    print()
    print("Starting development server...")
    print("Visit: http://localhost:8000")
    
    # Note: In a real application, you would run this with:
    # velithon run --app template_example:app --host 0.0.0.0 --port 8000
