/**
 * nearby_dermatologist.js
 * DermaCare AI — Nearby Dermatologist Page
 * Triggers the map load automatically on DOMContentLoaded.
 */
window.addEventListener('DOMContentLoaded', () => {
    if (typeof loadGoogleMapsNearby === 'function') {
        loadGoogleMapsNearby();
    }
});
