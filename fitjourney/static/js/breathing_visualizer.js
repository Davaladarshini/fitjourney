// static/js/breathing_visualizer.js

const breathingCircle = document.getElementById('breathingCircle');
const instructionsDisplay = document.getElementById('instructions');
const timerDisplay = document.getElementById('timer');
const startButton = document.getElementById('startButton');
const stopButton = document.getElementById('stopButton');
const patternSelect = document.getElementById('patternSelect');

// Audio elements (make sure these IDs match your HTML and files exist in static/audio/)
const backgroundMusic = document.getElementById('backgroundMusic');
const inhaleSound = document.getElementById('inhaleSound');
const exhaleSound = document.getElementById('exhaleSound');
const holdSound = document.getElementById('holdSound');


// This will be updated by the fetch request from the backend
let currentBreathingPattern = [
    { text: "Inhale", duration: 4, className: "expand" },
    { text: "Hold", duration: 4, className: "hold" },
    { text: "Exhale", duration: 6, className: "contract" },
    { text: "Hold", duration: 2, className: "hold" } // Default, in case fetch fails or is not available
];

let patternIndex = 0;
let cycleTimeout; // Timeout for the entire duration of a breathing step (e.g., 4s for Inhale)
let totalSeconds = 0; // Overall elapsed time for the entire breathing session
let timerInterval; // Interval for updating the overall timer (totalSeconds)
let isBreathingActive = false;
let stepCountdownInterval; // Interval for the numerical countdown *inside* the breathing circle

/**
 * Fetches the specific breathing pattern data from the Flask backend.
 * This is an asynchronous operation.
 * @param {string} patternName - The name of the breathing pattern to fetch (e.g., 'box', '4-7-8').
 */
async function fetchBreathingPattern(patternName) {
    console.log("[fetchPattern] Attempting to fetch pattern:", patternName);
    try {
        const response = await fetch('/get-breathing-pattern', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pattern: patternName })
        });
        if (!response.ok) {
            // Log detailed error if the HTTP response is not OK
            console.error(`[fetchPattern] HTTP error! Status: ${response.status} - ${response.statusText}`);
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const data = await response.json();
        currentBreathingPattern = data; // Update the global variable with the fetched pattern
        console.log("[fetchPattern] Fetched pattern successfully:", currentBreathingPattern);
    } catch (error) {
        console.error('[fetchPattern] Could not fetch breathing pattern. Using default pattern.', error);
        // Fallback to a hardcoded default pattern if there's any error during fetch
        currentBreathingPattern = [
            { text: "Inhale", duration: 4, className: "expand" },
            { text: "Hold", duration: 4, className: "hold" },
            { text: "Exhale", duration: 6, className: "contract" },
            { text: "Hold", duration: 2, className: "hold" }
        ];
        instructionsDisplay.textContent = "Error loading pattern. Using default.";
    }
}

/**
 * Updates the overall session timer display (e.g., 00:00, 00:01, etc.).
 * Called every second by `timerInterval`.
 */
function updateTimer() {
    totalSeconds++;
    const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, '0');
    const seconds = String(totalSeconds % 60).padStart(2, '0');
    timerDisplay.textContent = `${minutes}:${seconds}`;
    // Uncomment for detailed logs of the overall timer:
    // console.log("[Overall Timer] Updated to:", timerDisplay.textContent);
}

/**
 * Manages a single step of the breathing cycle (e.g., Inhale 4 seconds).
 * This function handles updating instructions, playing audio, applying animations,
 * managing the numerical countdown in the circle, and scheduling the next step.
 */
function startBreathingCycle() {
    // Prevent starting a cycle if breathing is not active (e.g., after stopping)
    if (!isBreathingActive) {
        console.log("[startCycle] Breathing is not active. Stopping cycle initiation.");
        return;
    }

    // Clear any previous step-specific countdown interval to prevent multiple intervals running simultaneously
    if (stepCountdownInterval) {
        clearInterval(stepCountdownInterval);
    }

    // Get the current breathing step from the pattern
    const currentStep = currentBreathingPattern[patternIndex];
    
    // --- 1. Update Instruction Text ---
    instructionsDisplay.textContent = currentStep.text;
    console.log(`[startCycle] Instruction text set to: "${currentStep.text}" (Duration: ${currentStep.duration}s)`);

    // --- 2. Play Audio Cues ---
    // Use a try-catch block for audio playback as it can fail (e.g., autoplay restrictions)
    try {
        if (currentStep.text === "Inhale") {
            inhaleSound.currentTime = 0; // Reset audio to start from beginning
            inhaleSound.play().catch(e => console.error("[Audio] Error playing inhale sound:", e));
        } else if (currentStep.text === "Exhale") {
            exhaleSound.currentTime = 0;
            exhaleSound.play().catch(e => console.error("[Audio] Error playing exhale sound:", e));
        } else if (currentStep.text === "Hold") {
            holdSound.currentTime = 0;
            holdSound.play().catch(e => console.error("[Audio] Error playing hold sound:", e));
        }
        console.log(`[Audio] Attempted to play sound for: "${currentStep.text}"`);
    } catch (error) {
        console.error("[Audio] General audio playback error:", error);
    }

    // Adjust background music volume based on the current breathing phase
    if (backgroundMusic) {
        backgroundMusic.volume = 0.5; // Default volume for 'Hold' or others
        if (currentStep.text === "Inhale") {
            backgroundMusic.volume = 0.7; // Slightly louder during inhale
        } else if (currentStep.text === "Exhale") {
            backgroundMusic.volume = 0.3; // Softer during exhale
        }
    }

    // --- 3. Apply Animation Classes to the Breathing Circle ---
    // Remove all existing animation classes first to ensure a clean slate before applying the new one.
    // This is crucial for CSS transitions to re-trigger.
    breathingCircle.classList.remove('expand', 'contract', 'hold'); 
    console.log("[startCycle] Removed previous animation classes from breathingCircle.");

    // A small delay (e.g., 50ms) ensures the browser has time to register the class removal
    // before the new class is added. This allows the CSS transition to work smoothly.
    setTimeout(() => {
        breathingCircle.classList.add(currentStep.className);
        console.log(`[startCycle] Added class: "${currentStep.className}" to breathingCircle.`);
        console.log("[startCycle] Current breathingCircle classes:", breathingCircle.classList.value); // Verify current classes
    }, 50); 

    // --- 4. Manage Numerical Countdown Display Inside the Circle ---
    let currentStepTimer = currentStep.duration;
    // Display the initial duration immediately when the step starts
    breathingCircle.textContent = currentStepTimer; 
    console.log(`[Countdown] Circle countdown initialized to: ${currentStepTimer} for "${currentStep.text}"`);

    // Set up an interval to decrement and display the countdown inside the circle every second
    stepCountdownInterval = setInterval(() => {
        currentStepTimer--;
        console.log(`[Countdown] Step: "${currentStep.text}", Remaining: ${currentStepTimer}`);

        // Update the circle's text content with the current count.
        // Display 0 for the last second of the countdown.
        if (currentStepTimer >= 0) { 
            breathingCircle.textContent = currentStepTimer;
        } else {
            // Once the countdown goes below 0, stop this specific interval.
            // The text content will be updated by the next call to startBreathingCycle,
            // so no need to clear it here, which prevents a flicker.
            clearInterval(stepCountdownInterval);
        }
    }, 1000);

    // --- 5. Schedule the Next Breathing Cycle Step ---
    // Set a timeout that will trigger the next step after the current step's full duration.
    cycleTimeout = setTimeout(() => {
        clearInterval(stepCountdownInterval); // Ensure current step's numerical countdown stops
        patternIndex = (patternIndex + 1) % currentBreathingPattern.length; // Move to the next step in the pattern
        startBreathingCycle(); // Recursively call this function to start the next step
    }, currentStep.duration * 1000); // Convert duration from seconds to milliseconds
}

/**
 * Initiates the entire breathing exercise. Called when the "Start Breathing" button is clicked.
 */
async function startBreathing() {
    console.log("[startBreathing] 'Start Breathing' button clicked!");
    // Prevent starting if already active
    if (isBreathingActive) {
        console.log("[startBreathing] Breathing is already active. Ignoring this click.");
        return;
    }

    isBreathingActive = true; // Set flag to indicate breathing is active
    totalSeconds = 0; // Reset overall session timer
    patternIndex = 0; // Start from the beginning of the breathing pattern
    timerDisplay.textContent = "00:00"; // Reset overall timer display
    startButton.style.display = 'none'; // Hide the Start button
    stopButton.style.display = 'inline-block'; // Show the Stop button

    // Get the currently selected pattern from the dropdown and fetch its details from the backend.
    // The `await` keyword ensures this operation completes before moving on.
    const selectedPatternName = patternSelect.value;
    await fetchBreathingPattern(selectedPatternName); 

    // Start the overall session timer, updating `timerDisplay` every second.
    timerInterval = setInterval(updateTimer, 1000);
    console.log("[startBreathing] Overall session timer interval set.");

    // Start the very first breathing cycle step.
    startBreathingCycle();

    // Attempt to play background music. Browsers often block autoplay without user interaction,
    // so include a catch block to handle potential errors.
    if (backgroundMusic) {
        backgroundMusic.play().catch(error => {
            console.error("[Audio] Background music playback failed (likely autoplay blocked):", error);
            // You could display a message to the user here, e.g.,
            // instructionsDisplay.textContent = "Music blocked. Click anywhere to enable.";
        });
        backgroundMusic.volume = 0.5; // Set an initial volume for the background music
    }
}

/**
 * Stops the breathing exercise. Called when the "Stop Breathing" button is clicked.
 */
function stopBreathing() {
    console.log("[stopBreathing] 'Stop Breathing' button clicked!");
    // Prevent stopping if not active
    if (!isBreathingActive) {
        console.log("[stopBreathing] Breathing is not active. Ignoring this click.");
        return;
    }

    isBreathingActive = false; // Set flag to indicate breathing is no longer active
    clearTimeout(cycleTimeout); // Clear the timeout for the current breathing step
    clearInterval(timerInterval); // Stop the overall session timer
    clearInterval(stepCountdownInterval); // Stop the numerical countdown inside the circle
    console.log("[stopBreathing] All timers and intervals cleared.");
    
    // Reset visualizer elements to their initial state
    breathingCircle.className = 'breathing-circle'; // Remove all animation classes from the circle
    breathingCircle.textContent = ''; // Clear any numerical countdown displayed
    instructionsDisplay.textContent = "Click 'Start Breathing' to begin"; // Reset instructions
    
    // Toggle button visibility back to initial state
    startButton.style.display = 'inline-block'; // Show Start button
    stopButton.style.display = 'none'; // Hide Stop button

    // Pause and reset all audio elements to their starting positions
    try {
        if (backgroundMusic) {
            backgroundMusic.pause();
            backgroundMusic.currentTime = 0;
        }
        if (inhaleSound) {
            inhaleSound.pause();
            inhaleSound.currentTime = 0;
        }
        if (exhaleSound) {
            exhaleSound.pause();
            exhaleSound.currentTime = 0;
        }
        if (holdSound) {
            holdSound.pause();
            holdSound.currentTime = 0;
        }
        console.log("[Audio] All audio paused and reset.");
    } catch (error) {
        console.error("[Audio] Error pausing/resetting audio:", error);
    }
}

// Attach event listeners to the Start and Stop buttons
startButton.addEventListener('click', startBreathing);
stopButton.addEventListener('click', stopBreathing);

// Initial setup when the page loads to ensure correct display
breathingCircle.textContent = ''; // Ensure breathing circle is empty
timerDisplay.textContent = "00:00"; // Ensure overall timer shows 00:00
instructionsDisplay.textContent = "Click 'Start Breathing' to begin"; // Set initial instructions
