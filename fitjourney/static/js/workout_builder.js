// static/js/workout_builder.js

document.addEventListener('DOMContentLoaded', function() {
    const exerciseLibraryList = document.getElementById('exercise-library-list');
    const workoutSessionList = document.getElementById('workout-session-list');

    // --- CRITICAL DATA INITIALIZATION ---
    // Safely retrieve and parse the data from the window object.
    let libraryData = window.EXERCISE_LIBRARY_DATA || [];
    
    if (typeof libraryData === 'string') {
        try {
            libraryData = JSON.parse(libraryData);
        } catch (e) {
            console.error("Failed to parse EXERCISE_LIBRARY_DATA. Using empty array.", e);
            libraryData = [];
        }
    }
    // --- END DATA INITIALIZATION ---
    
    // --- Core Function: Render Initial Library ---
    function renderExerciseLibrary() {
        exerciseLibraryList.innerHTML = '';
        libraryData.forEach(exercise => {
            const listItem = document.createElement('li');
            listItem.classList.add('exercise-item');
            listItem.dataset.name = exercise.name;
            listItem.dataset.type = exercise.type;
            
            const buttonText = exercise.type === 'duration' ? 'Add (Time)' : 'Add (Reps)';
            
            listItem.innerHTML = `
                <div class="details">
                    <span>${exercise.name}</span>
                    <p style="font-size:0.85em; color:#888;">${exercise.type.replace('_', ' ').toUpperCase()}</p>
                </div>
                <button class="add-btn" 
                        onclick="window.addExerciseToSession('${exercise.name}', '${exercise.type}')">
                    <i class="fas fa-plus"></i> ${buttonText}
                </button>
            `;
            exerciseLibraryList.appendChild(listItem);
        });
    }
    // --- End Render Initial Library ---
    
    // Function to add an exercise to the workout session with dynamic inputs
    window.addExerciseToSession = function(exerciseName, exerciseType) {
        const listItem = document.createElement('li');
        listItem.classList.add('session-item');
        listItem.dataset.name = exerciseName; 
        listItem.dataset.type = exerciseType; 

        let detailsHtml = `<div class="handle"><i class="fas fa-grip-vertical"></i></div><div class="details"><span>${exerciseName}</span>`;

        if (exerciseType === "duration") {
            detailsHtml += `<label>Duration (min): <input type="number" class="duration-input" value="1" min="0.5" step="0.5"></label>`;
        } else if (exerciseType === "reps_sets") {
            detailsHtml += `
                <label>Sets: <input type="number" class="sets-input" value="3" min="1"></label>
                <label>Reps: <input type="number" class="reps-input" value="10" min="1"></label>
            `;
        }
        detailsHtml += `</div>`;

        listItem.innerHTML = `
            ${detailsHtml}
            <button class="remove-btn" onclick="removeExercise(this)"><i class="fas fa-trash"></i></button>
        `;
        workoutSessionList.appendChild(listItem);
    }
    
    // Initialize Sortable for the workout session (Allows dragging to reorder)
    new Sortable(workoutSessionList, {
        group: 'session', 
        animation: 150,
        handle: '.handle', 
        onEnd: function (evt) {
            console.log('Item reordered:', evt.item);
        }
    });

    // Function to remove an exercise from the workout session
    window.removeExercise = function(buttonElement) {
        buttonElement.closest('.session-item').remove();
    };

    // Helper function to get workout data from the session list
    function getWorkoutData() {
        const sessionItems = workoutSessionList.querySelectorAll('.session-item');
        const workoutData = [];

        sessionItems.forEach(item => {
            const name = item.dataset.name;
            const type = item.dataset.type;
            let exerciseEntry = { name: name, type: type };

            if (type === "duration") {
                const durationInput = item.querySelector('.duration-input');
                exerciseEntry.duration = durationInput ? parseFloat(durationInput.value) : null;
            } else if (type === "reps_sets") {
                const setsInput = item.querySelector('.sets-input');
                const repsInput = item.querySelector('.reps-input');
                exerciseEntry.sets = setsInput ? parseInt(setsInput.value) : null;
                exerciseEntry.reps = repsInput ? parseInt(repsInput.value) : null;
            }
            workoutData.push(exerciseEntry);
        });
        return workoutData;
    }

    // Function to save the workout
    window.saveWorkout = function() {
        const workoutData = getWorkoutData();
        console.log("Workout to save:", workoutData); 

        if (workoutData.length === 0) {
            alert('Please add exercises to your workout session before saving!');
            return;
        }

        fetch('/save_custom_workout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(workoutData),
        })
        .then(response => {
            if (!response.ok) {
                return response.text().then(text => { throw new Error(text) });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                alert('Workout saved successfully!');
            } else {
                alert('Error saving workout: ' + data.message);
            }
        })
        .catch((error) => {
            console.error('Error:', error);
            alert('An error occurred while saving the workout: ' + error.message);
        });
    };

    // Function to start the workout
    window.startWorkout = function() {
        const workoutData = getWorkoutData();

        if (workoutData.length === 0) {
            alert('Please add exercises to your workout session before starting!');
            return;
        }

        fetch('/start_custom_workout', { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(workoutData),
        })
        .then(response => {
            if (!response.ok) {
                return response.text().then(text => { throw new Error(text) });
            }
            return response.json();
        })
        .then(data => {
            if (data.success && data.redirect_url) {
                window.location.href = data.redirect_url;
            } else {
                alert('Error starting workout: ' + data.message);
            }
        })
        .catch((error) => {
            console.error('Error:', error);
            alert('An error occurred while trying to start the workout: ' + error.message);
        });
    };

    // Initial load
    renderExerciseLibrary();
});