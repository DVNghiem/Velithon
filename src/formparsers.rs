use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict, PyString};
use pyo3::exceptions::{PyValueError, PyRuntimeError};
use std::collections::HashMap;
use std::io::{Read, Seek, SeekFrom, Write};
use percent_encoding::percent_decode;
use tempfile::SpooledTempFile;
use parking_lot::Mutex as ParkingLotMutex;
use std::sync::Arc;

#[derive(Debug, Clone)]
#[pyclass]
pub struct FormMessage {
    #[pyo3(get)]
    pub field_start: i32,
    #[pyo3(get)]
    pub field_name: i32,
    #[pyo3(get)]
    pub field_data: i32,
    #[pyo3(get)]
    pub field_end: i32,
    #[pyo3(get)]
    pub end: i32,
}

#[pymethods]
impl FormMessage {
    #[new]
    fn new() -> Self {
        FormMessage {
            field_start: 1,
            field_name: 2,
            field_data: 3,
            field_end: 4,
            end: 5,
        }
    }
}

#[derive(Debug)]
#[pyclass]
pub struct UploadFile {
    #[pyo3(get)]
    pub filename: String,
    #[pyo3(get)]
    pub content_type: Option<String>,
    #[pyo3(get)]
    pub size: usize,
    pub file: Arc<ParkingLotMutex<SpooledTempFile>>,
    #[pyo3(get)]
    pub headers: Py<PyAny>,
}

#[pymethods]
impl UploadFile {
    #[new]
    fn new(
        filename: String,
        content_type: Option<String>,
        size: usize,
        headers: Py<PyAny>,
    ) -> PyResult<Self> {
        Self::create_with_spool_size(filename, content_type, size, headers, 1024 * 1024)
    }

    fn read(&self, py: Python, size: Option<usize>) -> PyResult<Py<PyAny>> {
        // Use blocking runtime for sync operations to prevent GIL issues
        py.detach(|| {
            let mut file = self.file.lock();
            let mut buffer = if let Some(s) = size {
                vec![0u8; s]
            } else {
                Vec::new()
            };

            if size.is_some() {
                file.read_exact(&mut buffer).map_err(|e| {
                    PyRuntimeError::new_err(format!("Failed to read file: {}", e))
                })?;
            } else {
                file.read_to_end(&mut buffer).map_err(|e| {
                    PyRuntimeError::new_err(format!("Failed to read file: {}", e))
                })?;
            }

            Python::attach(|py| Ok(PyBytes::new(py, &buffer).into()))
        })
    }

    fn write(&self, data: &Bound<'_, PyBytes>) -> PyResult<usize> {
        let mut file = self.file.lock();
        let bytes_written = file.write(data.as_bytes()).map_err(|e| {
            PyRuntimeError::new_err(format!("Failed to write to file: {}", e))
        })?;
        Ok(bytes_written)
    }

    fn seek(&self, position: i64, whence: i32) -> PyResult<i64> {
        let mut file = self.file.lock();
        let seek_from = match whence {
            0 => SeekFrom::Start(position as u64), // SEEK_SET
            1 => SeekFrom::Current(position),      // SEEK_CUR  
            2 => SeekFrom::End(position),          // SEEK_END
            _ => return Err(PyValueError::new_err("Invalid whence value")),
        };

        let new_position = file.seek(seek_from).map_err(|e| {
            PyRuntimeError::new_err(format!("Failed to seek file: {}", e))
        })? as i64;
        Ok(new_position)
    }

    fn close(&self) -> PyResult<()> {
        // File will be automatically closed when dropped
        Ok(())
    }
}

impl UploadFile {
    fn create_with_spool_size(
        filename: String,
        content_type: Option<String>,
        size: usize,
        headers: Py<PyAny>,
        spool_max_size: usize,
    ) -> PyResult<Self> {
        let file = SpooledTempFile::new(spool_max_size);
        Ok(UploadFile {
            filename,
            content_type,
            size,
            file: Arc::new(ParkingLotMutex::new(file)),
            headers,
        })
    }
}

#[derive(Debug)]
#[pyclass]
pub struct FormData {
    #[pyo3(get)]
    pub items: Vec<(String, Py<PyAny>)>,
}

#[pymethods]
impl FormData {
    #[new]
    fn new(items: Vec<(String, Py<PyAny>)>) -> Self {
        FormData { items }
    }

    fn get(&self, py: Python, key: &str) -> PyResult<Option<Py<PyAny>>> {
        for (k, v) in &self.items {
            if k == key {
                return Ok(Some(v.clone_ref(py)));
            }
        }
        Ok(None)
    }

    fn getlist(&self, py: Python, key: &str) -> PyResult<Vec<Py<PyAny>>> {
        let mut result = Vec::new();
        for (k, v) in &self.items {
            if k == key {
                result.push(v.clone_ref(py));
            }
        }
        Ok(result)
    }
}

#[derive(Debug)]
#[pyclass]
pub struct FormParser {
    headers: HashMap<String, String>,
    max_part_size: usize,
}

#[pymethods]
impl FormParser {
    #[new]
    fn new(headers: Py<PyAny>, max_part_size: Option<usize>) -> PyResult<Self> {
        let headers_map = Python::attach(|py| {
            let mut map = HashMap::new();
            let headers_dict = headers.bind(py);
            
            if let Ok(dict) = headers_dict.downcast::<PyDict>() {
                for (key, value) in dict.iter() {
                    let key_str: String = key.extract()?;
                    let value_str: String = value.extract()?;
                    map.insert(key_str.to_lowercase(), value_str);
                }
            }
            Ok::<HashMap<String, String>, PyErr>(map)
        })?;

        Ok(FormParser {
            headers: headers_map,
            max_part_size: max_part_size.unwrap_or(1024 * 1024), // 1MB default
        })
    }

    fn parse_form_urlencoded(&self, py: Python, data: &Bound<'_, PyBytes>) -> PyResult<FormData> {
        let bytes = data.as_bytes();
        
        // Check content length against max_part_size to prevent DoS
        if bytes.len() > self.max_part_size {
            return Err(PyValueError::new_err(format!(
                "Form data size {} exceeds maximum allowed size {}", 
                bytes.len(), 
                self.max_part_size
            )));
        }
        
        // Validate content type if available
        if let Some(content_type) = self.headers.get("content-type") {
            if !content_type.starts_with("application/x-www-form-urlencoded") {
                return Err(PyValueError::new_err(format!(
                    "Invalid content type for form data: {}", 
                    content_type
                )));
            }
        }
        
        let content = std::str::from_utf8(bytes)
            .map_err(|e| PyValueError::new_err(format!("Invalid UTF-8: {}", e)))?;

        let mut items = Vec::new();
        
        for pair in content.split('&') {
            if let Some((key, value)) = pair.split_once('=') {
                // Replace + with space before percent decoding
                let key_with_spaces = key.replace('+', " ");
                let value_with_spaces = value.replace('+', " ");
                
                let decoded_key = percent_decode(key_with_spaces.as_bytes())
                    .decode_utf8()
                    .map_err(|e| PyValueError::new_err(format!("Failed to decode key: {}", e)))?;
                let decoded_value = percent_decode(value_with_spaces.as_bytes())
                    .decode_utf8()
                    .map_err(|e| PyValueError::new_err(format!("Failed to decode value: {}", e)))?;
                
                items.push((decoded_key.to_string(), PyString::new(py, &decoded_value).into()));
            } else {
                // Replace + with space before percent decoding
                let key_with_spaces = pair.replace('+', " ");
                let decoded_key = percent_decode(key_with_spaces.as_bytes())
                    .decode_utf8()
                    .map_err(|e| PyValueError::new_err(format!("Failed to decode key: {}", e)))?;
                
                items.push((decoded_key.to_string(), PyString::new(py, "").into()));
            }
        }

        Ok(FormData::new(items))
    }
}

#[derive(Debug)]
#[pyclass]
pub struct MultiPartParser {
    headers: HashMap<String, String>,
    max_files: usize,
    max_fields: usize,
    max_part_size: usize,
    spool_max_size: usize,
}

#[pymethods]
impl MultiPartParser {
    #[new]
    fn new(
        headers: Py<PyAny>,
        max_files: Option<usize>,
        max_fields: Option<usize>,
        max_part_size: Option<usize>,
    ) -> PyResult<Self> {
        let headers_map = Python::attach(|py| {
            let mut map = HashMap::new();
            let headers_dict = headers.bind(py);
            
            if let Ok(dict) = headers_dict.downcast::<PyDict>() {
                for (key, value) in dict.iter() {
                    let key_str: String = key.extract()?;
                    let value_str: String = value.extract()?;
                    map.insert(key_str.to_lowercase(), value_str);
                }
            }
            Ok::<HashMap<String, String>, PyErr>(map)
        })?;

        Ok(MultiPartParser {
            headers: headers_map,
            max_files: max_files.unwrap_or(1000),
            max_fields: max_fields.unwrap_or(1000),
            max_part_size: max_part_size.unwrap_or(1024 * 1024), // 1MB
            spool_max_size: 1024 * 1024, // 1MB
        })
    }

    fn parse_multipart(&self, py: Python, data: &Bound<'_, PyBytes>) -> PyResult<FormData> {
        let content_type = self.headers.get("content-type")
            .ok_or_else(|| PyValueError::new_err("Missing Content-Type header"))?;

        let boundary = extract_boundary(content_type)
            .ok_or_else(|| PyValueError::new_err("Missing boundary in Content-Type"))?;

        let mut parser = MultipartFormParser::new(&boundary, self.max_part_size);
        let parts = parser.parse(data.as_bytes())
            .map_err(|e| PyRuntimeError::new_err(format!("Multipart parsing error: {}", e)))?;

        let mut items = Vec::new();
        let mut file_count = 0;
        let mut field_count = 0;

        for part in parts {
            if part.filename.is_some() {
                file_count += 1;
                if file_count > self.max_files {
                    return Err(PyValueError::new_err(format!(
                        "Too many files. Maximum is {}", self.max_files
                    )));
                }

                let upload_file = UploadFile::create_with_spool_size(
                    part.filename.unwrap_or_default(),
                    part.content_type,
                    part.data.len(),
                    PyDict::new(py).into(), // Empty headers for now
                    self.spool_max_size,
                )?;

                // Write data to the upload file
                let py_bytes = PyBytes::new(py, &part.data);
                upload_file.write(&py_bytes)?;
                upload_file.seek(0, 0)?;

                items.push((part.name, Py::new(py, upload_file)?.into()));
            } else {
                field_count += 1;
                if field_count > self.max_fields {
                    return Err(PyValueError::new_err(format!(
                        "Too many fields. Maximum is {}", self.max_fields
                    )));
                }

                let value = String::from_utf8_lossy(&part.data).into_owned();
                items.push((part.name, PyString::new(py, &value).into()));
            }
        }

        Ok(FormData::new(items))
    }
}

// Helper functions and structs for multipart parsing
#[derive(Debug)]
struct MultipartPart {
    name: String,
    filename: Option<String>,
    content_type: Option<String>,
    data: Vec<u8>,
}

struct MultipartFormParser {
    boundary: Vec<u8>,
    max_part_size: usize,
}

impl MultipartFormParser {
    fn new(boundary: &str, max_part_size: usize) -> Self {
        let mut boundary_bytes = b"--".to_vec();
        boundary_bytes.extend_from_slice(boundary.as_bytes());
        
        Self {
            boundary: boundary_bytes,
            max_part_size,
        }
    }

    fn parse(&mut self, data: &[u8]) -> Result<Vec<MultipartPart>, String> {
        let mut parts = Vec::new();
        let mut cursor = 0;

        // Find first boundary
        if let Some(start) = self.find_boundary(data, cursor) {
            cursor = start + self.boundary.len();
            
            // Skip CRLF after boundary
            if cursor + 1 < data.len() && data[cursor] == b'\r' && data[cursor + 1] == b'\n' {
                cursor += 2;
            } else if cursor < data.len() && data[cursor] == b'\n' {
                cursor += 1;
            }
        } else {
            return Err("No boundary found".to_string());
        }

        while cursor < data.len() {
            // Find next boundary
            if let Some(end) = self.find_boundary(data, cursor) {
                // Parse part between cursor and end
                let part_data = &data[cursor..end];
                if let Ok(part) = self.parse_part(part_data) {
                    parts.push(part);
                }
                
                cursor = end + self.boundary.len();
                
                // Check if this is the final boundary (ends with --)
                if cursor + 1 < data.len() && data[cursor] == b'-' && data[cursor + 1] == b'-' {
                    break;
                }
                
                // Skip CRLF after boundary
                if cursor + 1 < data.len() && data[cursor] == b'\r' && data[cursor + 1] == b'\n' {
                    cursor += 2;
                } else if cursor < data.len() && data[cursor] == b'\n' {
                    cursor += 1;
                }
            } else {
                break;
            }
        }

        Ok(parts)
    }

    fn find_boundary(&self, data: &[u8], start: usize) -> Option<usize> {
        if start >= data.len() {
            return None;
        }

        for i in start..=data.len().saturating_sub(self.boundary.len()) {
            if data[i..i + self.boundary.len()] == self.boundary {
                return Some(i);
            }
        }
        None
    }

    fn parse_part(&self, data: &[u8]) -> Result<MultipartPart, String> {
        // Split headers and body by finding \r\n\r\n or \n\n
        let header_end = if let Some(pos) = self.find_pattern(data, b"\r\n\r\n") {
            pos
        } else if let Some(pos) = self.find_pattern(data, b"\n\n") {
            pos
        } else {
            return Err("No header/body separator found".to_string());
        };

        let headers_data = &data[..header_end];
        let body_start = if data[header_end..].starts_with(b"\r\n\r\n") {
            header_end + 4
        } else {
            header_end + 2
        };
        
        let mut body_data = data[body_start..].to_vec();
        
        // Remove trailing CRLF if present
        if body_data.ends_with(b"\r\n") {
            body_data.truncate(body_data.len() - 2);
        } else if body_data.ends_with(b"\n") {
            body_data.truncate(body_data.len() - 1);
        }

        if body_data.len() > self.max_part_size {
            return Err(format!("Part size {} exceeds maximum {}", body_data.len(), self.max_part_size));
        }

        // Parse headers
        let headers_str = String::from_utf8_lossy(headers_data);
        let mut name = String::new();
        let mut filename = None;
        let mut content_type = None;

        for line in headers_str.lines() {
            if line.to_lowercase().starts_with("content-disposition:") {
                if let Some(params) = parse_content_disposition(line) {
                    if let Some(n) = params.get("name") {
                        name = n.clone();
                    }
                    if let Some(f) = params.get("filename") {
                        filename = Some(f.clone());
                    }
                }
            } else if line.to_lowercase().starts_with("content-type:") {
                content_type = Some(line.splitn(2, ':').nth(1).unwrap_or("").trim().to_string());
            }
        }

        if name.is_empty() {
            return Err("Missing name in Content-Disposition".to_string());
        }

        Ok(MultipartPart {
            name,
            filename,
            content_type,
            data: body_data,
        })
    }

    fn find_pattern(&self, data: &[u8], pattern: &[u8]) -> Option<usize> {
        for i in 0..=data.len().saturating_sub(pattern.len()) {
            if data[i..i + pattern.len()] == *pattern {
                return Some(i);
            }
        }
        None
    }
}

fn extract_boundary(content_type: &str) -> Option<String> {
    for param in content_type.split(';') {
        let param = param.trim();
        if param.starts_with("boundary=") {
            let boundary = &param[9..];
            // Remove quotes if present
            if boundary.starts_with('"') && boundary.ends_with('"') {
                return Some(boundary[1..boundary.len()-1].to_string());
            } else {
                return Some(boundary.to_string());
            }
        }
    }
    None
}

fn parse_content_disposition(header: &str) -> Option<HashMap<String, String>> {
    let mut params = HashMap::new();
    
    // Skip "Content-Disposition:" part
    let header = header.splitn(2, ':').nth(1)?.trim();
    
    for param in header.split(';') {
        let param = param.trim();
        if let Some((key, value)) = param.split_once('=') {
            let key = key.trim().to_string();
            let mut value = value.trim();
            
            // Remove quotes if present
            if value.starts_with('"') && value.ends_with('"') {
                value = &value[1..value.len()-1];
            }
            
            params.insert(key, value.to_string());
        }
    }
    
    Some(params)
}

/// Parses HTTP options headers (like Content-Type) into a tuple of (content_type, options_dict).
/// This is a high-performance Rust implementation that replaces the python-multipart library.
/// 
/// # Arguments
/// * `value` - The header value to parse (str, bytes, or None)
/// 
/// # Returns
/// A tuple of (content_type: bytes, options: dict[bytes, bytes])
/// 
/// # Examples
/// ```python
/// from velithon._velithon import parse_options_header
/// 
/// # Basic content type
/// content_type, options = parse_options_header("text/html")
/// assert content_type == b"text/html"
/// assert options == {}
/// 
/// # With parameters
/// content_type, options = parse_options_header("text/html; charset=utf-8")
/// assert content_type == b"text/html"
/// assert options == {b"charset": b"utf-8"}
/// ```
#[pyfunction]
pub fn parse_options_header(py: Python<'_>, value: Option<Py<PyAny>>) -> PyResult<(Py<PyAny>, Py<PyAny>)> {
    let empty_bytes = PyBytes::new(py, b"").into();
    let empty_dict = PyDict::new(py).into();
    
    // Handle None or empty values
    let value_str = match value {
        None => return Ok((empty_bytes, empty_dict)),
        Some(v) => {
            let bound_v = v.bind(py);
            if bound_v.is_none() {
                return Ok((empty_bytes, empty_dict));
            }
            
            // Convert to string
            let s = if let Ok(bytes) = bound_v.extract::<&[u8]>() {
                // If it's bytes, decode as latin-1 (as per WSGI spec)
                match String::from_utf8(bytes.to_vec()) {
                    Ok(s) => s,
                    Err(_) => {
                        // Fallback to latin-1 decoding
                        bytes.iter().map(|&b| b as char).collect::<String>()
                    }
                }
            } else if let Ok(s) = bound_v.extract::<String>() {
                s
            } else {
                return Err(PyValueError::new_err("Value must be str, bytes, or None"));
            };
            
            if s.is_empty() {
                return Ok((empty_bytes, empty_dict));
            }
            
            s
        }
    };
    
    // If no semicolon, return the content type as-is
    if !value_str.contains(';') {
        let content_type = value_str.trim().to_lowercase();
        let content_type_bytes = PyBytes::new(py, content_type.as_bytes()).into();
        return Ok((content_type_bytes, empty_dict));
    }
    
    // Split at the first semicolon
    let mut parts = value_str.splitn(2, ';');
    let content_type = parts.next().unwrap_or("").trim().to_lowercase();
    let params_str = parts.next().unwrap_or("").trim();
    
    let content_type_bytes = PyBytes::new(py, content_type.as_bytes()).into();
    let options_dict = PyDict::new(py);
    
    // Parse parameters
    for param in params_str.split(';') {
        let param = param.trim();
        if param.is_empty() {
            continue;
        }
        
        if let Some((key, value)) = param.split_once('=') {
            let key = key.trim().to_lowercase();
            let mut value = value.trim();
            
            // Remove quotes if present
            if value.len() >= 2 && value.starts_with('"') && value.ends_with('"') {
                value = &value[1..value.len()-1];
            }
            
            // Handle filename parameter - fix IE6 bug that sends full path
            let final_value = if key == "filename" {
                if value.len() >= 3 && (&value[1..3] == ":\\" || &value[0..2] == "\\\\") {
                    value.split('\\').last().unwrap_or(value)
                } else {
                    value
                }
            } else {
                value
            };
            
            let key_bytes = PyBytes::new(py, key.as_bytes());
            let value_bytes = PyBytes::new(py, final_value.as_bytes());
            options_dict.set_item(key_bytes, value_bytes)?;
        }
    }
    
    Ok((content_type_bytes, options_dict.into()))
}

pub fn register_formparsers(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<FormMessage>()?;
    m.add_class::<UploadFile>()?;
    m.add_class::<FormData>()?;
    m.add_class::<FormParser>()?;
    m.add_class::<MultiPartParser>()?;
    m.add_function(wrap_pyfunction!(parse_options_header, m)?)?;
    
    Ok(())
}
