/**
 * FRP Console - Theme Manager
 * 主题管理器 - 支持深色/亮色主题切换
 */

(function() {
    'use strict';

    // Theme configuration
    const THEME_KEY = 'frp-console-theme';
    const THEMES = {
        LIGHT: 'light',
        DARK: 'dark',
        AUTO: 'auto'
    };

    /**
     * Get system preferred color scheme
     * @returns {string} 'dark' or 'light'
     */
    function getSystemTheme() {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? THEMES.DARK : THEMES.LIGHT;
    }

    /**
     * Get saved theme from localStorage
     * @returns {string|null}
     */
    function getSavedTheme() {
        try {
            return localStorage.getItem(THEME_KEY);
        } catch (e) {
            console.warn('Failed to access localStorage:', e);
            return null;
        }
    }

    /**
     * Save theme to localStorage
     * @param {string} theme
     */
    function saveTheme(theme) {
        try {
            localStorage.setItem(THEME_KEY, theme);
        } catch (e) {
            console.warn('Failed to save theme:', e);
        }
    }

    /**
     * Apply theme to document
     * @param {string} theme
     */
    function applyTheme(theme) {
        const root = document.documentElement;
        
        // Remove existing theme classes
        root.removeAttribute('data-theme');
        
        // Determine effective theme
        let effectiveTheme = theme;
        if (theme === THEMES.AUTO) {
            effectiveTheme = getSystemTheme();
        }
        
        // Apply theme
        if (effectiveTheme === THEMES.DARK) {
            root.setAttribute('data-theme', 'dark');
        }
        
        // Update meta theme-color for mobile browsers
        const metaThemeColor = document.querySelector('meta[name="theme-color"]');
        if (metaThemeColor) {
            metaThemeColor.setAttribute('content', effectiveTheme === THEMES.DARK ? '#0f172a' : '#ffffff');
        }
        
        // Dispatch custom event
        window.dispatchEvent(new CustomEvent('themechange', { 
            detail: { theme: effectiveTheme, saved: theme }
        }));
    }

    /**
     * Set theme
     * @param {string} theme - 'light', 'dark', or 'auto'
     */
    function setTheme(theme) {
        if (!Object.values(THEMES).includes(theme)) {
            console.warn('Invalid theme:', theme);
            return;
        }
        
        saveTheme(theme);
        applyTheme(theme);
        updateThemeToggleButton(theme);
    }

    /**
     * Toggle between light and dark
     */
    function toggleTheme() {
        const currentTheme = getSavedTheme() || THEMES.LIGHT;
        const newTheme = currentTheme === THEMES.DARK ? THEMES.LIGHT : THEMES.DARK;
        setTheme(newTheme);
    }

    /**
     * Get current effective theme
     * @returns {string}
     */
    function getCurrentTheme() {
        const saved = getSavedTheme();
        if (saved === THEMES.AUTO) {
            return getSystemTheme();
        }
        return saved || THEMES.LIGHT;
    }

    /**
     * Update theme toggle button appearance
     * @param {string} theme
     */
    function updateThemeToggleButton(theme) {
        const btn = document.getElementById('theme-toggle-btn');
        if (!btn) return;

        const isDark = theme === THEMES.DARK || 
                      (theme === THEMES.AUTO && getSystemTheme() === THEMES.DARK);
        
        // Update icon
        const icon = btn.querySelector('.theme-icon') || btn;
        if (isDark) {
            icon.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>`;
            btn.setAttribute('title', '切换到亮色模式');
            btn.setAttribute('aria-label', '切换到亮色模式');
        } else {
            icon.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>`;
            btn.setAttribute('title', '切换到深色模式');
            btn.setAttribute('aria-label', '切换到深色模式');
        }
    }

    /**
     * Create theme toggle button
     * @returns {HTMLElement}
     */
    function createThemeToggleButton() {
        const btn = document.createElement('button');
        btn.id = 'theme-toggle-btn';
        btn.className = 'theme-toggle-btn';
        btn.setAttribute('type', 'button');
        btn.innerHTML = `<span class="theme-icon"></span>`;
        
        btn.addEventListener('click', toggleTheme);
        
        // Add styles
        if (!document.getElementById('theme-toggle-styles')) {
            const style = document.createElement('style');
            style.id = 'theme-toggle-styles';
            style.textContent = `
                .theme-toggle-btn {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    width: 40px;
                    height: 40px;
                    border-radius: 10px;
                    border: 1px solid var(--border-color);
                    background: var(--bg-card);
                    color: var(--text-secondary);
                    cursor: pointer;
                    transition: all 0.2s ease;
                }
                .theme-toggle-btn:hover {
                    background: var(--bg-hover);
                    color: var(--text-primary);
                    border-color: var(--border-hover);
                    transform: translateY(-1px);
                }
                .theme-toggle-btn:active {
                    transform: translateY(0);
                }
                .theme-toggle-btn svg {
                    transition: transform 0.3s ease;
                }
                .theme-toggle-btn:hover svg {
                    transform: rotate(15deg);
                }
            `;
            document.head.appendChild(style);
        }
        
        return btn;
    }

    /**
     * Initialize theme system
     */
    function init() {
        // Get saved theme or default to light
        const savedTheme = getSavedTheme() || THEMES.LIGHT;
        
        // Apply theme immediately to prevent flash
        applyTheme(savedTheme);
        
        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            const currentSaved = getSavedTheme();
            if (currentSaved === THEMES.AUTO) {
                applyTheme(THEMES.AUTO);
                updateThemeToggleButton(THEMES.AUTO);
            }
        });
        
        // Expose API
        window.ThemeManager = {
            set: setTheme,
            toggle: toggleTheme,
            get: getCurrentTheme,
            getSaved: getSavedTheme,
            THEMES: THEMES,
            createToggleButton: createThemeToggleButton
        };
        
        console.log('[Theme] Initialized with theme:', savedTheme);
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
