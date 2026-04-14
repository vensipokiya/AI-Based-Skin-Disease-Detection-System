/**
 * booking.js
 * DermaCare AI — Appointment Booking Logic
 */

// ---------------------------
// Booking Appointment Logic
// ---------------------------

/**
 * cancelBookingConfirmation
 * Redirects back to the nearby specialists page.
 */
window.cancelBookingConfirmation = function() {
    window.location.href = '/nearby';
};

/**
 * submitBooking
 * Handles the submission of the appointment form.
 * @param {Event} event - The form submission event
 */
window.submitBooking = async function(event) {
    if (event) event.preventDefault();
    
    const dateInput = document.getElementById('booking-date');
    const timeInput = document.getElementById('booking-time');

    if (!dateInput || !dateInput.value || !timeInput || !timeInput.value) {
        alert('Please select both a date and a time.');
        return;
    }

    const selectedDate = new Date(dateInput.value);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    if (selectedDate < today) {
        alert('Please select a current or future date.');
        return;
    }

    // Save appointment data to localStorage
    localStorage.setItem('pendingAppointment', JSON.stringify({
        date: dateInput.value,        // YYYY-MM-DD
        time: timeInput.value + ':00' // HH:MM:SS
    }));

    // Submit to backend via dermacare-api.js utility
    if (typeof finalizeBooking === 'function') {
        await finalizeBooking();
    } else {
        console.error('finalizeBooking utility not found.');
    }
};

// ---------------------------
// Event Listeners & Population
// ---------------------------

document.addEventListener('DOMContentLoaded', () => {
    // Populate doctor name on booking page
    const bookingDocName = document.getElementById('booking-doctor-name');
    const docDetailName = document.getElementById('doc-detail-name');
    
    const dataStr = localStorage.getItem('selectedDoctorDetails');
    
    if (dataStr) {
        try {
            const data = JSON.parse(dataStr);
            
            // For booking_appointment.html
            if (docDetailName) {
                docDetailName.innerText = data.name;
                const address = document.getElementById('doc-detail-address');
                const phone = document.getElementById('doc-detail-phone');
                const time = document.getElementById('doc-detail-time');
                const rating = document.getElementById('doc-detail-rating');
                const review = document.getElementById('doc-detail-review');
                const title = document.getElementById('doc-detail-title');
                const imgContainer = document.getElementById('doc-detail-img-container');

                if (address) address.innerText = data.address || 'N/A';
                if (phone) phone.innerText = data.phone || 'N/A';
                if (time) time.innerText = data.time || 'N/A';
                if (rating) rating.innerHTML = `<i class="fas fa-star"></i> ${data.rating || '4.5'} (${data.reviews || '0'} reviews)`;
                if (review && data.review) review.innerText = `"${data.review}"`;

                if (title && imgContainer) {
                    if (data.isSpecialist) {
                        title.innerText = 'Skin Specialist / Surgeon';
                        imgContainer.style.background = 'linear-gradient(135deg, #10b981, #34d399)';
                    } else {
                        title.innerText = 'General Dermatologist';
                        imgContainer.style.background = 'linear-gradient(135deg, #2563eb, #38bdf8)';
                    }
                }
            }
            
            // For confirm_booking.html
            if (bookingDocName) {
                bookingDocName.textContent = data.name;
            }
        } catch (e) {
            console.error('Error populating doctor details', e);
        }
    }

    // Set min date to today for booking inputs
    const dateInput = document.getElementById('booking-date');
    if (dateInput) {
        const today = new Date().toISOString().split('T')[0];
        dateInput.setAttribute('min', today);
    }
});
