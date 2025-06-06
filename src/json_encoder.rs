use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyFloat, PyInt, PyBool, PyString};
use std::collections::HashMap;
use std::sync::Mutex;

/// Ultra-fast JSON encoder implemented in Rust
#[pyclass]
pub struct RustJSONEncoder {
    /// Cache for small, frequently-used JSON responses
    cache: Mutex<HashMap<String, Vec<u8>>>,
    cache_hits: Mutex<u64>,
    cache_misses: Mutex<u64>,
    max_cache_size: usize,
}

#[pymethods]
impl RustJSONEncoder {
    #[new]
    #[pyo3(signature = (max_cache_size = 1000))]
    fn new(max_cache_size: usize) -> Self {
        Self {
            cache: Mutex::new(HashMap::new()),
            cache_hits: Mutex::new(0),
            cache_misses: Mutex::new(0),
            max_cache_size,
        }
    }

    /// Encode Python object to JSON bytes with aggressive caching
    fn encode(&self, py: Python, obj: &Bound<'_, PyAny>) -> PyResult<Vec<u8>> {
        // Fast path for simple cacheable types
        if let Ok(cache_key) = self.get_cache_key(obj) {
            if let Ok(cache) = self.cache.try_lock() {
                if let Some(cached) = cache.get(&cache_key) {
                    *self.cache_hits.lock().unwrap() += 1;
                    return Ok(cached.clone());
                }
            }
        }

        // Encode the object
        let json_bytes = self.encode_value(py, obj)?;

        // Cache small responses
        if json_bytes.len() <= 1024 {
            if let Ok(cache_key) = self.get_cache_key(obj) {
                if let Ok(mut cache) = self.cache.try_lock() {
                    *self.cache_misses.lock().unwrap() += 1;
                    
                    // Limit cache size
                    if cache.len() >= self.max_cache_size {
                        // Remove 20% of entries when cache is full
                        let keys_to_remove: Vec<_> = cache.keys().take(self.max_cache_size / 5).cloned().collect();
                        for key in keys_to_remove {
                            cache.remove(&key);
                        }
                    }
                    
                    cache.insert(cache_key, json_bytes.clone());
                }
            }
        }

        Ok(json_bytes)
    }

    /// Get cache statistics
    fn get_cache_stats(&self) -> PyResult<(u64, u64, f64)> {
        let hits = *self.cache_hits.lock().unwrap();
        let misses = *self.cache_misses.lock().unwrap();
        let total = hits + misses;
        let hit_rate = if total > 0 { hits as f64 / total as f64 } else { 0.0 };
        Ok((hits, misses, hit_rate))
    }

    /// Clear the cache
    fn clear_cache(&self) -> PyResult<()> {
        self.cache.lock().unwrap().clear();
        *self.cache_hits.lock().unwrap() = 0;
        *self.cache_misses.lock().unwrap() = 0;
        Ok(())
    }
}

impl RustJSONEncoder {
    /// Generate a cache key for simple objects
    fn get_cache_key(&self, obj: &Bound<'_, PyAny>) -> PyResult<String> {
        if obj.is_instance_of::<PyString>() {
            let s: String = obj.extract()?;
            if s.len() <= 100 {
                return Ok(format!("str:{}", s));
            }
        } else if obj.is_instance_of::<PyInt>() {
            let i: i64 = obj.extract()?;
            return Ok(format!("int:{}", i));
        } else if obj.is_instance_of::<PyFloat>() {
            let f: f64 = obj.extract()?;
            return Ok(format!("float:{}", f));
        } else if obj.is_instance_of::<PyBool>() {
            let b: bool = obj.extract()?;
            return Ok(format!("bool:{}", b));
        } else if obj.is_none() {
            return Ok("null".to_string());
        } else if obj.is_instance_of::<PyDict>() {
            let dict: &Bound<'_, PyDict> = obj.downcast()?;
            if dict.len() <= 5 {
                // Create stable key for small dicts
                let mut items: Vec<_> = dict.iter().collect();
                items.sort_by(|a, b| {
                    let a_key: String = a.0.str().unwrap().to_string();
                    let b_key: String = b.0.str().unwrap().to_string();
                    a_key.cmp(&b_key)
                });
                
                let mut key_parts = Vec::new();
                for (k, v) in items {
                    let k_str: String = k.str()?.to_string();
                    if let Ok(v_str) = self.simple_value_to_string(&v) {
                        key_parts.push(format!("{}:{}", k_str, v_str));
                    } else {
                        // Skip complex values
                        return Err(pyo3::exceptions::PyValueError::new_err("Object not cacheable"));
                    }
                }
                
                if key_parts.len() == dict.len() {
                    return Ok(format!("dict:{}", key_parts.join("|")));
                }
            }
        }
        
        Err(pyo3::exceptions::PyValueError::new_err("Object not cacheable"))
    }

    /// Convert simple values to string for cache keys
    fn simple_value_to_string(&self, obj: &Bound<'_, PyAny>) -> PyResult<String> {
        if obj.is_instance_of::<PyString>() {
            let s: String = obj.extract()?;
            if s.len() <= 50 {
                return Ok(s);
            }
        } else if obj.is_instance_of::<PyInt>() {
            let i: i64 = obj.extract()?;
            return Ok(i.to_string());
        } else if obj.is_instance_of::<PyFloat>() {
            let f: f64 = obj.extract()?;
            return Ok(f.to_string());
        } else if obj.is_instance_of::<PyBool>() {
            let b: bool = obj.extract()?;
            return Ok(b.to_string());
        } else if obj.is_none() {
            return Ok("null".to_string());
        }
        
        Err(pyo3::exceptions::PyValueError::new_err("Value too complex for cache key"))
    }

    /// Core JSON encoding logic
    fn encode_value(&self, py: Python, obj: &Bound<'_, PyAny>) -> PyResult<Vec<u8>> {
        let mut result = Vec::new();
        self.encode_value_into(&mut result, py, obj)?;
        Ok(result)
    }

    /// Encode value directly into a byte vector (zero-copy when possible)
    fn encode_value_into(&self, buf: &mut Vec<u8>, py: Python, obj: &Bound<'_, PyAny>) -> PyResult<()> {
        if obj.is_none() {
            buf.extend_from_slice(b"null");
        } else if obj.is_instance_of::<PyBool>() {
            let b: bool = obj.extract()?;
            if b {
                buf.extend_from_slice(b"true");
            } else {
                buf.extend_from_slice(b"false");
            }
        } else if obj.is_instance_of::<PyInt>() {
            let i: i64 = obj.extract()?;
            buf.extend_from_slice(i.to_string().as_bytes());
        } else if obj.is_instance_of::<PyFloat>() {
            let f: f64 = obj.extract()?;
            if f.is_finite() {
                buf.extend_from_slice(f.to_string().as_bytes());
            } else {
                buf.extend_from_slice(b"null");
            }
        } else if obj.is_instance_of::<PyString>() {
            let s: String = obj.extract()?;
            self.encode_string_into(buf, &s);
        } else if obj.is_instance_of::<PyList>() {
            let list: &Bound<'_, PyList> = obj.downcast()?;
            buf.push(b'[');
            for (i, item) in list.iter().enumerate() {
                if i > 0 {
                    buf.push(b',');
                }
                self.encode_value_into(buf, py, &item)?;
            }
            buf.push(b']');
        } else if obj.is_instance_of::<PyDict>() {
            let dict: &Bound<'_, PyDict> = obj.downcast()?;
            buf.push(b'{');
            let mut first = true;
            for (key, value) in dict {
                if !first {
                    buf.push(b',');
                }
                first = false;
                
                // Keys must be strings in JSON
                let key_str: String = key.str()?.to_string();
                self.encode_string_into(buf, &key_str);
                buf.push(b':');
                self.encode_value_into(buf, py, &value)?;
            }
            buf.push(b'}');
        } else {
            // Try to convert to string for unknown types
            let s = obj.str()?.to_string();
            self.encode_string_into(buf, &s);
        }
        
        Ok(())
    }

    /// Efficiently encode string with proper JSON escaping
    fn encode_string_into(&self, buf: &mut Vec<u8>, s: &str) {
        buf.push(b'"');
        
        for byte in s.bytes() {
            match byte {
                b'"' => buf.extend_from_slice(b"\\\""),
                b'\\' => buf.extend_from_slice(b"\\\\"),
                b'\n' => buf.extend_from_slice(b"\\n"),
                b'\r' => buf.extend_from_slice(b"\\r"),
                b'\t' => buf.extend_from_slice(b"\\t"),
                b'\x08' => buf.extend_from_slice(b"\\b"),
                b'\x0C' => buf.extend_from_slice(b"\\f"),
                c if c < 32 => {
                    buf.extend_from_slice(format!("\\u{:04x}", c).as_bytes());
                }
                c => buf.push(c),
            }
        }
        
        buf.push(b'"');
    }
}

/// Register the JSON encoder
pub fn register_json_encoder(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustJSONEncoder>()?;
    Ok(())
}
