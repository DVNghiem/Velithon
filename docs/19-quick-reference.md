# Quick Reference

## File Upload Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `File(...)` | Required file upload | `file: UploadFile = File(...)` |
| `File(None)` | Optional file upload | `file: UploadFile = File(None)` |
| `List[UploadFile]` | Multiple files | `files: List[UploadFile] = File(...)` |

## Background Task Functions

| Function | Description | Example |
|----------|-------------|---------|
| `BackgroundTask(func, *args, **kwargs)` | Single task | `BackgroundTask(send_email, email, message)` |
| `BackgroundTasks(max_concurrent=10)` | Task collection | `tasks = BackgroundTasks(max_concurrent=5)` |
| `tasks.add_task(func, *args, **kwargs)` | Add task | `tasks.add_task(process_data, data)` |
| `await tasks(continue_on_error=True)` | Execute tasks | `await tasks(continue_on_error=False)` |

## File Upload Properties

| Property | Type | Description |
|----------|------|-------------|
| `file.filename` | `str` | Original filename |
| `file.content_type` | `str` | MIME type |
| `file.size` | `int` | File size in bytes |
| `await file.read()` | `bytes` | Read entire file |
| `await file.read(size)` | `bytes` | Read chunk |
| `await file.seek(position)` | `None` | Set file position |

## Form Data Limits

| Setting | Default | Description |
|---------|---------|-------------|
| `max_files` | 1000 | Maximum number of files |
| `max_fields` | 1000 | Maximum form fields |
| `max_part_size` | 1MB | Maximum size per part |

## HTTP Status Codes

| Code | Constant | Description |
|------|----------|-------------|
| 200 | `HTTP_200_OK` | Success |
| 201 | `HTTP_201_CREATED` | Created |
| 400 | `HTTP_400_BAD_REQUEST` | Bad Request |
| 401 | `HTTP_401_UNAUTHORIZED` | Unauthorized |
| 403 | `HTTP_403_FORBIDDEN` | Forbidden |
| 404 | `HTTP_404_NOT_FOUND` | Not Found |
| 500 | `HTTP_500_INTERNAL_SERVER_ERROR` | Internal Server Error |

## Common Decorators

| Decorator | Description | Example |
|-----------|-------------|---------|
| `@app.get()` | GET endpoint | `@app.get("/users")` |
| `@app.post()` | POST endpoint | `@app.post("/users")` |
| `@app.put()` | PUT endpoint | `@app.put("/users/{id}")` |
| `@app.delete()` | DELETE endpoint | `@app.delete("/users/{id}")` |
| `@app.websocket()` | WebSocket endpoint | `@app.websocket("/ws")` |
| `@inject` | Dependency injection | `@inject` |

## CLI Commands

| Command | Description | Example |
|---------|-------------|---------|
| `velithon run` | Start server | `velithon run --app main:app` |
| `--host` | Set host | `--host 0.0.0.0` |
| `--port` | Set port | `--port 8080` |
| `--reload` | Auto-reload | `--reload` |
| `--workers` | Worker processes | `--workers 4` |
| `--log-level` | Log level | `--log-level DEBUG` |
