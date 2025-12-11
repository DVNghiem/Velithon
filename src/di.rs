use pyo3::prelude::*;
use pyo3::sync::PyOnceLock;
use pyo3::types::{PyDict, PySet, PyString, PyType, PyTuple};
use std::collections::HashMap;
use parking_lot::Mutex as ParkingLotMutex;
use std::sync::Arc;

// Global caches with parking_lot mutex for better performance
static SIGNATURE_CACHE: PyOnceLock<ParkingLotMutex<HashMap<String, Py<PyAny>>>> = PyOnceLock::new();
static PROVIDER_INSTANCES: PyOnceLock<Arc<ParkingLotMutex<HashMap<String, Py<PyAny>>>>> = PyOnceLock::new();

#[pyfunction(name = "di_cached_signature")]
fn cached_signature(py: Python, func: Bound<PyAny>) -> PyResult<Py<PyAny>> {
    let cache_mutex = SIGNATURE_CACHE.get_or_init(py, || ParkingLotMutex::new(HashMap::new()));
    let mut cache = cache_mutex.lock();

    let func_obj = func.unbind();
    let func_str = format!("{:?}", func_obj);

    if let Some(cached_func) = cache.get(&func_str) {
        return Ok(cached_func.clone_ref(py));
    }

    let inspect_module = PyModule::import(py, "inspect")?;
    let signature = inspect_module.getattr("signature")?.call1((func_obj,))?;
    cache.insert(func_str, signature.clone().unbind());
    Ok(signature.unbind())
}

#[pyclass]
pub struct Provide {
    #[pyo3(get)]
    service: Py<PyAny>,
}

impl Clone for Provide {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            service: self.service.clone_ref(py),
        })
    }
}

#[pymethods]
impl Provide {
    #[new]
    fn new(service: Py<PyAny>) -> Self {
        Self { service }
    }

    #[classmethod]
    fn __class_getitem__(_cls: &Bound<'_, PyType>, service: Py<PyAny>) -> PyResult<Self> {
        Ok(Self::new(service))
    }

    fn __repr__(&self, py: Python) -> PyResult<String> {
        Ok(format!("Provide({})", self.service.bind(py).repr()?))
    }
}

#[pyclass(subclass)]
pub struct Provider;

#[pymethods]
impl Provider {
    #[new]
    fn new() -> Self {
        Self {}
    }

    fn get(
        &self,
        _py: Python,
        _container: Option<Py<PyAny>>,
        _resolution_stack: Option<Py<PyAny>>,
    ) -> PyResult<Py<PyAny>> {
        Err(PyErr::new::<pyo3::exceptions::PyNotImplementedError, _>(
            "get method must be implemented by subclasses",
        ))
    }
}

#[pyclass(extends = Provider)]
pub struct SingletonProvider {
    cls: Py<PyAny>,
    kwargs: Py<PyAny>,
    lock_key: String,
}

#[pymethods]
impl SingletonProvider {
    #[new]
    #[pyo3(signature = (cls, **kwargs))]
    fn new(cls: Py<PyAny>, kwargs: Option<Bound<PyDict>>) -> PyResult<(Self, Provider)> {
        let kwargs_dict = match kwargs {
            Some(k) => k.unbind().into(),
            None => Python::attach(|py| PyDict::new(py).unbind().into()),
        };

        let lock_key = format!("{:?}", cls);

        Ok((
            Self {
                cls,
                kwargs: kwargs_dict,
                lock_key,
            },
            Provider::new(),
        ))
    }

    fn get(
        &self,
        py: Python,
        _container: Py<PyAny>,
        _resolution_stack: Option<Py<PyAny>>,
    ) -> PyResult<Py<PyAny>> {
        let instances_lock = 
            PROVIDER_INSTANCES.get_or_init(py, || Arc::new(ParkingLotMutex::new(HashMap::new())));

        // Check if we already have an instance
        {
            let instances = instances_lock.lock();
            if let Some(instance) = instances.get(&self.lock_key) {
                return Ok(instance.clone_ref(py));
            }
        } // Release lock before creating new instance

        // Create new instance if needed (using optimized kwargs handling)
        let instance = if self.kwargs.bind(py).len()? == 0 {
            // No kwargs - fast path
            self.cls.call0(py)?
        } else {
            // Has kwargs - unpack them
            let kwargs_dict = self.kwargs.bind(py).cast::<PyDict>()?;
            let empty_args = PyTuple::empty(py);
            self.cls.call(py, empty_args, Some(kwargs_dict))?
        };

        // Store the instance
        {
            let mut instances = instances_lock.lock();
            // Double-check in case another thread created it while we were creating ours
            if let Some(existing) = instances.get(&self.lock_key) {
                return Ok(existing.clone_ref(py));
            } else {
                instances.insert(self.lock_key.clone(), instance.clone_ref(py));
                return Ok(instance);
            }
        }
    }
}

#[pyclass(extends = Provider)]
pub struct FactoryProvider {
    cls: Py<PyAny>,
    kwargs: Py<PyAny>,
}

#[pymethods]
impl FactoryProvider {
    #[new]
    #[pyo3(signature = (cls, **kwargs))]
    fn new(py: Python, cls: Py<PyAny>, kwargs: Option<Bound<PyDict>>) -> PyResult<(Self, Provider)> {
        let kwargs_dict = match kwargs {
            Some(k) => k.unbind().into(),
            None => PyDict::new(py).unbind().into(),
        };

        Ok((
            Self {
                cls,
                kwargs: kwargs_dict,
            },
            Provider::new(),
        ))
    }

    fn get(
        &self,
        py: Python,
        container: Py<PyAny>,
        resolution_stack: Option<Py<PyAny>>,
    ) -> PyResult<Py<PyAny>> {
        let resolution_stack = match resolution_stack {
            Some(stack) => stack,
            None => PySet::empty(py)?.unbind().into(),
        };

        let stack_bound = resolution_stack.bind(py);
        let key_str = PyString::new(py, &format!("{:?}", self.cls));

        if stack_bound.contains(&key_str)? {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Circular dependency detected for {:?}",
                self.cls
            )));
        }

        stack_bound.call_method1("add", (&key_str,))?;

        let result = {
            create_instance(
                py,
                &self.cls,
                &self.kwargs,
                &container,
                Some(resolution_stack.clone_ref(py)),
            )?
        };

        let _ = stack_bound.call_method1("discard", (&key_str,));
        Ok(result)
    }
}

#[pyclass(extends = Provider)]
pub struct AsyncFactoryProvider {
    factory: Py<PyAny>,
    kwargs: Py<PyAny>,
    signature: Py<PyAny>,
}

#[pymethods]
impl AsyncFactoryProvider {
    #[new]
    #[pyo3(signature = (factory, **kwargs))]
    fn new(
        py: Python,
        factory: Py<PyAny>,
        kwargs: Option<Bound<PyDict>>,
    ) -> PyResult<(Self, Provider)> {
        let kwargs_dict = match kwargs {
            Some(k) => k.unbind().into(),
            None => PyDict::new(py).unbind().into(),
        };

        let signature = cached_signature(py, factory.bind(py).clone())?;

        Ok((
            Self {
                factory,
                kwargs: kwargs_dict,
                signature,
            },
            Provider::new(),
        ))
    }

    fn get(
        &self,
        py: Python,
        container: Py<PyAny>,
        resolution_stack: Option<Py<PyAny>>,
    ) -> PyResult<Py<PyAny>> {
        let resolution_stack = match resolution_stack {
            Some(stack) => stack,
            None => PySet::empty(py)?.unbind().into(),
        };

        let stack_bound = resolution_stack.bind(py);
        let key_str = PyString::new(py, &format!("{:?}", self.factory));

        if stack_bound.contains(&key_str)? {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Circular dependency detected for {:?}",
                self.factory
            )));
        }

        stack_bound.call_method1("add", (&key_str,))?;

        let result = {
            let deps = resolve_dependencies(
                py,
                &self.signature,
                &container,
                &self.kwargs,
                Some(resolution_stack.clone_ref(py)),
            )?;

            // Call the async factory function and return the result/coroutine
            let factory_bound = self.factory.bind(py);
            let deps_dict = deps.cast::<PyDict>()?;
            let result = factory_bound.call((), Some(deps_dict))?;

            // Return the result directly - if it's a coroutine, let the caller handle awaiting
            result.unbind()
        };

        let _ = stack_bound.call_method1("discard", (&key_str,));
        Ok(result)
    }
}

#[pyclass]
pub struct ServiceContainer;

#[pymethods]
impl ServiceContainer {
    #[new]
    fn new(_py: Python) -> PyResult<Self> {
        Ok(Self {})
    }

    fn resolve(
        &self,
        py: Python,
        provide: Py<PyAny>, // Changed from &Provide to Py<PyAny>
        container: Py<PyAny>,
        resolution_stack: Option<Py<PyAny>>,
    ) -> PyResult<Py<PyAny>> {
        // Extract the service from the Provide object
        let service = if let Ok(provide_obj) = provide.extract::<Py<Provide>>(py) {
            provide_obj.borrow(py).service.clone_ref(py)
        } else {
            // Assume it's already a service object
            provide
        };

        // Check if service is a Provider
        let service_bound = service.bind(py);
        if !service_bound.hasattr("get")? {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "No service registered for {:?}",
                service
            )));
        }

        // Call the provider's get method
        let get_method = service_bound.getattr("get")?;
        let result = get_method.call((container, resolution_stack), None)?;

        // Return the result directly - don't try to handle async here
        // The Python side will handle awaiting if needed
        Ok(result.unbind())
    }
}

fn create_instance(
    py: Python,
    cls: &Py<PyAny>,
    kwargs: &Py<PyAny>,
    container: &Py<PyAny>,
    resolution_stack: Option<Py<PyAny>>,
) -> PyResult<Py<PyAny>> {
    let signature = cached_signature(py, cls.bind(py).clone())?;
    let deps = resolve_dependencies(py, &signature, container, kwargs, resolution_stack)?;

    let cls_bound = cls.bind(py);
    let deps_dict = deps.cast::<PyDict>()?;
    let instance = cls_bound.call((), Some(deps_dict))?;
    Ok(instance.unbind())
}

fn resolve_dependencies<'py>(
    py: Python<'py>,
    signature: &Py<PyAny>,
    container: &Py<PyAny>,
    kwargs: &Py<PyAny>,
    resolution_stack: Option<Py<PyAny>>,
) -> PyResult<Bound<'py, PyDict>> {
    let deps = PyDict::new(py);
    let sig_bound = signature.bind(py);
    let parameters = sig_bound.getattr("parameters")?;
    let kwargs_bound = kwargs.bind(py);

    for item in parameters.getattr("items")?.call0()?.try_iter()? {
        let item = item?;
        let (name, param) = item.extract::<(String, Py<PyAny>)>()?;

        // Check if dependency is already provided in kwargs
        if kwargs_bound.contains(&name)? {
            let value = kwargs_bound.get_item(&name)?;

            // Check if the value is a provider that needs to be resolved
            if value.hasattr("get")? {
                // This looks like a provider, resolve it through the container
                let resolved_value = value.call_method1("get", (container, &resolution_stack))?;
                deps.set_item(&name, resolved_value)?;
            } else {
                // Use the raw value
                deps.set_item(&name, value)?;
            }
            continue;
        }

        // Try to resolve parameter
        if let Ok(dep) = resolve_param(py, &name, &param, container, &resolution_stack) {
            deps.set_item(&name, dep)?;
        }
    }

    Ok(deps)
}

fn resolve_param(
    py: Python,
    _name: &str,
    param: &Py<PyAny>,
    container: &Py<PyAny>,
    // scope: Option<&Py<PyAny>>,
    resolution_stack: &Option<Py<PyAny>>,
) -> PyResult<Py<PyAny>> {
    let param_bound = param.bind(py);

    // Check annotation metadata
    if param_bound.hasattr("annotation")? {
        let annotation = param_bound.getattr("annotation")?;
        if annotation.hasattr("__metadata__")? {
            let metadata = annotation.getattr("__metadata__")?;
            for item in metadata.try_iter()? {
                let item_obj = item?;
                // Check if it's a Provide instance by looking for the service attribute
                if item_obj.hasattr("service")? {
                    let container_bound = container.bind(py);
                    let resolve_method = container_bound.getattr("resolve")?;
                    let result = resolve_method.call((item_obj.clone(), resolution_stack), None)?;

                    // Handle async result
                    if result.hasattr("__await__")? {
                        let asyncio = PyModule::import(py, "asyncio")?;
                        let event_loop = asyncio.getattr("get_event_loop")?.call0()?;
                        let awaited_result =
                            event_loop.getattr("run_until_complete")?.call1((result,))?;
                        return Ok(awaited_result.unbind());
                    } else {
                        return Ok(result.unbind());
                    }
                }
            }
        }
    }

    // Check default value
    if param_bound.hasattr("default")? {
        let default = param_bound.getattr("default")?;
        if default.hasattr("service")? {
            let container_bound = container.bind(py);
            let resolve_method = container_bound.getattr("resolve")?;
            let result = resolve_method.call((default.clone(), resolution_stack), None)?;

            // Handle async result
            if result.hasattr("__await__")? {
                let asyncio = PyModule::import(py, "asyncio")?;
                let event_loop = asyncio.getattr("get_event_loop")?.call0()?;
                let awaited_result = event_loop.getattr("run_until_complete")?.call1((result,))?;
                return Ok(awaited_result.unbind());
            } else {
                return Ok(result.unbind());
            }
        }
    }

    Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
        "Cannot resolve parameter",
    ))
}

/// Register all DI functions and classes with Python
pub fn register_di(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Register DI classes
    m.add_class::<Provide>()?;
    m.add_class::<Provider>()?;
    m.add_class::<SingletonProvider>()?;
    m.add_class::<FactoryProvider>()?;
    m.add_class::<AsyncFactoryProvider>()?;
    m.add_class::<ServiceContainer>()?;

    // Register utility functions
    m.add_function(wrap_pyfunction!(cached_signature, m)?)?;

    Ok(())
}
