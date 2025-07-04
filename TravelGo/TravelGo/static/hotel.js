document.addEventListener("DOMContentLoaded", function () {
    const hotelImage = document.querySelector('img[alt="Hotel"]');
    if (hotelImage) {
        hotelImage.style.cursor = "pointer";
        hotelImage.addEventListener("click", function () {
            window.location.href = "hotel.js";
        });
    }
});