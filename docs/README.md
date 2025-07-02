# Velithon Documentation

> **High-performance RSGI web framework for Python** - Comprehensive documentation built with MkDocs Material

## 🚀 Quick Start

### Local Development

```bash
# Install dependencies
./setup_docs.sh

# Start development server
mkdocs serve

# Open browser to http://localhost:8000
```

### Build Documentation

```bash
# Build static site
mkdocs build

# Clean build
mkdocs build --clean
```

## 📚 Documentation Structure

```
docs/
├── index.md                    # Homepage
├── getting-started/            # Getting Started Guide
│   ├── index.md               # Overview
│   ├── installation.md        # Installation guide
│   ├── quick-start.md         # Quick start tutorial
│   ├── first-application.md   # Comprehensive tutorial
│   └── project-structure.md   # Best practices
├── stylesheets/               # Custom CSS
├── javascripts/               # Custom JavaScript
└── includes/                  # Reusable snippets
```

## ✨ Features

- **📱 Responsive Design** - Mobile-first Material Design
- **🔍 Advanced Search** - Full-text search with highlighting
- **🎨 Code Highlighting** - Syntax highlighting for 100+ languages
- **📊 Mermaid Diagrams** - Support for flowcharts and diagrams
- **🔗 Cross-references** - Smart internal linking
- **📈 Analytics** - Google Analytics integration
- **🚀 Performance** - Optimized for speed and SEO

## 🛠️ Technology Stack

- **[MkDocs](https://www.mkdocs.org/)** - Static site generator
- **[Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)** - Beautiful theme
- **[Mermaid](https://mermaid-js.github.io/)** - Diagram support
- **[Python-Markdown](https://python-markdown.github.io/)** - Markdown processing

## 🚀 Deployment

### GitHub Pages (Recommended)

The repository includes automated GitHub Actions deployment:

1. Push changes to `main` branch
2. GitHub Actions builds and deploys automatically
3. Available at `https://[username].github.io/[repository]`

### Manual Deployment

```bash
# Deploy to GitHub Pages
mkdocs gh-deploy

# Or build and upload to any static host
mkdocs build
# Upload site/ directory to your hosting provider
```

## 📝 Writing Guidelines

### Markdown Best Practices

1. **Use semantic headings** (H1 → H2 → H3)
2. **Include language in code blocks**:
   ```python title="example.py"
   from velithon import Velithon
   ```
3. **Use admonitions** for important info:
   ```markdown
   !!! tip "Performance"
       Velithon achieves 110,000+ req/s with RSGI
   ```
4. **Add proper alt text** to images
5. **Use relative links** between pages

### Content Structure

- **Start with overview** - What and why
- **Provide examples** - Show, don't just tell
- **Include best practices** - How to do it right
- **Add troubleshooting** - Common issues and solutions
- **Link to related content** - Help users discover more

## 🔧 Configuration

Key configuration in `mkdocs.yml`:

```yaml
site_name: Velithon Documentation
theme:
  name: material
  features:
    - navigation.instant    # SPA-like navigation
    - navigation.tracking   # URL updates
    - search.highlight      # Search highlighting
    - content.code.copy     # Copy code buttons
```

## 🎨 Customization

### Custom CSS

Add styles to `docs/stylesheets/extra.css`:

```css
/* Custom Velithon branding */
.velithon-brand {
    background: linear-gradient(45deg, #667eea, #764ba2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
```

### Custom JavaScript

Add scripts to `docs/javascripts/`:

```javascript
// Custom analytics or interactive features
document.addEventListener('DOMContentLoaded', function() {
    // Your custom code here
});
```

## 📊 Analytics

Configure Google Analytics in `mkdocs.yml`:

```yaml
extra:
  analytics:
    provider: google
    property: G-XXXXXXXXXX
```

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b docs/feature-name`
3. **Write your documentation**
4. **Test locally**: `mkdocs serve`
5. **Submit a pull request**

### Documentation Standards

- **Clear and concise** - Get to the point quickly
- **Comprehensive examples** - Include working code
- **Cross-platform** - Consider all operating systems
- **Beginner-friendly** - Don't assume prior knowledge
- **Up-to-date** - Keep pace with framework changes

## 🐛 Troubleshooting

### Common Issues

**Build fails:**
```bash
# Check for missing dependencies
pip install -r requirements-docs.txt

# Validate configuration
mkdocs build --strict
```

**Broken links:**
```bash
# Use strict mode to catch issues
mkdocs build --strict --verbose
```

**Slow builds:**
```bash
# Use dirty mode for development
mkdocs serve --dirty
```

## 📈 Performance

### Optimization Tips

1. **Optimize images** - Use WebP format, appropriate sizes
2. **Minimize plugins** - Only use what you need
3. **Enable caching** - Configure CDN for production
4. **Monitor metrics** - Track build times and page load

### Build Performance

- **Local development**: ~1s with `--dirty` flag
- **Full build**: ~3-5s for complete documentation
- **GitHub Pages**: ~2-3 minutes including deployment

## 📞 Support

- **Documentation Issues**: [GitHub Issues](https://github.com/DVNghiem/Velithon/issues)
- **Framework Questions**: [GitHub Discussions](https://github.com/DVNghiem/Velithon/discussions)
- **MkDocs Help**: [MkDocs Documentation](https://www.mkdocs.org/)

---

**Ready to contribute?** Check out the [deployment guide](docs/DEPLOYMENT.md) to get started!
