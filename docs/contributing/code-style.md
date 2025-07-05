# Code Style Guidelines

This document outlines the coding standards and style guidelines for contributing to Velithon.

## Overview

Consistent code style makes the codebase easier to read, understand, and maintain. We use automated tools to enforce most style rules.

## Python Code Style

### Formatting Tools

We use these tools for Python code formatting:

- **Black** - Code formatter
- **isort** - Import sorter  
- **Ruff** - Linter and code checker

### Running Style Tools

```bash
# Format code
poetry run black .
poetry run isort .

# Check for style issues
poetry run ruff check

# Fix auto-fixable issues
poetry run ruff check --fix
```

### Style Rules

#### 1. Line Length
- Maximum line length: **88 characters** (Black default)
- For very long lines, prefer readability over strict adherence

#### 2. Imports
```python
# Standard library imports first
import asyncio
import datetime
from typing import Optional, List

# Third-party imports second
import pydantic
from granian import Granian

# Local imports last
from velithon.application import Velithon
from velithon.responses import JSONResponse
```

#### 3. String Quotes
- Use **double quotes** for strings by default
- Use single quotes for strings containing double quotes
- Use triple double quotes for docstrings

```python
# Good
message = "Hello, world!"
sql = 'SELECT * FROM users WHERE name = "John"'

# Bad
message = 'Hello, world!'
```

#### 4. Function and Variable Names
- Use **snake_case** for functions and variables
- Use **UPPER_CASE** for constants
- Use **PascalCase** for classes

```python
# Good
def get_user_by_id(user_id: int) -> User:
    pass

MAX_CONNECTIONS = 100

class UserService:
    pass

# Bad
def getUserById(userId: int) -> User:
    pass

maxConnections = 100
```

#### 5. Type Hints
- Always use type hints for function parameters and return values
- Use modern typing syntax (Python 3.10+)

```python
# Good
def process_items(items: list[str]) -> dict[str, int]:
    return {item: len(item) for item in items}

# For older Python compatibility in public APIs
from typing import List, Dict

def process_items(items: List[str]) -> Dict[str, int]:
    return {item: len(item) for item in items}
```

#### 6. Docstrings
- Use **Google-style docstrings**
- Include type information in docstrings for complex types

```python
def create_user(user_data: UserCreate, db: Database) -> User:
    """Create a new user in the database.
    
    Args:
        user_data: User information to create
        db: Database connection instance
        
    Returns:
        The created user with assigned ID
        
    Raises:
        ValidationError: If user data is invalid
        DatabaseError: If database operation fails
    """
    pass
```

## Rust Code Style

### Formatting Tools

- **rustfmt** - Official Rust formatter
- **clippy** - Rust linter

### Running Rust Tools

```bash
# Format Rust code
cargo fmt

# Check for issues
cargo clippy

# Run with all warnings
cargo clippy -- -W clippy::all
```

### Rust Style Rules

#### 1. Follow Rust Standard Style
- Use the default `rustfmt` configuration
- Follow [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/)

#### 2. Naming Conventions
```rust
// Snake case for functions and variables
fn process_request() -> Result<Response, Error> {
    let user_id = get_current_user_id();
    // ...
}

// Pascal case for types
struct UserRequest {
    name: String,
    email: String,
}

// Upper snake case for constants
const MAX_RETRY_ATTEMPTS: usize = 3;
```

#### 3. Error Handling
```rust
// Use Result types for fallible operations
fn parse_config(path: &str) -> Result<Config, ConfigError> {
    // Implementation
}

// Use ? operator for error propagation
fn process_file(path: &str) -> Result<String, Error> {
    let content = std::fs::read_to_string(path)?;
    let processed = process_content(&content)?;
    Ok(processed)
}
```

## Configuration Files

### Black Configuration (pyproject.toml)
```toml
[tool.black]
line-length = 88
target-version = ['py310']
include = '\.pyi?$'
extend-exclude = '''
/(
  \.eggs
  | \.git
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
  | target
)/
'''
```

### isort Configuration (pyproject.toml)
```toml
[tool.isort]
profile = "black"
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
line_length = 88
known_first_party = ["velithon"]
```

### Ruff Configuration (ruff.toml)
```toml
line-length = 88
target-version = "py310"

[lint]
select = [
    "E",  # pycodestyle errors
    "W",  # pycodestyle warnings
    "F",  # pyflakes
    "I",  # isort
    "B",  # flake8-bugbear
    "C4", # flake8-comprehensions
    "UP", # pyupgrade
]
ignore = [
    "E501",  # line too long (handled by black)
    "B008",  # do not perform function calls in argument defaults
]

[lint.per-file-ignores]
"tests/*" = ["F401", "F811"]  # Allow unused imports in tests
```

## Git Commit Guidelines

### Commit Message Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, missing semicolons, etc.)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **chore**: Maintenance tasks

### Examples
```bash
# Good commit messages
feat(auth): add JWT token validation
fix(routing): handle empty path parameters correctly
docs(api): update authentication examples
refactor(di): simplify container registration
test(middleware): add integration tests for CORS

# Bad commit messages
fix bug
update code
changes
```

## Code Review Guidelines

### For Authors
1. **Self-review** your code before submitting
2. **Write clear commit messages** and PR descriptions
3. **Add tests** for new functionality
4. **Update documentation** for API changes
5. **Run all checks** locally before pushing

### For Reviewers
1. **Be constructive** and helpful in feedback
2. **Focus on code quality** and maintainability
3. **Check for edge cases** and error handling
4. **Verify tests** cover the changes
5. **Suggest improvements** rather than just pointing out problems

## Pre-commit Hooks

We recommend using pre-commit hooks to catch issues early:

```bash
# Install pre-commit
poetry add --group dev pre-commit

# Install hooks
poetry run pre-commit install

# Run hooks manually
poetry run pre-commit run --all-files
```

### .pre-commit-config.yaml
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
```

## IDE Integration

### VS Code Settings
```json
{
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.sortImports.args": ["--profile", "black"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

## Common Patterns

### Error Handling
```python
# Good: Specific exceptions
try:
    user = get_user(user_id)
except UserNotFoundError:
    raise HTTPException(status_code=404, detail="User not found")
except DatabaseConnectionError:
    raise HTTPException(status_code=500, detail="Database unavailable")

# Bad: Catching all exceptions
try:
    user = get_user(user_id)
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

### Async/Await
```python
# Good: Proper async patterns
async def get_user_data(user_id: int) -> UserData:
    user = await get_user(user_id)
    profile = await get_user_profile(user_id)
    return UserData(user=user, profile=profile)

# Bad: Blocking calls in async functions
async def get_user_data(user_id: int) -> UserData:
    user = blocking_get_user(user_id)  # Blocks the event loop
    return user
```

### Resource Management
```python
# Good: Use context managers
async with database.transaction():
    user = await create_user(user_data)
    await create_user_profile(user.id, profile_data)

# Good: Proper cleanup
try:
    connection = await get_connection()
    result = await connection.execute(query)
    return result
finally:
    await connection.close()
```

## Enforcement

These style guidelines are enforced through:

1. **Automated tools** (Black, isort, Ruff)
2. **CI/CD pipeline** checks
3. **Pre-commit hooks**
4. **Code review** process

By following these guidelines, you help maintain a consistent and high-quality codebase that's easy for all contributors to work with.
