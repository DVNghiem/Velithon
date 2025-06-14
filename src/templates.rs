use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::{Arc, RwLock};
use handlebars::{Handlebars, RenderError as HandlebarsError};
use serde_json::{Value, Map};

#[derive(Debug)]
pub enum TemplateError {
    RenderError(String),
    IoError(String),
    JsonError(String),
}

impl From<HandlebarsError> for TemplateError {
    fn from(err: HandlebarsError) -> Self {
        TemplateError::RenderError(err.to_string())
    }
}

impl From<std::io::Error> for TemplateError {
    fn from(err: std::io::Error) -> Self {
        TemplateError::IoError(err.to_string())
    }
}

impl From<serde_json::Error> for TemplateError {
    fn from(err: serde_json::Error) -> Self {
        TemplateError::JsonError(err.to_string())
    }
}

/// High-performance template engine with caching and security features
#[pyclass(name = "_TemplateEngine")]
pub struct TemplateEngine {
    handlebars: Arc<RwLock<Handlebars<'static>>>,
    template_dir: PathBuf,
    auto_reload: bool,
}

#[pymethods]
impl TemplateEngine {
    #[new]
    pub fn new(
        template_dir: &str,
        auto_reload: bool,
        _cache_enabled: bool,
        strict_mode: bool,
    ) -> PyResult<Self> {
        let template_path = PathBuf::from(template_dir);
        
        if !template_path.exists() {
            return Err(PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(
                format!("Template directory not found: {}", template_dir)
            ));
        }

        let mut handlebars = Handlebars::new();
        
        // Configure handlebars for security and performance
        handlebars.set_strict_mode(strict_mode);
        handlebars.set_dev_mode(auto_reload);
        
        // Register built-in helpers
        Self::register_helpers(&mut handlebars);
        
        Ok(TemplateEngine {
            handlebars: Arc::new(RwLock::new(handlebars)),
            template_dir: template_path,
            auto_reload,
        })
    }

    /// Render a template with context data
    pub fn render(&self, template_name: &str, context: Option<&Bound<'_, PyDict>>) -> PyResult<String> {
        // Security check: prevent path traversal
        if self.is_path_traversal_attempt(template_name) {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Path traversal attempt detected: {}", template_name)
            ));
        }

        // Check if template is already registered (from string or file)
        if !self.is_template_registered(template_name) {
            let template_path = self.template_dir.join(template_name);
            
            // Check if template file exists
            if !template_path.exists() {
                return Err(PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(
                    format!("Template not found: {}", template_name)
                ));
            }
            
            // Load template from file
            self.load_template(template_name)?;
        } else if self.auto_reload {
            // If auto-reload is enabled and template is file-based, reload it
            let template_path = self.template_dir.join(template_name);
            if template_path.exists() {
                self.load_template(template_name)?;
            }
        }

        // Convert Python context to JSON
        let json_context = match context {
            Some(ctx) => self.python_dict_to_json(ctx)?,
            None => Value::Object(Map::new()),
        };

        // Render template
        let handlebars = self.handlebars.read().unwrap();
        match handlebars.render(template_name, &json_context) {
            Ok(rendered) => Ok(rendered),
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Template render error: {}", e)
            )),
        }
    }

    /// Load and register a template
    pub fn load_template(&self, template_name: &str) -> PyResult<()> {
        let template_path = self.template_dir.join(template_name);
        
        let template_content = std::fs::read_to_string(&template_path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

        let mut handlebars = self.handlebars.write().unwrap();
        handlebars.register_template_string(template_name, template_content)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PySyntaxError, _>(
                format!("Template syntax error in {}: {}", template_name, e)
            ))?;

        Ok(())
    }

    /// Load all templates from the template directory
    pub fn load_templates(&self) -> PyResult<Vec<String>> {
        let mut loaded_templates = Vec::new();
        
        fn load_recursive(
            engine: &TemplateEngine,
            dir: &Path,
            base_dir: &Path,
            loaded: &mut Vec<String>,
        ) -> PyResult<()> {
            for entry in std::fs::read_dir(dir)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?
            {
                let entry = entry
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
                let path = entry.path();
                
                if path.is_dir() {
                    load_recursive(engine, &path, base_dir, loaded)?;
                } else if let Some(ext) = path.extension() {
                    if ext == "html" || ext == "hbs" || ext == "handlebars" {
                        let relative_path = path.strip_prefix(base_dir)
                            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
                        let template_name = relative_path.to_string_lossy().to_string();
                        
                        // Try to load template, but don't fail if it has syntax errors
                        match engine.load_template(&template_name) {
                            Ok(_) => loaded.push(template_name),
                            Err(_) => {
                                // Log error but continue with other templates
                                eprintln!("Warning: Failed to load template '{}' due to syntax errors", template_name);
                            }
                        }
                    }
                }
            }
            Ok(())
        }

        load_recursive(self, &self.template_dir, &self.template_dir, &mut loaded_templates)?;
        Ok(loaded_templates)
    }

    /// Register a template from string content
    pub fn register_template(&self, name: &str, content: &str) -> PyResult<()> {
        let mut handlebars = self.handlebars.write().unwrap();
        handlebars.register_template_string(name, content)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PySyntaxError, _>(
                format!("Template syntax error: {}", e)
            ))?;
        Ok(())
    }

    /// Clear all registered templates
    pub fn clear_templates(&self) -> PyResult<()> {
        let mut handlebars = self.handlebars.write().unwrap();
        handlebars.clear_templates();
        Ok(())
    }

    /// Get list of registered template names
    pub fn get_template_names(&self) -> Vec<String> {
        let handlebars = self.handlebars.read().unwrap();
        handlebars.get_templates().keys().cloned().collect()
    }

    /// Check if template is registered
    pub fn is_template_registered(&self, name: &str) -> bool {
        let handlebars = self.handlebars.read().unwrap();
        handlebars.get_template(name).is_some()
    }

    /// Get template directory path
    pub fn get_template_dir(&self) -> String {
        self.template_dir.to_string_lossy().to_string()
    }

    /// Enable or disable strict mode
    pub fn set_strict_mode(&self, strict: bool) -> PyResult<()> {
        let mut handlebars = self.handlebars.write().unwrap();
        handlebars.set_strict_mode(strict);
        Ok(())
    }
}

impl TemplateEngine {
    /// Register built-in helpers for common template operations
    fn register_helpers(handlebars: &mut Handlebars<'static>) {
        use handlebars::{Context, Helper, HelperResult, Output, RenderContext};
        
        // String manipulation helpers
        handlebars.register_helper("upper", Box::new(|h: &Helper, _: &Handlebars, _: &Context, _: &mut RenderContext, out: &mut dyn Output| -> HelperResult {
            let param = h.param(0).and_then(|v| v.value().as_str())
                .ok_or_else(|| std::io::Error::new(std::io::ErrorKind::InvalidInput, "upper requires a string"))?;
            
            out.write(&param.to_uppercase())?;
            Ok(())
        }));

        handlebars.register_helper("lower", Box::new(|h: &Helper, _: &Handlebars, _: &Context, _: &mut RenderContext, out: &mut dyn Output| -> HelperResult {
            let param = h.param(0).and_then(|v| v.value().as_str())
                .ok_or_else(|| std::io::Error::new(std::io::ErrorKind::InvalidInput, "lower requires a string"))?;
            
            out.write(&param.to_lowercase())?;
            Ok(())
        }));

        // Length helper
        handlebars.register_helper("len", Box::new(|h: &Helper, _: &Handlebars, _: &Context, _: &mut RenderContext, out: &mut dyn Output| -> HelperResult {
            let param = h.param(0).ok_or_else(|| std::io::Error::new(std::io::ErrorKind::InvalidInput, "len requires a parameter"))?;
            
            let length = match param.value() {
                Value::Array(arr) => arr.len(),
                Value::Object(obj) => obj.len(),
                Value::String(s) => s.len(),
                _ => 0,
            };
            
            out.write(&length.to_string())?;
            Ok(())
        }));
    }

    /// Convert Python dictionary to JSON Value
    fn python_dict_to_json(&self, py_dict: &Bound<'_, PyDict>) -> PyResult<Value> {
        let mut map = Map::new();
        
        for (key, value) in py_dict.iter() {
            let key_str = key.str()?.to_string();
            let json_value = self.python_to_json_value(value)?;
            map.insert(key_str, json_value);
        }
        
        Ok(Value::Object(map))
    }

    /// Convert Python value to JSON Value
    fn python_to_json_value(&self, py_value: Bound<'_, PyAny>) -> PyResult<Value> {
        if py_value.is_none() {
            Ok(Value::Null)
        } else if let Ok(b) = py_value.extract::<bool>() {
            Ok(Value::Bool(b))
        } else if let Ok(i) = py_value.extract::<i64>() {
            Ok(Value::Number(serde_json::Number::from(i)))
        } else if let Ok(f) = py_value.extract::<f64>() {
            if let Some(n) = serde_json::Number::from_f64(f) {
                Ok(Value::Number(n))
            } else {
                Ok(Value::Null)
            }
        } else if let Ok(s) = py_value.extract::<String>() {
            Ok(Value::String(s))
        } else if let Ok(list) = py_value.downcast::<pyo3::types::PyList>() {
            let mut arr = Vec::new();
            for item in list.iter() {
                arr.push(self.python_to_json_value(item)?);
            }
            Ok(Value::Array(arr))
        } else if let Ok(dict) = py_value.downcast::<PyDict>() {
            self.python_dict_to_json(dict)
        } else {
            // Fallback: convert to string
            Ok(Value::String(py_value.str()?.to_string()))
        }
    }

    /// Check for path traversal attempts
    fn is_path_traversal_attempt(&self, template_name: &str) -> bool {
        template_name.contains("..") || 
        template_name.starts_with('/') ||
        template_name.contains("\\..") ||
        template_name.starts_with('\\')
    }
}

/// Template response for convenient HTTP responses
#[pyclass(name = "_TemplateResponse")]
pub struct TemplateResponse {
    engine: Py<TemplateEngine>,
    template_name: String,
    context: Option<Py<PyDict>>,
    status_code: u16,
    headers: HashMap<String, String>,
}

#[pymethods]
impl TemplateResponse {
    #[new]
    pub fn new(
        engine: Py<TemplateEngine>,
        template_name: String,
        context: Option<Py<PyDict>>,
        status_code: Option<u16>,
    ) -> Self {
        let mut headers = HashMap::new();
        headers.insert("content-type".to_string(), "text/html; charset=utf-8".to_string());
        
        TemplateResponse {
            engine,
            template_name,
            context,
            status_code: status_code.unwrap_or(200),
            headers,
        }
    }

    /// Render the template and return HTML content
    pub fn render(&self, py: Python) -> PyResult<String> {
        let engine = self.engine.bind(py);
        let context = self.context.as_ref().map(|c| c.bind(py));
        engine.call_method1("render", (&self.template_name, context))?.extract()
    }

    /// Get status code
    pub fn get_status_code(&self) -> u16 {
        self.status_code
    }

    /// Set status code
    pub fn set_status_code(&mut self, status_code: u16) {
        self.status_code = status_code;
    }

    /// Get headers
    pub fn get_headers(&self) -> HashMap<String, String> {
        self.headers.clone()
    }

    /// Set header
    pub fn set_header(&mut self, key: String, value: String) {
        self.headers.insert(key, value);
    }

    /// Add multiple headers
    pub fn add_headers(&mut self, headers: HashMap<String, String>) {
        self.headers.extend(headers);
    }
}

/// Register template engine with Python module
pub fn register_templates(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<TemplateEngine>()?;
    m.add_class::<TemplateResponse>()?;
    
    // Add module-level functions as a regular function instead of using pyfn
    m.add_function(wrap_pyfunction!(create_template_engine, m)?)?;
    
    Ok(())
}

/// Create template engine function for Python
#[pyfunction]
fn create_template_engine(
    template_dir: &str,
    auto_reload: Option<bool>,
    cache_enabled: Option<bool>,
    strict_mode: Option<bool>,
) -> PyResult<TemplateEngine> {
    TemplateEngine::new(
        template_dir,
        auto_reload.unwrap_or(true),
        cache_enabled.unwrap_or(true),
        strict_mode.unwrap_or(true),
    )
}
