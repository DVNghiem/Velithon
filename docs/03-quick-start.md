# Quick Start

## Basic Application

Create a simple web application:

```python
from velithon import Velithon
from velithon.responses import JSONResponse

app = Velithon()

@app.get("/")
async def root():
    return JSONResponse({"message": "Hello, World!"})

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    return JSONResponse({"item_id": item_id})
```

## Run with CLI

```bash
velithon run --app main:app --host 0.0.0.0 --port 8000
```
