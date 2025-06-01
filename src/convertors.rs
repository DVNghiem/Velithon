use pyo3::prelude::*;
use pyo3::types::PyDict;
use regex::Regex;
use std::sync::OnceLock;
use uuid::Uuid;

/// Cached regex patterns for better performance
static STRING_REGEX: OnceLock<Regex> = OnceLock::new();
static PATH_REGEX: OnceLock<Regex> = OnceLock::new();
static INT_REGEX: OnceLock<Regex> = OnceLock::new();
static FLOAT_REGEX: OnceLock<Regex> = OnceLock::new();
static UUID_REGEX: OnceLock<Regex> = OnceLock::new();

/// Initialize regex patterns
fn init_regex() {
    STRING_REGEX.get_or_init(|| Regex::new(r"[^/]+").unwrap());
    PATH_REGEX.get_or_init(|| Regex::new(r".*").unwrap());
    INT_REGEX.get_or_init(|| Regex::new(r"[0-9]+").unwrap());
    FLOAT_REGEX.get_or_init(|| Regex::new(r"[0-9]+(\.[0-9]+)?").unwrap());
    UUID_REGEX.get_or_init(|| Regex::new(r"[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}").unwrap());
}

/// Base trait for all convertors
#[pyclass]
#[derive(Clone)]
pub struct Convertor {
    #[pyo3(get)]
    pub regex: String,
    pub convertor_type: ConvertorType,
}

#[derive(Clone)]
pub enum ConvertorType {
    String,
    Path,
    Integer,
    Float,
    UUID,
}

#[pymethods]
impl Convertor {
    /// Convert a string value to the appropriate type
    #[pyo3(signature = (value))]
    fn convert(&self, value: &str) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            match self.convertor_type {
                ConvertorType::String => {
                    let result = self.convert_string(value)?;
                    Ok(result.into_pyobject(py)?.into_any().unbind())
                },
                ConvertorType::Path => {
                    let result = self.convert_path(value)?;
                    Ok(result.into_pyobject(py)?.into_any().unbind())
                },
                ConvertorType::Integer => {
                    let result = self.convert_integer(value)?;
                    Ok(result.into_pyobject(py)?.into_any().unbind())
                },
                ConvertorType::Float => {
                    let result = self.convert_float(value)?;
                    Ok(result.into_pyobject(py)?.into_any().unbind())
                },
                ConvertorType::UUID => {
                    let result = self.convert_uuid(value)?;
                    Ok(result.into_pyobject(py)?.into_any().unbind())
                },
            }
        })
    }

    /// Convert a value back to string representation
    #[pyo3(signature = (value))]
    fn to_string(&self, value: PyObject) -> PyResult<String> {
        Python::with_gil(|py| {
            let any_value = value.bind(py);
            match self.convertor_type {
                ConvertorType::String => {
                    let str_val: String = any_value.extract()?;
                    self.string_to_string(&str_val)
                },
                ConvertorType::Path => {
                    let str_val: String = any_value.extract()?;
                    Ok(str_val)
                },
                ConvertorType::Integer => {
                    let int_val: i64 = any_value.extract()?;
                    self.integer_to_string(int_val)
                },
                ConvertorType::Float => {
                    let float_val: f64 = any_value.extract()?;
                    self.float_to_string(float_val)
                },
                ConvertorType::UUID => {
                    let uuid_str: String = any_value.extract()?;
                    Ok(uuid_str)
                },
            }
        })
    }
}

impl Convertor {
    pub fn new_string() -> Self {
        Self {
            regex: "[^/]+".to_string(),
            convertor_type: ConvertorType::String,
        }
    }

    pub fn new_path() -> Self {
        Self {
            regex: ".*".to_string(),
            convertor_type: ConvertorType::Path,
        }
    }

    pub fn new_integer() -> Self {
        Self {
            regex: "[0-9]+".to_string(),
            convertor_type: ConvertorType::Integer,
        }
    }

    pub fn new_float() -> Self {
        Self {
            regex: r"[0-9]+(\.[0-9]+)?".to_string(),
            convertor_type: ConvertorType::Float,
        }
    }

    pub fn new_uuid() -> Self {
        Self {
            regex: "[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}".to_string(),
            convertor_type: ConvertorType::UUID,
        }
    }

    fn convert_string(&self, value: &str) -> PyResult<String> {
        Ok(value.to_string())
    }

    fn convert_path(&self, value: &str) -> PyResult<String> {
        Ok(value.to_string())
    }

    fn convert_integer(&self, value: &str) -> PyResult<i64> {
        value.parse::<i64>()
            .map_err(|_| pyo3::exceptions::PyValueError::new_err("Invalid integer"))
    }

    fn convert_float(&self, value: &str) -> PyResult<f64> {
        value.parse::<f64>()
            .map_err(|_| pyo3::exceptions::PyValueError::new_err("Invalid float"))
    }

    fn convert_uuid(&self, value: &str) -> PyResult<String> {
        // Parse and validate UUID, then return as string
        let uuid = Uuid::parse_str(value)
            .map_err(|_| pyo3::exceptions::PyValueError::new_err("Invalid UUID"))?;
        Ok(uuid.to_string())
    }

    fn string_to_string(&self, value: &str) -> PyResult<String> {
        if value.contains('/') {
            return Err(pyo3::exceptions::PyAssertionError::new_err("May not contain path separators"));
        }
        if value.is_empty() {
            return Err(pyo3::exceptions::PyAssertionError::new_err("Must not be empty"));
        }
        Ok(value.to_string())
    }

    fn integer_to_string(&self, value: i64) -> PyResult<String> {
        if value < 0 {
            return Err(pyo3::exceptions::PyAssertionError::new_err("Negative integers are not supported"));
        }
        Ok(value.to_string())
    }

    fn float_to_string(&self, value: f64) -> PyResult<String> {
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

/// Individual convertor classes for Python compatibility

#[pyclass(name = "StringConvertor")]
pub struct StringConvertor {
    #[pyo3(get)]
    regex: String,
}

#[pymethods]
impl StringConvertor {
    #[new]
    fn new() -> Self {
        Self {
            regex: "[^/]+".to_string(),
        }
    }

    fn convert(&self, value: &str) -> PyResult<String> {
        Ok(value.to_string())
    }

    fn to_string(&self, value: &str) -> PyResult<String> {
        if value.contains('/') {
            return Err(pyo3::exceptions::PyAssertionError::new_err("May not contain path separators"));
        }
        if value.is_empty() {
            return Err(pyo3::exceptions::PyAssertionError::new_err("Must not be empty"));
        }
        Ok(value.to_string())
    }
}

#[pyclass(name = "PathConvertor")]
pub struct PathConvertor {
    #[pyo3(get)]
    regex: String,
}

#[pymethods]
impl PathConvertor {
    #[new]
    fn new() -> Self {
        Self {
            regex: ".*".to_string(),
        }
    }

    fn convert(&self, value: &str) -> PyResult<String> {
        Ok(value.to_string())
    }

    fn to_string(&self, value: &str) -> PyResult<String> {
        Ok(value.to_string())
    }
}

#[pyclass(name = "IntegerConvertor")]
pub struct IntegerConvertor {
    #[pyo3(get)]
    regex: String,
}

#[pymethods]
impl IntegerConvertor {
    #[new]
    fn new() -> Self {
        Self {
            regex: "[0-9]+".to_string(),
        }
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

#[pyclass(name = "FloatConvertor")]
pub struct FloatConvertor {
    #[pyo3(get)]
    regex: String,
}

#[pymethods]
impl FloatConvertor {
    #[new]
    fn new() -> Self {
        Self {
            regex: r"[0-9]+(\.[0-9]+)?".to_string(),
        }
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

#[pyclass(name = "UUIDConvertor")]
pub struct UUIDConvertor {
    #[pyo3(get)]
    regex: String,
}

#[pymethods]
impl UUIDConvertor {
    #[new]
    fn new() -> Self {
        Self {
            regex: "[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}".to_string(),
        }
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

/// Fast convertor registry
#[pyfunction]
fn get_convertor_types() -> PyResult<PyObject> {
    Python::with_gil(|py| {
        let dict = PyDict::new(py);
        dict.set_item("str", Py::new(py, StringConvertor::new())?)?;
        dict.set_item("path", Py::new(py, PathConvertor::new())?)?;
        dict.set_item("int", Py::new(py, IntegerConvertor::new())?)?;
        dict.set_item("float", Py::new(py, FloatConvertor::new())?)?;
        dict.set_item("uuid", Py::new(py, UUIDConvertor::new())?)?;
        Ok(dict.into())
    })
}

/// Register a new convertor type
#[pyfunction]
fn register_url_convertor(_key: String, convertor: PyObject) -> PyResult<()> {
    // This would need to be implemented with a global registry
    // For now, we'll just validate the input
    Python::with_gil(|py| {
        let _conv = convertor.bind(py);
        // In a full implementation, we'd store this in a global HashMap
        Ok(())
    })
}

/// Fast path compilation that leverages pre-compiled regex patterns
#[pyfunction]
fn compile_path_fast(path: &str) -> PyResult<(String, Vec<String>)> {
    init_regex();
    
    let mut regex_pattern = String::new();
    let mut param_names = Vec::new();
    let mut chars = path.chars().peekable();
    
    while let Some(ch) = chars.next() {
        if ch == '{' {
            // Parse parameter
            let mut param = String::new();
            let mut param_type = "str".to_string();
            
            while let Some(ch) = chars.next() {
                if ch == '}' {
                    break;
                } else if ch == ':' {
                    param_type = param.clone();
                    param.clear();
                } else {
                    param.push(ch);
                }
            }
            
            if param.is_empty() {
                param = param_type.clone();
                param_type = "str".to_string();
            }
            
            param_names.push(param);
            
            // Get regex for the parameter type
            let type_regex = match param_type.as_str() {
                "str" => STRING_REGEX.get().unwrap().as_str(),
                "path" => PATH_REGEX.get().unwrap().as_str(),
                "int" => INT_REGEX.get().unwrap().as_str(),
                "float" => FLOAT_REGEX.get().unwrap().as_str(),
                "uuid" => UUID_REGEX.get().unwrap().as_str(),
                _ => "[^/]+", // default to string
            };
            
            regex_pattern.push('(');
            regex_pattern.push_str(type_regex);
            regex_pattern.push(')');
        } else {
            // Escape special regex characters
            match ch {
                '.' | '^' | '$' | '*' | '+' | '?' | '(' | ')' | '[' | ']' | '|' | '\\' => {
                    regex_pattern.push('\\');
                    regex_pattern.push(ch);
                }
                _ => regex_pattern.push(ch),
            }
        }
    }
    
    // Ensure exact match
    let mut final_pattern = String::with_capacity(regex_pattern.len() + 2);
    final_pattern.push('^');
    final_pattern.push_str(&regex_pattern);
    final_pattern.push('$');
    
    Ok((final_pattern, param_names))
}

/// Validate regex pattern for performance
#[pyfunction]
fn validate_regex_pattern(pattern: &str) -> PyResult<bool> {
    match Regex::new(pattern) {
        Ok(_) => Ok(true),
        Err(_) => Ok(false),
    }
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
    m.add_function(wrap_pyfunction!(get_convertor_types, m)?)?;
    m.add_function(wrap_pyfunction!(register_url_convertor, m)?)?;
    m.add_function(wrap_pyfunction!(compile_path_fast, m)?)?;
    m.add_function(wrap_pyfunction!(validate_regex_pattern, m)?)?;
    
    Ok(())
}
