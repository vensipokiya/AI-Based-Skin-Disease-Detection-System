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
            // Cache a flat version for logic that expects just user data
            localStorage.setItem('dermacare_current_user', JSON.stringify(resData.profile));
        } else {
            throw new Error(resData.error || 'Profile data missing');
        }

    } catch (err) {
        // Fallback to localStorage
        console.warn('Profile load error:', err);
        const cached = localStorage.getItem('dermacare_current_user');
        if (cached) {
            populateProfile(JSON.parse(cached));
        } else {
            showToast('Unable to load profile from server. Using local data if available.', 'error');
        }
    }
}

// ─────────────────────────────────────────────
// POPULATE PROFILE INTO DOM
// ─────────────────────────────────────────────
function populateProfile(data) {
    const fullName = `${data.first_name || ''} ${data.last_name || ''}`.trim();
    const email = data.email || 'guest';

    // Check for saved local avatar first, fallback to initial generator
    const avatarKey = `dermacare_avatar_${email}`;
    const savedAvatar = localStorage.getItem(avatarKey);
    const avatarUrl = savedAvatar ? savedAvatar : "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxNTAgMTUwIj48cmVjdCB3aWR0aD0iMTUwIiBoZWlnaHQ9IjE1MCIgZmlsbD0iIzI1NjNlYiIvPjxwYXRoIGQ9Ik03NSA0NWMxMS4wNSAwIDIwIDguOTUgMjAgMjBzLTguOTUgMjAtMjAgMjAtMjAtOC45NS0yMC0yMCA4Ljk1LTIwIDIwLTIwem0wIDQ1Yy0yMC44MyAwLTM5LjAzIDEwLjY1LTUwIDI2LjgyLjI1LTE2LjU2IDMzLTE4LjE0IDUwLTE4LjE0czQ5Ljc1IDEuNTggNTAgMTguMTRjLTEwLjk3LTE2LjE3LTI5LjE3LTI2LjgyLTUwLTI2LjgyeiaIGZpbGw9IiNmZmZmZmYiLz48L3N2Zz4=";

    // Sidebar
    setText('sidebar-name', fullName || 'User');
    setText('sidebar-email', email);
    setAttr('sidebar-avatar', 'src', avatarUrl);

    // Profile card avatar & name
    setAttr('profile-avatar', 'src', avatarUrl);
    setAttr('header-avatar', 'src', avatarUrl); // Ensure header stays synced
    setText('avatar-display-name', fullName || 'User');

    // Form fields
    setValue('prof-firstname', data.first_name || '');
    setValue('prof-lastname', data.last_name || '');
    setValue('prof-email', data.email || '');
    setValue('prof-phone', data.contact_number || '');
    setValue('prof-dob', data.date_of_birth || '');
    setValue('prof-age', data.age !== undefined ? data.age : '');

    const genderSel = document.getElementById('prof-gender');
    if (genderSel) {
        const val = (data.gender || '').toLowerCase();
        genderSel.value = val || 'male';
    }

    setValue('prof-location', (!data.location || data.location === 'Unknown') ? '' : data.location);

    // Quick stats in avatar column
    const genderLabel = (data.gender || '').charAt(0).toUpperCase() + (data.gender || '').slice(1);
    setText('stat-gender', genderLabel || '—');
    setText('stat-age', data.age ? `${data.age} yrs` : '—');
    setText('stat-phone', data.contact_number || '—');

    // Store for cancel reset
    window._originalProfile = { ...data };

    // 🔥 Auto-Detect Location logic 
    const isOldFormat = data.location && data.location.includes(',') && data.location.split(',').length < 3;
    if (!data.location || data.location === 'Unknown' || data.location === '' || isOldFormat) {
        const locInput = document.getElementById('prof-location');
        if (locInput) {
            locInput.placeholder = "Detecting location...";
            // SECURITY REVIEW: This geolocation usage is strictly for medical diagnostic/specialist discovery in Nearby Dermatologist.
            // It is only triggered if the user's location is missing or outdated.
            if (navigator && navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(async (position) => {

                    const lat = position.coords.latitude;
                    const lng = position.coords.longitude;
                    try {
                        const url = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}`;
                        const resp = await fetch(url, { headers: { "Accept-Language": "en-US,en;q=0.9" } });
                        if (resp.ok) {
                            const resData = await resp.json();
                            const addr = resData.address || {};
                            const area = addr.suburb || addr.neighbourhood || addr.residential || '';
                            const city = addr.city || addr.town || addr.municipality || addr.village || addr.county || addr.city_district || '';
                            const state = addr.state || '';

                            const parts = [];
                            if (area) parts.push(area);
                            if (city) parts.push(city);
                            if (state) parts.push(state);

                            const finalLoc = parts.length > 0 ? parts.join(', ') : 'Unknown';
                            if (finalLoc !== 'Unknown') {
                                locInput.value = finalLoc;
                                showToast("Location successfully auto-detected!", "success");
                            }
                        }
                    } catch (err) {
                        locInput.placeholder = "City / State";
                    }
                }, (error) => {
                    locInput.placeholder = "City / State";
                });
            }
        }
    }
}

// ─────────────────────────────────────────────
// SAVE PROFILE CHANGES
// ─────────────────────────────────────────────
async function saveProfile(e) {
    e.preventDefault();
    const token = localStorage.getItem('dermacare_token');
    if (!token) { window.location.href = '/login'; return; }

    const btn = document.getElementById('btn-save-profile');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving…';

    const payload = {
        first_name: getValue('prof-firstname'),
        last_name: getValue('prof-lastname'),
        contact_number: getValue('prof-phone'),
        date_of_birth: getValue('prof-dob'),
        age: parseInt(getValue('prof-age')) || null,
        gender: document.getElementById('prof-gender')?.value || 'male',
        location: getValue('prof-location') || 'Unknown' // Added location if present in DOM, else Unknown
    };

    // Client-side validation
    if (!payload.first_name || !payload.last_name) {
        showToast('First and last name are required.', 'error');
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-save"></i> Save Changes';
        return;
    }

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
            
            // Safe Local Storage Updates
            try {
                const cached = JSON.parse(localStorage.getItem('dermacare_current_user') || '{}');
                const updatedUser = { ...cached, ...payload };
                localStorage.setItem('dermacare_current_user', JSON.stringify(updatedUser));

                // Permanently save the avatar if one was staged
                if (window.pendingAvatarUrl) {
                    const avatarKey = `dermacare_avatar_${updatedUser.email || 'guest'}`;
                    localStorage.setItem(avatarKey, window.pendingAvatarUrl);
                    setAttr('sidebar-avatar', 'src', window.pendingAvatarUrl);
                    setAttr('header-avatar', 'src', window.pendingAvatarUrl);
                    window.pendingAvatarUrl = null; // Clear staged avatar
                }
            } catch (storageErr) {
                console.warn('LocalStorage Quota exceeded or update error:', storageErr);
                // We don't show a toast here to not confuse the user, 
                // as the server update was successful.
            }

            // Refresh display from server
            await loadProfile();
        } else {
            let errorMsg = data.error;
            if (!errorMsg && data.detail) {
                if (typeof data.detail === 'string') errorMsg = data.detail;
                else if (Array.isArray(data.detail)) errorMsg = data.detail[0].loc.join('.') + ': ' + data.detail[0].msg;
            }
            showToast(errorMsg || 'Update failed. Please check your information.', 'error');
        }
    } catch (err) {
        console.error('Save profile exception:', err);
        if (err.name === 'QuotaExceededError') {
            showToast('Local storage full. Profile saved but avatar might not persist locally.', 'info');
        } else {
            showToast('Could not connect to server. Check if backend is running.', 'error');
        }
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-save"></i> Save Changes';
    }
}

// ─────────────────────────────────────────────
// CANCEL — restore original values
// ─────────────────────────────────────────────
function cancelEdit() {
    if (window._originalProfile) {
        populateProfile(window._originalProfile);
        window.pendingAvatarUrl = null; // Discard staged avatar
        showToast('Changes discarded.', 'info');
    }
}



// ─────────────────────────────────────────────
// LOGOUT
// ─────────────────────────────────────────────
async function handleLogout(e) {
    e.preventDefault();
    const token = localStorage.getItem('dermacare_token');
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
    // Auth guard
    const token = localStorage.getItem('dermacare_token');
    if (!token) { window.location.href = '/login'; return; }

    // Load profile data
    loadProfile();

    // Bind profile form
    const profileForm = document.getElementById('profile-form');
    if (profileForm) profileForm.addEventListener('submit', saveProfile);

    // Bind cancel button
    const cancelBtn = document.getElementById('btn-cancel-profile');
    if (cancelBtn) cancelBtn.addEventListener('click', cancelEdit);


    // Bind logout links
    document.querySelectorAll('.logout-btn-trigger').forEach(el => {
        el.addEventListener('click', handleLogout);
    });

    // ─────────────────────────────────────────────
    // AVATAR MODAL & CAMERA LOGIC
    // ─────────────────────────────────────────────
    const avatarModal = document.getElementById('avatar-modal');
    const btnEditAvatar = document.querySelector('.btn-edit-avatar');
    const btnCloseAvatarModal = document.getElementById('btn-close-avatar-modal');

    const optionsGrid = document.getElementById('avatar-options-grid');
    const cameraContainer = document.getElementById('camera-container');
    const videoStream = document.getElementById('camera-stream');
    const cameraCanvas = document.getElementById('camera-canvas');

    const btnUploadPhoto = document.getElementById('btn-upload-photo');
    const avatarUploadInput = document.getElementById('avatar-upload-input');

    const btnTakePhoto = document.getElementById('btn-take-photo');
    const btnCapturePhoto = document.getElementById('btn-capture-photo');
    const btnCancelCamera = document.getElementById('btn-cancel-camera');

    let currentStream = null;

    // Open Modal
    if (btnEditAvatar) {
        btnEditAvatar.addEventListener('click', () => {
            optionsGrid.style.display = 'grid';
            cameraContainer.style.display = 'none';
            avatarModal.classList.add('active');
        });
    }

    // Close Modal Helper
    function closeAvatarModal() {
        avatarModal.classList.remove('active');
        stopCamera();
    }

    if (btnCloseAvatarModal) {
        btnCloseAvatarModal.addEventListener('click', closeAvatarModal);
    }

    // Close on outside click
    window.addEventListener('click', (e) => {
        if (e.target === avatarModal) {
            closeAvatarModal();
        }
    });

    // 1. Upload Photo Logic
    if (btnUploadPhoto && avatarUploadInput) {
        btnUploadPhoto.addEventListener('click', () => {
            avatarUploadInput.click();
        });

        avatarUploadInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (readerEvent) => {
                    const base64Data = readerEvent.target.result;

                    // Stage the avatar for save
                    window.pendingAvatarUrl = base64Data;
                    setAttr('profile-avatar', 'src', base64Data);
                    setAttr('sidebar-avatar', 'src', base64Data);
                    setAttr('header-avatar', 'src', base64Data);

                    closeAvatarModal();
                    showToast('Profile picture attached! Click Save Changes to apply.', 'info');
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // 2. Camera Logic
    function stopCamera() {
        if (currentStream) {
            currentStream.getTracks().forEach(track => track.stop());
            currentStream = null;
        }
        if (videoStream) {
            videoStream.srcObject = null;
        }
    }

    if (btnTakePhoto) {
        btnTakePhoto.addEventListener('click', async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ video: true });
                currentStream = stream;
                videoStream.srcObject = stream;

                optionsGrid.style.display = 'none';
                cameraContainer.style.display = 'flex';

            } catch (err) {
                console.error("Camera error:", err);
                showToast('Unable to access camera. Please check permissions.', 'error');
            }
        });
    }

    if (btnCancelCamera) {
        btnCancelCamera.addEventListener('click', () => {
            stopCamera();
            optionsGrid.style.display = 'grid';
            cameraContainer.style.display = 'none';
        });
    }

    if (btnCapturePhoto) {
        btnCapturePhoto.addEventListener('click', () => {
            if (!currentStream) return;

            // Set canvas dimensions to match video
            cameraCanvas.width = videoStream.videoWidth;
            cameraCanvas.height = videoStream.videoHeight;

            const ctx = cameraCanvas.getContext('2d');
            ctx.drawImage(videoStream, 0, 0, cameraCanvas.width, cameraCanvas.height);

            // Get base64 image
            const base64Data = cameraCanvas.toDataURL('image/jpeg', 0.9);

            // Stage the avatar for save
            window.pendingAvatarUrl = base64Data;
            setAttr('profile-avatar', 'src', base64Data);
            setAttr('sidebar-avatar', 'src', base64Data);
            setAttr('header-avatar', 'src', base64Data);

            closeAvatarModal();
            showToast('Profile picture captured! Click Save Changes to apply.', 'info');
        });
    }

    // Helper to apply avatar everywhere
    function updateAvatarImages(imageUrl) {
        setAttr('profile-avatar', 'src', imageUrl);
        setAttr('sidebar-avatar', 'src', imageUrl);
        setAttr('header-avatar', 'src', imageUrl);
        // Save to local storage so it persists on reload
        localStorage.setItem('dermacare_avatar_base64', imageUrl);
    }
});
