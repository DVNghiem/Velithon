# Template Engine

Velithon includes a high-performance template engine built in Rust with Handlebars-style syntax. This engine provides excellent performance, security features, and seamless integration with Velithon's response system.

## Features

- **High Performance**: Rust-powered template engine for maximum speed
- **Handlebars Syntax**: Familiar and widely-adopted template syntax
- **Template Compilation**: Templates are compiled for optimal performance
- **Caching**: Built-in template caching for production environments
- **Security**: XSS protection and path traversal prevention
- **Built-in Helpers**: Common template helpers included
- **Type Safety**: Full type hints and integration with Python

## Quick Start

### Basic Setup

```python
from velithon.templates import TemplateEngine

# Create template engine
engine = TemplateEngine("templates/")

# Render a template
html = engine.render("index.html", {"name": "World"})
```

### Integration with Velithon

```python
from velithon import Velithon
from velithon.templates import TemplateEngine

app = Velithon()
engine = TemplateEngine("templates/")

@app.get("/")
async def home():
    return engine.render_response("home.html", {
        "title": "Welcome",
        "user": {"name": "Alice"}
    })
```

## Template Syntax

Velithon uses Handlebars-style syntax for templates:

### Variables

```handlebars
<!-- Simple variable -->
<h1>Hello {{name}}!</h1>

<!-- Object properties -->
<p>{{user.name}} - {{user.email}}</p>

<!-- Array access -->
<p>First item: {{items.0}}</p>
```

### Conditionals

```handlebars
{{#if user}}
    <p>Welcome, {{user.name}}!</p>
{{else}}
    <p>Please log in.</p>
{{/if}}

{{#unless user.is_admin}}
    <p>Access denied.</p>
{{/unless}}
```

### Loops

```handlebars
<!-- Each loop -->
<ul>
{{#each items}}
    <li>{{this}}</li>
{{/each}}
</ul>

<!-- Loop with object -->
{{#each users}}
    <div>
        <h3>{{name}}</h3>
        <p>{{email}}</p>
    </div>
{{/each}}

<!-- Loop with index -->
{{#each items}}
    <p>{{@index}}: {{this}}</p>
{{/each}}
```

### Built-in Helpers

```handlebars
<!-- String manipulation -->
<p>{{upper name}}</p>  <!-- ALICE -->
<p>{{lower name}}</p>  <!-- alice -->

<!-- Length helper -->
<p>You have {{len items}} items</p>

<!-- Date formatting -->
<p>Today: {{format_date today}}</p>
```

## Template Engine Configuration

### Initialization Options

```python
engine = TemplateEngine(
    template_dir="templates/",
    auto_reload=True,        # Reload templates when changed (dev mode)
    cache_enabled=True,      # Enable template caching
    strict_mode=True,        # Enable strict mode for security
)
```

### Production Configuration

```python
# Production settings
engine = TemplateEngine(
    template_dir="templates/",
    auto_reload=False,       # Disable auto-reload for performance
    cache_enabled=True,      # Keep caching enabled
    strict_mode=True,        # Always use strict mode
)
```

## Template Management

### Loading Templates

```python
# Load all templates from directory
loaded = engine.load_templates()
print(f"Loaded {len(loaded)} templates")

# Load specific template
engine.load_template("specific.html")

# Register template from string
engine.register_template("custom", "<h1>{{title}}</h1>")
```

### Template Information

```python
# Get all template names
templates = engine.get_template_names()

# Check if template exists
if engine.is_template_registered("user.html"):
    html = engine.render("user.html", context)

# Get template directory
template_dir = engine.template_dir
```

## Response Integration

### Using render_response

```python
@app.get("/users/{user_id}")
async def user_profile(user_id: int):
    user = get_user(user_id)
    
    return engine.render_response(
        "profile.html",
        {"user": user},
        status_code=200,
        headers={"Cache-Control": "max-age=3600"}
    )
```

### Using TemplateResponse

```python
from velithon.templates import TemplateResponse

@app.get("/dashboard")
async def dashboard():
    template_response = TemplateResponse(
        engine,
        "dashboard.html",
        {"stats": get_stats()},
        status_code=200
    )
    
    # Add custom headers
    template_response.set_header("X-Custom", "value")
    
    return template_response.to_response()
```

## Advanced Features

### Template Inheritance

Create a base template (`base.html`):

```handlebars
<!DOCTYPE html>
<html>
<head>
    <title>{{title}}</title>
    {{#if styles}}
        {{#each styles}}
            <link rel="stylesheet" href="{{this}}">
        {{/each}}
    {{/if}}
</head>
<body>
    <header>
        <h1>{{site_name}}</h1>
    </header>
    
    <main>
        {{> content}}
    </main>
    
    <footer>
        <p>&copy; 2024 {{site_name}}</p>
    </footer>
</body>
</html>
```

Use inheritance in child templates:

```handlebars
{{#> base}}
    {{#content}}
        <h2>{{page_title}}</h2>
        <p>{{page_content}}</p>
    {{/content}}
{{/base}}
```

### Partials

Create reusable template parts (`_user_card.html`):

```handlebars
<div class="user-card">
    <h3>{{name}}</h3>
    <p>{{email}}</p>
    {{#if avatar}}
        <img src="{{avatar}}" alt="{{name}}">
    {{/if}}
</div>
```

Use partials in templates:

```handlebars
<div class="users">
    {{#each users}}
        {{> _user_card}}
    {{/each}}
</div>
```

### Context Data Types

The template engine supports various Python data types:

```python
context = {
    # Basic types
    "string_val": "Hello",
    "int_val": 42,
    "float_val": 3.14,
    "bool_val": True,
    "none_val": None,
    
    # Collections
    "list_val": [1, 2, 3],
    "dict_val": {"key": "value"},
    
    # Complex objects
    "user": {
        "name": "Alice",
        "settings": {
            "theme": "dark",
            "notifications": True
        }
    }
}
```

## Security Features

### Path Traversal Protection

The template engine automatically prevents path traversal attacks:

```python
# These will raise SecurityWarning
engine.render("../../../etc/passwd", {})
engine.render("..\\..\\windows\\system32", {})
```

### XSS Protection

HTML content is automatically escaped:

```python
context = {"user_input": "<script>alert('xss')</script>"}
# Output: &lt;script&gt;alert('xss')&lt;/script&gt;
```

To render raw HTML (use with caution):

```handlebars
{{{raw_html_content}}}
```

### Strict Mode

Strict mode provides additional security:

```python
# Enable strict mode (recommended)
engine.set_strict_mode(True)

# Strict mode will:
# - Require all variables to be defined
# - Prevent undefined property access
# - Provide better error messages
```

## Error Handling

### Common Errors

```python
try:
    html = engine.render("template.html", context)
except FileNotFoundError:
    # Template file not found
    print("Template does not exist")
except RuntimeError as e:
    # Template syntax error or render error
    print(f"Template error: {e}")
except Exception as e:
    # Security warnings, etc.
    print(f"Template security error: {e}")
```

### Template Debugging

```python
# List all available templates
templates = engine.get_template_names()
print("Available templates:", templates)

# Check if specific template exists
if not engine.is_template_registered("user.html"):
    print("Template 'user.html' not found")
    print("Available templates:", templates)
```

## Performance Optimization

### Production Best Practices

```python
# Production configuration
engine = TemplateEngine(
    template_dir="templates/",
    auto_reload=False,      # Disable for better performance
    cache_enabled=True,     # Enable caching
    strict_mode=True,       # Keep security enabled
)

# Pre-load all templates at startup
engine.load_templates()
```

### Template Organization

```
templates/
├── base.html           # Base layout
├── components/         # Reusable components
│   ├── _header.html
│   ├── _footer.html
│   └── _user_card.html
├── pages/             # Page templates
│   ├── home.html
│   ├── about.html
│   └── contact.html
└── emails/            # Email templates
    ├── welcome.html
    └── notification.html
```

### Caching Strategies

```python
# Template-level caching (built-in)
engine = TemplateEngine(template_dir="templates/", cache_enabled=True)

# Application-level caching
from functools import lru_cache

@lru_cache(maxsize=100)
def render_cached_template(template_name, context_hash):
    return engine.render(template_name, context)

# Use with caution - context must be hashable
```

## Integration Examples

### With Dependency Injection

```python
from velithon.di import Provide, ServiceContainer

def create_template_service(container: ServiceContainer):
    config = container.get("config")
    return TemplateEngine(
        template_dir=config.template_dir,
        auto_reload=config.debug,
        cache_enabled=not config.debug,
    )

@app.get("/")
async def home(templates: TemplateEngine = Provide(create_template_service)):
    return templates.render_response("home.html", {"title": "Home"})
```

### With Background Tasks

```python
from velithon.background import BackgroundTask

@app.post("/send-email")
async def send_email(email_data: dict):
    # Render email template
    html_content = engine.render("email/welcome.html", email_data)
    
    # Send email in background
    task = BackgroundTask(send_email_async, html_content, email_data["email"])
    
    return JSONResponse({"status": "sent"}, background=task)
```

### With Middleware

```python
from velithon.middleware import Middleware

class TemplateMiddleware:
    def __init__(self, app, template_engine):
        self.app = app
        self.engine = template_engine
    
    async def __call__(self, scope, protocol):
        # Add template engine to request scope
        scope["template_engine"] = self.engine
        await self.app(scope, protocol)

app.add_middleware(Middleware(TemplateMiddleware, engine))

@app.get("/")
async def home(request):
    engine = request.scope["template_engine"]
    return engine.render_response("home.html", {"title": "Home"})
```

## Testing Templates

### Unit Testing

```python
import pytest
from velithon.templates import TemplateEngine

class TestTemplates:
    def setup_method(self):
        self.engine = TemplateEngine("test_templates/")
    
    def test_simple_render(self):
        result = self.engine.render("simple.html", {"name": "Test"})
        assert "Hello Test!" in result
    
    def test_complex_context(self):
        context = {
            "user": {"name": "Alice"},
            "items": [1, 2, 3]
        }
        result = self.engine.render("complex.html", context)
        assert "Alice" in result
        assert "3" in result
```

### Integration Testing

```python
async def test_template_endpoint(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Welcome" in response.text
```

This template engine provides a powerful, secure, and high-performance solution for rendering HTML templates in Velithon applications. The Rust implementation ensures excellent performance while maintaining the familiar Handlebars syntax that developers love.
