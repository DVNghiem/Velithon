use pyo3::prelude::*;

pub mod service;
use service::{ServiceInfo, HealthStatus};

/// Register VSP components with Python
pub fn register_vsp(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Register service types
    m.add_class::<ServiceInfo>()?;
    m.add_class::<HealthStatus>()?;
    
    Ok(())
}
