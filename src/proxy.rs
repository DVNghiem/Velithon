use pyo3::prelude::*;
use pyo3::types::PyDict;
use tokio::time::{timeout, Duration};
use hyper::{Method, Request, Uri, Version};
use hyper::header::{HeaderMap, HeaderName, HeaderValue};
use hyper::body::Bytes;
use hyper_util::client::legacy::{Client, connect::HttpConnector};
use http_body_util::{BodyExt, Full};
use std::sync::Arc;
use tokio::sync::RwLock;
use std::str::FromStr;

// High-performance HTTP client with connection pooling using hyper
#[pyclass]
pub struct ProxyClient {
    client: Client<HttpConnector, Full<Bytes>>,
    target_url: String,
    timeout_ms: u64,
    max_retries: u32,
    circuit_breaker: Arc<RwLock<CircuitBreaker>>,
}

#[pyclass]
struct CircuitBreaker {
    failure_count: u32,
    last_failure_time: Option<std::time::Instant>,
    max_failures: u32,
    recovery_timeout_ms: u64,
    state: CircuitState,
}

#[derive(Debug, Clone, Copy, PartialEq)]
enum CircuitState {
    Closed,   // Normal operation
    Open,     // Failing, reject requests
    HalfOpen, // Testing if service recovered
}

#[pymethods]
impl ProxyClient {
    #[new]
    #[pyo3(signature = (target_url, timeout_ms=30000, max_retries=3, max_failures=5, recovery_timeout_ms=60000))]
    fn new(
        target_url: String,
        timeout_ms: u64,
        max_retries: u32,
        max_failures: u32,
        recovery_timeout_ms: u64,
    ) -> PyResult<Self> {
        // Create HTTP connector
        let connector = HttpConnector::new();
        
        // Create hyper client with connection pooling
        let client = Client::builder(hyper_util::rt::TokioExecutor::new())
            .build(connector);

        let circuit_breaker = Arc::new(RwLock::new(CircuitBreaker {
            failure_count: 0,
            last_failure_time: None,
            max_failures,
            recovery_timeout_ms,
            state: CircuitState::Closed,
        }));

        Ok(ProxyClient {
            client,
            target_url,
            timeout_ms,
            max_retries,
            circuit_breaker,
        })
    }

    /// Forward HTTP request to target with optimized performance
    #[pyo3(signature = (method, path, headers=None, body=None, query_params=None))]
    fn forward_request<'p>(
        &self,
        py: Python<'p>,
        method: &str,
        path: &str,
        headers: Option<Bound<'p, PyDict>>,
        body: Option<&[u8]>,
        query_params: Option<Bound<'p, PyDict>>,
    ) -> PyResult<Bound<'p, PyAny>> {
        let client = self.client.clone();
        let target_url = self.target_url.clone();
        let timeout_duration = Duration::from_millis(self.timeout_ms);
        let max_retries = self.max_retries;
        let circuit_breaker = self.circuit_breaker.clone();
        
        let method_str = method.to_string();
        let path_str = path.to_string();
        let body_data = body.map(|b| b.to_vec());

        // Build query string if provided
        let query_string = if let Some(params) = query_params.as_ref() {
            self.build_query_string_for_params(params)?
        } else {
            String::new()
        };

        // Build headers if provided
        let header_map = if let Some(headers_dict) = headers.as_ref() {
            Some(self.build_headers_from_dict(headers_dict)?)
        } else {
            None
        };

        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            // Build full URL
            let mut full_url = format!("{}{}", target_url, path_str);
            if !query_string.is_empty() {
                full_url.push('?');
                full_url.push_str(&query_string);
            }

            // Parse method
            let method = Method::from_str(&method_str)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Invalid HTTP method: {}", e)
                ))?;

            // Parse URI
            let uri = Uri::from_str(&full_url)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Invalid URI: {}", e)
                ))?;

            // Check circuit breaker
            let can_execute = {
                let breaker = circuit_breaker.read().await;
                match breaker.state {
                    CircuitState::Closed => true,
                    CircuitState::Open => {
                        if let Some(last_failure) = breaker.last_failure_time {
                            let elapsed = last_failure.elapsed().as_millis() as u64;
                            elapsed > breaker.recovery_timeout_ms
                        } else {
                            false
                        }
                    },
                    CircuitState::HalfOpen => true,
                }
            };

            if !can_execute {
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    "Circuit breaker is open"
                ));
            }

            let mut last_error = String::new();
            
            for attempt in 0..=max_retries {
                // Build request
                let mut req_builder = Request::builder()
                    .method(method.clone())
                    .uri(uri.clone())
                    .version(Version::HTTP_11);

                // Add headers if provided
                if let Some(ref header_map) = header_map {
                    for (name, value) in header_map.iter() {
                        req_builder = req_builder.header(name, value);
                    }
                }

                // Build request with body
                let request = if let Some(ref body_data) = body_data {
                    req_builder.body(Full::new(Bytes::from(body_data.clone())))
                } else {
                    req_builder.body(Full::new(Bytes::new()))
                };

                let request = match request {
                    Ok(req) => req,
                    Err(e) => {
                        last_error = format!("Failed to build request: {}", e);
                        continue;
                    }
                };

                // Execute request with timeout
                let response_result = timeout(timeout_duration, client.request(request)).await;

                match response_result {
                    Ok(Ok(response)) => {
                        // Success - record it
                        {
                            let mut breaker = circuit_breaker.write().await;
                            breaker.failure_count = 0;
                            breaker.state = CircuitState::Closed;
                            breaker.last_failure_time = None;
                        }
                        
                        let status = response.status().as_u16();
                        let headers = response.headers().clone();
                        
                        match response.collect().await {
                            Ok(collected) => {
                                let body_bytes = collected.to_bytes().to_vec();
                                
                                // Convert headers to Python dict
                                let headers_dict: PyObject = Python::with_gil(|py| {
                                    let dict = PyDict::new(py);
                                    for (name, value) in headers.iter() {
                                        if let Ok(value_str) = value.to_str() {
                                            let _ = dict.set_item(name.as_str(), value_str);
                                        }
                                    }
                                    dict.into()
                                });

                                return Ok((status, body_bytes, headers_dict));
                            },
                            Err(body_err) => {
                                last_error = format!("Failed to read response body: {}", body_err);
                            }
                        }
                    }
                    Ok(Err(req_err)) => {
                        last_error = format!("Request failed: {}", req_err);
                    }
                    Err(_) => {
                        last_error = "Request timeout".to_string();
                    }
                }

                // Record failure
                {
                    let mut breaker = circuit_breaker.write().await;
                    breaker.failure_count += 1;
                    breaker.last_failure_time = Some(std::time::Instant::now());
                    
                    if breaker.failure_count >= breaker.max_failures {
                        breaker.state = CircuitState::Open;
                    } else if breaker.state == CircuitState::HalfOpen {
                        breaker.state = CircuitState::Open;
                    }
                }

                // Implement exponential backoff
                if attempt < max_retries {
                    let backoff_ms = (2_u64.pow(attempt as u32)) * 100;
                    tokio::time::sleep(Duration::from_millis(backoff_ms)).await;
                }
            }

            Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(last_error))
        })
    }

    /// Get circuit breaker status
    fn get_circuit_breaker_status<'p>(&self, py: Python<'p>) -> PyResult<Bound<'p, PyAny>> {
        let circuit_breaker = self.circuit_breaker.clone();
        
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let breaker = circuit_breaker.read().await;
            let state_str = match breaker.state {
                CircuitState::Closed => "closed",
                CircuitState::Open => "open", 
                CircuitState::HalfOpen => "half_open",
            };
            
            Ok((
                state_str.to_string(),
                breaker.failure_count,
                breaker.last_failure_time.map(|t| t.elapsed().as_millis() as u64)
            ))
        })
    }

    /// Reset circuit breaker
    fn reset_circuit_breaker<'p>(&self, py: Python<'p>) -> PyResult<Bound<'p, PyAny>> {
        let circuit_breaker = self.circuit_breaker.clone();
        
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let mut breaker = circuit_breaker.write().await;
            breaker.failure_count = 0;
            breaker.state = CircuitState::Closed;
            breaker.last_failure_time = None;
            Ok(())
        })
    }
}

impl ProxyClient {
    /// Convert PyDict to query string for load balancer
    fn build_query_string_for_params(&self, params: &Bound<PyDict>) -> PyResult<String> {
        let mut query_parts = Vec::new();
        
        for (key, value) in params.iter() {
            let key_str = key.extract::<&str>()?;
            let value_str = value.extract::<&str>()?;
            let encoded_key = urlencoding::encode(key_str);
            let encoded_value = urlencoding::encode(value_str);
            query_parts.push(format!("{}={}", encoded_key, encoded_value));
        }
        
        Ok(query_parts.join("&"))
    }

    /// Build headers from PyDict with proper error handling  
    fn build_headers_from_dict(&self, headers_dict: &Bound<PyDict>) -> PyResult<HeaderMap> {
        let mut header_map = HeaderMap::new();
        
        for (key, value) in headers_dict.iter() {
            let key_str = key.extract::<&str>()?;
            let value_str = value.extract::<&str>()?;
            
            let header_name = HeaderName::from_bytes(key_str.as_bytes())
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Invalid header name: {}", e)
                ))?;
                
            let header_value = HeaderValue::from_str(value_str)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Invalid header value: {}", e)
                ))?;
                
            header_map.insert(header_name, header_value);
        }
        
        Ok(header_map)
    }
}

/// Load balancer for multiple proxy targets
#[pyclass]
pub struct ProxyLoadBalancer {
    targets: Vec<String>,
    current_index: Arc<std::sync::atomic::AtomicUsize>,
    strategy: LoadBalancingStrategy,
    health_check_url: Option<String>,
    healthy_targets: Arc<RwLock<std::collections::HashSet<usize>>>,
    health_client: Client<HttpConnector, Full<Bytes>>,
}

#[derive(Debug, Clone)]
enum LoadBalancingStrategy {
    RoundRobin,
    Random,
    WeightedRoundRobin(Vec<u32>),
}

#[pymethods]
impl ProxyLoadBalancer {
    #[new]
    #[pyo3(signature = (targets, strategy="round_robin", weights=None, health_check_url=None))]
    fn new(
        targets: Vec<String>,
        strategy: &str,
        weights: Option<Vec<u32>>,
        health_check_url: Option<String>,
    ) -> PyResult<Self> {
        if targets.is_empty() {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "At least one target is required"
            ));
        }

        let lb_strategy = match strategy {
            "round_robin" => LoadBalancingStrategy::RoundRobin,
            "random" => LoadBalancingStrategy::Random,
            "weighted" => {
                if let Some(w) = weights {
                    if w.len() != targets.len() {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            "Weights length must match targets length"
                        ));
                    }
                    LoadBalancingStrategy::WeightedRoundRobin(w)
                } else {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        "Weights required for weighted strategy"
                    ));
                }
            }
            _ => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Invalid strategy. Use 'round_robin', 'random', or 'weighted'"
            )),
        };

        let healthy_targets: std::collections::HashSet<usize> = (0..targets.len()).collect();

        // Create health check client
        let connector = HttpConnector::new();
        let health_client = Client::builder(hyper_util::rt::TokioExecutor::new())
            .build(connector);

        Ok(ProxyLoadBalancer {
            targets,
            current_index: Arc::new(std::sync::atomic::AtomicUsize::new(0)),
            strategy: lb_strategy,
            health_check_url,
            healthy_targets: Arc::new(RwLock::new(healthy_targets)),
            health_client,
        })
    }

    /// Get next target URL using the configured strategy
    fn get_next_target<'p>(&self, py: Python<'p>) -> PyResult<Bound<'p, PyAny>> {
        let targets = self.targets.clone();
        let strategy = self.strategy.clone();
        let current_index = self.current_index.clone();
        let healthy_targets = self.healthy_targets.clone();

        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let healthy = healthy_targets.read().await;
            let healthy_list: Vec<usize> = healthy.iter().cloned().collect();
            
            if healthy_list.is_empty() {
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    "No healthy targets available"
                ));
            }

            let target_index = match strategy {
                LoadBalancingStrategy::RoundRobin => {
                    let index = current_index.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    healthy_list[index % healthy_list.len()]
                }
                LoadBalancingStrategy::Random => {
                    use rand::Rng;
                    let mut rng = rand::rng();
                    healthy_list[rng.random_range(0..healthy_list.len())]
                }
                LoadBalancingStrategy::WeightedRoundRobin(ref weights) => {
                    // Simplified weighted round robin - could be more sophisticated
                    let total_weight: u32 = healthy_list.iter()
                        .map(|&i| weights.get(i).unwrap_or(&1))
                        .sum();
                    
                    let mut weight_sum = 0u32;
                    let target_weight = (current_index.fetch_add(1, std::sync::atomic::Ordering::Relaxed) as u32) % total_weight;
                    
                    for &target_idx in &healthy_list {
                        weight_sum += weights.get(target_idx).unwrap_or(&1);
                        if weight_sum > target_weight {
                            return Ok(targets[target_idx].clone());
                        }
                    }
                    
                    healthy_list[0] // Fallback
                }
            };

            Ok(targets[target_index].clone())
        })
    }

    /// Perform health check on all targets
    fn health_check<'p>(&self, py: Python<'p>) -> PyResult<Bound<'p, PyAny>> {
        let targets = self.targets.clone();
        let health_check_url = self.health_check_url.clone();
        let healthy_targets = self.healthy_targets.clone();
        let client = self.health_client.clone();

        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let mut new_healthy = std::collections::HashSet::new();

            for (index, target) in targets.iter().enumerate() {
                let check_url = if let Some(ref health_url) = health_check_url {
                    format!("{}{}", target, health_url)
                } else {
                    format!("{}/health", target)
                };

                if let Ok(uri) = Uri::from_str(&check_url) {
                    let request = Request::builder()
                        .method(Method::GET)
                        .uri(uri)
                        .body(Full::new(Bytes::new()));

                    if let Ok(req) = request {
                        match timeout(Duration::from_secs(5), client.request(req)).await {
                            Ok(Ok(response)) if response.status().is_success() => {
                                new_healthy.insert(index);
                            }
                            _ => {
                                // Target is unhealthy
                            }
                        }
                    }
                }
            }

            {
                let mut healthy = healthy_targets.write().await;
                *healthy = new_healthy;
            }

            Ok(())
        })
    }

    /// Get current health status
    fn get_health_status<'p>(&self, py: Python<'p>) -> PyResult<Bound<'p, PyAny>> {
        let healthy_targets = self.healthy_targets.clone();
        let targets = self.targets.clone();

        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let healthy = healthy_targets.read().await;
            let status: Vec<(String, bool)> = targets.iter().enumerate()
                .map(|(i, target)| (target.clone(), healthy.contains(&i)))
                .collect();
            Ok(status)
        })
    }
}

/// Register proxy module with Python
pub fn register_proxy(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<ProxyClient>()?;
    m.add_class::<ProxyLoadBalancer>()?;
    Ok(())
}
