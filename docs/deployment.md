# Documentation Deployment Guide

This guide explains how to build and deploy the Velithon documentation using MkDocs.

## 📋 Prerequisites

- Python 3.10+
- Git
- MkDocs and plugins (installed via setup script)

## 🚀 Local Development

### 1. Initial Setup

Run the setup script to install all dependencies and configure the documentation:

```bash
./setup_docs.sh
```

### 2. Start Development Server

```bash
mkdocs serve
```

The documentation will be available at `http://localhost:8000` with auto-reload on file changes.

### 3. Development with Custom Port

```bash
mkdocs serve --dev-addr 0.0.0.0:8080
```

## 🏗️ Building Documentation

### Build for Production

```bash
mkdocs build
```

This creates a `site/` directory with static HTML files ready for deployment.

### Clean Build

```bash
mkdocs build --clean
```

Removes the previous build before creating a new one.

## 🌐 Deployment Options

### 1. GitHub Pages (Recommended)

The repository includes a GitHub Actions workflow that automatically deploys documentation to GitHub Pages when changes are pushed to the main branch.

**Setup:**

1. Enable GitHub Pages in repository settings
2. Set source to "GitHub Actions"
3. Push changes to main branch
4. Documentation will be available at `https://[username].github.io/[repository]`

### 2. Manual GitHub Pages Deployment

```bash
mkdocs gh-deploy
```

This builds the documentation and pushes it to the `gh-pages` branch.

### 3. Netlify Deployment

**Build Command:** `mkdocs build`
**Publish Directory:** `site`

### 4. Vercel Deployment

Create `vercel.json`:

```json
{
  "builds": [
    {
      "src": "mkdocs.yml",
      "use": "@vercel/static-build",
      "config": {
        "distDir": "site"
      }
    }
  ],
  "buildCommand": "pip install -r requirements-docs.txt && mkdocs build"
}
```

### 5. Docker Deployment

```dockerfile
FROM python:3.12-slim

WORKDIR /docs

COPY requirements-docs.txt .
RUN pip install -r requirements-docs.txt

COPY . .
RUN mkdocs build

FROM nginx:alpine
COPY --from=0 /docs/site /usr/share/nginx/html
```

## 📊 Documentation Analytics

The documentation includes Google Analytics support. Set the `GOOGLE_ANALYTICS_KEY` environment variable or update `mkdocs.yml`:

```yaml
extra:
  analytics:
    provider: google
    property: G-XXXXXXXXXX
```

## 🔧 Customization

### Custom CSS

Add custom styles to `docs/stylesheets/extra.css`. The file is already included in the MkDocs configuration.

### Custom JavaScript

Add custom scripts to `docs/javascripts/`. Update `mkdocs.yml` to include them:

```yaml
extra_javascript:
  - javascripts/custom.js
```

### Custom Templates

Override Material theme templates by creating files in `overrides/` directory.

## 🚨 Troubleshooting

### Common Issues

**1. Plugin not found**
```bash
pip install mkdocs-[plugin-name]
```

**2. Theme not found**
```bash
pip install mkdocs-material
```

**3. Build fails with git warnings**
```bash
git init
git add .
git commit -m "Initial commit"
```

**4. Permission denied on deployment**
```bash
chmod +x setup_docs.sh
```

### Performance Optimization

**1. Optimize images**
- Use WebP format for images
- Compress images before adding to docs
- Use appropriate image sizes

**2. Minimize build time**
- Use `--dirty` flag for incremental builds during development:
```bash
mkdocs serve --dirty
```

**3. Enable search optimization**
The configuration already includes optimized search settings.

## 📝 Content Guidelines

### Markdown Best Practices

1. **Use proper headings hierarchy** (H1 → H2 → H3)
2. **Include code language** in fenced code blocks
3. **Use admonitions** for notes, tips, and warnings
4. **Add alt text** to images
5. **Use relative links** between documentation pages

### Code Examples

Always include complete, runnable examples:

```python title="example.py"
from velithon import Velithon
from velithon.responses import JSONResponse

app = Velithon()

@app.get("/")
async def root():
    return JSONResponse({"message": "Hello, Velithon!"})
```

### Admonitions

Use Material Design admonitions for better content organization:

```markdown
!!! note "Performance Tip"
    Velithon with Granian achieves ~70,000 requests/second.

!!! warning "Important"
    Always use HTTPS in production.

!!! tip "Pro Tip"
    Use dependency injection for better code organization.
```

## 🔄 Maintenance

### Regular Updates

1. **Update dependencies** monthly:
```bash
pip install --upgrade mkdocs mkdocs-material
```

2. **Review broken links** using:
```bash
mkdocs build --strict
```

3. **Update content** based on framework changes

4. **Monitor analytics** for popular content

### Version Management

For versioned documentation:

1. Create version-specific directories: `docs/v1.0/`, `docs/v2.0/`
2. Update navigation in `mkdocs.yml`
3. Use mike for version management:

```bash
pip install mike
mike deploy v1.0 latest
mike set-default latest
```

## 📈 Success Metrics

Track documentation success with:

- **Page views** and **time on page**
- **Search queries** and **results clicks**
- **User feedback** and **GitHub issues**
- **Conversion rates** from docs to downloads

---

**Ready to contribute to Velithon documentation?** Start with the [Getting Started](getting-started/index.md) guide!
