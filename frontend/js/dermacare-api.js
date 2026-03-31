/**
 * Single API origin for DermaCare — avoids localhost vs 127.0.0.1 token mismatch.
 * When served from FastAPI (port 8000), uses page origin. Otherwise localStorage or default.
 */
(function () {
    var w = window;
    var origin = '';
    try {
        if (w.location.protocol !== 'file:' && String(w.location.port) === '8000') {
            origin = w.location.origin;
        } else {
            // Force 8000 out of local cache bugs
            origin = 'http://127.0.0.1:8000';
        }
    } catch (e) {
        origin = 'http://127.0.0.1:8000';
    }
    w.DERMACARE_API_BASE = origin;
})();
