/**
 * user_profile.js
 * DermaCare AI — User Profile Page Logic
 * Handles: load profile, update profile, change password, logout
 */

const API_URL = (window.DERMACARE_API_BASE) ? window.DERMACARE_API_BASE : 'http://127.0.0.1:8000';

// ─────────────────────────────────────────────
// TOAST HELPER
// ─────────────────────────────────────────────
function showToast(message, type = 'info') {
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
    setTimeout(() => toast.remove(), 3200);
}

// ─────────────────────────────────────────────
// LOAD PROFILE FROM API
// ─────────────────────────────────────────────
async function loadProfile() {
    const token = localStorage.getItem('dermacare_token');
    if (!token) {
        window.location.href = '/login';
        return;
    }

    try {
        const res = await fetch(`${API_URL}/api/user/profile`, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!res.ok) {
            if (res.status === 401) {
                localStorage.removeItem('dermacare_token');
                window.location.href = '/login';
                return;
            }
            throw new Error('Failed to fetch profile');
        }

        const resData = await res.json();
        if (resData.success && resData.profile) {
            populateProfile(resData.profile);
            localStorage.setItem('dermacare_current_user', JSON.stringify(resData.profile));
        } else {
            throw new Error(resData.error || 'Profile data missing');
        }

    } catch (err) {
        console.warn('Profile load error:', err);
        const cached = localStorage.getItem('dermacare_current_user');
        if (cached) {
            populateProfile(JSON.parse(cached));
        } else {
            showToast('Unable to load profile from server.', 'error');
        }
    }
}

// ─────────────────────────────────────────────
// POPULATE PROFILE INTO DOM
// ─────────────────────────────────────────────
function populateProfile(data) {
    const fullName = `${data.first_name || ''} ${data.last_name || ''}`.trim();
    const email = data.email || 'guest';

    const avatarKey = `dermacare_avatar_${email}`;
    const savedAvatar = localStorage.getItem(avatarKey);
    const avatarUrl = savedAvatar ? savedAvatar : "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxNTAgMTUwIj48cmVjdCB3aWR0aD0iMTUwIiBoZWlnaHQ9IjE1MCIgZmlsbD0iIzI1NjNlYiIvPjxwYXRoIGQ9Ik03NSA0NWMxMS4wNSAwIDIwIDguOTUgMjAgMjBzLTguOTUgMjAtMjAgMjAtMjAtOC45NS0yMC0yMCA4Ljk1LTIwIDIwLTIwem0wIDQ1Yy0yMC44MyAwLTM5LjAzIDEwLjY1LTUwIDI2LjgyLjI1LTE2LjU2IDMzLTE4LjE0IDUwLTE4LjE0czQ5Ljc1IDEuNTggNTAgMTguMTRjLTEwLjk3LTE2LjE3LTI5LjE3LTI2LjgyLTUwLTI2LjgyeiaIGZpbGw9IiNmZmZmZmYiLz48L3N2Zz4=";

    setText('display-full-name', fullName || 'User');
    setText('display-email', email);
    setAttr('display-profile-img', 'src', avatarUrl);

    setValue('prof-first-name', data.first_name || '');
    setValue('prof-last-name', data.last_name || '');
    setValue('prof-phone', data.contact_number || '');
    setValue('prof-location', data.user_location || '');

    window._originalProfile = { ...data };
}

// ─────────────────────────────────────────────
// SAVE PROFILE CHANGES
// ─────────────────────────────────────────────
async function saveProfile(e) {
    e.preventDefault();
    const token = localStorage.getItem('dermacare_token');
    if (!token) { window.location.href = '/login'; return; }

    const payload = {
        first_name: getValue('prof-first-name'),
        last_name: getValue('prof-last-name'),
        contact_number: getValue('prof-phone'),
        user_location: getValue('prof-location')
    };

    try {
        const res = await fetch(`${API_URL}/api/user/profile`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (res.ok && data.success) {
            showToast('Profile updated successfully!', 'success');
            await loadProfile();
        } else {
            showToast(data.error || 'Update failed.', 'error');
        }
    } catch (err) {
        showToast('Connection error.', 'error');
    }
}

// ─────────────────────────────────────────────
// DOM HELPERS
// ─────────────────────────────────────────────
function setText(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }
function setAttr(id, a, v) { const el = document.getElementById(id); if (el) el.setAttribute(a, v); }
function setValue(id, val) { const el = document.getElementById(id); if (el) el.value = val; }
function getValue(id) { return (document.getElementById(id) || {}).value?.trim() || ''; }

// ─────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('dermacare_token');
    if (!token) { window.location.href = '/login'; return; }

    loadProfile();
    const profileForm = document.getElementById('form-account-info');
    if (profileForm) profileForm.addEventListener('submit', saveProfile);
    
    // Bind logout link
    const logoutBtn = id => document.getElementById(id)?.addEventListener('click', () => {
        localStorage.clear();
        window.location.href = '/login';
    });
    logoutBtn('btn-logout-profile');
});
