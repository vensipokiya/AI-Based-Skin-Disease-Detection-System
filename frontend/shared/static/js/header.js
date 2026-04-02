document.addEventListener('DOMContentLoaded', () => {
    // Inject header CSS if not already present
    if (!document.querySelector('link[href*="header.css"]')) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = '/static/shared/css/header.css';
        document.head.appendChild(link);
    }

    const headerContainer = document.getElementById('header-container');
    if (!headerContainer) return; // Only run if placeholder exists

    // Inject header directly to avoid CORS issues on file:/// protocol
    const headerHTML = `
<header id="main-header" class="header-container">
    <div class="container nav rounded-nav">
        <a href="/" class="logo">
            <i class="fas fa-microscope text-gradient"></i>
            DermaCare <span>AI</span>
        </a>

        <ul class="nav-links" id="nav-menu">
            <li><a href="/" class="nav-item">Home</a></li>
            <li><a href="/about" class="nav-item">About Us</a></li>
            <li><a href="/detect" class="nav-item">AI Scanner</a></li>
            <li id="nav-history-item"><a href="/history" class="nav-item">History</a></li>
        </ul>

        <div class="user-actions">
            <!-- Logged Out State -->
            <div id="auth-buttons" class="auth-buttons">
                <a href="/login" class="btn btn-secondary">Sign In</a>
                <a href="/register" class="btn btn-primary">Register</a>
            </div>

            <!-- Logged In State -->
            <div id="user-profile-menu" class="user-profile-dropdown" style="display: none;">
                <div class="profile-trigger" id="profile-trigger">
                    <img src="https://i.pravatar.cc/150" alt="User Avatar" id="header-avatar" class="header-avatar">
                    <span id="header-username" class="header-user-name">User</span>
                    <i class="fas fa-chevron-down" style="font-size: 0.8em;"></i>
                </div>
                <ul class="profile-dropdown-menu" id="profile-menu">
                    <li id="admin-panel-link" style="display:none;"><a href="/admin"><i class="fas fa-shield-alt"></i> Admin Panel</a></li>
                    <li><a href="/profile"><i class="fas fa-user-circle"></i> My Profile</a></li>
                    <li><a href="/history"><i class="fas fa-history"></i> My History</a></li>
                    <div class="dropdown-divider"></div>
                    <li><a href="#" id="header-logout-btn" style="color: #ef4444;"><i class="fas fa-sign-out-alt"></i>
                            Logout</a></li>
                </ul>
            </div>
        </div>

        <!-- Mobile Toggle -->
        <button class="mobile-menu-toggle" id="mobile-menu-toggle">
            <i class="fas fa-bars"></i>
        </button>
    </div>
</header>
    `;

    headerContainer.innerHTML = headerHTML;

    // Initialization Logic once loaded
    initializeHeader();
});

function initializeHeader() {
    // 1. Highlight Active Page
    const currentPath = window.location.pathname.split('/').pop() || '/';
    const navItems = document.querySelectorAll('.nav-item');

    // Default matching logic
    navItems.forEach(item => {
        item.classList.remove('active');
        if (item.getAttribute('href') === currentPath ||
            (currentPath === '/' && item.getAttribute('href').startsWith('/'))) {
            // Slight distinction for index sections vs pages
            if (item.getAttribute('href') === currentPath) {
                item.classList.add('active');
            }
        }
    });

    // Manual matching for specific sections
    if (currentPath === '/' && window.location.hash !== '#features') {
        const homeLink = Array.from(navItems).find(n => n.textContent.trim() === 'Home');
        if (homeLink) homeLink.classList.add('active');
    }
    if (currentPath.includes('detection.') || currentPath.includes('Scan_') || currentPath.includes('nearby') || currentPath.includes('booking')) {
        const scanLink = Array.from(navItems).find(n => n.textContent.trim().includes('Scanner') || n.textContent.trim() === 'Scan');
        if (scanLink) scanLink.classList.add('active');
    }

    // 2. Auth Logic via localStorage
    const authButtons = document.getElementById('auth-buttons');
    const profileMenu = document.getElementById('user-profile-menu');
    const headerUsername = document.getElementById('header-username');
    const headerAvatar = document.getElementById('header-avatar');
    const headerEmail = document.getElementById('header-email');
    const historyNav = document.getElementById('nav-history-item');
    const loginNav = document.getElementById('nav-login-item');
    const logoutBtn = document.getElementById('header-logout-btn');

    // Default to true if user logged in via API, or simulated
    const token = localStorage.getItem('dermacare_token');

    if (token) {
        // Logged In
        if (authButtons) authButtons.style.display = 'none';
        if (profileMenu) profileMenu.style.display = 'block';
        if (historyNav) historyNav.style.display = 'block';
        if (loginNav) loginNav.style.display = 'none';

        // Extract user info
        let user = { name: 'User', email: 'user@example.com' };
        try {
            const stored = localStorage.getItem('dermacare_current_user');
            if (stored) {
                const parsed = JSON.parse(stored);
                user.name = parsed.first_name || parsed.username || 'User';
                user.email = parsed.email || 'user@example.com';
                user.role = parsed.role || 'User';
            }
        } catch (e) { }

        if (headerUsername) headerUsername.textContent = user.name;
        if (headerEmail) headerEmail.textContent = user.email;

        const adminLink = document.getElementById('admin-panel-link');
        if (adminLink && user.role === 'Admin') {
            adminLink.style.display = 'block';
        }

        const avatarKey = `dermacare_avatar_${user.email || 'guest'}`;
        const savedAvatar = localStorage.getItem(avatarKey);
        const fallbackAvatar = `https://ui-avatars.com/api/?name=${encodeURIComponent(user.name)}&background=2563eb&color=fff&size=150&bold=true`;
        if (headerAvatar) {
            headerAvatar.src = savedAvatar ? savedAvatar : fallbackAvatar;
        }

        // Logout Event
        if (logoutBtn) {
            logoutBtn.addEventListener('click', (e) => {
                e.preventDefault();
                // Clear state
                localStorage.removeItem('dermacare_token');
                localStorage.removeItem('dermacare_current_user');
                sessionStorage.clear();
                // API logout call could be added here
                if (window.API_URL) {
                    fetch(window.API_URL + '/api/auth/logout', {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${token}` }
                    }).catch(console.error);
                }

                // Redirect
                window.location.href = '/login';
            });
        }
    } else {
        // Logged Out
        if (authButtons) authButtons.style.display = 'flex';
        if (profileMenu) profileMenu.style.display = 'none';
        if (historyNav) historyNav.style.display = 'none';
        if (loginNav) loginNav.style.display = 'block';
    }

    // Dropdown toggle works on click
    const profileTriggerBtn = document.getElementById('profile-trigger');
    const dropdownMenu = document.querySelector('.profile-dropdown-menu');
    if (profileTriggerBtn && dropdownMenu) {
        profileTriggerBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            profileTriggerBtn.classList.toggle('active');
            // If css doesn't rely on .active, toggle display inline
            if (dropdownMenu.style.display === 'block') {
                dropdownMenu.style.display = 'none';
            } else {
                dropdownMenu.style.display = 'block';
                dropdownMenu.style.opacity = '1';
                dropdownMenu.style.visibility = 'visible';
            }
        });

        document.addEventListener('click', (e) => {
            if (!profileTriggerBtn.contains(e.target)) {
                profileTriggerBtn.classList.remove('active');
                dropdownMenu.style.display = 'none';
                dropdownMenu.style.opacity = '0';
                dropdownMenu.style.visibility = 'hidden';
            }
        });
    }
}
