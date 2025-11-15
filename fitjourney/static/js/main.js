// Calculate BMI using values from the Profile Card
document.addEventListener('DOMContentLoaded', function () {
    const heightInput = document.getElementById('profileHeight');
    const weightInput = document.getElementById('profileWeight');
    const bmiResultInput = document.getElementById("bmiResult");
    const bmiButton = document.getElementById('bmiButton');

    function calculateBMIFromProfile() {
        const height = parseFloat(heightInput.value);
        const weight = parseFloat(weightInput.value);

        if (!height || !weight || height <= 0 || weight <= 0) {
            bmiResultInput.value = '';
            return;
        }

        const bmi = (weight / ((height / 100) ** 2)).toFixed(2);
        bmiResultInput.value = bmi;
    }

    if (bmiButton) {
        bmiButton.addEventListener('click', calculateBMIFromProfile);
    }

    // Optionally auto-calculate if inputs are pre-filled
    calculateBMIFromProfile();
});

// This is your existing toggleDropdown function (assuming you have one)
function toggleDropdown(button) {
    const dropdownOptions = button.nextElementSibling; // Gets the div.dropdown-options
    dropdownOptions.style.display = dropdownOptions.style.display === 'block' ? 'none' : 'block';
}

function redirectToMeditationOptions(event) {
    console.log("Meditation option clicked! Attempting redirect."); // <-- CONFIRM THIS IS HERE
    event.preventDefault();
    window.location.href = '/meditation-options';
}