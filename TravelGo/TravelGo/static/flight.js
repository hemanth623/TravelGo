document.addEventListener("DOMContentLoaded", function () {
    const flightImage = document.querySelector('img[alt="Flight"]');
    if (flightImage) {
        flightImage.style.cursor = "pointer";
        flightImage.addEventListener("click", function () {
            window.location.href = "flight.js";
        });
    }
});