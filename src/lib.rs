use pyo3::prelude::*;

mod convertors;

/// Velithon Rust Extensions
/// High-performance Rust implementations for critical Velithon components
#[pymodule]
fn _velithon(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Register convertor classes and functions
    convertors::register_convertors(m.py(), m)?;
    
    Ok(())
}
