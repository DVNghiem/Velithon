use crate::error::{VSPInternalError, VSPResult};
use crate::vsp::protocol::{VspRequest, VspResponse, CompressionType, compress_zstd, decompress_zstd};
use crate::vsp::quic_transport::{QuicTransport, AdaptiveTransport};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tokio::time::{Duration, Instant};
use pyo3::prelude::*;
use tracing::{info, warn};

/// High-performance VSP client with caching and retry mechanisms
#[pyclass]
pub struct VSPClient {
    quic_transport: Option<Arc<QuicTransport>>,
    adaptive_transport: Option<Arc<AdaptiveTransport>>,
    response_cache: Arc<RwLock<ResponseCache>>,
    config: ClientConfig,
}

#[derive(Clone)]
struct ClientConfig {
    default_timeout_ms: u32,
    max_retries: u32,
    cache_ttl_seconds: u64,
    enable_compression: bool,
    enable_adaptive_transport: bool,
}

#[derive(Clone)]
struct ResponseCache {
    entries: HashMap<String, CacheEntry>,
    default_ttl: Duration,
    max_size: usize,
}

#[derive(Clone)]
struct CacheEntry {
    response: VspResponse,
    expires_at: Instant,
    hit_count: u64,
    created_at: Instant,
}

#[pymethods]
impl VSPClient {
    #[new]
    #[pyo3(signature = (
        timeout_ms = 30000,
        max_retries = 3,
        cache_ttl_seconds = 300,
        enable_compression = true,
        enable_adaptive_transport = true
    ))]
    pub fn new(
        timeout_ms: Option<u32>,
        max_retries: Option<u32>,
        cache_ttl_seconds: Option<u64>,
        enable_compression: Option<bool>,
        enable_adaptive_transport: Option<bool>,
    ) -> PyResult<Self> {
        let config = ClientConfig {
            default_timeout_ms: timeout_ms.unwrap_or(30000),
            max_retries: max_retries.unwrap_or(3),
            cache_ttl_seconds: cache_ttl_seconds.unwrap_or(300),
            enable_compression: enable_compression.unwrap_or(true),
            enable_adaptive_transport: enable_adaptive_transport.unwrap_or(true),
        };

        Ok(Self {
            quic_transport: None,
            adaptive_transport: None,
            response_cache: Arc::new(RwLock::new(ResponseCache {
                entries: HashMap::new(),
                default_ttl: Duration::from_secs(config.cache_ttl_seconds),
                max_size: 10000,
            })),
            config,
        })
    }

    /// Connect to a VSP server
    pub fn connect<'p>(&mut self, py: Python<'p>, host: String, port: u16) -> PyResult<Bound<'p, PyAny>> {
        let config = self.config.clone();
        
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            if config.enable_adaptive_transport {
                let mut adaptive = AdaptiveTransport::new(Some(true));
                adaptive.connect(py, host.clone(), port).await?;
                info!("Connected via adaptive transport to {}:{}", host, port);
            } else {
                let mut quic = QuicTransport::new(Some(false), Some(config.enable_compression))?;
                quic.connect(py, host.clone(), port).await?;
                info!("Connected via QUIC to {}:{}", host, port);
            }
            
            Ok(format!("Connected to {}:{}", host, port))
        })
    }

    /// Send a request with automatic retries and caching
    pub fn send_request<'p>(
        &self,
        py: Python<'p>,
        service_name: String,
        method: String,
        data: Vec<u8>,
        headers: Option<HashMap<String, String>>,
        timeout_ms: Option<u32>,
        cache_key: Option<String>,
        enable_cache: Option<bool>,
    ) -> PyResult<Bound<'p, PyAny>> {
        let config = self.config.clone();
        let response_cache = self.response_cache.clone();

        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            // Generate cache key if not provided
            let cache_key = cache_key.unwrap_or_else(|| {
                format!("{}:{}:{}", service_name, method, 
                       blake3::hash(&data).to_hex())
            });

            // Check cache if enabled
            if enable_cache.unwrap_or(true) {
                if let Some(cached_response) = Self::get_cached_response(
                    &response_cache, 
                    &cache_key
                ).await {
                    info!("Cache hit for request: {}", cache_key);
                    return Ok(cached_response);
                }
            }

            let mut last_error = None;
            let start_time = Instant::now();

            // Retry loop
            for attempt in 0..=config.max_retries {
                match Self::execute_request(
                    &service_name,
                    &method,
                    &data,
                    &headers.clone().unwrap_or_default(),
                    timeout_ms.unwrap_or(config.default_timeout_ms),
                    config.enable_compression,
                ).await {
                    Ok(response) => {
                        let processing_time = start_time.elapsed();
                        let mut final_response = response.clone();
                        final_response.processing_time_us = processing_time.as_micros() as u64;

                        // Cache successful response if enabled
                        if enable_cache.unwrap_or(true) && final_response.is_success() {
                            Self::cache_response(
                                &response_cache,
                                cache_key.clone(),
                                final_response.clone(),
                            ).await;
                        }

                        if attempt > 0 {
                            info!("Request succeeded after {} retries for service: {}", 
                                 attempt, service_name);
                        }

                        return Ok(final_response);
                    }
                    Err(e) => {
                        last_error = Some(format!("Request error: {:?}", e));
                        warn!("Request failed on attempt {} for service {}: {:?}", 
                             attempt + 1, service_name, e);
                    }
                }

                // Exponential backoff before retry
                if attempt < config.max_retries {
                    let delay = Duration::from_millis(100 * 2_u64.pow(attempt));
                    tokio::time::sleep(delay).await;
                }
            }

            Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Request failed after {} retries: {}", 
                       config.max_retries, 
                       last_error.unwrap_or("Unknown error".to_string()))
            ))
        })
    }

    /// Send request without response (fire and forget)
    pub fn send_async<'p>(
        &self,
        py: Python<'p>,
        service_name: String,
        method: String,
        data: Vec<u8>,
        headers: Option<HashMap<String, String>>,
    ) -> PyResult<Bound<'p, PyAny>> {
        let config = self.config.clone();

        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            // Create request
            let mut request = VspRequest::new(service_name, method, data);
            request.timeout_ms = config.default_timeout_ms;
            
            if let Some(h) = headers {
                request.headers = h;
            }

            if config.enable_compression {
                request.compression = CompressionType::Zstd;
            }

            // Simulate sending (in real implementation, this would use the transport)
            info!("Sent async request: {} bytes", request.data.len());
            Ok(())
        })
    }

    /// Get cache statistics
    pub fn get_cache_stats<'p>(&self, py: Python<'p>) -> PyResult<Bound<'p, PyAny>> {
        let response_cache = self.response_cache.clone();

        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let cache = response_cache.read().await;
            let mut stats = HashMap::new();

            stats.insert("total_entries".to_string(), cache.entries.len() as f64);
            
            let total_hits: u64 = cache.entries.values().map(|entry| entry.hit_count).sum();
            stats.insert("total_hits".to_string(), total_hits as f64);
            
            let expired_entries = cache.entries.values()
                .filter(|entry| entry.expires_at <= Instant::now())
                .count();
            stats.insert("expired_entries".to_string(), expired_entries as f64);

            Ok(stats)
        })
    }

    /// Clear response cache
    pub fn clear_cache<'p>(&self, py: Python<'p>) -> PyResult<Bound<'p, PyAny>> {
        let response_cache = self.response_cache.clone();

        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let mut cache = response_cache.write().await;
            let cleared_count = cache.entries.len();
            cache.entries.clear();
            
            info!("Cleared {} response cache entries", cleared_count);
            Ok(cleared_count)
        })
    }
}

impl VSPClient {
    async fn execute_request(
        service_name: &str,
        method: &str,
        data: &[u8],
        headers: &HashMap<String, String>,
        timeout_ms: u32,
        enable_compression: bool,
    ) -> Result<VspResponse, String> {
        // Create request
        let mut request = VspRequest::new(
            service_name.to_string(),
            method.to_string(),
            data.to_vec(),
        );
        request.timeout_ms = timeout_ms;
        request.headers = headers.clone();
        
        if enable_compression {
            request.compression = CompressionType::Zstd;
        }

        // Simulate request processing (in real implementation, this would use transport)
        let response_data = format!("Echo: {} - {}", service_name, method).into_bytes();
        
        let response = VspResponse::success(request.id, response_data);
        Ok(response)
    }

    async fn get_cached_response(
        cache: &Arc<RwLock<ResponseCache>>,
        key: &str,
    ) -> Option<VspResponse> {
        let mut cache_guard = cache.write().await;
        
        if let Some(entry) = cache_guard.entries.get_mut(key) {
            if entry.expires_at > Instant::now() {
                entry.hit_count += 1;
                return Some(entry.response.clone());
            } else {
                cache_guard.entries.remove(key);
            }
        }
        
        None
    }

    async fn cache_response(
        cache: &Arc<RwLock<ResponseCache>>,
        key: String,
        response: VspResponse,
    ) {
        let mut cache_guard = cache.write().await;
        
        // Implement LRU eviction if cache is full
        if cache_guard.entries.len() >= cache_guard.max_size {
            let oldest_key = cache_guard.entries.iter()
                .min_by_key(|(_, entry)| entry.created_at)
                .map(|(key, _)| key.clone());
            
            if let Some(key_to_remove) = oldest_key {
                cache_guard.entries.remove(&key_to_remove);
            }
        }

        let default_ttl = cache_guard.default_ttl;
        cache_guard.entries.insert(key, CacheEntry {
            response,
            expires_at: Instant::now() + default_ttl,
            hit_count: 0,
            created_at: Instant::now(),
        });
    }
}

impl Default for VSPClient {
    fn default() -> Self {
        Self::new(None, None, None, None, None).unwrap()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_vsp_client_creation() {
        let client = VSPClient::new(
            Some(5000), 
            Some(2), 
            Some(120), 
            Some(true), 
            Some(true)
        ).unwrap();
        
        assert_eq!(client.config.default_timeout_ms, 5000);
        assert_eq!(client.config.max_retries, 2);
        assert!(client.config.enable_compression);
        assert!(client.config.enable_adaptive_transport);
    }
}
