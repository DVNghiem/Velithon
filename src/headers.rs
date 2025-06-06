use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyTuple};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};

/// Fast HTTP header parsing and processing
#[pyclass]
pub struct HeaderProcessor {
    /// Cache for parsed headers
    header_cache: Arc<RwLock<HashMap<String, Vec<(String, String)>>>>,
    /// Cache for content-type parsing
    content_type_cache: Arc<RwLock<HashMap<String, (String, HashMap<String, String>)>>>,
    max_cache_size: usize,
}

#[pymethods]
impl HeaderProcessor {
    #[new]
    #[pyo3(signature = (max_cache_size = 2000))]
    fn new(max_cache_size: usize) -> Self {
        Self {
            header_cache: Arc::new(RwLock::new(HashMap::new())),
            content_type_cache: Arc::new(RwLock::new(HashMap::new())),
            max_cache_size,
        }
    }

    /// Parse raw headers into a structured format
    fn parse_headers(&self, raw_headers: &Bound<'_, PyList>) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            let parsed_headers = PyDict::new(py);
            
            for item in raw_headers.iter() {
                let header_tuple: &Bound<'_, PyTuple> = item.downcast()?;
                if header_tuple.len() == 2 {
                    let name: String = header_tuple.get_item(0)?.extract()?;
                    let value: String = header_tuple.get_item(1)?.extract()?;
                    
                    // Normalize header name to lowercase for consistency
                    let normalized_name = name.to_lowercase();
                    
                    // Handle multiple values for the same header
                    if let Some(existing) = parsed_headers.get_item(&normalized_name)? {
                        if let Ok(existing_str) = existing.extract::<String>() {
                            // Convert single value to list
                            let list = PyList::new(py, &[existing_str, value])?;
                            parsed_headers.set_item(&normalized_name, list)?;
                        } else if let Ok(existing_list) = existing.downcast::<PyList>() {
                            // Append to existing list
                            existing_list.append(value)?;
                        }
                    } else {
                        parsed_headers.set_item(&normalized_name, value)?;
                    }
                }
            }
            
            Ok(parsed_headers.into())
        })
    }

    /// Parse Content-Type header with caching
    fn parse_content_type(&self, content_type: &str) -> PyResult<(String, PyObject)> {
        // Check cache first
        {
            let cache = self.content_type_cache.read().unwrap();
            if let Some((media_type, params)) = cache.get(content_type) {
                return Python::with_gil(|py| {
                    let params_dict = PyDict::new(py);
                    for (k, v) in params {
                        params_dict.set_item(k, v)?;
                    }
                    Ok((media_type.clone(), params_dict.into()))
                });
            }
        }

        // Parse content type
        let (media_type, params) = self.parse_content_type_internal(content_type);

        // Cache the result
        if content_type.len() <= 256 {
            let mut cache = self.content_type_cache.write().unwrap();
            if cache.len() >= self.max_cache_size {
                // Simple cache eviction
                let keys_to_remove: Vec<_> = cache.keys().take(self.max_cache_size / 5).cloned().collect();
                for key in keys_to_remove {
                    cache.remove(&key);
                }
            }
            cache.insert(content_type.to_string(), (media_type.clone(), params.clone()));
        }

        Python::with_gil(|py| {
            let params_dict = PyDict::new(py);
            for (k, v) in params {
                params_dict.set_item(k, v)?;
            }
            Ok((media_type, params_dict.into()))
        })
    }    /// Fast header validation
    fn validate_headers(&self, headers: &Bound<'_, PyDict>) -> PyResult<Vec<String>> {
        let mut errors = Vec::new();
        
        for (key, value) in headers {
            let header_name: String = key.extract()?;
            let header_value: String = value.str()?.to_string();
            
            // Basic header validation
            if header_name.is_empty() {
                errors.push("Empty header name".to_string());
                continue;
            }
            
            // Check for invalid characters in header name
            if header_name.chars().any(|c| c.is_control() || c == ':' || c == ' ') {
                errors.push(format!("Invalid characters in header name: {}", header_name));
            }
            
            // Check for invalid characters in header value (basic check)
            if header_value.chars().any(|c| c == '\r' || c == '\n') {
                errors.push(format!("Invalid characters in header value for {}", header_name));
            }
            
            // Specific validations for common headers
            match header_name.to_lowercase().as_str() {
                "content-length" => {
                    if header_value.parse::<u64>().is_err() {
                        errors.push("Invalid Content-Length value".to_string());
                    }
                }
                "host" => {
                    if header_value.is_empty() {
                        errors.push("Host header cannot be empty".to_string());
                    }
                }
                _ => {}
            }
        }
        
        Ok(errors)
    }

    /// Optimize headers for response (remove duplicates, normalize)
    fn optimize_response_headers(&self, headers: &Bound<'_, PyList>) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            let mut header_map: HashMap<String, String> = HashMap::new();
            
            for item in headers.iter() {
                let header_tuple: &Bound<'_, PyTuple> = item.downcast()?;
                if header_tuple.len() == 2 {
                    let name: String = header_tuple.get_item(0)?.extract()?;
                    let value: String = header_tuple.get_item(1)?.extract()?;
                    
                    let normalized_name = name.to_lowercase();
                    
                    // Handle special cases for headers that can have multiple values
                    match normalized_name.as_str() {
                        "set-cookie" => {
                            // Don't merge set-cookie headers
                            header_map.insert(format!("set-cookie-{}", header_map.len()), value);
                        }
                        _ => {
                            header_map.insert(normalized_name, value);
                        }
                    }
                }
            }
            
            // Convert back to list of tuples
            let result_list = PyList::empty(py);
            for (name, value) in header_map {
                if name.starts_with("set-cookie-") {
                    let tuple = PyTuple::new(py, &["set-cookie", &value])?;
                    result_list.append(tuple)?;
                } else {
                    let tuple = PyTuple::new(py, &[&name, &value])?;
                    result_list.append(tuple)?;
                }
            }
            
            Ok(result_list.into())
        })
    }

    /// Clear all caches
    fn clear_caches(&self) -> PyResult<()> {
        self.header_cache.write().unwrap().clear();
        self.content_type_cache.write().unwrap().clear();
        Ok(())
    }

    /// Get cache statistics
    fn get_cache_stats(&self) -> PyResult<(usize, usize)> {
        let header_cache_size = self.header_cache.read().unwrap().len();
        let content_type_cache_size = self.content_type_cache.read().unwrap().len();
        Ok((header_cache_size, content_type_cache_size))
    }
}

impl HeaderProcessor {
    /// Internal content-type parsing logic
    fn parse_content_type_internal(&self, content_type: &str) -> (String, HashMap<String, String>) {
        let mut params = HashMap::new();
        
        if let Some((media_type, params_str)) = content_type.split_once(';') {
            let media_type = media_type.trim().to_lowercase();
            
            // Parse parameters
            for param in params_str.split(';') {
                if let Some((key, value)) = param.split_once('=') {
                    let key = key.trim().to_lowercase();
                    let value = value.trim().trim_matches('"').to_string();
                    params.insert(key, value);
                }
            }
            
            (media_type, params)
        } else {
            (content_type.trim().to_lowercase(), params)
        }
    }
}

/// High-performance cookie parsing
#[pyclass]
pub struct CookieProcessor {
    /// Cache for parsed cookies
    cookie_cache: Arc<RwLock<HashMap<String, HashMap<String, String>>>>,
    max_cache_size: usize,
}

#[pymethods]
impl CookieProcessor {
    #[new]
    #[pyo3(signature = (max_cache_size = 1000))]
    fn new(max_cache_size: usize) -> Self {
        Self {
            cookie_cache: Arc::new(RwLock::new(HashMap::new())),
            max_cache_size,
        }
    }

    /// Parse cookie header with caching
    fn parse_cookies(&self, cookie_header: &str) -> PyResult<PyObject> {
        if cookie_header.is_empty() {
            return Python::with_gil(|py| {
                let dict = PyDict::new(py);
                Ok(dict.into())
            });
        }

        // Check cache
        {
            let cache = self.cookie_cache.read().unwrap();
            if let Some(cached) = cache.get(cookie_header) {
                return Python::with_gil(|py| {
                    let dict = PyDict::new(py);
                    for (k, v) in cached {
                        dict.set_item(k, v)?;
                    }
                    Ok(dict.into())
                });
            }
        }

        // Parse cookies
        let mut cookies = HashMap::new();
        for pair in cookie_header.split(';') {
            if let Some((name, value)) = pair.split_once('=') {
                let name = name.trim().to_string();
                let value = value.trim().to_string();
                cookies.insert(name, value);
            }
        }

        // Cache the result
        if cookie_header.len() <= 512 {
            let mut cache = self.cookie_cache.write().unwrap();
            if cache.len() >= self.max_cache_size {
                let keys_to_remove: Vec<_> = cache.keys().take(self.max_cache_size / 5).cloned().collect();
                for key in keys_to_remove {
                    cache.remove(&key);
                }
            }
            cache.insert(cookie_header.to_string(), cookies.clone());
        }

        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            for (k, v) in cookies {
                dict.set_item(k, v)?;
            }
            Ok(dict.into())
        })
    }

    /// Clear cookie cache
    fn clear_cache(&self) -> PyResult<()> {
        self.cookie_cache.write().unwrap().clear();
        Ok(())
    }
}

/// Register header processing components
pub fn register_headers(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<HeaderProcessor>()?;
    m.add_class::<CookieProcessor>()?;
    Ok(())
}
