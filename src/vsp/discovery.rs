use pyo3::prelude::*;
use crate::vsp::service::ServiceInfo;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

/// Discovery type enumeration
#[pyclass]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DiscoveryType {
    Static,
    MDNS,
    Consul,
}

#[pymethods]
impl DiscoveryType {
    fn __repr__(&self) -> String {
        match self {
            DiscoveryType::Static => "DiscoveryType.Static".to_string(),
            DiscoveryType::MDNS => "DiscoveryType.MDNS".to_string(),
            DiscoveryType::Consul => "DiscoveryType.Consul".to_string(),
        }
    }
}

/// Abstract Discovery trait (for internal use)
pub trait Discovery: Send + Sync {
    fn register(&mut self, service: ServiceInfo) -> Result<(), String>;
    fn query(&self, service_name: &str) -> Result<Vec<ServiceInfo>, String>;
    fn unregister(&mut self, service_name: &str) -> Result<(), String>;
    fn close(&mut self) -> Result<(), String>;
}

/// Static service discovery implementation
#[pyclass]
#[derive(Debug, Clone)]
pub struct StaticDiscovery {
    services: Arc<Mutex<HashMap<String, Vec<ServiceInfo>>>>,
}

#[pymethods]
impl StaticDiscovery {
    #[new]
    pub fn new() -> Self {
        Self {
            services: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    /// Register a service
    pub fn register(&mut self, service: ServiceInfo) -> PyResult<()> {
        let mut services = self.services.lock().unwrap();
        services
            .entry(service.name.clone())
            .or_insert_with(Vec::new)
            .push(service);
        Ok(())
    }

    /// Query services by name
    pub fn query(&self, service_name: &str) -> PyResult<Vec<ServiceInfo>> {
        let services = self.services.lock().unwrap();
        let service_list = services
            .get(service_name)
            .cloned()
            .unwrap_or_default();
        
        // Filter for healthy services
        let healthy_services: Vec<ServiceInfo> = service_list
            .into_iter()
            .filter(|s| s.is_healthy())
            .collect();
        
        Ok(healthy_services)
    }

    /// Unregister all services with given name
    pub fn unregister(&mut self, service_name: String) -> PyResult<()> {
        let mut services = self.services.lock().unwrap();
        services.remove(&service_name);
        Ok(())
    }

    /// List all registered services
    pub fn list_all_services(&self) -> PyResult<Vec<ServiceInfo>> {
        let services = self.services.lock().unwrap();
        let mut all_services = Vec::new();
        
        for service_list in services.values() {
            all_services.extend(service_list.clone());
        }
        
        Ok(all_services)
    }

    /// Get service count for a given service name
    pub fn get_service_count(&self, service_name: String) -> PyResult<usize> {
        let services = self.services.lock().unwrap();
        Ok(services.get(&service_name).map(|s| s.len()).unwrap_or(0))
    }

    /// Clear all services
    pub fn clear(&mut self) -> PyResult<()> {
        let mut services = self.services.lock().unwrap();
        services.clear();
        Ok(())
    }

    fn __repr__(&self) -> String {
        let services = self.services.lock().unwrap();
        let count = services.len();
        format!("StaticDiscovery(services={})", count)
    }
}

impl Discovery for StaticDiscovery {
    fn register(&mut self, service: ServiceInfo) -> Result<(), String> {
        let mut services = self.services.lock().unwrap();
        services
            .entry(service.name.clone())
            .or_insert_with(Vec::new)
            .push(service);
        Ok(())
    }

    fn query(&self, service_name: &str) -> Result<Vec<ServiceInfo>, String> {
        let services = self.services.lock().unwrap();
        let service_list = services
            .get(service_name)
            .cloned()
            .unwrap_or_default();
        
        // Filter for healthy services
        let healthy_services: Vec<ServiceInfo> = service_list
            .into_iter()
            .filter(|s| s.is_healthy())
            .collect();
        
        Ok(healthy_services)
    }

    fn unregister(&mut self, service_name: &str) -> Result<(), String> {
        let mut services = self.services.lock().unwrap();
        services.remove(service_name);
        Ok(())
    }

    fn close(&mut self) -> Result<(), String> {
        let mut services = self.services.lock().unwrap();
        services.clear();
        Ok(())
    }
}

/// mDNS Discovery implementation (placeholder for now)
#[pyclass]
#[derive(Debug, Clone)]
pub struct MDNSDiscovery {
    services: Arc<Mutex<HashMap<String, Vec<ServiceInfo>>>>,
}

#[pymethods]
impl MDNSDiscovery {
    #[new]
    pub fn new() -> Self {
        Self {
            services: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    /// Register a service
    pub fn register(&mut self, service: ServiceInfo) -> PyResult<()> {
        // TODO: Implement actual mDNS registration
        let mut services = self.services.lock().unwrap();
        services
            .entry(service.name.clone())
            .or_insert_with(Vec::new)
            .push(service);
        Ok(())
    }

    /// Query services by name
    pub fn query(&self, service_name: &str) -> PyResult<Vec<ServiceInfo>> {
        // TODO: Implement actual mDNS query
        let services = self.services.lock().unwrap();
        Ok(services.get(service_name).cloned().unwrap_or_default())
    }

    fn __repr__(&self) -> String {
        "MDNSDiscovery()".to_string()
    }
}

/// Consul Discovery implementation (placeholder for now)
#[pyclass]
#[derive(Debug, Clone)]
pub struct ConsulDiscovery {
    consul_host: String,
    consul_port: u16,
    services: Arc<Mutex<HashMap<String, Vec<ServiceInfo>>>>,
}

#[pymethods]
impl ConsulDiscovery {
    #[new]
    #[pyo3(signature = (consul_host = "localhost".to_string(), consul_port = 8500))]
    pub fn new(consul_host: Option<String>, consul_port: Option<u16>) -> Self {
        Self {
            consul_host: consul_host.unwrap_or_else(|| "localhost".to_string()),
            consul_port: consul_port.unwrap_or(8500),
            services: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    /// Register a service
    pub fn register(&mut self, service: ServiceInfo) -> PyResult<()> {
        // TODO: Implement actual Consul registration
        let mut services = self.services.lock().unwrap();
        services
            .entry(service.name.clone())
            .or_insert_with(Vec::new)
            .push(service);
        Ok(())
    }

    /// Query services by name
    pub fn query(&self, service_name: &str) -> PyResult<Vec<ServiceInfo>> {
        // TODO: Implement actual Consul query
        let services = self.services.lock().unwrap();
        Ok(services.get(service_name).cloned().unwrap_or_default())
    }

    fn __repr__(&self) -> String {
        format!(
            "ConsulDiscovery(host='{}', port={})",
            self.consul_host, self.consul_port
        )
    }
}
