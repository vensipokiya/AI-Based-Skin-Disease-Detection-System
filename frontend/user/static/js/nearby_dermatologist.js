window.addEventListener('DOMContentLoaded', () => {
    const detectBtn = document.getElementById('btn-detect-nearby');
    const locationStatus = document.getElementById('location-status');
    const locationControls = document.getElementById('location-controls');

    if (detectBtn) {
        detectBtn.addEventListener('click', () => {
            if (typeof loadGoogleMapsNearby === 'function') {
                if (locationStatus) locationStatus.style.display = 'block';
                if (locationControls) locationControls.style.display = 'none';
                loadGoogleMapsNearby();
            }
        });
    }
});
