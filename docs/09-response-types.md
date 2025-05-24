# Response Types

## Built-in Response Types

```python
from velithon.responses import (
    JSONResponse,
    PlainTextResponse,
    HTMLResponse,
    RedirectResponse,
    FileResponse,
    StreamingResponse
)

@app.get("/json")
async def json_response():
    return JSONResponse({"message": "Hello JSON"})

@app.get("/text")
async def text_response():
    return PlainTextResponse("Hello Text")

@app.get("/html")
async def html_response():
    return HTMLResponse("<h1>Hello HTML</h1>")

@app.get("/redirect")
async def redirect_response():
    return RedirectResponse("/json")

@app.get("/file")
async def file_response():
    return FileResponse("path/to/file.pdf")

@app.get("/stream")
async def streaming_response():
    def generate():
        for i in range(100):
            yield f"data chunk {i}\n"
    
    return StreamingResponse(generate(), media_type="text/plain")
```

## Custom Response Status and Headers

```python
@app.get("/custom")
async def custom_response():
    return JSONResponse(
        content={"message": "Created"},
        status_code=201,
        headers={"X-Custom-Header": "value"}
    )
```
