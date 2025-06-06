use pyo3::prelude::*;
use async_trait::async_trait;
use tokio::net::TcpStream;
use tokio::io::AsyncWriteExt;
use std::sync::Arc;
use parking_lot::Mutex;
use crate::error::{VSPInternalError, VSPResult};

#[async_trait]
#[allow(dead_code)]
pub trait Transport: Send + Sync {
    async fn connect(&mut self, host: &str, port: u16) -> VSPResult<()>;
    async fn send(&mut self, data: &[u8]) -> VSPResult<()>;
    fn close(&mut self) -> VSPResult<()>;
    fn is_closed(&self) -> bool;
}

#[pyclass]
pub struct TCPTransport {
    stream: Arc<Mutex<Option<TcpStream>>>,
    is_closed: Arc<Mutex<bool>>,
}

#[pymethods]
impl TCPTransport {
    #[new]
    pub fn new() -> Self {
        Self {
            stream: Arc::new(Mutex::new(None)),
            is_closed: Arc::new(Mutex::new(true)),
        }
    }
    
    pub fn connect<'p>(&mut self, py: Python<'p>, host: String, port: u16) -> PyResult<Bound<'p, PyAny>> {
        let stream_arc = self.stream.clone();
        let is_closed_arc = self.is_closed.clone();
        
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let stream = TcpStream::connect(format!("{}:{}", host, port)).await
                .map_err(|e| VSPInternalError::Connection(e.to_string()))?;
            
            {
                let mut stream_guard = stream_arc.lock();
                *stream_guard = Some(stream);
            }
            
            {
                let mut closed_guard = is_closed_arc.lock();
                *closed_guard = false;
            }
            
            Ok(())
        })
    }
    pub fn send<'p>(&mut self, py: Python<'p>, data: Vec<u8>) -> PyResult<Bound<'p, PyAny>> {
        let stream_arc = self.stream.clone();
        let is_closed_arc = self.is_closed.clone();
        
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let is_closed = {
                let closed_guard = is_closed_arc.lock();
                *closed_guard
            };
            
            if is_closed {
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    "Cannot send: TCP transport is closed"
                ));
            }
            
            // Extract the stream from the Arc<Mutex<Option<TcpStream>>> temporarily
            let stream_option = {
                let mut stream_guard = stream_arc.lock();
                stream_guard.take()
            };
            
            if let Some(mut stream) = stream_option {
                let result = stream.write_all(&data).await
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                        format!("Transport error: {}", e)
                    ));
                
                // Put the stream back
                {
                    let mut stream_guard = stream_arc.lock();
                    *stream_guard = Some(stream);
                }
                
                result
            } else {
                Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    "TCP transport not connected"
                ))
            }
        })
    }
    
    pub fn close(&mut self) -> PyResult<()> {
        {
            let mut stream_guard = self.stream.lock();
            *stream_guard = None;
        }
        
        {
            let mut closed_guard = self.is_closed.lock();
            *closed_guard = true;
        }
        
        Ok(())
    }
    
    pub fn is_closed(&self) -> bool {
        let closed_guard = self.is_closed.lock();
        *closed_guard
    }
}

#[async_trait]
impl Transport for TCPTransport {
    async fn connect(&mut self, host: &str, port: u16) -> VSPResult<()> {
        let stream = TcpStream::connect(format!("{}:{}", host, port)).await
            .map_err(|e| VSPInternalError::Connection(e.to_string()))?;
        
        {
            let mut stream_guard = self.stream.lock();
            *stream_guard = Some(stream);
        }
        
        {
            let mut closed_guard = self.is_closed.lock();
            *closed_guard = false;
        }
        
        Ok(())
    }
    
    async fn send(&mut self, data: &[u8]) -> VSPResult<()> {
        let is_closed = {
            let closed_guard = self.is_closed.lock();
            *closed_guard
        };
        
        if is_closed {
            return Err(VSPInternalError::Transport(
                "Cannot send: TCP transport is closed".to_string()
            ));
        }
        
        // Extract the stream from the Arc<Mutex<Option<TcpStream>>> temporarily
        let stream_option = {
            let mut stream_guard = self.stream.lock();
            stream_guard.take()
        };
        
        if let Some(mut stream) = stream_option {
            let result = stream.write_all(data).await
                .map_err(|e| VSPInternalError::Transport(e.to_string()));
            
            // Put the stream back
            {
                let mut stream_guard = self.stream.lock();
                *stream_guard = Some(stream);
            }
            
            result
        } else {
            Err(VSPInternalError::Transport(
                "TCP transport not connected".to_string()
            ))
        }
    }
    
    fn close(&mut self) -> VSPResult<()> {
        {
            let mut stream_guard = self.stream.lock();
            *stream_guard = None;
        }
        
        {
            let mut closed_guard = self.is_closed.lock();
            *closed_guard = true;
        }
        
        Ok(())
    }
    
    fn is_closed(&self) -> bool {
        let closed_guard = self.is_closed.lock();
        *closed_guard
    }
}

impl Default for TCPTransport {
    fn default() -> Self {
        Self::new()
    }
}

// Transport factory trait
#[allow(dead_code)]
pub trait TransportFactory: Send + Sync {
    fn create_transport(&self) -> Box<dyn Transport>;
}

#[derive(Clone)]
pub struct TCPTransportFactory;

impl TransportFactory for TCPTransportFactory {
    fn create_transport(&self) -> Box<dyn Transport> {
        Box::new(TCPTransport::new())
    }
}