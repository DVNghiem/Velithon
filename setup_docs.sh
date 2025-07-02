#!/bin/bash

# Velithon Documentation Setup Script
# This script sets up MkDocs with Material theme for Velithon framework documentation

set -e

echo "🚀 Setting up Velithon Documentation with MkDocs..."

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ] || [ ! -d "velithon" ]; then
    echo "❌ Please run this script from the Velithon project root directory"
    exit 1
fi

# Install MkDocs and dependencies
echo "📦 Installing MkDocs and dependencies..."
pip install -q mkdocs mkdocs-material mkdocs-mermaid2-plugin mkdocs-awesome-pages-plugin mkdocs-git-revision-date-localized-plugin

# Create additional required files
echo "📁 Creating additional documentation files..."

# Create CSS directory and custom styles
mkdir -p docs/stylesheets
cat > docs/stylesheets/extra.css << 'EOF'
/* Custom styles for Velithon documentation */

/* Improve code block appearance */
.highlight {
    border-radius: 6px;
}

/* Custom admonition colors */
.md-typeset .admonition.note {
    border-left-color: #448aff;
}

.md-typeset .admonition.tip {
    border-left-color: #00c853;
}

.md-typeset .admonition.warning {
    border-left-color: #ff9100;
}

/* Performance highlight boxes */
.performance-box {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 1rem;
    border-radius: 8px;
    margin: 1rem 0;
}

/* Feature grid styling */
.grid.cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1rem;
    margin: 1rem 0;
}

.grid.cards > div {
    border: 1px solid var(--md-default-fg-color--lightest);
    border-radius: 8px;
    padding: 1rem;
    transition: box-shadow 0.2s ease;
}

.grid.cards > div:hover {
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

/* Velithon branding */
.velithon-brand {
    background: linear-gradient(45deg, #667eea, #764ba2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: bold;
}
EOF

# Create JavaScript directory and MathJax config
mkdir -p docs/javascripts
cat > docs/javascripts/mathjax.js << 'EOF'
window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"]],
    processEscapes: true,
    processEnvironments: true
  },
  options: {
    ignoreHtmlClass: ".*|",
    processHtmlClass: "arithmatex"
  }
};

document$.subscribe(() => { 
  MathJax.startup.output.clearCache()
  MathJax.typesetClear()
  MathJax.texReset()
  MathJax.typesetPromise()
})
EOF

# Create includes directory for snippets
mkdir -p docs/includes
cat > docs/includes/mkdocs.md << 'EOF'
<!-- Common snippets and abbreviations for Velithon documentation -->

*[RSGI]: Rust Server Gateway Interface
*[ASGI]: Asynchronous Server Gateway Interface  
*[API]: Application Programming Interface
*[HTTP]: Hypertext Transfer Protocol
*[JSON]: JavaScript Object Notation
*[JWT]: JSON Web Token
*[CRUD]: Create, Read, Update, Delete
*[CLI]: Command Line Interface
*[SSL]: Secure Sockets Layer
*[TLS]: Transport Layer Security
*[CORS]: Cross-Origin Resource Sharing
*[SSE]: Server-Sent Events
*[DI]: Dependency Injection
*[ORM]: Object-Relational Mapping
*[WebSocket]: WebSocket Protocol
EOF

# Create GitHub Actions workflow for documentation deployment
mkdir -p .github/workflows
cat > .github/workflows/docs.yml << 'EOF'
name: Deploy Documentation

on:
  push:
    branches: [ main ]
    paths:
      - 'docs/**'
      - 'mkdocs.yml'
      - '.github/workflows/docs.yml'
  pull_request:
    branches: [ main ]
    paths:
      - 'docs/**'
      - 'mkdocs.yml'

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install mkdocs mkdocs-material mkdocs-mermaid2-plugin mkdocs-awesome-pages-plugin mkdocs-git-revision-date-localized-plugin
      
      - name: Build documentation
        run: mkdocs build --clean
      
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: site

  deploy:
    if: github.ref == 'refs/heads/main'
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    needs: build
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
EOF

echo "✅ MkDocs setup completed successfully!"
echo ""
echo "🔧 Next steps:"
echo "1. Start the development server: mkdocs serve"
echo "2. Open your browser to: http://localhost:8000"
echo "3. Edit documentation files in the docs/ directory"
echo "4. Build for production: mkdocs build"
echo "5. Deploy to GitHub Pages: git push origin main"
echo ""
echo "📚 Documentation structure:"
echo "- docs/              - Documentation source files"
echo "- docs/stylesheets/  - Custom CSS styles"
echo "- docs/javascripts/  - Custom JavaScript"
echo "- docs/includes/     - Reusable snippets"
echo "- mkdocs.yml         - MkDocs configuration"
echo ""
echo "🎉 Happy documenting with Velithon!"
