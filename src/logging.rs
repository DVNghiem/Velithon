use chrono::{DateTime, Utc};
use crossbeam_channel::{unbounded, Receiver, Sender};
use flate2::write::GzEncoder;
use flate2::Compression;
use parking_lot::Mutex;
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use serde_json;
use std::collections::HashMap;
use std::fs::{File, OpenOptions};
use std::io::{BufWriter, Write};
use std::path::Path;
use std::sync::{Arc, OnceLock};
use std::thread;

#[derive(Debug, Clone, PartialEq)]
pub enum LogLevel {
    Debug,
    Info,
    Warn,
    Error,
    Critical,
}

impl LogLevel {
    fn from_str(s: &str) -> Self {
        match s.to_uppercase().as_str() {
            "DEBUG" => LogLevel::Debug,
            "INFO" => LogLevel::Info,
            "WARN" | "WARNING" => LogLevel::Warn,
            "ERROR" => LogLevel::Error,
            "CRITICAL" => LogLevel::Critical,
            _ => LogLevel::Info,
        }
    }

    fn to_string(&self) -> &'static str {
        match self {
            LogLevel::Debug => "DEBUG",
            LogLevel::Info => "INFO",
            LogLevel::Warn => "WARN",
            LogLevel::Error => "ERROR",
            LogLevel::Critical => "CRITICAL",
        }
    }

    fn to_int(&self) -> u8 {
        match self {
            LogLevel::Debug => 10,
            LogLevel::Info => 20,
            LogLevel::Warn => 30,
            LogLevel::Error => 40,
            LogLevel::Critical => 50,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogRecord {
    pub timestamp: DateTime<Utc>,
    pub level: String,
    pub message: String,
    pub module: String,
    pub line: u32,
    pub request_id: Option<String>,
    pub method: Option<String>,
    pub client_ip: Option<String>,
    pub duration_ms: Option<f64>,
    pub status: Option<u16>,
    pub user_agent: Option<String>,
    #[serde(flatten)]
    pub extra: HashMap<String, String>,
}

impl LogRecord {
    pub fn new(level: LogLevel, message: String, module: String, line: u32) -> Self {
        Self {
            timestamp: Utc::now(),
            level: level.to_string().to_string(),
            message,
            module,
            line,
            request_id: None,
            method: None,
            client_ip: None,
            duration_ms: None,
            status: None,
            user_agent: None,
            extra: HashMap::new(),
        }
    }

    pub fn with_extra(mut self, extra: HashMap<String, String>) -> Self {
        for (key, value) in extra {
            match key.as_str() {
                "request_id" => self.request_id = Some(value),
                "method" => self.method = Some(value),
                "client_ip" => self.client_ip = Some(value),
                "duration_ms" => {
                    if let Ok(duration) = value.parse::<f64>() {
                        self.duration_ms = Some(duration);
                    }
                }
                "status" => {
                    if let Ok(status) = value.parse::<u16>() {
                        self.status = Some(status);
                    }
                }
                "user_agent" => self.user_agent = Some(value),
                _ => {
                    // Store arbitrary extra fields
                    self.extra.insert(key, value);
                }
            }
        }
        self
    }
}

pub trait Formatter: Send + Sync {
    fn format(&self, record: &LogRecord) -> String;
}

pub struct TextFormatter {
    _cache: Arc<Mutex<HashMap<String, Vec<String>>>>,
}

impl TextFormatter {
    pub fn new() -> Self {
        Self {
            _cache: Arc::new(Mutex::new(HashMap::new())),
        }
    }
}

impl Formatter for TextFormatter {
    fn format(&self, record: &LogRecord) -> String {
        let time_str = record.timestamp.format("%Y-%m-%d %H:%M:%S%.3f");
        let mut msg = format!(
            "{} | {:<8} | {}:{} - {}",
            time_str, record.level, record.module, record.line, record.message
        );

        // Collect all extra fields (both predefined and arbitrary)
        let mut extra_parts = Vec::new();
        
        // Predefined fields
        if let Some(ref val) = record.request_id {
            extra_parts.push(format!("request_id={}", val));
        }
        if let Some(ref val) = record.method {
            extra_parts.push(format!("method={}", val));
        }
        if let Some(ref val) = record.client_ip {
            extra_parts.push(format!("client_ip={}", val));
        }
        if let Some(val) = record.duration_ms {
            extra_parts.push(format!("duration_ms={:.2}", val));
        }
        if let Some(val) = record.status {
            extra_parts.push(format!("status={}", val));
        }
        if let Some(ref val) = record.user_agent {
            extra_parts.push(format!("user_agent={}", val));
        }
        
        // Arbitrary extra fields
        for (key, value) in &record.extra {
            extra_parts.push(format!("{}={}", key, value));
        }

        if !extra_parts.is_empty() {
            msg = format!("{} | {}", msg, extra_parts.join(", "));
        }

        msg
    }
}

pub struct JsonFormatter {
    _cache: Arc<Mutex<HashMap<String, Vec<String>>>>,
}

impl JsonFormatter {
    pub fn new() -> Self {
        Self {
            _cache: Arc::new(Mutex::new(HashMap::new())),
        }
    }
}

impl Formatter for JsonFormatter {
    fn format(&self, record: &LogRecord) -> String {
        serde_json::to_string(record).unwrap_or_else(|_| {
            format!(
                r#"{{"timestamp": "{}", "level": "{}", "message": "{}", "module": "{}", "line": {}}}"#,
                record.timestamp.to_rfc3339(),
                record.level,
                record.message,
                record.module,
                record.line
            )
        })
    }
}

pub trait Handler: Send + Sync {
    fn handle(&self, record: &LogRecord);
    #[allow(dead_code)]
    fn set_level(&mut self, level: LogLevel);
    fn is_enabled(&self, level: &LogLevel) -> bool;
}

pub struct ConsoleHandler {
    level: LogLevel,
    formatter: Box<dyn Formatter>,
}

impl ConsoleHandler {
    pub fn new(level: LogLevel, formatter: Box<dyn Formatter>) -> Self {
        Self { level, formatter }
    }
}

impl Handler for ConsoleHandler {
    fn handle(&self, record: &LogRecord) {
        let level = LogLevel::from_str(&record.level);
        if self.is_enabled(&level) {
            let formatted = self.formatter.format(record);
            eprintln!("{}", formatted);
        }
    }

    fn set_level(&mut self, level: LogLevel) {
        self.level = level;
    }

    fn is_enabled(&self, level: &LogLevel) -> bool {
        level.to_int() >= self.level.to_int()
    }
}

pub struct FileHandler {
    level: LogLevel,
    formatter: Box<dyn Formatter>,
    file: Arc<Mutex<BufWriter<File>>>,
    max_bytes: u64,
    backup_count: u32,
    current_size: Arc<Mutex<u64>>,
    file_path: String,
}

impl FileHandler {
    pub fn new(
        file_path: String,
        level: LogLevel,
        formatter: Box<dyn Formatter>,
        max_bytes: u64,
        backup_count: u32,
    ) -> Result<Self, Box<dyn std::error::Error>> {
        let file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&file_path)?;
        let current_size = file.metadata()?.len();
        let buf_writer = BufWriter::new(file);

        Ok(Self {
            level,
            formatter,
            file: Arc::new(Mutex::new(buf_writer)),
            max_bytes,
            backup_count,
            current_size: Arc::new(Mutex::new(current_size)),
            file_path,
        })
    }

    fn rotate(&self) -> Result<(), Box<dyn std::error::Error>> {
        // Close current file
        {
            let mut file = self.file.lock();
            file.flush()?;
        }

        // Rotate backup files
        for i in (1..self.backup_count).rev() {
            let src = format!("{}.{}.gz", self.file_path, i);
            let dst = format!("{}.{}.gz", self.file_path, i + 1);
            if Path::new(&src).exists() {
                std::fs::rename(&src, &dst)?;
            }
        }

        // Compress current file to .1.gz
        if Path::new(&self.file_path).exists() {
            let dst = format!("{}.1.gz", self.file_path);
            let input = std::fs::read(&self.file_path)?;
            let output = File::create(&dst)?;
            let mut encoder = GzEncoder::new(output, Compression::default());
            encoder.write_all(&input)?;
            encoder.finish()?;
            std::fs::remove_file(&self.file_path)?;
        }

        // Create new file
        let new_file = OpenOptions::new()
            .create(true)
            .write(true)
            .truncate(true)
            .open(&self.file_path)?;
        let buf_writer = BufWriter::new(new_file);
        *self.file.lock() = buf_writer;
        *self.current_size.lock() = 0;

        Ok(())
    }
}

impl Handler for FileHandler {
    fn handle(&self, record: &LogRecord) {
        let level = LogLevel::from_str(&record.level);
        if !self.is_enabled(&level) {
            return;
        }

        let formatted = self.formatter.format(record);
        let log_line = format!("{}\n", formatted);

        // Check if rotation is needed
        {
            let current_size = *self.current_size.lock();
            if current_size + log_line.len() as u64 > self.max_bytes {
                if let Err(e) = self.rotate() {
                    eprintln!("Failed to rotate log file: {}", e);
                }
            }
        }

        // Write to file
        {
            let mut file = self.file.lock();
            if let Err(e) = file.write_all(log_line.as_bytes()) {
                eprintln!("Failed to write to log file: {}", e);
            } else {
                // Flush immediately to ensure data is written
                if let Err(e) = file.flush() {
                    eprintln!("Failed to flush log file: {}", e);
                } else {
                    let mut size = self.current_size.lock();
                    *size += log_line.len() as u64;
                }
            }
        }
    }

    fn set_level(&mut self, level: LogLevel) {
        self.level = level;
    }

    fn is_enabled(&self, level: &LogLevel) -> bool {
        level.to_int() >= self.level.to_int()
    }
}

pub struct Logger {
    level: LogLevel,
    handlers: Vec<Arc<dyn Handler>>,
    sender: Option<Sender<LogRecord>>,
}

impl Logger {
    pub fn new(level: LogLevel) -> Self {
        Self {
            level,
            handlers: Vec::new(),
            sender: None,
        }
    }

    pub fn add_handler(&mut self, handler: Arc<dyn Handler>) {
        self.handlers.push(handler);
    }

    pub fn set_level(&mut self, level: LogLevel) {
        self.level = level;
    }

    pub fn is_enabled(&self, level: &LogLevel) -> bool {
        level.to_int() >= self.level.to_int()
    }

    pub fn start_async_processing(&mut self) {
        let (sender, receiver): (Sender<LogRecord>, Receiver<LogRecord>) = unbounded();
        let handlers = self.handlers.clone();

        thread::spawn(move || {
            for record in receiver {
                for handler in &handlers {
                    handler.handle(&record);
                }
            }
        });

        self.sender = Some(sender);
    }

    pub fn log(&self, level: LogLevel, message: String, module: String, line: u32) {
        self.log_with_extra(level, message, module, line, HashMap::new());
    }

    pub fn log_with_extra(
        &self,
        level: LogLevel,
        message: String,
        module: String,
        line: u32,
        extra: HashMap<String, String>,
    ) {
        if !self.is_enabled(&level) {
            return;
        }

        let record = LogRecord::new(level, message, module, line).with_extra(extra);

        if let Some(ref sender) = self.sender {
            if let Err(_) = sender.try_send(record.clone()) {
                // If async queue is full, handle synchronously
                for handler in &self.handlers {
                    handler.handle(&record);
                }
            }
        } else {
            // Synchronous handling
            for handler in &self.handlers {
                handler.handle(&record);
            }
        }
    }

    pub fn debug(&self, message: String, module: String, line: u32) {
        self.log(LogLevel::Debug, message, module, line);
    }

    pub fn info(&self, message: String, module: String, line: u32) {
        self.log(LogLevel::Info, message, module, line);
    }

    pub fn info_with_extra(
        &self,
        message: String,
        module: String,
        line: u32,
        extra: HashMap<String, String>,
    ) {
        self.log_with_extra(LogLevel::Info, message, module, line, extra);
    }

    pub fn warn(&self, message: String, module: String, line: u32) {
        self.log(LogLevel::Warn, message, module, line);
    }

    pub fn error(&self, message: String, module: String, line: u32) {
        self.log(LogLevel::Error, message, module, line);
    }

    pub fn critical(&self, message: String, module: String, line: u32) {
        self.log(LogLevel::Critical, message, module, line);
    }
}

// Global logger instance
static GLOBAL_LOGGER: OnceLock<Arc<Mutex<Logger>>> = OnceLock::new();

pub fn get_logger() -> Arc<Mutex<Logger>> {
    GLOBAL_LOGGER.get_or_init(|| {
        let logger = Logger::new(LogLevel::Info);
        Arc::new(Mutex::new(logger))
    }).clone()
}

#[pyfunction]
pub fn configure_logger(
    log_file: Option<String>,
    level: String,
    log_format: String,
    log_to_file: bool,
    max_bytes: u64,
    backup_count: u32,
) -> PyResult<()> {
    let log_level = LogLevel::from_str(&level);
    let logger_arc = get_logger();
    let mut logger = logger_arc.lock();

    // Clear existing handlers
    logger.handlers.clear();
    logger.set_level(log_level.clone());

    // Create console handler
    let formatter: Box<dyn Formatter> = if log_format == "json" {
        Box::new(JsonFormatter::new())
    } else {
        Box::new(TextFormatter::new())
    };

    let console_handler = Arc::new(ConsoleHandler::new(log_level.clone(), formatter));
    logger.add_handler(console_handler);

    // Create file handler if needed
    if log_to_file {
        let file_path = log_file.unwrap_or_else(|| "velithon.log".to_string());
        let json_formatter = Box::new(JsonFormatter::new());
        
        match FileHandler::new(file_path, log_level, json_formatter, max_bytes, backup_count) {
            Ok(file_handler) => {
                logger.add_handler(Arc::new(file_handler));
            }
            Err(e) => {
                eprintln!("Failed to create file handler: {}", e);
            }
        }
    }

    // Start async processing
    logger.start_async_processing();

    Ok(())
}

#[pyfunction]
pub fn log_debug(message: String, module: String, line: u32) -> PyResult<()> {
    let logger = get_logger();
    let logger = logger.lock();
    logger.debug(message, module, line);
    Ok(())
}

#[pyfunction]
pub fn log_debug_with_extra(
    message: String,
    module: String,
    line: u32,
    extra: HashMap<String, String>,
) -> PyResult<()> {
    let logger = get_logger();
    let logger = logger.lock();
    logger.log_with_extra(LogLevel::Debug, message, module, line, extra);
    Ok(())
}

#[pyfunction]
pub fn log_info(message: String, module: String, line: u32) -> PyResult<()> {
    let logger = get_logger();
    let logger = logger.lock();
    logger.info(message, module, line);
    Ok(())
}

#[pyfunction]
pub fn log_info_with_extra(
    message: String,
    module: String,
    line: u32,
    extra: HashMap<String, String>,
) -> PyResult<()> {
    let logger = get_logger();
    let logger = logger.lock();
    logger.info_with_extra(message, module, line, extra);
    Ok(())
}

#[pyfunction]
pub fn log_warn(message: String, module: String, line: u32) -> PyResult<()> {
    let logger = get_logger();
    let logger = logger.lock();
    logger.warn(message, module, line);
    Ok(())
}

#[pyfunction]
pub fn log_warn_with_extra(
    message: String,
    module: String,
    line: u32,
    extra: HashMap<String, String>,
) -> PyResult<()> {
    let logger = get_logger();
    let logger = logger.lock();
    logger.log_with_extra(LogLevel::Warn, message, module, line, extra);
    Ok(())
}

#[pyfunction]
pub fn log_error(message: String, module: String, line: u32) -> PyResult<()> {
    let logger = get_logger();
    let logger = logger.lock();
    logger.error(message, module, line);
    Ok(())
}

#[pyfunction]
pub fn log_error_with_extra(
    message: String,
    module: String,
    line: u32,
    extra: HashMap<String, String>,
) -> PyResult<()> {
    let logger = get_logger();
    let logger = logger.lock();
    logger.log_with_extra(LogLevel::Error, message, module, line, extra);
    Ok(())
}

#[pyfunction]
pub fn log_critical(message: String, module: String, line: u32) -> PyResult<()> {
    let logger = get_logger();
    let logger = logger.lock();
    logger.critical(message, module, line);
    Ok(())
}

#[pyfunction]
pub fn log_critical_with_extra(
    message: String,
    module: String,
    line: u32,
    extra: HashMap<String, String>,
) -> PyResult<()> {
    let logger = get_logger();
    let logger = logger.lock();
    logger.log_with_extra(LogLevel::Critical, message, module, line, extra);
    Ok(())
}

#[pyfunction]
pub fn is_enabled_for(level: String) -> PyResult<bool> {
    let log_level = LogLevel::from_str(&level);
    let logger = get_logger();
    let logger = logger.lock();
    Ok(logger.is_enabled(&log_level))
}

pub fn register_logging(_py: Python, m: &Bound<PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(configure_logger, m)?)?;
    m.add_function(wrap_pyfunction!(log_debug, m)?)?;
    m.add_function(wrap_pyfunction!(log_debug_with_extra, m)?)?;
    m.add_function(wrap_pyfunction!(log_info, m)?)?;
    m.add_function(wrap_pyfunction!(log_info_with_extra, m)?)?;
    m.add_function(wrap_pyfunction!(log_warn, m)?)?;
    m.add_function(wrap_pyfunction!(log_warn_with_extra, m)?)?;
    m.add_function(wrap_pyfunction!(log_error, m)?)?;
    m.add_function(wrap_pyfunction!(log_error_with_extra, m)?)?;
    m.add_function(wrap_pyfunction!(log_critical, m)?)?;
    m.add_function(wrap_pyfunction!(log_critical_with_extra, m)?)?;
    m.add_function(wrap_pyfunction!(is_enabled_for, m)?)?;
    Ok(())
}
