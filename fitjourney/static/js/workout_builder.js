// static/js/workout_builder.js

document.addEventListener('DOMContentLoaded', function() {
    const exerciseLibraryList = document.getElementById('exercise-library-list');
    const workoutSessionList = document.getElementById('workout-session-list');

    // Initialize Sortable for the exercise library (source)
    new Sortable(exerciseLibraryList, {
        group: {
            name: 'shared',
            pull: 'clone', // Allows cloning items from here
            put: false // Does not allow items to be dropped into here
        },
        animation: 150,
        sort: false, // Items in the library shouldn't be reordered
        forceFallback: true, // Needed for drag and drop to work reliably across different list types
        onEnd: function (evt) {
            // This function runs when dragging from the library stops
            // If the item was dragged *out* of the library (to session list)
            if (evt.to === workoutSessionList) {
                const originalItem = evt.item; // The cloned item in the target list
                const exerciseName = originalItem.dataset.name;
                const exerciseType = originalItem.dataset.type;

                // Remove the cloned item initially placed by SortableJS
                originalItem.remove();

                // Call our custom function to create the session item with inputs
                addExerciseToSession(exerciseName, exerciseType);
            }
        }
    });

    // Initialize Sortable for the workout session (target and sortable)
    new Sortable(workoutSessionList, {
        group: 'shared', // Allows items from the 'shared' group to be put here
        animation: 150,
        handle: '.handle', // Drag handle for reordering within the session
        onEnd: function (evt) {
            // This event fires when an item is dropped, useful for reordering feedback
            console.log('Item moved or added to session list:', evt.item);
        }
    });

    // Function to add an exercise to the workout session with dynamic inputs
    function addExerciseToSession(exerciseName, exerciseType) {
        const listItem = document.createElement('li');
        listItem.classList.add('session-item');
        listItem.dataset.name = exerciseName; // Store name
        listItem.dataset.type = exerciseType; // Store type

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
            <button class="remove-btn" onclick="removeExercise(this)">Remove</button>
        `;
        workoutSessionList.appendChild(listItem);
    }

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

    // Function to save the workout (existing functionality)
    window.saveWorkout = function() {
        const workoutData = getWorkoutData();
        console.log("Workout to save:", workoutData); // For debugging

        fetch('/save_custom_workout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
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

    // New function to start the workout
    window.startWorkout = function() {
        const workoutData = getWorkoutData();

        if (workoutData.length === 0) {
            alert('Please add exercises to your workout session before starting!');
            return;
        }

        console.log("Workout to start:", workoutData); // For debugging

        fetch('/start_custom_workout', { // New endpoint for starting
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
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
                // Redirect to the workout player page
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
});