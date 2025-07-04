document.addEventListener("DOMContentLoaded", function () {
    const trainImage = document.querySelector('img[alt="Train"]');
    if (trainImage) {
        trainImage.style.cursor = "pointer";
        trainImage.addEventListener("click", function () {
            window.location.href = "train.html";
        });
    }
});