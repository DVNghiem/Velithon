# GitHub Copilot Custom Instructions for Velithon Framework

## Framework Overview
Velithon is a high-performance web framework built on top of Granian RSGI, leveraging the combined power of Python and Rust to deliver maximum performance. The framework is designed with speed as the primary criterion, utilizing Rust's performance capabilities while maintaining Python's flexibility.

## Code Standards and Guidelines

### Language and Documentation
- **All code comments must be written in English**
- All documentation, docstrings, and inline comments should be in English
- Use clear, descriptive variable and function names in English

### File Management and Optimization
- **Never create new files with "optimize" or similar suffixes** (e.g., avoid `login_optimize.py`)
- Always modify existing files and improve the logic in place
- Before implementing any feature, **thoroughly review the entire source code** to understand existing patterns and avoid duplication
- Eliminate redundant code and consolidate similar functionalities

### Performance Priority
- **Speed is the top priority** - always choose the most performant solution
- **Prioritize Rust implementation first**, then load it into Python for optimal performance
- Leverage Rust's strengths for CPU-intensive operations, data processing, and core algorithms
- Use Python for high-level orchestration and API interfaces

### Development Workflow
1. **Rust-First Approach**: Implement core functionality in Rust when possible
2. **Python Integration**: Create Python bindings using PyO3 for seamless integration
3. **Build Process**: Always use `maturin develop` for building Rust components
4. **Code Quality**: Follow Ruff standards for Python code formatting and linting

### Testing Requirements
- **Comprehensive testing is mandatory** for all features
- Implement both functional tests and real-world integration tests
- **Create test servers** to validate functionality in realistic scenarios
- Test the interaction between Rust and Python components thoroughly
- Avoid merging code that hasn't been tested in a server environment

### Code Quality Standards
- **Follow Ruff standards** for Python code formatting, linting, and style
- Minimize unused variable declarations
- Use type hints consistently
- Maintain clean, readable code structure
- Follow async/await patterns for non-blocking operations

### Documentation Maintenance
- **Update documentation** whenever implementing new features or fixing bugs
- Keep README.md, API documentation, and inline docs current
- Document both Python and Rust components
- Include performance benchmarks when relevant

## Architecture Guidelines

### Rust Components
- Use Rust for:
  - Core performance-critical algorithms
  - Data processing and transformation
  - Network operations and protocol handling
  - Memory-intensive operations
  - Concurrent/parallel processing tasks

### Python Components
- Use Python for:
  - API endpoint definitions and routing
  - High-level application logic
  - Integration with external services
  - Configuration management
  - Development tooling

### Integration Patterns
- Use PyO3 for creating Python bindings to Rust code
- Implement proper error handling between Rust and Python layers
- Ensure thread safety when sharing data between languages
- Use appropriate serialization for data exchange

## Build and Development
- Always use `maturin develop` for local development builds
- Use `maturin build --release` for production builds
- Maintain both Cargo.toml (Rust) and pyproject.toml (Python) configurations
- Ensure compatibility across Python versions 3.10+

## Performance Considerations
- Profile code regularly to identify bottlenecks
- Benchmark new features against existing implementations
- Consider memory usage and allocation patterns
- Optimize for both latency and throughput
- Use appropriate data structures for the task at hand

## Error Handling
- Implement comprehensive error handling in both Rust and Python layers
- Use appropriate logging levels for different types of events
- Provide meaningful error messages for debugging
- Handle async operation failures gracefully

## Security and Best Practices
- Validate all inputs at the boundary
- Use safe Rust practices to prevent memory issues
- Implement proper authentication and authorization patterns
- Follow security best practices for web applications
- Regular dependency updates and vulnerability scanning

## Code Review Checklist
Before submitting code, ensure:
- [ ] Rust components are implemented where performance matters
- [ ] All code is commented in English
- [ ] No unnecessary file duplication or "optimize" variants
- [ ] Comprehensive tests are included
- [ ] Documentation is updated
- [ ] Ruff standards are followed
- [ ] No unused variables or imports
- [ ] Performance impact has been considered
- [ ] Integration between Rust and Python works correctly

## Framework-Specific Patterns
- Extend the HTTPEndpoint class for new API endpoints
- Use the routing system consistently
- Leverage the built-in middleware capabilities
- Utilize the async/await patterns throughout
- Make use of the Rust-powered core for heavy lifting
- Follow the established project structure and naming conventions

Remember: The goal is to create a blazingly fast web framework that combines the best of both Rust and Python while maintaining clean, maintainable, and well-documented code.