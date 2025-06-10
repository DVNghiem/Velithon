use pyo3::prelude::*;
use pyo3::exceptions::PyException;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum VSPInternalError {
    #[error("Transport error: {0}")]
    Transport(String),
    
    #[error("Serialization error: {0}")]
    Serialization(String),
    
    #[error("Connection error: {0}")]
    Connection(String),
    
    #[error("Discovery error: {0}")]
    Discovery(String),
    
    #[error("Service error: {0}")]
    Service(String),
    
    #[error("Timeout error: {0}")]
    Timeout(String),
    
    #[error("Queue full error: {0}")]
    QueueFull(String),
    
    #[error("Worker error: {0}")]
    Worker(String),
    
    #[error("Protocol error: {0}")]
    Protocol(String),
    
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
    
    #[error("Other error: {0}")]
    Other(String),
}

#[pyclass(extends=PyException)]
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
    
    pub fn __str__(&self) -> String {
        self.message.clone()
    }
    
    pub fn __repr__(&self) -> String {
        format!("VSPError('{}')", self.message)
    }
}

impl From<VSPInternalError> for VSPError {
    fn from(err: VSPInternalError) -> Self {
        VSPError::new(err.to_string())
    }
}

impl From<VSPError> for PyErr {
    fn from(err: VSPError) -> Self {
        PyErr::new::<VSPError, _>(err.message)
    }
}

impl From<VSPInternalError> for PyErr {
    fn from(err: VSPInternalError) -> Self {
        PyErr::new::<VSPError, _>(err.to_string())
    }
}

// Helper macro for error handling
#[macro_export]
macro_rules! vsp_error {
    ($msg:expr) => {
        VSPInternalError::Other($msg.to_string())
    };
    ($fmt:expr, $($arg:tt)*) => {
        VSPInternalError::Other(format!($fmt, $($arg)*))
    };
}

// Result type alias
pub type VSPResult<T> = Result<T, VSPInternalError>;