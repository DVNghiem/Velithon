use pyo3::prelude::*;

mod background;
mod convertors;
mod di;
mod headers;
mod json_encoder;
mod logging;
mod middleware;
mod performance;
mod routing;
mod template_engine;
mod vsp;
mod websocket;

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
    
    // Register JSON encoder functions
    json_encoder::register_json_encoder(m.py(), m)?;
    
    // Register routing optimization functions
    routing::register_routing(m.py(), m)?;
    
    // Register header processing functions
    headers::register_headers(m.py(), m)?;
    
    // Register middleware optimization functions
    middleware::register_middleware(m.py(), m)?;
    
    // Register template engine functions
    template_engine::register_template_engine(m.py(), m)?;
    
    // Register WebSocket optimization functions
    websocket::register_websocket(m.py(), m)?;

    Ok(())
}
