use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyTuple};
use pyo3_async_runtimes::tokio::future_into_py;
use std::collections::VecDeque;
use std::sync::Arc;
use parking_lot::Mutex as ParkingLotMutex;
use tokio::sync::Semaphore;

/// A high-performance background task implementation in Rust
#[pyclass]
pub struct BackgroundTask {
    func: Py<PyAny>,
    args: Py<PyAny>,
    kwargs: Py<PyAny>,
    is_async: bool,
}

impl Clone for BackgroundTask {
    fn clone(&self) -> Self {
        Python::attach(|py| {
            Self {
                func: self.func.clone_ref(py),
                args: self.args.clone_ref(py),
                kwargs: self.kwargs.clone_ref(py),
                is_async: self.is_async,
            }
        })
    }
}

#[pymethods]
impl BackgroundTask {
    #[new]
    #[pyo3(signature = (func, args = None, kwargs = None))]
    fn new(
        py: Python<'_>,
        func: Py<PyAny>,
        args: Option<&Bound<'_, PyTuple>>,
        kwargs: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<Self> {
        let is_async = Self::is_async_callable(py, &func)?;
        let kwargs_obj = match kwargs {
            Some(k) => k.clone().unbind(),
            None => PyDict::new(py).unbind(),
        };
        let args_obj = match args {
            Some(a) => a.clone().unbind(),
            None => PyTuple::empty(py).unbind(),
        };

        Ok(Self {
            func,
            args: args_obj.into(),
            kwargs: kwargs_obj.into(),
            is_async,
        })
    }

    /// Execute the background task
    fn __call__<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let func = self.func.clone_ref(py);
        let args = self.args.clone_ref(py);
        let kwargs = self.kwargs.clone_ref(py);
        let is_async = self.is_async;

        future_into_py(py, async move {
            if is_async {
                // For async functions, create the coroutine and properly await it
                let coroutine = Python::attach(|py| -> PyResult<Py<PyAny>> {
                    let func_bound = func.bind(py);
                    let args_bound = args.bind(py).cast::<PyTuple>()?;
                    let kwargs_bound = kwargs.bind(py).cast::<PyDict>()?;
                    let coro = func_bound.call(args_bound, Some(kwargs_bound))?;
                    Ok(coro.unbind())
                })?;

                // Use pyo3_asyncio to properly await the Python coroutine
                let future_result = Python::attach(|py| {
                    let coro_bound = coroutine.bind(py);
                    pyo3_async_runtimes::tokio::into_future(coro_bound.clone())
                });
                
                let result = match future_result {
                    Ok(future) => future.await,
                    Err(err) => return Err(err),
                };
                
                match result {
                    Ok(py_result) => Ok(py_result.into()),
                    Err(py_err) => {
                        Python::attach(|py| {
                            let type_name = py_err.get_type(py).name().map(|s| s.to_string()).unwrap_or_else(|_| "UnknownError".to_string());
                            Err(pyo3::exceptions::PyRuntimeError::new_err(
                                format!("{}: {}", type_name, py_err)
                            ))
                        })
                    }
                }
            } else {
                // For sync functions, run them in a thread pool to avoid blocking
                let result = tokio::task::spawn_blocking(move || {
                    Python::attach(|py| -> PyResult<Py<PyAny>> {
                        let func_bound = func.bind(py);
                        let args_bound = args.bind(py).cast::<PyTuple>()?;
                        let kwargs_bound = kwargs.bind(py).cast::<PyDict>()?;
                        let result = func_bound.call(args_bound, Some(kwargs_bound))?;
                        Ok(result.unbind())
                    })
                }).await;
                
                match result {
                    Ok(Ok(py_result)) => Ok(py_result),
                    Ok(Err(py_err)) => {
                        Python::attach(|py| {
                            let type_name = py_err.get_type(py).name().map(|s| s.to_string()).unwrap_or_else(|_| "UnknownError".to_string());
                            Err(pyo3::exceptions::PyRuntimeError::new_err(
                                format!("{}: {}", type_name, py_err)
                            ))
                        })
                    },
                    Err(join_err) => Err(pyo3::exceptions::PyRuntimeError::new_err(
                        format!("Task execution failed: {}", join_err)
                    )),
                }
            }
        })
    }
}

impl BackgroundTask {
    /// Check if a Python callable is async
    fn is_async_callable(py: Python<'_>, func: &Py<PyAny>) -> PyResult<bool> {
        let inspect = py.import("inspect")?;
        let is_coroutine_function = inspect.getattr("iscoroutinefunction")?;
        let result = is_coroutine_function.call1((func,))?;
        result.extract::<bool>()
    }
}

/// High-performance background tasks manager
#[pyclass]
pub struct BackgroundTasks {
    tasks: Arc<ParkingLotMutex<VecDeque<BackgroundTask>>>,
    max_concurrent: usize,
}

#[pymethods]
impl BackgroundTasks {
    #[new]
    #[pyo3(signature = (tasks = None, max_concurrent = None))]
    fn new(tasks: Option<&Bound<'_, PyList>>, max_concurrent: Option<usize>) -> PyResult<Self> {
        let task_queue = if let Some(tasks_list) = tasks {
            let mut queue = VecDeque::with_capacity(tasks_list.len());
            for task in tasks_list.iter() {
                let bg_task: BackgroundTask = task.extract()?;
                queue.push_back(bg_task);
            }
            queue
        } else {
            VecDeque::new()
        };

        Ok(Self {
            tasks: Arc::new(ParkingLotMutex::new(task_queue)),
            max_concurrent: max_concurrent.unwrap_or(10),
        })
    }

    /// Add a task to the background tasks queue
    #[pyo3(signature = (func, args = None, kwargs = None))]
    fn add_task(
        &self,
        py: Python<'_>,
        func: Py<PyAny>,
        args: Option<&Bound<'_, PyTuple>>,
        kwargs: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<()> {
        let task = BackgroundTask::new(py, func, args, kwargs)?;
        
        // Use ParkingLot mutex for thread-safe access without GIL issues
        let tasks = self.tasks.clone();
        py.detach(|| {
            let mut task_queue = tasks.lock();
            task_queue.push_back(task);
        });
        
        Ok(())
    }

    /// Execute all background tasks concurrently with controlled concurrency
    #[pyo3(signature = (continue_on_error = true))]
    fn __call__<'py>(
        &self, 
        py: Python<'py>,
        continue_on_error: bool
    ) -> PyResult<Bound<'py, PyAny>> {
        let tasks = self.tasks.clone();
        let max_concurrent = self.max_concurrent;

        future_into_py(py, async move {
            let task_queue = {
                let mut queue = tasks.lock();
                let mut extracted_tasks = Vec::with_capacity(queue.len());
                // Extract all tasks and clear the queue
                while let Some(task) = queue.pop_front() {
                    extracted_tasks.push(task);
                }
                // Queue is now empty after popping all tasks
                extracted_tasks
            };

            if task_queue.is_empty() {
                return Python::attach(|py| {
                    Ok(py.None())
                });
            }

            let mut errors: Vec<String> = Vec::new();

            // Separate sync and async tasks for different handling
            let mut sync_tasks = Vec::new();
            let mut async_coroutines = Vec::new();
            
            // Prepare tasks and create coroutines for async tasks
            for task in task_queue {
                if task.is_async {
                    // Create the coroutine immediately in the main context
                    let coroutine_result = Python::attach(|py| -> PyResult<Py<PyAny>> {
                        let func = task.func.clone_ref(py);
                        let args = task.args.clone_ref(py);
                        let kwargs = task.kwargs.clone_ref(py);
                        
                        let func_bound = func.bind(py);
                        let args_bound = args.bind(py).cast::<PyTuple>()?;
                        let kwargs_bound = kwargs.bind(py).cast::<PyDict>()?;
                        
                        // Create the coroutine
                        let coro = func_bound.call(args_bound, Some(kwargs_bound))?;
                        Ok(coro.unbind())
                    });
                    
                    match coroutine_result {
                        Ok(coro) => async_coroutines.push(coro),
                        Err(err) => {
                            errors.push(format!("Failed to create async task: {}", err));
                            if !continue_on_error {
                                break;
                            }
                        }
                    }
                } else {
                    sync_tasks.push(task);
                }
            }

            // Use semaphore to limit concurrent execution
            let semaphore = Arc::new(Semaphore::new(max_concurrent));
            let mut handles = Vec::new();

            // Execute sync tasks in background threads
            for task in sync_tasks {
                let permit = semaphore.clone().acquire_owned().await.unwrap();
                let handle = tokio::spawn(async move {
                    let _permit = permit;
                    
                    Python::attach(|py| -> Result<(), String> {
                        let func = task.func.clone_ref(py);
                        let args = task.args.clone_ref(py);
                        let kwargs = task.kwargs.clone_ref(py);
                        
                        let func_bound = func.bind(py);
                        let args_bound = args.bind(py).cast::<PyTuple>().map_err(|e| format!("Args error: {}", e))?;
                        let kwargs_bound = kwargs.bind(py).cast::<PyDict>().map_err(|e| format!("Kwargs error: {}", e))?;
                        
                        let _result = func_bound.call(args_bound, Some(kwargs_bound)).map_err(|e| format!("Call error: {}", e))?;
                        Ok(())
                    })
                });
                handles.push(handle);
            }

            // Execute async coroutines directly in the main event loop context  
            for coroutine in async_coroutines {
                let permit = semaphore.clone().acquire_owned().await.unwrap();
                
                // Convert coroutine to future and execute it
                let future_result = Python::attach(|py| {
                    let coro_bound = coroutine.bind(py);
                    pyo3_async_runtimes::tokio::into_future(coro_bound.clone())
                });

                match future_result {
                    Ok(future) => {
                        let async_handle = tokio::spawn(async move {
                            let _permit = permit;
                            match future.await {
                                Ok(_) => Ok(()),
                                Err(err) => Err(format!("Async task failed: {}", err)),
                            }
                        });
                        handles.push(async_handle);
                    }
                    Err(err) => {
                        errors.push(format!("Failed to convert coroutine to future: {}", err));
                        if !continue_on_error {
                            break;
                        }
                    }
                }
            }

            // Wait for all tasks to complete
            for handle in handles {
                match handle.await {
                    Ok(Ok(())) => {}, // Task completed successfully
                    Ok(Err(error_msg)) => {
                        errors.push(error_msg);
                        if !continue_on_error {
                            break;
                        }
                    }
                    Err(join_err) => {
                        let error_msg = format!("Task failed with join error: {}", join_err);
                        errors.push(error_msg);
                        if !continue_on_error {
                            break;
                        }
                    }
                }
            }

            Python::attach(|py| {
                if !errors.is_empty() {
                    // Print errors
                    for error in &errors {
                        let builtins = py.import("builtins")?;
                        let print = builtins.getattr("print")?;
                        print.call1((format!("Task failed with error: {}", error),))?;
                    }
                    
                    if !continue_on_error {
                        return Err(pyo3::exceptions::PyRuntimeError::new_err(
                            "One or more background tasks failed"
                        ));
                    }
                }
                Ok(py.None())
            })
        })
    }

    /// Run all background tasks concurrently (alias for __call__)
    #[pyo3(signature = (continue_on_error = true))]
    fn run_all<'py>(
        &self, 
        py: Python<'py>,
        continue_on_error: bool
    ) -> PyResult<Bound<'py, PyAny>> {
        self.__call__(py, continue_on_error)
    }

    /// Get the number of pending tasks
    fn task_count<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let tasks = self.tasks.clone();
        
        future_into_py(py, async move {
            let task_queue = tasks.lock();
            let count = task_queue.len();
            // Return the count as a regular integer - PyO3 will handle the conversion
            Ok(count)
        })
    }

    /// Clear all pending tasks
    fn clear<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let tasks = self.tasks.clone();
        
        future_into_py(py, async move {
            let mut task_queue = tasks.lock();
            task_queue.clear();
            Python::attach(|py| Ok(py.None()))
        })
    }
}

/// Register background task classes and functions with the Python module
pub fn register_background(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<BackgroundTask>()?;
    m.add_class::<BackgroundTasks>()?;
    Ok(())
}
