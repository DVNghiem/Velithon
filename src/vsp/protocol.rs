use pyo3::prelude::*;
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use uuid::Uuid;

/// Message types for VSP protocol
#[pyclass]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum MessageType {
    Request,
    Response,
    HealthCheck,
    ServiceDiscovery,
    Heartbeat,
}

/// Compression types
#[pyclass]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CompressionType {
    None,
    Zstd,
    Gzip,
}

/// Transport protocols
#[pyclass]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TransportType {
    Tcp,
    Quic,
    Auto,
}

/// VSP Request message
#[pyclass]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VspRequest {
    #[pyo3(get, set)]
    pub id: String,
    #[pyo3(get, set)]
    pub service_name: String,
    #[pyo3(get, set)]
    pub method: String,
    #[pyo3(get, set)]
    pub data: Vec<u8>,
    #[pyo3(get, set)]
    pub headers: HashMap<String, String>,
    #[pyo3(get, set)]
    pub timeout_ms: u32,
    #[pyo3(get, set)]
    pub compression: CompressionType,
}

/// VSP Response message
#[pyclass]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VspResponse {
    #[pyo3(get, set)]
    pub id: String,
    #[pyo3(get, set)]
    pub status_code: u32,
    #[pyo3(get, set)]
    pub data: Vec<u8>,
    #[pyo3(get, set)]
    pub headers: HashMap<String, String>,
    #[pyo3(get, set)]
    pub error_message: String,
    #[pyo3(get, set)]
    pub processing_time_us: u64,
}

#[pymethods]
impl VspRequest {
    #[new]
    pub fn new(service_name: String, method: String, data: Vec<u8>) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            service_name,
            method,
            data,
            headers: HashMap::new(),
            timeout_ms: 30000,
            compression: CompressionType::Zstd,
        }
    }

    pub fn add_header(&mut self, key: String, value: String) {
        self.headers.insert(key, value);
    }

    pub fn to_bytes(&self) -> PyResult<Vec<u8>> {
        serde_json::to_vec(self)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Serialization error: {}", e)
            ))
    }

    #[staticmethod]
    pub fn from_bytes(data: &[u8]) -> PyResult<Self> {
        serde_json::from_slice(data)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Deserialization error: {}", e)
            ))
    }
}

#[pymethods]
impl VspResponse {
    #[new]
    pub fn new(id: String, status_code: u32, data: Vec<u8>) -> Self {
        Self {
            id,
            status_code,
            data,
            headers: HashMap::new(),
            error_message: String::new(),
            processing_time_us: 0,
        }
    }

    #[staticmethod]
    pub fn success(id: String, data: Vec<u8>) -> Self {
        Self::new(id, 200, data)
    }

    #[staticmethod]
    pub fn error(id: String, status_code: u32, error_message: String) -> Self {
        let mut response = Self::new(id, status_code, Vec::new());
        response.error_message = error_message;
        response
    }

    pub fn is_success(&self) -> bool {
        self.status_code >= 200 && self.status_code < 300
    }

    pub fn add_header(&mut self, key: String, value: String) {
        self.headers.insert(key, value);
    }

    pub fn to_bytes(&self) -> PyResult<Vec<u8>> {
        serde_json::to_vec(self)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Serialization error: {}", e)
            ))
    }

    #[staticmethod]
    pub fn from_bytes(data: &[u8]) -> PyResult<Self> {
        serde_json::from_slice(data)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Deserialization error: {}", e)
            ))
    }
}

// Compression utilities
#[pyfunction]
pub fn compress_zstd(data: &[u8]) -> PyResult<Vec<u8>> {
    zstd::bulk::compress(data, 3)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("Zstd compression error: {}", e)
        ))
}

#[pyfunction]
pub fn decompress_zstd(data: &[u8]) -> PyResult<Vec<u8>> {
    zstd::bulk::decompress(data, 1024 * 1024) // 1MB max
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("Zstd decompression error: {}", e)
        ))
}

#[pyfunction]
pub fn compress_gzip(data: &[u8]) -> PyResult<Vec<u8>> {
    use flate2::{write::GzEncoder, Compression};
    use std::io::Write;

    let mut encoder = GzEncoder::new(Vec::new(), Compression::default());
    encoder.write_all(data)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("Gzip write error: {}", e)
        ))?;
    encoder.finish()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("Gzip finish error: {}", e)
        ))
}

#[pyfunction]
pub fn decompress_gzip(data: &[u8]) -> PyResult<Vec<u8>> {
    use flate2::read::GzDecoder;
    use std::io::Read;

    let mut decoder = GzDecoder::new(data);
    let mut decompressed = Vec::new();
    decoder.read_to_end(&mut decompressed)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("Gzip decompression error: {}", e)
        ))?;
    Ok(decompressed)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_request_creation() {
        let request = VspRequest::new(
            "test-service".to_string(),
            "test-method".to_string(),
            b"test data".to_vec(),
        );
        
        assert_eq!(request.service_name, "test-service");
        assert_eq!(request.method, "test-method");
        assert_eq!(request.data, b"test data");
        assert!(!request.id.is_empty());
    }

    #[test]
    fn test_response_creation() {
        let response = VspResponse::success(
            "test-id".to_string(),
            b"response data".to_vec(),
        );
        
        assert_eq!(response.id, "test-id");
        assert_eq!(response.status_code, 200);
        assert!(response.is_success());
    }

    #[test]
    fn test_serialization() {
        let request = VspRequest::new(
            "test-service".to_string(),
            "test-method".to_string(),
            b"test data".to_vec(),
        );
        
        let bytes = request.to_bytes().unwrap();
        let deserialized = VspRequest::from_bytes(&bytes).unwrap();
        
        assert_eq!(request.service_name, deserialized.service_name);
        assert_eq!(request.method, deserialized.method);
        assert_eq!(request.data, deserialized.data);
    }

    #[test]
    fn test_compression() {
        let data = b"hello world".repeat(100);
        let compressed = compress_zstd(&data).unwrap();
        let decompressed = decompress_zstd(&compressed).unwrap();
        
        assert_eq!(data, decompressed);
        assert!(compressed.len() < data.len());
    }
}
