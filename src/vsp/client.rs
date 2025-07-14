use crate::error::VSPInternalError;
use crate::vsp::protocol::{VspRequest, VspResponse, MessageType, CompressionType};
use crate::vsp::quic_transport::{QuicTransport, AdaptiveTransport};
use crate::vsp::service_registry::{ServiceRegistry, SmartLoadBalancer};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tokio::time::{Duration, Instant, timeout};
use pyo3::prelude::*;
use tracing::{info, warn, error, debug};
use ahash::AHashMap;
use serde::{Serialize, Deserialize};

/// High-performance VSP client with caching, retries, and circuit breaking
#[pyclass]
pub struct VSPClient {
    service_registry: Arc<ServiceRegistry>,
    load_balancer: Arc<SmartLoadBalancer>,
    response_cache: Arc<RwLock<ResponseCache>>,
    circuit_breaker: Arc<RwLock<CircuitBreakerRegistry>>,
    transport_pool: Arc<RwLock<TransportPool>>,
    config: ClientConfig,
}

#[derive(Clone)]
struct ClientConfig {
    default_timeout_ms: u32,
    max_retries: u32,
    cache_ttl_seconds: u64,
    circuit_breaker_threshold: u32,
    circuit_breaker_timeout_seconds: u64,
    compression_type: CompressionType,
    enable_adaptive_transport: bool,
}

#[derive(Clone)]
struct ResponseCache {
    entries: AHashMap<String, CacheEntry>,
    default_ttl: Duration,
    max_size: usize,
}

#[derive(Clone)]
struct CacheEntry {
    response: Response,
    expires_at: Instant,
    hit_count: u64,
    created_at: Instant,
}

#[derive(Clone)]
struct CircuitBreakerRegistry {
    breakers: AHashMap<String, CircuitBreaker>,
}

#[derive(Clone, Debug)]
struct CircuitBreaker {
    state: CircuitState,
    failure_count: u32,
    last_failure_time: Instant,
    threshold: u32,
    timeout: Duration,
}

#[derive(Clone, Copy, Debug, PartialEq)]
enum CircuitState {
    Closed,    // Normal operation
    Open,      // Failing fast
    HalfOpen,  // Testing if service is back
}

struct TransportPool {
    quic_transports: HashMap<String, Arc<QuicTransport>>,
    adaptive_transports: HashMap<String, Arc<AdaptiveTransport>>,
}

#[pymethods]
impl VSPClient {
    #[new]
    #[pyo3(signature = (
        timeout_ms = 30000,
        max_retries = 3,
        cache_ttl_seconds = 300,
        circuit_breaker_threshold = 5,
        enable_compression = true,
        enable_adaptive_transport = true
    ))]
    pub fn new(
        timeout_ms: Option<u32>,
        max_retries: Option<u32>,
        cache_ttl_seconds: Option<u64>,
        circuit_breaker_threshold: Option<u32>,
        enable_compression: Option<bool>,
        enable_adaptive_transport: Option<bool>,
    ) -> PyResult<Self> {
        let config = ClientConfig {
            default_timeout_ms: timeout_ms.unwrap_or(30000),
            max_retries: max_retries.unwrap_or(3),
            cache_ttl_seconds: cache_ttl_seconds.unwrap_or(300),
            circuit_breaker_threshold: circuit_breaker_threshold.unwrap_or(5),
            circuit_breaker_timeout_seconds: 60,
            compression_type: if enable_compression.unwrap_or(true) {
                CompressionType::Zstd
            } else {
                CompressionType::None
            },
            enable_adaptive_transport: enable_adaptive_transport.unwrap_or(true),
        };

        Ok(Self {
            service_registry: Arc::new(ServiceRegistry::new(
                Some(config.cache_ttl_seconds),
                Some(30),
            )),
            load_balancer: Arc::new(SmartLoadBalancer::new(Some("weighted_round_robin"))?),
            response_cache: Arc::new(RwLock::new(ResponseCache {
                entries: AHashMap::new(),
                default_ttl: Duration::from_secs(config.cache_ttl_seconds),
                max_size: 10000,
            })),
            circuit_breaker: Arc::new(RwLock::new(CircuitBreakerRegistry {
                breakers: AHashMap::new(),
            })),
            transport_pool: Arc::new(RwLock::new(TransportPool {
                quic_transports: HashMap::new(),
                adaptive_transports: HashMap::new(),
            })),
            config,
        })
    }

    /// Send a request with automatic retries, caching, and circuit breaking
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
        let service_registry = self.service_registry.clone();
        let load_balancer = self.load_balancer.clone();
        let response_cache = self.response_cache.clone();
        let circuit_breaker = self.circuit_breaker.clone();
        let transport_pool = self.transport_pool.clone();

        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let timeout_duration = Duration::from_millis(
                timeout_ms.unwrap_or(config.default_timeout_ms) as u64
            );

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
                    debug!("Cache hit for request: {}", cache_key);
                    return Ok(cached_response);
                }
            }

            // Check circuit breaker
            if Self::is_circuit_open(&circuit_breaker, &service_name).await {
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Circuit breaker is open for service: {}", service_name)
                ));
            }

            let mut last_error = None;
            let start_time = Instant::now();

            // Retry loop
            for attempt in 0..=config.max_retries {
                match timeout(timeout_duration, Self::execute_request(
                    &service_name,
                    &method,
                    &data,
                    &headers.clone().unwrap_or_default(),
                    &config,
                    &service_registry,
                    &load_balancer,
                    &transport_pool,
                )).await {
                    Ok(Ok(response)) => {
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

                        // Record success in circuit breaker
                        Self::record_success(&circuit_breaker, &service_name).await;

                        if attempt > 0 {
                            info!("Request succeeded after {} retries for service: {}", 
                                 attempt, service_name);
                        }

                        return Ok(final_response);
                    }
                    Ok(Err(e)) => {
                        last_error = Some(format!("Request error: {:?}", e));
                        warn!("Request failed on attempt {} for service {}: {:?}", 
                             attempt + 1, service_name, e);
                    }
                    Err(_) => {
                        last_error = Some("Request timeout".to_string());
                        warn!("Request timeout on attempt {} for service {}", 
                             attempt + 1, service_name);
                    }
                }

                // Record failure in circuit breaker
                Self::record_failure(&circuit_breaker, &service_name, &config).await;

                // Exponential backoff before retry
                if attempt < config.max_retries {
                    let delay = Duration::from_millis(100 * 2_u64.pow(attempt));
                    tokio::time::sleep(delay).await;
                }
            }

            error!("All retries exhausted for service: {} after {} attempts", 
                   service_name, config.max_retries + 1);

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
        let service_registry = self.service_registry.clone();
        let load_balancer = self.load_balancer.clone();
        let transport_pool = self.transport_pool.clone();

        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            // Get service instance
            let service = load_balancer.select_service(
                py,
                service_name.clone(),
                None,
            ).await?;

            // Get or create transport
            let transport = Self::get_transport(
                &transport_pool,
                &service.endpoint(),
                config.enable_adaptive_transport,
            ).await?;

            // Create request
            let request = Request::new(service_name, method, data)
                .with_timeout(config.default_timeout_ms);

            let request_data = request.encode_to_vec();
            let envelope = Envelope::new_compressed(
                MessageType::Request,
                request_data,
                config.compression_type,
            ).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Serialization error: {}", e)
            ))?;

            // Send without waiting for response
            transport.send_data(py, envelope.to_bytes().map_err(|e| 
                PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Encoding error: {}", e)
                ))?).await?;

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

    /// Get circuit breaker status for all services
    pub fn get_circuit_breaker_status<'p>(&self, py: Python<'p>) -> PyResult<Bound<'p, PyAny>> {
        let circuit_breaker = self.circuit_breaker.clone();

        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let breakers = circuit_breaker.read().await;
            let mut status = HashMap::new();

            for (service_name, breaker) in &breakers.breakers {
                let mut service_status = HashMap::new();
                service_status.insert("state".to_string(), format!("{:?}", breaker.state));
                service_status.insert("failure_count".to_string(), breaker.failure_count as f64);
                service_status.insert("threshold".to_string(), breaker.threshold as f64);
                
                status.insert(service_name.clone(), service_status);
            }

            Ok(status)
        })
    }
}

impl VSPClient {
    async fn execute_request(
        service_name: &str,
        method: &str,
        data: &[u8],
        headers: &HashMap<String, String>,
        config: &ClientConfig,
        service_registry: &ServiceRegistry,
        load_balancer: &SmartLoadBalancer,
        transport_pool: &TransportPool,
    ) -> VSPResult<Response> {
        // Get service instance using load balancer
        let service = load_balancer.select_service(
            Python::with_gil(|py| py),
            service_name.to_string(),
            None,
        ).await.map_err(|e| VSPInternalError::ServiceNotFound(e.to_string()))?;

        // Get or create transport for this service
        let transport = Self::get_transport(
            &Arc::new(RwLock::new(transport_pool.clone())),
            &service.endpoint(),
            config.enable_adaptive_transport,
        ).await?;

        // Create and send request
        let mut request = Request::new(
            service_name.to_string(),
            method.to_string(),
            data.to_vec(),
        ).with_timeout(config.default_timeout_ms);

        // Add headers
        for (key, value) in headers {
            request = request.with_header(key.clone(), value.clone());
        }

        let request_data = request.encode_to_vec();
        let envelope = Envelope::new_compressed(
            MessageType::Request,
            request_data,
            config.compression_type,
        ).map_err(|e| VSPInternalError::Serialization(e.to_string()))?;

        // Send request and get response
        let response = transport.send_request(
            Python::with_gil(|py| py),
            service.name,
            method.to_string(),
            envelope.to_bytes().map_err(|e| VSPInternalError::Serialization(e.to_string()))?,
            Some(config.default_timeout_ms),
        ).await.map_err(|e| VSPInternalError::Transport(e.to_string()))?;

        Ok(response)
    }

    async fn get_transport(
        transport_pool: &Arc<RwLock<TransportPool>>,
        endpoint: &str,
        enable_adaptive: bool,
    ) -> VSPResult<Arc<dyn TransportLike + Send + Sync>> {
        let pool = transport_pool.read().await;
        
        if enable_adaptive {
            if let Some(transport) = pool.adaptive_transports.get(endpoint) {
                return Ok(transport.clone() as Arc<dyn TransportLike + Send + Sync>);
            }
        } else {
            if let Some(transport) = pool.quic_transports.get(endpoint) {
                return Ok(transport.clone() as Arc<dyn TransportLike + Send + Sync>);
            }
        }

        drop(pool);

        // Create new transport
        let mut pool = transport_pool.write().await;
        
        if enable_adaptive {
            let transport = Arc::new(AdaptiveTransport::new());
            pool.adaptive_transports.insert(endpoint.to_string(), transport.clone());
            Ok(transport as Arc<dyn TransportLike + Send + Sync>)
        } else {
            let transport = Arc::new(QuicTransport::new(Some(false), Some("zstd"))
                .map_err(|e| VSPInternalError::Configuration(e.to_string()))?);
            pool.quic_transports.insert(endpoint.to_string(), transport.clone());
            Ok(transport as Arc<dyn TransportLike + Send + Sync>)
        }
    }

    async fn get_cached_response(
        cache: &Arc<RwLock<ResponseCache>>,
        key: &str,
    ) -> Option<Response> {
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
        response: Response,
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

        cache_guard.entries.insert(key, CacheEntry {
            response,
            expires_at: Instant::now() + cache_guard.default_ttl,
            hit_count: 0,
            created_at: Instant::now(),
        });
    }

    async fn is_circuit_open(
        circuit_breaker: &Arc<RwLock<CircuitBreakerRegistry>>,
        service_name: &str,
    ) -> bool {
        let breakers = circuit_breaker.read().await;
        
        if let Some(breaker) = breakers.breakers.get(service_name) {
            match breaker.state {
                CircuitState::Open => {
                    // Check if timeout has expired
                    if Instant::now() - breaker.last_failure_time > breaker.timeout {
                        // Should transition to half-open, but that requires write access
                        false
                    } else {
                        true
                    }
                }
                _ => false,
            }
        } else {
            false
        }
    }

    async fn record_failure(
        circuit_breaker: &Arc<RwLock<CircuitBreakerRegistry>>,
        service_name: &str,
        config: &ClientConfig,
    ) {
        let mut breakers = circuit_breaker.write().await;
        let breaker = breakers.breakers.entry(service_name.to_string())
            .or_insert_with(|| CircuitBreaker {
                state: CircuitState::Closed,
                failure_count: 0,
                last_failure_time: Instant::now(),
                threshold: config.circuit_breaker_threshold,
                timeout: Duration::from_secs(config.circuit_breaker_timeout_seconds),
            });

        breaker.failure_count += 1;
        breaker.last_failure_time = Instant::now();

        if breaker.failure_count >= breaker.threshold {
            breaker.state = CircuitState::Open;
            warn!("Circuit breaker opened for service: {}", service_name);
        }
    }

    async fn record_success(
        circuit_breaker: &Arc<RwLock<CircuitBreakerRegistry>>,
        service_name: &str,
    ) {
        let mut breakers = circuit_breaker.write().await;
        
        if let Some(breaker) = breakers.breakers.get_mut(service_name) {
            breaker.failure_count = 0;
            breaker.state = CircuitState::Closed;
        }
    }
}

// Trait to abstract transport types
trait TransportLike {
    // This would need to be implemented for both QuicTransport and AdaptiveTransport
}

impl TransportLike for QuicTransport {}
impl TransportLike for AdaptiveTransport {}

impl Default for VSPClient {
    fn default() -> Self {
        Self::new(None, None, None, None, None, None).unwrap()
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
            Some(3), 
            Some(true), 
            Some(true)
        ).unwrap();
        
        assert_eq!(client.config.default_timeout_ms, 5000);
        assert_eq!(client.config.max_retries, 2);
    }

    #[test]
    fn test_circuit_breaker() {
        let breaker = CircuitBreaker {
            state: CircuitState::Closed,
            failure_count: 0,
            last_failure_time: Instant::now(),
            threshold: 5,
            timeout: Duration::from_secs(60),
        };

        assert_eq!(breaker.state, CircuitState::Closed);
        assert_eq!(breaker.threshold, 5);
    }
}
