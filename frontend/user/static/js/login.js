const API_URL = window.DERMACARE_API_BASE || 'http://127.0.0.1:8000';

// ---------------------------
// Validation Helpers
// ---------------------------
function showError(elementId, message) {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = message;
        el.classList.add('visible');
    }
}

function clearErrors() {
    document.querySelectorAll('.field-error').forEach(el => {
        el.textContent = '';
        el.classList.remove('visible');
    });
    document.querySelectorAll('.input-wrapper.error').forEach(el => {
        el.classList.remove('error');
    });
    const registerPrompt = document.getElementById('register-prompt');
    if (registerPrompt) registerPrompt.classList.add('hidden');
}

// ---------------------------
// Main Logic
// ---------------------------
document.addEventListener('DOMContentLoaded', () => {
    // 1. Pre-fill email if coming from registration
    const registeredEmail = sessionStorage.getItem('registered_email');
    if (registeredEmail) {
        const emailInput = document.getElementById('login-email');
        if (emailInput) {
            emailInput.value = registeredEmail;
            setTimeout(() => {
                const passwordInput = document.getElementById('login-password');
                if (passwordInput) passwordInput.focus();
            }, 300);
        }
    }

    // 2. Success banner for registration
    if (sessionStorage.getItem('just_registered') === 'true') {
        sessionStorage.removeItem('just_registered');
        sessionStorage.removeItem('registered_email');

        const banner = document.createElement('div');
        banner.style.cssText = 'background:linear-gradient(135deg,#10b981,#34d399);color:white;padding:1rem;border-radius:12px;margin-bottom:1.5rem;display:flex;align-items:center;gap:0.75rem;font-weight:600;box-shadow:0 4px 15px rgba(16,185,129,0.3)';
        banner.innerHTML = '<i class="fas fa-check-circle"></i> Account created successfully! Please sign in.';

        const loginForm = document.getElementById('login-form');
        if (loginForm) loginForm.parentElement.insertBefore(banner, loginForm);
    }

    // 3. Email Login Form Submission
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            clearErrors();

            const email = document.getElementById('login-email')?.value.trim();
            const password = document.getElementById('login-password')?.value;

            if (!email || !DermaUtils.isValidEmail(email)) return showError('error-login-email', 'Please enter a valid email');
            if (!password || password.length < 6) return showError('error-login-password', 'Password too short');

            const btn = document.getElementById('btn-login');
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Signing In...';
            btn.disabled = true;

            try {
                const response = await fetch(API_URL + '/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    btn.innerHTML = '<i class="fas fa-check-circle"></i> Login Successful!';
                    btn.style.background = 'linear-gradient(135deg, #10b981, #34d399)';
                    DermaUtils.handleSuccessfulLogin(result.token, result.refresh_token, result.user);
                } else {
                    btn.innerHTML = '<i class="fas fa-sign-in-alt"></i> Sign In';
                    btn.disabled = false;
                    showError('error-login-password', result.error || 'Login failed.');
                }
            } catch (error) {
                btn.innerHTML = '<i class="fas fa-sign-in-alt"></i> Sign In';
                btn.disabled = false;
                showError('error-login-password', 'Server connection error.');
            }
        });
    }

    // 4. Navbar Auth Button Toggle
    const navAuthBtn = document.getElementById('nav-login-hist');
    const tokenToken = localStorage.getItem('dermacare_token');
    if (navAuthBtn && tokenToken) {
        let userName = '';
        try {
            const user = JSON.parse(localStorage.getItem('dermacare_current_user') || '{}');
            userName = user.first_name || user.name || '';
        } catch (e) { }
        navAuthBtn.innerText = `Logout (${userName})`;
        navAuthBtn.addEventListener('click', (e) => {
            e.preventDefault();
            localStorage.removeItem('dermacare_token');
            window.location.href = '/';
        });
    }

    // 5. Apple Sign-In Implementation
    const APPLE_CLIENT_ID = "com.your.app.service";
    const APPLE_REDIRECT_URL = window.location.origin + "/login";

    window.handleAppleLogin = async (response) => {
        const idToken = response.id_token;
        const appleUser = response.user;

        try {
            const apiRes = await fetch(API_URL + '/api/auth/apple', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: idToken, user: appleUser })
            });

            const result = await apiRes.json();
            if (apiRes.ok && result.success) {
                DermaUtils.showToast("Apple Login Successful ✅", "success");
                DermaUtils.handleSuccessfulLogin(result.token, result.refresh_token, result.user);
            } else {
                alert(result.error || 'Apple login failed ❌');
            }
        } catch (error) {
            console.error('[ERROR] Apple Login error:', error);
        }
    };

    if (typeof AppleID !== 'undefined') {
        AppleID.auth.init({
            clientId: APPLE_CLIENT_ID,
            scope: 'name email',
            redirectURI: APPLE_REDIRECT_URL,
            state: 'login_state',
            usePopup: true
        });

        document.addEventListener('AppleIDSignInOnSuccess', (event) => {
            window.handleAppleLogin(event.detail.data);
        });
        document.addEventListener('AppleIDSignInOnFailure', (event) => {
            console.error('Apple Sign-In failed:', event.detail.error);
        });
    }
});

// 6. Google Sign-In Trigger
window.googleLogin = function () {
    window.location.href = API_URL + "/api/auth/google/login";
};

// Handle OAuth Return from Backend Redirect
document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    const userStr = urlParams.get('user');

    if (token) {
        try {
            const user = userStr ? JSON.parse(decodeURIComponent(userStr)) : { role: 'User' };
            window.history.replaceState({}, document.title, window.location.pathname);
            DermaUtils.showToast("Google Login Successful ✅", "success");
            DermaUtils.handleSuccessfulLogin(token, token, user);
        } catch (e) {
            console.error("Failed to parse Google login data:", e);
        }
    }
});
