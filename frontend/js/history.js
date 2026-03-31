const API_BASE = window.DERMACARE_API_BASE || 'http://127.0.0.1:8000';

// ---------------------------
// Auth Token Helper
// ---------------------------
function getAuthToken() {
    return localStorage.getItem('dermacare_token');
}

function getAuthHeaders() {
    const token = getAuthToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return headers;
}

// ---------------------------
// History Management
// ---------------------------
let historyData = [];
let selectedIndex = -1;

window.loadHistory = async function() {
    const token = getAuthToken();
    let serverData = [];
    let serverStats = null;

    if (token) {
        try {
            const response = await fetch(API_BASE + '/api/scan/history', {
                headers: getAuthHeaders()
            });

            if (response.ok) {
                const data = await response.json();
                serverData = data.history || [];
                serverStats = data.stats;
            } else if (response.status === 401) {
                localStorage.removeItem('dermacare_token');
            }
        } catch (error) {
            console.warn('⚠️ API fetch failed:', error.message);
        }
    }

    // Get Local Data
    const localDataStr = localStorage.getItem('dermacare_history');
    const localData = localDataStr ? JSON.parse(localDataStr) : [];

    // Display Logic: Logged in users ONLY see server data. Guests see local.
    if (token) {
        historyData = serverData;
        if (serverStats) {
            const elTotal = document.getElementById('stat-total');
            const elAvg = document.getElementById('stat-avg-confidence');
            if (elTotal) elTotal.textContent = serverStats.total_scans;
            if (elAvg) elAvg.textContent = serverStats.avg_confidence + '%';
        } else {
            updateStatsLocal(historyData);
        }
    } else {
        historyData = localData || [];
        updateStatsLocal(historyData);
    }

    renderHistory();
};

function updateStatsLocal(history) {
    const elTotal = document.getElementById('stat-total');
    const elAvg = document.getElementById('stat-avg-confidence');

    if (elTotal) elTotal.textContent = history.length;

    if (history.length > 0) {
        const avg = history.reduce((sum, h) => sum + h.confidence, 0) / history.length;
        if (elAvg) elAvg.textContent = avg.toFixed(1) + '%';
    } else {
        if (elAvg) elAvg.textContent = '0%';
    }
}

function renderHistory() {
    const listEl = document.getElementById('history-list');
    const emptyEl = document.getElementById('empty-state');
    if(!listEl || !emptyEl) return;

    if (historyData.length === 0) {
        listEl.classList.add('hidden');
        emptyEl.classList.remove('hidden');
        return;
    }

    emptyEl.classList.add('hidden');
    listEl.classList.remove('hidden');

    // Sort by date (newest first)
    historyData.sort((a, b) => new Date(b.date) - new Date(a.date));

    listEl.innerHTML = historyData.map((item, index) => {
        const date = new Date(item.date);
        const formattedDate = date.toLocaleDateString('en-US', {
            year: 'numeric', month: 'short', day: 'numeric'
        });
        const formattedTime = date.toLocaleTimeString('en-US', {
            hour: '2-digit', minute: '2-digit'
        });

        const severityClass = getSeverityClass(item.disease, item.confidence);
        const isSelected = index === selectedIndex ? 'selected' : '';

        return `
            <div class="history-card fade-in ${isSelected}" style="padding: 1rem; margin-bottom: 0.75rem; cursor: pointer; border-radius: 12px; transition: all 0.2s ease;" onclick="showDetail(${index})">
                <div class="history-card-left" style="display: flex; align-items: center; gap: 0.75rem;">
                    <div class="history-disease-badge ${severityClass}" style="width: 35px; height: 35px; font-size: 0.8rem;">
                        <i class="${getDiseaseIcon(item.disease)}"></i>
                    </div>
                    <div class="history-card-info">
                        <h3 style="font-size: 0.95rem; margin-bottom: 0.1rem;">${item.disease}</h3>
                        <p class="history-date" style="font-size: 0.75rem;">
                            ${formattedDate} &bull; ${formattedTime}
                        </p>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function getSeverityClass(disease, confidence) {
    if (disease === 'Normal') return 'severity-normal';
    if (disease === 'Malignant') return 'severity-critical';
    if (confidence >= 80) return 'severity-high';
    return 'severity-moderate';
}

function getSeverityLabel(disease, confidence) {
    if (disease === 'Normal') return 'Healthy';
    if (disease === 'Malignant') return 'Critical';
    if (confidence >= 80) return 'High Confidence';
    return 'Moderate';
}

function getDiseaseIcon(disease) {
    const icons = {
        'Acne': 'fas fa-face-meh',
        'Benign': 'fas fa-shield-halved',
        'Eczema': 'fas fa-hand-dots',
        'Malignant': 'fas fa-triangle-exclamation',
        'Normal': 'fas fa-heart',
        'Psoriasis': 'fas fa-droplet',
        'Vitiligo': 'fas fa-palette',
        'Fungal': 'fas fa-virus'
    };
    return icons[disease] || 'fas fa-question-circle';
}

window.showDetail = function(index) {
    selectedIndex = index;
    renderHistory(); // Refresh to show selected state

    const item = historyData[index];
    if (!item) return;

    const date = new Date(item.date);
    const formattedDate = date.toLocaleDateString('en-US', {
        year: 'numeric', month: 'long', day: 'numeric'
    });
    const formattedTime = date.toLocaleTimeString('en-US', {
        hour: '2-digit', minute: '2-digit', second: '2-digit'
    });

    const severityClass = getSeverityClass(item.disease, item.confidence);

    let remediesHtml = '';
    if (item.remedies) {
        const sections = [
            { key: 'home_remedies', title: 'Home Remedies', icon: 'fas fa-home' },
            { key: 'skincare_routine', title: 'Skincare Routine', icon: 'fas fa-spa' },
            { key: 'diet_suggestions', title: 'Diet Suggestions', icon: 'fas fa-utensils' },
            { key: 'consult_doctor', title: 'Consult Doctor', icon: 'fas fa-user-md' }
        ];

        sections.forEach(section => {
            if (item.remedies[section.key] && item.remedies[section.key].length > 0) {
                const isWarning = section.key === 'consult_doctor';
                if (isWarning && (item.confidence < 60 || item.disease === 'Normal')) return;

                const titleColor = isWarning ? '#ef4444' : '#3b82f6';
                const iconColor = isWarning ? '#ef4444' : '#3b82f6';

                remediesHtml += `
                    <div class="modal-remedy-section" style="background: white; padding: 1.5rem; border-radius: 12px; border: 1px solid #e2e8f0; ${isWarning ? 'border-left: 4px solid #ef4444;' : ''}">
                        <h4 style="margin: 0 0 1rem 0; color: ${titleColor}; display: flex; align-items: center; gap: 0.5rem; font-size: 1.05rem;"><i class="${section.icon}" style="color: ${iconColor};"></i> ${section.title}</h4>
                        <ul style="padding-left: 1.25rem; font-size: 0.95rem; color: #334155; line-height: 1.6; margin: 0;">
                            ${item.remedies[section.key].map(r => `<li style="margin-bottom: 0.5rem;">${r}</li>`).join('')}
                        </ul>
                    </div>
                `;
            }
        });
    }

    const deleteIdentifier = item.id ? `deleteHistoryById(${item.id})` : `deleteHistoryByIndex(${index})`;

    const detailPane = document.getElementById('detail-pane');
    if(detailPane) {
        detailPane.innerHTML = `
            <div class="fade-in" style="display: flex; flex-direction: column;">
                <div class="detail-header" style="display: flex; flex-direction: row; gap: 2rem; align-items: center; margin-bottom: 2rem; padding: 2rem; background: #fdfdfd; border: 1px solid #e2e8f0; border-radius: 16px;">
                    <div class="modal-disease-icon ${severityClass}" style="width: 100px; height: 100px; font-size: 3rem; display: flex; align-items: center; justify-content: center; border-radius: 50%; color: white; flex-shrink: 0;">
                        <i class="${getDiseaseIcon(item.disease)}"></i>
                    </div>
                    <div style="flex: 1; text-align: left;">
                        <p style="text-transform: uppercase; font-size: 0.75rem; font-weight: 700; letter-spacing: 1px; color: #64748b; margin-bottom: 0.5rem;">SCAN RESULT</p>
                        <h2 style="font-size: 2.2rem; margin: 0 0 0.5rem 0; color: #0f172a; font-weight: 800;">${item.disease}</h2>
                        <p style="color: #64748b; font-weight: 500; font-size: 0.9rem; margin: 0;"><i class="fas fa-calendar-alt"></i> ${formattedDate} &bull; ${formattedTime}</p>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 2rem;">
                    <div style="background: white; padding: 1.5rem; border-radius: 16px; border: 1px solid #e2e8f0; display: flex; flex-direction: column; box-shadow: 0 2px 4px rgba(0,0,0,0.02)">
                        <p style="text-transform: uppercase; font-size: 0.75rem; font-weight: 700; letter-spacing: 1px; color: #64748b; margin-bottom: 0.5rem;">Confidence Score</p>
                        <div style="font-size: 2.2rem; font-weight: 800; color: #3b82f6;">${item.confidence}%</div>
                    </div>
                    <div style="background: white; padding: 1.5rem; border-radius: 16px; border: 1px solid #e2e8f0; display: flex; flex-direction: column; box-shadow: 0 2px 4px rgba(0,0,0,0.02)">
                        <p style="text-transform: uppercase; font-size: 0.75rem; font-weight: 700; letter-spacing: 1px; color: #64748b; margin-bottom: 0.5rem;">Clinical Status</p>
                        <span class="severity-tag ${severityClass}" style="display: inline-block; padding: 0.4rem 1rem; border-radius: 8px; font-weight: 700; font-size: 0.95rem; margin-top: 0.5rem; width: fit-content;">
                            ${getSeverityLabel(item.disease, item.confidence)}
                        </span>
                    </div>
                </div>

                ${remediesHtml ? `
                    <div style="margin-bottom: 4rem; background: #fdfdfd; padding: 2rem; border-radius: 16px; border: 1px solid #e2e8f0;">
                        <h3 style="margin: 0 0 1.5rem 0; font-weight: 800; font-size: 1.25rem; color: #0f172a; display: flex; align-items: center; gap: 0.5rem;"><i class="fas fa-notes-medical" style="color: #3b82f6;"></i> Recommendations</h3>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
                            ${remediesHtml}
                        </div>
                    </div>
                ` : ''}

                <div style="display: flex; gap: 1rem; justify-content: center; margin-top: 2rem; padding-top: 2rem; border-top: 1px solid #e2e8f0;">
                    <button class="btn btn-primary" style="padding: 1rem 3rem; border-radius: 30px; font-weight: 600; font-size: 1rem; box-shadow: 0 4px 12px rgba(59,130,246,0.3);" onclick="window.location.href='detection.html'"><i class="fas fa-redo"></i> Scan Again</button>
                    <button class="btn btn-secondary" style="padding: 1rem 3rem; border-radius: 30px; font-weight: 600; font-size: 1rem; color: #ef4444; border-color: #fecaca; background: #fef2f2;" onclick="${deleteIdentifier}">
                        <i class="fas fa-trash-alt"></i> Delete Record
                    </button>
                </div>
            </div>
        `;
    }
};

window.deleteHistoryById = async function(scanId) {
    if (!confirm('Are you sure you want to delete this record?')) return;
    try {
        const response = await fetch(API_BASE + '/api/scan/history/' + scanId, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if (response.ok) {
            showNotification('Record deleted successfully!');
            resetDetailPane();
            await loadHistory();
        } else {
            alert('Failed to delete record.');
        }
    } catch (error) {
        alert('Could not connect to server.');
    }
};

window.deleteHistoryByIndex = function(index) {
    if (!confirm('Are you sure you want to delete this record?')) return;
    const history = JSON.parse(localStorage.getItem('dermacare_history') || '[]');
    history.sort((a, b) => new Date(b.date) - new Date(a.date));
    history.splice(index, 1);
    localStorage.setItem('dermacare_history', JSON.stringify(history));
    showNotification('Local record removed.');
    resetDetailPane();
    historyData = history;
    updateStatsLocal(history);
    renderHistory();
};

function showNotification(message) {
    const toast = document.createElement('div');
    toast.className = 'fade-in';
    toast.style.position = 'fixed';
    toast.style.bottom = '20px';
    toast.style.right = '20px';
    toast.style.background = '#0f172a';
    toast.style.color = 'white';
    toast.style.padding = '1rem 1.5rem';
    toast.style.borderRadius = '12px';
    toast.style.boxShadow = '0 10px 15px -3px rgba(0,0,0,0.1)';
    toast.style.zIndex = '9999';
    toast.style.display = 'flex';
    toast.style.alignItems = 'center';
    toast.style.gap = '10px';
    toast.innerHTML = `<i class="fas fa-check-circle" style="color: #10b981;"></i> ${message}`;

    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.5s ease';
        setTimeout(() => toast.remove(), 500);
    }, 3000);
}

function resetDetailPane() {
    selectedIndex = -1;
    const detailPane = document.getElementById('detail-pane');
    if(detailPane) {
        detailPane.innerHTML = `
            <div class="empty-detail-state">
                <i class="fas fa-file-medical"></i>
                <h3>Select a Record</h3>
                <p>Click on any scan from the list to view detailed analysis and recommendations.</p>
            </div>
        `;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const token = getAuthToken();
    if (!token) {
        window.location.href = 'login.html';
        return;
    }
    loadHistory();
});
