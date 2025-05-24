# File Uploads and Form Handling

Velithon provides comprehensive support for handling file uploads and form data through its built-in form parsing capabilities.

## Basic File Upload

```python
from velithon import Velithon
from velithon.params import File
from velithon.datastructures import UploadFile

app = Velithon()

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Read file content
    content = await file.read()
    
    # Get file information
    filename = file.filename
    content_type = file.content_type
    size = file.size
    
    # Process the file
    with open(f"uploads/{filename}", "wb") as f:
        f.write(content)
    
    return {"filename": filename, "size": size}
```

## Multiple File Uploads

```python
from typing import List

@app.post("/upload-multiple")
async def upload_multiple_files(files: List[UploadFile] = File(...)):
    uploaded_files = []
    
    for file in files:
        content = await file.read()
        with open(f"uploads/{file.filename}", "wb") as f:
            f.write(content)
        
        uploaded_files.append({
            "filename": file.filename,
            "size": file.size,
            "content_type": file.content_type
        })
    
    return {"uploaded_files": uploaded_files}
```

## Form Data with Files

```python
from velithon.params import Form

@app.post("/upload-with-data")
async def upload_with_data(
    title: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(...)
):
    # Process form data
    await file.read()
    
    return {
        "title": title,
        "description": description,
        "filename": file.filename
    }
```

## Advanced File Handling

```python
@app.post("/upload-advanced")
async def upload_advanced(file: UploadFile = File(...)):
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "Only image files allowed")
    
    # Validate file size (limit to 5MB)
    if file.size > 5 * 1024 * 1024:
        raise HTTPException(400, "File too large")
    
    # Stream file to disk for large files
    with open(f"uploads/{file.filename}", "wb") as f:
        while chunk := await file.read(1024):  # Read in chunks
            f.write(chunk)
    
    return {"message": "File uploaded successfully"}
```

## Form Parsing Configuration

The framework automatically handles multipart form parsing with configurable limits:

```python
# Form parsing happens automatically with these default limits:
# - max_files: 1000
# - max_fields: 1000  
# - max_part_size: 1MB per part

# These limits protect against malicious uploads
```

## File Upload Best Practices

1. **Validate file types**: Always check `content_type` and file extensions
2. **Limit file sizes**: Set reasonable size limits to prevent abuse
3. **Use streaming**: For large files, read in chunks to avoid memory issues
4. **Sanitize filenames**: Clean filename inputs to prevent directory traversal
5. **Store securely**: Don't store uploads in web-accessible directories

```python
import os
import uuid
from pathlib import Path

@app.post("/secure-upload")
async def secure_upload(file: UploadFile = File(...)):
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(400, "File type not allowed")
    
    # Generate secure filename
    file_extension = Path(file.filename).suffix
    secure_filename = f"{uuid.uuid4()}{file_extension}"
    
    # Ensure upload directory exists
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    # Save file
    file_path = upload_dir / secure_filename
    with open(file_path, "wb") as f:
        while chunk := await file.read(1024):
            f.write(chunk)
    
    return {
        "filename": secure_filename,
        "original_name": file.filename,
        "size": file.size
    }
```
