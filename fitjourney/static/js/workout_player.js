// static/js/workout_player.js

document.addEventListener('DOMContentLoaded', function() {
    // --- Data Initialization Change ---
    // Safely retrieve the JSON string from the window object (defined in start_workout.html) and parse it.
    const workoutDataString = window.WORKOUT_DATA_JSON || '[]';
    
    // The main workout object is initialized here, guaranteeing it's an array.
    let currentWorkout;
    try {
        // Use a try-catch block for JSON parsing for maximum robustness
        currentWorkout = JSON.parse(workoutDataString);
    } catch (e) {
        console.error("Error parsing workout data:", e);
        currentWorkout = [];
    }
    // --- End Data Initialization Change ---

    const currentExerciseNameEl = document.getElementById('current-exercise-name');
    const exerciseDetailsEl = document.getElementById('exercise-details');
    const timerDisplayEl = document.getElementById('timer-display');
    const prevExerciseBtn = document.getElementById('prev-exercise-btn');
    const togglePauseBtn = document.getElementById('toggle-pause-btn');
    const nextExerciseBtn = document.getElementById('next-exercise-btn');
    const finishWorkoutBtn = document.getElementById('finish-workout-btn');
    const upcomingExercisesListEl = document.getElementById('upcoming-exercises-list');

    let currentExerciseIndex = 0;
    let timerInterval;
    let isPaused = true;
    let timeTrackingDirection = 'down'; 
    
    // Reps/Sets tracking state
    let currentSet = 1;
    let targetSets = 0;
    let targetReps = 0;

    // Timer state for Reps/Sets (counts total time taken for the current exercise)
    let repsSetsTimeElapsed = 0; 

    // Function to format time for display (MM:SS)
    function formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes < 10 ? '0' : ''}${minutes}:${remainingSeconds < 10 ? '0' : ''}${remainingSeconds}`;
    }

    // Function to update the timer display
    function updateTimerDisplay(seconds) {
        timerDisplayEl.textContent = formatTime(seconds);
    }

    // Function to start the timer (handles both count-up and count-down)
    function startTimer() {
        if (timerInterval) clearInterval(timerInterval);
        isPaused = false;
        togglePauseBtn.innerHTML = '<i class="fas fa-pause"></i> Pause';

        if (timeTrackingDirection === 'down') {
            // Duration logic (Count Down)
            let timeLeftInExercise = currentWorkout[currentExerciseIndex].duration * 60;
            
            timerInterval = setInterval(() => {
                if (!isPaused) {
                    timeLeftInExercise--;
                    updateTimerDisplay(timeLeftInExercise);

                    if (timeLeftInExercise <= 0) {
                        clearInterval(timerInterval);
                        moveNextExercise();
                    }
                }
            }, 1000); 

        } else if (timeTrackingDirection === 'up') {
            // Reps/Sets logic (Count Up)
            
            timerInterval = setInterval(() => {
                if (!isPaused) {
                    repsSetsTimeElapsed++;
                    updateTimerDisplay(repsSetsTimeElapsed);
                }
            }, 1000); 
        }
    }

    // Function to pause the timer
    function pauseTimer() {
        isPaused = true;
        togglePauseBtn.innerHTML = '<i class="fas fa-play"></i> Resume';
        clearInterval(timerInterval);
    }

    // Function to load and display the current exercise
    function loadCurrentExercise() {
        if (currentExerciseIndex >= currentWorkout.length) {
            finishWorkout();
            return;
        }
        
        // Reset exercise-specific timers/states
        pauseTimer();
        repsSetsTimeElapsed = 0;
        updateTimerDisplay(0);

        const exercise = currentWorkout[currentExerciseIndex];
        currentExerciseNameEl.textContent = exercise.name;
        exerciseDetailsEl.innerHTML = '';
        
        // Duration-based Logic
        if (exercise.type === 'duration') {
            timeTrackingDirection = 'down';
            exerciseDetailsEl.textContent = `Duration: ${exercise.duration} minutes`;
            
            // Auto-start duration exercises
            isPaused = false; 
            startTimer(); 

        // Reps/Sets-based Logic (Count-up timer, Manual set completion)
        } else if (exercise.type === 'reps_sets') {
            timeTrackingDirection = 'up';
            targetSets = exercise.sets;
            targetReps = exercise.reps;
            currentSet = 1;
            
            // Display initial set/rep data and update button
            updateRepsSetsDisplay(); 
            
            // Start the count-up timer immediately
            isPaused = false;
            startTimer(); 
        }

        updateNavigationButtons();
        renderUpcomingExercises();
    }

    // Function to update display for reps/sets exercises
    function updateRepsSetsDisplay() {
        if (timeTrackingDirection === 'up') {
            // MODIFIED DISPLAY LOGIC TO EMPHASIZE GOAL 
            exerciseDetailsEl.innerHTML = `
                <div style="font-size: 1.4em; font-weight: bold; color: #007bff; margin-bottom: 10px;">
                    GOAL: ${targetSets} Sets Total
                </div>
                <div style="font-size: 1.2em; color: #555; margin-bottom: 5px;">
                    Current Set: <span style="font-weight: bold; color: #dc3545;">${currentSet}</span>
                </div>
                <div>Target Reps: ${targetReps}</div>
            `;
            
            // Change Next button function and text
            nextExerciseBtn.innerHTML = '<i class="fas fa-check"></i> Complete Set';
            nextExerciseBtn.onclick = completeSet;
            
        } else {
             // Revert Next button function and text for duration/last set state
            nextExerciseBtn.innerHTML = 'Next <i class="fas fa-forward"></i>';
            nextExerciseBtn.onclick = moveNextExercise;
        }
    }

    // Function to handle set completion
    function completeSet() {
        // Optional: Could send set completion time to a backend endpoint here
        console.log(`Set ${currentSet} completed in ${formatTime(repsSetsTimeElapsed)}.`);
        
        if (currentSet < targetSets) {
            currentSet++;
            repsSetsTimeElapsed = 0; // Reset timer for the new set
            updateRepsSetsDisplay();
            startTimer(); // Restart timer for the new set
        } else {
            // All sets complete, move to the next exercise
            moveNextExercise();
        }
    }
    
    // Centralized function to move to the next exercise
    function moveNextExercise() {
        currentExerciseIndex++;
        if (currentExerciseIndex < currentWorkout.length) {
            loadCurrentExercise();
        } else {
            finishWorkout();
        }
    }


    // Function to update navigation button states
    function updateNavigationButtons() {
        prevExerciseBtn.disabled = currentExerciseIndex === 0;
        
        const isLastExercise = currentExerciseIndex >= currentWorkout.length - 1;

        if (isLastExercise) {
            nextExerciseBtn.style.display = 'none'; 
            finishWorkoutBtn.style.display = 'inline-flex';
        } else {
            nextExerciseBtn.style.display = 'inline-flex';
            finishWorkoutBtn.style.display = 'none';
        }
        
        // Ensure the pause button is always set correctly on load
        if (isPaused) {
            togglePauseBtn.innerHTML = '<i class="fas fa-play"></i> Resume';
        } else {
            togglePauseBtn.innerHTML = '<i class="fas fa-pause"></i> Pause';
        }
        
        togglePauseBtn.disabled = false;
    }

    // Function to render upcoming exercises
    function renderUpcomingExercises() {
        upcomingExercisesListEl.innerHTML = '';
        for (let i = currentExerciseIndex + 1; i < currentWorkout.length; i++) {
            const exercise = currentWorkout[i];
            const detailText = exercise.type === 'duration' 
                ? exercise.duration + ' min' 
                : exercise.sets + ' sets x ' + exercise.reps + ' reps';
                
            const listItem = document.createElement('li');
            listItem.textContent = `${exercise.name} (${detailText})`;
            upcomingExercisesListEl.appendChild(listItem);
        }
        if (upcomingExercisesListEl.children.length === 0) {
            upcomingExercisesListEl.innerHTML = '<li>No more exercises.</li>';
        }
    }

    // Event Listeners
    prevExerciseBtn.addEventListener('click', () => {
        if (currentExerciseIndex > 0) {
            currentExerciseIndex--;
            loadCurrentExercise();
        }
    });
    
    // Toggle pause uses the central pauseTimer/startTimer functions
    togglePauseBtn.addEventListener('click', () => {
        if (isPaused) {
            startTimer();
        } else {
            pauseTimer();
        }
    });

    // The 'Next' button's behavior is now set dynamically in updateRepsSetsDisplay()

    finishWorkoutBtn.addEventListener('click', finishWorkout);

    // Function to handle workout completion
    function finishWorkout() {
        clearInterval(timerInterval);
        alert('Workout Finished! Great job!');
        window.location.href = '/dashboard';
    }

    // Initial load
    if (currentWorkout && currentWorkout.length > 0) {
        loadCurrentExercise();
    } else {
        currentExerciseNameEl.textContent = "No workout loaded.";
        exerciseDetailsEl.textContent = "Please build a workout first.";
        updateTimerDisplay(0);
        prevExerciseBtn.disabled = true;
        togglePauseBtn.disabled = true;
        nextExerciseBtn.disabled = true;
        finishWorkoutBtn.disabled = true;
    }
});