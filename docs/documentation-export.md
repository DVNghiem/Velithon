# Velithon Documentation Export Feature

Velithon now includes a comprehensive documentation export feature that automatically generates API documentation from your routes, type hints, and docstrings. This feature supports both Markdown and PDF export formats and provides extensive configuration options.

## Features

### ✨ **Comprehensive Information Extraction**
- **Route Information**: Automatically extracts all HTTP routes, methods, and paths
- **Type Hints**: Analyzes function parameter type annotations for precise documentation
- **Docstrings**: Parses function docstrings to extract descriptions, parameter documentation, and examples
- **Response Codes**: Intelligently infers response codes from docstrings and function implementations
- **Tags and Grouping**: Supports route grouping by tags for better organization

### 📋 **Export Formats**
- **Markdown**: Clean, readable documentation in Markdown format
- **PDF**: Professional-looking PDF documents with custom styling (requires weasyprint)
- **Both**: Export to both formats simultaneously

### ⚙️ **Configuration Options**
- **Custom Title and Description**: Set your API title, version, and description
- **Contact Information**: Include developer contact details
- **License Information**: Add license details to your documentation
- **Server Information**: Specify development and production server URLs
- **Route Filtering**: Include or exclude specific routes from documentation
- **Tag Grouping**: Organize routes by tags for better structure
- **Examples and Schemas**: Toggle inclusion of examples and detailed schemas

## Installation

The documentation export feature requires additional dependencies:

```bash
# For Markdown export only
pip install markdown jinja2

# For PDF export (full functionality)
pip install markdown jinja2 weasyprint
```

## Usage

### CLI Commands

#### Basic Export
```bash
velithon export-docs --app myapp:app --output api_docs
```

#### Advanced Configuration
```bash
velithon export-docs \
  --app myapp:app \
  --output comprehensive_docs \
  --format both \
  --title "My API Documentation" \
  --version "1.2.0" \
  --description "Complete API reference for My Application" \
  --contact-name "API Team" \
  --contact-email "api@mycompany.com" \
  --contact-url "https://mycompany.com/api" \
  --license-name "MIT" \
  --license-url "https://opensource.org/licenses/MIT" \
  --group-by-tags \
  --include-examples \
  --include-schemas
```

#### Route Filtering
```bash
# Exclude specific routes
velithon export-docs --app myapp:app --exclude-routes "/admin,/internal"

# Include only specific routes  
velithon export-docs --app myapp:app --include-only-routes "/users,/posts"
```

### CLI Options Reference

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--app` | TEXT | `simple_app:app` | Application module and instance (format: module:app_instance) |
| `--output` | TEXT | `api_docs` | Output file path (without extension) |
| `--format` | CHOICE | `markdown` | Output format: `markdown`, `pdf`, or `both` |
| `--title` | TEXT | `API Documentation` | Documentation title |
| `--version` | TEXT | `1.0.0` | API version |
| `--description` | TEXT | `Generated API Documentation` | API description |
| `--contact-name` | TEXT | `` | Contact name |
| `--contact-email` | TEXT | `` | Contact email |
| `--contact-url` | TEXT | `` | Contact URL |
| `--license-name` | TEXT | `` | License name |
| `--license-url` | TEXT | `` | License URL |
| `--exclude-routes` | TEXT | `` | Comma-separated list of route paths/names to exclude |
| `--include-only-routes` | TEXT | `` | Comma-separated list of route paths/names to include (excludes all others) |
| `--group-by-tags/--no-group-by-tags` | BOOL | `True` | Group routes by tags |
| `--include-examples/--no-include-examples` | BOOL | `True` | Include examples in documentation |
| `--include-schemas/--no-include-schemas` | BOOL | `True` | Include schemas in documentation |

### Programmatic Usage

You can also use the documentation generator programmatically:

```python
from velithon.documentation import DocumentationGenerator, DocumentationConfig
from myapp import app

# Create configuration
config = DocumentationConfig(
    title="My API Documentation",
    version="1.0.0", 
    description="Comprehensive API documentation",
    contact_name="API Team",
    contact_email="api@example.com",
    include_examples=True,
    group_by_tags=True,
    exclude_routes=["/admin", "/internal"]
)

# Generate documentation
generator = DocumentationGenerator(app, config)

# Export to files
generator.export_markdown("docs/api.md")
generator.export_pdf("docs/api.pdf")

# Or get content directly
markdown_content = generator.generate_markdown()
pdf_bytes = generator.generate_pdf()
```

## Writing Documentation-Friendly Code

To get the best results from the documentation generator, follow these best practices:

### Function Docstrings

Use comprehensive docstrings with clear sections:

```python
def create_user(name: str, email: str, age: int | None = None):
    """Create a new user in the system.
    
    This endpoint creates a new user account with the provided information.
    The email address must be unique across all users.
    
    Args:
        name: The user's full name (2-100 characters)
        email: The user's email address (must be valid and unique)
        age: The user's age in years (optional, 13-120 if provided)
        
    Returns:
        The created user object with assigned ID and timestamps.
        
    Raises:
        400: Invalid input data (name too short, invalid email, etc.)
        409: Email address already exists
        422: Validation error
        
    Example:
        Create a new user:
        ```json
        {
            "name": "John Doe",
            "email": "john@example.com", 
            "age": 30
        }
        ```
        
        Response:
        ```json
        {
            "id": 123,
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30,
            "created_at": "2023-01-01T12:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z"
        }
        ```
    """
    # Implementation here
    pass
```

### Route Definitions

Use descriptive route definitions with metadata:

```python
app = Velithon(routes=[
    Route(
        "/users", 
        create_user, 
        methods=["POST"],
        name="create_user",
        summary="Create a new user",
        description="Create a new user account in the system",
        tags=["Users", "Authentication"],
        include_in_schema=True
    ),
    Route(
        "/admin/users", 
        admin_create_user, 
        methods=["POST"],
        name="admin_create_user", 
        summary="Admin: Create user",
        description="Administrative endpoint for creating users",
        tags=["Admin", "Users"],
        include_in_schema=False  # Exclude from public docs
    )
])
```

### Type Hints

Use precise type hints for better documentation:

```python
from typing import Annotated, List
from velithon.params import Query, Path, Body

def get_users(
    page: Annotated[int, Query(description="Page number", ge=1)] = 1,
    limit: Annotated[int, Query(description="Items per page", ge=1, le=100)] = 10,
    search: Annotated[str | None, Query(description="Search term")] = None
) -> List[User]:
    """Get paginated list of users with optional search."""
    pass

def get_user(
    user_id: Annotated[int, Path(description="User ID")]
) -> User:
    """Get a specific user by ID.""" 
    pass
```

## Generated Documentation Structure

The generated documentation includes:

### 📄 **Header Section**
- API title and version
- Generation timestamp  
- API description
- Contact information
- License information
- Server URLs

### 🛣️ **API Endpoints**
For each route, the documentation includes:
- **HTTP Methods**: GET, POST, PUT, DELETE, etc.
- **Path**: The endpoint URL with parameter placeholders
- **Summary**: Brief description of the endpoint
- **Description**: Detailed explanation of functionality
- **Parameters**: Table with parameter details:
  - Name and type
  - Location (path, query, body, header, form, file)
  - Required/optional status
  - Description and constraints
- **Responses**: Expected response codes and descriptions
- **Examples**: Request/response examples when available

### 🏷️ **Organization**
- Routes grouped by tags (when enabled)
- Hierarchical structure for easy navigation
- Cross-references and links
- Professional styling (especially in PDF format)

## Examples

### Basic API Documentation

For a simple API like this:

```python
from velithon import Velithon
from velithon.routing import Route

def hello_world():
    """Say hello to the world."""
    return {"message": "Hello, World!"}

app = Velithon(routes=[
    Route("/hello", hello_world, methods=["GET"])
])
```

The generated documentation will include:

```markdown
# API Documentation

## API Endpoints

### GET /hello

**Summary:** Say hello to the world.

**Responses:**
- **200**: Successful response
```

### Complex API with Full Documentation

For a more complex API with comprehensive docstrings and type hints, the generator produces detailed documentation with:

- Complete parameter tables
- Response code documentation
- Request/response examples
- Type information
- Validation constraints
- Error descriptions

## Best Practices

### 1. **Consistent Docstring Format**
- Use the same docstring style throughout your application
- Include Args, Returns, and Raises sections
- Provide examples for complex endpoints

### 2. **Meaningful Route Names and Summaries**
- Use descriptive route names that reflect functionality
- Write clear, concise summaries
- Group related endpoints with tags

### 3. **Comprehensive Type Hints**
- Use modern Python type hint syntax (`str | None` instead of `Optional[str]`)
- Annotate all parameters with types
- Use Velithon's parameter annotations for validation rules

### 4. **Documentation Maintenance**
- Regenerate documentation as part of your CI/CD pipeline
- Keep docstrings up to date with code changes
- Review generated documentation regularly

### 5. **Route Organization**
- Use tags to group related endpoints
- Consider the logical flow when organizing routes
- Use `include_in_schema=False` for internal/debug endpoints

## Troubleshooting

### Common Issues

**"Missing dependencies" Error**
```bash
# Install required dependencies
pip install markdown jinja2

# For PDF support
pip install weasyprint
```

**"No routes found" Error**
- Verify your app instance is correctly specified
- Check that routes are properly registered with the Velithon application
- Ensure the module can be imported

**PDF Generation Fails**
- Install weasyprint: `pip install weasyprint`
- On some systems, you may need additional system dependencies for weasyprint

**Poor Documentation Quality**
- Add comprehensive docstrings to your endpoint functions
- Use type hints for all parameters
- Include examples in docstrings
- Use route metadata (summary, description, tags)

### Getting Help

If you encounter issues with the documentation export feature:

1. Check that all dependencies are installed
2. Verify your route definitions and docstrings
3. Try with a simple example first
4. Check the Velithon documentation for updates

## Future Enhancements

Planned improvements for the documentation export feature:

- **OpenAPI Integration**: Generate OpenAPI/Swagger specifications
- **Interactive Documentation**: HTML documentation with interactive API explorer
- **Custom Templates**: Support for custom documentation templates
- **Multi-language Support**: Generate documentation in multiple languages
- **API Testing**: Integration with testing frameworks for example generation
- **Schema Validation**: Automatic schema generation from Pydantic models

---

The documentation export feature makes it easy to maintain up-to-date, comprehensive API documentation that helps both developers and API consumers understand and use your Velithon applications effectively.
