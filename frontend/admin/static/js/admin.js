// Critical Check: Browsers block API requests from file:// origins
if (window.location.protocol === 'file:') {
    document.addEventListener('DOMContentLoaded', () => {
        const overlay = document.createElement('div');
        overlay.style = "position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.9);z-index:10000;display:flex;flex-direction:column;align-items:center;justify-content:center;color:white;text-align:center;padding:2rem;font-family:inherit;";
        overlay.innerHTML = `
            <h1 style="color:#ef4444;margin-bottom:1rem;"><i class="fas fa-exclamation-triangle"></i> Browser Security Conflict</h1>
            <p style="font-size:1.2rem;max-width:600px;margin-bottom:2rem;">
                You are currently viewing the admin panel as a local file. Browsers block the connection to the database for security reasons.
            </p>
            <div style="background:#1e293b;padding:1.5rem;border-radius:12px;border:1px solid #334155;">
                <p style="color:#94a3b8;margin-bottom:0.5rem;font-size:0.9rem;">PLEASE CLICK THE LINK BELOW TO LOAD DATA:</p>
                <a href="http://127.0.0.1:8000/static/admin.html" style="color:#3b82f6;font-weight:bold;font-size:1.3rem;text-decoration:none;border-bottom:2px solid #3b82f6;">http://127.0.0.1:8000/static/admin.html</a>
            </div>
            <p style="margin-top:2rem;font-size:0.8rem;color:#64748b;">(Note: Ensure your backend "main.py" is running)</p>
        `;
        document.body.appendChild(overlay);
    });
}

// Diagnostic API Configuration
const API_URL = (typeof window !== 'undefined' && window.DERMACARE_API_BASE)
    ? window.DERMACARE_API_BASE
    : (window.location.origin.includes('localhost') || window.location.origin.includes('127.0.0.1') ? window.location.origin : 'http://127.0.0.1:8000');

// Websocket initialization
const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsHost = API_URL.replace(/^http(s?):\/\//, '');
const socket = new WebSocket(`${wsProto}//${wsHost}/ws`);

socket.onmessage = function (event) {
    const data = JSON.parse(event.data);
    if (data.action === "delete") {
        const row = document.getElementById(`${data.table}-row-${data.id}`);
        if (row) row.remove();
    }
};

// ── Shared Admin Helpers ──────────────────────────────────────────────────────

function showToast(message, type = "success") {
    const container = document.getElementById("toast-container");
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerText = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

/**
 * adminFetch — wraps every admin API call with token + error handling.
 * Returns { res, data } or throws on network error.
 */
async function adminFetch(url, options = {}) {
    const token = localStorage.getItem('admin_token');
    const headers = { 'Authorization': `Bearer ${token}`, ...(options.headers || {}) };
    const res = await fetch(url, { ...options, headers });
    const data = await res.json();
    return { res, data };
}

/**
 * setTableLoading — shows a spinner row in a tbody.
 */
function setTableLoading(tbodyId, cols, message = 'Loading...') {
    const tbody = document.getElementById(tbodyId);
    if (tbody) tbody.innerHTML = `<tr><td colspan="${cols}" class="text-center"><i class="fas fa-spinner fa-spin"></i> ${message}</td></tr>`;
    return tbody;
}

/**
 * setTableError — shows an error row in a tbody.
 */
function setTableError(tbodyId, cols, message = 'Network Error') {
    const tbody = document.getElementById(tbodyId);
    if (tbody) tbody.innerHTML = `<tr><td colspan="${cols}" class="text-center text-danger">${message}</td></tr>`;
}

/**
 * setTableEmpty — shows an empty state row in a tbody.
 */
function setTableEmpty(tbodyId, cols, message = 'No records found.') {
    const tbody = document.getElementById(tbodyId);
    if (tbody) tbody.innerHTML = `<tr><td colspan="${cols}" class="text-center text-muted">${message}</td></tr>`;
}

// ── Initialization ────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('admin_token');

    if (token) {
        const dashboard = document.getElementById('admin-dashboard');
        if (dashboard) dashboard.style.display = 'flex';

        const overlay = document.getElementById('admin-login-overlay');
        if (overlay) overlay.style.display = 'none';

        try {
            const payloadStr = atob(token.split('.')[1]);
            const payload = JSON.parse(payloadStr);
            document.getElementById('admin-active-email').innerText = payload.email || 'System Admin';
        } catch (e) { }

        adminLoadUsers();
    } else {
        window.location.href = '/login';
    }
});

// ── Tab Navigation ────────────────────────────────────────────────────────────

const TAB_CONFIG = {
    users: { view: 'admin-users-view', title: 'User Management', loader: () => adminLoadUsers() },
    scans: { view: 'admin-scans-view', title: 'Scan History', loader: () => adminLoadScans() },
    medical: { view: 'admin-medical-view', title: 'Medical Profiles', loader: () => adminLoadMedicalProfiles() },
    appointments: { view: 'admin-appointments-view', title: 'Doctor Appointments', loader: () => adminLoadAppointments() },
    activity: { view: 'admin-activity-view', title: 'System Logs', loader: () => adminLoadLogs() },
    locations: { view: 'admin-locations-view', title: 'User Locations', loader: () => adminLoadLocations() },
    otps: { view: 'admin-otps-view', title: 'OTP Verifications', loader: () => adminLoadOTPs() },
    'login-history': { view: 'admin-login-history-view', title: 'Login History', loader: () => adminLoadLoginHistory() }
};

/** Activate sidebar tab from keyboard (Enter/Space) — keeps Sonar/accessibility rules satisfied. */
function adminSidebarNavKeydown(event, tabName) {
    if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        switchAdminTab(tabName);
    }
}

function switchAdminTab(tabName) {
    document.querySelectorAll('.sidebar-menu li').forEach((el) => {
        el.classList.toggle('active', el.dataset.adminTab === tabName);
    });

    Object.keys(TAB_CONFIG).forEach(key => {
        const el = document.getElementById(TAB_CONFIG[key].view);
        if (el) el.style.display = key === tabName ? 'block' : 'none';
    });

    const cfg = TAB_CONFIG[tabName];
    if (cfg) {
        document.getElementById('page-title').innerText = cfg.title;
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) refreshBtn.onclick = cfg.loader;
        cfg.loader();
    }
}

function logoutAdmin() {
    localStorage.removeItem('admin_token');
    window.location.href = '/';
}

// ── API Loaders ───────────────────────────────────────────────────────────────

async function adminLoadUsers() {
    const tbody = setTableLoading('user-table-body', 9, 'Refreshing user list...');
    if (!tbody) return;
    try {
        const { res, data } = await adminFetch(`${API_URL}/api/admin/users`);
        if (res.ok && data.success) {
            tbody.innerHTML = '';
            data.users.forEach(u => {
                const roleHtml = `<span class="t-status ${u.role === 'Admin' ? 's-admin' : 's-active'}">${u.role}</span>`;
                const statusText = u.is_logged_in ? "Active" : "Inactive";
                const statusClass = u.is_logged_in ? "status-online" : "status-offline";
                const statusHtml = `<span class="badge ${statusClass}">${statusText}</span>`;
                const actionsHtml = u.role !== 'Admin'
                    ? `<button class="btn-icon" onclick="deleteRecord('users', ${u.id})" title="Delete User"><i class="fas fa-trash"></i></button>`
                    : '';
                tbody.innerHTML += `
                    <tr id="users-row-${u.id}">
                        <td>#${u.id}</td>
                        <td><strong>${u.first_name} ${u.last_name}</strong></td>
                        <td>${u.email}</td>
                        <td>${u.age || '-'}</td>
                        <td>${u.date_of_birth || '-'}</td>
                        <td>${u.contact_number || '-'}</td>
                        <td class="text-secondary">${u.user_location || 'Unknown'}</td>
                        <td>${statusHtml}</td>
                        <td>${roleHtml}</td>
                        <td>${actionsHtml}</td>
                    </tr>`;
            });
        } else {
            setTableError('user-table-body', 9, `Error: ${data.message || data.detail || 'Access Denied'}`);
            if (res.status === 403 || res.status === 401) setTimeout(logoutAdmin, 2500);
        }
    } catch (err) {
        setTableError('user-table-body', 9);
    }
}

async function adminLoadScans() {
    const tbody = setTableLoading('scan-table-body', 7, 'Refreshing scan history...');
    if (!tbody) return;
    try {
        const { res, data } = await adminFetch(`${API_URL}/api/admin/scans`);
        if (res.ok && data.success) {
            if (data.scans.length === 0) { setTableEmpty('scan-table-body', 8, 'No scan records found.'); return; }
            tbody.innerHTML = '';
            data.scans.forEach(s => {
                const date = new Date(s.scan_date).toLocaleString();
                const confidenceHtml = `<span class="badge ${s.confidence > 70 ? 'status-online' : 'status-offline'}">${s.confidence}%</span>`;
                let conditionDetails = "Monitoring recommended";
                let conditionClass = "status-offline";
                if (s.remedies && s.remedies.consult_doctor && s.remedies.consult_doctor.length > 0) {
                    conditionDetails = s.remedies.consult_doctor[0];
                    if (s.disease === "Normal" || s.disease === "Benign") conditionClass = "status-online";
                }
                tbody.innerHTML += `
                    <tr id="scan_history-row-${s.id}">
                        <td>#${s.id}</td>
                        <td><strong>${s.user_name}</strong></td>
                        <td>${s.user_id}</td>
                        <td><span class="badge ${s.disease === 'Malignant' ? 'status-offline' : 's-active'}">${s.disease}</span></td>
                        <td>${s.image_base64 ? `<img src="${s.image_path}" style="width:50px;height:50px;object-fit:cover;border-radius:4px;border:1px solid #e2e8f0;">` : '<span class="text-muted" style="font-size:0.7rem;">No Image</span>'}</td>
                        <td>${confidenceHtml}</td>
                        <td title="${conditionDetails}"><span class="badge ${conditionClass}">${conditionDetails.substring(0, 30)}${conditionDetails.length > 30 ? '...' : ''}</span></td>
                        <td>${date}</td>
                        <td><button class="btn-icon" onclick="deleteRecord('scan_history', ${s.id})" title="Delete Record"><i class="fas fa-trash"></i></button></td>
                    </tr>`;
            });
        } else {
            setTableError('scan-table-body', 8, `Error: ${data.detail || data.error || data.message || 'Access Denied'}`);
        }
    } catch (err) {
        setTableError('scan-table-body', 8);
    }
}

async function deleteRecord(table, id) {
    if (!confirm(`Are you sure you want to delete record #${id} from ${table}?`)) return;
    try {
        const { res, data } = await adminFetch(`${API_URL}/api/admin/delete/${table}/${id}`, { method: "DELETE" });
        if (res.ok && data.status === "success") {
            showToast(data.message, "success");
            const row = document.getElementById(`${table}-row-${id}`);
            if (row) row.remove();
        } else {
            showToast(data.message || data.detail || "Error deleting record", "error");
        }
    } catch (err) {
        showToast("Network Error", "error");
    }
}

async function adminLoadMedicalProfiles() {
    const tbody = setTableLoading('medical-table-body', 7, 'Refreshing medical records...');
    if (!tbody) return;
    try {
        const { res, data } = await adminFetch(`${API_URL}/api/admin/medical-profiles`);
        if (res.ok && data.success) {
            if (data.profiles.length === 0) { setTableEmpty('medical-table-body', 8, 'No medical profiles found.'); return; }
            tbody.innerHTML = '';
            data.profiles.forEach(p => {
                const date = new Date(p.created_at).toLocaleString();
                const historyHtml = p.has_previous_conditions
                    ? `<span class="badge status-offline">Yes</span>`
                    : `<span class="badge status-online">No</span>`;
                const prevDetails = p.previous_condition_details || "N/A";
                tbody.innerHTML += `
                    <tr id="medical_profiles-row-${p.id}">
                        <td>#${p.id}</td>
                        <td><strong>${p.patient_name}</strong></td>
                        <td title="${p.symptoms}">${p.symptoms.substring(0, 30)}${p.symptoms.length > 30 ? '...' : ''}</td>
                        <td>${p.symptom_duration}</td>
                        <td>${historyHtml}</td>
                        <td title="${prevDetails}">${prevDetails.substring(0, 30)}${prevDetails.length > 30 ? '...' : ''}</td>
                        <td>${date}</td>
                        <td><button class="btn-icon" onclick="deleteRecord('medical_profiles', ${p.id})" title="Delete Profile"><i class="fas fa-trash"></i></button></td>
                    </tr>`;
            });
        } else {
            setTableError('medical-table-body', 8, `Error: ${data.detail || data.error || 'Access Denied'}`);
        }
    } catch (err) {
        setTableError('medical-table-body', 8);
    }
}

async function adminLoadLogs() {
    const tbody = setTableLoading('logs-table-body', 5, 'Fetching activity...');
    if (!tbody) return;
    try {
        const { res, data } = await adminFetch(`${API_URL}/api/admin/logs`);
        if (res.ok && data.success) {
            if (data.logs.length === 0) { setTableEmpty('logs-table-body', 5, 'No activity logs found. Try performing some actions!'); return; }
            tbody.innerHTML = '';
            data.logs.forEach(log => {
                const date = new Date(log.timestamp).toLocaleString();
                tbody.innerHTML += `
                    <tr>
                        <td style="font-size:0.85rem;color:#64748b;">${date}</td>
                        <td><strong>${log.user_email || 'System'}</strong></td>
                        <td><span class="badge ${(log.action || '').includes('Delete') ? 'status-offline' : 's-active'}">${log.action || 'Action'}</span></td>
                        <td title="${log.details || ''}" style="font-size:0.85rem;">${(log.details || '').substring(0, 50)}${(log.details || '').length > 50 ? '...' : ''}</td>
                        <td style="font-family:monospace;font-size:0.8rem;">${log.ip_address || '-'}</td>
                    </tr>`;
            });
        }
    } catch (err) {
        setTableError('logs-table-body', 5, 'Failed to load logs.');
    }
}

async function adminClearLogs() {
    if (!confirm("Are you sure you want to PERMANENTLY delete all system audit logs?")) return;
    try {
        const { res } = await adminFetch(`${API_URL}/api/admin/logs`, { method: 'DELETE' });
        if (res.ok) adminLoadLogs();
    } catch (err) { alert("Error clearing logs"); }
}

async function adminLoadAppointments() {
    const tbody = setTableLoading('appointments-table-body', 9, 'Loading appointments...');
    if (!tbody) return;
    try {
        const { res, data } = await adminFetch(`${API_URL}/api/admin/appointments`);
        if (res.ok && data.success) {
            if (data.appointments.length === 0) { setTableEmpty('appointments-table-body', 9, 'No appointments found.'); return; }
            tbody.innerHTML = '';
            data.appointments.forEach(a => {
                const statusHtml = a.status === 'Done'
                    ? '<span class="status done">✅ Completed</span>'
                    : '<span class="status pending">⏳ Upcoming</span>';
                tbody.innerHTML += `
                    <tr>
                        <td style="font-size:0.8rem;color:#64748b;">#${a.id}</td>
                        <td>
                            <div style="font-size:0.9rem;font-weight:600;">${a.first_name} ${a.last_name}</div>
                            <div style="font-size:0.75rem;color:#64748b;">${a.email}</div>
                        </td>
                        <td><strong>${a.doctor_name}</strong></td>
                        <td>${a.doctor_specialty}</td>
                        <td>
                            <div style="font-weight:500;">${a.doctor_area}</div>
                            <div style="font-size:0.75rem;color:#64748b;">${a.doctor_city || 'Unknown City'}</div>
                        </td>
                        <td style="font-size:0.85rem;">${a.appointment_date}</td>
                        <td style="font-size:0.85rem;">${a.appointment_time}</td>
                        <td>${statusHtml}</td>
                        <td><button class="btn-icon" style="color:#64748b" title="Complete Record"><i class="fas fa-check-circle"></i></button></td>
                    </tr>`;
            });
        } else {
            setTableError('appointments-table-body', 9, `Error: ${data.message || 'Access Denied'}`);
        }
    } catch (err) {
        setTableError('appointments-table-body', 9);
    }
}

async function adminLoadLocations() {
    const tbody = setTableLoading('locations-table-body', 6, 'Fetching locations...');
    if (!tbody) return;
    try {
        const { res, data } = await adminFetch(`${API_URL}/api/admin/user-locations`);
        if (res.ok && data.success) {
            if (data.locations.length === 0) { setTableEmpty('locations-table-body', 6, 'No location data found.'); return; }
            tbody.innerHTML = '';
            data.locations.forEach(l => {
                const date = new Date(l.timestamp).toLocaleString();
                const coordsHtml = `<span style="font-size:0.75rem;color:#64748b;" title="${l.latitude}, ${l.longitude}">[View Map]</span>`;
                tbody.innerHTML += `
                    <tr>
                        <td>#${l.id}</td>
                        <td><strong>${l.patient_name}</strong></td>
                        <td>${l.email}</td>
                        <td style="font-weight:500;">${l.location_name || 'Unknown'}</td>
                        <td><a href="https://maps.google.com/?q=${l.latitude},${l.longitude}" target="_blank" style="text-decoration:none;">${coordsHtml}</a></td>
                        <td style="font-size:0.85rem;color:#64748b;">${date}</td>
                    </tr>`;
            });
        }
    } catch (err) {
        setTableError('locations-table-body', 6, 'Failed to load locations.');
    }
}

async function adminLoadOTPs() {
    const tbody = setTableLoading('otps-table-body', 5, 'Fetching OTPs...');
    if (!tbody) return;
    try {
        const { res, data } = await adminFetch(`${API_URL}/api/admin/otp-verifications`);
        if (res.ok && data.success) {
            if (data.otps.length === 0) { setTableEmpty('otps-table-body', 5, 'No OTP records found.'); return; }
            tbody.innerHTML = '';
            data.otps.forEach(o => {
                const created = new Date(o.created_at).toLocaleString();
                const expires = new Date(o.expires_at).toLocaleString();
                tbody.innerHTML += `
                    <tr>
                        <td>#${o.id}</td>
                        <td>${o.contact}</td>
                        <td><span class="badge s-active" style="font-family:monospace;letter-spacing:2px;">${o.otp}</span></td>
                        <td style="font-size:0.85rem;">${expires}</td>
                        <td style="font-size:0.85rem;color:#64748b;">${created}</td>
                    </tr>`;
            });
        }
    } catch (err) {
        setTableError('otps-table-body', 5, 'Failed to load OTPs.');
    }
}

async function adminLoadLoginHistory() {
    const tbody = setTableLoading('login-history-table-body', 8, 'Fetching login history...');
    if (!tbody) return;

    let url = `${API_URL}/api/admin/login-history?page=1&limit=50`;
    const searchEl = document.getElementById('loginSearch');
    const dateEl = document.getElementById('loginDateFilter');
    const statusEl = document.getElementById('loginStatusFilter');
    if (statusEl && statusEl.value) url += `&status=${statusEl.value}`;
    if (dateEl && dateEl.value) url += `&date=${dateEl.value}`;
    if (searchEl && searchEl.value) url += `&search=${encodeURIComponent(searchEl.value)}`;

    try {
        const { res, data } = await adminFetch(url);
        if (res.ok && data.success) {
            const history = data.history;
            if (history.length === 0) { setTableEmpty('login-history-table-body', 8, 'No login history found.'); return; }
            tbody.innerHTML = '';
            history.forEach(h => {
                const loginTime = new Date(h.login_time).toLocaleString();
                const logoutTime = h.logout_time ? new Date(h.logout_time).toLocaleString() : '-';
                let statusClass = 'status-offline';
                if (h.status === 'ACTIVE') statusClass = 'status-online s-active';
                else if (h.status === 'LOGIN') statusClass = 'status-online';
                const canForceLogout = h.status === 'LOGIN' || h.status === 'ACTIVE';
                const actionHtml = canForceLogout
                    ? `<button class="btn btn-secondary" style="color:#ef4444;border-color:#fca5a5;padding:4px 8px;font-size:0.8rem;" onclick="adminForceLogout('${h.session_id}')">Force Logout</button>`
                    : '-';
                tbody.innerHTML += `
                    <tr>
                        <td><strong>${h.first_name} ${h.last_name}</strong></td>
                        <td>${h.email}</td>
                        <td style="font-size:0.85rem;">${loginTime}</td>
                        <td style="font-size:0.85rem;">${logoutTime}</td>
                        <td style="font-size:0.85rem;" title="${h.device_info}">${h.device_info ? (h.device_info.substring(0, 20) + (h.device_info.length > 20 ? '...' : '')) : 'Unknown'}</td>
                        <td style="font-family:monospace;font-size:0.8rem;">${h.ip_address || '-'}</td>
                        <td><span class="badge ${statusClass}">${h.status}</span></td>
                        <td>${actionHtml}</td>
                    </tr>`;
            });
        }
    } catch (err) {
        setTableError('login-history-table-body', 8, 'Failed to load login history.');
    }
}

async function adminForceLogout(sessionId) {
    if (!confirm("Are you sure you want to force logout this session? The user will be disconnected automatically.")) return;
    try {
        const { res, data } = await adminFetch(`${API_URL}/api/admin/force-logout/${sessionId}`, { method: 'POST' });
        if (res.ok && data.success) {
            alert(data.message || "User logged out successfully.");
            adminLoadLoginHistory();
        } else {
            alert(`Error: ${data.detail || data.error}`);
        }
    } catch (err) { alert("Error force logging out."); }
}
