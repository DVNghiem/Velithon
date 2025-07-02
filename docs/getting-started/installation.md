# Installation

This guide will help you install Velithon and set up your development environment.

## 📋 Requirements

Before installing Velithon, ensure your system meets these requirements:

- **Python 3.10 or higher**
- **pip** (Python package installer)
- **Operating System**: Linux, macOS, or Windows

!!! info "Python Version Support"
    Velithon supports Python 3.10, 3.11, 3.12, and 3.13. We recommend using the latest stable version for the best performance and security features.

## 🔧 Installation Methods

### Option 1: Install via pip (Recommended)

The easiest way to install Velithon is using pip:

```bash
pip install velithon
```

This will install Velithon and all its required dependencies.

### Option 2: Install from Source

For the latest development version:

```bash
# Clone the repository
git clone https://github.com/DVNghiem/Velithon.git
cd Velithon

# Install in development mode
pip install -e .
```

## 🐍 Virtual Environment Setup

We strongly recommend using a virtual environment to avoid dependency conflicts:

=== "venv (Built-in)"

    ```bash
    # Create virtual environment
    python -m venv velithon-env
    
    # Activate it
    # On Linux/macOS:
    source velithon-env/bin/activate
    # On Windows:
    velithon-env\Scripts\activate
    
    # Install Velithon
    pip install velithon
    ```

=== "conda"

    ```bash
    # Create conda environment
    conda create -n velithon-env python=3.12
    
    # Activate it
    conda activate velithon-env
    
    # Install Velithon
    pip install velithon
    ```

=== "poetry"

    ```bash
    # Initialize new project
    poetry new my-velithon-app
    cd my-velithon-app
    
    # Add Velithon
    poetry add velithon
    
    # Activate shell
    poetry shell
    ```

## ✅ Verify Installation

After installation, verify that Velithon is working correctly:

### 1. Check Version

```bash
python -c "import velithon; print(velithon.__version__)"
```

### 2. Test CLI

```bash
velithon --help
```

You should see the Velithon CLI help message.

### 3. Create Test Application

Create a file named `test_app.py`:

```python title="test_app.py"
from velithon import Velithon
from velithon.responses import JSONResponse

app = Velithon()

@app.get("/")
async def root():
    return JSONResponse({"message": "Velithon is working!"})

@app.get("/health")
async def health_check():
    return JSONResponse({"status": "healthy"})
```

Run the application:

```bash
velithon run --app test_app:app
```

Open your browser and visit `http://127.0.0.1:8000`. You should see:

```json
{"message": "Velithon is working!"}
```

## 🔧 Development Tools (Optional)

For a better development experience, consider installing these additional tools:

### Code Formatting and Linting

```bash
pip install black isort flake8 mypy
```

### Testing Framework

```bash
pip install pytest pytest-asyncio httpx
```

### Development Server with Auto-reload

Velithon uses Granian as its RSGI server, which is already included:

## 🐳 Docker Setup (Optional)

If you prefer using Docker:

```dockerfile title="Dockerfile"
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["velithon", "run", "--app", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml title="docker-compose.yml"
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    environment:
      - VELITHON_ENV=development
```

## 📦 Core Dependencies

Velithon comes with these core dependencies:

- **[Granian](https://github.com/emmett-framework/granian)** - High-performance RSGI server
- **[Pydantic](https://pydantic-docs.helpmanual.io/)** - Data validation and serialization  
- **[orjson](https://github.com/ijl/orjson)** - Fast JSON serialization
- **[python-multipart](https://andrew-d.github.io/python-multipart/)** - File upload support
- **[Jinja2](https://jinja.palletsprojects.com/)** - Template engine
- **[msgpack](https://msgpack.org/)** - Efficient binary serialization
- **[pydash](https://pydash.readthedocs.io/)** - Utility library
- **[zeroconf](https://python-zeroconf.readthedocs.io/)** - Service discovery
- **[python-consul](https://python-consul.readthedocs.io/)** - Consul integration
- **[markdown](https://python-markdown.github.io/)** - Markdown processing
- **[weasyprint](https://weasyprint.org/)** - PDF generation

## 🚨 Troubleshooting

### Common Issues

!!! failure "ImportError: No module named 'velithon'"
    
    **Solution**: Make sure you're in the correct virtual environment and Velithon is installed:
    ```bash
    pip list | grep velithon
    ```

!!! failure "Command 'velithon' not found"
    
    **Solution**: The CLI might not be in your PATH. Try:
    ```bash
    python -m velithon --help
    ```

!!! failure "Permission denied on Linux/macOS"
    
    **Solution**: Use `--user` flag or virtual environment:
    ```bash
    pip install --user velithon
    ```

### Getting Help

- **GitHub Issues**: [Report bugs](https://github.com/DVNghiem/Velithon/issues)
- **Discussions**: [Community discussions](https://github.com/DVNghiem/Velithon/discussions)
- **Documentation**: You're reading it! 📚

## ✨ What's Next?

Now that you have Velithon installed, let's build your first application!

**[Quick Start Guide →](quick-start.md)**
