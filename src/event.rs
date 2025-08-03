use parking_lot::Mutex;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use pyo3_async_runtimes::tokio::get_runtime;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::mpsc::{self, Sender};

struct Listener {
    callback: PyObject,
    is_async: bool,
}

#[pyclass(subclass, name = "RustEventChannel")]
struct EventChannel {
    channels: Arc<Mutex<HashMap<String, Sender<Py<PyDict>>>>>,
    listeners: Arc<Mutex<HashMap<String, Vec<Listener>>>>,
    // Buffer size for the channel
    buffer_size: usize,
}

#[pymethods]
impl EventChannel {
    #[new]
    #[pyo3(signature = (buffer_size=1000))]
    fn new(buffer_size: usize) -> Self {
        EventChannel {
            channels: Arc::new(Mutex::new(HashMap::new())),
            listeners: Arc::new(Mutex::new(HashMap::new())),
            buffer_size,
        }
    }

    fn register_listener(
        &mut self,
        event_name: String,
        callback: PyObject,
        is_async: bool,
        event_loop: PyObject,
        py: Python,
    ) -> PyResult<()> {
        let (tx, mut rx) = mpsc::channel(self.buffer_size);
        let listeners = Arc::clone(&self.listeners);

        // Register the listener
        // This is done in a blocking context to avoid deadlocks
        let mut listeners_lock = listeners.lock();
        listeners_lock
            .entry(event_name.clone())
            .or_insert_with(Vec::new)
            .push(Listener {
                callback: callback.clone_ref(py),
                is_async,
            });

        // Store the sender in the channels map
        // This is also done in a blocking context.
        let mut channels = self.channels.lock();
        channels.insert(event_name.clone(), tx);
        // Start the receiver task
        let event_name = event_name.clone();
        let listeners_for_task = Arc::clone(&self.listeners);
        get_runtime().spawn(async move {
            while let Some(data) = rx.recv().await {
                // Clone data and get listeners in a single GIL scope
                Python::with_gil(|py| {
                    let data = data.clone_ref(py);
                    let listeners = listeners_for_task.lock();
                    if let Some(listeners) = listeners.get(&event_name) {
                        for listener in listeners {
                            let callback = listener.callback.clone_ref(py);
                            if listener.is_async {
                                let callback = callback.clone_ref(py);
                                let coro =
                                    callback.call1(py, (data.clone_ref(py),))?;
                                event_loop
                                    .call_method1(py, "create_task", (coro,))
                                    .map_err(|e| PyErr::from(e))?;
                            } else {
                                // Run sync listener in thread pool
                                let callback = callback.clone_ref(py);
                                let data_for_listener = data.clone_ref(py);
                                get_runtime().spawn_blocking(move || {
                                    Python::with_gil(|py| {
                                        callback
                                            .call1(py, (data_for_listener,))
                                            .map_err(|e| PyErr::from(e))?;
                                        Ok::<(), PyErr>(())
                                    })
                                });
                            }
                        }
                    }
                    Ok::<(), PyErr>(())
                })
                .unwrap();
            }
        });

        Ok(())
    }

    async fn emit(&self, event_name: String, data: Py<PyDict>) -> PyResult<()> {
        // Clone the sender before await to avoid holding the lock across await
        let tx_opt = {
            let channels = self.channels.lock();
            channels.get(&event_name).cloned()
        };
        if let Some(tx) = tx_opt {
            tx.send(data).await.map_err(|e| {
                PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                    "Channel send error: {}",
                    e
                ))
            })?;
        }
        Ok(())
    }

    async fn cleanup(&self) -> PyResult<()> {
        {
            let mut channels = self.channels.lock();
            channels.clear();
        }
        {
            let mut listeners = self.listeners.lock();
            listeners.clear();
        }
        Ok(())
    }
}

pub fn register_events(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Register DI classes
    m.add_class::<EventChannel>()?;

    Ok(())
}
