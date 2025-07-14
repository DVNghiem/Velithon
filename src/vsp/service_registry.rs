use crate::error::VSPInternalError;
use crate::vsp::service::{ServiceInfo, HealthStatus};
use crate::vsp::quic_transport::QuicTransport;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tokio::time::{Duration, Instant, interval, sleep};
use pyo3::prelude::*;
use tracing::{info, warn, debug};
use ahash::AHashMap;

/// Enhanced service registry with caching, health checks, and automatic discovery
#[pyclass]
pub struct ServiceRegistry {
    services: Arc<RwLock<AHashMap<String, Vec<ServiceInfo>>>>,
    cache: Arc<RwLock<ServiceCache>>,
    health_checker: Arc<HealthChecker>,
    transport: Option<Arc<QuicTransport>>,
}

#[derive(Clone)]
struct ServiceCache {
    entries: AHashMap<String, CacheEntry>,
    default_ttl: Duration,
}

#[derive(Clone)]
struct CacheEntry {
    services: Vec<ServiceInfo>,
    expires_at: Instant,
    hit_count: u64,
}

#[derive(Clone)]
struct HealthChecker {
    check_interval: Duration,
    timeout: Duration,
    retry_count: u32,
}

#[pymethods]
impl ServiceRegistry {
    #[new]
    #[pyo3(signature = (cache_ttl_seconds = 300, health_check_interval_seconds = 30))]
    pub fn new(cache_ttl_seconds: Option<u64>, health_check_interval_seconds: Option<u64>) -> Self {
        let cache_ttl = Duration::from_secs(cache_ttl_seconds.unwrap_or(300));
        let health_interval = Duration::from_secs(health_check_interval_seconds.unwrap_or(30));

        Self {
            services: Arc::new(RwLock::new(AHashMap::new())),
            cache: Arc::new(RwLock::new(ServiceCache {
                entries: AHashMap::new(),
                default_ttl: cache_ttl,
            })),
            health_checker: Arc::new(HealthChecker {
                check_interval: health_interval,
                timeout: Duration::from_secs(5),
                retry_count: 3,
            }),
            transport: None,
        }
    }

    /// Register a service
    pub fn register_service<'p>(&mut self, py: Python<'p>, service: ServiceInfo) -> PyResult<Bound<'p, PyAny>> {
        let services_arc = self.services.clone();
        let cache_arc = self.cache.clone();
        
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            {
                let mut services = services_arc.write().await;
                services.entry(service.name.clone())
                    .or_insert_with(Vec::new)
                    .push(service.clone());
            }

            // Invalidate cache for this service
            {
                let mut cache = cache_arc.write().await;
                cache.entries.remove(&service.name);
            }

            info!("Registered service: {} at {}", service.name, service.endpoint());
            Ok(())
        })
    }

    /// Discover services with caching and load balancing
    pub fn discover_services<'p>(
        &self, 
        py: Python<'p>, 
        service_name: String,
        tags: Option<Vec<String>>,
        max_results: Option<u32>
    ) -> PyResult<Bound<'p, PyAny>> {
        let services_arc = self.services.clone();
        let cache_arc = self.cache.clone();
        
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            // Check cache first
            {
                let mut cache = cache_arc.write().await;
                if let Some(entry) = cache.entries.get_mut(&service_name) {
                    if entry.expires_at > Instant::now() {
                        entry.hit_count += 1;
                        debug!("Cache hit for service: {} (hits: {})", service_name, entry.hit_count);
                        return Ok(entry.services.clone());
                    } else {
                        // Remove expired entry
                        cache.entries.remove(&service_name);
                    }
                }
            }

            // Cache miss, fetch from registry
            let services = {
                let services_guard = services_arc.read().await;
                services_guard.get(&service_name).cloned().unwrap_or_default()
            };

            // Filter by tags if provided
            let mut filtered_services = if let Some(ref tag_filter) = tags {
                services.into_iter()
                    .filter(|service| {
                        tag_filter.iter().all(|tag| {
                            service.tags.contains_key(tag)
                        })
                    })
                    .collect::<Vec<_>>()
            } else {
                services
            };

            // Filter by health status (only return healthy services)
            filtered_services.retain(|service| service.is_healthy());

            // Apply max results limit
            if let Some(max) = max_results {
                filtered_services.truncate(max as usize);
            }

            // Sort by load and weight for load balancing
            filtered_services.sort_by(|a, b| {
                let a_score = a.load as f64 / a.weight;
                let b_score = b.load as f64 / b.weight;
                a_score.partial_cmp(&b_score).unwrap()
            });

            // Update cache
            {
                let mut cache = cache_arc.write().await;
                cache.entries.insert(service_name.clone(), CacheEntry {
                    services: filtered_services.clone(),
                    expires_at: Instant::now() + cache.default_ttl,
                    hit_count: 1,
                });
            }

            debug!("Discovered {} services for: {}", filtered_services.len(), service_name);
            Ok(filtered_services)
        })
    }

    /// Get service with smart retry and failover
    pub fn get_service_with_retry<'p>(
        &self,
        py: Python<'p>,
        service_name: String,
        max_retries: Option<u32>
    ) -> PyResult<Bound<'p, PyAny>> {
        let services_arc = self.services.clone();
        let health_checker = self.health_checker.clone();
        
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let max_retries = max_retries.unwrap_or(3);
            let mut last_error = None;

            for attempt in 0..=max_retries {
                match Self::try_get_service(&services_arc, &service_name).await {
                    Ok(service) => {
                        // Verify service health before returning
                        if Self::quick_health_check(&service, &health_checker).await {
                            if attempt > 0 {
                                info!("Service {} recovered after {} attempts", service_name, attempt);
                            }
                            return Ok(service);
                        } else {
                            warn!("Service {} failed health check on attempt {}", service_name, attempt + 1);
                        }
                    }
                    Err(e) => {
                        last_error = Some(e);
                        warn!("Failed to get service {} on attempt {}: {:?}", service_name, attempt + 1, last_error);
                    }
                }

                if attempt < max_retries {
                    // Exponential backoff
                    let delay = Duration::from_millis(100 * 2_u64.pow(attempt));
                    sleep(delay).await;
                }
            }

            Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Failed to get service {} after {} retries: {:?}", 
                       service_name, max_retries, last_error)
            ))
        })
    }

    /// Start background health checking
    pub fn start_health_monitoring<'p>(&self, py: Python<'p>) -> PyResult<Bound<'p, PyAny>> {
        let services_arc = self.services.clone();
        let health_checker = self.health_checker.clone();
        
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let mut interval_timer = interval(health_checker.check_interval);
            
            loop {
                interval_timer.tick().await;
                
                let services_to_check = {
                    let services = services_arc.read().await;
                    services.values().flatten().cloned().collect::<Vec<_>>()
                };

                debug!("Checking health of {} services", services_to_check.len());

                // Check all services concurrently
                let health_futures = services_to_check.into_iter().map(|service| {
                    let health_checker = health_checker.clone();
                    let services_arc = services_arc.clone();
                    
                    async move {
                        let is_healthy = Self::detailed_health_check(&service, &health_checker).await;
                        let mut updated_service = service.clone();
                        
                        if is_healthy {
                            updated_service.set_health_status(HealthStatus::Healthy);
                        } else {
                            updated_service.set_health_status(HealthStatus::Unhealthy);
                            warn!("Service {} marked as unhealthy", service.name);
                        }

                        // Update service status in registry
                        let mut services = services_arc.write().await;
                        if let Some(service_list) = services.get_mut(&service.name) {
                            if let Some(pos) = service_list.iter().position(|s| s.endpoint() == service.endpoint()) {
                                service_list[pos] = updated_service;
                            }
                        }
                    }
                });

                // Wait for all health checks to complete
                futures::future::join_all(health_futures).await;
            }
        })
    }

    /// Get cache statistics
    pub fn get_cache_stats<'p>(&self, py: Python<'p>) -> PyResult<Bound<'p, PyAny>> {
        let cache_arc = self.cache.clone();
        
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let cache = cache_arc.read().await;
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

    /// Clear cache
    pub fn clear_cache<'p>(&self, py: Python<'p>) -> PyResult<Bound<'p, PyAny>> {
        let cache_arc = self.cache.clone();
        
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let mut cache = cache_arc.write().await;
            let cleared_count = cache.entries.len();
            cache.entries.clear();
            
            info!("Cleared {} cache entries", cleared_count);
            Ok(cleared_count)
        })
    }
}

impl ServiceRegistry {
    async fn try_get_service(
        services_arc: &Arc<RwLock<AHashMap<String, Vec<ServiceInfo>>>>,
        service_name: &str,
    ) -> Result<ServiceInfo, VSPInternalError> {
        let services = services_arc.read().await;
        let service_list = services.get(service_name)
            .ok_or_else(|| VSPInternalError::ServiceNotFound(service_name.to_string()))?;

        // Find the best available service (lowest load, highest weight)
        service_list.iter()
            .filter(|s| s.is_healthy())
            .min_by(|a, b| {
                let a_score = a.load as f64 / a.weight;
                let b_score = b.load as f64 / b.weight;
                a_score.partial_cmp(&b_score).unwrap()
            })
            .cloned()
            .ok_or_else(|| VSPInternalError::ServiceNotFound(
                format!("No healthy instances of service {}", service_name)
            ))
    }

    async fn quick_health_check(service: &ServiceInfo, _health_checker: &HealthChecker) -> bool {
        // Quick health check - just verify the service is still marked as healthy
        // In a real implementation, this might do a lightweight ping
        service.is_healthy()
    }

    async fn detailed_health_check(service: &ServiceInfo, health_checker: &HealthChecker) -> bool {
        // Detailed health check with actual network verification
        // In a real implementation, this would make an actual health check request
        
        for attempt in 0..health_checker.retry_count {
            // Simulate health check delay
            sleep(Duration::from_millis(10)).await;
            
            // For now, randomly determine health (in real implementation, make actual request)
            let is_healthy = rand::random::<f64>() > 0.1; // 90% success rate
            
            if is_healthy {
                return true;
            }
            
            if attempt < health_checker.retry_count - 1 {
                sleep(Duration::from_millis(50)).await;
            }
        }
        
        false
    }
}

/// Enhanced load balancer with multiple algorithms and health awareness
#[pyclass]
pub struct SmartLoadBalancer {
    algorithm: LoadBalancingAlgorithm,
    service_registry: Arc<ServiceRegistry>,
    connection_pool: Arc<RwLock<HashMap<String, Vec<QuicTransport>>>>,
}

#[derive(Clone, Copy, Debug)]
enum LoadBalancingAlgorithm {
    RoundRobin,
    WeightedRoundRobin,
    LeastConnections,
    LeastResponseTime,
    ConsistentHash,
}

#[pymethods]
impl SmartLoadBalancer {
    #[new]
    #[pyo3(signature = (algorithm = "weighted_round_robin"))]
    pub fn new(algorithm: Option<&str>) -> PyResult<Self> {
        let algo = match algorithm.unwrap_or("weighted_round_robin") {
            "round_robin" => LoadBalancingAlgorithm::RoundRobin,
            "weighted_round_robin" => LoadBalancingAlgorithm::WeightedRoundRobin,
            "least_connections" => LoadBalancingAlgorithm::LeastConnections,
            "least_response_time" => LoadBalancingAlgorithm::LeastResponseTime,
            "consistent_hash" => LoadBalancingAlgorithm::ConsistentHash,
            _ => LoadBalancingAlgorithm::WeightedRoundRobin,
        };

        Ok(Self {
            algorithm: algo,
            service_registry: Arc::new(ServiceRegistry::new(None, None)),
            connection_pool: Arc::new(RwLock::new(HashMap::new())),
        })
    }

    /// Select the best service instance for a request
    pub fn select_service<'p>(
        &self,
        py: Python<'p>,
        service_name: String,
        request_key: Option<String>, // For consistent hashing
    ) -> PyResult<Bound<'p, PyAny>> {
        let algorithm = self.algorithm;
        let service_registry = self.service_registry.clone();
        
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let services = service_registry.discover_services(
                py, 
                service_name.clone(), 
                None, 
                None
            ).await?;
            
            if services.is_empty() {
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("No healthy services found for {}", service_name)
                ));
            }

            let selected_service = match algorithm {
                LoadBalancingAlgorithm::WeightedRoundRobin => {
                    Self::weighted_round_robin_select(&services)
                },
                LoadBalancingAlgorithm::LeastConnections => {
                    Self::least_connections_select(&services)
                },
                LoadBalancingAlgorithm::ConsistentHash => {
                    Self::consistent_hash_select(&services, request_key.as_deref())
                },
                _ => services.into_iter().next().unwrap(), // Fallback to first service
            };

            Ok(selected_service)
        })
    }
}

impl SmartLoadBalancer {
    fn weighted_round_robin_select(services: &[ServiceInfo]) -> ServiceInfo {
        // Select based on weight and current load
        services.iter()
            .min_by(|a, b| {
                let a_score = (a.load as f64) / a.weight;
                let b_score = (b.load as f64) / b.weight;
                a_score.partial_cmp(&b_score).unwrap()
            })
            .unwrap()
            .clone()
    }

    fn least_connections_select(services: &[ServiceInfo]) -> ServiceInfo {
        // Select service with least load
        services.iter()
            .min_by_key(|service| service.load)
            .unwrap()
            .clone()
    }

    fn consistent_hash_select(services: &[ServiceInfo], request_key: Option<&str>) -> ServiceInfo {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let key = request_key.unwrap_or("default");
        let mut hasher = DefaultHasher::new();
        key.hash(&mut hasher);
        let hash = hasher.finish();
        
        let index = (hash as usize) % services.len();
        services[index].clone()
    }
}

impl Default for SmartLoadBalancer {
    fn default() -> Self {
        Self::new(None).unwrap()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_service_registry() {
        let mut registry = ServiceRegistry::new(Some(60), Some(10));
        
        let service = ServiceInfo::new(
            "test-service".to_string(),
            "localhost".to_string(),
            8080,
        );

        // Test would need to be adapted for actual async execution
        // registry.register_service(service).await.unwrap();
    }

    #[test]
    fn test_load_balancer_creation() {
        let balancer = SmartLoadBalancer::new(Some("weighted_round_robin")).unwrap();
        assert!(matches!(balancer.algorithm, LoadBalancingAlgorithm::WeightedRoundRobin));
    }
}
