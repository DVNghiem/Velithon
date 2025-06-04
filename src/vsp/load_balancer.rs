use pyo3::prelude::*;

use crate::vsp::service::ServiceInfo;

#[pyclass(subclass)]
pub struct LoadBalancer;

#[pymethods]
impl LoadBalancer {
    // Load Balancer base class

    pub fn select(&self, _instances: Vec<ServiceInfo>) -> PyResult<ServiceInfo> {
        // This method should be overridden by subclasses
        Err(pyo3::exceptions::PyNotImplementedError::new_err(
            "select() must be implemented by subclasses",
        ))
    }
}

// implementation of LoadBalancer subclass
// Round-robin load balancing strategy

#[pyclass(extends=LoadBalancer)]
pub struct RoundRobinBalancer {
    index: u32,
}

#[pymethods]
impl RoundRobinBalancer {
    // Round-Robin Load Balancer

    #[new]
    pub fn new() -> (Self, LoadBalancer) {
        (RoundRobinBalancer { index: 0 }, LoadBalancer)
    }

    pub fn select(&mut self, instances: Vec<ServiceInfo>) -> PyResult<ServiceInfo> {
        if instances.is_empty() {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "No instances available for selection",
            ));
        }

        // Select the next instance in a round-robin fashion
        self.index = (self.index + 1) % instances.len() as u32;
        let selected_instance = instances[self.index as usize].clone();

        Ok(selected_instance)
    }
}

// WeightedBalancer load balancing strategy
#[pyclass(extends=LoadBalancer)]
pub struct WeightedBalancer;

#[pymethods]
impl WeightedBalancer {
    // Weighted Load Balancer
    #[new]
    pub fn new() -> (Self, LoadBalancer) {
        (WeightedBalancer, LoadBalancer)
    }

    pub fn select(&mut self, mut instances: Vec<ServiceInfo>) -> PyResult<ServiceInfo> {
        if instances.is_empty() {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "No instances available for selection",
            ));
        }
        // sort weights and instances together
        instances
            .sort_by(|a, b| a.weight.partial_cmp(&b.weight).unwrap_or(std::cmp::Ordering::Equal));
        // Select the instance with the highest weight
        let selected_instance = instances.last().unwrap().clone();
        Ok(selected_instance)
    }
}
