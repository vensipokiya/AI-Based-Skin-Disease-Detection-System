const API_BASE = window.DERMACARE_API_BASE || 'http://127.0.0.1:8000';

// ---------------------------
// Toggle Password Visibility
// ---------------------------
function togglePasswordVisibility(inputId, btn) {
    const input = document.getElementById(inputId);
    const icon = btn.querySelector('i');
    if (input.type === 'password') {
        input.type = 'text';
        icon.className = 'fas fa-eye-slash';
    } else {
        input.type = 'password';
        icon.className = 'fas fa-eye';
    }
}

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

function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// ---------------------------
// Helper: After successful login
// ---------------------------
function handleSuccessfulLogin(token, refreshToken, user) {
    const btn = document.getElementById('btn-login');

    // Store token and user info for API calls
    localStorage.setItem('dermacare_token', token);
    localStorage.setItem('dermacare_refresh_token', refreshToken);
    localStorage.setItem('dermacare_logged_in', 'true');
    localStorage.setItem('dermacare_current_user', JSON.stringify(user));

    if (user.role === 'Admin') {
        // Clone token specifically for the Admin dashboard panel
        localStorage.setItem('admin_token', token);
    }

    // Show success feedback
    btn.innerHTML = '<i class="fas fa-check-circle"></i> Login Successful!';
    btn.style.background = 'linear-gradient(135deg, #10b981, #34d399)';

    console.log('[OK] Login successful!', user.name || user.email);

    setTimeout(() => {
        if (user.role === 'Admin') {
            window.location.href = 'admin.html';
        } else if (sessionStorage.getItem('pending_scan_result') || sessionStorage.getItem('scan_result')) {
            sessionStorage.setItem('scan_result_authenticated', 'true');
            window.location.href = 'Scan_Result.html';
        } else {
            window.location.href = 'index.html';
        }
    }, 1000);
}

// ---------------------------
// Email/Password Login -> Backend API
// ---------------------------
document.addEventListener('DOMContentLoaded', () => {
    // 1. Immediately pre-fill email if coming from registration (Highest Priority)
    const registeredEmail = sessionStorage.getItem('registered_email');
    console.log('[DEBUG] Initial check for registered email:', registeredEmail);
    
    if (registeredEmail) {
        const emailInput = document.getElementById('login-email');
        if (emailInput) {
            emailInput.value = registeredEmail;
            console.log('[DEBUG] Pre-filled email input:', registeredEmail);
            
            // Set a small delay to ensure it's not cleared by autocomplete
            setTimeout(() => {
                if (emailInput.value !== registeredEmail) {
                    emailInput.value = registeredEmail;
                    console.log('[DEBUG] Reinforced pre-filled email.');
                }
                
                // Focus the password field so the user only needs to type their password
                const passwordInput = document.getElementById('login-password');
                if (passwordInput) {
                    passwordInput.focus();
                    console.log('[DEBUG] Focused password input.');
                }
            }, 300);
            
            // Note: sessionStorage.removeItem('registered_email') is handled below or after success
        }
    }

    // 2. Show success banner if arriving from registration
    if (sessionStorage.getItem('just_registered') === 'true') {
        sessionStorage.removeItem('just_registered');
        // If we found an email, keep it for a bit longer just in case of reload, but then remove
        sessionStorage.removeItem('registered_email');

        // Inject a styled success banner at the top of the form
        const banner = document.createElement('div');
        banner.id = 'reg-success-banner';
        banner.style.cssText = [
            'background: linear-gradient(135deg, #10b981, #34d399)',
            'color: white',
            'padding: 1rem 1.5rem',
            'border-radius: 12px',
            'margin-bottom: 1.5rem',
            'display: flex',
            'align-items: center',
            'gap: 0.75rem',
            'font-weight: 600',
            'font-size: 0.95rem',
            'box-shadow: 0 4px 15px rgba(16,185,129,0.3)'
        ].join(';');
        banner.innerHTML = '<i class="fas fa-check-circle" style="font-size:1.4rem"></i>' +
            '<div><div>Account created successfully!</div>' +
            '<div style="font-weight:400;font-size:0.85rem;opacity:0.9">Please sign in with your new credentials below.</div></div>';

        const loginForm = document.getElementById('login-form');
        if (loginForm) loginForm.parentElement.insertBefore(banner, loginForm);

        // Auto-scroll banner into view
        banner.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            clearErrors();

            const emailInput = document.getElementById('login-email');
            const passwordInput = document.getElementById('login-password');
            if(!emailInput || !passwordInput) return;

            const email = emailInput.value.trim();
            const password = passwordInput.value;
            let isValid = true;

            if (!email) {
                showError('error-login-email', 'Email address is required');
                isValid = false;
            } else if (!isValidEmail(email)) {
                showError('error-login-email', 'Please enter a valid email address');
                isValid = false;
            }

            if (!password) {
                showError('error-login-password', 'Password is required');
                isValid = false;
            } else if (password.length < 6) {
                showError('error-login-password', 'Password must be at least 6 characters');
                isValid = false;
            }

            if (!isValid) return;

            // Show loading state
            const btn = document.getElementById('btn-login');
            if(!btn) return;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Signing In...';
            btn.disabled = true;

            try {
                const response = await fetch(API_BASE + '/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    handleSuccessfulLogin(result.token, result.refresh_token, result.user);
                } else {
                    // Support both FastAPI's 'detail' and custom 'error' fields
                    const errorMsg = result.error || result.detail || 'Login failed. Please try again.';

                    btn.innerHTML = '<i class="fas fa-sign-in-alt"></i> Sign In';
                    btn.disabled = false;

                    if (errorMsg === 'Email not registered' || errorMsg === 'User not found') {
                        showError('error-login-email', 'This email is not registered. Please register first.');
                        const registerPrompt = document.getElementById('register-prompt');
                        if (registerPrompt) registerPrompt.classList.remove('hidden');
                    } else if (errorMsg === 'Incorrect password' || errorMsg === 'Invalid email or password') {
                        showError('error-login-password', 'Incorrect password or email. Please try again.');
                    } else {
                        showError('error-login-password', errorMsg);
                    }
                }
            } catch (error) {
                console.error('[ERROR] Login error:', error);
                btn.innerHTML = '<i class="fas fa-sign-in-alt"></i> Sign In';
                btn.disabled = false;
                showError('error-login-password', 'Could not connect to server. Make sure the backend is running.');
            }
        });
    }

    // Set Login/Logout Button based on Auth
    const navAuthBtn = document.getElementById('nav-login-hist');
    const token = localStorage.getItem('dermacare_token');

    if (navAuthBtn) {
        if (token) {
            // User is logged in
            let userName = '';
            try {
                const user = JSON.parse(localStorage.getItem('dermacare_current_user') || '{}');
                userName = user.first_name || user.name || '';
            } catch (e) { }

            navAuthBtn.innerText = userName ? `Logout (${userName})` : 'Logout';
            navAuthBtn.href = '#';
            navAuthBtn.className = 'btn btn-secondary';

            navAuthBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                try {
                    await fetch(API_BASE + '/api/auth/logout', {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${token}`
                        }
                    });
                } catch (err) {
                    console.error('Logout error:', err);
                } finally {
                    localStorage.removeItem('dermacare_token');
                    window.location.href = 'index.html';
                }
            });
        } else {
            // User is NOT logged in
            navAuthBtn.innerText = 'Login';
            navAuthBtn.href = 'login.html';
            navAuthBtn.className = 'btn btn-secondary';
        }
    }
    
    // Google/Apple placeholders
    const gBtn = document.getElementById('btn-google-login');
    if(gBtn) gBtn.addEventListener('click', () => alert('Google login requires OAuth2 setup.\nThis feature will be available soon.'));
    
    const aBtn = document.getElementById('btn-apple-login');
    if(aBtn) aBtn.addEventListener('click', () => alert('Apple login requires OAuth2 setup.\nThis feature will be available soon.'));
});
