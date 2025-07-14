use crate::vsp::protocol::{VspRequest, VspResponse};
use std::collections::HashMap;
use pyo3::prelude::*;
use tracing::info;

/// Simple VSP client for testing and basic operations
#[pyclass]
pub struct SimpleVSPClient {
    connected: bool,
    host: String,
    port: u16,
}

#[pymethods]
impl SimpleVSPClient {
    #[new]
    pub fn new() -> PyResult<Self> {
        Ok(Self {
            connected: false,
            host: String::new(),
            port: 0,
        })
    }

    /// Connect to a VSP server
    pub fn connect(&mut self, host: String, port: u16) -> PyResult<String> {
        self.host = host.clone();
        self.port = port;
        self.connected = true;
        
        info!("Connected to VSP server at {}:{}", host, port);
        Ok(format!("Connected to {}:{}", host, port))
    }

    /// Send a simple request
    pub fn send_request(
        &self,
        service_name: String,
        method: String,
        data: Vec<u8>,
        headers: Option<HashMap<String, String>>,
    ) -> PyResult<VspResponse> {
        if !self.connected {
            return Err(PyErr::new::<pyo3::exceptions::PyConnectionError, _>(
                "Not connected to server"
            ));
        }

        // Create request
        let mut request = VspRequest::new(service_name.clone(), method.clone(), data);
        request.timeout_ms = 30000;
        
        if let Some(h) = headers {
            request.headers = h;
        }

        // Simulate processing
        let response_data = format!("Echo: {} - {}", service_name, method).into_bytes();
        let response = VspResponse::success(request.id, response_data);
        
        info!("Sent request to service: {}", service_name);
        Ok(response)
    }

    /// Check if connected
    pub fn is_connected(&self) -> PyResult<bool> {
        Ok(self.connected)
    }

    /// Disconnect from server
    pub fn disconnect(&mut self) -> PyResult<()> {
        self.connected = false;
        self.host.clear();
        self.port = 0;
        
        info!("Disconnected from VSP server");
        Ok(())
    }

    /// Get connection info
    pub fn get_connection_info(&self) -> PyResult<HashMap<String, String>> {
        let mut info = HashMap::new();
        info.insert("host".to_string(), self.host.clone());
        info.insert("port".to_string(), self.port.to_string());
        info.insert("connected".to_string(), self.connected.to_string());
        
        Ok(info)
    }
}
