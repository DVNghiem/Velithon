use pyo3::prelude::*;
use pyo3::types::{PyDict, PyBytes, PyList, PyType};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use uuid::Uuid;

/// VSP Error type
#[pyclass]
#[derive(Debug, Clone)]
pub struct VSPError {
    #[pyo3(get)]
    pub message: String,
}

#[pymethods]
impl VSPError {
    #[new]
    pub fn new(message: String) -> Self {
        Self { message }
    }

    fn __str__(&self) -> String {
        self.message.clone()
    }

    fn __repr__(&self) -> String {
        format!("VSPError('{}')", self.message)
    }
}

impl std::fmt::Display for VSPError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.message)
    }
}

impl std::error::Error for VSPError {}

/// VSP Message Header
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VSPHeader {
    pub request_id: String,
    pub service: String,
    pub endpoint: String,
    pub is_response: bool,
}

/// VSP Message body type
pub type VSPBody = HashMap<String, serde_json::Value>;

/// VSP Message implementation with high-performance serialization
#[pyclass]
#[derive(Debug, Clone)]
pub struct VSPMessage {
    #[pyo3(get)]
    pub request_id: String,
    #[pyo3(get)]
    pub service: String,
    #[pyo3(get)]
    pub endpoint: String,
    #[pyo3(get)]
    pub is_response: bool,
    
    // Internal representation
    header: VSPHeader,
    body: VSPBody,
    serialized_cache: Option<Vec<u8>>,
}

#[pymethods]
impl VSPMessage {
    #[new]
    pub fn new(
        request_id: String,
        service: String,
        endpoint: String,
        body: Bound<PyDict>,
        is_response: Option<bool>,
    ) -> PyResult<Self> {
        let is_response = is_response.unwrap_or(false);
        
        // Convert Python dict to VSPBody
        let mut vsp_body = HashMap::new();
        for (key, value) in body.iter() {
            let key_str: String = key.extract()?;
            let json_value = python_to_json_value(value)?;
            vsp_body.insert(key_str, json_value);
        }

        let header = VSPHeader {
            request_id: request_id.clone(),
            service: service.clone(),
            endpoint: endpoint.clone(),
            is_response,
        };

        Ok(Self {
            request_id,
            service,
            endpoint,
            is_response,
            header,
            body: vsp_body,
            serialized_cache: None,
        })
    }

    /// Serialize message to bytes with caching
    pub fn to_bytes<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyBytes>> {
        if let Some(cached) = &self.serialized_cache {
            return Ok(PyBytes::new(py, cached));
        }

        // Create the message structure
        let message_data = serde_json::json!({
            "header": self.header,
            "body": self.body
        });

        // Serialize with optimized JSON
        let serialized = serde_json::to_vec(&message_data)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Serialization failed: {}", e)
            ))?;

        // Cache small messages only to avoid memory bloat
        if serialized.len() < 1024 {
            self.serialized_cache = Some(serialized.clone());
        }

        Ok(PyBytes::new(py, &serialized))
    }

    /// Deserialize message from bytes
    #[classmethod]
    pub fn from_bytes(_cls: &Bound<PyType>, data: Bound<PyBytes>) -> PyResult<Self> {
        let bytes = data.as_bytes();
        
        // Deserialize JSON
        let message_data: serde_json::Value = serde_json::from_slice(bytes)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Deserialization failed: {}", e)
            ))?;

        // Extract header
        let header_obj = message_data.get("header")
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing header"))?;
        
        let header: VSPHeader = serde_json::from_value(header_obj.clone())
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Invalid header: {}", e)
            ))?;

        // Extract body
        let body_obj = message_data.get("body")
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing body"))?;
        
        let body: VSPBody = match body_obj.as_object() {
            Some(obj) => obj.iter().map(|(k, v)| (k.clone(), v.clone())).collect(),
            None => HashMap::new(),
        };

        Ok(Self {
            request_id: header.request_id.clone(),
            service: header.service.clone(),
            endpoint: header.endpoint.clone(),
            is_response: header.is_response,
            header,
            body,
            serialized_cache: None,
        })
    }

    /// Clear serialization cache
    pub fn clear_cache(&mut self) {
        self.serialized_cache = None;
    }

    /// Get body as Python dict
    pub fn get_body<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let dict = PyDict::new(py);
        for (key, value) in &self.body {
            let py_value = json_value_to_python(py, value)?;
            dict.set_item(key, py_value)?;
        }
        Ok(dict)
    }

    /// Generate new request ID
    #[staticmethod]
    pub fn generate_request_id() -> String {
        Uuid::new_v4().to_string()
    }

    fn __repr__(&self) -> String {
        format!(
            "VSPMessage(request_id={}, service={}, endpoint={}, is_response={})",
            self.request_id, self.service, self.endpoint, self.is_response
        )
    }
}

/// Convert Python value to JSON value
fn python_to_json_value(value: Bound<pyo3::PyAny>) -> PyResult<serde_json::Value> {
    if let Ok(s) = value.extract::<String>() {
        Ok(serde_json::Value::String(s))
    } else if let Ok(i) = value.extract::<i64>() {
        Ok(serde_json::Value::Number(serde_json::Number::from(i)))
    } else if let Ok(f) = value.extract::<f64>() {
        Ok(serde_json::Value::Number(serde_json::Number::from_f64(f).unwrap_or_else(|| serde_json::Number::from(0))))
    } else if let Ok(b) = value.extract::<bool>() {
        Ok(serde_json::Value::Bool(b))
    } else if value.is_none() {
        Ok(serde_json::Value::Null)
    } else {
        // Fallback: convert to string
        let s: String = value.str()?.extract()?;
        Ok(serde_json::Value::String(s))
    }
}

/// Convert JSON value to Python value
fn json_value_to_python(py: Python, value: &serde_json::Value) -> PyResult<PyObject> {
    match value {
        serde_json::Value::Null => Ok(py.None()),
        serde_json::Value::Bool(b) => {
            Ok(b.into_pyobject(py)?.as_any().clone().unbind())
        },
        serde_json::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Ok(pyo3::types::PyInt::new(py, i).unbind().into())
            } else if let Some(f) = n.as_f64() {
                Ok(pyo3::types::PyFloat::new(py, f).unbind().into())
            } else {
                Ok(py.None())
            }
        }
        serde_json::Value::String(s) => {
            Ok(pyo3::types::PyString::new(py, s).unbind().into())
        },
        serde_json::Value::Array(arr) => {
            let py_list = PyList::empty(py);
            for item in arr {
                let py_item = json_value_to_python(py, item)?;
                py_list.append(py_item)?;
            }
            Ok(py_list.unbind().into())
        }
        serde_json::Value::Object(obj) => {
            let py_dict = PyDict::new(py);
            for (key, val) in obj {
                let py_val = json_value_to_python(py, val)?;
                py_dict.set_item(key, py_val)?;
            }
            Ok(py_dict.unbind().into())
        }
    }
}
