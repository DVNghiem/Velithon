use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::sync::{Arc, Mutex};
use std::collections::HashMap;
use uuid::Uuid;

use crate::vsp::service::ServiceInfo;
use crate::vsp::discovery::StaticDiscovery;
use crate::vsp::load_balancer::RoundRobinBalancer;
use crate::vsp::transport::TCPTransport;
use crate::vsp::message::VSPMessage;
use crate::vsp::connection_pool::ConnectionPool;

/// VSP Client for making service calls
#[pyclass]
#[derive(Debug)]
pub struct VSPClient {
    discovery: Arc<Mutex<StaticDiscovery>>,
    load_balancer: Arc<RoundRobinBalancer>,
    connection_pool: Arc<ConnectionPool>,
    response_queues: Arc<Mutex<HashMap<String, String>>>, // Simplified for now
    max_transports: usize,
    timeout_seconds: u64,
}

#[pymethods]
impl VSPClient {
    #[new]
    #[pyo3(signature = (
        discovery = None,
        load_balancer = None,
        max_transports = None,
        timeout_seconds = None,
    ))]
    pub fn new(
        discovery: Option<StaticDiscovery>,
        load_balancer: Option<RoundRobinBalancer>,
        max_transports: Option<usize>,
        timeout_seconds: Option<u64>,
    ) -> Self {
        let discovery = discovery.unwrap_or_else(StaticDiscovery::new);
        let load_balancer = load_balancer.unwrap_or_else(RoundRobinBalancer::new);
        
        Self {
            discovery: Arc::new(Mutex::new(discovery)),
            load_balancer: Arc::new(load_balancer),
            connection_pool: Arc::new(ConnectionPool::new(max_transports)),
            response_queues: Arc::new(Mutex::new(HashMap::new())),
            max_transports: max_transports.unwrap_or(5),
            timeout_seconds: timeout_seconds.unwrap_or(30),
        }
    }

    /// Make a synchronous service call
    pub fn call_sync<'py>(
        &self,
        py: Python<'py>,
        service_name: String,
        endpoint: String,
        data: Bound<'py, PyDict>,
    ) -> PyResult<Bound<'py, PyDict>> {
        // Get service instances
        let services = {
            let discovery_lock = self.discovery.lock().unwrap();
            discovery_lock.query(&service_name)?
        };

        if services.is_empty() {
            return Err(PyErr::new::<pyo3::exceptions::PyConnectionError, _>(
                format!("No healthy instances found for service: {}", service_name)
            ));
        }

        // Select service instance using load balancer
        let selected_service = self.load_balancer.select(services)
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                "Load balancer failed to select service instance"
            ))?;

        // Generate request ID
        let request_id = Uuid::new_v4().to_string();

        // Create message
        let _message = VSPMessage::new(
            request_id.clone(),
            service_name.clone(),
            endpoint.clone(),
            data,
            Some(false),
        )?;

        // Get transport (simplified for now)
        let endpoint_addr = format!("{}:{}", selected_service.host, selected_service.port);
        let _transport = self.connection_pool.get_transport_internal(&endpoint_addr);

        // For now, return a simple response
        let response_dict = PyDict::new(py);
        response_dict.set_item("status", "success")?;
        response_dict.set_item("request_id", request_id)?;
        response_dict.set_item("service", service_name)?;
        response_dict.set_item("endpoint", endpoint)?;
        
        Ok(response_dict)
    }

    /// Get available services
    pub fn get_services(&self, service_name: String) -> PyResult<Vec<ServiceInfo>> {
        let discovery_lock = self.discovery.lock().unwrap();
        discovery_lock.query(&service_name)
    }

    /// Select service instance using load balancer
    pub fn select_service(&self, services: Vec<ServiceInfo>) -> PyResult<Option<ServiceInfo>> {
        Ok(self.load_balancer.select(services))
    }

    /// Add service to discovery
    pub fn register_service(&self, service: ServiceInfo) -> PyResult<()> {
        let mut discovery_lock = self.discovery.lock().unwrap();
        discovery_lock.register(service)?;
        Ok(())
    }

    /// Remove service from discovery
    pub fn unregister_service(&self, service_name: String) -> PyResult<()> {
        let mut discovery_lock = self.discovery.lock().unwrap();
        discovery_lock.unregister(service_name)?;
        Ok(())
    }

    /// Get client statistics
    pub fn get_stats(&self) -> PyResult<(usize, usize)> {
        self.connection_pool.get_stats()
    }

    /// Cleanup closed connections
    pub fn cleanup(&self) -> PyResult<usize> {
        self.connection_pool.cleanup()
    }

    fn __repr__(&self) -> String {
        let stats = self.connection_pool.get_stats().unwrap_or((0, 0));
        format!(
            "VSPClient(endpoints={}, connections={}, max_transports={}, timeout={}s)",
            stats.0, stats.1, self.max_transports, self.timeout_seconds
        )
    }
}

impl VSPClient {
    /// Internal method to get transport
    pub fn get_transport_for_service(&self, service: &ServiceInfo) -> Option<Arc<Mutex<TCPTransport>>> {
        let endpoint_addr = format!("{}:{}", service.host, service.port);
        self.connection_pool.get_transport_internal(&endpoint_addr)
    }
}
