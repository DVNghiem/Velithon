use pyo3::prelude::*;
use std::collections::HashMap;

#[pyfunction]
fn header_init(
    body_length: usize,
    status_code: u16,
    media_type: Option<String>,
    charset: String,
    provided_headers: Option<HashMap<String, String>>,
) -> PyResult<Vec<(String, String)>> {
    let mut headers = Vec::new();
    let mut has_content_length = false;
    let mut has_content_type = false;
    
    // Process existing headers
    if let Some(header_dict) = provided_headers {
        headers.reserve(header_dict.len() + 3);
        
        for (key, value) in header_dict {
            let key_lower = key.to_lowercase();
            
            if key_lower == "content-length" {
                has_content_length = true;
            } else if key_lower == "content-type" {
                has_content_type = true;
            }
            
            headers.push((key_lower, value));
        }
    }
    
    // Add content-length if needed
    if !has_content_length && 
       body_length > 0 && 
       !(status_code < 200 || status_code == 204 || status_code == 304) {
        headers.push(("content-length".to_string(), body_length.to_string()));
    }
    
    // Add content-type if needed
    if !has_content_type {
        if let Some(mut media_type) = media_type {
            if media_type.starts_with("text/") && !media_type.to_lowercase().contains("charset=") {
                media_type.push_str(&format!("; charset={}", charset));
            }
            headers.push(("content-type".to_string(), media_type));
        }
    }
    
    // Always add server header
    headers.push(("server".to_string(), "velithon".to_string()));
    
    Ok(headers)
}

/// Register response functions and classes with Python module
pub fn register_responses(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(header_init, m)?)?;
    Ok(())
}
