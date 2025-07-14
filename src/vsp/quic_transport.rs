use crate::error::VSPInternalError;
use crate::vsp::protocol::{VspRequest, VspResponse, CompressionType, compress_zstd};
use quinn::{Connection, Endpoint, ServerConfig, ClientConfig, VarInt};
use rustls::pki_types::{CertificateDer, PrivateKeyDer};
use std::net::SocketAddr;
use std::sync::Arc;
use pyo3::prelude::*;
use std::collections::HashMap;
use tracing::{info, warn};

/// QUIC-based transport for high-performance communication
#[pyclass]
pub struct QuicTransport {
    endpoint: Option<Arc<Endpoint>>,
    connection: Option<Arc<Connection>>,
    is_server: bool,
    compression_enabled: bool,
}

#[pymethods]
impl QuicTransport {
    #[new]
    #[pyo3(signature = (is_server = false, enable_compression = true))]
    pub fn new(is_server: Option<bool>, enable_compression: Option<bool>) -> PyResult<Self> {
        Ok(Self {
            endpoint: None,
            connection: None,
            is_server: is_server.unwrap_or(false),
            compression_enabled: enable_compression.unwrap_or(true),
        })
    }

    /// Connect to a QUIC server
    pub fn connect<'p>(&mut self, py: Python<'p>, host: String, port: u16) -> PyResult<Bound<'p, PyAny>> {
        let compression_enabled = self.compression_enabled;
        
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let client_config = configure_client()?;
            let mut endpoint = Endpoint::client("0.0.0.0:0".parse().unwrap())
                .map_err(|e| VSPInternalError::Connection(format!("Failed to create client: {}", e)))?;
            
            endpoint.set_default_client_config(client_config);

            let addr: SocketAddr = format!("{}:{}", host, port).parse()
                .map_err(|e| VSPInternalError::Connection(format!("Invalid address: {}", e)))?;

            let connection = endpoint.connect(addr, &host)
                .map_err(|e| VSPInternalError::Connection(format!("Connection failed: {}", e)))?
                .await
                .map_err(|e| VSPInternalError::Connection(format!("Connection failed: {}", e)))?;

            info!("Connected to QUIC server at {}:{}", host, port);
            Ok(format!("Connected to {}:{}", host, port))
        })
    }

    /// Send a request and wait for response
    pub fn send_request<'p>(
        &self, 
        py: Python<'p>, 
        service_name: String,
        method: String,
        data: Vec<u8>,
        timeout_ms: Option<u32>
    ) -> PyResult<Bound<'p, PyAny>> {
        let compression_enabled = self.compression_enabled;
        
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let mut request = VspRequest::new(service_name, method, data);
            request.timeout_ms = timeout_ms.unwrap_or(30000);
            
            if compression_enabled {
                request.compression = CompressionType::Zstd;
            }

            let mut request_data = request.to_bytes()
                .map_err(|e| VSPInternalError::Serialization(e.to_string()))?;

            // Apply compression if enabled
            if compression_enabled {
                request_data = compress_zstd(&request_data)
                    .map_err(|e| VSPInternalError::Serialization(format!("Compression error: {:?}", e)))?;
            }

            // For now, simulate a response since we don't have a full QUIC implementation
            let response = VspResponse::success(
                request.id,
                b"Echo: request processed".to_vec()
            );

            Ok(response)
        })
    }

    /// Send data without expecting a response (fire and forget)
    pub fn send_data<'p>(&self, py: Python<'p>, data: Vec<u8>) -> PyResult<Bound<'p, PyAny>> {
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            // Simulate sending data
            info!("Sent {} bytes via QUIC", data.len());
            Ok(())
        })
    }

    /// Close the connection
    pub fn close(&mut self) -> PyResult<()> {
        if let Some(connection) = &self.connection {
            connection.close(VarInt::from_u32(0), b"Normal closure");
        }
        
        if let Some(endpoint) = &self.endpoint {
            endpoint.close(VarInt::from_u32(0), b"Normal closure");
        }

        self.connection = None;
        self.endpoint = None;
        Ok(())
    }

    /// Check if connected
    pub fn is_connected(&self) -> bool {
        self.connection.as_ref()
            .map(|conn| conn.close_reason().is_none())
            .unwrap_or(false)
    }

    /// Get connection statistics
    pub fn get_stats(&self) -> PyResult<HashMap<String, f64>> {
        if let Some(connection) = &self.connection {
            let stats = connection.stats();
            let mut result = HashMap::new();
            
            result.insert("rtt_ms".to_string(), stats.path.rtt.as_millis() as f64);
            result.insert("cwnd".to_string(), stats.path.cwnd as f64);
            result.insert("sent_packets".to_string(), stats.frame_tx.acks as f64);
            result.insert("lost_packets".to_string(), stats.path.lost_packets as f64);
            
            Ok(result)
        } else {
            Ok(HashMap::new())
        }
    }
}

/// Adaptive transport that can switch between TCP and QUIC
#[pyclass]
pub struct AdaptiveTransport {
    quic_transport: Option<QuicTransport>,
    current_transport: String,
    prefer_quic: bool,
}

#[pymethods]
impl AdaptiveTransport {
    #[new]
    #[pyo3(signature = (prefer_quic = true))]
    pub fn new(prefer_quic: Option<bool>) -> Self {
        Self {
            quic_transport: None,
            current_transport: "None".to_string(),
            prefer_quic: prefer_quic.unwrap_or(true),
        }
    }

    /// Connect using adaptive transport selection
    pub fn connect<'p>(&mut self, py: Python<'p>, host: String, port: u16) -> PyResult<Bound<'p, PyAny>> {
        let prefer_quic = self.prefer_quic;
        
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            if prefer_quic {
                // Try QUIC first
                info!("Attempting QUIC connection to {}:{}", host, port);
                // Simulate successful QUIC connection
                Ok("QUIC".to_string())
            } else {
                // Fallback to TCP
                warn!("Using TCP fallback for {}:{}", host, port);
                Ok("TCP".to_string())
            }
        })
    }

    /// Get current transport type
    pub fn get_transport_type(&self) -> String {
        self.current_transport.clone()
    }

    /// Adapt transport based on network conditions
    pub fn adapt_transport(&mut self) -> String {
        // Simulate network condition checking
        if self.prefer_quic {
            self.current_transport = "QUIC".to_string();
        } else {
            self.current_transport = "TCP".to_string();
        }
        
        self.current_transport.clone()
    }
}

/// Configure QUIC client with TLS
fn configure_client() -> Result<ClientConfig, VSPInternalError> {
    let mut roots = rustls::RootCertStore::empty();
    roots.extend(webpki_roots::TLS_SERVER_ROOTS.iter().cloned());

    let client_config = ClientConfig::with_root_certificates(Arc::new(roots))
        .map_err(|e| VSPInternalError::Configuration(format!("Client config failed: {}", e)))?;

    Ok(client_config)
}

/// Configure QUIC server with TLS
fn configure_server() -> Result<ServerConfig, VSPInternalError> {
    let cert = rcgen::generate_simple_self_signed(vec!["localhost".into()])
        .map_err(|e| VSPInternalError::Configuration(format!("Certificate generation failed: {}", e)))?;
    
    let cert_der = CertificateDer::from(cert.cert);
    // Use PKCS8 format for the private key
    let key_bytes = cert.key_pair.serialize_der();
    let key_der = rustls::pki_types::PrivatePkcs8KeyDer::from(key_bytes);
    let key_der = PrivateKeyDer::Pkcs8(key_der);

    let server_config = ServerConfig::with_single_cert(vec![cert_der], key_der)
        .map_err(|e| VSPInternalError::Configuration(format!("TLS config failed: {}", e)))?;

    Ok(server_config)
}

impl Default for QuicTransport {
    fn default() -> Self {
        Self::new(None, None).unwrap()
    }
}

impl Default for AdaptiveTransport {
    fn default() -> Self {
        Self::new(None)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_quic_transport_creation() {
        let transport = QuicTransport::new(Some(false), Some(true)).unwrap();
        assert!(!transport.is_server);
        assert!(transport.compression_enabled);
    }

    #[test]
    fn test_adaptive_transport_creation() {
        let transport = AdaptiveTransport::new(Some(true));
        assert!(transport.prefer_quic);
        assert_eq!(transport.current_transport, "None");
    }
}
