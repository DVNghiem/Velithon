use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use crate::vsp::service::ServiceInfo;
use crate::vsp::discovery::StaticDiscovery;
use crate::vsp::client::VSPClient;

/// Worker type enumeration
#[pyclass]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum WorkerType {
    Asyncio,
    Multicore,
}

#[pymethods]
impl WorkerType {
    fn __repr__(&self) -> String {
        match self {
            WorkerType::Asyncio => "WorkerType.Asyncio".to_string(),
            WorkerType::Multicore => "WorkerType.Multicore".to_string(),
        }
    }
}

/// VSP Manager for handling service endpoints and workers
#[pyclass]
#[derive(Debug)]
pub struct VSPManager {
    #[pyo3(get)]
    pub name: String,
    
    discovery: Arc<Mutex<StaticDiscovery>>,
    client: Arc<VSPClient>,
    endpoints: Arc<Mutex<HashMap<String, String>>>, // endpoint -> handler name
    
    // Worker configuration
    num_workers: usize,
    worker_type: WorkerType,
    max_queue_size: usize,
    
    // Server state
    server_running: Arc<Mutex<bool>>,
}

#[pymethods]
impl VSPManager {
    #[new]
    #[pyo3(signature = (name, service_mesh = None, num_workers = 4, worker_type = WorkerType::Asyncio, max_queue_size = 2000, max_transports = 10))]
    pub fn new(
        name: String,
        service_mesh: Option<StaticDiscovery>,
        num_workers: Option<usize>,
        worker_type: Option<WorkerType>,
        max_queue_size: Option<usize>,
        max_transports: Option<usize>,
    ) -> Self {
        let discovery = service_mesh.unwrap_or_else(StaticDiscovery::new);
        let client = VSPClient::new(
            Some(discovery.clone()),
            None,
            max_transports,
            None,
        );
        
        Self {
            name,
            discovery: Arc::new(Mutex::new(discovery)),
            client: Arc::new(client),
            endpoints: Arc::new(Mutex::new(HashMap::new())),
            num_workers: num_workers.unwrap_or(4).max(1),
            worker_type: worker_type.unwrap_or(WorkerType::Asyncio),
            max_queue_size: max_queue_size.unwrap_or(2000),
            server_running: Arc::new(Mutex::new(false)),
        }
    }

    /// Register a service endpoint
    pub fn register_endpoint(&self, endpoint: String, handler_name: String) -> PyResult<()> {
        let mut endpoints_lock = self.endpoints.lock().unwrap();
        endpoints_lock.insert(endpoint, handler_name);
        Ok(())
    }

    /// Start the VSP server
    pub fn start_server(&self, host: String, port: u16) -> PyResult<()> {
        let mut running = self.server_running.lock().unwrap();
        *running = true;
        
        println!("Starting VSP server '{}' on {}:{}", self.name, host, port);
        println!("Workers: {} ({})", self.num_workers, self.worker_type.__repr__());
        
        Ok(())
    }

    /// Stop the VSP server
    pub fn stop_server(&self) -> PyResult<()> {
        let mut running = self.server_running.lock().unwrap();
        *running = false;
        println!("VSP server '{}' stopped", self.name);
        Ok(())
    }

    /// Handle a VSP endpoint call
    pub fn handle_endpoint(&self, endpoint: String, _body: Bound<PyDict>) -> PyResult<String> {
        let endpoints = self.endpoints.lock().unwrap();
        let handler_name = endpoints.get(&endpoint)
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>(
                format!("Endpoint '{}' not found", endpoint)
            ))?;

        // For now, just return a simple response
        Ok(format!("Handled by {}", handler_name))
    }

    /// Check if server is running
    pub fn is_running(&self) -> bool {
        *self.server_running.lock().unwrap()
    }

    /// Get registered endpoints
    pub fn get_endpoints(&self) -> PyResult<Vec<String>> {
        let endpoints = self.endpoints.lock().unwrap();
        Ok(endpoints.keys().cloned().collect())
    }

    /// Register a service in the service mesh
    pub fn register_service(&self, service: ServiceInfo) -> PyResult<()> {
        let mut discovery = self.discovery.lock().unwrap();
        discovery.register(service)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e))
    }

    /// Check if client is available
    pub fn has_client(&self) -> bool {
        true // Client is always available since it's created in new()
    }

    fn __repr__(&self) -> String {
        let running = *self.server_running.lock().unwrap();
        let endpoints_count = self.endpoints.lock().unwrap().len();
        
        format!(
            "VSPManager(name='{}', running={}, workers={}, endpoints={})",
            self.name, running, self.num_workers, endpoints_count
        )
    }
}
