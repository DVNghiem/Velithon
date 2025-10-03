use std::sync::Arc;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use async_graphql::{
    EmptyMutation, EmptySubscription, Object, Schema, SimpleObject, 
    Variables, ID, Request
};
use serde::{Deserialize, Serialize};
use tokio::runtime::Runtime;

/// High-performance GraphQL schema wrapper for Python integration
#[pyclass]
pub struct GraphQLSchema {
    schema: Schema<QueryRoot, EmptyMutation, EmptySubscription>,
    runtime: Arc<Runtime>,
}

/// Root query object for GraphQL schema
pub struct QueryRoot;

#[Object]
impl QueryRoot {
    /// Hello world query for testing
    async fn hello(&self, name: Option<String>) -> String {
        format!("Hello, {}!", name.unwrap_or_else(|| "World".to_string()))
    }

    /// Get current server time
    async fn server_time(&self) -> chrono::DateTime<chrono::Utc> {
        chrono::Utc::now()
    }
}

#[pymethods]
impl GraphQLSchema {
    #[new]
    pub fn new() -> PyResult<Self> {
        let runtime = Arc::new(
            Runtime::new()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Failed to create tokio runtime: {}", e)
                ))?
        );

        let schema = Schema::build(QueryRoot, EmptyMutation, EmptySubscription)
            .finish();

        Ok(GraphQLSchema {
            schema,
            runtime,
        })
    }

    /// Execute a GraphQL query
    #[pyo3(signature = (query, variables=None, operation_name=None))]
    pub fn execute(
        &self,
        py: Python,
        query: &str,
        variables: Option<&Bound<'_, PyDict>>,
        operation_name: Option<&str>,
    ) -> PyResult<String> {
        // Convert Python variables to GraphQL variables
        let variables = if let Some(vars) = variables {
            let mut graphql_vars = Variables::default();
            for (key, value) in vars.iter() {
                let key_str: String = key.extract()?;
                let value_json = python_to_json_value(&value)?;
                graphql_vars.insert(
                    async_graphql::Name::new(key_str), 
                    async_graphql::Value::from_json(value_json).unwrap_or(async_graphql::Value::Null)
                );
            }
            graphql_vars
        } else {
            Variables::default()
        };

        // Build and execute request
        let response = {
            let runtime = self.runtime.clone();
            let schema = self.schema.clone();
            
            py.allow_threads(|| {
                runtime.block_on(async {
                    let mut request = Request::new(query);
                    if !variables.is_empty() {
                        request = request.variables(variables);
                    }
                    if let Some(op_name) = operation_name {
                        request = request.operation_name(op_name);
                    }
                    schema.execute(request).await
                })
            })
        };

        // Convert response to JSON string
        let json_response = serde_json::to_string(&response)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Failed to serialize GraphQL response: {}", e)
            ))?;

        Ok(json_response)
    }

    /// Validate a GraphQL query without executing it
    pub fn validate(&self, query: &str) -> PyResult<bool> {
        match async_graphql_parser::parse_query(query) {
            Ok(_) => Ok(true), // Basic validation - just check if it parses
            Err(_) => Ok(false),
        }
    }

    /// Get the GraphQL schema definition (SDL)
    pub fn get_schema_sdl(&self) -> String {
        self.schema.sdl()
    }

    /// Execute multiple queries in batch
    pub fn execute_batch(
        &self,
        py: Python,
        queries: &Bound<'_, PyList>,
    ) -> PyResult<Vec<String>> {
        let mut results = Vec::new();
        
        for query_item in queries.iter() {
            let query_dict = query_item.downcast::<PyDict>()?;
            
            let query: String = query_dict
                .get_item("query")?
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("query key required"))?
                .extract()?;

            // Execute with default parameters for simplicity in batch mode
            let result = self.execute(py, &query, None, None)?;
            results.push(result);
        }
        
        Ok(results)
    }
}

/// Convert Python object to JSON value
fn python_to_json_value(obj: &Bound<'_, PyAny>) -> PyResult<serde_json::Value> {
    if obj.is_none() {
        Ok(serde_json::Value::Null)
    } else if let Ok(b) = obj.extract::<bool>() {
        Ok(serde_json::Value::Bool(b))
    } else if let Ok(i) = obj.extract::<i64>() {
        Ok(serde_json::Value::Number(serde_json::Number::from(i)))
    } else if let Ok(f) = obj.extract::<f64>() {
        if let Some(num) = serde_json::Number::from_f64(f) {
            Ok(serde_json::Value::Number(num))
        } else {
            Ok(serde_json::Value::Null)
        }
    } else if let Ok(s) = obj.extract::<String>() {
        Ok(serde_json::Value::String(s))
    } else if let Ok(list) = obj.downcast::<PyList>() {
        let mut vec = Vec::new();
        for item in list.iter() {
            vec.push(python_to_json_value(&item)?);
        }
        Ok(serde_json::Value::Array(vec))
    } else if let Ok(dict) = obj.downcast::<PyDict>() {
        let mut map = serde_json::Map::new();
        for (key, value) in dict.iter() {
            let key_str: String = key.extract()?;
            map.insert(key_str, python_to_json_value(&value)?);
        }
        Ok(serde_json::Value::Object(map))
    } else {
        // Try to convert to string as fallback
        let s: String = obj.str()?.extract()?;
        Ok(serde_json::Value::String(s))
    }
}

/// High-performance GraphQL query builder
#[pyclass]
pub struct GraphQLQueryBuilder {
    query_parts: Vec<String>,
}

#[pymethods]
impl GraphQLQueryBuilder {
    #[new]
    pub fn new() -> Self {
        GraphQLQueryBuilder {
            query_parts: Vec::new(),
        }
    }

    /// Add a query field
    pub fn field(&mut self, field_name: &str, args: Option<&Bound<'_, PyDict>>, subfields: Option<&Bound<'_, PyList>>) -> PyResult<()> {
        let mut field_str = field_name.to_string();
        
        // Add arguments if provided
        if let Some(args) = args {
            let mut arg_parts = Vec::new();
            for (key, value) in args.iter() {
                let key_str: String = key.extract()?;
                let value_str = format_value_for_query(&value)?;
                arg_parts.push(format!("{}: {}", key_str, value_str));
            }
            if !arg_parts.is_empty() {
                field_str.push_str(&format!("({})", arg_parts.join(", ")));
            }
        }
        
        // Add subfields if provided
        if let Some(subfields) = subfields {
            let mut subfield_parts = Vec::new();
            for subfield in subfields.iter() {
                let subfield_str: String = subfield.extract()?;
                subfield_parts.push(subfield_str);
            }
            if !subfield_parts.is_empty() {
                field_str.push_str(&format!(" {{ {} }}", subfield_parts.join(" ")));
            }
        }
        
        self.query_parts.push(field_str);
        Ok(())
    }

    /// Build the final GraphQL query string
    pub fn build(&self, operation_type: Option<&str>) -> String {
        let op_type = operation_type.unwrap_or("query");
        format!("{} {{ {} }}", op_type, self.query_parts.join(" "))
    }

    /// Reset the query builder
    pub fn reset(&mut self) {
        self.query_parts.clear();
    }
}

/// Format Python value for GraphQL query string
fn format_value_for_query(value: &Bound<'_, PyAny>) -> PyResult<String> {
    if value.is_none() {
        Ok("null".to_string())
    } else if let Ok(b) = value.extract::<bool>() {
        Ok(b.to_string())
    } else if let Ok(i) = value.extract::<i64>() {
        Ok(i.to_string())
    } else if let Ok(f) = value.extract::<f64>() {
        Ok(f.to_string())
    } else if let Ok(s) = value.extract::<String>() {
        Ok(format!("\"{}\"", s.replace('"', "\\\"")))
    } else {
        let s: String = value.str()?.extract()?;
        Ok(format!("\"{}\"", s.replace('"', "\\\"")))
    }
}

/// Register GraphQL functions and classes with Python
pub fn register_graphql(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<GraphQLSchema>()?;
    m.add_class::<GraphQLQueryBuilder>()?;
    m.add_class::<ExtendedGraphQLSchema>()?;
    
    // Add convenience function to create a new schema
    m.add_function(wrap_pyfunction!(create_graphql_schema, m)?)?;
    
    // Add convenience function to create a query builder
    m.add_function(wrap_pyfunction!(create_query_builder, m)?)?;
    
    Ok(())
}

/// Create a new GraphQL schema
#[pyfunction]
fn create_graphql_schema() -> PyResult<GraphQLSchema> {
    GraphQLSchema::new()
}

/// Create a new query builder
#[pyfunction]
fn create_query_builder() -> GraphQLQueryBuilder {
    GraphQLQueryBuilder::new()
}

// Custom GraphQL types for common use cases
#[derive(SimpleObject, Serialize, Deserialize)]
pub struct User {
    id: ID,
    name: String,
    email: String,
    created_at: chrono::DateTime<chrono::Utc>,
}

#[derive(SimpleObject, Serialize, Deserialize)]
pub struct Post {
    id: ID,
    title: String,
    content: String,
    author_id: ID,
    created_at: chrono::DateTime<chrono::Utc>,
    updated_at: chrono::DateTime<chrono::Utc>,
}

/// Extended query root with more complex operations
pub struct ExtendedQueryRoot {
    users: Vec<User>,
    posts: Vec<Post>,
}

#[Object]
impl ExtendedQueryRoot {
    /// Get all users
    async fn users(&self) -> &Vec<User> {
        &self.users
    }
    
    /// Get user by ID
    async fn user(&self, id: ID) -> Option<&User> {
        self.users.iter().find(|user| user.id == id)
    }
    
    /// Get all posts
    async fn posts(&self) -> &Vec<Post> {
        &self.posts
    }
    
    /// Get post by ID
    async fn post(&self, id: ID) -> Option<&Post> {
        self.posts.iter().find(|post| post.id == id)
    }
    
    /// Search posts by title
    async fn search_posts(&self, query: String) -> Vec<&Post> {
        self.posts
            .iter()
            .filter(|post| post.title.to_lowercase().contains(&query.to_lowercase()))
            .collect()
    }
}

/// Extended GraphQL schema with more complex types
#[pyclass]
pub struct ExtendedGraphQLSchema {
    schema: Schema<ExtendedQueryRoot, EmptyMutation, EmptySubscription>,
    runtime: Arc<Runtime>,
}

#[pymethods]
impl ExtendedGraphQLSchema {
    #[new]
    pub fn new() -> PyResult<Self> {
        let runtime = Arc::new(
            Runtime::new()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Failed to create tokio runtime: {}", e)
                ))?
        );

        // Initialize with some sample data
        let users = vec![
            User {
                id: ID::from("1"),
                name: "John Doe".to_string(),
                email: "john@example.com".to_string(),
                created_at: chrono::Utc::now(),
            },
            User {
                id: ID::from("2"),
                name: "Jane Smith".to_string(),
                email: "jane@example.com".to_string(),
                created_at: chrono::Utc::now(),
            },
        ];

        let posts = vec![
            Post {
                id: ID::from("1"),
                title: "Hello GraphQL".to_string(),
                content: "This is my first GraphQL post".to_string(),
                author_id: ID::from("1"),
                created_at: chrono::Utc::now(),
                updated_at: chrono::Utc::now(),
            },
            Post {
                id: ID::from("2"),
                title: "Rust Performance".to_string(),
                content: "Why Rust is perfect for high-performance GraphQL".to_string(),
                author_id: ID::from("2"),
                created_at: chrono::Utc::now(),
                updated_at: chrono::Utc::now(),
            },
        ];

        let query_root = ExtendedQueryRoot { users, posts };
        let schema = Schema::build(query_root, EmptyMutation, EmptySubscription)
            .finish();

        Ok(ExtendedGraphQLSchema {
            schema,
            runtime,
        })
    }

    /// Execute a GraphQL query on the extended schema
    #[pyo3(signature = (query, variables=None, operation_name=None))]
    pub fn execute(
        &self,
        py: Python,
        query: &str,
        variables: Option<&Bound<'_, PyDict>>,
        operation_name: Option<&str>,
    ) -> PyResult<String> {
        let variables = if let Some(vars) = variables {
            let mut graphql_vars = Variables::default();
            for (key, value) in vars.iter() {
                let key_str: String = key.extract()?;
                let value_json = python_to_json_value(&value)?;
                graphql_vars.insert(
                    async_graphql::Name::new(key_str), 
                    async_graphql::Value::from_json(value_json).unwrap_or(async_graphql::Value::Null)
                );
            }
            graphql_vars
        } else {
            Variables::default()
        };

        let response = {
            let runtime = self.runtime.clone();
            let schema = self.schema.clone();
            
            py.allow_threads(|| {
                runtime.block_on(async {
                    let mut request = Request::new(query);
                    if !variables.is_empty() {
                        request = request.variables(variables);
                    }
                    if let Some(op_name) = operation_name {
                        request = request.operation_name(op_name);
                    }
                    schema.execute(request).await
                })
            })
        };

        let json_response = serde_json::to_string(&response)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Failed to serialize GraphQL response: {}", e)
            ))?;

        Ok(json_response)
    }

    /// Get the GraphQL schema definition (SDL)
    pub fn get_schema_sdl(&self) -> String {
        self.schema.sdl()
    }
}