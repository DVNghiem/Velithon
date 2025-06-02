use pyo3::prelude::*;

mod convertors;
mod performance;

/// Velithon Rust Extensions
/// High-performance Rust implementations for critical Velithon components
#[pymodule]
fn _velithon(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Register convertor classes and functions
    convertors::register_convertors(m.py(), m)?;
    // Register performance-related functions and classes
    performance::register_performance(m.py(), m)?;
    
    Ok(())
}
