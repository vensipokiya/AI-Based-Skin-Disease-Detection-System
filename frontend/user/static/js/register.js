const API_BASE = window.DERMACARE_API_BASE || 'http://127.0.0.1:8000';

// ---------------------------
// Multi-Step Form Logic
// ---------------------------
let currentStep = 1;
const totalSteps = 3;

window.nextStep = function(step) {
    if (!validateStep(step)) return;

    const currentEl = document.getElementById(`form-step-${step}`);
    const nextEl = document.getElementById(`form-step-${step + 1}`);
    if (currentEl) currentEl.classList.remove('active');
    if (nextEl) nextEl.classList.add('active');

    const nextIndicator = document.getElementById(`step-indicator-${step + 1}`);
    const nextLine = document.getElementById(`progress-line-${step}`);
    if (nextIndicator) nextIndicator.classList.add('active');
    if (nextLine) nextLine.classList.add('active');

    currentStep = step + 1;
    window.scrollTo({ top: 0, behavior: 'smooth' });
};

window.prevStep = function(step) {
    const currentEl = document.getElementById(`form-step-${step}`);
    const prevEl = document.getElementById(`form-step-${step - 1}`);
    if (currentEl) currentEl.classList.remove('active');
    if (prevEl) prevEl.classList.add('active');

    const currentIndicator = document.getElementById(`step-indicator-${step}`);
    const prevLine = document.getElementById(`progress-line-${step - 1}`);
    if (currentIndicator) currentIndicator.classList.remove('active');
    if (prevLine) prevLine.classList.remove('active');

    currentStep = step - 1;
};

// ---------------------------
// Validation
// ---------------------------
function validateStep(step) {
    clearErrors();
    let isValid = true;

    if (step === 1) {
        const firstName = document.getElementById('reg-firstname').value.trim();
        const lastName  = document.getElementById('reg-lastname').value.trim();
        const email     = document.getElementById('reg-email').value.trim();
        const contact   = document.getElementById('reg-contact').value.trim();
        const gender    = document.getElementById('reg-gender').value;
        const dob       = document.getElementById('reg-dob').value;
        const age       = document.getElementById('reg-age').value;

        if (!firstName) { showError('error-firstname', 'First name is required'); isValid = false; }
        if (!lastName)  { showError('error-lastname',  'Last name is required');  isValid = false; }
        if (!email) {
            showError('error-email', 'Email is required'); isValid = false;
        } else if (!isValidEmail(email)) {
            showError('error-email', 'Please enter a valid email address'); isValid = false;
        }
        if (!contact) {
            showError('error-contact', 'Contact number is required'); isValid = false;
        } else if (contact.replace(/\D/g, '').length < 10) {
            showError('error-contact', 'Please enter a valid contact number'); isValid = false;
        }
        if (!gender) { showError('error-gender', 'Please select your gender'); isValid = false; }
        if (!dob)    { showError('error-dob',    'Date of birth is required'); isValid = false; }
        if (!age || age < 1 || age > 120) {
            showError('error-age', 'Please enter a valid age (1-120)'); isValid = false;
        }
    }

    if (step === 2) {
        const symptoms = document.getElementById('reg-symptoms').value.trim();
        const duration = document.querySelector('input[name="symptom-duration"]:checked');
        const previous = document.querySelector('input[name="previous-conditions"]:checked');

        if (!symptoms)  { showError('error-symptoms',  'Please describe your symptoms'); isValid = false; }
        if (!duration)  { showError('error-duration',  'Please select the duration of your symptoms'); isValid = false; }
        if (!previous)  { showError('error-previous',  'Please indicate if you have previous skin conditions'); isValid = false; }
    }

    if (step === 3) {
        const password        = document.getElementById('reg-password').value;
        const confirmPassword = document.getElementById('reg-confirm-password').value;
        const terms           = document.getElementById('reg-terms').checked;

        if (!password) {
            showError('error-password', 'Password is required'); isValid = false;
        } else if (password.length < 8) {
            showError('error-password', 'Password must be at least 8 characters'); isValid = false;
        }
        if (password !== confirmPassword) {
            showError('error-confirm-password', 'Passwords do not match'); isValid = false;
        }
        if (!terms) { showError('error-terms', 'You must accept the terms and conditions'); isValid = false; }
    }

    return isValid;
}

function showError(elementId, message) {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = message;
        el.classList.add('visible');
        const wrapper = el.previousElementSibling;
        if (wrapper && wrapper.classList.contains('input-wrapper')) {
            wrapper.classList.add('error');
        }
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
}

function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// ---------------------------
// Toggle Password Visibility
// ---------------------------
window.togglePasswordVisibility = function(inputId, btn) {
    const input = document.getElementById(inputId);
    const icon  = btn.querySelector('i');
    if (input) {
        if (input.type === 'password') {
            input.type = 'text';
            icon.className = 'fas fa-eye-slash';
        } else {
            input.type = 'password';
            icon.className = 'fas fa-eye';
        }
    }
};

// ---------------------------
// Password Strength
// ---------------------------
function handlePasswordInput() {
    const password = this.value;
    let strength = 0;

    const hasLength = password.length >= 8;
    const hasUpper  = /[A-Z]/.test(password);
    const hasLower  = /[a-z]/.test(password);
    const hasNumber = /[0-9]/.test(password);

    if (hasLength) strength++;
    if (hasUpper)  strength++;
    if (hasLower)  strength++;
    if (hasNumber) strength++;

    updateReq('req-length', hasLength);
    updateReq('req-upper',  hasUpper);
    updateReq('req-lower',  hasLower);
    updateReq('req-number', hasNumber);

    const bars   = ['str-bar-1', 'str-bar-2', 'str-bar-3', 'str-bar-4'];
    const colors = ['#ef4444', '#f59e0b', '#38bdf8', '#10b981'];
    const labels = ['Weak', 'Fair', 'Good', 'Strong'];

    bars.forEach((bar, i) => {
        const el = document.getElementById(bar);
        if (el) {
            el.style.backgroundColor = i < strength ? colors[strength - 1] : '#e2e8f0';
        }
    });

    const strengthText = document.getElementById('strength-text');
    if (strengthText) {
        if (password.length === 0) {
            strengthText.textContent = 'Password strength';
            strengthText.style.color = '#94a3b8';
        } else {
            strengthText.textContent = labels[strength - 1] || 'Very Weak';
            strengthText.style.color = colors[strength - 1] || '#ef4444';
        }
    }
}

function updateReq(id, met) {
    const el = document.getElementById(id);
    if (el) {
        el.classList.toggle('met', met);
        el.querySelector('i').className = met ? 'fas fa-check-circle' : 'fas fa-circle';
    }
}

// ---------------------------
// Event Listeners
// ---------------------------
document.addEventListener('DOMContentLoaded', () => {
    const pwInput = document.getElementById('reg-password');
    if (pwInput) pwInput.addEventListener('input', handlePasswordInput);

    // Previous Condition Toggle
    document.querySelectorAll('input[name="previous-conditions"]').forEach(radio => {
        radio.addEventListener('change', function () {
            const detailsDiv = document.getElementById('prev-condition-details');
            if (detailsDiv) {
                detailsDiv.classList.toggle('hidden', this.value !== 'yes');
            }
        });
    });

    // Auto-calculate Age from DOB
    const dobInput = document.getElementById('reg-dob');
    if (dobInput) {
        dobInput.addEventListener('change', function () {
            const dob   = new Date(this.value);
            const today = new Date();
            let age = today.getFullYear() - dob.getFullYear();
            const monthDiff = today.getMonth() - dob.getMonth();
            if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dob.getDate())) age--;
            if (age > 0 && age <= 120) {
                const ageInput = document.getElementById('reg-age');
                if (ageInput) ageInput.value = age;
            }
        });
    }

    // Form Submission
    const regForm = document.getElementById('register-form');
    if (regForm) {
        regForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            if (!validateStep(3)) return;

            const btn = document.getElementById('btn-register');
            if (!btn) return;
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating Account...';
            btn.disabled = true;

            const formData = {
                first_name:                  document.getElementById('reg-firstname').value.trim(),
                last_name:                   document.getElementById('reg-lastname').value.trim(),
                email:                       document.getElementById('reg-email').value.trim(),
                password:                    document.getElementById('reg-password').value,
                contact_number:              document.getElementById('reg-contact').value.trim(),
                gender:                      document.getElementById('reg-gender').value,
                date_of_birth:               document.getElementById('reg-dob').value,
                age:                         parseInt(document.getElementById('reg-age').value),
                symptoms:                    document.getElementById('reg-symptoms').value.trim(),
                symptom_duration:            document.querySelector('input[name="symptom-duration"]:checked')?.value || 'Less than 1 week',
                previous_conditions:         document.querySelector('input[name="previous-conditions"]:checked')?.value || 'no',
                previous_condition_details:  document.getElementById('reg-prev-details')?.value.trim() || ''
            };

            try {
                const response = await fetch(API_BASE + '/api/auth/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    localStorage.removeItem('dermacare_token');
                    localStorage.removeItem('dermacare_refresh_token');
                    localStorage.removeItem('dermacare_logged_in');

                    console.log('[OK] Registration successful! User ID:', result.user_id);

                    sessionStorage.setItem('registered_email', formData.email);
                    sessionStorage.setItem('just_registered', 'true');

                    const successModal = document.getElementById('success-modal');
                    if (successModal) {
                        successModal.classList.remove('hidden');
                        document.body.style.overflow = 'hidden';
                    }

                    setTimeout(() => { window.location.href = '/login'; }, 2500);
                } else {
                    btn.innerHTML = originalText;
                    btn.disabled  = false;

                    const errorMsg = result.error || result.detail || 'Unknown error';

                    if (errorMsg === 'Email already registered' || errorMsg === 'Email already exists') {
                        showError('error-email', 'This email is already registered. Please sign in instead.');

                        ['form-step-3', 'step-indicator-3', 'step-indicator-2', 'progress-line-2', 'progress-line-1']
                            .forEach(id => document.getElementById(id)?.classList.remove('active'));
                        document.getElementById('form-step-1')?.classList.add('active');
                        currentStep = 1;
                    } else {
                        alert('Registration failed: ' + (Array.isArray(errorMsg) ? JSON.stringify(errorMsg) : errorMsg));
                    }
                }
            } catch (error) {
                console.error('Registration error:', error);
                btn.innerHTML = originalText;
                btn.disabled  = false;
                alert('Could not connect to the server. Please make sure the backend is running.');
            }
        });
    }

    // ---------------------------
    // Apple Sign-In
    // ---------------------------
    const APPLE_CLIENT_ID  = "com.your.app.service";
    const APPLE_REDIRECT_URL = window.location.origin + "/register";

    window.handleAppleRegister = async (response) => {
        const idToken   = response.id_token;
        const appleUser = response.user;

        console.log("[OK] Received Apple ID Token (Register)");

        try {
            const apiRes = await fetch(API_BASE + '/api/auth/apple', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: idToken, user: appleUser })
            });

            const result = await apiRes.json();
            if (apiRes.ok && result.success) {
                DermaUtils.handleSuccessfulLogin(result.token, result.refresh_token, result.user);
            } else {
                alert(result.error || 'Apple registration failed.');
            }
        } catch (error) {
            console.error('[ERROR] Apple Reg error:', error);
        }
    };

    if (typeof AppleID !== 'undefined') {
        AppleID.auth.init({
            clientId:    APPLE_CLIENT_ID,
            scope:       'name email',
            redirectURI: APPLE_REDIRECT_URL,
            state:       'reg_state',
            usePopup:    true
        });
        document.addEventListener('AppleIDSignInOnSuccess', (event) => {
            window.handleAppleRegister(event.detail.data);
        });
    }

    // Nav Login/Logout button
    const navAuthBtn = document.getElementById('nav-login-hist');
    const token      = localStorage.getItem('dermacare_token');

    if (navAuthBtn) {
        if (token) {
            let userName = '';
            try {
                const user = JSON.parse(localStorage.getItem('dermacare_current_user') || '{}');
                userName = user.first_name || user.name || '';
            } catch (e) { /* ignore */ }

            navAuthBtn.innerText  = userName ? `Logout (${userName})` : 'Logout';
            navAuthBtn.href       = '#';
            navAuthBtn.className  = 'btn btn-secondary';

            navAuthBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                try {
                    await fetch(API_BASE + '/api/auth/logout', {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                } catch (err) { /* ignore network error */ } finally {
                    localStorage.removeItem('dermacare_token');
                    window.location.href = '/';
                }
            });
        } else {
            navAuthBtn.innerText = 'Login';
            navAuthBtn.href      = '/login';
            navAuthBtn.className = 'btn btn-secondary';
        }
    }
});


window.closeSuccessModal = function() {
    const successModal = document.getElementById('success-modal');
    if (successModal) successModal.classList.add('hidden');
    document.body.style.overflow = '';
};

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeSuccessModal();
});
