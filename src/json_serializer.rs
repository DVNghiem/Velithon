use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyString, PyTuple, PyAny, PyBool, PyFloat, PyInt};
use rayon::prelude::*;
use serde_json::{Map, Value, Number};
use std::collections::HashMap;
use std::sync::Arc;
use parking_lot::RwLock;

/// High-performance parallel JSON serializer using Rayon for concurrent processing
#[pyclass]
pub struct ParallelJSONSerializer {
    /// Threshold for when to use parallel processing (number of items)
    parallel_threshold: usize,
    /// Maximum depth for nested structures
    max_depth: usize,
    /// Cache for frequently serialized objects
    cache: Arc<RwLock<HashMap<u64, String>>>,
    /// Cache size limit
    cache_size_limit: usize,
}

#[pymethods]
impl ParallelJSONSerializer {
    #[new]
    #[pyo3(signature = (parallel_threshold = 10000, max_depth = 32, cache_size_limit = 1000))]
    fn new(parallel_threshold: usize, max_depth: usize, cache_size_limit: usize) -> Self {
        Self {
            parallel_threshold,
            max_depth,
            cache: Arc::new(RwLock::new(HashMap::new())),
            cache_size_limit,
        }
    }

    /// Serialize Python object to JSON bytes with parallel processing
    #[pyo3(signature = (obj, use_parallel = None))]
    fn serialize(&self, py: Python<'_>, obj: &Bound<'_, PyAny>, use_parallel: Option<bool>) -> PyResult<Vec<u8>> {
        // Try fast path first for simple/small objects
        if let Ok(Some(result)) = self.serialize_fast_path(py, obj) {
            return Ok(result);
        }

        // Convert Python object to serde_json::Value
        let value = self.python_to_value(py, obj, 0)?;
        
        // Determine if we should use parallel processing
        let should_parallelize = use_parallel.unwrap_or_else(|| {
            self.should_use_parallel(&value)
        });

        if should_parallelize {
            self.serialize_parallel(&value)
        } else {
            self.serialize_sequential(&value)
        }
    }

    /// Serialize large arrays/objects in parallel chunks
    fn serialize_parallel_chunks(&self, py: Python<'_>, obj: &Bound<'_, PyAny>) -> PyResult<Vec<u8>> {
        if let Ok(list) = obj.downcast::<PyList>() {
            self.serialize_list_parallel(py, list)
        } else if let Ok(dict) = obj.downcast::<PyDict>() {
            self.serialize_dict_parallel(py, dict)
        } else {
            // Fall back to sequential for other types
            let value = self.python_to_value(py, obj, 0)?;
            self.serialize_sequential(&value)
        }
    }

    /// Fast path for simple objects (primitives, small collections)
    fn serialize_fast_path(&self, py: Python<'_>, obj: &Bound<'_, PyAny>) -> PyResult<Option<Vec<u8>>> {
        // Handle common simple types first
        if obj.is_none() {
            return Ok(Some(b"null".to_vec()));
        }
        
        if let Ok(s) = obj.downcast::<PyString>() {
            let rust_string = s.to_string();
            // Avoid intermediate allocation for small strings
            if rust_string.len() < 64 {
                let json = format!("\"{}\"", rust_string.replace('"', "\\\""));
                return Ok(Some(json.into_bytes()));
            } else {
                let json = serde_json::to_vec(&rust_string).map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("JSON serialization error: {}", e))
                })?;
                return Ok(Some(json));
            }
        }

        if let Ok(b) = obj.downcast::<PyBool>() {
            let value = b.is_true();
            return Ok(Some(if value { b"true".to_vec() } else { b"false".to_vec() }));
        }

        if let Ok(i) = obj.downcast::<PyInt>() {
            if let Ok(value) = i.extract::<i64>() {
                // Use more efficient number serialization for common cases
                if value >= -999999 && value <= 999999 {
                    return Ok(Some(value.to_string().into_bytes()));
                }
            }
        }

        if let Ok(f) = obj.downcast::<PyFloat>() {
            let value = f.value();
            // Fast path for common float values
            if value.is_finite() && value.fract() == 0.0 && value >= -999999.0 && value <= 999999.0 {
                return Ok(Some(format!("{:.0}", value).into_bytes()));
            } else {
                return Ok(Some(value.to_string().into_bytes()));
            }
        }

        // Check if it's a small collection that doesn't need parallelization
        if let Ok(list) = obj.downcast::<PyList>() {
            if list.len() < self.parallel_threshold {
                let value = self.python_to_value(py, obj, 0)?;
                return Ok(Some(self.serialize_sequential(&value)?));
            }
        }

        if let Ok(dict) = obj.downcast::<PyDict>() {
            if dict.len() < self.parallel_threshold {
                let value = self.python_to_value(py, obj, 0)?;
                return Ok(Some(self.serialize_sequential(&value)?));
            }
        }

        Ok(None)
    }

    /// Get cache statistics
    fn get_cache_stats(&self) -> HashMap<String, usize> {
        let cache = self.cache.read();
        let mut stats = HashMap::new();
        stats.insert("size".to_string(), cache.len());
        stats.insert("capacity".to_string(), self.cache_size_limit);
        stats
    }

    /// Clear the serialization cache
    fn clear_cache(&self) {
        let mut cache = self.cache.write();
        cache.clear();
    }
}

impl ParallelJSONSerializer {
    /// Convert Python object to serde_json::Value recursively
    fn python_to_value(&self, py: Python<'_>, obj: &Bound<'_, PyAny>, depth: usize) -> PyResult<Value> {
        if depth >= self.max_depth {
            return Err(PyErr::new::<pyo3::exceptions::PyRecursionError, _>(
                "Maximum recursion depth exceeded during JSON serialization"
            ));
        }

        if obj.is_none() {
            return Ok(Value::Null);
        }

        // Handle strings
        if let Ok(s) = obj.downcast::<PyString>() {
            return Ok(Value::String(s.to_string()));
        }

        // Handle booleans
        if let Ok(b) = obj.downcast::<PyBool>() {
            return Ok(Value::Bool(b.is_true()));
        }

        // Handle integers
        if let Ok(i) = obj.downcast::<PyInt>() {
            if let Ok(value) = i.extract::<i64>() {
                return Ok(Value::Number(Number::from(value)));
            } else if let Ok(value) = i.extract::<u64>() {
                return Ok(Value::Number(Number::from(value)));
            }
        }

        // Handle floats
        if let Ok(f) = obj.downcast::<PyFloat>() {
            let value = f.value();
            if let Some(num) = Number::from_f64(value) {
                return Ok(Value::Number(num));
            }
        }

        // Handle lists
        if let Ok(list) = obj.downcast::<PyList>() {
            let mut values = Vec::with_capacity(list.len());
            for item in list {
                values.push(self.python_to_value(py, &item, depth + 1)?);
            }
            return Ok(Value::Array(values));
        }

        // Handle tuples
        if let Ok(tuple) = obj.downcast::<PyTuple>() {
            let mut values = Vec::with_capacity(tuple.len());
            for item in tuple {
                values.push(self.python_to_value(py, &item, depth + 1)?);
            }
            return Ok(Value::Array(values));
        }

        // Handle dictionaries
        if let Ok(dict) = obj.downcast::<PyDict>() {
            let mut map = Map::new();
            for (key, value) in dict {
                let key_str = if let Ok(s) = key.downcast::<PyString>() {
                    s.to_string()
                } else {
                    key.str()?.to_string()
                };
                map.insert(key_str, self.python_to_value(py, &value, depth + 1)?);
            }
            return Ok(Value::Object(map));
        }

        // Try to handle other types by converting to string
        let str_repr = obj.str()?.to_string();
        Ok(Value::String(str_repr))
    }

    /// Serialize list in parallel chunks with optimized memory allocation
    fn serialize_list_parallel(&self, py: Python<'_>, list: &Bound<'_, PyList>) -> PyResult<Vec<u8>> {
        let list_len = list.len();
        
        // Use more efficient approach for small lists
        if list_len < 50 {
            let mut result = Vec::with_capacity(list_len * 8 + 2); // Pre-allocate
            result.push(b'[');
            
            for (i, item) in list.iter().enumerate() {
                if i > 0 {
                    result.push(b',');
                }
                let value = self.python_to_value(py, &item, 0)?;
                let serialized = serde_json::to_string(&value).map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        format!("List item serialization error: {}", e)
                    )
                })?;
                result.extend_from_slice(serialized.as_bytes());
            }
            
            result.push(b']');
            return Ok(result);
        }

        // For larger lists, use parallel processing
        // First, convert all Python objects to serde_json::Value (thread-safe)
        let mut values = Vec::with_capacity(list_len);
        for item in list {
            values.push(self.python_to_value(py, &item, 0)?);
        }

        // Use optimal chunk size for parallel processing
        let chunk_size = (list_len / rayon::current_num_threads().max(1)).max(10);
        
        let serialized_chunks: Result<Vec<_>, _> = values
            .par_chunks(chunk_size)
            .map(|chunk| -> Result<String, serde_json::Error> {
                let chunk_strings: Result<Vec<String>, _> = chunk.iter()
                    .map(|item| serde_json::to_string(item))
                    .collect();
                Ok(chunk_strings?.join(","))
            })
            .collect();

        match serialized_chunks {
            Ok(chunks) => {
                let total_size = chunks.iter().map(|s| s.len()).sum::<usize>() + 2;
                let mut result = Vec::with_capacity(total_size);
                result.push(b'[');
                
                for (i, chunk) in chunks.iter().enumerate() {
                    if i > 0 {
                        result.push(b',');
                    }
                    result.extend_from_slice(chunk.as_bytes());
                }
                
                result.push(b']');
                Ok(result)
            }
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Parallel list serialization error: {}", e)
            )),
        }
    }

    /// Serialize dictionary in parallel
    fn serialize_dict_parallel(&self, py: Python<'_>, dict: &Bound<'_, PyDict>) -> PyResult<Vec<u8>> {
        // First, convert all Python objects to thread-safe data
        let mut kv_pairs = Vec::new();
        for (key, value) in dict {
            let key_str = if let Ok(s) = key.downcast::<PyString>() {
                s.to_string()
            } else {
                key.str()?.to_string()
            };
            let value_json = self.python_to_value(py, &value, 0)?;
            kv_pairs.push((key_str, value_json));
        }

        // Now parallelize the serialization of thread-safe data
        let chunk_size = (kv_pairs.len() / rayon::current_num_threads()).max(1);
        
        let serialized_chunks: Result<Vec<_>, _> = kv_pairs
            .par_chunks(chunk_size)
            .map(|chunk| -> Result<Vec<String>, serde_json::Error> {
                chunk.iter()
                    .map(|(key, value)| {
                        let key_json = serde_json::to_string(key)?;
                        let value_json = serde_json::to_string(value)?;
                        Ok(format!("{}:{}", key_json, value_json))
                    })
                    .collect()
            })
            .collect();

        match serialized_chunks {
            Ok(chunks) => {
                let mut result = Vec::new();
                result.push(b'{');
                
                let mut first = true;
                for chunk in chunks {
                    for item in chunk {
                        if !first {
                            result.push(b',');
                        }
                        result.extend_from_slice(item.as_bytes());
                        first = false;
                    }
                }
                
                result.push(b'}');
                Ok(result)
            }
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Parallel dict serialization error: {}", e)
            )),
        }
    }

    /// Determine if parallel processing should be used
    fn should_use_parallel(&self, value: &Value) -> bool {
        match value {
            Value::Array(arr) => arr.len() >= self.parallel_threshold,
            Value::Object(obj) => obj.len() >= self.parallel_threshold,
            _ => false,
        }
    }

    /// Serialize using parallel processing
    fn serialize_parallel(&self, value: &Value) -> PyResult<Vec<u8>> {
        match value {
            Value::Array(arr) if arr.len() >= self.parallel_threshold => {
                self.serialize_array_parallel(arr)
            }
            Value::Object(obj) if obj.len() >= self.parallel_threshold => {
                self.serialize_object_parallel(obj)
            }
            _ => self.serialize_sequential(value),
        }
    }

    /// Serialize array with parallel processing
    fn serialize_array_parallel(&self, arr: &[Value]) -> PyResult<Vec<u8>> {
        let chunk_size = (arr.len() / rayon::current_num_threads()).max(1);
        
        let serialized_chunks: Result<Vec<_>, _> = arr
            .par_chunks(chunk_size)
            .map(|chunk| {
                chunk.iter()
                    .map(|item| serde_json::to_string(item))
                    .collect::<Result<Vec<_>, _>>()
            })
            .collect();

        match serialized_chunks {
            Ok(chunks) => {
                let mut result = Vec::new();
                result.push(b'[');
                
                let mut first = true;
                for chunk in chunks {
                    for item in chunk {
                        if !first {
                            result.push(b',');
                        }
                        result.extend_from_slice(item.as_bytes());
                        first = false;
                    }
                }
                
                result.push(b']');
                Ok(result)
            }
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Parallel array serialization error: {}", e)
            )),
        }
    }

    /// Serialize object with parallel processing
    fn serialize_object_parallel(&self, obj: &Map<String, Value>) -> PyResult<Vec<u8>> {
        let items: Vec<_> = obj.iter().collect();
        let chunk_size = (items.len() / rayon::current_num_threads()).max(1);
        
        let serialized_chunks: Result<Vec<_>, _> = items
            .par_chunks(chunk_size)
            .map(|chunk| {
                chunk.iter()
                    .map(|(key, value)| {
                        let key_json = serde_json::to_string(key)?;
                        let value_json = serde_json::to_string(value)?;
                        Ok(format!("{}:{}", key_json, value_json))
                    })
                    .collect::<Result<Vec<_>, serde_json::Error>>()
            })
            .collect();

        match serialized_chunks {
            Ok(chunks) => {
                let mut result = Vec::new();
                result.push(b'{');
                
                let mut first = true;
                for chunk in chunks {
                    for item in chunk {
                        if !first {
                            result.push(b',');
                        }
                        result.extend_from_slice(item.as_bytes());
                        first = false;
                    }
                }
                
                result.push(b'}');
                Ok(result)
            }
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Parallel object serialization error: {}", e)
            )),
        }
    }

    /// Serialize using sequential processing (fallback)
    fn serialize_sequential(&self, value: &Value) -> PyResult<Vec<u8>> {
        serde_json::to_vec(value).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Sequential JSON serialization error: {}", e)
            )
        })
    }
}

/// Optimized JSON Response class with parallel serialization
#[pyclass]
pub struct FastJSONResponse {
    serializer: ParallelJSONSerializer,
    content: Option<PyObject>,
    rendered_cache: Option<Vec<u8>>,
    status_code: u16,
}

#[pymethods]
impl FastJSONResponse {
    #[new]
    #[pyo3(signature = (content, status_code = 200, parallel_threshold = 10000))]
    fn new(content: PyObject, status_code: Option<u16>, parallel_threshold: Option<usize>) -> Self {
        Self {
            serializer: ParallelJSONSerializer::new(
                parallel_threshold.unwrap_or(10000), 
                32, 
                1000
            ),
            content: Some(content),
            rendered_cache: None,
            status_code: status_code.unwrap_or(200),
        }
    }

    /// Render the response content to JSON bytes
    fn render(&mut self, py: Python<'_>) -> PyResult<Vec<u8>> {
        // Return cached version if available
        if let Some(ref cached) = self.rendered_cache {
            return Ok(cached.clone());
        }

        if let Some(ref content) = self.content {
            let content_bound = content.bind(py);
            
            // Try fast path first
            if let Ok(Some(fast_result)) = self.serializer.serialize_fast_path(py, &content_bound) {
                self.rendered_cache = Some(fast_result.clone());
                return Ok(fast_result);
            }

            // Use parallel serialization for complex objects
            let result = self.serializer.serialize(py, &content_bound, None)?;
            self.rendered_cache = Some(result.clone());
            Ok(result)
        } else {
            Ok(b"null".to_vec())
        }
    }

    /// Get the status code
    fn get_status_code(&self) -> u16 {
        self.status_code
    }

    /// Set new content (clears cache)
    fn set_content(&mut self, content: PyObject) {
        self.content = Some(content);
        self.rendered_cache = None;
    }

    /// Get rendering statistics
    fn get_stats(&self) -> HashMap<String, usize> {
        self.serializer.get_cache_stats()
    }
}

/// Batch JSON serializer for processing multiple objects concurrently
#[pyclass]
pub struct BatchJSONSerializer {
    serializer: ParallelJSONSerializer,
}

#[pymethods]
impl BatchJSONSerializer {
    #[new]
    #[pyo3(signature = (parallel_threshold = 10000, max_depth = 32, cache_size_limit = 2000))]
    fn new(parallel_threshold: usize, max_depth: usize, cache_size_limit: usize) -> Self {
        Self {
            serializer: ParallelJSONSerializer::new(parallel_threshold, max_depth, cache_size_limit),
        }
    }

    /// Serialize multiple objects in parallel
    fn serialize_batch(&self, py: Python<'_>, objects: Vec<PyObject>) -> PyResult<Vec<Vec<u8>>> {
        // First convert all Python objects to thread-safe serde_json::Value
        let mut values = Vec::with_capacity(objects.len());
        for obj in objects {
            let obj_bound = obj.bind(py);
            values.push(self.serializer.python_to_value(py, &obj_bound, 0)?);
        }

        // Now parallelize the serialization
        let results: Result<Vec<_>, _> = values
            .into_par_iter()
            .map(|value| -> Result<Vec<u8>, serde_json::Error> {
                serde_json::to_vec(&value)
            })
            .collect();

        results.map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Batch serialization failed: {}", e)
            )
        })
    }

    /// Serialize multiple objects and combine into a JSON array
    fn serialize_batch_to_array(&self, py: Python<'_>, objects: Vec<PyObject>) -> PyResult<Vec<u8>> {
        let serialized_objects = self.serialize_batch(py, objects)?;
        
        let mut result = Vec::new();
        result.push(b'[');
        
        for (i, obj_bytes) in serialized_objects.iter().enumerate() {
            if i > 0 {
                result.push(b',');
            }
            result.extend_from_slice(obj_bytes);
        }
        
        result.push(b']');
        Ok(result)
    }
}

/// Register JSON serialization functions and classes
pub fn register_json_serializer(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<ParallelJSONSerializer>()?;
    m.add_class::<FastJSONResponse>()?;
    m.add_class::<BatchJSONSerializer>()?;
    Ok(())
}
