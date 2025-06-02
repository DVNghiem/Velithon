use pyo3::prelude::*;
use pyo3::types::{PyDict, PyBytes};
use crate::vsp::message::VSPMessage;

/// VSP Protocol handler for connection management
#[derive(Debug, Clone)]
#[pyclass]
pub struct VSPProtocol {
    buffer: Vec<u8>,
    expected_length: Option<usize>,
    connected: bool,
}

#[pymethods]
impl VSPProtocol {
    #[new]
    pub fn new() -> Self {
        Self {
            buffer: Vec::new(),
            expected_length: None,
            connected: false,
        }
    }

    /// Handle connection made event
    pub fn connection_made(&mut self) {
        self.connected = true;
        println!("VSP connection established");
    }

    /// Handle connection lost event
    pub fn connection_lost(&mut self, exc: Option<String>) {
        self.connected = false;
        if let Some(error) = exc {
            println!("VSP connection lost: {}", error);
        } else {
            println!("VSP connection closed normally");
        }
    }

    /// Process received data and return complete messages
    pub fn data_received<'py>(&mut self, py: Python<'py>, data: Vec<u8>) -> PyResult<Vec<VSPMessage>> {
        self.buffer.extend_from_slice(&data);
        let mut messages = Vec::new();

        while self.buffer.len() >= 4 {
            // Read message length from first 4 bytes
            if self.expected_length.is_none() {
                let length_bytes = &self.buffer[0..4];
                let length = u32::from_be_bytes([
                    length_bytes[0],
                    length_bytes[1],
                    length_bytes[2], 
                    length_bytes[3],
                ]) as usize;
                self.expected_length = Some(length);
            }

            let expected_length = self.expected_length.unwrap();
            
            // Check if we have complete message
            if self.buffer.len() < 4 + expected_length {
                break; // Wait for more data
            }

            // Extract message data
            let message_data = self.buffer[4..4 + expected_length].to_vec();
            
            // Remove processed data
            self.buffer.drain(0..4 + expected_length);
            self.expected_length = None;

            // Deserialize message
            match self.parse_message(py, message_data) {
                Ok(message) => messages.push(message),
                Err(e) => {
                    eprintln!("Failed to parse VSP message: {}", e);
                    continue; // Skip invalid messages
                }
            }
        }

        Ok(messages)
    }

    /// Send a message through the protocol
    pub fn send_message<'py>(&self, py: Python<'py>, message: &mut VSPMessage) -> PyResult<Vec<u8>> {
        let message_bytes = message.to_bytes(py)?;
        let message_data = message_bytes.as_bytes();
        
        let length = message_data.len() as u32;
        let length_bytes = length.to_be_bytes();
        
        let mut result = Vec::with_capacity(4 + message_data.len());
        result.extend_from_slice(&length_bytes);
        result.extend_from_slice(message_data);
        
        Ok(result)
    }

    /// Handle an incoming message and generate response
    pub fn handle_message<'py>(&self, py: Python<'py>, message: VSPMessage) -> PyResult<Option<VSPMessage>> {
        // This would be implemented by the service handler
        // For now, just echo back a simple response
        if !message.is_response {
            let response = VSPMessage::new(
                message.request_id.clone(),
                message.service.clone(),
                message.endpoint.clone(),
                PyDict::new(py),
                Some(true),
            )?;
            Ok(Some(response))
        } else {
            // It's already a response, don't respond to responses
            Ok(None)
        }
    }

    /// Check if protocol is connected
    pub fn is_connected(&self) -> bool {
        self.connected
    }

    /// Get buffer information
    pub fn get_buffer_info(&self) -> (usize, Option<usize>) {
        (self.buffer.len(), self.expected_length)
    }

    /// Clear the buffer
    pub fn clear_buffer(&mut self) {
        self.buffer.clear();
        self.expected_length = None;
    }

    fn __repr__(&self) -> String {
        format!(
            "VSPProtocol(connected={}, buffer_size={}, expected_length={:?})",
            self.connected,
            self.buffer.len(),
            self.expected_length
        )
    }
}

impl VSPProtocol {
    fn parse_message<'py>(&self, py: Python<'py>, data: Vec<u8>) -> PyResult<VSPMessage> {
        let py_bytes = PyBytes::new(py, &data);
        let py_type = py.get_type::<VSPMessage>();
        VSPMessage::from_bytes(&py_type, py_bytes)
    }
}

/// Protocol factory for creating VSP protocols
#[pyclass]
#[derive(Debug)]
pub struct VSPProtocolFactory {
    // Protocol configuration
    max_message_size: usize,
    timeout_seconds: u64,
}

#[pymethods]
impl VSPProtocolFactory {
    #[new]
    #[pyo3(signature = (max_message_size = 1048576, timeout_seconds = 30))]
    pub fn new(max_message_size: Option<usize>, timeout_seconds: Option<u64>) -> Self {
        Self {
            max_message_size: max_message_size.unwrap_or(1048576), // 1MB default
            timeout_seconds: timeout_seconds.unwrap_or(30),
        }
    }

    /// Create a new protocol instance
    pub fn create_protocol(&self) -> VSPProtocol {
        VSPProtocol::new()
    }

    /// Get factory configuration
    pub fn get_config(&self) -> (usize, u64) {
        (self.max_message_size, self.timeout_seconds)
    }

    fn __repr__(&self) -> String {
        format!(
            "VSPProtocolFactory(max_message_size={}, timeout_seconds={})",
            self.max_message_size, self.timeout_seconds
        )
    }
}
