/**
 * dermacare-utils.js
 * Common utility functions for DermaCare AI across multiple pages.
 */

window.DERMACARE_API_BASE = window.DERMACARE_API_BASE || 'http://127.0.0.1:8000';

window.DermaUtils = {
    // ── DOM Helpers ──
    setText: (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; },
    setAttr: (id, a, v) => { const el = document.getElementById(id); if (el) el.setAttribute(a, v); },
    setValue: (id, val) => { const el = document.getElementById(id); if (el) el.value = val; },
    getValue: (id) => (document.getElementById(id) || {}).value?.trim() || '',
    // Safe linear-time email validation (no nested quantifiers)
    isValidEmail: (email) => /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/.test(email),
    hide: (id) => { const el = document.getElementById(id); if (el) el.classList.add('hidden'); },
    show: (id) => { const el = document.getElementById(id); if (el) el.classList.remove('hidden'); },

    // ── UI Components ──
    togglePasswordVisibility: function (inputId, btn) {
        const input = document.getElementById(inputId);
        if (!input) return;
        const icon = btn.querySelector('i');
        if (input.type === 'password') {
            input.type = 'text';
            if (icon) icon.className = 'fas fa-eye-slash';
        } else {
            input.type = 'password';
            if (icon) icon.className = 'fas fa-eye';
        }
    },

    showToast: function (message, type = 'info', duration = 3200) {
        const container = document.getElementById('toast-container');
        if (!container) return;
        const icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            info: 'fa-info-circle'
        };
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `<i class="fas ${icons[type] || icons.info}"></i><span>${message}</span>`;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 400);
        }, duration);
    },

    /**
     * showNotification — lightweight inline toast (no toast-container required)
     * Used in history.js and anywhere else a quick fixed notification is needed.
     */
    showNotification: function (message) {
        const toast = document.createElement('div');
        toast.className = 'fade-in';
        Object.assign(toast.style, {
            position: 'fixed', bottom: '20px', right: '20px',
            background: '#0f172a', color: 'white',
            padding: '1rem 1.5rem', borderRadius: '12px',
            boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)',
            zIndex: '9999', display: 'flex', alignItems: 'center', gap: '10px'
        });
        toast.innerHTML = `<i class="fas fa-check-circle" style="color:#10b981;"></i> ${message}`;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.5s ease';
            setTimeout(() => toast.remove(), 500);
        }, 3000);
    },

    // ── Auth Helpers ──
    /**
     * getAuthHeaders — returns headers including Authorization Bearer token.
     */
    getAuthHeaders: function (includeContentType = true) {
        const token = localStorage.getItem('dermacare_token');
        const headers = {};
        if (includeContentType) headers['Content-Type'] = 'application/json';
        if (token) headers['Authorization'] = `Bearer ${token}`;
        return headers;
    },

    /**
     * handleSuccessfulLogin — stores credentials and redirects after login.
     * Shared by login.js and Google/Apple OAuth callbacks.
     */
    handleSuccessfulLogin: function (token, refreshToken, user) {
        localStorage.setItem('dermacare_token', token);
        localStorage.setItem('dermacare_refresh_token', refreshToken || token);
        localStorage.setItem('dermacare_logged_in', 'true');
        localStorage.setItem('dermacare_current_user', JSON.stringify(user));
        if (user.role === 'Admin') {
            localStorage.setItem('admin_token', token);
        }
        setTimeout(() => {
            if (user.role === 'Admin') {
                window.location.href = '/admin';
            } else if (sessionStorage.getItem('pending_scan_result') || sessionStorage.getItem('scan_result')) {
                sessionStorage.setItem('scan_result_authenticated', 'true');
                window.location.href = '/scan-result';
            } else {
                window.location.href = '/';
            }
        }, 1000);
    },

    logout: async function () {
        const token = localStorage.getItem('dermacare_token');
        const API_URL = window.DERMACARE_API_BASE;
        try {
            if (token) {
                await fetch(`${API_URL}/api/auth/logout`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}` }
                });
            }
        } catch (err) {
            console.error('Logout error:', err);
        } finally {
            localStorage.removeItem('dermacare_token');
            localStorage.removeItem('dermacare_refresh_token');
            localStorage.removeItem('dermacare_logged_in');
            localStorage.removeItem('dermacare_current_user');
            window.location.href = '/login';
        }
    }
};

// Global shorthands for inline HTML usage
window.togglePasswordVisibility = window.DermaUtils.togglePasswordVisibility;
