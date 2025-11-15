// static/js/workout_player.js

document.addEventListener('DOMContentLoaded', function() {
    const currentExerciseNameEl = document.getElementById('current-exercise-name');
    const exerciseDetailsEl = document.getElementById('exercise-details');
    const timerDisplayEl = document.getElementById('timer-display');
    const prevExerciseBtn = document.getElementById('prev-exercise-btn');
    const togglePauseBtn = document.getElementById('toggle-pause-btn');
    const nextExerciseBtn = document.getElementById('next-exercise-btn');
    const finishWorkoutBtn = document.getElementById('finish-workout-btn');
    const upcomingExercisesListEl = document.getElementById('upcoming-exercises-list');

    let currentWorkout = workoutData; // This comes from Flask via the HTML script tag
    let currentExerciseIndex = 0;
    let timerInterval;
    let isPaused = true;
    let timeLeftInExercise = 0; // In seconds
    let totalWorkoutDuration = 0; // To track overall time if needed

    // Function to format time for display (MM:SS)
    function formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes < 10 ? '0' : ''}${minutes}:${remainingSeconds < 10 ? '0' : ''}${remainingSeconds}`;
    }

    // Function to update the timer display
    function updateTimerDisplay() {
        timerDisplayEl.textContent = formatTime(timeLeftInExercise);
    }

    // Function to start the timer
    function startTimer() {
        if (timerInterval) clearInterval(timerInterval); // Clear any existing timer
        isPaused = false;
        togglePauseBtn.innerHTML = '<i class="fas fa-pause"></i> Pause';

        timerInterval = setInterval(() => {
            if (!isPaused) {
                timeLeftInExercise--;
                updateTimerDisplay();

                if (timeLeftInExercise <= 0) {
                    clearInterval(timerInterval);
                    // Automatically move to next exercise for duration-based
                    if (currentExerciseIndex < currentWorkout.length - 1) {
                        currentExerciseIndex++;
                        loadCurrentExercise();
                    } else {
                        // Workout finished
                        finishWorkout();
                    }
                }
            }
        }, 1000); // Update every second
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

        const exercise = currentWorkout[currentExerciseIndex];
        currentExerciseNameEl.textContent = exercise.name;
        exerciseDetailsEl.innerHTML = ''; // Clear previous details

        if (exercise.type === 'duration') {
            exerciseDetailsEl.textContent = `Duration: ${exercise.duration} minutes`;
            timeLeftInExercise = exercise.duration * 60; // Convert minutes to seconds
            // If starting a duration exercise, automatically start timer
            if (!isPaused) { // Only start if not globally paused
                startTimer();
            } else {
                updateTimerDisplay(); // Just update display if paused
            }

        } else if (exercise.type === 'reps_sets') {
            exerciseDetailsEl.textContent = `Sets: ${exercise.sets}, Reps: ${exercise.reps}`;
            // For reps/sets, timer will count up or be controlled manually
            timeLeftInExercise = 0; // Reset for reps/sets
            pauseTimer(); // Reps/sets are typically self-paced, so start paused
            timerDisplayEl.textContent = '00:00'; // Reset timer display
        }

        updateTimerDisplay(); // Ensure timer display is correct immediately
        updateNavigationButtons();
        renderUpcomingExercises();
    }

    // Function to update navigation button states
    function updateNavigationButtons() {
        prevExerciseBtn.disabled = currentExerciseIndex === 0;
        nextExerciseBtn.disabled = currentExerciseIndex >= currentWorkout.length - 1;
        if (currentExerciseIndex >= currentWorkout.length -1) {
            nextExerciseBtn.style.display = 'none'; // Hide next if it's the last exercise
            finishWorkoutBtn.style.display = 'inline-block'; // Show finish button
        } else {
            nextExerciseBtn.style.display = 'inline-block';
            finishWorkoutBtn.style.display = 'none';
        }
    }

    // Function to render upcoming exercises
    function renderUpcomingExercises() {
        upcomingExercisesListEl.innerHTML = ''; // Clear current list
        for (let i = currentExerciseIndex + 1; i < currentWorkout.length; i++) {
            const exercise = currentWorkout[i];
            const listItem = document.createElement('li');
            listItem.textContent = `${exercise.name} (${exercise.type === 'duration' ? exercise.duration + ' min' : exercise.sets + ' sets x ' + exercise.reps + ' reps'})`;
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
            pauseTimer(); // Pause when moving back/forward
        }
    });

    togglePauseBtn.addEventListener('click', () => {
        if (isPaused) {
            startTimer();
        } else {
            pauseTimer();
        }
    });

    nextExerciseBtn.addEventListener('click', () => {
        if (currentExerciseIndex < currentWorkout.length - 1) {
            currentExerciseIndex++;
            loadCurrentExercise();
            pauseTimer(); // Pause when moving back/forward
        } else {
            // This case should be handled by finishWorkoutBtn, but as a fallback
            finishWorkout();
        }
    });

    finishWorkoutBtn.addEventListener('click', finishWorkout);

    // Function to handle workout completion
    function finishWorkout() {
        clearInterval(timerInterval);
        alert('Workout Finished! Great job!');
        // Optionally redirect to a summary page or home
        window.location.href = '/dashboard'; // Or wherever you want to send them
    }

    // Initial load
    if (currentWorkout && currentWorkout.length > 0) {
        // Automatically start the first exercise's timer if it's duration-based
        isPaused = false; // Set to false to auto-start if duration-based
        loadCurrentExercise();
    } else {
        currentExerciseNameEl.textContent = "No workout loaded.";
        exerciseDetailsEl.textContent = "Please build a workout first.";
        timerDisplayEl.textContent = "00:00";
        prevExerciseBtn.disabled = true;
        togglePauseBtn.disabled = true;
        nextExerciseBtn.disabled = true;
        finishWorkoutBtn.disabled = true;
    }
});