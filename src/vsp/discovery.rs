use pyo3::prelude::*;
use crate::vsp::service::ServiceInfo;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use tokio::runtime::Runtime;
use serde_json::Value;

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

/// mDNS Discovery implementation with simplified functionality
#[pyclass]
#[derive(Debug, Clone)]
pub struct MDNSDiscovery {
    services: Arc<Mutex<HashMap<String, Vec<ServiceInfo>>>>,
    service_type: String,
    runtime: Arc<Runtime>,
}

#[pymethods]
impl MDNSDiscovery {
    #[new]
    pub fn new() -> Self {
        Self {
            services: Arc::new(Mutex::new(HashMap::new())),
            service_type: "_vsp._tcp.local.".to_string(),
            runtime: Arc::new(Runtime::new().expect("Failed to create Tokio runtime")),
        }
    }

    /// Register a service with mDNS
    pub fn register(&mut self, service: ServiceInfo) -> PyResult<()> {
        // Cache the service locally
        let mut services = self.services.lock().unwrap();
        services
            .entry(service.name.clone())
            .or_insert_with(Vec::new)
            .push(service.clone());
        
        // Log the registration - in a real implementation, we would broadcast via mDNS
        println!("mDNS: Registered service {} at {}:{}", 
                service.name, service.host, service.port);
        
        Ok(())
    }

    /// Query services by name using mDNS
    pub fn query(&self, service_name: &str) -> PyResult<Vec<ServiceInfo>> {
        let services = self.services.lock().unwrap();
        let local_services = services.get(service_name).cloned().unwrap_or_default();
        
        // Log the query - in a real implementation, we would query the network
        println!("mDNS: Queried service {} - found {} instances", 
                service_name, local_services.len());
        
        Ok(local_services)
    }

    /// Unregister a service from mDNS
    pub fn unregister(&mut self, service_name: String) -> PyResult<()> {
        let mut services = self.services.lock().unwrap();
        services.remove(&service_name);
        
        println!("mDNS: Unregistered service {}", service_name);
        Ok(())
    }

    /// Set custom service type for mDNS
    pub fn set_service_type(&mut self, service_type: String) -> PyResult<()> {
        self.service_type = service_type;
        Ok(())
    }

    /// Get current service type
    pub fn get_service_type(&self) -> String {
        self.service_type.clone()
    }

    /// List all locally cached services
    pub fn list_local_services(&self) -> PyResult<Vec<ServiceInfo>> {
        let services = self.services.lock().unwrap();
        let mut all_services = Vec::new();
        
        for service_list in services.values() {
            all_services.extend(service_list.clone());
        }
        
        Ok(all_services)
    }

    fn __repr__(&self) -> String {
        "MDNSDiscovery()".to_string()
    }
}

/// Consul Discovery implementation with actual HTTP API calls
#[pyclass]
#[derive(Debug, Clone)]
pub struct ConsulDiscovery {
    consul_host: String,
    consul_port: u16,
    services: Arc<Mutex<HashMap<String, Vec<ServiceInfo>>>>,
    runtime: Arc<Runtime>,
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
            runtime: Arc::new(Runtime::new().expect("Failed to create Tokio runtime")),
        }
    }

    /// Register a service with Consul
    pub fn register(&mut self, service: ServiceInfo) -> PyResult<()> {
        let consul_url = format!("http://{}:{}", self.consul_host, self.consul_port);
        let service_id = format!("{}-{}-{}", service.name, service.host, service.port);
        
        // Create the service registration payload
        let registration = serde_json::json!({
            "ID": service_id,
            "Name": service.name,
            "Address": service.host,
            "Port": service.port,
            "Tags": [format!("weight={}", service.weight)],
            "Check": {
                "TCP": format!("{}:{}", service.host, service.port),
                "Interval": "10s"
            }
        });

        let rt = &self.runtime;
        let register_url = format!("{}/v1/agent/service/register", consul_url);
        
        // Perform the registration
        let result = rt.block_on(async {
            let client = reqwest::Client::new();
            let response = client
                .put(&register_url)
                .json(&registration)
                .send()
                .await
                .map_err(|e| format!("HTTP request failed: {}", e))?;
            
            if response.status().is_success() {
                Ok(())
            } else {
                Err(format!("Consul registration failed: {}", response.status()))
            }
        });

        match result {
            Ok(()) => {
                // Cache the service locally as well
                let mut services = self.services.lock().unwrap();
                services
                    .entry(service.name.clone())
                    .or_insert_with(Vec::new)
                    .push(service);
                Ok(())
            }
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Failed to register service with Consul: {}", e)
            ))
        }
    }

    /// Query services by name from Consul
    pub fn query(&self, service_name: &str) -> PyResult<Vec<ServiceInfo>> {
        let consul_url = format!("http://{}:{}", self.consul_host, self.consul_port);
        let query_url = format!("{}/v1/catalog/service/{}", consul_url, service_name);
        
        let rt = &self.runtime;
        
        let result = rt.block_on(async {
            let client = reqwest::Client::new();
            let response = client
                .get(&query_url)
                .send()
                .await
                .map_err(|e| format!("HTTP request failed: {}", e))?;
            
            if response.status().is_success() {
                let services_data: Vec<Value> = response.json().await
                    .map_err(|e| format!("JSON parsing failed: {}", e))?;
                let mut services = Vec::new();
                
                for service_data in services_data {
                    if let (Some(address), Some(port)) = (
                        service_data["Address"].as_str(),
                        service_data["ServicePort"].as_u64()
                    ) {
                        let mut weight = 1.0;
                        
                        // Extract weight from tags
                        if let Some(tags) = service_data["ServiceTags"].as_array() {
                            for tag in tags {
                                if let Some(tag_str) = tag.as_str() {
                                    if tag_str.starts_with("weight=") {
                                        if let Ok(w) = tag_str[7..].parse::<f64>() {
                                            weight = w;
                                        }
                                    }
                                }
                            }
                        }
                        
                        services.push(ServiceInfo::new(
                            service_name.to_string(),
                            address.to_string(),
                            port as u16,
                            Some(weight),
                        ));
                    }
                }
                
                Ok(services)
            } else {
                Err(format!("Consul query failed: {}", response.status()))
            }
        });

        match result {
            Ok(services) => Ok(services),
            Err(e) => {
                // Fallback to local cache on error
                let services = self.services.lock().unwrap();
                let cached_services = services.get(service_name).cloned().unwrap_or_default();
                
                // Return cached services but log the error
                eprintln!("Consul query failed, using cached services: {}", e);
                Ok(cached_services)
            }
        }
    }

    /// Unregister a service from Consul
    pub fn unregister(&mut self, service_name: String) -> PyResult<()> {
        let consul_url = format!("http://{}:{}", self.consul_host, self.consul_port);
        let rt = &self.runtime;
        
        // Get all services with this name to unregister them
        let services_to_remove = {
            let services = self.services.lock().unwrap();
            services.get(&service_name).cloned().unwrap_or_default()
        };
        
        for service in &services_to_remove {
            let service_id = format!("{}-{}-{}", service.name, service.host, service.port);
            let deregister_url = format!("{}/v1/agent/service/deregister/{}", consul_url, service_id);
            
            let _ = rt.block_on(async {
                let client = reqwest::Client::new();
                client.put(&deregister_url).send().await
            });
        }
        
        // Remove from local cache
        let mut services = self.services.lock().unwrap();
        services.remove(&service_name);
        
        Ok(())
    }

    /// Get the Consul API URL
    pub fn get_consul_url(&self) -> String {
        format!("http://{}:{}", self.consul_host, self.consul_port)
    }

    /// Health check - verify Consul is accessible
    pub fn health_check(&self) -> PyResult<bool> {
        let consul_url = format!("http://{}:{}/v1/status/leader", self.consul_host, self.consul_port);
        let rt = &self.runtime;
        
        let result: Result<bool, reqwest::Error> = rt.block_on(async {
            let client = reqwest::Client::new();
            let response = client.get(&consul_url).send().await?;
            Ok(response.status().is_success())
        });
        
        match result {
            Ok(is_healthy) => Ok(is_healthy),
            Err(_) => Ok(false),
        }
    }

    /// Check if Consul is healthy/available
    pub fn check_health(&self) -> PyResult<bool> {
        let consul_url = format!("http://{}:{}", self.consul_host, self.consul_port);
        let health_url = format!("{}/v1/status/leader", consul_url);
        
        let rt = &self.runtime;
        let result: Result<bool, reqwest::Error> = rt.block_on(async {
            let client = reqwest::Client::new();
            match client.get(&health_url).send().await {
                Ok(response) => Ok(response.status().is_success()),
                Err(_) => Ok(false),
            }
        });
        
        Ok(result.unwrap_or(false))
    }

    fn __repr__(&self) -> String {
        format!(
            "ConsulDiscovery(host='{}', port={})",
            self.consul_host, self.consul_port
        )
    }
}
