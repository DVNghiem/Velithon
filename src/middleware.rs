use pyo3::prelude::*;
use pyo3::types::PyAny;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Instant;
use parking_lot::Mutex;

use crate::logging::{get_logger, LogLevel};

#[pyclass]
pub struct RustLoggingMiddleware {
    app: Py<PyAny>,
    logger: Arc<Mutex<crate::logging::Logger>>,
}

#[pymethods]
impl RustLoggingMiddleware {
    #[new]
    pub fn new(app: Py<PyAny>) -> PyResult<Self> {
        let logger = get_logger();

        Ok(Self {
            app,
            logger,
        })
    }    pub fn __call__<'py>(
        &self,
        py: Python<'py>,
        scope: Py<PyAny>,
        protocol: Py<PyAny>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let logger = self.logger.clone();
        let app = self.app.clone_ref(py);
        
        // Create coroutine for the middleware logic
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            // Ultra-fast path: Check if logging is enabled to avoid all overhead
            let should_log = {
                let logger_guard = logger.lock();
                logger_guard.is_enabled(&LogLevel::Info)
            };

            if !should_log {
                // Logging disabled - direct passthrough with zero overhead
                return call_app_async(app, scope, protocol).await;
            }

            // Minimal logging path - only measure time and get essential info
            let start_time = Instant::now();
            
            // Call the app first
            let result = call_app_async(app, scope, protocol).await;
            
            // Quick timing calculation
            let duration_ms = start_time.elapsed().as_secs_f64() * 1000.0;
            
            // Log minimal info without heavy extraction
            log_minimal_request(logger, duration_ms, result.is_err());

            result
        })
    }
}

// Helper function to call the app asynchronously
async fn call_app_async(
    app: Py<PyAny>,
    scope: Py<PyAny>,
    protocol: Py<PyAny>,
) -> PyResult<()> {
    // Call the app and get the coroutine
    let coroutine = Python::with_gil(|py| {
        app.call1(py, (scope.bind(py), protocol.bind(py)))
    })?;
    
    // Await the coroutine
    let _result = Python::with_gil(|py| {
        let coro_bound = coroutine.bind(py);
        pyo3_async_runtimes::tokio::into_future(coro_bound.clone())
    })?
    .await?;
    
    Ok(())
}

// Minimal logging function - only log essential info
fn log_minimal_request(
    logger: Arc<Mutex<crate::logging::Logger>>,
    duration_ms: f64,
    had_error: bool,
) {
    let mut extra = HashMap::new();
    extra.insert("duration_ms".to_string(), format!("{:.2}", duration_ms));

    let log_message = "Request processed".to_string();
    
    // Log without holding the GIL
    let logger_guard = logger.lock();
    if had_error {
        logger_guard.log_with_extra(
            LogLevel::Error,
            log_message,
            "velithon.middleware.logging".to_string(),
            0,
            extra,
        );
    } else {
        logger_guard.log_with_extra(
            LogLevel::Info,
            log_message,
            "velithon.middleware.logging".to_string(),
            0,
            extra,
        );
    }
}

#[pyclass]
pub struct RustMiddlewareOptimizer {
    _middleware_cache: std::collections::HashMap<String, Py<PyAny>>,
}

#[pymethods]
impl RustMiddlewareOptimizer {
    #[new]
    pub fn new() -> Self {
        Self {
            _middleware_cache: std::collections::HashMap::new(),
        }
    }

    /// Optimize middleware stack for better performance
    pub fn optimize_middleware_stack(&self, py: Python, middlewares: Vec<Py<PyAny>>) -> PyResult<Vec<Py<PyAny>>> {
        if middlewares.is_empty() {
            return Ok(Vec::new());
        }

        // Categorize middlewares by priority
        let mut high_priority = Vec::new();
        let mut normal_priority = Vec::new();
        let mut low_priority = Vec::new();

        // Remove duplicates and categorize
        let mut seen = std::collections::HashSet::new();

        for middleware in middlewares {
            let middleware_id = middleware.as_ptr() as usize;
            if seen.contains(&middleware_id) {
                continue; // Skip duplicates
            }
            seen.insert(middleware_id);

            // Get middleware class name for categorization
            let middleware_name = middleware
                .bind(py)
                .getattr("__class__")?
                .getattr("__name__")?
                .to_string()
                .to_lowercase();

            // Categorize by middleware type
            if middleware_name.contains("security") 
                || middleware_name.contains("auth") 
                || middleware_name.contains("cors") {
                high_priority.push(middleware);
            } else if middleware_name.contains("log") 
                || middleware_name.contains("compression") 
                || middleware_name.contains("cache") {
                low_priority.push(middleware);
            } else {
                normal_priority.push(middleware);
            }
        }

        // Return optimized middleware stack with priority ordering
        let mut result = high_priority;
        result.extend(normal_priority);
        result.extend(low_priority);
        
        Ok(result)
    }
}

/// Register middleware-related functions and classes with Python
pub fn register_middleware(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustLoggingMiddleware>()?;
    m.add_class::<RustMiddlewareOptimizer>()?;
    Ok(())
}