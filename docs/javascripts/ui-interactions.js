/**
 * Enhanced UI Features for Velithon Documentation
 * Provides interactive animations, smooth scrolling, and enhanced user experience
 */

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
    initializeEnhancedUI();
});

// Initialize all enhanced UI features
function initializeEnhancedUI() {
    initSmoothScrolling();
    // Code block enhancements removed - using default MkDocs functionality
    initProgressIndicators();
    initInteractiveElements();
    initPerformanceMetrics();
    initSearchEnhancements();
    initAccessibilityFeatures();
    initAnimationObserver();
}

// ===========================
// Smooth Scrolling & Navigation
// ===========================

function initSmoothScrolling() {
    // Enhanced smooth scrolling for anchor links
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    
    anchorLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                const headerOffset = 80;
                const elementPosition = targetElement.offsetTop;
                const offsetPosition = elementPosition - headerOffset;
                
                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });
                
                // Add highlight effect to target element
                targetElement.classList.add('highlighted');
                setTimeout(() => {
                    targetElement.classList.remove('highlighted');
                }, 2000);
            }
        });
    });
}

// ===========================
// Code Block Enhancements Removed
// Using default MkDocs functionality
// ===========================

// Code block enhancement functions removed to prevent conflicts with default MkDocs styling

// ===========================
// Progress Indicators
// ===========================

function initProgressIndicators() {
    // Reading progress bar
    const progressBar = document.createElement('div');
    progressBar.className = 'reading-progress';
    progressBar.innerHTML = '<div class="reading-progress-fill"></div>';
    document.body.appendChild(progressBar);
    
    const progressFill = progressBar.querySelector('.reading-progress-fill');
    
    window.addEventListener('scroll', function() {
        const scrolled = (window.scrollY / (document.documentElement.scrollHeight - window.innerHeight)) * 100;
        progressFill.style.width = `${Math.min(scrolled, 100)}%`;
    });
    
    // Section progress indicators
    const sections = document.querySelectorAll('h2, h3');
    sections.forEach(section => {
        const progressIndicator = document.createElement('div');
        progressIndicator.className = 'section-progress';
        progressIndicator.innerHTML = '<div class="section-progress-fill"></div>';
        section.appendChild(progressIndicator);
    });
}

// ===========================
// Interactive Elements
// ===========================

function initInteractiveElements() {
    // Enhanced tooltips
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    tooltipElements.forEach(element => {
        const tooltip = document.createElement('div');
        tooltip.className = 'enhanced-tooltip';
        tooltip.textContent = element.getAttribute('data-tooltip');
        
        element.addEventListener('mouseenter', function() {
            document.body.appendChild(tooltip);
            const rect = element.getBoundingClientRect();
            tooltip.style.left = `${rect.left + rect.width / 2}px`;
            tooltip.style.top = `${rect.top - 40}px`;
            tooltip.classList.add('visible');
        });
        
        element.addEventListener('mouseleave', function() {
            tooltip.classList.remove('visible');
            setTimeout(() => {
                if (tooltip.parentNode) {
                    tooltip.parentNode.removeChild(tooltip);
                }
            }, 300);
        });
    });
    
    // Interactive cards
    const cards = document.querySelectorAll('.grid.cards > div');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
}

// ===========================
// Performance Metrics
// ===========================

function initPerformanceMetrics() {
    // Page load performance indicator
    window.addEventListener('load', function() {
        let loadTime;
        try {
            // Use modern Performance API
            const perfEntries = performance.getEntriesByType('navigation');
            if (perfEntries.length > 0) {
                loadTime = Math.round(perfEntries[0].loadEventEnd - perfEntries[0].navigationStart);
            } else {
                // Fallback to timing API with validation
                const start = performance.timing.navigationStart;
                const end = performance.timing.loadEventEnd;
                if (start && end && end > start) {
                    loadTime = end - start;
                } else {
                    loadTime = null;
                }
            }
        } catch (error) {
            console.warn('Performance measurement failed:', error);
            loadTime = null;
        }
        
        // Only show indicator if we have valid load time
        if (loadTime && loadTime > 0 && loadTime < 60000) { // Reasonable range: 0-60 seconds
            const perfIndicator = document.createElement('div');
            perfIndicator.className = 'performance-indicator';
            perfIndicator.innerHTML = `
                <div class="perf-icon">⚡</div>
                <div class="perf-text">Page loaded in ${loadTime}ms</div>
            `;
            
            document.body.appendChild(perfIndicator);
            
            setTimeout(() => {
                perfIndicator.classList.add('visible');
            }, 1000);
            
            setTimeout(() => {
                perfIndicator.classList.remove('visible');
                // Remove from DOM after animation
                setTimeout(() => {
                    if (perfIndicator.parentNode) {
                        perfIndicator.parentNode.removeChild(perfIndicator);
                    }
                }, 300);
            }, 4000);
        }
    });
}

// ===========================
// Search Enhancements
// ===========================

function initSearchEnhancements() {
    const searchInput = document.querySelector('.md-search__input');
    if (searchInput) {
        // Add search suggestions
        const suggestions = document.createElement('div');
        suggestions.className = 'search-suggestions';
        searchInput.parentNode.appendChild(suggestions);
        
        // Popular search terms
        const popularTerms = [
            'getting started', 'authentication', 'routing', 'middleware',
            'dependency injection', 'websockets', 'performance', 'deployment'
        ];
        
        searchInput.addEventListener('focus', function() {
            suggestions.innerHTML = popularTerms.map(term => 
                `<div class="suggestion-item" data-term="${term}">${term}</div>`
            ).join('');
            suggestions.classList.add('visible');
        });
        
        searchInput.addEventListener('blur', function() {
            setTimeout(() => {
                suggestions.classList.remove('visible');
            }, 200);
        });
        
        // Handle suggestion clicks
        suggestions.addEventListener('click', function(e) {
            if (e.target.classList.contains('suggestion-item')) {
                searchInput.value = e.target.getAttribute('data-term');
                searchInput.dispatchEvent(new Event('input'));
                suggestions.classList.remove('visible');
            }
        });
    }
}

// ===========================
// Accessibility Features
// ===========================

function initAccessibilityFeatures() {
    // Skip to content link
    const skipLink = document.createElement('a');
    skipLink.href = '#main-content';
    skipLink.className = 'skip-link';
    skipLink.textContent = 'Skip to main content';
    document.body.insertBefore(skipLink, document.body.firstChild);
    
    // Restore high contrast preference
    if (localStorage.getItem('highContrast') === 'true') {
        document.body.classList.add('high-contrast');
    }
    
    // Keyboard navigation enhancements
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Tab') {
            document.body.classList.add('keyboard-navigation');
        }
    });
    
    document.addEventListener('mousedown', function() {
        document.body.classList.remove('keyboard-navigation');
    });
}

// ===========================
// Animation Observer
// ===========================

function initAnimationObserver() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);
    
    // Observe elements for animation
    const animateElements = document.querySelectorAll('.grid.cards > div, .performance-box, .md-typeset .admonition');
    animateElements.forEach(element => {
        element.classList.add('animate-ready');
        observer.observe(element);
    });
}

// ===========================
// Utility Functions
// ===========================

// Debounce function for performance
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Throttle function for scroll events
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Export functions for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initializeEnhancedUI,
        debounce,
        throttle
    };
}
