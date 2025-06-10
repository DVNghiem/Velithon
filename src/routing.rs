use pyo3::prelude::*;
use pyo3::types::PyDict;
use regex::Regex;
use ahash::AHashMap;

/// Match result for route matching
#[pyclass]
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Match {
    #[pyo3(name = "NONE")]
    None = 0,
    #[pyo3(name = "PARTIAL")]
    Partial = 1,
    #[pyo3(name = "FULL")]
    Full = 2,
}

#[pymethods]
impl Match {
    fn __int__(&self) -> i32 {
        *self as i32
    }
    
    fn __eq__(&self, other: &Self) -> bool {
        self == other
    }
    
    fn __repr__(&self) -> String {
        match self {
            Match::None => "Match.NONE".to_string(),
            Match::Partial => "Match.PARTIAL".to_string(),
            Match::Full => "Match.FULL".to_string(),
        }
    }
}

/// Fast route matching with path parameter extraction
#[pyclass(name = "_RouteOptimizer")]
pub struct RouteOptimizer {
    path_regex: Regex,
    param_convertors: Py<PyDict>,
    methods: Option<AHashMap<String, ()>>,
    path_cache: AHashMap<String, (Match, Option<AHashMap<String, Py<PyAny>>>)>,
    max_cache_size: usize,
    // Fast path for simple routes without parameters
    is_simple_route: bool,
    simple_path: Option<String>,
}

#[pymethods]
impl RouteOptimizer {
    #[new]
    #[pyo3(signature = (path_regex, path_format, param_convertors, methods=None, max_cache_size=1000))]
    fn new(
        path_regex: &str,
        path_format: String,
        param_convertors: Py<PyDict>,
        methods: Option<Vec<String>>,
        max_cache_size: usize,
    ) -> PyResult<Self> {
        let regex = Regex::new(path_regex)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid regex: {}", e)))?;
        
        let methods_map = methods.map(|m| {
            let mut map = AHashMap::new();
            for method in m {
                map.insert(method.to_uppercase(), ());
            }
            // Add HEAD if GET is present
            if map.contains_key("GET") {
                map.insert("HEAD".to_string(), ());
            }
            map
        });

        // Check if this is a simple route (no parameters)
        let is_simple_route = !path_format.contains('{') && !path_regex.contains('(');
        let simple_path = if is_simple_route { Some(path_format.clone()) } else { None };

        Ok(RouteOptimizer {
            path_regex: regex,
            param_convertors,
            methods: methods_map,
            path_cache: AHashMap::new(),
            max_cache_size,
            is_simple_route,
            simple_path,
        })
    }

    /// Fast path matching with caching
    #[pyo3(signature = (route_path, method))]
    fn matches(&mut self, py: Python, route_path: &str, method: &str) -> PyResult<(Match, Option<Py<PyDict>>)> {
        // Fast path for simple routes without parameters
        if self.is_simple_route {
            if let Some(ref simple_path) = self.simple_path {
                if route_path == simple_path {
                    let match_type = if let Some(ref methods) = self.methods {
                        if methods.contains_key(&method.to_uppercase()) {
                            Match::Full
                        } else {
                            Match::Partial
                        }
                    } else {
                        Match::Full
                    };
                    return Ok((match_type, None));
                } else {
                    return Ok((Match::None, None));
                }
            }
        }

        let path_key = format!("{}:{}", route_path, method);
        
        // Check cache first
        if let Some((match_type, cached_params)) = self.path_cache.get(&path_key) {
            let params_dict = if let Some(params) = cached_params {
                let dict = PyDict::new(py);
                for (key, value) in params {
                    dict.set_item(key, value.bind(py))?;
                }
                Some(dict.unbind())
            } else {
                None
            };
            return Ok((*match_type, params_dict));
        }

        // Perform regex matching
        if let Some(captures) = self.path_regex.captures(route_path) {
            let mut matched_params = AHashMap::new();
            let param_convertors_dict = self.param_convertors.bind(py);
            
            // Extract and convert parameters
            for (name, value) in captures.iter().skip(1).zip(self.path_regex.capture_names().skip(1)) {
                if let (Some(capture), Some(param_name)) = (name, value) {
                    let param_value = capture.as_str();
                    if let Ok(Some(convertor)) = param_convertors_dict.get_item(param_name) {
                        // Call the convert method on the convertor
                        let converted = convertor.call_method1("convert", (param_value,))?;
                        matched_params.insert(param_name.to_string(), converted.unbind());
                    }
                }
            }

            // Determine match type
            let match_type = if let Some(ref methods) = self.methods {
                if methods.contains_key(&method.to_uppercase()) {
                    Match::Full
                } else {
                    Match::Partial
                }
            } else {
                Match::Full
            };

            // Cache the result (with size limit)
            if self.path_cache.len() >= self.max_cache_size {
                // Clear 20% of the cache when it gets too big
                let keys_to_remove: Vec<String> = self.path_cache.keys()
                    .take(self.max_cache_size / 5)
                    .cloned()
                    .collect();
                for key in keys_to_remove {
                    self.path_cache.remove(&key);
                }
            }
            
            let cache_params = if matched_params.is_empty() {
                None
            } else {
                // Create a new hashmap for caching by cloning the values
                let mut cache_map = AHashMap::new();
                for (key, value) in &matched_params {
                    cache_map.insert(key.clone(), value.clone_ref(py));
                }
                Some(cache_map)
            };
            self.path_cache.insert(path_key, (match_type, cache_params));

            // Convert to Python dict
            let params_dict = if matched_params.is_empty() {
                None
            } else {
                let dict = PyDict::new(py);
                for (key, value) in matched_params {
                    dict.set_item(key, value.bind(py))?;
                }
                Some(dict.unbind())
            };

            Ok((match_type, params_dict))
        } else {
            // Cache miss result
            if self.path_cache.len() < self.max_cache_size {
                self.path_cache.insert(path_key, (Match::None, None));
            }
            Ok((Match::None, None))
        }
    }

    /// Get allowed methods for this route
    fn get_allowed_methods(&self) -> Option<Vec<String>> {
        self.methods.as_ref().map(|m| m.keys().cloned().collect())
    }

    /// Clear the path cache
    fn clear_cache(&mut self) {
        self.path_cache.clear();
    }

    /// Get cache statistics
    fn cache_stats(&self) -> (usize, usize) {
        (self.path_cache.len(), self.max_cache_size)
    }
}

/// High-performance router with optimized route lookup
#[pyclass(name = "_RouterOptimizer")]
pub struct RouterOptimizer {
    exact_routes: AHashMap<String, usize>, // path:method -> route_index
    route_lookup: AHashMap<String, isize>, // path:method -> route_index or -1 for not_found
    max_cache_size: usize,
}

#[pymethods]
impl RouterOptimizer {
    #[new]
    #[pyo3(signature = (max_cache_size=1000))]
    fn new(max_cache_size: usize) -> Self {
        RouterOptimizer {
            exact_routes: AHashMap::new(),
            route_lookup: AHashMap::new(),
            max_cache_size,
        }
    }

    /// Cache a route lookup result
    #[pyo3(signature = (path, method, route_index, is_exact=false))]
    fn cache_route(&mut self, path: &str, method: &str, route_index: isize, is_exact: bool) {
        let route_key = format!("{}:{}", path, method);
        
        if is_exact && route_index >= 0 {
            self.exact_routes.insert(route_key.clone(), route_index as usize);
        }
        
        // Limit cache size
        if self.route_lookup.len() >= self.max_cache_size {
            let keys_to_remove: Vec<String> = self.route_lookup.keys()
                .take(self.max_cache_size / 5)
                .cloned()
                .collect();
            for key in keys_to_remove {
                self.route_lookup.remove(&key);
            }
        }
        
        self.route_lookup.insert(route_key, route_index);
    }

    /// Look up a cached route
    #[pyo3(signature = (path, method))]
    fn lookup_route(&self, path: &str, method: &str) -> Option<isize> {
        let route_key = format!("{}:{}", path, method);
        
        // Check exact routes first
        if let Some(&route_index) = self.exact_routes.get(&route_key) {
            return Some(route_index as isize);
        }
        
        // Then check general lookup
        self.route_lookup.get(&route_key).copied()
    }

    /// Clear all caches
    fn clear_caches(&mut self) {
        self.exact_routes.clear();
        self.route_lookup.clear();
    }

    /// Get cache statistics
    fn cache_stats(&self) -> (usize, usize, usize) {
        (self.exact_routes.len(), self.route_lookup.len(), self.max_cache_size)
    }
}

/// High-performance route pattern matcher
#[pyclass(name = "_RoutePatternMatcher")]
pub struct RoutePatternMatcher {
    patterns: Vec<(Regex, String, Py<PyDict>)>, // (regex, path_format, convertors)
    exact_paths: AHashMap<String, usize>, // exact path -> pattern index
}

#[pymethods]
impl RoutePatternMatcher {
    #[new]
    fn new() -> Self {
        RoutePatternMatcher {
            patterns: Vec::new(),
            exact_paths: AHashMap::new(),
        }
    }

    /// Add a compiled route pattern
    #[pyo3(signature = (path_regex, path_format, param_convertors, is_exact_path=false))]
    fn add_pattern(
        &mut self,
        path_regex: &str,
        path_format: String,
        param_convertors: Py<PyDict>,
        is_exact_path: bool,
    ) -> PyResult<usize> {
        let regex = Regex::new(path_regex)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid regex: {}", e)))?;
        
        let index = self.patterns.len();
        self.patterns.push((regex, path_format, param_convertors));
        
        if is_exact_path {
            // Extract the exact path from the regex if it's a simple path
            let path = path_regex.trim_start_matches('^').trim_end_matches('$');
            if !path.contains('(') && !path.contains('[') && !path.contains('{') {
                self.exact_paths.insert(path.to_string(), index);
            }
        }
        
        Ok(index)
    }

    /// Match a path against all patterns
    #[pyo3(signature = (route_path))]
    fn match_path(&self, py: Python, route_path: &str) -> PyResult<Option<(usize, Option<Py<PyDict>>)>> {
        // Check exact paths first
        if let Some(&index) = self.exact_paths.get(route_path) {
            return Ok(Some((index, None)));
        }
        
        // Check patterns
        for (index, (regex, _, param_convertors)) in self.patterns.iter().enumerate() {
            if let Some(captures) = regex.captures(route_path) {
                let param_convertors_dict = param_convertors.bind(py);
                let params_dict = PyDict::new(py);
                
                for (capture, name) in captures.iter().skip(1).zip(regex.capture_names().skip(1)) {
                    if let (Some(capture), Some(param_name)) = (capture, name) {
                        let param_value = capture.as_str();
                        if let Ok(Some(convertor)) = param_convertors_dict.get_item(param_name) {
                            let converted = convertor.call_method1("convert", (param_value,))?;
                            params_dict.set_item(param_name, converted)?;
                        }
                    }
                }
                
                let params = if params_dict.is_empty() {
                    None
                } else {
                    Some(params_dict.unbind())
                };
                
                return Ok(Some((index, params)));
            }
        }
        
        Ok(None)
    }

    /// Get the number of patterns
    fn pattern_count(&self) -> usize {
        self.patterns.len()
    }

    /// Clear all patterns
    fn clear(&mut self) {
        self.patterns.clear();
        self.exact_paths.clear();
    }
}

/// Register routing functions and classes with Python
pub fn register_routing(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Register enums
    m.add_class::<Match>()?;
    
    // Register main classes
    m.add_class::<RouteOptimizer>()?;
    m.add_class::<RouterOptimizer>()?;
    m.add_class::<RoutePatternMatcher>()?;
    
    Ok(())
}
