use pyo3::prelude::*;
use pyo3::types::PyDict;
use tokio::sync::mpsc::{self, Sender};
use std::sync::Arc;
use tokio::sync::Mutex;
use std::collections::HashMap;
use pyo3_async_runtimes::tokio::future_into_py;

struct Listener {
    callback: PyObject,
    is_async: bool,
}

#[pyclass]
struct EventChannel {
    channels: Arc<Mutex<HashMap<String, Sender<Py<PyDict>>>>>,
    listeners: Arc<Mutex<HashMap<String, Vec<Listener>>>>,
}

#[pymethods]
impl EventChannel {
    #[new]
    fn new() -> Self {
        EventChannel {
            channels: Arc::new(Mutex::new(HashMap::new())),
            listeners: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    fn register_listener(&mut self, event_name: String, callback: PyObject, is_async: bool, py: Python) -> PyResult<()> {
        let (tx, mut rx) = mpsc::channel(1000); // Buffer size 1000
        let listeners = Arc::clone(&self.listeners);
        
        // Register the listener
        // This is done in a blocking context to avoid deadlocks
        let mut listeners_lock = listeners.blocking_lock();
        listeners_lock.entry(event_name.clone()).or_insert_with(Vec::new).push(Listener {
            callback: callback.clone_ref(py),
            is_async,
        });

        // Store the sender in the channels map
        // This is also done in a blocking context.
        let mut channels = self.channels.blocking_lock();
        channels.insert(event_name.clone(), tx);

        // Start the receiver task
        let event_name = event_name.clone();
        let listeners_for_task = Arc::clone(&self.listeners);
        tokio::spawn(async move {
            while let Some(data) = rx.recv().await {
                // Clone data and get listeners in a single GIL scope
                Python::with_gil(|py| {
                    let data = data.clone_ref(py);
                    let listeners = listeners_for_task.blocking_lock();
                    if let Some(listeners) = listeners.get(&event_name) {
                        for listener in listeners {
                            let callback = listener.callback.clone_ref(py);
                            let data_for_listener = data.clone_ref(py);
                            if listener.is_async {
                                // Run async listener in asyncio event loop
                                future_into_py(py, async move {
                                    Python::with_gil(|py| {
                                        let coro = callback.call1(py, (data_for_listener.clone_ref(py),))?;
                                        coro.call0(py)?;
                                        Ok::<(), PyErr>(())
                                    })
                                }).unwrap();
                            } else {
                                // Run sync listener in thread pool
                                let callback = callback.clone_ref(py);
                                let data = data_for_listener.clone_ref(py);
                                tokio::task::spawn_blocking(move || {
                                    Python::with_gil(|py| {
                                        callback.call1(py, (data,))?;
                                        Ok::<(), PyErr>(())
                                    })
                                });
                            }
                        }
                    }
                    Ok::<(), PyErr>(())
                }).unwrap();
            }
        });

        Ok(())
    }

    async fn emit(&self, event_name: String, data: Py<PyDict>) -> PyResult<()> {
        let channels = self.channels.lock().await;
        if let Some(tx) = channels.get(&event_name) {
            tx.send(data).await.map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Channel send error: {}", e)))?;
        }
        Ok(())
    }

    async fn cleanup(&self) -> PyResult<()> {
        let mut channels = self.channels.lock().await;
        channels.clear();
        let mut listeners = self.listeners.lock().await;
        listeners.clear();
        Ok(())
    }
}


pub fn register_events(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Register DI classes
    m.add_class::<EventChannel>()?;

    Ok(())
}
