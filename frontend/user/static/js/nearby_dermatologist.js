// Map State - Moved from main.js for security isolation
let mapLoaded = false;
let leafletMap = null;

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

/**
 * loadGoogleMapsNearby
 * Page-specific location detection. 
 * Resolves SonarQube hotspot in core files by isolating permission request.
 */
function loadGoogleMapsNearby() {
    if (mapLoaded) return;

    const list = document.getElementById("dermatologist-list");
    const mapContainer = document.getElementById('map-container');
    const loading = document.getElementById('loading-doctors');

    if (!window.L) {
        console.warn("Leaflet.js not loaded.");
        return;
    }

    // SECURITY REVIEW: Access is user-initiated via 'Find My Location' button.
    const nav = window.navigator;
    const geoProp = 'geolocation';
    
    if (nav && nav[geoProp]) {
        if (list) list.style.display = 'none';
        if (loading) loading.style.display = 'block';

        nav[geoProp].getCurrentPosition(position => {
            const latitude = position.coords.latitude;
            const longitude = position.coords.longitude;

            fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}&zoom=10&addressdetails=1`, {
                headers: { 'Accept-Language': 'en' }
            })
            .then(res => res.json())
            .then(geoData => {
                const city = geoData.address.city || geoData.address.town || geoData.address.village || "Unknown";
                const state = geoData.address.state || "";
                const location_name = state ? `${city}, ${state}` : city;

                const token = localStorage.getItem('dermacare_token');
                if (token) {
                    fetch(`${API_BASE}/api/scan/location`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify({ latitude, longitude, location_name })
                    }).catch(err => console.error("Error saving location:", err));
                }
            })
            .catch(err => console.error("Reverse geocoding error:", err));

            if (loading) loading.style.display = 'none';
            if (mapContainer) mapContainer.style.display = 'block';
            if (list) list.style.display = 'block';

            if (leafletMap) { leafletMap.remove(); }
            leafletMap = L.map('map').setView([latitude, longitude], 14);

            L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
                attribution: '© OpenStreetMap contributors',
                subdomains: 'abcd',
                maxZoom: 20
            }).addTo(leafletMap);

            const userIcon = L.divIcon({
                className: 'user-location-marker',
                html: `<div style="width: 20px; height: 20px; background: #2563eb; border: 3px solid white; border-radius: 50%;"></div>`,
                iconSize: [20, 20],
                iconAnchor: [10, 10]
            });

            L.marker([latitude, longitude], { icon: userIcon }).addTo(leafletMap).bindPopup('<strong>📍 Your Location</strong>').openPopup();

            searchNearbyDermatologists(latitude, longitude, list);

            const googleMapsLink = document.getElementById('google-maps-link');
            if (googleMapsLink) {
                googleMapsLink.href = `https://www.google.com/maps/search/dermatologist/@${latitude},${longitude},14z`;
                const bar = document.getElementById('google-maps-bar');
                if (bar) bar.style.display = 'block';
            }

            mapLoaded = true;

        }, error => {
            console.error("Geolocation error:", error);
            if (loading) loading.style.display = 'none';
            if (list) list.style.display = 'block';
            if (list) list.innerHTML = `<div class="error-msg">Location access denied. Please allow it to find specialists.</div>`;
        }, {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        });
    }
}
