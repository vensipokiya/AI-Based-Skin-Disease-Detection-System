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

document.addEventListener('DOMContentLoaded', () => {


    // Validate current session on page load
    const token = localStorage.getItem('admin_token');

    if (token) {
        // Assume valid, setup the UI
        const dashboard = document.getElementById('admin-dashboard');
        if (dashboard) dashboard.style.display = 'flex';

        const overlay = document.getElementById('admin-login-overlay');
        if (overlay) overlay.style.display = 'none';

        // Parse email from JWT blindly for UI (assuming valid format)
        try {
            const payloadStr = atob(token.split('.')[1]);
            const payload = JSON.parse(payloadStr);
            document.getElementById('admin-active-email').innerText = payload.email || 'System Admin';
        } catch (e) { }

        // Fetch the users safely
        adminLoadUsers();
    } else {
        // Force them to login page because Google Auth overlay is removed
        window.location.href = '/login';
    }
});

function switchAdminTab(tabName) {
    document.querySelectorAll('.sidebar-menu li').forEach(el => el.classList.remove('active'));
    event.currentTarget.classList.add('active');

    document.getElementById('admin-users-view').style.display = tabName === 'users' ? 'block' : 'none';
    document.getElementById('admin-scans-view').style.display = tabName === 'scans' ? 'block' : 'none';
    document.getElementById('admin-medical-view').style.display = tabName === 'medical' ? 'block' : 'none';
    document.getElementById('admin-appointments-view').style.display = tabName === 'appointments' ? 'block' : 'none';
    document.getElementById('admin-activity-view').style.display = tabName === 'activity' ? 'block' : 'none';
    document.getElementById('admin-locations-view').style.display = tabName === 'locations' ? 'block' : 'none';
    document.getElementById('admin-otps-view').style.display = tabName === 'otps' ? 'block' : 'none';
    document.getElementById('admin-login-history-view').style.display = tabName === 'login-history' ? 'block' : 'none';

    document.getElementById('page-title').innerText =
        tabName === 'users' ? 'User Management' :
            tabName === 'scans' ? 'Scan History' :
                tabName === 'medical' ? 'Medical Profiles' :
                    tabName === 'appointments' ? 'Doctor Appointments' :
                        tabName === 'activity' ? 'System Logs' : 
                            tabName === 'locations' ? 'User Locations' : 
                                tabName === 'otps' ? 'OTP Verifications' : 'Login History';

    // Update refresh button
    const refreshBtn = document.getElementById('refresh-btn');
    if (tabName === 'users') {
        refreshBtn.onclick = adminLoadUsers;
        adminLoadUsers(); // Trigger load
    } else if (tabName === 'scans') {
        refreshBtn.onclick = adminLoadScans;
        adminLoadScans();
    } else if (tabName === 'medical') {
        refreshBtn.onclick = adminLoadMedicalProfiles;
        adminLoadMedicalProfiles();
    } else if (tabName === 'appointments') {
        refreshBtn.onclick = adminLoadAppointments;
        adminLoadAppointments();
    } else if (tabName === 'activity') {
        refreshBtn.onclick = adminLoadLogs;
        adminLoadLogs();
    } else if (tabName === 'locations') {
        refreshBtn.onclick = adminLoadLocations;
        adminLoadLocations();
    } else if (tabName === 'otps') {
        refreshBtn.onclick = adminLoadOTPs;
        adminLoadOTPs();
    } else if (tabName === 'login-history') {
        refreshBtn.onclick = adminLoadLoginHistory;
        adminLoadLoginHistory();
    }
}





function logoutAdmin() {
    localStorage.removeItem('admin_token');
    window.location.href = '/';
}

// =====================================
// API Integrations
// =====================================

async function adminLoadUsers() {
    const token = localStorage.getItem('admin_token');
    const tbody = document.getElementById('user-table-body');
    if (!tbody) return;

    // Visual feedback
    tbody.innerHTML = `<tr><td colspan="9" class="text-center"><i class="fas fa-spinner fa-spin"></i> Refreshing user list...</td></tr>`;

    try {
        const res = await fetch(`${API_URL}/api/admin/users`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });


        const data = await res.json();

        if (res.ok && data.success) {
            tbody.innerHTML = '';
            data.users.forEach(u => {
                const roleHtml = `<span class="t-status ${u.role === 'Admin' ? 's-admin' : 's-active'}">${u.role}</span>`;

                // Dynamic Status based on is_logged_in from database
                const statusText = u.is_logged_in ? "Active" : "Inactive";
                const statusClass = u.is_logged_in ? "status-online" : "status-offline";
                const statusHtml = `<span class="badge ${statusClass}">${statusText}</span>`;

                // Hide delete button for admins
                const actionsHtml = u.role !== 'Admin'
                    ? `<button class="btn-icon" onclick="adminDeleteUser(${u.id}, '${u.first_name}')" title="Delete User"><i class="fas fa-trash"></i></button>`
                    : ``;

                const row = `
                    <tr>
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
                    </tr>
                `;
                tbody.innerHTML += row;

            });
        } else {
            // Probably 403 Forbidden!
            tbody.innerHTML = `<tr><td colspan="9" class="text-center text-danger">Error: ${data.message || data.detail || 'Access Denied'}</td></tr>`;
            if (res.status === 403 || res.status === 401) {
                // Kick out to login
                setTimeout(logoutAdmin, 2500);
            }
        }
    } catch (err) {
        console.error(err);
        tbody.innerHTML = `<tr><td colspan="9" class="text-center text-danger">Network Error</td></tr>`;
    }
}

async function adminLoadScans() {
    const token = localStorage.getItem('admin_token');
    const tbody = document.getElementById('scan-table-body');
    if (!tbody) return;

    // Visual feedback
    tbody.innerHTML = `<tr><td colspan="7" class="text-center"><i class="fas fa-spinner fa-spin"></i> Refreshing scan history...</td></tr>`;

    try {
        const res = await fetch(`${API_URL}/api/admin/scans`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });


        const data = await res.json();

        if (res.ok && data.success) {
            tbody.innerHTML = '';
            if (data.scans.length === 0) {
                tbody.innerHTML = `<tr><td colspan="8" class="text-center">No scan records found.</td></tr>`;
                return;
            }
            data.scans.forEach(s => {
                const date = new Date(s.scan_date).toLocaleString();
                const confidenceHtml = `<span class="badge ${s.confidence > 70 ? 'status-online' : 'status-offline'}">${s.confidence}%</span>`;

                // Extract Condition Details (Doctor Advisory)
                let conditionDetails = "Monitoring recommended";
                let conditionClass = "status-offline";

                if (s.remedies && s.remedies.consult_doctor && s.remedies.consult_doctor.length > 0) {
                    conditionDetails = s.remedies.consult_doctor[0];
                    if (s.disease === "Normal" || s.disease === "Benign") {
                        conditionClass = "status-online";
                    }
                }

                const row = `
                    <tr>
                        <td>#${s.id}</td>
                        <td><strong>${s.user_name}</strong></td>
                        <td>${s.user_id}</td>
                        <td><span class="badge ${s.disease === 'Malignant' ? 'status-offline' : 's-active'}">${s.disease}</span></td>
                        <td>
                            ${s.image_base64 ? `<img src="${s.image_path ? `http://localhost:8000${s.image_path}` : ""}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px; border: 1px solid #e2e8f0;">` : '<span class="text-muted" style="font-size:0.7rem;">No Image</span>'}
                        </td>
                        <td>${confidenceHtml}</td>
                        <td title="${conditionDetails}"><span class="badge ${conditionClass}">${conditionDetails.substring(0, 30)}${conditionDetails.length > 30 ? '...' : ''}</span></td>
                        <td>${date}</td>
                        <td>
                            <button class="btn-icon" onclick="adminDeleteScan(${s.id})" title="Delete Record">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
        } else {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">Error: ${data.detail || data.error || data.message || 'Access Denied'}</td></tr>`;
        }
    } catch (err) {
        console.error(err);
        tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">Network Error</td></tr>`;
    }

}

async function adminDeleteUser(userId, name) {
    if (!confirm(`Are you absolutely sure you want to permanently delete patient ${name} (ID: ${userId})? This deletes all scan history and logs.`)) {
        return;
    }

    const token = localStorage.getItem('admin_token');
    try {
        const res = await fetch(`${API_URL}/api/admin/users/${userId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        const data = await res.json();

        if (res.ok && data.success) {
            alert("User deleted successfully.");
            adminLoadUsers(); // Refresh the table
        } else {
            alert(`Error deleting user: ${data.detail || data.error}`);
        }
    } catch (err) {
        alert("Network Error");
    }
}

async function adminDeleteScan(scanId) {
    if (!confirm(`Are you sure you want to delete scan record #${scanId}?`)) {
        return;
    }

    const token = localStorage.getItem('admin_token');
    try {
        const res = await fetch(`${API_URL}/api/admin/scans/${scanId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        const data = await res.json();

        if (res.ok && data.success) {
            adminLoadScans(); // Refresh
        } else {
            alert(`Error: ${data.detail || data.error}`);
        }
    } catch (err) {
        alert("Network Error");
    }
}

async function adminLoadMedicalProfiles() {
    const token = localStorage.getItem('admin_token');
    const tbody = document.getElementById('medical-table-body');
    if (!tbody) return;

    // Visual feedback
    tbody.innerHTML = `<tr><td colspan="7" class="text-center"><i class="fas fa-spinner fa-spin"></i> Refreshing medical records...</td></tr>`;

    try {
        const res = await fetch(`${API_URL}/api/admin/medical-profiles`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const data = await res.json();

        if (res.ok && data.success) {
            tbody.innerHTML = '';
            if (data.profiles.length === 0) {
                tbody.innerHTML = `<tr><td colspan="8" class="text-center">No medical profiles found.</td></tr>`;
                return;
            }
            data.profiles.forEach(p => {
                const date = new Date(p.created_at).toLocaleString();
                const historyHtml = p.has_previous_conditions
                    ? `<span class="badge status-offline">Yes</span>`
                    : `<span class="badge status-online">No</span>`;

                const prevDetails = p.previous_condition_details || "N/A";

                const row = `
                    <tr>
                        <td>#${p.id}</td>
                        <td><strong>${p.patient_name}</strong></td>
                        <td title="${p.symptoms}">${p.symptoms.substring(0, 30)}${p.symptoms.length > 30 ? '...' : ''}</td>
                        <td>${p.symptom_duration}</td>
                        <td>${historyHtml}</td>
                        <td title="${prevDetails}">${prevDetails.substring(0, 30)}${prevDetails.length > 30 ? '...' : ''}</td>
                        <td>${date}</td>
                        <td>
                            <button class="btn-icon" onclick="adminDeleteMedicalProfile(${p.id})" title="Delete Profile">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
        } else {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">Error: ${data.detail || data.error || 'Access Denied'}</td></tr>`;
        }
    } catch (err) {
        console.error(err);
        tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">Network Error</td></tr>`;
    }

}

async function adminDeleteMedicalProfile(profileId) {
    if (!confirm(`Are you sure you want to delete medical profile #${profileId}?`)) {
        return;
    }

    const token = localStorage.getItem('admin_token');
    try {
        const res = await fetch(`${API_URL}/api/admin/medical-profiles/${profileId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        const data = await res.json();

        if (res.ok && data.success) {
            adminLoadMedicalProfiles(); // Refresh
        } else {
            alert(`Error: ${data.detail || data.error}`);
        }
    } catch (err) {
        alert("Network Error");
    }
}

async function adminLoadLogs() {
    const token = localStorage.getItem('admin_token');
    const tbody = document.getElementById('logs-table-body');
    if (!tbody) return;

    tbody.innerHTML = `<tr><td colspan="5" class="text-center"><i class="fas fa-spinner fa-spin"></i> Fetching activity...</td></tr>`;

    try {
        const res = await fetch(`${API_URL}/api/admin/logs`, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();

        if (res.ok && data.success) {
            tbody.innerHTML = '';
            if (data.logs.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No activity logs found. Try performing some actions!</td></tr>`;
                return;
            }
            data.logs.forEach(log => {
                const date = new Date(log.timestamp).toLocaleString();
                const row = `
                    <tr>
                        <td style="font-size: 0.85rem; color: #64748b;">${date}</td>
                        <td><strong>${log.user_email || 'System'}</strong></td>
                        <td><span class="badge ${log.action.includes('Delete') ? 'status-offline' : 's-active'}">${log.action}</span></td>
                        <td title="${log.details}" style="font-size: 0.85rem;">${log.details.substring(0, 50)}${log.details.length > 50 ? '...' : ''}</td>
                        <td style="font-family: monospace; font-size: 0.8rem;">${log.ip_address || '-'}</td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
        }
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center text-danger">Failed to load logs.</td></tr>`;
    }
}

async function adminClearLogs() {
    if (!confirm("Are you sure you want to PERMANENTLY delete all system audit logs?")) return;

    const token = localStorage.getItem('admin_token');
    try {
        const res = await fetch(`${API_URL}/api/admin/logs`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) adminLoadLogs();
    } catch (err) { alert("Error clearing logs"); }
}





// Doctor Appointments Loading
async function adminLoadAppointments() {
    const token = localStorage.getItem('admin_token');
    const tbody = document.getElementById('appointments-table-body');
    if (!tbody) return;

    tbody.innerHTML = `<tr><td colspan="9" class="text-center"><i class="fas fa-spinner fa-spin"></i> Loading appointments...</td></tr>`;

    try {
        const res = await fetch(`${API_URL}/api/admin/appointments`, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();

        if (res.ok && data.success) {
            if (data.appointments.length === 0) {
                tbody.innerHTML = `<tr><td colspan="9" class="text-center text-muted">No appointments found.</td></tr>`;
                return;
            }
            tbody.innerHTML = '';
            data.appointments.forEach(a => {
                const statusClass = a.status === 'Confirmed' ? 'status-online' : 'status-offline';
                tbody.innerHTML += `
                    <tr>
                        <td style="font-size: 0.8rem; color: #64748b;">#${a.id}</td>
                        <td>
                            <div style="font-size: 0.9rem; font-weight: 600;">${a.first_name} ${a.last_name}</div>
                            <div style="font-size: 0.75rem; color: #64748b;">${a.email}</div>
                        </td>
                        <td><strong>${a.doctor_name}</strong></td>
                        <td>${a.doctor_specialty}</td>
                        <td>
                            <div style="font-weight: 500;">${a.doctor_area}</div>
                            <div style="font-size: 0.75rem; color: #64748b;">${a.doctor_city || 'Unknown City'}</div>
                        </td>

                        <td style="font-size: 0.85rem;">${a.appointment_date}</td>
                        <td style="font-size: 0.85rem;">${a.appointment_time}</td>
                        <td><span class="badge ${statusClass}">${a.status}</span></td>
                        <td>
                             <button class="btn-icon" style="color: #64748b" title="Complete Record">
                                <i class="fas fa-check-circle"></i>
                            </button>
                        </td>
                    </tr>
                `;
            });
        } else {
            tbody.innerHTML = `<tr><td colspan="9" class="text-center text-danger">Error: ${data.message || 'Access Denied'}</td></tr>`;
        }
    } catch (err) {
        console.error(err);
        tbody.innerHTML = `<tr><td colspan="9" class="text-center text-danger">Network Error</td></tr>`;
    }
}
async function adminLoadLocations() {
    const token = localStorage.getItem('admin_token');
    const tbody = document.getElementById('locations-table-body');
    if (!tbody) return;

    tbody.innerHTML = `<tr><td colspan="6" class="text-center"><i class="fas fa-spinner fa-spin"></i> Fetching locations...</td></tr>`;

    try {
        const res = await fetch(`${API_URL}/api/admin/user-locations`, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();

        if (res.ok && data.success) {
            tbody.innerHTML = '';
            if (data.locations.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">No location data found.</td></tr>`;
                return;
            }
            data.locations.forEach(l => {
                const date = new Date(l.timestamp).toLocaleString();
                tbody.innerHTML += `
                    <tr>
                        <td>#${l.id}</td>
                        <td><strong>${l.patient_name}</strong></td>
                        <td>${l.email}</td>
                        <td>${l.latitude.toFixed(6)}</td>
                        <td>${l.longitude.toFixed(6)}</td>
                        <td style="font-size: 0.85rem; color: #64748b;">${date}</td>
                    </tr>
                `;
            });
        }
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">Failed to load locations.</td></tr>`;
    }
}

async function adminLoadOTPs() {
    const token = localStorage.getItem('admin_token');
    const tbody = document.getElementById('otps-table-body');
    if (!tbody) return;

    tbody.innerHTML = `<tr><td colspan="5" class="text-center"><i class="fas fa-spinner fa-spin"></i> Fetching OTPs...</td></tr>`;

    try {
        const res = await fetch(`${API_URL}/api/admin/otp-verifications`, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();

        if (res.ok && data.success) {
            tbody.innerHTML = '';
            if (data.otps.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No OTP records found.</td></tr>`;
                return;
            }
            data.otps.forEach(o => {
                const created = new Date(o.created_at).toLocaleString();
                const expires = new Date(o.expires_at).toLocaleString();
                tbody.innerHTML += `
                    <tr>
                        <td>#${o.id}</td>
                        <td>${o.contact}</td>
                        <td><span class="badge s-active" style="font-family: monospace; letter-spacing: 2px;">${o.otp}</span></td>
                        <td style="font-size: 0.85rem;">${expires}</td>
                        <td style="font-size: 0.85rem; color: #64748b;">${created}</td>
                    </tr>
                `;
            });
        }
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center text-danger">Failed to load OTPs.</td></tr>`;
    }
}

async function adminLoadLoginHistory() {
    const token = localStorage.getItem('admin_token');
    const tbody = document.getElementById('login-history-table-body');
    if (!tbody) return;

    tbody.innerHTML = `<tr><td colspan="8" class="text-center"><i class="fas fa-spinner fa-spin"></i> Fetching login history...</td></tr>`;

    let url = `${API_URL}/api/admin/login-history?page=1&limit=50`;
    const searchEl = document.getElementById('loginSearch');
    const dateEl = document.getElementById('loginDateFilter');
    const statusEl = document.getElementById('loginStatusFilter');
    
    if (statusEl && statusEl.value) {
        url += `&status=${statusEl.value}`;
    }
    if (dateEl && dateEl.value) {
        url += `&date=${dateEl.value}`;
    }
    if (searchEl && searchEl.value) {
        url += `&search=${encodeURIComponent(searchEl.value)}`;
    }

    try {
        const res = await fetch(url, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();

        if (res.ok && data.success) {
            tbody.innerHTML = '';
            
            const history = data.history;

            if (history.length === 0) {
                tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted">No login history found.</td></tr>`;
                return;
            }
            history.forEach(h => {
                const loginTime = new Date(h.login_time).toLocaleString();
                const logoutTime = h.logout_time ? new Date(h.logout_time).toLocaleString() : '-';
                
                let statusClass = 'status-offline';
                if (h.status === 'ACTIVE') statusClass = 'status-online s-active';
                else if (h.status === 'LOGIN') statusClass = 'status-online';

                const canForceLogout = h.status === 'LOGIN' || h.status === 'ACTIVE';
                const actionHtml = canForceLogout 
                    ? `<button class="btn btn-secondary" style="color: #ef4444; border-color: #fca5a5; padding: 4px 8px; font-size: 0.8rem;" onclick="adminForceLogout('${h.session_id}')">Force Logout</button>`
                    : '-';

                tbody.innerHTML += `
                    <tr>
                        <td><strong>${h.first_name} ${h.last_name}</strong></td>
                        <td>${h.email}</td>
                        <td style="font-size: 0.85rem;">${loginTime}</td>
                        <td style="font-size: 0.85rem;">${logoutTime}</td>
                        <td style="font-size: 0.85rem;" title="${h.device_info}">${h.device_info ? (h.device_info.substring(0, 20) + (h.device_info.length > 20 ? '...' : '')) : 'Unknown'}</td>
                        <td style="font-family: monospace; font-size: 0.8rem;">${h.ip_address || '-'}</td>
                        <td><span class="badge ${statusClass}">${h.status}</span></td>
                        <td>${actionHtml}</td>
                    </tr>
                `;
            });
        }
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">Failed to load login history.</td></tr>`;
    }
}

async function adminForceLogout(sessionId) {
    if (!confirm("Are you sure you want to force logout this session? The user will be disconnected automatically.")) return;

    const token = localStorage.getItem('admin_token');
    try {
        const res = await fetch(`${API_URL}/api/admin/force-logout/${sessionId}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        
        if (res.ok && data.success) {
            alert(data.message || "User logged out successfully.");
            adminLoadLoginHistory();
        } else {
            alert(`Error: ${data.detail || data.error}`);
        }
    } catch (err) { alert("Error force logging out."); }
}
