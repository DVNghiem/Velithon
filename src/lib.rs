use pyo3::prelude::*;

mod background;
mod convertors;
mod di;
mod logging;
mod performance;
mod vsp;

/// Velithon Rust Extensions
/// High-performance Rust implementations for critical Velithon components
#[pymodule]
fn _velithon(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Register background task classes and functions
    background::register_background(m.py(), m)?;
    
    // Register convertor classes and functions
    convertors::register_convertors(m.py(), m)?;
    
    // Register performance-related functions and classes
    performance::register_performance(m.py(), m)?;

    // Register dependency injection related functions and classes
    di::register_di(m.py(), m)?;

    // Register logging functions
    logging::register_logging(m.py(), m)?;
    
    // Register VSP (Velithon Service Protocol) components
    vsp::register_vsp(m.py(), m)?;

    Ok(())
}
