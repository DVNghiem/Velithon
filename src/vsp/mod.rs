use pyo3::prelude::*;

pub mod service;
pub mod load_balancer;
pub mod transport;
pub mod message;

use service::{ServiceInfo, HealthStatus};

/// Register VSP components with Python
pub fn register_vsp(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Register service types
    m.add_class::<ServiceInfo>()?;
    m.add_class::<HealthStatus>()?;

    // Register load balancer
    m.add_class::<load_balancer::LoadBalancer>()?;
    m.add_class::<load_balancer::RoundRobinBalancer>()?;
    m.add_class::<load_balancer::WeightedBalancer>()?;

    // Register transport classes
    m.add_class::<transport::TCPTransport>()?;
    
    Ok(())
}
