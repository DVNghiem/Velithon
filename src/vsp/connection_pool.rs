use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use crate::vsp::transport::TCPTransport;

/// Connection pool for managing transports
#[pyclass]
#[derive(Debug)]
pub struct ConnectionPool {
    transports: Arc<Mutex<HashMap<String, Vec<Arc<Mutex<TCPTransport>>>>>>,
    max_connections: usize,
}

#[pymethods]
impl ConnectionPool {
    #[new]
    #[pyo3(signature = (max_connections = 10))]
    pub fn new(max_connections: Option<usize>) -> Self {
        Self {
            transports: Arc::new(Mutex::new(HashMap::new())),
            max_connections: max_connections.unwrap_or(10),
        }
    }

    /// Remove closed transports
    pub fn cleanup(&self) -> PyResult<usize> {
        let mut transports = self.transports.lock().unwrap();
        let mut cleaned = 0;
        
        for (_, transport_list) in transports.iter_mut() {
            let initial_len = transport_list.len();
            transport_list.retain(|transport| {
                let transport_lock = transport.lock().unwrap();
                !transport_lock.is_closed()
            });
            cleaned += initial_len - transport_list.len();
        }
        
        Ok(cleaned)
    }

    /// Get pool statistics
    pub fn get_stats(&self) -> PyResult<(usize, usize)> {
        let transports = self.transports.lock().unwrap();
        let total_endpoints = transports.len();
        let total_connections: usize = transports.values().map(|v| v.len()).sum();
        Ok((total_endpoints, total_connections))
    }

    fn __repr__(&self) -> String {
        let transports = self.transports.lock().unwrap();
        let total_connections: usize = transports.values().map(|v| v.len()).sum();
        format!(
            "ConnectionPool(endpoints={}, connections={}, max={})",
            transports.len(),
            total_connections,
            self.max_connections
        )
    }
}

impl ConnectionPool {
    /// Get or create a transport for the given endpoint (internal use only)
    pub fn get_transport_internal(&self, endpoint: &str) -> Option<Arc<Mutex<TCPTransport>>> {
        let mut transports = self.transports.lock().unwrap();
        let transport_list = transports.entry(endpoint.to_string()).or_insert_with(Vec::new);
        
        // Find an available transport
        for transport in transport_list.iter() {
            let transport_lock = transport.lock().unwrap();
            if !transport_lock.is_closed() {
                return Some(transport.clone());
            }
        }
        
        // Create new transport if under limit
        if transport_list.len() < self.max_connections {
            // Parse endpoint to get host and port (basic implementation)
            let parts: Vec<&str> = endpoint.split(':').collect();
            let host = parts.get(0).unwrap_or(&"localhost").to_string();
            let port = parts.get(1).and_then(|p| p.parse().ok()).unwrap_or(8080);
            
            let new_transport = Arc::new(Mutex::new(TCPTransport::new(host, port)));
            transport_list.push(new_transport.clone());
            Some(new_transport)
        } else {
            None
        }
    }
}
