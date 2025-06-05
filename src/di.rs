use pyo3::prelude::*;
use pyo3::sync::GILOnceCell;
use pyo3::types::{PyDict, PySet, PyString, PyType};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

// Global caches
static SIGNATURE_CACHE: GILOnceCell<Mutex<HashMap<String, PyObject>>> = GILOnceCell::new();
static PROVIDER_INSTANCES: GILOnceCell<Arc<Mutex<HashMap<String, PyObject>>>> = GILOnceCell::new();

#[pyfunction(name = "di_cached_signature")]
fn cached_signature(py: Python, func: Bound<PyAny>) -> PyResult<PyObject> {
    let cache_mutex = SIGNATURE_CACHE.get_or_init(py, || Mutex::new(HashMap::new()));
    let mut cache = cache_mutex.lock().unwrap();

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
    service: PyObject,
}

impl Clone for Provide {
    fn clone(&self) -> Self {
        Python::with_gil(|py| Self {
            service: self.service.clone_ref(py),
        })
    }
}

#[pymethods]
impl Provide {
    #[new]
    fn new(service: PyObject) -> Self {
        Self { service }
    }

    #[classmethod]
    fn __class_getitem__(_cls: &Bound<'_, PyType>, service: PyObject) -> PyResult<Self> {
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
        _scope: Option<PyObject>,
        _resolution_stack: Option<PyObject>,
    ) -> PyResult<PyObject> {
        Err(PyErr::new::<pyo3::exceptions::PyNotImplementedError, _>(
            "get method must be implemented by subclasses",
        ))
    }
}

#[pyclass(extends = Provider)]
pub struct SingletonProvider {
    cls: PyObject,
    kwargs: PyObject,
    lock_key: String,
}

#[pymethods]
impl SingletonProvider {
    #[new]
    #[pyo3(signature = (cls, **kwargs))]
    fn new(cls: PyObject, kwargs: Option<Bound<PyDict>>) -> PyResult<(Self, Provider)> {
        let kwargs_dict = match kwargs {
            Some(k) => k.unbind().into(),
            None => Python::with_gil(|py| PyDict::new(py).unbind().into()),
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
        scope: Option<PyObject>,
        resolution_stack: Option<PyObject>,
    ) -> PyResult<PyObject> {
        let instances_lock = PROVIDER_INSTANCES.get_or_init(py, || {
            Arc::new(Mutex::new(HashMap::new()))
        });

        // Check if instance already exists
        {
            let instances = instances_lock.lock().unwrap();
            if let Some(instance) = instances.get(&self.lock_key) {
                return Ok(instance.clone_ref(py));
            }
        }

        // Create new instance with circular dependency detection
        let resolution_stack = match resolution_stack {
            Some(stack) => stack,
            None => PySet::empty(py)?.unbind().into(),
        };

        let stack_bound = resolution_stack.bind(py);
        let key_str = PyString::new(py, &self.lock_key);
        
        if stack_bound.contains(&key_str)? {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Circular dependency detected for {}", self.lock_key)
            ));
        }
        
        stack_bound.call_method1("add", (&key_str,))?;

        let result = {
            let mut instances = instances_lock.lock().unwrap();
            
            // Double-check after acquiring write lock
            if let Some(instance) = instances.get(&self.lock_key) {
                let _ = stack_bound.call_method1("discard", (&key_str,));
                return Ok(instance.clone_ref(py));
            }

            // Get container and create instance
            let container = get_container_from_scope(py, scope.as_ref())?;
            let instance = create_instance(py, &self.cls, &self.kwargs, &container, scope.as_ref(), Some(resolution_stack.clone_ref(py)))?;
            
            instances.insert(self.lock_key.clone(), instance.clone_ref(py));
            instance
        };

        let _ = stack_bound.call_method1("discard", (&key_str,));
        Ok(result)
    }
}

#[pyclass(extends = Provider)]
pub struct FactoryProvider {
    cls: PyObject,
    kwargs: PyObject,
}

#[pymethods]
impl FactoryProvider {
    #[new]
    #[pyo3(signature = (cls, **kwargs))]
    fn new(py: Python, cls: PyObject, kwargs: Option<Bound<PyDict>>) -> PyResult<(Self, Provider)> {
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
        scope: Option<PyObject>,
        resolution_stack: Option<PyObject>,
    ) -> PyResult<PyObject> {
        let resolution_stack = match resolution_stack {
            Some(stack) => stack,
            None => PySet::empty(py)?.unbind().into(),
        };

        let stack_bound = resolution_stack.bind(py);
        let key_str = PyString::new(py, &format!("{:?}", self.cls));
        
        if stack_bound.contains(&key_str)? {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Circular dependency detected for {:?}", self.cls)
            ));
        }
        
        stack_bound.call_method1("add", (&key_str,))?;

        let result = {
            let container = get_container_from_scope(py, scope.as_ref())?;
            create_instance(py, &self.cls, &self.kwargs, &container, scope.as_ref(), Some(resolution_stack.clone_ref(py)))?
        };

        let _ = stack_bound.call_method1("discard", (&key_str,));
        Ok(result)
    }
}

#[pyclass(extends = Provider)]
pub struct AsyncFactoryProvider {
    factory: PyObject,
    kwargs: PyObject,
    signature: PyObject,
}

#[pymethods]
impl AsyncFactoryProvider {
    #[new]
    #[pyo3(signature = (factory, **kwargs))]
    fn new(py: Python, factory: PyObject, kwargs: Option<Bound<PyDict>>) -> PyResult<(Self, Provider)> {
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
        scope: Option<PyObject>,
        resolution_stack: Option<PyObject>,
    ) -> PyResult<PyObject> {
        let resolution_stack = match resolution_stack {
            Some(stack) => stack,
            None => PySet::empty(py)?.unbind().into(),
        };

        let stack_bound = resolution_stack.bind(py);
        let key_str = PyString::new(py, &format!("{:?}", self.factory));
        
        if stack_bound.contains(&key_str)? {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Circular dependency detected for {:?}", self.factory)
            ));
        }
        
        stack_bound.call_method1("add", (&key_str,))?;

        let result = {
            let container = get_container_from_scope(py, scope.as_ref())?;
            let deps = resolve_dependencies(py, &self.signature, &container, scope.as_ref(), &self.kwargs, Some(resolution_stack.clone_ref(py)))?;
            
            // Call the async factory function and return the result/coroutine
            let factory_bound = self.factory.bind(py);
            let deps_dict = deps.downcast::<PyDict>()?;
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
        provide: PyObject,  // Changed from &Provide to PyObject
        scope: Option<PyObject>,
        resolution_stack: Option<PyObject>,
    ) -> PyResult<PyObject> {
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
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("No service registered for {:?}", service)
            ));
        }
        
        // Call the provider's get method
        let get_method = service_bound.getattr("get")?;
        let result = get_method.call((scope, resolution_stack), None)?;
        
        // Return the result directly - don't try to handle async here
        // The Python side will handle awaiting if needed
        Ok(result.unbind())
    }
}

// Helper functions

fn get_container_from_scope(py: Python, scope: Option<&PyObject>) -> PyResult<PyObject> {
    let scope = scope.ok_or_else(|| {
        PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            "Invalid scope or missing container in scope._di_context['velithon']"
        )
    })?;

    let scope_bound = scope.bind(py);
    
    if !scope_bound.hasattr("_di_context")? {
        return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            "Invalid scope or missing container in scope._di_context['velithon']"
        ));
    }
    
    let di_context = scope_bound.getattr("_di_context")?;
    
    if !di_context.contains("velithon")? {
        return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            "Invalid scope or missing container in scope._di_context['velithon']"
        ));
    }
    
    let velithon_context = di_context.get_item("velithon")?;
    let container = velithon_context.getattr("container")?;
    
    Ok(container.unbind())
}

fn create_instance(
    py: Python,
    cls: &PyObject,
    kwargs: &PyObject,
    container: &PyObject,
    scope: Option<&PyObject>,
    resolution_stack: Option<PyObject>,
) -> PyResult<PyObject> {
    let signature = cached_signature(py, cls.bind(py).clone())?;
    let deps = resolve_dependencies(py, &signature, container, scope, kwargs, resolution_stack)?;
    
    let cls_bound = cls.bind(py);
    let deps_dict = deps.downcast::<PyDict>()?;
    let instance = cls_bound.call((), Some(deps_dict))?;
    Ok(instance.unbind())
}

fn resolve_dependencies<'py>(
    py: Python<'py>,
    signature: &PyObject,
    container: &PyObject,
    scope: Option<&PyObject>,
    kwargs: &PyObject,
    resolution_stack: Option<PyObject>,
) -> PyResult<Bound<'py, PyDict>> {
    let deps = PyDict::new(py);
    let sig_bound = signature.bind(py);
    let parameters = sig_bound.getattr("parameters")?;
    let kwargs_bound = kwargs.bind(py);
    
    for item in parameters.getattr("items")?.call0()?.try_iter()? {
        let item = item?;
        let (name, param) = item.extract::<(String, PyObject)>()?;
        
        // Check if dependency is already provided in kwargs
        if kwargs_bound.contains(&name)? {
            let value = kwargs_bound.get_item(&name)?;
            
            // Check if the value is a provider that needs to be resolved
            if value.hasattr("get")? {
                // This looks like a provider, resolve it through the container
                let resolved_value = value.call_method1("get", (scope, &resolution_stack))?;
                deps.set_item(&name, resolved_value)?;
            } else {
                // Use the raw value
                deps.set_item(&name, value)?;
            }
            continue;
        }
        
        // Try to resolve parameter
        if let Ok(dep) = resolve_param(py, &name, &param, container, scope, &resolution_stack) {
            deps.set_item(&name, dep)?;
        }
    }
    
    Ok(deps)
}

fn resolve_param(
    py: Python,
    _name: &str,
    param: &PyObject,
    container: &PyObject,
    scope: Option<&PyObject>,
    resolution_stack: &Option<PyObject>,
) -> PyResult<PyObject> {
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
                    let result = resolve_method.call((item_obj.clone(), scope, resolution_stack), None)?;
                    
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
        }
    }
    
    // Check default value
    if param_bound.hasattr("default")? {
        let default = param_bound.getattr("default")?;
        if default.hasattr("service")? {
            let container_bound = container.bind(py);
            let resolve_method = container_bound.getattr("resolve")?;
            let result = resolve_method.call((default.clone(), scope, resolution_stack), None)?;
            
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
        "Cannot resolve parameter"
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
