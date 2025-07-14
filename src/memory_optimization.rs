use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::Arc;
use parking_lot::{Mutex, RwLock};

/// Simple memory statistics tracking  
#[pyclass]
pub struct MemoryStats {
    allocated_bytes: Arc<Mutex<u64>>,
    peak_allocated_bytes: Arc<Mutex<u64>>,
    allocation_count: Arc<Mutex<u64>>,
}

#[pymethods]
impl MemoryStats {
    #[new]
    fn new() -> Self {
        Self {
            allocated_bytes: Arc::new(Mutex::new(0)),
            peak_allocated_bytes: Arc::new(Mutex::new(0)),
            allocation_count: Arc::new(Mutex::new(0)),
        }
    }

    /// Record an allocation
    fn record_allocation(&self, size: u64) {
        let mut allocated = self.allocated_bytes.lock();
        let mut peak = self.peak_allocated_bytes.lock();
        let mut count = self.allocation_count.lock();

        *allocated += size;
        *count += 1;

        if *allocated > *peak {
            *peak = *allocated;
        }
    }

    /// Record a deallocation
    fn record_deallocation(&self, size: u64) {
        let mut allocated = self.allocated_bytes.lock();
        *allocated = allocated.saturating_sub(size);
    }

    /// Get current statistics
    fn get_stats(&self) -> HashMap<String, u64> {
        let allocated = *self.allocated_bytes.lock();
        let peak = *self.peak_allocated_bytes.lock();
        let count = *self.allocation_count.lock();

        let mut stats = HashMap::new();
        stats.insert("allocated_bytes".to_string(), allocated);
        stats.insert("peak_allocated_bytes".to_string(), peak);
        stats.insert("allocation_count".to_string(), count);
        stats.insert("allocated_mb".to_string(), allocated / (1024 * 1024));
        stats.insert("peak_allocated_mb".to_string(), peak / (1024 * 1024));

        stats
    }

    /// Reset all statistics
    fn reset(&self) {
        *self.allocated_bytes.lock() = 0;
        *self.peak_allocated_bytes.lock() = 0;
        *self.allocation_count.lock() = 0;
    }
}

/// String interning for memory efficiency
#[pyclass]
pub struct StringInterner {
    strings: Arc<RwLock<HashMap<String, String>>>,
    stats: Arc<Mutex<InternerStats>>,
}

#[derive(Debug, Default)]
struct InternerStats {
    interns: u64,
    hits: u64,
    cleanups: u64,
}

#[pymethods]
impl StringInterner {
    #[new]
    fn new() -> Self {
        Self {
            strings: Arc::new(RwLock::new(HashMap::new())),
            stats: Arc::new(Mutex::new(InternerStats::default())),
        }
    }

    /// Intern a string, returning a reference to the canonical version
    fn intern(&self, s: String) -> String {
        let mut stats = self.stats.lock();
        stats.interns += 1;

        // Check if we already have this string
        {
            let strings = self.strings.read();
            if let Some(existing) = strings.get(&s) {
                stats.hits += 1;
                return existing.clone();
            }
        }

        // Add new string
        {
            let mut strings = self.strings.write();
            // Double-check after acquiring write lock
            if let Some(existing) = strings.get(&s) {
                stats.hits += 1;
                return existing.clone();
            }
            strings.insert(s.clone(), s.clone());
        }

        s
    }

    /// Get interner statistics
    fn get_stats(&self) -> HashMap<String, u64> {
        let stats = self.stats.lock();
        let strings = self.strings.read();
        
        let mut result = HashMap::new();
        result.insert("interns".to_string(), stats.interns);
        result.insert("hits".to_string(), stats.hits);
        result.insert("current_strings".to_string(), strings.len() as u64);
        
        let hit_rate = if stats.interns > 0 {
            (stats.hits * 100) / stats.interns
        } else {
            0
        };
        result.insert("hit_rate_percent".to_string(), hit_rate);
        
        result
    }

    /// Clear all interned strings
    fn clear(&self) {
        let mut strings = self.strings.write();
        strings.clear();
        
        let mut stats = self.stats.lock();
        *stats = InternerStats::default();
    }
}

/// Memory-aware LRU cache with automatic eviction
#[pyclass]
pub struct MemoryAwareLRUCache {
    cache: Arc<RwLock<HashMap<String, CacheEntry>>>,
    access_order: Arc<Mutex<Vec<String>>>,
    max_entries: usize,
    max_memory_bytes: usize,
    current_memory_bytes: Arc<Mutex<usize>>,
    stats: Arc<Mutex<CacheStats>>,
}

struct CacheEntry {
    value: String, // Simplified to String for thread safety
    size_bytes: usize,
    access_count: u64,
}

#[derive(Debug, Default)]
struct CacheStats {
    hits: u64,
    misses: u64,
    evictions: u64,
    memory_evictions: u64,
}

#[pymethods]
impl MemoryAwareLRUCache {
    #[new]
    #[pyo3(signature = (max_entries = 1000, max_memory_mb = 100))]
    fn new(max_entries: usize, max_memory_mb: usize) -> Self {
        Self {
            cache: Arc::new(RwLock::new(HashMap::new())),
            access_order: Arc::new(Mutex::new(Vec::new())),
            max_entries,
            max_memory_bytes: max_memory_mb * 1024 * 1024,
            current_memory_bytes: Arc::new(Mutex::new(0)),
            stats: Arc::new(Mutex::new(CacheStats::default())),
        }
    }

    /// Get value from cache
    fn get(&self, key: String) -> Option<String> {
        let mut stats = self.stats.lock();
        
        {
            let cache = self.cache.read();
            if let Some(entry) = cache.get(&key) {
                stats.hits += 1;
                
                // Update access order
                {
                    let mut access_order = self.access_order.lock();
                    access_order.retain(|k| k != &key);
                    access_order.push(key);
                }
                
                return Some(entry.value.clone());
            }
        }
        
        stats.misses += 1;
        None
    }

    /// Put value in cache with memory-aware eviction
    fn put(&self, key: String, value: String) -> PyResult<()> {
        let value_size = value.len();
        
        // Check if single value exceeds memory limit
        if value_size > self.max_memory_bytes {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Value too large for cache"
            ));
        }

        let entry = CacheEntry {
            value,
            size_bytes: value_size,
            access_count: 1,
        };

        // Evict entries if necessary
        self.evict_if_necessary(value_size)?;

        // Insert new entry
        {
            let mut cache = self.cache.write();
            if let Some(old_entry) = cache.insert(key.clone(), entry) {
                let mut current_memory = self.current_memory_bytes.lock();
                *current_memory = current_memory.saturating_sub(old_entry.size_bytes);
            }
        }

        // Update memory usage
        {
            let mut current_memory = self.current_memory_bytes.lock();
            *current_memory += value_size;
        }

        // Update access order
        {
            let mut access_order = self.access_order.lock();
            access_order.retain(|k| k != &key);
            access_order.push(key);
        }

        Ok(())
    }

    /// Evict entries if memory or count limits are exceeded
    fn evict_if_necessary(&self, incoming_size: usize) -> PyResult<()> {
        let mut stats = self.stats.lock();
        
        // Check memory limit
        let current_memory = *self.current_memory_bytes.lock();
        if current_memory + incoming_size > self.max_memory_bytes {
            stats.memory_evictions += 1;
            self.evict_lru_entries(current_memory + incoming_size - self.max_memory_bytes)?;
        }

        // Check count limit
        let cache_count = {
            let cache = self.cache.read();
            cache.len()
        };

        if cache_count >= self.max_entries {
            stats.evictions += 1;
            self.evict_lru_entries(1)?; // Evict at least one entry
        }

        Ok(())
    }

    /// Evict LRU entries to free specified amount of memory
    fn evict_lru_entries(&self, target_bytes: usize) -> PyResult<()> {
        let mut freed_bytes = 0;
        let mut keys_to_remove = Vec::new();

        {
            let mut access_order = self.access_order.lock();
            let cache = self.cache.read();

            // Find LRU entries to remove
            while freed_bytes < target_bytes && !access_order.is_empty() {
                let key = access_order.remove(0);
                if let Some(entry) = cache.get(&key) {
                    freed_bytes += entry.size_bytes;
                    keys_to_remove.push(key);
                }
            }
        }

        // Remove entries from cache
        {
            let mut cache = self.cache.write();
            let mut current_memory = self.current_memory_bytes.lock();

            for key in keys_to_remove {
                if let Some(entry) = cache.remove(&key) {
                    *current_memory = current_memory.saturating_sub(entry.size_bytes);
                }
            }
        }

        Ok(())
    }

    /// Get cache statistics
    fn get_stats(&self) -> HashMap<String, u64> {
        let stats = self.stats.lock();
        let cache_count = {
            let cache = self.cache.read();
            cache.len() as u64
        };
        let current_memory = *self.current_memory_bytes.lock() as u64;

        let mut result = HashMap::new();
        result.insert("hits".to_string(), stats.hits);
        result.insert("misses".to_string(), stats.misses);
        result.insert("evictions".to_string(), stats.evictions);
        result.insert("memory_evictions".to_string(), stats.memory_evictions);
        result.insert("entries".to_string(), cache_count);
        result.insert("memory_bytes".to_string(), current_memory);
        result.insert("memory_mb".to_string(), current_memory / (1024 * 1024));

        let total_requests = stats.hits + stats.misses;
        let hit_rate = if total_requests > 0 {
            (stats.hits * 100) / total_requests
        } else {
            0
        };
        result.insert("hit_rate_percent".to_string(), hit_rate);

        result
    }

    /// Clear all cache entries
    fn clear(&self) {
        let mut cache = self.cache.write();
        let mut access_order = self.access_order.lock();
        let mut current_memory = self.current_memory_bytes.lock();

        cache.clear();
        access_order.clear();
        *current_memory = 0;
    }
}

/// Register memory optimization classes
pub fn register_memory_optimization(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<MemoryStats>()?;
    m.add_class::<StringInterner>()?;
    m.add_class::<MemoryAwareLRUCache>()?;
    Ok(())
}