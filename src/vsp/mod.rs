use pyo3::prelude::*;

pub mod message;
pub mod transport;
pub mod protocol;
pub mod client;
pub mod manager;
pub mod service;
pub mod discovery;
pub mod load_balancer;
pub mod connection_pool;

use message::{VSPMessage, VSPError};
use transport::{TCPTransport, WebSocketTransport};
use protocol::{VSPProtocol, VSPProtocolFactory};
use client::VSPClient;
use manager::{VSPManager, WorkerType};
use service::{ServiceInfo, HealthStatus};
use discovery::{StaticDiscovery, MDNSDiscovery, ConsulDiscovery, DiscoveryType};
use load_balancer::{RoundRobinBalancer, WeightedBalancer, RandomBalancer};
use connection_pool::ConnectionPool;

/// Register VSP components with Python
pub fn register_vsp(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Register message types
    m.add_class::<VSPMessage>()?;
    m.add_class::<VSPError>()?;
    
    // Register transport types
    m.add_class::<TCPTransport>()?;
    m.add_class::<WebSocketTransport>()?;
    
    // Register protocol types  
    m.add_class::<VSPProtocol>()?;
    m.add_class::<VSPProtocolFactory>()?;
    
    // Register client types
    m.add_class::<VSPClient>()?;
    
    // Register manager types
    m.add_class::<VSPManager>()?;
    m.add_class::<WorkerType>()?;
    
    // Register service types
    m.add_class::<ServiceInfo>()?;
    m.add_class::<HealthStatus>()?;
    
    // Register discovery types
    m.add_class::<StaticDiscovery>()?;
    m.add_class::<MDNSDiscovery>()?;
    m.add_class::<ConsulDiscovery>()?;
    m.add_class::<DiscoveryType>()?;
    
    // Register load balancer types
    m.add_class::<RoundRobinBalancer>()?;
    m.add_class::<WeightedBalancer>()?;
    m.add_class::<RandomBalancer>()?;
    
    // Register connection pool
    m.add_class::<ConnectionPool>()?;
    
    Ok(())
}
