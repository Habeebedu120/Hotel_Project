
// Lightbox functionality
function openLightbox(lightboxId, slideIndex) {
    const lightboxModal = new bootstrap.Modal(document.getElementById(lightboxId));
    const carousel = document.getElementById(lightboxId + 'Carousel');
    const bsCarousel = bootstrap.Carousel.getInstance(carousel) || new bootstrap.Carousel(carousel);
    bsCarousel.to(slideIndex);
    lightboxModal.show();
}

// Amenities lightbox functionality
function openAmenitiesLightbox(slideIndex) {
    const lightboxModal = new bootstrap.Modal(document.getElementById('amenitiesLightbox'));
    const carousel = document.getElementById('amenitiesLightboxCarousel');
    const bsCarousel = bootstrap.Carousel.getInstance(carousel) || new bootstrap.Carousel(carousel);
    bsCarousel.to(slideIndex);
    lightboxModal.show();
}

// Single image lightbox for Experience and Gallery sections
function openSingleImageLightbox(imageSrc, caption) {
    document.getElementById('singleLightboxImage').src = imageSrc;
    document.getElementById('singleLightboxCaption').textContent = caption;
    const lightboxModal = new bootstrap.Modal(document.getElementById('singleImageLightbox'));
    lightboxModal.show();
}

// smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(function (a) {
    a.addEventListener('click', function (e) {
        var target = document.querySelector(this.getAttribute('href'));
        if (target) {
            e.preventDefault();
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});

// Price calculation and date validation
document.addEventListener('DOMContentLoaded', function () {
    const checkinInput = document.querySelector('input[name="checkin"]');
    const checkoutInput = document.querySelector('input[name="checkout"]');
    const roomSelect = document.querySelector('select[name="room_type_id"]');
    const priceDisplay = document.getElementById('priceCalculation');
    const totalPriceSpan = document.getElementById('totalPrice');
    const nightsSpan = document.getElementById('nightsCount');

    // Set min date for checkin to today
    const today = new Date().toISOString().split('T')[0];
    if (checkinInput) checkinInput.min = today;

    function calculatePrice() {
        const checkin = new Date(checkinInput.value);
        const checkout = new Date(checkoutInput.value);
        const selectedOption = roomSelect.selectedOptions[0];

        if (checkin && checkout && checkin < checkout && selectedOption && selectedOption.value) {
            const price = parseInt(selectedOption.dataset.price);
            const nights = Math.ceil((checkout - checkin) / (1000 * 60 * 60 * 24));
            const total = price * nights;

            totalPriceSpan.textContent = `₦${total.toLocaleString()}`;
            nightsSpan.textContent = nights;
            priceDisplay.style.display = 'block';
        } else {
            priceDisplay.style.display = 'none';
        }
    }

    if (checkinInput) checkinInput.addEventListener('change', calculatePrice);
    if (checkoutInput) checkoutInput.addEventListener('change', calculatePrice);
    if (roomSelect) roomSelect.addEventListener('change', calculatePrice);

    // Update room availability in real-time
    function updateRoomOptions() {
        // This would typically make an AJAX call to get latest availability
        console.log('Room availability should be refreshed');
    }

    // Refresh availability when modal opens
    const bookingModal = document.getElementById('bookingModal');
    if (bookingModal) {
        bookingModal.addEventListener('show.bs.modal', updateRoomOptions);
    }


});
