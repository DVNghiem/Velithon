use pyo3::prelude::*;
use pyo3::sync::GILOnceCell;
use std::collections::HashMap;
use std::sync::Mutex;

static SIGNATURE_CACHE: GILOnceCell<Mutex<HashMap<String, PyObject>>> = GILOnceCell::new();

#[pyfunction(name = "di_cached_signature")]
fn cached_signature(py: Python, func: Bound<PyAny>) -> PyResult<PyObject> {
    let cache_mutex = SIGNATURE_CACHE.get_or_init(py, || Mutex::new(HashMap::new()));
    let mut cache = cache_mutex.lock().unwrap();

    let func_obj = func.unbind();

    // convert function/object to string representation
    let func_str = format!("{:?}", func_obj);

    if let Some(cached_func) = cache.get(&func_str) {
        return Ok(cached_func.clone_ref(py));
    }
    // If not cached, create a new function and cache it
    // import signature module
    let inspect_module = PyModule::import(py, "inspect")?;
    let func = inspect_module.getattr("signature")?.call1((func_obj,))?;
    cache.insert(func_str, func.clone().unbind());
    Ok(func.unbind())
}

/// Register all DI functions and classes with Python
pub fn register_di(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Register individual DI classes

    // Register utility functions
    m.add_function(wrap_pyfunction!(cached_signature, m)?)?;
    Ok(())
}
