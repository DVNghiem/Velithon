/**
 * Homepage Enhancements for Velithon Documentation
 * Provides interactive demos, animations, and enhanced homepage experience
 */

// Homepage-specific enhancements
document.addEventListener('DOMContentLoaded', function() {
    if (isHomePage()) {
        initHomepageEnhancements();
    }
});

function isHomePage() {
    return window.location.pathname === '/' || window.location.pathname.endsWith('/index.html');
}

function initHomepageEnhancements() {
    createLiveDemo();
    initPerformanceCounter();
    enhanceFeatureCards();
    // Interactive code example removed - using default MkDocs functionality
    initHeroAnimations();
}

// ===========================
// Live API Demo
// ===========================

function createLiveDemo() {
    const demoContainer = document.createElement('div');
    demoContainer.className = 'live-demo-container';
    demoContainer.innerHTML = `
        <div class="demo-header">
            <h3>🚀 Velithon API Examples</h3>
        </div>
        <div class="demo-content">
            <div class="demo-tabs">
                <button class="demo-tab active" data-demo="basic">Basic API</button>
                <button class="demo-tab" data-demo="advanced">Advanced</button>
                <button class="demo-tab" data-demo="websocket">WebSocket</button>
            </div>
            <div class="demo-examples">
                <div class="demo-example active" data-demo="basic">
                    <h4>GET /</h4>
                    <pre class="demo-response-body success">{
  "message": "Welcome to Velithon!",
  "version": "1.0.0",
  "performance": "⚡ Ultra-fast RSGI framework",
  "timestamp": "2025-07-04T12:00:00Z"
}</pre>
                </div>
                <div class="demo-example" data-demo="advanced">
                    <h4>GET /users/123</h4>
                    <pre class="demo-response-body success">{
  "user_id": 123,
  "name": "User 123",
  "endpoint": "/users/123",
  "method": "GET",
  "timestamp": "2025-07-04T12:00:00Z"
}</pre>
                </div>
                <div class="demo-example" data-demo="websocket">
                    <h4>WebSocket /ws</h4>
                    <pre class="demo-response-body success">{
  "status": "connected",
  "message": "WebSocket connection established",
  "features": ["real-time", "bidirectional", "high-performance"]
}</pre>
                </div>
            </div>
        </div>
    `;

    // Insert after the first content section
    const contentArea = document.querySelector('.md-content__inner');
    if (contentArea) {
        const firstSection = contentArea.querySelector('h2');
        if (firstSection) {
            firstSection.parentNode.insertBefore(demoContainer, firstSection.nextSibling);
        }
    }

    bindDemoTabEvents(demoContainer);
}

function bindDemoEvents(container) {
    const sendBtn = container.querySelector('.demo-send');
    const methodSelect = container.querySelector('.demo-method');
    const urlInput = container.querySelector('.demo-url');
    const requestBody = container.querySelector('.demo-request-body');
    const responseBody = container.querySelector('.demo-response-body');

    sendBtn.addEventListener('click', async function() {
        const method = methodSelect.value;
        const url = urlInput.value;
        const body = requestBody.value;

        this.textContent = 'Sending...';
        this.disabled = true;

        try {
            // Simulate API call to a Velithon endpoint
            const response = await simulateVelithonRequest(method, url, body);
            responseBody.textContent = JSON.stringify(response, null, 2);
            responseBody.className = 'demo-response-body success';
        } catch (error) {
            responseBody.textContent = `Error: ${error.message}`;
            responseBody.className = 'demo-response-body error';
        } finally {
            this.textContent = 'Send Request';
            this.disabled = false;
        }
    });

    // Update request body visibility based on method
    methodSelect.addEventListener('change', function() {
        const requestSection = container.querySelector('.demo-request');
        requestSection.style.display = this.value === 'POST' ? 'block' : 'none';
    });

    // Trigger initial change
    methodSelect.dispatchEvent(new Event('change'));
}

async function simulateVelithonRequest(method, url, body) {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 300 + Math.random() * 500));

    // Mock responses based on URL patterns
    if (url === '/' || url === '') {
        return {
            message: "Welcome to Velithon!",
            version: "1.0.0",
            performance: "⚡ Ultra-fast RSGI framework",
            timestamp: new Date().toISOString()
        };
    } else if (url.startsWith('/hello/')) {
        const name = url.split('/')[2] || 'World';
        return {
            message: `Hello, ${name}!`,
            endpoint: url,
            method: method,
            timestamp: new Date().toISOString()
        };
    } else if (url === '/health') {
        return {
            status: "healthy",
            uptime: "99.9%",
            response_time: "0.8ms",
            memory_usage: "45MB",
            timestamp: new Date().toISOString()
        };
    } else if (method === 'POST' && url === '/items') {
        try {
            const item = body ? JSON.parse(body) : {};
            return {
                message: "Item created successfully",
                item: {
                    id: Math.floor(Math.random() * 10000),
                    ...item,
                    created_at: new Date().toISOString()
                }
            };
        } catch (e) {
            throw new Error('Invalid JSON in request body');
        }
    } else {
        throw new Error(`Endpoint ${url} not found`);
    }
}

// ===========================
// Performance Counter
// ===========================

function initPerformanceCounter() {
    const counterContainer = document.createElement('div');
    counterContainer.className = 'performance-counter';
    counterContainer.innerHTML = `
        <div class="counter-item">
            <div class="counter-number" data-target="70000">0</div>
            <div class="counter-label">Requests/sec</div>
        </div>
        <div class="counter-item">
            <div class="counter-number" data-target="0.8">0</div>
            <div class="counter-label">ms Response Time</div>
        </div>
        <div class="counter-item">
            <div class="counter-number" data-target="99.9">0</div>
            <div class="counter-label">% Uptime</div>
        </div>
        <div class="counter-item">
            <div class="counter-number" data-target="45">0</div>
            <div class="counter-label">MB Memory Usage</div>
        </div>
    `;

    // Insert after the hero section
    const heroSection = document.querySelector('h1').parentElement;
    if (heroSection) {
        heroSection.appendChild(counterContainer);
    }

    // Animate counters when they come into view
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounters();
                observer.unobserve(entry.target);
            }
        });
    });

    observer.observe(counterContainer);
}

function animateCounters() {
    const counters = document.querySelectorAll('.counter-number');
    
    counters.forEach(counter => {
        const target = parseFloat(counter.getAttribute('data-target'));
        const duration = 2000; // 2 seconds
        const start = performance.now();
        
        function updateCounter(currentTime) {
            const elapsed = currentTime - start;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function for smooth animation
            const easeOut = 1 - Math.pow(1 - progress, 3);
            const current = target * easeOut;
            
            if (target >= 1000) {
                counter.textContent = Math.floor(current).toLocaleString();
            } else {
                counter.textContent = current.toFixed(1);
            }
            
            if (progress < 1) {
                requestAnimationFrame(updateCounter);
            }
        }
        
        requestAnimationFrame(updateCounter);
    });
}

// ===========================
// Enhanced Feature Cards
// ===========================

function enhanceFeatureCards() {
    const featureCards = document.querySelectorAll('.grid.cards > div');
    
    featureCards.forEach(card => {
        // Add hover effect data
        card.setAttribute('data-tooltip', 'Click to learn more');
        
        // Add click handlers for navigation
        card.addEventListener('click', function() {
            const cardText = this.textContent.toLowerCase();
            let targetUrl = '';
            
            if (cardText.includes('performance')) {
                targetUrl = '/advanced/performance/';
            } else if (cardText.includes('dependency')) {
                targetUrl = '/user-guide/dependency-injection/';
            } else if (cardText.includes('websocket')) {
                targetUrl = '/user-guide/websocket/';
            } else if (cardText.includes('template')) {
                targetUrl = '/user-guide/templates/';
            } else if (cardText.includes('security')) {
                targetUrl = '/security/';
            } else if (cardText.includes('gateway')) {
                targetUrl = '/advanced/gateway/';
            }
            
            if (targetUrl) {
                window.location.href = targetUrl;
            }
        });
        
        // Add icon animations
        const icon = card.querySelector('[class*="material-"]');
        if (icon) {
            card.addEventListener('mouseenter', function() {
                icon.style.transform = 'scale(1.2) rotate(5deg)';
            });
            
            card.addEventListener('mouseleave', function() {
                icon.style.transform = 'scale(1) rotate(0deg)';
            });
        }
    });
}

// ===========================
// Interactive Code Example Removed
// Using default MkDocs functionality
// ===========================

// Interactive code example function removed to prevent conflicts with default MkDocs styling

// ===========================
// Hero Animations
// ===========================

function initHeroAnimations() {
    const heroTitle = document.querySelector('h1');
    const heroDescription = document.querySelector('p strong');
    
    if (heroTitle) {
        heroTitle.classList.add('hero-animate');
        
        // Add typing effect to the title
        const originalText = heroTitle.textContent;
        heroTitle.textContent = '';
        
        let i = 0;
        const typeWriter = () => {
            if (i < originalText.length) {
                heroTitle.textContent += originalText.charAt(i);
                i++;
                setTimeout(typeWriter, 100);
            }
        };
        
        // Start typing effect after a short delay
        setTimeout(typeWriter, 500);
    }
    
    if (heroDescription) {
        heroDescription.classList.add('hero-description-animate');
    }

    // Add floating animation to badges
    const badges = document.querySelectorAll('img[alt*="version"], img[alt*="Python"], img[alt*="License"], img[alt*="Build"]');
    badges.forEach((badge, index) => {
        badge.style.animationDelay = `${index * 0.2}s`;
        badge.classList.add('badge-float');
    });
}

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initHomepageEnhancements,
        simulateVelithonRequest,
        animateCounters
    };
}
