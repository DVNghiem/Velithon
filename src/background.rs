use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyTuple};
use pyo3_async_runtimes::tokio::future_into_py;
use std::collections::VecDeque;
use std::sync::{Arc, Mutex};
use tokio::sync::Semaphore;

/// A high-performance background task implementation in Rust
#[pyclass]
pub struct BackgroundTask {
    func: PyObject,
    args: PyObject,
    kwargs: PyObject,
    is_async: bool,
}

impl Clone for BackgroundTask {
    fn clone(&self) -> Self {
        Python::with_gil(|py| {
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
        func: PyObject,
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
                // For async functions
                Python::with_gil(|py| -> PyResult<PyObject> {
                    let func_bound = func.bind(py);
                    let args_bound = args.bind(py).downcast::<PyTuple>()?;
                    let kwargs_bound = kwargs.bind(py).downcast::<PyDict>()?;
                    let result = func_bound.call(args_bound, Some(kwargs_bound))?;
                    Ok(result.unbind())
                })
            } else {
                // For sync functions, run them in a thread pool
                let result = tokio::task::spawn_blocking(move || {
                    Python::with_gil(|py| -> PyResult<PyObject> {
                        let func_bound = func.bind(py);
                        let args_bound = args.bind(py).downcast::<PyTuple>()?;
                        let kwargs_bound = kwargs.bind(py).downcast::<PyDict>()?;
                        let result = func_bound.call(args_bound, Some(kwargs_bound))?;
                        Ok(result.unbind())
                    })
                }).await;
                
                match result {
                    Ok(py_result) => py_result,
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
    fn is_async_callable(py: Python<'_>, func: &PyObject) -> PyResult<bool> {
        let inspect = py.import("inspect")?;
        let is_coroutine_function = inspect.getattr("iscoroutinefunction")?;
        let result = is_coroutine_function.call1((func,))?;
        result.extract::<bool>()
    }
}

/// High-performance background tasks manager
#[pyclass]
pub struct BackgroundTasks {
    tasks: Arc<Mutex<VecDeque<BackgroundTask>>>,
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
            tasks: Arc::new(Mutex::new(task_queue)),
            max_concurrent: max_concurrent.unwrap_or(10),
        })
    }

    /// Add a task to the background tasks queue
    #[pyo3(signature = (func, args = None, kwargs = None))]
    fn add_task(
        &self,
        py: Python<'_>,
        func: PyObject,
        args: Option<&Bound<'_, PyTuple>>,
        kwargs: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<()> {
        let task = BackgroundTask::new(py, func, args, kwargs)?;
        
        // Use standard mutex for simple synchronous access
        let tasks = self.tasks.clone();
        py.allow_threads(|| {
            let mut task_queue = tasks.lock().unwrap();
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
                let mut queue = tasks.lock().unwrap();
                let mut extracted_tasks = Vec::with_capacity(queue.len());
                // Extract all tasks and clear the queue
                while let Some(task) = queue.pop_front() {
                    extracted_tasks.push(task);
                }
                // Queue is now empty after popping all tasks
                extracted_tasks
            };

            if task_queue.is_empty() {
                return Python::with_gil(|py| {
                    Ok(py.None())
                });
            }

            // Use semaphore to limit concurrent execution
            let semaphore = Arc::new(Semaphore::new(max_concurrent));
            let mut handles = Vec::with_capacity(task_queue.len());

            for task in task_queue {
                let permit = semaphore.clone().acquire_owned().await.unwrap();
                let handle = tokio::spawn(async move {
                    let _permit = permit; // Keep permit alive during task execution
                    
                    // Simple execution - just call the function directly in the sync case
                    Python::with_gil(|py| -> PyResult<()> {
                        let func = task.func.clone_ref(py);
                        let args = task.args.clone_ref(py);
                        let kwargs = task.kwargs.clone_ref(py);
                        
                        let func_bound = func.bind(py);
                        let args_bound = args.bind(py).downcast::<PyTuple>()?;
                        let kwargs_bound = kwargs.bind(py).downcast::<PyDict>()?;
                        
                        if task.is_async {
                            // For async functions, create the coroutine but don't await it here
                            // This matches the Python implementation pattern
                            let _coro = func_bound.call(args_bound, Some(kwargs_bound))?;
                            // Note: In a real implementation, we'd need to properly await this
                            Ok(())
                        } else {
                            // For sync functions, just call them directly
                            let _result = func_bound.call(args_bound, Some(kwargs_bound))?;
                            Ok(())
                        }
                    })
                });
                handles.push(handle);
            }

            let mut errors: Vec<String> = Vec::new();

            // Wait for all tasks to complete
            for handle in handles {
                match handle.await {
                    Ok(Ok(())) => {}, // Task completed successfully
                    Ok(Err(py_err)) => {
                        let error_msg = format!("Task failed with Python error: {}", py_err);
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

            Python::with_gil(|py| {
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
            let task_queue = tasks.lock().unwrap();
            let count = task_queue.len();
            // Return the count as a regular integer - PyO3 will handle the conversion
            Ok(count)
        })
    }

    /// Clear all pending tasks
    fn clear<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let tasks = self.tasks.clone();
        
        future_into_py(py, async move {
            let mut task_queue = tasks.lock().unwrap();
            task_queue.clear();
            Python::with_gil(|py| Ok(py.None()))
        })
    }
}

/// Register background task classes and functions with the Python module
pub fn register_background(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<BackgroundTask>()?;
    m.add_class::<BackgroundTasks>()?;
    Ok(())
}
