use pyo3::prelude::*;
use pyo3::wrap_pyfunction;

pub mod service;
pub mod load_balancer;
pub mod transport;
pub mod message;
pub mod protocol;
pub mod quic_transport;
pub mod simple_vsp_client;

use service::{ServiceInfo, HealthStatus};

/// Register VSP components with Python
pub fn register_vsp(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Register service types
    m.add_class::<ServiceInfo>()?;
    m.add_class::<HealthStatus>()?;

    // Register legacy load balancer
    m.add_class::<load_balancer::LoadBalancer>()?;
    m.add_class::<load_balancer::RoundRobinBalancer>()?;
    m.add_class::<load_balancer::WeightedBalancer>()?;

    // Register legacy transport classes
    m.add_class::<transport::TCPTransport>()?;
    
    // Register protocol classes
    m.add_class::<protocol::VspRequest>()?;
    m.add_class::<protocol::VspResponse>()?;
    m.add_class::<protocol::MessageType>()?;
    m.add_class::<protocol::CompressionType>()?;
    
    // Register compression functions
    m.add_function(wrap_pyfunction!(protocol::compress_zstd, m)?)?;
    m.add_function(wrap_pyfunction!(protocol::decompress_zstd, m)?)?;
    m.add_function(wrap_pyfunction!(protocol::compress_gzip, m)?)?;
    m.add_function(wrap_pyfunction!(protocol::decompress_gzip, m)?)?;
    
    // Register new QUIC transport classes
    m.add_class::<quic_transport::QuicTransport>()?;
    m.add_class::<quic_transport::AdaptiveTransport>()?;
    
    // Register simple VSP client
    m.add_class::<simple_vsp_client::SimpleVSPClient>()?;
    
    Ok(())
}
