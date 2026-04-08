/**
 * dermacare-utils.js
 * Common utility functions for DermaCare AI across multiple pages.
 */

window.DermaUtils = {
    // ── DOM Helpers ──
    setText: (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; },
    setAttr: (id, a, v) => { const el = document.getElementById(id); if (el) el.setAttribute(a, v); },
    setValue: (id, val) => { const el = document.getElementById(id); if (el) el.value = val; },
    getValue: (id) => (document.getElementById(id) || {}).value?.trim() || '',
    isValidEmail: (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email),
    hide: (id) => { const el = document.getElementById(id); if (el) el.classList.add('hidden'); },
    show: (id) => { const el = document.getElementById(id); if (el) el.classList.remove('hidden'); },

    // ── UI Components ──
    togglePasswordVisibility: function(inputId, btn) {
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

    showToast: function(message, type = 'info') {
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
        }, 3200);
    },

    // ── Auth Helpers ──
    logout: async function() {
        const token = localStorage.getItem('dermacare_token');
        const API_URL = window.DERMACARE_API_BASE || 'http://127.0.0.1:8000';
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

// Global shorthand for password toggle since it's used in inline HTML
window.togglePasswordVisibility = window.DermaUtils.togglePasswordVisibility;
