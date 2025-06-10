use pyo3::prelude::*;
use serde::{Serialize, Deserialize};
use std::time::SystemTime;

/// Service health status
#[pyclass]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum HealthStatus {
    Healthy,
    Unhealthy,
    Unknown,
}

#[pymethods]
impl HealthStatus {
    fn __repr__(&self) -> String {
        match self {
            HealthStatus::Healthy => "HealthStatus.Healthy".to_string(),
            HealthStatus::Unhealthy => "HealthStatus.Unhealthy".to_string(),
            HealthStatus::Unknown => "HealthStatus.Unknown".to_string(),
        }
    }
}

/// Service information for discovery and load balancing
#[pyclass]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServiceInfo {
    #[pyo3(get, set)]
    pub name: String,
    #[pyo3(get, set)]
    pub host: String,
    #[pyo3(get, set)]
    pub port: u16,
    #[pyo3(get, set)]
    pub weight: f64,
    #[pyo3(get)]
    pub health_status: HealthStatus,
    #[pyo3(get)]
    pub last_health_check: u64,
    
}

#[pymethods]
impl ServiceInfo {
    #[new]
    #[pyo3(signature = (name, host, port, weight = 1.0))]
    pub fn new(name: String, host: String, port: u16, weight: Option<f64>) -> Self {
        let weight = weight.unwrap_or(1.0);
        Self {
            name,
            host,
            port,
            weight,
            health_status: HealthStatus::Unknown,
            last_health_check: SystemTime::now()
                .duration_since(SystemTime::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        }
    }

    /// Mark service as healthy
    pub fn mark_healthy(&mut self) {
        self.health_status = HealthStatus::Healthy;
        self.last_health_check = SystemTime::now()
            .duration_since(SystemTime::UNIX_EPOCH)
            .unwrap()
            .as_secs();
    }

    /// Mark service as unhealthy
    pub fn mark_unhealthy(&mut self) {
        self.health_status = HealthStatus::Unhealthy;
        self.last_health_check = SystemTime::now()
            .duration_since(SystemTime::UNIX_EPOCH)
            .unwrap()
            .as_secs();
    }

    /// Check if service is healthy
    pub fn is_healthy(&self) -> bool {
        self.health_status == HealthStatus::Healthy
    }

    /// Get service endpoint as string
    pub fn endpoint(&self) -> String {
        format!("{}:{}", self.host, self.port)
    }

    fn __repr__(&self) -> String {
        format!(
            "ServiceInfo(name='{}', host='{}', port={}, weight={}, health={})",
            self.name, self.host, self.port, self.weight, self.health_status.__repr__()
        )
    }

    fn __eq__(&self, other: &Self) -> bool {
        self.name == other.name && self.host == other.host && self.port == other.port
    }

    fn __hash__(&self) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        
        let mut hasher = DefaultHasher::new();
        self.name.hash(&mut hasher);
        self.host.hash(&mut hasher);
        self.port.hash(&mut hasher);
        hasher.finish()
    }
}

impl ServiceInfo {
    /// Create a copy with updated health status
    pub fn with_health_status(&self, status: HealthStatus) -> Self {
        let mut new_service = self.clone();
        new_service.health_status = status;
        new_service.last_health_check = SystemTime::now()
            .duration_since(SystemTime::UNIX_EPOCH)
            .unwrap()
            .as_secs();
        new_service
    }
}
