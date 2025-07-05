/**
 * Theme and Visual Enhancements for Velithon Documentation
 * Provides dynamic theming, particle effects, and visual improvements
 */

// Theme manager
class ThemeManager {
    constructor() {
        this.themes = {
            velithon: {
                primary: '#667eea',
                secondary: '#764ba2',
                accent: '#00c853',
                background: '#ffffff',
                text: '#333333'
            },
            dark: {
                primary: '#667eea',
                secondary: '#764ba2',
                accent: '#00c853',
                background: '#1a1a1a',
                text: '#ffffff'
            },
            high_contrast: {
                primary: '#000000',
                secondary: '#ffffff',
                accent: '#ffff00',
                background: '#ffffff',
                text: '#000000'
            }
        };
        
        this.currentTheme = 'velithon';
        this.init();
    }
    
    init() {
        this.createThemeControls();
        this.loadSavedTheme();
        this.initParticleEffects();
        this.initDynamicBackgrounds();
    }
    
    createThemeControls() {
        const themePanel = document.createElement('div');
        themePanel.className = 'theme-panel';
        themePanel.innerHTML = `
            <button class="theme-toggle" title="Theme Settings">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="5"></circle>
                    <line x1="12" y1="1" x2="12" y2="3"></line>
                    <line x1="12" y1="21" x2="12" y2="23"></line>
                    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
                    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
                    <line x1="1" y1="12" x2="3" y2="12"></line>
                    <line x1="21" y1="12" x2="23" y2="12"></line>
                    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
                    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
                </svg>
            </button>
            <div class="theme-options">
                <button class="theme-option" data-theme="velithon">Velithon</button>
                <button class="theme-option" data-theme="dark">Dark</button>
                <button class="theme-option" data-theme="high_contrast">High Contrast</button>
                <div class="theme-feature">
                    <label>
                        <input type="checkbox" id="particles-toggle"> Particle Effects
                    </label>
                </div>
                <div class="theme-feature">
                    <label>
                        <input type="checkbox" id="animations-toggle" checked> Animations
                    </label>
                </div>
            </div>
        `;
        
        document.body.appendChild(themePanel);
        this.bindThemeEvents(themePanel);
    }
    
    bindThemeEvents(panel) {
        const toggle = panel.querySelector('.theme-toggle');
        const options = panel.querySelector('.theme-options');
        
        toggle.addEventListener('click', () => {
            options.classList.toggle('visible');
        });
        
        // Theme selection
        panel.querySelectorAll('.theme-option').forEach(option => {
            option.addEventListener('click', () => {
                const theme = option.getAttribute('data-theme');
                this.setTheme(theme);
                options.classList.remove('visible');
            });
        });
        
        // Feature toggles
        const particlesToggle = panel.querySelector('#particles-toggle');
        particlesToggle.addEventListener('change', () => {
            this.toggleParticles(particlesToggle.checked);
        });
        
        const animationsToggle = panel.querySelector('#animations-toggle');
        animationsToggle.addEventListener('change', () => {
            this.toggleAnimations(animationsToggle.checked);
        });
    }
    
    setTheme(themeName) {
        if (!this.themes[themeName]) return;
        
        this.currentTheme = themeName;
        const theme = this.themes[themeName];
        
        // Update CSS custom properties
        document.documentElement.style.setProperty('--velithon-primary', theme.primary);
        document.documentElement.style.setProperty('--velithon-secondary', theme.secondary);
        document.documentElement.style.setProperty('--velithon-accent', theme.accent);
        document.documentElement.style.setProperty('--theme-background', theme.background);
        document.documentElement.style.setProperty('--theme-text', theme.text);
        
        // Update body class
        document.body.className = document.body.className.replace(/theme-\w+/g, '');
        document.body.classList.add(`theme-${themeName}`);
        
        // Save preference
        localStorage.setItem('selectedTheme', themeName);
    }
    
    loadSavedTheme() {
        const savedTheme = localStorage.getItem('selectedTheme');
        if (savedTheme && this.themes[savedTheme]) {
            this.setTheme(savedTheme);
        }
    }
    
    initParticleEffects() {
        this.particleCanvas = document.createElement('canvas');
        this.particleCanvas.className = 'particle-canvas';
        this.particleCanvas.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: -1;
            opacity: 0.1;
        `;
        document.body.appendChild(this.particleCanvas);
        
        this.particles = [];
        this.particleCtx = this.particleCanvas.getContext('2d');
        this.resizeCanvas();
        
        window.addEventListener('resize', () => this.resizeCanvas());
    }
    
    resizeCanvas() {
        this.particleCanvas.width = window.innerWidth;
        this.particleCanvas.height = window.innerHeight;
    }
    
    createParticle() {
        return {
            x: Math.random() * this.particleCanvas.width,
            y: Math.random() * this.particleCanvas.height,
            vx: (Math.random() - 0.5) * 0.5,
            vy: (Math.random() - 0.5) * 0.5,
            radius: Math.random() * 2 + 1,
            opacity: Math.random() * 0.5 + 0.5,
            color: `hsl(${Math.random() * 60 + 220}, 70%, 60%)`
        };
    }
    
    updateParticles() {
        this.particleCtx.clearRect(0, 0, this.particleCanvas.width, this.particleCanvas.height);
        
        this.particles.forEach((particle, index) => {
            particle.x += particle.vx;
            particle.y += particle.vy;
            particle.opacity -= 0.001;
            
            // Wrap around screen
            if (particle.x < 0) particle.x = this.particleCanvas.width;
            if (particle.x > this.particleCanvas.width) particle.x = 0;
            if (particle.y < 0) particle.y = this.particleCanvas.height;
            if (particle.y > this.particleCanvas.height) particle.y = 0;
            
            // Remove faded particles
            if (particle.opacity <= 0) {
                this.particles.splice(index, 1);
                return;
            }
            
            // Draw particle
            this.particleCtx.beginPath();
            this.particleCtx.arc(particle.x, particle.y, particle.radius, 0, Math.PI * 2);
            this.particleCtx.fillStyle = particle.color;
            this.particleCtx.globalAlpha = particle.opacity;
            this.particleCtx.fill();
        });
        
        // Add new particles
        if (this.particles.length < 50 && Math.random() < 0.1) {
            this.particles.push(this.createParticle());
        }
    }
    
    toggleParticles(enabled) {
        if (enabled) {
            this.particleCanvas.style.display = 'block';
            this.animateParticles();
        } else {
            this.particleCanvas.style.display = 'none';
            if (this.particleAnimation) {
                cancelAnimationFrame(this.particleAnimation);
            }
        }
        localStorage.setItem('particlesEnabled', enabled);
    }
    
    animateParticles() {
        this.updateParticles();
        this.particleAnimation = requestAnimationFrame(() => this.animateParticles());
    }
    
    toggleAnimations(enabled) {
        if (enabled) {
            document.body.classList.remove('no-animations');
        } else {
            document.body.classList.add('no-animations');
        }
        localStorage.setItem('animationsEnabled', enabled);
    }
    
    initDynamicBackgrounds() {
        // Create gradient background that changes based on scroll position
        const gradientOverlay = document.createElement('div');
        gradientOverlay.className = 'gradient-overlay';
        gradientOverlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: -2;
            opacity: 0.05;
            background: linear-gradient(45deg, var(--velithon-primary), var(--velithon-secondary));
            transition: opacity 0.3s ease;
        `;
        document.body.appendChild(gradientOverlay);
        
        // Update gradient based on scroll
        let ticking = false;
        window.addEventListener('scroll', () => {
            if (!ticking) {
                requestAnimationFrame(() => {
                    const scrollPercent = window.scrollY / (document.documentElement.scrollHeight - window.innerHeight);
                    const hue = 220 + (scrollPercent * 40);
                    gradientOverlay.style.background = `linear-gradient(45deg, hsl(${hue}, 70%, 60%), hsl(${hue + 20}, 70%, 50%))`;
                    ticking = false;
                });
                ticking = true;
            }
        });
    }
}

// Enhanced code syntax highlighting
class SyntaxHighlighter {
    constructor() {
        this.init();
    }
    
    init() {
        this.enhanceCodeBlocks();
        this.addSyntaxThemes();
    }
    
    enhanceCodeBlocks() {
        const codeBlocks = document.querySelectorAll('pre code');
        codeBlocks.forEach(block => {
            this.addSyntaxHighlighting(block);
        });
    }
    
    addSyntaxHighlighting(block) {
        // Add enhanced syntax highlighting for Python, JavaScript, etc.
        const language = this.detectLanguage(block);
        
        if (language === 'python') {
            this.highlightPython(block);
        } else if (language === 'javascript') {
            this.highlightJavaScript(block);
        } else if (language === 'css') {
            this.highlightCSS(block);
        }
    }
    
    detectLanguage(block) {
        const classes = block.parentElement.className;
        if (classes.includes('python')) return 'python';
        if (classes.includes('javascript') || classes.includes('js')) return 'javascript';
        if (classes.includes('css')) return 'css';
        return 'generic';
    }
    
    highlightPython(block) {
        // Enhanced Python syntax highlighting
        let html = block.innerHTML;
        
        // Keywords
        html = html.replace(/\b(def|class|import|from|if|elif|else|for|while|try|except|finally|with|as|return|yield|break|continue|pass|async|await)\b/g, 
            '<span class="keyword">$1</span>');
        
        // Built-in functions
        html = html.replace(/\b(print|len|range|enumerate|zip|map|filter|sorted|reversed|any|all|sum|min|max|abs|round|int|float|str|list|dict|set|tuple)\b/g, 
            '<span class="builtin">$1</span>');
        
        // Strings
        html = html.replace(/(["`'])((?:\\.|(?!\1)[^\\])*?)\1/g, '<span class="string">$1$2$1</span>');
        
        // Comments
        html = html.replace(/(#.*$)/gm, '<span class="comment">$1</span>');
        
        block.innerHTML = html;
    }
    
    highlightJavaScript(block) {
        // Enhanced JavaScript syntax highlighting
        let html = block.innerHTML;
        
        // Keywords
        html = html.replace(/\b(function|const|let|var|if|else|for|while|do|switch|case|default|break|continue|return|class|extends|constructor|async|await|try|catch|finally|throw|new|this|super|static|import|export|from|default)\b/g, 
            '<span class="keyword">$1</span>');
        
        // Built-in objects
        html = html.replace(/\b(console|window|document|Array|Object|String|Number|Boolean|Date|RegExp|Math|JSON|Promise|setTimeout|setInterval|clearTimeout|clearInterval)\b/g, 
            '<span class="builtin">$1</span>');
        
        block.innerHTML = html;
    }
    
    highlightCSS(block) {
        // Enhanced CSS syntax highlighting
        let html = block.innerHTML;
        
        // Properties
        html = html.replace(/([a-zA-Z-]+)(\s*:)/g, '<span class="property">$1</span>$2');
        
        // Values
        html = html.replace(/(:\s*)([^;{]+)/g, '$1<span class="value">$2</span>');
        
        // Selectors
        html = html.replace(/^([^{]+)(\s*\{)/gm, '<span class="selector">$1</span>$2');
        
        block.innerHTML = html;
    }
    
    addSyntaxThemes() {
        const syntaxStyles = document.createElement('style');
        syntaxStyles.textContent = `
            .keyword { color: #c792ea; font-weight: bold; }
            .builtin { color: #82aaff; }
            .string { color: #c3e88d; }
            .comment { color: #546e7a; font-style: italic; }
            .property { color: #f07178; }
            .value { color: #c3e88d; }
            .selector { color: #ffcb6b; }
            .number { color: #f78c6c; }
            .operator { color: #89ddff; }
        `;
        document.head.appendChild(syntaxStyles);
    }
}

// Interactive documentation features
class InteractiveFeatures {
    constructor() {
        this.init();
    }
    
    init() {
        this.createFloatingActionButton();
        this.initQuickNavigation();
        this.initTableOfContents();
        this.initFeedbackSystem();
    }
    
    createFloatingActionButton() {
        const fab = document.createElement('div');
        fab.className = 'floating-action-button';
        fab.innerHTML = `
            <button class="fab-main">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="3"></circle>
                    <path d="M12 1v6m0 6v6"></path>
                    <path d="M1 12h6m6 0h6"></path>
                </svg>
            </button>
            <div class="fab-menu">
                <button class="fab-option" data-action="scroll-top" title="Back to Top">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 15l-6-6-6 6"></path>
                    </svg>
                </button>
                <button class="fab-option" data-action="toggle-toc" title="Table of Contents">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="8" y1="6" x2="21" y2="6"></line>
                        <line x1="8" y1="12" x2="21" y2="12"></line>
                        <line x1="8" y1="18" x2="21" y2="18"></line>
                        <line x1="3" y1="6" x2="3.01" y2="6"></line>
                        <line x1="3" y1="12" x2="3.01" y2="12"></line>
                        <line x1="3" y1="18" x2="3.01" y2="18"></line>
                    </svg>
                </button>
                <button class="fab-option" data-action="print" title="Print Page">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="6,9 6,2 18,2 18,9"></polyline>
                        <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path>
                        <rect x="6" y="14" width="12" height="8"></rect>
                    </svg>
                </button>
                <button class="fab-option" data-action="share" title="Share Page">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"></path>
                        <polyline points="16,6 12,2 8,6"></polyline>
                        <line x1="12" y1="2" x2="12" y2="15"></line>
                    </svg>
                </button>
            </div>
        `;
        
        document.body.appendChild(fab);
        this.bindFabEvents(fab);
    }
    
    bindFabEvents(fab) {
        const mainButton = fab.querySelector('.fab-main');
        const menu = fab.querySelector('.fab-menu');
        
        mainButton.addEventListener('click', () => {
            fab.classList.toggle('active');
        });
        
        fab.querySelectorAll('.fab-option').forEach(option => {
            option.addEventListener('click', () => {
                const action = option.getAttribute('data-action');
                this.handleFabAction(action);
                fab.classList.remove('active');
            });
        });
        
        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!fab.contains(e.target)) {
                fab.classList.remove('active');
            }
        });
    }
    
    handleFabAction(action) {
        switch (action) {
            case 'scroll-top':
                window.scrollTo({ top: 0, behavior: 'smooth' });
                break;
            case 'toggle-toc':
                this.toggleTableOfContents();
                break;
            case 'print':
                window.print();
                break;
            case 'share':
                this.shareCurrentPage();
                break;
        }
    }
    
    toggleTableOfContents() {
        const toc = document.querySelector('.md-nav--secondary');
        if (toc) {
            toc.classList.toggle('visible');
        }
    }
    
    shareCurrentPage() {
        if (navigator.share) {
            navigator.share({
                title: document.title,
                text: 'Check out this Velithon documentation page',
                url: window.location.href
            });
        } else {
            // Fallback: copy to clipboard
            navigator.clipboard.writeText(window.location.href).then(() => {
                this.showNotification('Link copied to clipboard!');
            });
        }
    }
    
    showNotification(message) {
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('visible');
        }, 100);
        
        setTimeout(() => {
            notification.classList.remove('visible');
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }
    
    initQuickNavigation() {
        // Add keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'k':
                        e.preventDefault();
                        this.focusSearch();
                        break;
                    case 'p':
                        e.preventDefault();
                        window.print();
                        break;
                }
            }
        });
    }
    
    focusSearch() {
        const searchInput = document.querySelector('.md-search__input');
        if (searchInput) {
            searchInput.focus();
        }
    }
    
    initTableOfContents() {
        // Enhanced table of contents with progress tracking
        const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
        const tocProgress = document.createElement('div');
        tocProgress.className = 'toc-progress';
        
        headings.forEach((heading, index) => {
            const progress = document.createElement('div');
            progress.className = 'toc-progress-item';
            progress.textContent = heading.textContent;
            progress.addEventListener('click', () => {
                heading.scrollIntoView({ behavior: 'smooth' });
            });
            tocProgress.appendChild(progress);
        });
        
        document.body.appendChild(tocProgress);
        
        // Update progress on scroll
        window.addEventListener('scroll', () => {
            const scrollTop = window.scrollY;
            const windowHeight = window.innerHeight;
            
            headings.forEach((heading, index) => {
                const rect = heading.getBoundingClientRect();
                const progressItem = tocProgress.children[index];
                
                if (rect.top <= windowHeight / 2 && rect.bottom >= windowHeight / 2) {
                    progressItem.classList.add('active');
                } else {
                    progressItem.classList.remove('active');
                }
            });
        });
    }
    
    initFeedbackSystem() {
        // Simple feedback system
        const feedbackButton = document.createElement('button');
        feedbackButton.className = 'feedback-button';
        feedbackButton.innerHTML = '💬 Feedback';
        feedbackButton.title = 'Send feedback about this page';
        
        feedbackButton.addEventListener('click', () => {
            this.showFeedbackModal();
        });
        
        document.body.appendChild(feedbackButton);
    }
    
    showFeedbackModal() {
        const modal = document.createElement('div');
        modal.className = 'feedback-modal';
        modal.innerHTML = `
            <div class="feedback-content">
                <h3>Send Feedback</h3>
                <p>Help us improve this documentation page:</p>
                <textarea placeholder="Your feedback..." rows="4"></textarea>
                <div class="feedback-actions">
                    <button class="btn-cancel">Cancel</button>
                    <button class="btn-submit">Send</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Handle modal actions
        modal.querySelector('.btn-cancel').addEventListener('click', () => {
            document.body.removeChild(modal);
        });
        
        modal.querySelector('.btn-submit').addEventListener('click', () => {
            const feedback = modal.querySelector('textarea').value;
            if (feedback.trim()) {
                this.showNotification('Thank you for your feedback!');
                document.body.removeChild(modal);
            }
        });
        
        // Close on outside click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        });
    }
}

// Initialize all enhancements
document.addEventListener('DOMContentLoaded', () => {
    new ThemeManager();
    new SyntaxHighlighter();
    new InteractiveFeatures();
});

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        ThemeManager,
        SyntaxHighlighter,
        InteractiveFeatures
    };
}
