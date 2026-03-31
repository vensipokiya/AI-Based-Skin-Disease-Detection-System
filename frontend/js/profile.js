document.addEventListener('DOMContentLoaded', async () => {
    const token = localStorage.getItem('dermacare_token');

    if (!token) {
        window.location.href = 'login.html';
        return;
    }

    // Base API URL
    const API_URL = (typeof window !== 'undefined' && window.DERMACARE_API_BASE) ? window.DERMACARE_API_BASE : 'http://127.0.0.1:8000';

    try {
        const response = await fetch(`${API_URL}/api/user/profile`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            if (response.status === 401) {
                localStorage.removeItem('dermacare_token');
                window.location.href = 'login.html';
                return;
            }
            throw new Error('Failed to fetch profile');
        }

        const profile = await response.json();
        populateProfile(profile);

    } catch (error) {
        console.error('Error loading profile:', error);
        alert('Could not load profile details. Please try again later.');
    }

    // Handle Logout
    const logoutTriggers = document.querySelectorAll('.logout-btn-trigger');
    logoutTriggers.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            try {
                await fetch(`${API_URL}/api/auth/logout`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}` }
                });
            } catch (err) {
                console.error('Logout error:', err);
            } finally {
                localStorage.removeItem('dermacare_token');
                window.location.href = 'login.html';
            }
        });
    });
});

function populateProfile(data) {
    const fullName = `${data.first_name} ${data.last_name}`;

    // Sidebar info
    const sidebarName = document.getElementById('sidebar-name');
    const sidebarEmail = document.getElementById('sidebar-email');
    const sidebarAvatar = document.getElementById('sidebar-avatar');

    if (sidebarName) sidebarName.textContent = fullName;
    if (sidebarEmail) sidebarEmail.textContent = data.email;
    if (sidebarAvatar) sidebarAvatar.src = `https://i.pravatar.cc/150?u=${data.email}`;

    // Profile card info
    const profileAvatar = document.getElementById('profile-avatar');
    const inputFullName = document.getElementById('prof-fullname');
    const inputEmail = document.getElementById('prof-email');
    const inputPhone = document.getElementById('prof-phone');
    const inputDob = document.getElementById('prof-dob');
    const inputGender = document.getElementById('prof-gender');

    if (profileAvatar) profileAvatar.src = `https://i.pravatar.cc/150?u=${data.email}`;
    if (inputFullName) inputFullName.value = fullName;
    if (inputEmail) inputEmail.value = data.email;
    if (inputPhone) inputPhone.value = data.contact_number || '';
    if (inputDob) inputDob.value = data.date_of_birth || '';
    if (inputGender) inputGender.value = data.gender || 'Male';
}
