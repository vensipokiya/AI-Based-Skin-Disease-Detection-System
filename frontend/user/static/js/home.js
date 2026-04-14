/**
 * home.js
 * DermaCare AI — Landing Page Logic
 */

/**
 * switchMainTab
 * Handles switching between 'How it Works' and 'Features' on the landing page.
 * @param {string} tabId - ID of the tab content to show
 * @param {HTMLElement} btn - The button element that was clicked
 */
window.switchMainTab = function(tabId, btn) {
    // Hide all tab content
    document.querySelectorAll('.main-tab-content').forEach(el => {
        el.classList.add('hidden');
        el.classList.remove('fade-in');
    });

    // Show the selected tab
    const target = document.getElementById(tabId);
    if (target) {
        target.classList.remove('hidden');
        target.classList.add('fade-in');
    }

    // Update button styles for all landing tab buttons
    document.querySelectorAll('.tab-btn-main').forEach(el => {
        el.className = 'btn btn-secondary tab-btn-main';
        el.style.background = 'transparent';
        el.style.color = 'var(--text-light)';
        el.style.boxShadow = 'none';
    });

    // Set active button styles
    if (btn) {
        btn.className = 'btn btn-primary tab-btn-main active';
        btn.style.background = 'linear-gradient(135deg, var(--primary-color), var(--accent-color))';
        btn.style.color = 'var(--white)';
        btn.style.boxShadow = 'var(--shadow-md)';
    }
};
