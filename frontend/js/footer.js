/**
 * DermaCare AI Reusable Footer Loader
 * Dynamically injects the footer HTML into the #footer placeholder.
 */

document.addEventListener('DOMContentLoaded', () => {
    const footerPlaceholder = document.getElementById('footer');
    if (!footerPlaceholder) return;

    // Direct injection of footer HTML to ensure it works on all environments (even without a server)
    footerPlaceholder.innerHTML = `
    <footer id="main-footer">
        <div class="container">
            <div class="footer-grid">
                <!-- Column 1: Brand -->
                <div class="footer-col" style="min-width: 250px;">
                    <a href="/" class="logo" style="color: white; margin-bottom: 1.5rem; display: inline-flex;">
                        <i class="fas fa-microscope" style="color: var(--accent-color);"></i>
                        DermaCare <span style="color: var(--accent-color);">AI</span>
                    </a>
                    <p>Empowering better skin health through advanced AI technology, our system analyzes skin conditions
                        with precision and provides reliable insights, early detection support, and personalized care
                        recommendations.</p>
                </div>

                <!-- Column 2: Services -->
                <div class="footer-col">
                    <h4>Services</h4>
                    <ul class="footer-links">
                        <li><a href="detection.html">AI Scanner</a></li>
                        <li><a href="detection.html">Skin Analysis</a></li>
                        <li><a href="history.html">Suggested Remedies</a></li>
                        <li><a href="javascript:void(0)" onclick="alert('Find Dermatologist feature coming soon!')">Find Dermatologist</a></li>
                        <li><a href="history.html">Scan History</a></li>
                    </ul>
                </div>

                <!-- Column 3: Quick Links -->
                <div class="footer-col">
                    <h4>Quick Links</h4>
                    <ul class="footer-links">
                        <li><a href="index.html">Home</a></li>
                        <li><a href="About_Us.html">About Us</a></li>
                        <li><a href="index.html#how-it-works">How It Works</a></li>
                        <li><a href="index.html#features">Features</a></li>
                    </ul>
                </div>

                <!-- Column 4: Contact -->
                <div class="footer-col">
                    <h4>Contact</h4>
                    <div class="contact-item">
                        <i class="fas fa-envelope"></i>
                        <span>support@dermacare.ai</span>
                    </div>
                    <div class="contact-item">
                        <i class="fas fa-map-marker-alt"></i>
                        <span>India</span>
                    </div>
                </div>
            </div>

            <!-- Footer Bottom -->
            <div class="footer-bottom">
                <div class="copyright">
                    &copy; 2026 <strong>DermaCare AI.</strong> All rights reserved.
                </div>
                <div class="footer-bottom-links">
                    <a href="#">Privacy Policy</a>
                    <span>|</span>
                    <a href="#">Terms of Service</a>
                </div>
                <div class="social-links">
                    <a href="#" class="social-icon"><i class="fab fa-facebook"></i></a>
                    <a href="#" class="social-icon"><i class="fab fa-instagram"></i></a>
                    <a href="#" class="social-icon"><i class="fab fa-twitter"></i></a>
                </div>
            </div>
        </div>
    </footer>`;
});
