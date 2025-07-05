# Swagger UI

Learn how to customize and configure the Swagger UI interface for your Velithon API documentation.

## Overview

Swagger UI provides an interactive interface for exploring and testing your API directly from the documentation. Velithon includes built-in support for Swagger UI with extensive customization options.

## Basic Configuration

```python
from velithon import Velithon

app = Velithon(
    title="My API",
    description="API documentation with custom Swagger UI",
    version="1.0.0",
    docs_url="/docs",  # Custom Swagger UI URL
    openapi_url="/api/v1/openapi.json"  # Custom OpenAPI schema URL
)

@app.get("/")
async def root():
    return {"message": "Visit /docs for API documentation"}
```

## Custom Swagger UI HTML

```python
from velithon.openapi import get_swagger_ui_html

@app.get("/custom-docs", include_in_schema=False)
async def custom_swagger_ui():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Custom API Documentation",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui.css",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui-bundle.js",
        swagger_favicon_url="/static/favicon.ico"
    )
```

## Swagger UI Configuration

```python
from velithon.openapi import get_swagger_ui_html

@app.get("/advanced-docs", include_in_schema=False)
async def advanced_swagger_ui():
    swagger_config = {
        "deepLinking": True,
        "displayOperationId": False,
        "defaultModelsExpandDepth": 1,
        "defaultModelExpandDepth": 1,
        "defaultModelRendering": "example",
        "displayRequestDuration": True,
        "docExpansion": "none",
        "filter": True,
        "showExtensions": True,
        "showCommonExtensions": True,
        "tryItOutEnabled": True,
        "supportedSubmitMethods": ["get", "post", "put", "delete", "patch"]
    }
    
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Advanced API Documentation",
        swagger_ui_config=swagger_config
    )
```

## Custom CSS Styling

```python
@app.get("/styled-docs", include_in_schema=False)
async def styled_swagger_ui():
    custom_css = """
    <style>
    .swagger-ui .topbar {
        background-color: #2c3e50;
        padding: 10px 0;
    }
    
    .swagger-ui .topbar .download-url-wrapper {
        display: none;
    }
    
    .swagger-ui .info {
        margin: 50px 0;
    }
    
    .swagger-ui .info .title {
        color: #2c3e50;
        font-size: 36px;
    }
    
    .swagger-ui .scheme-container {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 5px;
        margin: 20px 0;
    }
    
    .swagger-ui .btn.authorize {
        background-color: #27ae60;
        border-color: #27ae60;
    }
    
    .swagger-ui .btn.authorize:hover {
        background-color: #229954;
        border-color: #229954;
    }
    
    .swagger-ui .opblock.opblock-get .opblock-summary-method {
        background: #27ae60;
    }
    
    .swagger-ui .opblock.opblock-post .opblock-summary-method {
        background: #e74c3c;
    }
    
    .swagger-ui .opblock.opblock-put .opblock-summary-method {
        background: #f39c12;
    }
    
    .swagger-ui .opblock.opblock-delete .opblock-summary-method {
        background: #e67e22;
    }
    </style>
    """
    
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Styled API Documentation",
        custom_css=custom_css
    )
```

## Adding Custom JavaScript

```python
@app.get("/interactive-docs", include_in_schema=False)
async def interactive_swagger_ui():
    custom_js = """
    <script>
    window.onload = function() {
        // Add custom functionality
        const ui = SwaggerUIBundle({
            url: '/openapi.json',
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIBundle.presets.standalone
            ],
            layout: "StandaloneLayout",
            onComplete: function() {
                // Custom logic after Swagger UI loads
                console.log("Swagger UI loaded successfully");
                
                // Add custom buttons or modify UI
                const topbar = document.querySelector('.topbar');
                if (topbar) {
                    const customButton = document.createElement('button');
                    customButton.textContent = 'Export Schema';
                    customButton.onclick = function() {
                        window.open('/openapi.json', '_blank');
                    };
                    customButton.style.margin = '0 10px';
                    customButton.style.padding = '5px 10px';
                    customButton.style.backgroundColor = '#27ae60';
                    customButton.style.color = 'white';
                    customButton.style.border = 'none';
                    customButton.style.borderRadius = '3px';
                    topbar.appendChild(customButton);
                }
            }
        });
    };
    </script>
    """
    
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Interactive API Documentation",
        custom_js=custom_js
    )
```

## Authentication Integration

```python
from velithon.security import HTTPBearer

security = HTTPBearer()

@app.get("/protected-docs", include_in_schema=False)
async def protected_swagger_ui():
    """Swagger UI with pre-configured authentication"""
    swagger_config = {
        "persistAuthorization": True,  # Remember auth tokens
        "preauthorizeBasic": {
            "username": "demo",
            "password": "demo"
        },
        "authAction": {
            "bearerAuth": {
                "name": "bearerAuth",
                "schema": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                },
                "value": "Bearer <your-jwt-token>"
            }
        }
    }
    
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Protected API Documentation",
        swagger_ui_config=swagger_config
    )
```

## Multiple API Versions

```python
# Support multiple API versions in same Swagger UI
@app.get("/multi-version-docs", include_in_schema=False)
async def multi_version_swagger_ui():
    swagger_config = {
        "urls": [
            {
                "url": "/api/v1/openapi.json",
                "name": "API v1.0"
            },
            {
                "url": "/api/v2/openapi.json", 
                "name": "API v2.0"
            }
        ],
        "urls.primaryName": "API v2.0"
    }
    
    return get_swagger_ui_html(
        title="Multi-Version API Documentation",
        swagger_ui_config=swagger_config
    )
```

## Environment-Specific Configuration

```python
import os

@app.get("/docs", include_in_schema=False)
async def environment_docs():
    """Environment-specific Swagger UI configuration"""
    
    if os.getenv("ENV") == "production":
        # Production configuration
        config = {
            "tryItOutEnabled": False,  # Disable "try it out" in production
            "supportedSubmitMethods": ["get"],  # Only allow GET requests
            "docExpansion": "none"
        }
        title = "Production API Documentation"
    else:
        # Development configuration
        config = {
            "tryItOutEnabled": True,
            "supportedSubmitMethods": ["get", "post", "put", "delete", "patch"],
            "docExpansion": "list",
            "defaultModelsExpandDepth": 2
        }
        title = "Development API Documentation"
    
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=title,
        swagger_ui_config=config
    )
```

## Embedded Documentation

```python
@app.get("/embedded-docs", include_in_schema=False)
async def embedded_swagger_ui():
    """Swagger UI embedded in a custom page layout"""
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>My API Portal</title>
        <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui.css" />
        <style>
        body { margin: 0; font-family: Arial, sans-serif; }
        .header { background: #2c3e50; color: white; padding: 20px; text-align: center; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .footer { background: #34495e; color: white; text-align: center; padding: 20px; margin-top: 50px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>My API Portal</h1>
            <p>Comprehensive API documentation and testing interface</p>
        </div>
        
        <div class="container">
            <div id="swagger-ui"></div>
        </div>
        
        <div class="footer">
            <p>&copy; 2025 My Company. All rights reserved.</p>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui-bundle.js"></script>
        <script>
        SwaggerUIBundle({
            url: '/openapi.json',
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIBundle.presets.standalone
            ],
            layout: "StandaloneLayout"
        });
        </script>
    </body>
    </html>
    """
    
    return html_content
```

## Conditional Documentation Access

```python
from velithon import Request

@app.get("/conditional-docs", include_in_schema=False)
async def conditional_swagger_ui(request: Request):
    """Show different documentation based on request context"""
    
    # Check if user is internal (e.g., from company IP range)
    client_ip = request.client.host
    is_internal = client_ip.startswith("192.168.") or client_ip == "127.0.0.1"
    
    if is_internal:
        # Show full documentation for internal users
        openapi_url = "/openapi.json"
        title = "Internal API Documentation"
    else:
        # Show limited documentation for external users  
        openapi_url = "/public-openapi.json"
        title = "Public API Documentation"
    
    return get_swagger_ui_html(
        openapi_url=openapi_url,
        title=title
    )
```

## Best Practices

1. **Customize the UI** to match your brand
2. **Configure appropriate permissions** for different environments
3. **Use meaningful titles** and descriptions
4. **Enable/disable features** based on your needs
5. **Add custom authentication** flows when needed
6. **Provide multiple API versions** if applicable
7. **Optimize for mobile** viewing when necessary
8. **Include helpful custom buttons** and links
