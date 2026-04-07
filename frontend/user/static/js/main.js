/* API base: set by dermacare-api.js if included before this script */
var API_URL = (typeof window !== 'undefined' && window.DERMACARE_API_BASE) ? window.DERMACARE_API_BASE : 'http://127.0.0.1:8000';

// State
let videoStream = null;

// DOM Elements
const pages = {
    splash: document.getElementById('splash-screen'),
    dashboard: document.getElementById('dashboard'),
    detection: document.getElementById('detection-page'),
    result: document.getElementById('result-page'),
    nearby: document.getElementById('nearby-dermatologists'),
    login: document.getElementById('login-page'),
    details: document.getElementById('dermatologist-details'),
    booking: document.getElementById('booking-page')
};

const header = document.getElementById('main-header');

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    // -----------------------------------------
    // Set Login/Logout Button based on Auth
    // -----------------------------------------
    const navAuthBtn = document.getElementById('nav-login-hist');
    const token = localStorage.getItem('dermacare_token');


    if (navAuthBtn) {
        if (token) {
            // User is logged in
            let userName = 'User';
            try {
                const user = JSON.parse(localStorage.getItem('dermacare_current_user') || '{}');
                userName = user.first_name || user.name || 'User';
            } catch (e) { }

            // Replace standard login button with a profile box
            const userActions = document.getElementById('header-user-actions');
            if (userActions) {
                userActions.innerHTML = `
                    <div class="user-profile-box">
                        <img src="https://i.pravatar.cc/150?u=${userName}" alt="Avatar" class="user-avatar">
                        <span class="user-name">${userName}</span>
                        <a href="#" class="logout-link" id="btn-logout">Logout</a>
                    </div>
                `;

                const logoutBtn = document.getElementById('btn-logout');
                if (logoutBtn) {
                    logoutBtn.addEventListener('click', async (e) => {
                        e.preventDefault();
                        try {
                            await fetch(API_URL + '/api/auth/logout', {
                                method: 'POST',
                                headers: { 'Authorization': `Bearer ${token}` }
                            });
                        } catch (err) {
                            console.error('Logout error:', err);
                        } finally {
                            localStorage.removeItem('dermacare_token');
                            window.location.href = '/';
                        }
                    });
                }
            }
        } else {
            // User is NOT logged in
            navAuthBtn.innerText = 'Login';
            navAuthBtn.href = '/login';
            navAuthBtn.className = 'btn btn-secondary';
        }
    }

    // Completely Hide 'History' link from Navigation if NOT logged in
    const historyLinks = document.querySelectorAll("ul.nav-links a[href='/history']");
    historyLinks.forEach(link => {
        if (!token) {
            if (link.parentElement && link.parentElement.tagName === 'LI') {
                link.parentElement.style.display = 'none';
            }
        }
    });

    // If splash screen exists (Home Page)
    if (pages.splash) {
        setTimeout(() => {
            pages.splash.classList.add('fade-out');
            pages.splash.style.display = 'none';
            if (header) header.classList.remove('hidden');
            showPage('dashboard');
        }, 3500);
    }
    // If no splash screen (Detection Page)
    else if (pages.detection) {
        if (header) header.classList.remove('hidden');
        showPage('detection');

        // Toggle guest warning on detection page
        const guestBanner = document.getElementById('guest-mode-warning');
        if (guestBanner) {
            guestBanner.style.display = token ? 'none' : 'inline-flex';
            guestBanner.classList.toggle('hidden', !!token);
        }
    }

    // If on Scan_Result.html — load result from sessionStorage
    const resultPage = document.getElementById('result-page');
    if (resultPage && !pages.detection && !pages.splash) {
        if (header) header.classList.remove('hidden');

        const storedResult = sessionStorage.getItem('scan_result');
        const isAuthenticated = sessionStorage.getItem('scan_result_authenticated') === 'true';

        if (storedResult) {
            const result = JSON.parse(storedResult);
            displayResult(result);

            const blurContainer = document.getElementById('result-content-container');
            const authOverlay = document.getElementById('result-auth-overlay');

            if (isAuthenticated) {
                // User is logged in — show full results
                if (blurContainer) blurContainer.style.filter = 'none';
                if (authOverlay) authOverlay.classList.add('hidden');
            } else {
                // Not logged in — blur results and show auth overlay
                sessionStorage.setItem('pending_scan_result', storedResult);
                if (blurContainer) {
                    blurContainer.style.filter = 'blur(12px)';
                    blurContainer.style.pointerEvents = 'none';
                    blurContainer.style.userSelect = 'none';
                }
                if (authOverlay) {
                    authOverlay.classList.remove('hidden');
                    authOverlay.style.display = 'flex';
                }
            }
        } else {
            // No scan result found — redirect back to detection
            window.location.href = '/detect';
        }
    }

    // Fetch and display user activity if on dashboard and logged in
    const activityWidget = document.getElementById('user-activity-dashboard');
    if (activityWidget && token) {
        // Widget removed as per user request
    }
});

// Navigation
function showPage(pageId) {
    // Hide all pages
    Object.values(pages).forEach(page => {
        if (page && page.id !== 'splash-screen') {
            page.classList.add('hidden');
            page.classList.remove('fade-in');
        }
    });

    // Show specific page
    const target = pages[pageId];
    if (target) {
        target.classList.remove('hidden');
        target.classList.add('fade-in');
    } else {
        // Redirect to separate files if sections are missing (Refactoring)
        if (pageId === 'nearby') window.location.href = '/nearby';
        if (pageId === 'details' || pageId === 'booking') window.location.href = '/booking';
        return;
    }

    // Stop camera if leaving detection page
    if (pageId !== 'detection' && videoStream) {
        stopCamera();
    }

    // Custom hook for booking page to populate the doctor name
    if (pageId === 'booking') {
        let docName = 'Selected Dermatologist';
        try {
            const stored = localStorage.getItem('selectedDoctorDetails');
            if (stored) docName = JSON.parse(stored).name;
        } catch (e) { }

        const nameEl = document.getElementById('booking-doctor-name');
        if (nameEl) nameEl.textContent = docName;

        // Reset sub-cards dynamically
        const form = document.getElementById('booking-form');
        const confirmationCard = document.getElementById('booking-confirmation-card');
        if (form) form.style.display = 'block';
        if (confirmationCard) confirmationCard.style.display = 'none';
    }

    // Trigger map load if navigating to nearby
    if (pageId === 'nearby') {
        loadGoogleMapsNearby();
    }
}

// Event Listeners for Navigation (Replaced inline JS)
document.addEventListener('DOMContentLoaded', () => {
    const attachListener = (id, event, handler) => {
        const el = document.getElementById(id);
        if (el) el.addEventListener(event, handler);
    };

    attachListener('nav-home', 'click', (e) => {
        if (pages.dashboard) {
            e.preventDefault();
            showPage('dashboard');
        }
    });
    attachListener('btn-nearby-suggestions', 'click', () => showPage('nearby'));
    attachListener('btn-demo-book', 'click', checkLoginAndBook);
    attachListener('btn-back-result', 'click', () => showPage('result'));
});

// Camera Handling
async function startCamera() {
    const video = document.getElementById('camera-feed');
    const cameraInitial = document.getElementById('camera-initial');
    const cameraUi = document.getElementById('camera-ui');

    try {
        videoStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
        video.srcObject = videoStream;
        video.style.display = 'block';
        
        // Ensure video plays
        await video.play();

        if (cameraInitial) cameraInitial.classList.add('hidden');
        if (cameraUi) cameraUi.classList.remove('hidden');

    } catch (err) {
        console.error("Camera error:", err);
        alert("Could not access camera. Please allow permissions.");
    }
}

function stopCamera() {
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
        videoStream = null;
    }

    // Reset UI
    const cameraInitial = document.getElementById('camera-initial');
    const cameraUi = document.getElementById('camera-ui');

    if (cameraUi) cameraUi.classList.add('hidden');
    if (cameraInitial) cameraInitial.classList.remove('hidden');
}

function stopCameraAndReset() {
    stopCamera();
}

function switchTab(tab) {
    const uploadBtn = document.getElementById('tab-upload');
    const cameraBtn = document.getElementById('tab-camera');
    const uploadView = document.getElementById('upload-view');
    const cameraView = document.getElementById('camera-view');

    if (!uploadBtn || !cameraBtn || !uploadView || !cameraView) return;

    if (tab === 'camera') {
        uploadBtn.classList.remove('active');
        cameraBtn.classList.add('active');
        uploadView.classList.add('hidden');
        cameraView.classList.remove('hidden');
    } else {
        cameraBtn.classList.remove('active');
        uploadBtn.classList.add('active');
        cameraView.classList.add('hidden');
        uploadView.classList.remove('hidden');
        stopCameraAndReset();
    }
}

function captureImage() {
    const video = document.getElementById('camera-feed');
    const canvas = document.getElementById('camera-canvas');

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);

    // Convert to blob/file and predict
    canvas.toBlob(blob => {
        const file = new File([blob], "capture.jpg", { type: "image/jpeg" });
        handleFileUpload(file);
    }, 'image/jpeg');

    stopCamera();
}

// File Upload
function handleFiles(files) {
    if (files.length > 0) {
        handleFileUpload(files[0]);
    }
}

// Prediction Logic
async function handleFileUpload(file) {
    const status = document.getElementById('upload-status');
    status.innerHTML = `<i class="fas fa-check-circle" style="color: var(--primary-color);"></i> Image uploaded successfully! Analyzing...`;
    status.style.color = "var(--primary-color)";

    // Show image preview
    const reader = new FileReader();
    reader.onload = function (e) {
        let preview = document.getElementById('uploaded-preview');
        const uploadContent = document.getElementById('upload-content');

        if (!preview) {
            preview = document.createElement('img');
            preview.id = 'uploaded-preview';
            preview.style.width = '100%';
            preview.style.height = '150px';
            preview.style.objectFit = 'cover';
            preview.style.borderRadius = '8px';
            preview.style.marginTop = '1rem';
            preview.style.marginBottom = '1rem';

            // Hide other elements in the card temporarily to focus on the image
            if (uploadContent) {
                Array.from(uploadContent.children).forEach(child => {
                    if (child.tagName !== 'INPUT' && child.tagName !== 'BUTTON') {
                        child.classList.add('hidden');
                    }
                });
                uploadContent.insertBefore(preview, uploadContent.querySelector('button'));
            }
        }
        preview.src = e.target.result;
        sessionStorage.setItem('uploaded_image_base64', e.target.result);
    }
    reader.readAsDataURL(file);

    try {
        const formData = new FormData();
        formData.append('file', file);

        // Include auth token if logged in
        const headers = {};
        const token = localStorage.getItem('dermacare_token');
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(`${API_URL}/api/predict`, { method: 'POST', headers, body: formData });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();

        // Near-instant redirect
        setTimeout(() => {
            status.innerHTML = "";

            // Save result to sessionStorage so scan_result.html can read it
            sessionStorage.setItem('scan_result', JSON.stringify(result));
            sessionStorage.setItem('scan_result_authenticated', token ? 'true' : 'false');

            // Redirect to the dedicated result page
            window.location.href = '/scan-result';
        }, 50);

    } catch (error) {
        console.error("Error:", error);
        status.innerText = "Error analyzing image. Ensure backend is running.";

        // Fallback for demo if fetch fails
        // alert("Backend not responding. Showing demo result.");
        // const demoResult = {
        //     disease: "Eczema (Demo)",
        //     confidence: 90.0,
        //     remedy: ["Keep skin moisturized", "Avoid stress"]
        // };
        // displayResult(demoResult);
        // showPage('result-page');
    }
}

function displayResult(data) {
    // ── Disease name & confidence ───────────────────────────────────────────
    const diseaseEl = document.getElementById('disease-name');
    if (diseaseEl) diseaseEl.innerText = data.disease;

    const confidenceText = document.getElementById('confidence-text');
    if (confidenceText) confidenceText.innerText = data.confidence + "%";

    // ── Show uploaded image ─────────────────────────────────────────────────
    const scannedImageFinal = document.getElementById('scanned-image-final');
    if (scannedImageFinal) {
        // Priority 1: Use base64 returned directly from the AI API
        // Priority 2: Use locally stored preview as fallback
        const uploadedImg = (data.image_base64) ? `data:image/jpeg;base64,${data.image_base64}` : sessionStorage.getItem('uploaded_image_base64');
        
        if (uploadedImg) {
            scannedImageFinal.src = uploadedImg;
            // Show image: new HTML uses a wrapper div
            const imgWrap = document.getElementById('scanned-image-wrap');
            if (imgWrap) imgWrap.style.display = 'block';
            else scannedImageFinal.style.display = 'block';
        }
    }

    // ── Accuracy level & colour ─────────────────────────────────────────────
    const accuracyIndicator = document.getElementById('accuracy-indicator');
    const accuracyLevel = document.getElementById('accuracy-level');
    let accColor = '#3b82f6';
    if (accuracyIndicator && accuracyLevel) {
        accuracyIndicator.style.display = 'inline-block';
        let levelLabel = 'LOW';
        let accColor = '#ef4444'; // Red for LOW
        let accBg = 'rgba(239, 68, 68, 0.1)';

        if (data.confidence >= 80) {
            levelLabel = 'HIGH';
            accColor = '#3b82f6'; // Blue
            accBg = 'rgba(59, 130, 246, 0.1)';
        } else if (data.confidence >= 50) {
            levelLabel = 'MEDIUM';
            accColor = '#f59e0b'; // Amber
            accBg = 'rgba(245, 158, 11, 0.1)';
        }

        accuracyLevel.innerText = levelLabel;
        accuracyIndicator.style.backgroundColor = accBg;
        accuracyIndicator.style.color = accColor;
        accuracyIndicator.style.border = `1px solid ${accColor}`;
    }

    // ── Confidence SVG Ring Animation ──────────────────────────────────────────
    const pctEle = document.getElementById('confidence-pct');
    const ring = document.getElementById('meter-progress-ring');
    if (pctEle) {
        pctEle.innerText = `${Math.round(data.confidence)}%`;
        pctEle.style.color = accColor;
    }
    if (ring) {
        ring.style.stroke = accColor;
        // Circumference is approx 440 (2 * PI * 70)
        const offset = 440 - (440 * data.confidence) / 100;
        // Small delay to trigger the transition after rendering
        setTimeout(() => {
            ring.style.strokeDashoffset = offset;
        }, 100);
    }

    // ── "Find Doctors" button ───────────────────────────────────────────────
    const isNormalSkin = ['normal skin', 'normal'].includes(data.disease.toLowerCase().trim());
    const btnNearby = document.getElementById('btn-find-nearby-doctor');
    if (btnNearby) {
        btnNearby.style.display = (data.confidence >= 60 && !isNormalSkin) ? 'inline-flex' : 'none';
    }

    // ── Top-3 confidence breakdown ──────────────────────────────────────────
    const topPanel = document.getElementById('top-predictions-panel');
    const topList = document.getElementById('top-predictions-list');
    if (topPanel && topList && data.top_predictions && data.top_predictions.length > 0) {
        topPanel.style.display = 'block';
        const barColors = ['#3b82f6', '#94a3b8', '#cbd5e1'];
        topList.innerHTML = data.top_predictions.map((pred, i) => {
            const isTop = i === 0;
            const barColor = barColors[i] || '#e2e8f0';
            return `
                <div style="margin-bottom: 0.75rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
                        <span style="font-size: 0.85rem; font-weight: ${isTop ? '700' : '500'}; color: ${isTop ? '#1e293b' : '#64748b'};">
                            ${isTop ? '🏆 ' : ''}${pred.disease}
                        </span>
                        <span style="font-size: 0.85rem; font-weight: 700; color: ${isTop ? '#3b82f6' : '#94a3b8'};">${pred.confidence}%</span>
                    </div>
                    <div style="height: 6px; background: #e2e8f0; border-radius: 3px; overflow: hidden;">
                        <div style="height: 100%; width: ${Math.min(pred.confidence, 100)}%; background: ${barColor}; border-radius: 3px; transition: width 0.5s ease;"></div>
                    </div>
                </div>`;
        }).join('');
    }
    // ── End Top Predictions ────────────────────────────────────────────────

    // ── Save to history ─────────────────────────────────────────────────────
    saveToHistory(data);

    // ── Disease description ───────────────────────────────────────────────
    const descEl = document.getElementById('disease-description');
    if (descEl && data.remedies) {
        descEl.style.display = data.remedies.description ? 'block' : 'none';
        descEl.innerHTML = `<i class="fas fa-info-circle" style="margin-right:8px;"></i> ${data.remedies.description}`;
    }

    // ── Remedy cards (new card-based layout) ────────────────────────────────
    const grid = document.getElementById('remedy-grid');
    if (grid) {
        // Save & remove disclaimer so we can re-append at the end
        const disclaimer = grid.querySelector('.disclaimer-card');
        grid.innerHTML = '';

        const makeCard = (icon, title, items, cssClass = '') => {
            if (!items || items.length === 0) return '';
            const lis = items.map(item => `<li>${item}</li>`).join('');
            return `
            <div class="remedy-card ${cssClass}" style="min-height: 200px; display: flex; flex-direction: column;">
                <h4><i class="${icon}"></i> ${title}</h4>
                <ul style="flex: 1;">${lis}</ul>
            </div>`;
        };

        if (data.remedies) {
            grid.innerHTML += makeCard('fas fa-home', 'Home Remedies', data.remedies.home_remedies);
            grid.innerHTML += makeCard('fas fa-spa', 'Skincare Routine', data.remedies.skincare_routine);
            grid.innerHTML += makeCard('fas fa-utensils', 'Diet Suggestions', data.remedies.diet_suggestions);

            const doctorAdvice = data.remedies.consult_doctor;
            if (doctorAdvice && doctorAdvice.length > 0 && data.confidence >= 60 && !isNormalSkin) {
                grid.innerHTML += makeCard('fas fa-user-md', 'When to Consult a Doctor', doctorAdvice, 'warning-card');
            }
        } else if (data.remedy) {
            grid.innerHTML += makeCard('fas fa-notes-medical', 'Recommended Remedies', data.remedy);
        }

        // Re-append disclaimer
        if (disclaimer) grid.appendChild(disclaimer);
        else grid.innerHTML += `
        <div class="remedy-card disclaimer-card">
            <h4><i class="fas fa-exclamation-circle"></i> Disclaimer</h4>
            <div style="font-size:0.92rem;color:#334155;line-height:1.7;">
                This AI-based diagnosis is <strong>not a substitute</strong> for professional
                medical advice. Always consult a licensed dermatologist for a confirmed diagnosis.
            </div>
        </div>`;

    } else {
        // Legacy fallback: old HTML used #remedy-list
        const list = document.getElementById('remedy-list');
        if (!list) return;
        list.innerHTML = '';
        if (data.remedies) {
            const createSection = (title, items, icon) => {
                if (!items || items.length === 0) return '';
                let html = `<div class="remedy-section"><h4 style="color:var(--primary-color);margin:1rem 0;"><i class="${icon}"></i> ${title}</h4>`;
                items.forEach(item => { html += `<div class="remedy-item">${item}</div>`; });
                return html + '</div>';
            };
            list.innerHTML += createSection('Home Remedies', data.remedies.home_remedies, 'fas fa-home');
            list.innerHTML += createSection('Skincare Routine', data.remedies.skincare_routine, 'fas fa-spa');
            list.innerHTML += createSection('Diet Suggestions', data.remedies.diet_suggestions, 'fas fa-utensils');
        }
    }
}


// Save prediction to history (API + localStorage fallback)
function saveToHistory(data) {
    try {
        const token = localStorage.getItem('dermacare_token');
        if (!token) {
            // Only save to localStorage if NOT logged in!
            // If logged in, the Python backend already saved it to MySQL.
            const history = JSON.parse(localStorage.getItem('dermacare_history') || '[]');
            history.push({
                disease: data.disease,
                confidence: data.confidence,
                remedies: data.remedies || null,
                date: new Date().toISOString()
            });
            localStorage.setItem('dermacare_history', JSON.stringify(history));
        }

        // Note: The backend /predict endpoint already saves the result 
        // to the database if the user is logged in, so we don't fetch here.
    } catch (e) {
        console.error('Failed to save to history:', e);
    }
}

// Login & Nearby Logic
function checkLoginAndBook(dataStr) {
    if (dataStr) {
        try {
            const data = JSON.parse(decodeURIComponent(dataStr));
            localStorage.setItem('selectedDoctorDetails', JSON.stringify(data));
        } catch (e) {
            console.error("Failed to parse doctor data", e);
        }
    }

    const isLoggedIn = localStorage.getItem('dermacare_token');
    if (!isLoggedIn) {
        window.location.href = '/login';
    } else {
        window.location.href = '/booking';
    }
}

function handleBooking(event) {
    event.preventDefault();
    const dateInput = document.getElementById('booking-date');
    const timeInput = document.getElementById('booking-time');

    if (dateInput && dateInput.value && timeInput && timeInput.value) {
        const selectedDate = new Date(dateInput.value);
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        if (selectedDate < today) {
            alert("Error: Please select a current or future date.");
            return;
        }

        // If it's today, check the time
        if (selectedDate.getTime() === today.getTime()) {
            const now = new Date();
            const [hours, minutes] = timeInput.value.split(':');
            const selectedTime = new Date();
            selectedTime.setHours(parseInt(hours), parseInt(minutes), 0, 0);

            if (selectedTime <= now) {
                alert("Error: Please select a future time for today's appointment.");
                return;
            }
        }

        // Format the date string (DD-MM-YYYY)
        const dateParts = dateInput.value.split('-'); // YYYY-MM-DD
        const formattedDate = `${dateParts[2]}-${dateParts[1]}-${dateParts[0]}`;

        // Format the time string (12H AM/PM)
        const timeParts = timeInput.value.split(':');
        let hour = parseInt(timeParts[0], 10);
        const minute = timeParts[1];
        const ampm = hour >= 12 ? 'PM' : 'AM';
        const formattedHour = hour % 12 || 12;
        const formattedTime = `${formattedHour}:${minute} ${ampm}`;

        // Save pending appointment data for the confirmation page (using raw values for backend)
        localStorage.setItem('pendingAppointment', JSON.stringify({
            date: dateInput.value, // YYYY-MM-DD
            time: timeInput.value + ":00" // HH:MM:SS
        }));


        // Redirect to the new confirmation page if not already there
        if (!window.location.href.includes('/confirm-booking')) {
            window.location.href = '/confirm-booking';
        }
    }
}

function cancelBookingConfirmation() {
    // This is now handled by browser back or explicit links in the new confirmation page
    window.location.href = '/booking';
}

async function finalizeBooking() {
    const token = localStorage.getItem('dermacare_token');
    const doctorData = JSON.parse(localStorage.getItem('selectedDoctorDetails') || '{}');
    const bookingData = JSON.parse(localStorage.getItem('pendingAppointment') || '{}');

    if (!token) {
        alert("Session expired. Please log in again.");
        window.location.href = '/login';
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/user/appointments`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                doctor_name: doctorData.name || "Unknown Doctor",
                doctor_specialty: doctorData.typeLabel || "Specialist",
                doctor_area: doctorData.area || doctorData.address || "Unknown Area",
                doctor_city: doctorData.city || "Unknown City",
                appointment_date: bookingData.date,
                appointment_time: bookingData.time
            })

        });

        const result = await response.json();

        if (response.ok) {
            // ... (rest of the success notification logic)
            // Show beautiful success notification
            const notification = document.createElement('div');
            notification.className = 'booking-success-notification';
            Object.assign(notification.style, {
                position: 'fixed', bottom: '20px', right: '20px',
                background: '#10b981', color: 'white', padding: '1rem 2rem',
                borderRadius: '8px', boxShadow: '0 4px 15px rgba(0,0,0,0.2)',
                zIndex: '9999', display: 'flex', alignItems: 'center',
                gap: '10px', fontWeight: '600', animation: 'slideInRight 0.3s ease-out forwards'
            });
            notification.innerHTML = '<i class="fas fa-check-circle" style="font-size: 1.5rem;"></i> Booking Confirmed Successfully!';

            const style = document.createElement('style');
            style.textContent = `
                @keyframes slideInRight { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
                @keyframes fadeOutDown { from { transform: translateY(0); opacity: 1; } to { transform: translateY(100%); opacity: 0; } }
            `;
            document.head.appendChild(style);
            document.body.appendChild(notification);

            // Clear local storage
            localStorage.removeItem('pendingAppointment');
            localStorage.removeItem('selectedDoctorDetails');

            // Auto remove notification and redirect
            setTimeout(() => {
                notification.style.animation = 'fadeOutDown 0.3s ease-in forwards';
                setTimeout(() => {
                    notification.remove();
                    window.location.href = '/';
                }, 300);
            }, 3000);
        } else if (response.status === 401) {
            // Token is invalid or expired
            localStorage.removeItem('dermacare_token');
            alert('Your session has expired or is invalid. Please log in again.');
            window.location.href = '/login';
        } else {
            alert(`Booking failed: ${result.error || result.detail || result.message || 'Unknown error'}`);
        }
    } catch (err) {
        console.error("Booking Error:", err);
        alert("Failed to connect to server. Please try again later.");
    }
}


// Leaflet.js + OpenStreetMap Integration (Free - No API Key Required)
let mapLoaded = false;
let leafletMap = null;
let userMarker = null;   // draggable / click-set marker

// ──── Initialise map & get user location ────────────────────────────────────
function loadGoogleMapsNearby() {
    mapLoaded = false;

    const list = document.getElementById("dermatologist-list");
    const mapContainer = document.getElementById('map-container');
    const loading = document.getElementById('loading-doctors');

    if (!window.L) { console.warn("Leaflet.js not loaded."); return; }

    if (list) list.style.display = 'none';
    if (loading) loading.style.display = 'block';

    // ── Better Location Strategy ──
    const handleSuccess = (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        const acc = pos.coords.accuracy || 1000;
        console.log(`[Geo] Success: ${lat}, ${lng} (acc: ${acc}m)`);
        initMapAtPosition(lat, lng, list, mapContainer, loading, acc);
    };

    const handleFallback = async () => {
        console.warn('[Geo] Using IP fallback...');
        try {
            const resp = await fetch('https://ipapi.co/json/');
            const data = await resp.json();
            if (data.latitude && data.longitude) {
                console.log(`[Geo] IP Fallback: ${data.city}, ${data.region}`);
                initMapAtPosition(data.latitude, data.longitude, list, mapContainer, loading, 10000); // 10km accuracy for IP
            } else {
                throw new Error('IP Geo failed');
            }
        } catch (e) {
            // Final fallback: Ahmedabad
            initMapAtPosition(23.0225, 72.5714, list, mapContainer, loading, 99999);
        }
    };

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(handleSuccess, handleFallback, {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        });
    } else {
        handleFallback();
    }
}

// ──── Core: build the map at a position ─────────────────────────────────────
function initMapAtPosition(lat, lng, list, mapContainer, loading, accuracyMetres) {
    if (loading) loading.style.display = 'none';
    if (mapContainer) mapContainer.style.display = 'block';
    if (list) list.style.display = 'block';

    // Create / recreate map
    if (leafletMap) { leafletMap.remove(); leafletMap = null; }
    leafletMap = L.map('map', { zoomControl: false }).setView([lat, lng], 14);
    
    // Add zoom control top right
    L.control.zoom({ position: 'topright' }).addTo(leafletMap);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        attribution: '© OpenStreetMap, © CARTO',
        subdomains: 'abcd', maxZoom: 20
    }).addTo(leafletMap);

    // ── User marker (draggable so user can correct it) ──────────────────────
    const userIcon = L.divIcon({
        className: 'user-location-marker',
        html: `<div style="width:24px;height:24px;background:#2563eb;border:4px solid white;border-radius:50%;box-shadow:0 0 0 8px rgba(37,99,235,0.15), 0 4px 15px rgba(0,0,0,0.3);cursor:grab;"></div>`,
        iconSize: [24, 24], iconAnchor: [12, 12]
    });

    if (userMarker) { try { leafletMap.removeLayer(userMarker); } catch(e){} }
    userMarker = L.marker([lat, lng], { icon: userIcon, draggable: true })
        .addTo(leafletMap)
        .bindPopup('<strong>📍 Your Location</strong><br><span style="font-size:0.8rem;color:#64748b;">Drag me or click map to correct</span>')
        .openPopup();

    // When user drags the pin → re-search
    userMarker.on('dragend', function () {
        const pos = userMarker.getLatLng();
        leafletMap.setView([pos.lat, pos.lng], 15);
        refreshDoctorSearch(pos.lat, pos.lng, list);
    });

    // Click anywhere on map → move pin & re-search
    leafletMap.on('click', function (e) {
        const { lat: cLat, lng: cLng } = e.latlng;
        userMarker.setLatLng([cLat, cLng]);
        userMarker.bindPopup('<strong>📍 Location Updated</strong>').openPopup();
        refreshDoctorSearch(cLat, cLng, list);
    });

    // ── Display Location Search Overlay ──
    addLocationSearchBox(list);

    // ── Google Maps bar ─────────────────────────────────────────────────────
    const gBar  = document.getElementById('google-maps-bar');
    const gLink = document.getElementById('google-maps-link');
    if (gBar && gLink) {
        gLink.href = `https://www.google.com/maps/search/dermatologist/@${lat},${lng},14z`;
        gBar.style.display = 'block';
    }

    // ── Helpful Hint (Prominent) ──
    const hint = document.createElement('div');
    hint.id = 'location-accuracy-hint';
    hint.style.cssText = 'padding:1.25rem;background:#f0f9ff;border:1.5px solid #bae6fd;border-radius:16px;margin-bottom:1.5rem;font-size:0.9rem;color:#0369a1;display:flex;align-items:flex-start;gap:0.75rem;box-shadow:0 2px 6px rgba(0,0,0,0.03);';
    hint.innerHTML = `
        <div style="background:#0284c7;color:white;width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
            <i class="fas fa-map-marker-alt" style="font-size:0.9rem;"></i>
        </div>
        <div>
            <strong style="display:block;margin-bottom:4px;color:#0c4a6e;">Location Incorrect?</strong>
            <span>Search your area using the <strong>box on the map</strong> or simply <strong>click anywhere on the map</strong> to find doctors there.</span>
        </div>`;
    if (list) {
        const existing = document.getElementById('location-accuracy-hint');
        if (existing) existing.remove();
        list.insertBefore(hint, list.firstChild);
    }

    // Run initial search
    searchNearbyDermatologists(lat, lng, list);
    saveLocationToBackend(lat, lng);
    mapLoaded = true;
}

// ──── Search Box with Global Support ─────────────────────────────────────────
function addLocationSearchBox(listEl) {
    if (document.getElementById('location-search-box')) return;

    const wrapper = document.createElement('div');
    wrapper.id = 'location-search-box';
    wrapper.style.cssText = 'position:absolute;top:20px;left:20px;z-index:2000;width:calc(100% - 40px);max-width:400px;';
    wrapper.innerHTML = `
        <div style="display:flex;gap:0;box-shadow:0 8px 24px rgba(0,0,0,0.12);border-radius:12px;overflow:hidden;border:1px solid #e2e8f0;">
            <input id="loc-search-input" type="text" placeholder="Enter your city or area..."
                style="flex:1;padding:0.9rem 1.25rem;border:none;outline:none;font-size:0.95rem;font-family:inherit;background:white;" />
            <button id="loc-search-btn" style="padding:0.9rem 1.4rem;background:#2563eb;color:white;border:none;cursor:pointer;font-size:1rem;transition:background 0.2s;">
                <i class="fas fa-search"></i>
            </button>
        </div>
        <div id="loc-search-results" style="display:none;background:white;margin-top:8px;border-radius:12px;box-shadow:0 10px 25px rgba(0,0,0,0.15);max-height:220px;overflow-y:auto;border:1px solid #f1f5f9;"></div>`;

    const mapPanel = document.querySelector('.right-panel-map');
    if (mapPanel) mapPanel.appendChild(wrapper);

    const input = document.getElementById('loc-search-input');
    const btn   = document.getElementById('loc-search-btn');
    const resultsDiv = document.getElementById('loc-search-results');

    async function doSearch() {
        const q = input.value.trim();
        if (!q || q.length < 3) return;

        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        try {
            // Global search (removed country restriction)
            const res = await fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(q)}&format=json&limit=6&addressdetails=1`, {
                headers: { 'User-Agent': 'DermaCareAI/1.0' }
            });
            const data = await res.json();

            if (!data || data.length === 0) {
                resultsDiv.innerHTML = '<div style="padding:1rem;text-align:center;color:#64748b;">No results found.</div>';
                resultsDiv.style.display = 'block';
                return;
            }

            resultsDiv.innerHTML = data.map(item => `
                <div class="loc-result-item" data-lat="${item.lat}" data-lon="${item.lon}"
                    style="padding:0.8rem 1.2rem;cursor:pointer;border-bottom:1px solid #f8fafc;font-size:0.9rem;transition:all 0.2s;"
                    onmouseover="this.style.background='#f0f9ff'" onmouseout="this.style.background='white'">
                    <div style="font-weight:600;margin-bottom:2px;">${item.display_name.split(',')[0]}</div>
                    <div style="font-size:0.75rem;color:#64748b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${item.display_name}</div>
                </div>`).join('');
            resultsDiv.style.display = 'block';

            resultsDiv.querySelectorAll('.loc-result-item').forEach(el => {
                el.addEventListener('click', () => {
                    const rLat = parseFloat(el.dataset.lat);
                    const rLon = parseFloat(el.dataset.lon);
                    userMarker.setLatLng([rLat, rLon]);
                    leafletMap.setView([rLat, rLon], 15);
                    userMarker.bindPopup('<strong>📍 Location Updated</strong>').openPopup();
                    resultsDiv.style.display = 'none';
                    input.value = el.querySelector('div').innerText;
                    refreshDoctorSearch(rLat, rLon, listEl);
                });
            });
        } catch (err) {
            console.error('Search error:', err);
        } finally {
            btn.innerHTML = '<i class="fas fa-search"></i>';
        }
    }

    btn.addEventListener('click', doSearch);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });
    document.addEventListener('click', e => { if (wrapper && !wrapper.contains(e.target)) resultsDiv.style.display = 'none'; });
}

// ──── Save location to backend ──────────────────────────────────────────────
function saveLocationToBackend(lat, lng) {
    fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=14&addressdetails=1`, {
        headers: { 'Accept-Language': 'en' }
    })
    .then(r => r.json())
    .then(geo => {
        const city = geo.address?.city || geo.address?.town || geo.address?.village || 'Unknown';
        const state = geo.address?.state || '';
        const name = state ? `${city}, ${state}` : city;
        const token = localStorage.getItem('dermacare_token');
        if (token) {
            fetch(`${API_URL}/api/scan/location`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ latitude: lat, longitude: lng, location_name: name })
            }).catch(() => {});
        }
    }).catch(() => {});
}

// ──── Refresh search from a new position ────────────────────────────────────
function refreshDoctorSearch(lat, lng, listEl) {
    // Update Google Maps link
    const gLink = document.getElementById('google-maps-link');
    if (gLink) gLink.href = `https://www.google.com/maps/search/dermatologist/@${lat},${lng},14z`;

    // Clear existing doctor markers (keep user marker & tiles)
    leafletMap.eachLayer(layer => {
        if (layer instanceof L.Marker && layer !== userMarker) {
            leafletMap.removeLayer(layer);
        }
    });

    searchNearbyDermatologists(lat, lng, listEl);
    saveLocationToBackend(lat, lng);
}

// ──── Search nearby dermatologists via backend proxy ─────────────────────────
async function searchNearbyDermatologists(lat, lng, listEl) {
    if (listEl) {
        // Keep the accuracy hint if it exists
        const hint = document.getElementById('location-accuracy-hint');
        const hintHtml = hint ? hint.outerHTML : '';
        listEl.innerHTML = hintHtml + `
            <div style="text-align:center;padding:2.5rem 1rem;">
                <div style="width:60px;height:60px;margin:0 auto 1.5rem;background:rgba(37,99,235,0.1);border-radius:50%;display:flex;align-items:center;justify-content:center;">
                    <i class="fas fa-street-view fa-2x" style="color:var(--primary-color);"></i>
                </div>
                <h3 style="color:var(--text-dark);margin-bottom:0.5rem;">Scanning your area...</h3>
                <p style="color:var(--text-light);font-size:0.9rem;">Searching for skin specialists near your location</p>
            </div>`;
    }

    try {
        const res = await fetch(`${API_URL}/api/nearby-doctors?lat=${lat}&lng=${lng}`);
        if (!res.ok) throw new Error(`Server error: ${res.status}`);
        const doctors = await res.json();

        if (!doctors || doctors.length === 0) {
            searchOverpassInBackground(lat, lng, listEl, '', []);
            return;
        }

        const places = doctors.map(d => ({
            tags: { name: d.name, 'addr:street': d.street || '', healthcare: d.type || 'clinic' },
            lat: d.lat, lon: d.lon, distance: d.distance, city: d.city || ''
        }));

        renderDermatologistList(places, listEl, lat, lng);
    } catch (err) {
        console.error('Backend nearby-doctors failed:', err);
        searchOverpassInBackground(lat, lng, listEl, '', []);
    }
}

// Runs Overpass API in background — updates list if better results found
async function searchOverpassInBackground(lat, lng, listEl, cacheKey, existingPlaces) {
    const endpoints = [
        'https://overpass-api.de/api/interpreter',
        'https://overpass.kumi.systems/api/interpreter',
        'https://lz4.overpass-api.de/api/interpreter'
    ];

    async function fetchFromOverpass(q) {
        const queryData = "?data=" + encodeURIComponent(q);
        const promises = endpoints.map(url =>
            fetch(url + queryData, { method: 'GET', headers: { 'Accept': 'application/json' } })
                .then(res => res.ok ? res.json() : null)
                .catch(() => null)
        );
        const results = await Promise.all(promises);
        for (const data of results) {
            if (data && data.elements && data.elements.length > 0) {
                return data.elements.filter(p => p.tags && p.tags.name);
            }
        }
        return [];
    }

    try {
        const q = `[out:json][timeout:20];(nwr["healthcare:speciality"~"dermatology|skin|aesthetic",i](around:50000,${lat},${lng});nwr["name"~"Derma|Skin|Clinic",i](around:50000,${lat},${lng}););out center body;`;
        const apiResults = await fetchFromOverpass(q);

        if (apiResults.length === 0) return; // No better data, keep existing

        // Merge API results with existing
        const seenNames = new Set(existingPlaces.map(p => (p.tags?.name || '').toLowerCase()));
        let merged = [...existingPlaces];

        apiResults.forEach(p => {
            const name = p.tags?.name;
            if (!name || seenNames.has(name.toLowerCase())) return;
            seenNames.add(name.toLowerCase());
            merged.push({
                ...p,
                lat: p.lat || p.center?.lat,
                lon: p.lon || p.center?.lon
            });
        });

        merged = merged.filter(p => p.lat && p.lon);
        merged.forEach(p => p.distance = parseFloat(getDistanceKm(lat, lng, p.lat, p.lon)));
        merged.sort((a, b) => a.distance - b.distance);
        merged = merged.slice(0, 15);

        // Only update UI if we got MORE results than what's already shown
        if (merged.length > existingPlaces.length) {
            sessionStorage.setItem(cacheKey, JSON.stringify(merged));
            renderDermatologistList(merged, listEl, lat, lng);
        }
    } catch(e) {
        // Silent fail — existing list stays visible
    }
}

// Separate function to render the list for caching purposes
function renderDermatologistList(finalPlaces, listEl, lat, lng) {

    if (finalPlaces.length === 0) {
        if (listEl) listEl.innerHTML = `
            <div style="text-align: center; padding: 4rem 1.5rem; background: #fff; border-radius: 16px; border: 1px dashed #ced4da; margin: 1rem;">
                <div style="font-size: 3.5rem; margin-bottom: 2rem;">🔍</div>
                <h3 style="margin-bottom: 1rem; color: #3c4043; font-weight: 500;">No Specialized Skin Clinics Found</h3>
                <p style="color: #70757a; margin-bottom: 2.5rem; font-size: 0.95rem; line-height: 1.5;">
                    We couldn't find a dedicated dermatologist in the OpenStreetMap database within 150km of your location. 
                </p>
                <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                    <a href="https://www.google.com/maps/search/dermatologist/@${lat},${lng},13z" target="_blank" class="btn" style="background: #2563eb; color: white; border-radius: 24px; padding: 0.8rem 2rem; text-decoration: none; font-weight: 600; display: inline-flex; align-items: center; justify-content: center; gap: 0.5rem; box-shadow: 0 4px 12px rgba(37,99,235,0.2);">
                        <i class="fab fa-google"></i> Search on Google Maps
                    </a>
                    <button class="btn btn-secondary" onclick="window.location.reload()" style="border-radius: 24px; padding: 0.8rem 2rem;">
                        <i class="fas fa-redo"></i> Retry Deep Search
                    </button>
                </div>
            </div>`;
        return;
    }

    if (listEl) listEl.innerHTML = "";

    const doctorIcon = L.divIcon({
        className: 'doctor-marker',
        html: `<div style="width: 36px; height: 36px; background: #2563eb; border: 3px solid white; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(37,99,235,0.4); color: white;"><i class="fas fa-user-md"></i></div>`,
        iconSize: [36, 36],
        iconAnchor: [18, 18]
    });

    // Mock Review Database for realistic feel
    const mockReviews = [
        "Highly knowledgeable and professional. The treatment for my acne worked wonders!",
        "Very clean clinic and the staff is wonderful. Dr. is very patient.",
        "Best dermatologist in the area. Fixed my skin irritation in one visit.",
        "Excellent experience. Minimal waiting time and very clear diagnosis.",
        "The laser treatment was virtually painless. Great results!",
        "Takes time to explain everything. I felt very comfortable and cared for.",
        "Professional service and state-of-the-art equipment. Highly recommended."
    ];

    finalPlaces.forEach((place, index) => {
        const name = place.tags.name;
        const operator = place.tags.operator || place.tags['contact:person'] || "";
        // Support both backend proxy format (top-level city/street) and Overpass format (tags)
        const city   = place.city || place.tags['addr:city'] || place.tags['addr:suburb'] || "";
        const street = place.tags['addr:street'] || place.tags['addr:housenumber'] || "";
        const address = street ? `${street}${city ? ", " + city : ""}` : (city || "Location available on map");
        const phone = place.tags.phone || place.tags['contact:phone'] || "";
        const distance = place.distance;

        // Mocking sophisticated data for "Google Maps" feel
        const seed = name.length + index;
        const rating = (4.5 + (seed % 6) / 10).toFixed(1);
        const reviewCount = 20 + (seed * 7 % 480);
        const reviewText = mockReviews[seed % mockReviews.length];

        // Mock Timings
        const hour = new Date().getHours();
        const openHour = 8 + (seed % 2);
        const closeHour = 18 + (seed % 4);
        const isOpen = hour >= openHour && hour < closeHour;
        const statusColor = isOpen ? "#1e8e3e" : "#d93025";

        const doctorDisplay = operator ? `Dr. ${operator}` : (name.length > 25 ? name.substring(0, 25) + '...' : name);
        const clinicDisplay = operator ? name : (name.includes('Dr.') ? "Dermatology Clinic" : name);

        // Add marker to map
        L.marker([place.lat, place.lon], { icon: doctorIcon })
            .addTo(leafletMap)
            .bindPopup(`<div style="font-family:'Inter',sans-serif; padding:5px;">
                            <strong style="color:#2563eb">${doctorDisplay}</strong><br>
                            <span style="font-size:0.8rem;color:#64748b">${clinicDisplay}</span><br>
                            <span style="font-size:0.85rem">⭐ ${rating} (${reviewCount} reviews)</span>
                        </div>`);

        if (listEl) {
            listEl.innerHTML += `
            <div class="doctor-card" style="display: flex; flex-direction: column; padding: 1.5rem; background: #fff; border-radius: 16px; margin-bottom: 1.25rem; border: 1px solid #f1f5f9; box-shadow: 0 2px 4px rgba(0,0,0,0.02); transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);">
                
                <div style="display: flex; gap: 1.25rem; align-items: flex-start; margin-bottom: 1rem;">
                    <div style="width: 56px; height: 56px; background: linear-gradient(135deg, #2563eb, #3b82f6); border-radius: 14px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; box-shadow: 0 4px 12px rgba(37,99,235,0.2);">
                        <i class="fas fa-user-md" style="color: white; font-size: 1.5rem;"></i>
                    </div>
                    
                    <div style="flex: 1; min-width: 0;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem;">
                            <h3 style="color: #0f172a; margin: 0; font-size: 1.15rem; font-weight: 700; line-height: 1.2;">${doctorDisplay}</h3>
                            <div style="display: flex; align-items: center; background: #fefce8; padding: 4px 8px; border-radius: 6px; border: 1px solid #fef08a;">
                                <i class="fas fa-star" style="color: #eab308; font-size: 0.8rem; margin-right: 4px;"></i>
                                <span style="color: #854d0e; font-weight: 700; font-size: 0.85rem;">${rating}</span>
                            </div>
                        </div>
                        <p style="color: #2563eb; font-weight: 600; font-size: 0.85rem; margin-top: 2px;">${clinicDisplay}</p>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr; gap: 0.5rem; margin-bottom: 1.25rem;">
                    <div style="display: flex; items: center; gap: 8px; color: #64748b; font-size: 0.85rem;">
                        <i class="fas fa-map-marker-alt" style="margin-top: 3px; color: #94a3b8; width: 14px;"></i>
                        <span style="line-height: 1.4;">${address} <strong>(${distance} km)</strong></span>
                    </div>
                    <div style="display: flex; items: center; gap: 8px; font-size: 0.85rem;">
                        <i class="fas fa-clock" style="margin-top: 3px; color: #94a3b8; width: 14px;"></i>
                        <span style="color: ${statusColor === '#1e8e3e' ? '#10b981' : '#ef4444'}; font-weight: 600;">${isOpen ? 'Open Now' : 'Closed'}</span>
                        <span style="color: #94a3b8;">•</span>
                        <span style="color: #64748b;">${isOpen ? 'Closes ' + closeHour + ':00' : 'Opens ' + openHour + ':00'}</span>
                    </div>
                </div>

                <div style="background: #f8fafc; padding: 1rem; border-radius: 12px; margin-bottom: 1.25rem; position: relative;">
                    <i class="fas fa-quote-left" style="position: absolute; top: 10px; right: 10px; color: #cbd5e1; font-size: 1.5rem; opacity: 0.4;"></i>
                    <p style="color: #475569; font-style: italic; font-size: 0.85rem; margin: 0; line-height: 1.5; padding-right: 20px;">
                        "${reviewText}"
                    </p>
                    <div style="margin-top: 8px; font-size: 0.75rem; color: #94a3b8; font-weight: 600;">— Verified Patient</div>
                </div>
                
                <div style="display: flex; gap: 0.75rem;">
                    <button onclick="checkLoginAndBook('${encodeURIComponent(JSON.stringify({
                name: doctorDisplay,
                clinic: clinicDisplay,
                typeLabel: 'Skin Specialist',
                rating,
                reviews: reviewCount,
                review: reviewText,
                address,
                distance,
                isSpecialist: true
            })).replace(/'/g, "%27")}')" class="btn btn-primary" style="flex: 2; justify-content: center; border-radius: 10px; height: 44px; font-weight: 600;">
                        <i class="fas fa-calendar-check" style="margin-right: 8px;"></i> Book Appointment
                    </button>
                    <a href="https://www.google.com/maps/dir/?api=1&destination=${place.lat},${place.lon}" target="_blank" class="btn btn-secondary" style="flex: 1; text-decoration: none; display: flex; align-items: center; justify-content: center; border-radius: 10px; height: 44px; background: #fff; border: 1.5px solid #e2e8f0; color: #64748b;">
                        <i class="fas fa-directions"></i>
                    </a>
                </div>
            </div>`;
        }
    });
}

// Calculate distance between two coordinates in km
function getDistanceKm(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
        Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return (R * c).toFixed(1);
}

// Drag & Drop
const dropArea = document.getElementById('drop-area');

if (dropArea) {
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false)
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false)
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false)
    });

    function highlight(e) {
        dropArea.classList.add('dragover');
    }

    function unhighlight(e) {
        dropArea.classList.remove('dragover');
    }

    dropArea.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }
}

// Relative time helper
function timeSince(date) {
    if (!date || isNaN(date)) return "Never";
    const seconds = Math.floor((new Date() - date) / 1000);

    // Server time vs client time can be off slightly, prevent negative seconds
    if (seconds < 0) return "Just now";

    let interval = seconds / 31536000;
    if (interval >= 1) return Math.floor(interval) + " year" + (Math.floor(interval) > 1 ? "s" : "") + " ago";
    interval = seconds / 2592000;
    if (interval >= 1) return Math.floor(interval) + " month" + (Math.floor(interval) > 1 ? "s" : "") + " ago";
    interval = seconds / 604800; // 7 days
    if (interval >= 1) return Math.floor(interval) + " week" + (Math.floor(interval) > 1 ? "s" : "") + " ago";
    interval = seconds / 86400;
    if (interval >= 1) {
        const d = Math.floor(interval);
        return d === 1 ? "1 day ago" : d + " days ago";
    }
    interval = seconds / 3600;
    if (interval >= 1) {
        const h = Math.floor(interval);
        return h === 1 ? "1 hour ago" : h + " hours ago";
    }
    interval = seconds / 60;
    if (interval >= 1) {
        const m = Math.floor(interval);
        return m === 1 ? "1 minute ago" : m + " minutes ago";
    }
    // Handle less than 60 seconds
    return "Just now";
}
