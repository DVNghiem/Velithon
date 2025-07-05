# Getting Started

Welcome to Velithon! This section will guide you through everything you need to know to start building high-performance web applications with Velithon.

## 🎯 What You'll Learn

In this section, you'll discover:

<div class="grid cards" markdown>

-   **[Installation](installation.md)**
    
    Set up your development environment and install Velithon with all its dependencies

-   **[Quick Start](quick-start.md)**
    
    Build and run your first Velithon application in just a few minutes

-   **[First Application](first-application.md)**
    
    Create a more comprehensive application with routing, middleware, and responses

-   **[Project Structure](project-structure.md)**
    
    Learn the recommended project structure and best practices for organizing your code

</div>

## 📋 Prerequisites

Before you begin, make sure you have:

- **Python 3.10+** installed on your system
- Basic knowledge of **Python** and **async/await**
- Familiarity with **HTTP concepts** (requests, responses, status codes)
- A **text editor** or **IDE** (VS Code, PyCharm, etc.)

!!! tip "New to Async Python?"
    If you're new to asynchronous programming in Python, check out the [Python async/await documentation](https://docs.python.org/3/library/asyncio.html) before diving into Velithon.

## 🚀 Quick Overview

Velithon is designed to be intuitive and developer-friendly. Here's a taste of what you'll be building:

```python
from velithon import Velithon
from velithon.responses import JSONResponse

app = Velithon()

@app.get("/")
async def root():
    return {"message": "Welcome to Velithon!"}

@app.post("/items")
async def create_item(item: dict):
    # Process the item
    return JSONResponse({"created": item}, status_code=201)
```

## 📚 Learning Path

We recommend following the sections in order:

1. **Installation** - Get Velithon installed and ready
2. **Quick Start** - Your first "Hello World" application
3. **First Application** - A more realistic example with multiple features
4. **Project Structure** - Organize your code like a pro

Each section builds upon the previous one, so you'll gradually become proficient with all of Velithon's features.

## 🔄 What's Next?

After completing the Getting Started guide, you'll be ready to explore:

- **[First Application](first-application.md)** - Build a comprehensive real-world application
- **[Project Structure](project-structure.md)** - Best practices for organizing your code
- **[Advanced Examples](first-application.md)** - WebSockets, authentication, and more

Let's get started! 🚀

**[Install Velithon →](installation.md)**
