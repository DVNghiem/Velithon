use pyo3::prelude::*;


#[pyclass]
struct ResponseCache {
    max_size: usize,
    cache: std::collections::HashMap<String, PyObject>,
    access_order: Vec<String>,
}

#[pymethods]
impl ResponseCache {

    // default max size is 100
    #[pyo3(signature = (max_size = 100))]
    #[new]
    fn new(max_size: usize) -> Self {
        ResponseCache {
            max_size,
            cache: std::collections::HashMap::new(),
            access_order: Vec::new(),
        }
    }

    fn get(&mut self, py: Python, key: String) -> Option<PyObject> {
        if let Some(value) = self.cache.get(&key) {
            // Move the accessed key to the end of the access order
            self.access_order.retain(|k| k != &key);
            self.access_order.push(key.clone());
            Some(value.clone_ref(py))
        } else {
            None
        }
    }

    fn put(&mut self, key: String, value: PyObject) {
        if self.cache.len() >= self.max_size {
            // Remove the least recently used item
            if let Some(old_key) = self.access_order.pop() {
                self.cache.remove(&old_key);
            }
        }
        self.cache.insert(key.clone(), value);
        // Add the new key to the access order
        self.access_order.push(key);
    }
}


/// Register all performance functions and classes with Python
pub fn register_performance(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Register individual performance classes
    m.add_class::<ResponseCache>()?;
    
    Ok(())
}
