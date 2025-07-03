# File Upload Example

This example demonstrates how to handle file uploads in Velithon applications.

## Basic File Upload

```python
from velithon import Velithon, Request
from velithon.responses import JSONResponse
import aiofiles
import os
from pathlib import Path

app = Velithon()

# Create uploads directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.post("/upload")
async def upload_file(request: Request):
    """Handle single file upload."""
    form = await request.form()
    file = form.get("file")
    
    if not file or not file.filename:
        return JSONResponse(
            {"error": "No file provided"},
            status_code=400
        )
    
    # Save file
    file_path = UPLOAD_DIR / file.filename
    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)
    
    return JSONResponse({
        "message": "File uploaded successfully",
        "filename": file.filename,
        "size": len(content)
    })

@app.post("/upload/multiple")
async def upload_multiple_files(request: Request):
    """Handle multiple file uploads."""
    form = await request.form()
    files = form.getlist("files")
    
    if not files:
        return JSONResponse(
            {"error": "No files provided"},
            status_code=400
        )
    
    uploaded_files = []
    
    for file in files:
        if file.filename:
            file_path = UPLOAD_DIR / file.filename
            async with aiofiles.open(file_path, "wb") as f:
                content = await file.read()
                await f.write(content)
                
            uploaded_files.append({
                "filename": file.filename,
                "size": len(content)
            })
    
    return JSONResponse({
        "message": f"Uploaded {len(uploaded_files)} files",
        "files": uploaded_files
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## File Upload with Validation

```python
from velithon import Velithon, Request
from velithon.responses import JSONResponse
import aiofiles
import os
from pathlib import Path
import mimetypes

app = Velithon()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Allowed file types and maximum size
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".pdf", ".txt", ".doc", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@app.post("/upload/validated")
async def upload_with_validation(request: Request):
    """Handle file upload with validation."""
    form = await request.form()
    file = form.get("file")
    
    if not file or not file.filename:
        return JSONResponse(
            {"error": "No file provided"},
            status_code=400
        )
    
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return JSONResponse(
            {"error": f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"},
            status_code=400
        )
    
    # Read file content to check size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return JSONResponse(
            {"error": f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"},
            status_code=400
        )
    
    # Generate safe filename
    safe_filename = f"{int(time.time())}_{file.filename}"
    file_path = UPLOAD_DIR / safe_filename
    
    # Save file
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)
    
    return JSONResponse({
        "message": "File uploaded successfully",
        "filename": safe_filename,
        "original_filename": file.filename,
        "size": len(content),
        "content_type": file.content_type
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Image Upload with Processing

```python
from velithon import Velithon, Request
from velithon.responses import JSONResponse
import aiofiles
from pathlib import Path
from PIL import Image
import io
import time

app = Velithon()

UPLOAD_DIR = Path("uploads")
THUMBNAIL_DIR = Path("thumbnails")
UPLOAD_DIR.mkdir(exist_ok=True)
THUMBNAIL_DIR.mkdir(exist_ok=True)

@app.post("/upload/image")
async def upload_image(request: Request):
    """Handle image upload with thumbnail generation."""
    form = await request.form()
    file = form.get("image")
    
    if not file or not file.filename:
        return JSONResponse(
            {"error": "No image provided"},
            status_code=400
        )
    
    # Check if file is an image
    if not file.content_type.startswith("image/"):
        return JSONResponse(
            {"error": "File must be an image"},
            status_code=400
        )
    
    content = await file.read()
    
    # Generate filenames
    timestamp = int(time.time())
    file_ext = Path(file.filename).suffix.lower()
    safe_filename = f"{timestamp}_{file.filename}"
    thumbnail_filename = f"{timestamp}_thumb_{file.filename}"
    
    # Save original image
    file_path = UPLOAD_DIR / safe_filename
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)
    
    # Create thumbnail
    try:
        image = Image.open(io.BytesIO(content))
        image.thumbnail((200, 200), Image.Resampling.LANCZOS)
        
        thumbnail_path = THUMBNAIL_DIR / thumbnail_filename
        image.save(thumbnail_path)
        
        return JSONResponse({
            "message": "Image uploaded successfully",
            "filename": safe_filename,
            "thumbnail": thumbnail_filename,
            "size": len(content),
            "dimensions": {
                "width": image.width,
                "height": image.height
            }
        })
        
    except Exception as e:
        return JSONResponse(
            {"error": f"Failed to process image: {str(e)}"},
            status_code=500
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## File Download

```python
from velithon import Velithon, Request
from velithon.responses import FileResponse, JSONResponse
from pathlib import Path

app = Velithon()

UPLOAD_DIR = Path("uploads")

@app.get("/download/{filename}")
async def download_file(request: Request):
    """Download uploaded file."""
    filename = request.path_params["filename"]
    file_path = UPLOAD_DIR / filename
    
    if not file_path.exists():
        return JSONResponse(
            {"error": "File not found"},
            status_code=404
        )
    
    return FileResponse(
        path=file_path,
        filename=filename
    )

@app.get("/files")
async def list_files(request: Request):
    """List all uploaded files."""
    if not UPLOAD_DIR.exists():
        return JSONResponse({"files": []})
    
    files = []
    for file_path in UPLOAD_DIR.iterdir():
        if file_path.is_file():
            stat = file_path.stat()
            files.append({
                "filename": file_path.name,
                "size": stat.st_size,
                "created": stat.st_ctime,
                "download_url": f"/download/{file_path.name}"
            })
    
    return JSONResponse({"files": files})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Testing File Upload

```python
import pytest
import httpx
import aiofiles
from pathlib import Path

@pytest.mark.asyncio
async def test_file_upload():
    """Test file upload endpoint."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Create test file
        test_content = b"Test file content"
        
        response = await client.post(
            "/upload",
            files={"file": ("test.txt", test_content, "text/plain")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.txt"
        assert data["size"] == len(test_content)

@pytest.mark.asyncio
async def test_multiple_file_upload():
    """Test multiple file upload."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        files = [
            ("files", ("test1.txt", b"Content 1", "text/plain")),
            ("files", ("test2.txt", b"Content 2", "text/plain"))
        ]
        
        response = await client.post("/upload/multiple", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["files"]) == 2

@pytest.mark.asyncio
async def test_file_validation():
    """Test file validation."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Test invalid file type
        response = await client.post(
            "/upload/validated",
            files={"file": ("test.exe", b"executable", "application/octet-stream")}
        )
        
        assert response.status_code == 400
        assert "not allowed" in response.json()["error"]
```

## HTML Upload Form

```html
<!DOCTYPE html>
<html>
<head>
    <title>File Upload</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .upload-form { max-width: 500px; }
        .file-input { margin: 10px 0; }
        .upload-btn { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; }
        .progress { margin: 10px 0; }
        .file-list { margin-top: 20px; }
    </style>
</head>
<body>
    <div class="upload-form">
        <h2>File Upload</h2>
        
        <form id="uploadForm" enctype="multipart/form-data">
            <div class="file-input">
                <label>Select file:</label>
                <input type="file" id="fileInput" name="file" required>
            </div>
            
            <button type="submit" class="upload-btn">Upload</button>
        </form>
        
        <div id="progress" class="progress" style="display: none;">
            <div>Uploading...</div>
        </div>
        
        <div id="result"></div>
        
        <div class="file-list">
            <h3>Uploaded Files</h3>
            <div id="fileList"></div>
        </div>
    </div>

    <script>
        document.getElementById('uploadForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData();
            const fileInput = document.getElementById('fileInput');
            formData.append('file', fileInput.files[0]);
            
            document.getElementById('progress').style.display = 'block';
            
            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                document.getElementById('progress').style.display = 'none';
                
                if (response.ok) {
                    document.getElementById('result').innerHTML = 
                        `<div style="color: green;">File uploaded: ${result.filename} (${result.size} bytes)</div>`;
                    loadFileList();
                } else {
                    document.getElementById('result').innerHTML = 
                        `<div style="color: red;">Error: ${result.error}</div>`;
                }
            } catch (error) {
                document.getElementById('progress').style.display = 'none';
                document.getElementById('result').innerHTML = 
                    `<div style="color: red;">Upload failed: ${error.message}</div>`;
            }
        });
        
        async function loadFileList() {
            try {
                const response = await fetch('/files');
                const data = await response.json();
                
                const fileListDiv = document.getElementById('fileList');
                fileListDiv.innerHTML = data.files.map(file => 
                    `<div><a href="${file.download_url}">${file.filename}</a> (${file.size} bytes)</div>`
                ).join('');
            } catch (error) {
                console.error('Failed to load file list:', error);
            }
        }
        
        // Load file list on page load
        loadFileList();
    </script>
</body>
</html>
```

## Key Features

- **File Validation**: Check file types, sizes, and content
- **Security**: Generate safe filenames, validate content types
- **Multiple Uploads**: Handle single and multiple file uploads
- **Image Processing**: Generate thumbnails for uploaded images
- **Download Support**: Serve uploaded files for download
- **Progress Tracking**: Show upload progress in web interface
- **Error Handling**: Comprehensive error handling and validation

## Best Practices

1. **Always validate file uploads** - Check file types, sizes, and content
2. **Use safe filenames** - Prevent directory traversal attacks
3. **Limit file sizes** - Prevent DoS attacks with large uploads
4. **Store files outside web root** - Prevent direct access to uploaded files
5. **Scan for malware** - In production, consider virus scanning
6. **Use streaming for large files** - Handle large uploads efficiently
7. **Implement rate limiting** - Prevent abuse of upload endpoints
