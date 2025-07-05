# Export Documentation

Learn how to export your OpenAPI documentation in various formats for external use, integration, and distribution.

## Overview

Velithon allows you to export your API documentation in multiple formats, making it easy to share with team members, integrate with other tools, or publish for external developers.

## Export OpenAPI JSON Schema

```python
from velithon import Velithon
import json

app = Velithon()

# Add your routes here
@app.get("/users")
async def get_users():
    """Get all users"""
    return []

# Export OpenAPI schema
def export_openapi_schema(filename="openapi.json"):
    """Export the OpenAPI schema to a JSON file"""
    schema = app.openapi()
    
    with open(filename, "w") as f:
        json.dump(schema, f, indent=2)
    
    print(f"OpenAPI schema exported to {filename}")

# Export when running the script
if __name__ == "__main__":
    export_openapi_schema()
```

## Export to YAML Format

```python
import yaml

def export_openapi_yaml(filename="openapi.yaml"):
    """Export the OpenAPI schema to a YAML file"""
    schema = app.openapi()
    
    with open(filename, "w") as f:
        yaml.dump(schema, f, default_flow_style=False, indent=2)
    
    print(f"OpenAPI schema exported to {filename}")

# Usage
export_openapi_yaml()
```

## Command Line Export

```python
import sys
import argparse

def export_documentation():
    """Command line tool to export documentation"""
    parser = argparse.ArgumentParser(description="Export API documentation")
    parser.add_argument("--format", choices=["json", "yaml"], default="json",
                       help="Export format (default: json)")
    parser.add_argument("--output", "-o", default="openapi",
                       help="Output filename (without extension)")
    parser.add_argument("--pretty", action="store_true",
                       help="Pretty print the output")
    
    args = parser.parse_args()
    
    schema = app.openapi()
    
    if args.format == "json":
        filename = f"{args.output}.json"
        with open(filename, "w") as f:
            if args.pretty:
                json.dump(schema, f, indent=2, ensure_ascii=False)
            else:
                json.dump(schema, f)
    else:  # yaml
        filename = f"{args.output}.yaml"
        with open(filename, "w") as f:
            yaml.dump(schema, f, default_flow_style=False, indent=2)
    
    print(f"Documentation exported to {filename}")

if __name__ == "__main__":
    export_documentation()
```

## Export HTML Documentation

```python
from velithon.openapi import get_swagger_ui_html, get_redoc_html

def export_html_docs():
    """Export documentation as standalone HTML files"""
    
    # Export Swagger UI
    swagger_html = get_swagger_ui_html(
        openapi_url="openapi.json",
        title="API Documentation",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png"
    )
    
    with open("swagger-ui.html", "w") as f:
        f.write(swagger_html.body.decode())
    
    # Export ReDoc
    redoc_html = get_redoc_html(
        openapi_url="openapi.json",
        title="API Reference"
    )
    
    with open("redoc.html", "w") as f:
        f.write(redoc_html.body.decode())
    
    print("HTML documentation exported to swagger-ui.html and redoc.html")

export_html_docs()
```

## Automated Export Script

```python
#!/usr/bin/env python3
"""
Automated documentation export script
"""
import os
import json
import yaml
from datetime import datetime
from pathlib import Path

def export_all_formats(output_dir="docs_export"):
    """Export documentation in all available formats"""
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    # Get OpenAPI schema
    schema = app.openapi()
    
    # Add export metadata
    schema["info"]["x-exported-at"] = datetime.utcnow().isoformat()
    schema["info"]["x-exported-by"] = "Velithon Documentation Exporter"
    
    # Export JSON
    json_file = os.path.join(output_dir, "openapi.json")
    with open(json_file, "w") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    
    # Export YAML
    yaml_file = os.path.join(output_dir, "openapi.yaml")
    with open(yaml_file, "w") as f:
        yaml.dump(schema, f, default_flow_style=False, indent=2)
    
    # Export minified JSON
    minified_file = os.path.join(output_dir, "openapi.min.json")
    with open(minified_file, "w") as f:
        json.dump(schema, f, separators=(',', ':'))
    
    # Create index file
    index_content = f"""
# API Documentation Export

Generated on: {datetime.utcnow().isoformat()}

## Available Formats

- [OpenAPI JSON](openapi.json) - Full OpenAPI 3.0 specification
- [OpenAPI YAML](openapi.yaml) - YAML format for better readability
- [Minified JSON](openapi.min.json) - Compressed JSON for production use

## Usage

These files can be imported into:
- Postman (Import > OpenAPI 3.0)
- Insomnia (Import from URL or File)
- API Gateway services
- Code generation tools
- Documentation platforms
"""
    
    with open(os.path.join(output_dir, "README.md"), "w") as f:
        f.write(index_content)
    
    print(f"Documentation exported to {output_dir}/")
    print(f"- OpenAPI JSON: {json_file}")
    print(f"- OpenAPI YAML: {yaml_file}")
    print(f"- Minified JSON: {minified_file}")

# Run export
export_all_formats()
```

## Integration with CI/CD

```yaml
# .github/workflows/docs.yml
name: Export Documentation

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  export-docs:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Export documentation
      run: |
        python export_docs.py
    
    - name: Upload artifacts
      uses: actions/upload-artifact@v2
      with:
        name: api-documentation
        path: docs_export/
    
    - name: Deploy to GitHub Pages
      if: github.ref == 'refs/heads/main'
      uses: peaceiris/actions-gh-pages@v3
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_dir: docs_export/
```

## Makefile Integration

```makefile
# Makefile
.PHONY: export-docs clean-docs

export-docs:
	@echo "Exporting API documentation..."
	python export_docs.py
	@echo "Documentation exported to docs_export/"

export-json:
	@echo "Exporting OpenAPI JSON..."
	python -c "from main import app; import json; json.dump(app.openapi(), open('openapi.json', 'w'), indent=2)"

export-yaml:
	@echo "Exporting OpenAPI YAML..."
	python -c "from main import app; import yaml; yaml.dump(app.openapi(), open('openapi.yaml', 'w'), default_flow_style=False)"

clean-docs:
	rm -rf docs_export/
	rm -f openapi.json openapi.yaml

validate-docs:
	@echo "Validating OpenAPI schema..."
	swagger-codegen validate -i openapi.json
```

## Postman Collection Export

```python
def export_postman_collection():
    """Convert OpenAPI schema to Postman collection format"""
    schema = app.openapi()
    
    postman_collection = {
        "info": {
            "name": schema["info"]["title"],
            "description": schema["info"]["description"],
            "version": schema["info"]["version"],
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "item": []
    }
    
    # Convert paths to Postman requests
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            request_item = {
                "name": operation.get("summary", f"{method.upper()} {path}"),
                "request": {
                    "method": method.upper(),
                    "url": f"{{{{base_url}}}}{path}",
                    "description": operation.get("description", "")
                }
            }
            postman_collection["item"].append(request_item)
    
    # Save collection
    with open("postman_collection.json", "w") as f:
        json.dump(postman_collection, f, indent=2)
    
    print("Postman collection exported to postman_collection.json")
```

## Best Practices

1. **Version your exports** with timestamps or version numbers
2. **Include metadata** about the export process
3. **Validate exported schemas** before distribution
4. **Automate exports** in your CI/CD pipeline
5. **Provide multiple formats** for different use cases
6. **Document export usage** for team members
7. **Keep exports up to date** with API changes
