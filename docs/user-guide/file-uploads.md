# File Uploads

Velithon provides comprehensive support for handling file uploads and form data through its built-in form parsing capabilities with automatic multipart parsing, security features, and performance optimizations.

## Overview

Velithon's file upload system features:
- **Automatic multipart parsing** with configurable limits
- **Memory-efficient streaming** for large files
- **Built-in security** with file validation
- **Type safety** with full typing support
- **Background processing** integration
- **Production-ready** with proper error handling

## Basic File Upload

### Single File Upload

```python
from velithon import Velithon
from velithon.params import File
from velithon.datastructures import UploadFile
from velithon.responses import JSONResponse

app = Velithon()

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Read file content
    content = await file.read()
    
    # Get file information
    filename = file.filename
    content_type = file.content_type
    size = file.size
    
    # Save the file
    with open(f"uploads/{filename}", "wb") as f:
        f.write(content)
    
    return JSONResponse({
        "filename": filename,
        "size": size,
        "content_type": content_type
    })
```

### File Properties

```python
@app.post("/file-info")
async def file_info(file: UploadFile = File(...)):
    info = {
        "filename": file.filename,           # Original filename
        "content_type": file.content_type,   # MIME type
        "size": file.size,                   # File size in bytes
        "headers": dict(file.headers),       # All file headers
    }
    
    # Read file content
    content = await file.read()
    info["content_preview"] = content[:100].decode('utf-8', errors='ignore')
    
    # Reset file position for further reading
    await file.seek(0)
    
    return JSONResponse(info)
```

## Multiple File Uploads

### List of Files

```python
from typing import List

@app.post("/upload-multiple")
async def upload_multiple_files(files: List[UploadFile] = File(...)):
    uploaded_files = []
    
    for file in files:
        # Process each file
        content = await file.read()
        
        # Save file
        file_path = f"uploads/{file.filename}"
        with open(file_path, "wb") as f:
            f.write(content)
        
        uploaded_files.append({
            "filename": file.filename,
            "size": file.size,
            "content_type": file.content_type,
            "saved_path": file_path
        })
    
    return JSONResponse({
        "uploaded_files": uploaded_files,
        "total_count": len(uploaded_files)
    })
```

### Optional Multiple Files

```python
@app.post("/upload-optional")
async def upload_optional_files(
    files: List[UploadFile] = File(default=[])
):
    if not files:
        return JSONResponse({"message": "No files uploaded"})
    
    results = []
    for file in files:
        # Process files...
        results.append({"filename": file.filename, "size": file.size})
    
    return JSONResponse({"files": results})
```

## Form Data with Files

### Mixed Form Data

```python
from velithon.params import Form

@app.post("/upload-with-data")
async def upload_with_data(
    title: str = Form(...),
    description: str = Form(None),
    category: str = Form("general"),
    file: UploadFile = File(...)
):
    # Process form data and file
    content = await file.read()
    
    # Create record
    record = {
        "title": title,
        "description": description,
        "category": category,
        "file_info": {
            "filename": file.filename,
            "size": file.size,
            "content_type": file.content_type
        }
    }
    
    # Save file
    file_path = f"uploads/{category}/{file.filename}"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)
    
    return JSONResponse(record)
```

### Complex Form Structure

```python
@app.post("/upload-complex")
async def upload_complex_form(
    user_id: int = Form(...),
    tags: str = Form(""),  # Comma-separated tags
    is_public: bool = Form(False),
    files: List[UploadFile] = File(...),
    thumbnail: UploadFile = File(None)  # Optional thumbnail
):
    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
    
    # Process main files
    main_files = []
    for file in files:
        content = await file.read()
        # Process and save...
        main_files.append({"filename": file.filename, "size": file.size})
    
    # Process optional thumbnail
    thumbnail_info = None
    if thumbnail:
        thumb_content = await thumbnail.read()
        thumbnail_info = {
            "filename": thumbnail.filename,
            "size": thumbnail.size
        }
    
    return JSONResponse({
        "user_id": user_id,
        "tags": tag_list,
        "is_public": is_public,
        "main_files": main_files,
        "thumbnail": thumbnail_info
    })
```

## Advanced File Handling

### Streaming Large Files

```python
import aiofiles

@app.post("/upload-large")
async def upload_large_file(file: UploadFile = File(...)):
    # Validate file type
    if not file.content_type.startswith("video/"):
        raise HTTPException(400, "Only video files allowed")
    
    # Validate file size (limit to 100MB)
    if file.size > 100 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 100MB)")
    
    # Stream file to disk for large files
    file_path = f"uploads/videos/{file.filename}"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    async with aiofiles.open(file_path, "wb") as f:
        while chunk := await file.read(8192):  # Read in 8KB chunks
            await f.write(chunk)
    
    return JSONResponse({
        "message": "Large file uploaded successfully",
        "filename": file.filename,
        "path": file_path
    })
```

### File Validation

```python
import magic
from pathlib import Path

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.txt', '.docx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

async def validate_file(file: UploadFile) -> bool:
    """Comprehensive file validation"""
    
    # Check filename
    if not file.filename:
        raise HTTPException(400, "Filename is required")
    
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type {file_ext} not allowed")
    
    # Check file size
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large")
    
    # Check MIME type
    content_start = await file.read(1024)
    await file.seek(0)  # Reset position
    
    # Use python-magic for content validation
    detected_type = magic.from_buffer(content_start, mime=True)
    if not detected_type.startswith(('image/', 'application/pdf', 'text/')):
        raise HTTPException(400, "Invalid file content")
    
    return True

@app.post("/upload-validated")
async def upload_validated_file(file: UploadFile = File(...)):
    # Validate file
    await validate_file(file)
    
    # Process validated file
    content = await file.read()
    
    # Generate secure filename
    secure_filename = f"{uuid.uuid4()}{Path(file.filename).suffix}"
    file_path = f"uploads/validated/{secure_filename}"
    
    # Save file
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)
    
    return JSONResponse({
        "message": "File validated and uploaded",
        "original_name": file.filename,
        "secure_filename": secure_filename,
        "size": file.size
    })
```

## Form Parsing Configuration

### Default Limits

Velithon automatically handles multipart form parsing with these default limits:

```python
# Default form parsing limits (automatically applied)
# - max_files: 1000 files per request
# - max_fields: 1000 form fields per request  
# - max_part_size: 1MB per individual part

# These limits protect against malicious uploads
```

### Custom Parsing Limits

```python
from velithon.requests import Request

@app.post("/upload-custom-limits")
async def upload_with_custom_limits(request: Request):
    # Custom form parsing with specific limits
    form = await request.form(
        max_files=50,           # Allow up to 50 files
        max_fields=100,         # Allow up to 100 form fields
        max_part_size=5*1024*1024  # 5MB per part
    )
    
    files = []
    fields = {}
    
    for name, value in form.items():
        if isinstance(value, UploadFile):
            files.append({
                "field_name": name,
                "filename": value.filename,
                "size": value.size
            })
        else:
            fields[name] = value
    
    return JSONResponse({
        "files": files,
        "fields": fields,
        "total_files": len(files)
    })
```

## File Upload Best Practices

### Security Best Practices

```python
import os
import uuid
from pathlib import Path

# Secure file upload configuration
UPLOAD_DIR = Path("uploads")
ALLOWED_TYPES = ["image/jpeg", "image/png", "image/gif", "application/pdf"]
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

@app.post("/secure-upload")
async def secure_upload(file: UploadFile = File(...)):
    # 1. Validate file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "File type not allowed")
    
    # 2. Validate file size
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large")
    
    # 3. Generate secure filename (prevent directory traversal)
    file_extension = Path(file.filename).suffix
    secure_filename = f"{uuid.uuid4()}{file_extension}"
    
    # 4. Ensure upload directory exists and is secure
    upload_dir = UPLOAD_DIR / "secure"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # 5. Save file outside web root
    file_path = upload_dir / secure_filename
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # 6. Store metadata securely
    file_record = {
        "id": str(uuid.uuid4()),
        "original_name": file.filename,
        "secure_filename": secure_filename,
        "size": file.size,
        "content_type": file.content_type,
        "upload_time": datetime.now().isoformat()
    }
    
    return JSONResponse({
        "file_id": file_record["id"],
        "message": "File uploaded securely",
        "size": file.size
    })
```

### Performance Optimization

```python
from velithon.background import BackgroundTask
import asyncio

@app.post("/upload-optimized")
async def upload_optimized(
    files: List[UploadFile] = File(...),
    process_async: bool = Form(True)
):
    """Optimized file upload with background processing"""
    
    upload_results = []
    background_tasks = []
    
    for file in files:
        # Quick validation
        if file.size > 50 * 1024 * 1024:  # 50MB limit
            continue
        
        # Generate secure filename
        secure_name = f"{uuid.uuid4()}{Path(file.filename).suffix}"
        file_path = f"uploads/{secure_name}"
        
        # Save file quickly
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        upload_results.append({
            "filename": secure_name,
            "original_name": file.filename,
            "size": file.size
        })
        
        # Schedule background processing if requested
        if process_async:
            background_tasks.append(
                BackgroundTask(process_file_async, file_path, file.content_type)
            )
    
    # Execute background tasks
    if background_tasks:
        async def run_background():
            await asyncio.gather(
                *[task() for task in background_tasks],
                return_exceptions=True
            )
        
        await run_background()
    
    return JSONResponse({
        "uploaded_files": upload_results,
        "background_processing": process_async
    })

async def process_file_async(file_path: str, content_type: str):
    """Background file processing"""
    if content_type.startswith("image/"):
        # Generate thumbnails, optimize images, etc.
        await generate_thumbnail(file_path)
    elif content_type == "application/pdf":
        # Extract text, generate preview, etc.
        await extract_pdf_text(file_path)
```

### Memory Management

```python
@app.post("/upload-memory-efficient")
async def upload_memory_efficient(file: UploadFile = File(...)):
    """Memory-efficient file handling for large uploads"""
    
    # Create temporary file path
    temp_path = f"temp/{uuid.uuid4()}.tmp"
    final_path = f"uploads/{file.filename}"
    
    try:
        # Stream file to temporary location
        os.makedirs("temp", exist_ok=True)
        with open(temp_path, "wb") as temp_file:
            total_size = 0
            while True:
                chunk = await file.read(8192)  # 8KB chunks
                if not chunk:
                    break
                
                temp_file.write(chunk)
                total_size += len(chunk)
                
                # Check size limit during streaming
                if total_size > 100 * 1024 * 1024:  # 100MB
                    raise HTTPException(400, "File too large")
        
        # Move to final location after successful upload
        os.makedirs(os.path.dirname(final_path), exist_ok=True)
        os.rename(temp_path, final_path)
        
        return JSONResponse({
            "message": "File uploaded successfully",
            "filename": file.filename,
            "size": total_size
        })
        
    except Exception as e:
        # Clean up temporary file on error
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e
```

## HTML Form Examples

### Single File Upload Form

```html
<!DOCTYPE html>
<html>
<head>
    <title>File Upload</title>
</head>
<body>
    <h1>Upload a File</h1>
    
    <form action="/upload" method="post" enctype="multipart/form-data">
        <div>
            <label for="file">Choose file:</label>
            <input type="file" name="file" id="file" required>
        </div>
        
        <div>
            <button type="submit">Upload</button>
        </div>
    </form>
</body>
</html>
```

### Multiple Files with Form Data

```html
<form action="/upload-with-data" method="post" enctype="multipart/form-data">
    <div>
        <label for="title">Title:</label>
        <input type="text" name="title" id="title" required>
    </div>
    
    <div>
        <label for="description">Description:</label>
        <textarea name="description" id="description"></textarea>
    </div>
    
    <div>
        <label for="category">Category:</label>
        <select name="category" id="category">
            <option value="images">Images</option>
            <option value="documents">Documents</option>
            <option value="videos">Videos</option>
        </select>
    </div>
    
    <div>
        <label for="files">Files:</label>
        <input type="file" name="files" id="files" multiple>
    </div>
    
    <div>
        <label for="thumbnail">Thumbnail (optional):</label>
        <input type="file" name="thumbnail" id="thumbnail" accept="image/*">
    </div>
    
    <div>
        <label>
            <input type="checkbox" name="is_public" value="true">
            Make public
        </label>
    </div>
    
    <button type="submit">Upload Files</button>
</form>
```

## Error Handling

### Common Upload Errors

```python
from velithon.exceptions import HTTPException, MultiPartException

@app.post("/upload-with-errors")
async def upload_with_error_handling(file: UploadFile = File(...)):
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(400, "No file provided")
        
        if file.size > 10 * 1024 * 1024:
            raise HTTPException(413, "File too large")
        
        # Process file
        content = await file.read()
        
        # Save file
        with open(f"uploads/{file.filename}", "wb") as f:
            f.write(content)
        
        return JSONResponse({"status": "success", "filename": file.filename})
        
    except MultiPartException as e:
        return JSONResponse(
            {"error": "Multipart form error", "detail": str(e)},
            status_code=400
        )
    except HTTPException as e:
        return JSONResponse(
            {"error": "Upload error", "detail": str(e)},
            status_code=e.status_code
        )
    except Exception as e:
        return JSONResponse(
            {"error": "Internal server error", "detail": str(e)},
            status_code=500
        )
```

### Error Handling

```python
from velithon.exceptions import MultiPartException

@app.post("/upload-with-error-handling")
async def upload_with_error_handling(file: UploadFile):
    try:
        # Validate file
        if not file.filename:
            raise ValueError("No file provided")
        
        if file.size > 10 * 1024 * 1024:  # 10MB
            raise ValueError("File too large")
        
        # Process file
        content = await file.read()
        return {"filename": file.filename, "size": len(content)}
        
    except ValueError as e:
        return JSONResponse(
            content={
                "error": "File upload error",
                "message": str(e)
            },
            status_code=400
        )
    except MultiPartException as e:
        return JSONResponse(
            content={
                "error": "File upload error", 
                "message": "Invalid multipart form data",
                "details": str(e)
            },
            status_code=400
        )
```
```

## Testing File Uploads

### Unit Testing

```python
import pytest
from velithon.testing import TestClient
from io import BytesIO

def test_file_upload():
    client = TestClient(app)
    
    # Create test file
    test_file = BytesIO(b"test file content")
    test_file.name = "test.txt"
    
    # Test upload
    response = client.post(
        "/upload",
        files={"file": ("test.txt", test_file, "text/plain")}
    )
    
    assert response.status_code == 200
    assert response.json()["filename"] == "test.txt"

def test_multiple_file_upload():
    client = TestClient(app)
    
    files = [
        ("files", ("file1.txt", BytesIO(b"content 1"), "text/plain")),
        ("files", ("file2.txt", BytesIO(b"content 2"), "text/plain")),
    ]
    
    response = client.post("/upload-multiple", files=files)
    
    assert response.status_code == 200
    assert len(response.json()["uploaded_files"]) == 2
```

## Production Considerations

### Web Server Configuration

**Nginx configuration** for file uploads:

```nginx
server {
    client_max_body_size 100M;  # Allow large uploads
    
    location /upload {
        proxy_pass http://backend;
        proxy_request_buffering off;  # Stream uploads
        proxy_read_timeout 300;       # Longer timeout for uploads
    }
}
```

### Monitoring and Logging

```python
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@app.post("/upload-monitored")
async def upload_monitored(file: UploadFile = File(...)):
    start_time = datetime.now()
    
    try:
        # Log upload start
        logger.info(f"Upload started: {file.filename}, size: {file.size}")
        
        # Process file
        content = await file.read()
        
        # Save file
        file_path = f"uploads/{file.filename}"
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Log success
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Upload completed: {file.filename}, duration: {duration}s")
        
        return JSONResponse({
            "status": "success",
            "filename": file.filename,
            "duration": duration
        })
        
    except Exception as e:
        # Log error
        logger.error(f"Upload failed: {file.filename}, error: {str(e)}")
        raise
```

Velithon's file upload system provides a comprehensive, secure, and performant solution for handling file uploads in web applications. The automatic multipart parsing, built-in security features, and flexible API make it easy to build robust file upload functionality.
