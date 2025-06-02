use pyo3::prelude::*;
use crate::vsp::service::ServiceInfo;
use rand::prelude::*;

/// Abstract Load Balancer trait (for internal use)
pub trait LoadBalancer: Send + Sync {
    fn select(&self, instances: &[ServiceInfo]) -> Option<ServiceInfo>;
}

/// Round-robin load balancer
#[pyclass]
#[derive(Debug)]
pub struct RoundRobinBalancer {
    counter: std::sync::atomic::AtomicUsize,
}

impl Clone for RoundRobinBalancer {
    fn clone(&self) -> Self {
        Self {
            counter: std::sync::atomic::AtomicUsize::new(
                self.counter.load(std::sync::atomic::Ordering::Relaxed)
            ),
        }
    }
}

#[pymethods]
impl RoundRobinBalancer {
    #[new]
    pub fn new() -> Self {
        Self {
            counter: std::sync::atomic::AtomicUsize::new(0),
        }
    }

    /// Select a service instance using round-robin
    pub fn select(&self, py_instances: Vec<ServiceInfo>) -> Option<ServiceInfo> {
        let instances = &py_instances;
        if instances.is_empty() {
            return None;
        }

        let count = self.counter.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        let index = count % instances.len();
        instances.get(index).cloned()
    }

    fn __repr__(&self) -> String {
        "RoundRobinBalancer()".to_string()
    }
}

impl LoadBalancer for RoundRobinBalancer {
    fn select(&self, instances: &[ServiceInfo]) -> Option<ServiceInfo> {
        if instances.is_empty() {
            return None;
        }

        let count = self.counter.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        let index = count % instances.len();
        instances.get(index).cloned()
    }
}

/// Weighted load balancer
#[pyclass]
#[derive(Debug, Clone)]
pub struct WeightedBalancer {
    rng: std::sync::Arc<std::sync::Mutex<rand::rngs::StdRng>>,
}

#[pymethods]
impl WeightedBalancer {
    #[new]
    pub fn new() -> Self {
        Self {
            rng: std::sync::Arc::new(std::sync::Mutex::new(StdRng::from_entropy())),
        }
    }

    /// Select a service instance using weighted random selection
    pub fn select(&self, py_instances: Vec<ServiceInfo>) -> Option<ServiceInfo> {
        let instances = &py_instances;
        if instances.is_empty() {
            return None;
        }

        let total_weight: f64 = instances.iter().map(|s| s.weight).sum();
        if total_weight <= 0.0 {
            // Fallback to round-robin if no valid weights
            let mut rng = self.rng.lock().unwrap();
            let index = rng.gen_range(0..instances.len());
            return instances.get(index).cloned();
        }

        let mut rng = self.rng.lock().unwrap();
        let mut random_weight = rng.gen_range(0.0..total_weight);

        for service in instances {
            random_weight -= service.weight;
            if random_weight <= 0.0 {
                return Some(service.clone());
            }
        }

        // Fallback to last instance (shouldn't happen)
        instances.last().cloned()
    }

    fn __repr__(&self) -> String {
        "WeightedBalancer()".to_string()
    }
}

impl LoadBalancer for WeightedBalancer {
    fn select(&self, instances: &[ServiceInfo]) -> Option<ServiceInfo> {
        if instances.is_empty() {
            return None;
        }

        let total_weight: f64 = instances.iter().map(|s| s.weight).sum();
        if total_weight <= 0.0 {
            // Fallback to random selection if no valid weights
            let mut rng = self.rng.lock().unwrap();
            let index = rng.gen_range(0..instances.len());
            return instances.get(index).cloned();
        }

        let mut rng = self.rng.lock().unwrap();
        let mut random_weight = rng.gen_range(0.0..total_weight);

        for service in instances {
            random_weight -= service.weight;
            if random_weight <= 0.0 {
                return Some(service.clone());
            }
        }

        // Fallback to last instance (shouldn't happen)
        instances.last().cloned()
    }
}

/// Random load balancer
#[pyclass]
#[derive(Debug, Clone)]
pub struct RandomBalancer {
    rng: std::sync::Arc<std::sync::Mutex<rand::rngs::StdRng>>,
}

#[pymethods]
impl RandomBalancer {
    #[new]
    pub fn new() -> Self {
        Self {
            rng: std::sync::Arc::new(std::sync::Mutex::new(StdRng::from_entropy())),
        }
    }

    /// Select a service instance randomly
    pub fn select(&self, py_instances: Vec<ServiceInfo>) -> Option<ServiceInfo> {
        let instances = &py_instances;
        if instances.is_empty() {
            return None;
        }

        let mut rng = self.rng.lock().unwrap();
        let index = rng.gen_range(0..instances.len());
        instances.get(index).cloned()
    }

    fn __repr__(&self) -> String {
        "RandomBalancer()".to_string()
    }
}

impl LoadBalancer for RandomBalancer {
    fn select(&self, instances: &[ServiceInfo]) -> Option<ServiceInfo> {
        if instances.is_empty() {
            return None;
        }

        let mut rng = self.rng.lock().unwrap();
        let index = rng.gen_range(0..instances.len());
        instances.get(index).cloned()
    }
}
