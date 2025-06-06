use pyo3::prelude::*;
use pyo3::types::PyDict;
use regex::Regex;
use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use std::hash::{Hash, Hasher};
use std::collections::hash_map::DefaultHasher;

/// High-performance route matcher with caching
#[pyclass]
pub struct RouteCache {
    /// Cache of compiled routes: path_pattern -> RouteInfo
    routes: Arc<RwLock<HashMap<String, RouteInfo>>>,
    /// Fast lookup cache: (method, path) -> (RouteInfo, extracted_params)
    match_cache: Arc<RwLock<HashMap<u64, CachedMatch>>>,
    max_cache_size: usize,
    cache_hits: Arc<RwLock<u64>>,
    cache_misses: Arc<RwLock<u64>>,
}

#[derive(Clone)]
struct RouteInfo {
    pattern: String,
    regex: Regex,
    param_names: Vec<String>,
    methods: Option<Vec<String>>,
}

#[derive(Clone)]
struct CachedMatch {
    route_pattern: String,
    params: HashMap<String, String>,
    match_type: MatchType,
}

#[derive(Clone, PartialEq)]
enum MatchType {
    None,
    Partial,  // Path matches but method doesn't
    Full,     // Both path and method match
}

#[pymethods]
impl RouteCache {
    #[new]
    #[pyo3(signature = (max_cache_size = 10000))]
    fn new(max_cache_size: usize) -> Self {
        Self {
            routes: Arc::new(RwLock::new(HashMap::new())),
            match_cache: Arc::new(RwLock::new(HashMap::new())),
            max_cache_size,
            cache_hits: Arc::new(RwLock::new(0)),
            cache_misses: Arc::new(RwLock::new(0)),
        }
    }

    /// Register a route pattern with its regex and parameter information
    fn add_route(
        &self,
        pattern: String,
        regex_str: String,
        param_names: Vec<String>,
        methods: Option<Vec<String>>,
    ) -> PyResult<()> {
        let regex = Regex::new(&regex_str)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid regex: {}", e)))?;

        let route_info = RouteInfo {
            pattern: pattern.clone(),
            regex,
            param_names,
            methods,
        };

        let mut routes = self.routes.write().unwrap();
        routes.insert(pattern, route_info);
        Ok(())
    }

    /// Fast route matching with caching
    fn match_route(
        &self,
        method: &str,
        path: &str,
    ) -> PyResult<(String, PyObject)> {  // Returns (match_type, params_dict)
        let cache_key = self.generate_cache_key(method, path);

        // Check cache first
        {
            let cache = self.match_cache.read().unwrap();
            if let Some(cached) = cache.get(&cache_key) {
                *self.cache_hits.write().unwrap() += 1;
                
                let match_type_str = match cached.match_type {
                    MatchType::None => "none",
                    MatchType::Partial => "partial", 
                    MatchType::Full => "full",
                };
                
                return Python::with_gil(|py| {
                    let params_dict = PyDict::new(py);
                    for (k, v) in &cached.params {
                        params_dict.set_item(k, v)?;
                    }
                    Ok((match_type_str.to_string(), params_dict.into()))
                });
            }
        }

        // Cache miss - perform actual matching
        *self.cache_misses.write().unwrap() += 1;
        let (match_type, params, route_pattern) = self.perform_matching(method, path)?;

        // Cache the result
        self.cache_match_result(cache_key, route_pattern, params.clone(), match_type.clone());

        let match_type_str = match match_type {
            MatchType::None => "none",
            MatchType::Partial => "partial",
            MatchType::Full => "full",
        };

        Python::with_gil(|py| {
            let params_dict = PyDict::new(py);
            for (k, v) in params {
                params_dict.set_item(k, v)?;
            }
            Ok((match_type_str.to_string(), params_dict.into()))
        })
    }

    /// Get cache statistics
    fn get_cache_stats(&self) -> PyResult<(u64, u64, f64, usize)> {
        let hits = *self.cache_hits.read().unwrap();
        let misses = *self.cache_misses.read().unwrap();
        let total = hits + misses;
        let hit_rate = if total > 0 { hits as f64 / total as f64 } else { 0.0 };
        let cache_size = self.match_cache.read().unwrap().len();
        Ok((hits, misses, hit_rate, cache_size))
    }

    /// Clear the route cache
    fn clear_cache(&self) -> PyResult<()> {
        self.match_cache.write().unwrap().clear();
        *self.cache_hits.write().unwrap() = 0;
        *self.cache_misses.write().unwrap() = 0;
        Ok(())
    }

    /// Remove a route
    fn remove_route(&self, pattern: &str) -> PyResult<()> {
        let mut routes = self.routes.write().unwrap();
        routes.remove(pattern);
        
        // Clear match cache since routes changed
        self.match_cache.write().unwrap().clear();
        Ok(())
    }
}

impl RouteCache {
    /// Generate a fast hash key for method+path combination
    fn generate_cache_key(&self, method: &str, path: &str) -> u64 {
        let mut hasher = DefaultHasher::new();
        method.hash(&mut hasher);
        path.hash(&mut hasher);
        hasher.finish()
    }

    /// Perform the actual route matching logic
    fn perform_matching(
        &self,
        method: &str,
        path: &str,
    ) -> PyResult<(MatchType, HashMap<String, String>, String)> {
        let routes = self.routes.read().unwrap();

        // Try to match each route
        for (pattern, route_info) in routes.iter() {
            if let Some(captures) = route_info.regex.captures(path) {
                // Extract parameters
                let mut params = HashMap::new();
                for (i, param_name) in route_info.param_names.iter().enumerate() {
                    if let Some(capture) = captures.get(i + 1) {
                        params.insert(param_name.clone(), capture.as_str().to_string());
                    }
                }

                // Check if method matches
                let match_type = if let Some(ref allowed_methods) = route_info.methods {
                    if allowed_methods.iter().any(|m| m.eq_ignore_ascii_case(method)) {
                        MatchType::Full
                    } else {
                        MatchType::Partial
                    }
                } else {
                    MatchType::Full // No method restriction means all methods allowed
                };

                return Ok((match_type, params, pattern.clone()));
            }
        }

        Ok((MatchType::None, HashMap::new(), String::new()))
    }

    /// Cache a match result
    fn cache_match_result(
        &self,
        cache_key: u64,
        route_pattern: String,
        params: HashMap<String, String>,
        match_type: MatchType,
    ) {
        let cached_match = CachedMatch {
            route_pattern,
            params,
            match_type,
        };

        let mut cache = self.match_cache.write().unwrap();
        
        // Limit cache size
        if cache.len() >= self.max_cache_size {
            // Remove 20% of entries when cache is full (simple LRU approximation)
            let keys_to_remove: Vec<_> = cache.keys().take(self.max_cache_size / 5).copied().collect();
            for key in keys_to_remove {
                cache.remove(&key);
            }
        }

        cache.insert(cache_key, cached_match);
    }
}

/// High-performance parameter parsing for query strings and form data
#[pyclass]
pub struct ParameterParser {
    /// Cache for parsed query strings
    query_cache: Arc<RwLock<HashMap<String, HashMap<String, String>>>>,
    max_cache_size: usize,
}

#[pymethods]
impl ParameterParser {
    #[new]
    #[pyo3(signature = (max_cache_size = 5000))]
    fn new(max_cache_size: usize) -> Self {
        Self {
            query_cache: Arc::new(RwLock::new(HashMap::new())),
            max_cache_size,
        }
    }

    /// Parse query string with caching
    fn parse_query_string(&self, query_string: &str) -> PyResult<PyObject> {
        if query_string.is_empty() {
            return Python::with_gil(|py| {
                let dict = PyDict::new(py);
                Ok(dict.into())
            });
        }

        // Check cache
        {
            let cache = self.query_cache.read().unwrap();
            if let Some(cached) = cache.get(query_string) {
                return Python::with_gil(|py| {
                    let dict = PyDict::new(py);
                    for (k, v) in cached {
                        dict.set_item(k, v)?;
                    }
                    Ok(dict.into())
                });
            }
        }

        // Parse the query string
        let mut params = HashMap::new();
        for pair in query_string.split('&') {
            if let Some((key, value)) = pair.split_once('=') {
                let decoded_key = urlencoding::decode(key).unwrap_or_else(|_| key.into());
                let decoded_value = urlencoding::decode(value).unwrap_or_else(|_| value.into());
                params.insert(decoded_key.to_string(), decoded_value.to_string());
            } else if !pair.is_empty() {
                let decoded_key = urlencoding::decode(pair).unwrap_or_else(|_| pair.into());
                params.insert(decoded_key.to_string(), String::new());
            }
        }

        // Cache the result
        if query_string.len() <= 1024 { // Only cache reasonably sized query strings
            let mut cache = self.query_cache.write().unwrap();
            if cache.len() >= self.max_cache_size {
                // Simple cache eviction
                let keys_to_remove: Vec<_> = cache.keys().take(self.max_cache_size / 5).cloned().collect();
                for key in keys_to_remove {
                    cache.remove(&key);
                }
            }
            cache.insert(query_string.to_string(), params.clone());
        }

        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            for (k, v) in params {
                dict.set_item(k, v)?;
            }
            Ok(dict.into())
        })
    }

    /// Clear the query cache
    fn clear_cache(&self) -> PyResult<()> {
        self.query_cache.write().unwrap().clear();
        Ok(())
    }

    /// Get cache statistics
    fn get_cache_size(&self) -> PyResult<usize> {
        Ok(self.query_cache.read().unwrap().len())
    }
}

/// Register routing components
pub fn register_routing(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RouteCache>()?;
    m.add_class::<ParameterParser>()?;
    Ok(())
}
