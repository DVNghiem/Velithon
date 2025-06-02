use pyo3::prelude::*;

/// Transport trait for VSP communication
pub trait VSPTransport: Send + Sync {
    fn get_type(&self) -> String;
    fn is_connected(&self) -> bool;
}

/// TCP Transport implementation
#[pyclass]
#[derive(Debug, Clone)]
pub struct TCPTransport {
    pub host: String,
    pub port: u16,
    pub connected: bool,
}

#[pymethods]
impl TCPTransport {
    #[new]
    pub fn new(host: String, port: u16) -> Self {
        Self {
            host,
            port,
            connected: false,
        }
    }

    #[getter]
    pub fn get_host(&self) -> &str {
        &self.host
    }

    #[getter]
    pub fn get_port(&self) -> u16 {
        self.port
    }

    #[getter]
    pub fn is_connected(&self) -> bool {
        self.connected
    }

    /// Connect to the TCP endpoint
    pub fn connect(&mut self) -> PyResult<()> {
        // Simplified connection for now - just mark as connected
        self.connected = true;
        Ok(())
    }

    /// Send data through the TCP connection
    pub fn send(&self, data: Vec<u8>) -> PyResult<usize> {
        if !self.connected {
            return Err(PyErr::new::<pyo3::exceptions::PyConnectionError, _>(
                "Not connected"
            ));
        }
        // For now, return the data length as if sent
        Ok(data.len())
    }

    /// Close the TCP connection
    pub fn close(&mut self) -> PyResult<()> {
        self.connected = false;
        Ok(())
    }

    /// Check if connection is closed
    pub fn is_closed(&self) -> bool {
        !self.connected
    }

    fn __repr__(&self) -> String {
        format!(
            "TCPTransport(host='{}', port={}, connected={})",
            self.host, self.port, self.connected
        )
    }
}

impl VSPTransport for TCPTransport {
    fn get_type(&self) -> String {
        "tcp".to_string()
    }

    fn is_connected(&self) -> bool {
        self.connected
    }
}

/// WebSocket Transport implementation
#[pyclass]
#[derive(Debug, Clone)]
pub struct WebSocketTransport {
    pub url: String,
    pub connected: bool,
}

#[pymethods]
impl WebSocketTransport {
    #[new]
    pub fn new(url: String) -> Self {
        Self {
            url,
            connected: false,
        }
    }

    #[getter]
    pub fn get_url(&self) -> &str {
        &self.url
    }

    #[getter]
    pub fn is_connected(&self) -> bool {
        self.connected
    }

    /// Connect to WebSocket
    pub fn connect(&mut self) -> PyResult<()> {
        self.connected = true;
        Ok(())
    }

    /// Send data through WebSocket
    pub fn send(&self, data: Vec<u8>) -> PyResult<usize> {
        if !self.connected {
            return Err(PyErr::new::<pyo3::exceptions::PyConnectionError, _>(
                "Not connected"
            ));
        }
        Ok(data.len())
    }

    /// Close WebSocket connection
    pub fn close(&mut self) -> PyResult<()> {
        self.connected = false;
        Ok(())
    }

    fn __repr__(&self) -> String {
        format!(
            "WebSocketTransport(url='{}', connected={})",
            self.url, self.connected
        )
    }
}

impl VSPTransport for WebSocketTransport {
    fn get_type(&self) -> String {
        "websocket".to_string()
    }

    fn is_connected(&self) -> bool {
        self.connected
    }
}
