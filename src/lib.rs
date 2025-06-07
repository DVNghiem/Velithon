#[cfg(not(any(
    target_env = "musl",
    target_os = "freebsd",
    target_os = "openbsd",
    target_os = "windows",
    feature = "mimalloc"
)))]
#[global_allocator]
static GLOBAL: tikv_jemallocator::Jemalloc = tikv_jemallocator::Jemalloc;

#[cfg(feature = "mimalloc")]
#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

use pyo3::prelude::*;

mod background;
mod convertors;
mod di;
mod logging;
mod performance;
mod routing;
mod vsp;
mod error;

/// Velithon Rust Extensions
/// High-performance Rust implementations for critical Velithon components
#[pymodule(gil_used = false)]
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
    
    // Register routing functions and classes
    routing::register_routing(m.py(), m)?;
    
    // Register VSP (Velithon Service Protocol) components
    vsp::register_vsp(m.py(), m)?;
    
    Ok(())
}
