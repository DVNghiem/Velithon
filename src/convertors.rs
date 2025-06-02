use pyo3::prelude::*;
use pyo3::types::PyDict;
use regex::Regex;
use std::collections::HashSet;
use uuid::Uuid;

/// Base trait for all convertors
#[pyclass(subclass)]
#[derive(Clone)]
pub struct Convertor {
    #[pyo3(get)]
    pub regex: String,
}


#[pymethods]
impl Convertor {
    #[new]
    fn new(regex: String) -> Self {
        Self { regex }
    }

    /// Convert a value to the appropriate type
    fn convert(&self, _py: Python, _value: &str) -> PyResult<PyObject> {
        // raise not implemented error
        Err(pyo3::exceptions::PyNotImplementedError::new_err("Convertor.convert() must be implemented in subclasses"))
    }

    /// Convert a value to a string representation
    fn to_string(&self, _py: Python, _value: &str) -> PyResult<PyObject> {
        // raise not implemented error
        Err(pyo3::exceptions::PyNotImplementedError::new_err("Convertor.to_string() must be implemented in subclasses"))
    }
}
/// Individual convertor classes for Python compatibility

#[pyclass(extends = Convertor, name = "StringConvertor")]
pub struct StringConvertor;

#[pymethods]
impl StringConvertor {

    #[new]
    fn new() -> (Self, Convertor) {
        (
            StringConvertor {},
            Convertor {
                regex: "[^/]+".to_string(),
            },
        )
    }

    #[pyo3(signature = (value))]
    fn convert(&self, _py: Python, value: &str) -> PyResult<String> {
        Ok(value.to_string())
    }

    #[pyo3(signature = (value))]
    fn to_string(&self, _py: Python, value: &str) -> PyResult<String> {
        if value.contains('/') {
            return Err(pyo3::exceptions::PyAssertionError::new_err("May not contain path separators"));
        }
        if value.is_empty() {
            return Err(pyo3::exceptions::PyAssertionError::new_err("Must not be empty"));
        }
        Ok(value.to_string())
    }
}

#[pyclass(extends = Convertor, name = "PathConvertor")]
pub struct PathConvertor;
#[pymethods]
impl PathConvertor {
    #[new]
    fn new() -> (Self, Convertor) {
        (
            PathConvertor {},
            Convertor {
                regex: ".*".to_string(),
            },
        )
    }

    fn convert(&self, value: &str) -> PyResult<String> {
        Ok(value.to_string())
    }

    fn to_string(&self, value: &str) -> PyResult<String> {
        Ok(value.to_string())
    }
}

#[pyclass(extends = Convertor, name = "IntegerConvertor")]
pub struct IntegerConvertor;
#[pymethods]
impl IntegerConvertor {
    #[new]
    fn new() -> (Self, Convertor) {
        (
            IntegerConvertor {},
            Convertor {
                regex: "[0-9]+".to_string(),
            },
        )
    }

    fn convert(&self, value: &str) -> PyResult<i64> {
        value.parse::<i64>()
            .map_err(|_| pyo3::exceptions::PyValueError::new_err("Invalid integer"))
    }

    fn to_string(&self, value: i64) -> PyResult<String> {
        if value < 0 {
            return Err(pyo3::exceptions::PyAssertionError::new_err("Negative integers are not supported"));
        }
        Ok(value.to_string())
    }
}

#[pyclass(extends=Convertor, name = "FloatConvertor")]
pub struct FloatConvertor;

#[pymethods]
impl FloatConvertor {
    #[new]
    fn new() -> (Self, Convertor) {
        (
            FloatConvertor {},
            Convertor {
                regex: "[0-9]+(\\.[0-9]+)?".to_string(),
            },
        )
    }

    fn convert(&self, value: &str) -> PyResult<f64> {
        value.parse::<f64>()
            .map_err(|_| pyo3::exceptions::PyValueError::new_err("Invalid float"))
    }

    fn to_string(&self, value: f64) -> PyResult<String> {
        if value < 0.0 {
            return Err(pyo3::exceptions::PyAssertionError::new_err("Negative floats are not supported"));
        }
        if value.is_nan() {
            return Err(pyo3::exceptions::PyAssertionError::new_err("NaN values are not supported"));
        }
        if value.is_infinite() {
            return Err(pyo3::exceptions::PyAssertionError::new_err("Infinite values are not supported"));
        }
        
        // Format float similar to Python's ("%0.20f" % value).rstrip("0").rstrip(".")
        let formatted = format!("{:.20}", value);
        let trimmed = formatted.trim_end_matches('0').trim_end_matches('.');
        Ok(trimmed.to_string())
    }
}

#[pyclass(extends=Convertor, name = "UUIDConvertor")]
pub struct UUIDConvertor;

#[pymethods]
impl UUIDConvertor {
    #[new]
    fn new() -> (Self, Convertor) {
        (
            UUIDConvertor {},
            Convertor {
                regex: "[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}".to_string(),
            },
        )
    }

    fn convert(&self, value: &str) -> PyResult<String> {
        // Parse and validate UUID, then return as string
        let uuid = Uuid::parse_str(value)
            .map_err(|_| pyo3::exceptions::PyValueError::new_err("Invalid UUID"))?;
        Ok(uuid.to_string())
    }

    fn to_string(&self, value: &str) -> PyResult<String> {
        // Validate it's a proper UUID first
        let uuid = Uuid::parse_str(value)
            .map_err(|_| pyo3::exceptions::PyValueError::new_err("Invalid UUID"))?;
        Ok(uuid.to_string())
    }
}

/// Fast path compilation that leverages pre-compiled regex patterns
#[pyfunction]
fn compile_path(py: Python, path: &str, convertor_types: Bound<PyDict>) -> PyResult<(String, String, Py<PyDict>)> {

    let is_host = !path.starts_with('/');
    let mut path_regex = "^".to_string();
    let mut path_format = String::new();
    let mut duplicated_params: HashSet<String> = HashSet::new();
    let mut idx = 0;
    let param_convertors = PyDict::new(py);

    let param_regex = Regex::new(r"\{([a-zA-Z_][a-zA-Z0-9_]*)(:[a-zA-Z_][a-zA-Z0-9_]*)?\}").unwrap();
    for caps in param_regex.captures_iter(path) {
        let param_name = caps.get(1).unwrap().as_str();
        let convertor_name = caps.get(2).map_or("str", |m| m.as_str().trim_start_matches(':'));
        let convertor = convertor_types.get_item(convertor_name)?
            .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err(format!("Unknown convertor type: {}", convertor_name)))?;
        let regex = match convertor.extract::<Convertor>() {
            Ok(conv) => conv.regex.clone(),
            Err(_) => return Err(pyo3::exceptions::PyTypeError::new_err("Invalid convertor type")),
        };
        if idx < caps.get(0).unwrap().start() {
            path_regex.push_str(&regex::escape(&path[idx..caps.get(0).unwrap().start()]));
        }
        path_regex.push_str(&format!("(?P<{}>{})", param_name, regex));

        if idx < caps.get(0).unwrap().start() {
            path_format.push_str(&path[idx..caps.get(0).unwrap().start()]);
        }
        path_format.push_str(&format!("{{{}}}", param_name));

        if param_convertors.contains(param_name).unwrap_or(false) {
            duplicated_params.insert(param_name.to_string());
        }

        // Store the convertor in the dictionary
        param_convertors.set_item(param_name, convertor)?;

        if let Some(matched) = caps.get(0) {
            idx = matched.end();
        }
    }
    if duplicated_params.len() > 0 {
        return Err(pyo3::exceptions::PyValueError::new_err(format!(
            "Duplicate parameters found: {}",
            duplicated_params.into_iter().collect::<Vec<_>>().join(", ")
        )));
    }
    if is_host {
        // hostname = path[idx:].split(":")[0]
        let hostname = path[idx..].split(':').next().unwrap_or("");
        // path_regex += re.escape(hostname) + "$"
        path_regex.push_str(&regex::escape(hostname));
        path_regex.push_str("$");
    } else {
        if idx < path.len() {
            path_regex.push_str(&regex::escape(&path[idx..]));
        }
        path_regex.push_str("$");

        
    path_format.push_str(&path[idx..]);}

    Ok((path_regex, path_format, param_convertors.unbind()))
}

/// Register all convertor functions and classes with Python
pub fn register_convertors(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Register individual convertor classes
    m.add_class::<StringConvertor>()?;
    m.add_class::<PathConvertor>()?;
    m.add_class::<IntegerConvertor>()?;
    m.add_class::<FloatConvertor>()?;
    m.add_class::<UUIDConvertor>()?;
    m.add_class::<Convertor>()?;
    
    // Register utility functions
    m.add_function(wrap_pyfunction!(compile_path, m)?)?;
    
    Ok(())
}
