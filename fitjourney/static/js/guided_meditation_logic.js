        // Use an array of objects to store scripts and their estimated durations
        const MEDITATION_SCRIPTS = {
            "focus": [
                 { text: "Welcome to this focus meditation. Find a quiet space where you won't be disturbed.", duration: 6 },
        { text: "Settle into a comfortable position, whether sitting upright or lying down. Allow your body to feel supported by whatever is beneath you.", duration: 9 },
        { text: "Gently close your eyes, or if you prefer, soften your gaze to a single, unmoving point in front of you.", duration: 8 },
        { text: "Take a deep breath in through your nose, filling your lungs completely.", duration: 6 },
        { text: "And slowly exhale through your mouth, letting go of any tension you might be holding.", duration: 7 },
        { text: "Repeat this gentle breathing for a few more cycles, noticing the natural rhythm of your breath.", duration: 8 },
        { text: "Now, bring your full attention to the sensation of your breath. Feel the air as it enters your nostrils, travels down, and fills your belly.", duration: 10 },
        { text: "Notice the subtle pause, and then the gentle release as the air leaves your body.", duration: 8 },
        { text: "Your breath is an anchor. Whenever your mind begins to wander, gently bring your awareness back to this simple, natural process.", duration: 10 },
        { text: "Thoughts will inevitably arise. Acknowledge them without judgment, as if they are clouds passing in the sky.", duration: 9 },
        { text: "Then, redirect your focus back to the rise and fall of your abdomen, or the sensation of air at your nostrils.", duration: 10 },
        { text: "Stay with this focused attention for the next few moments, simply breathing, simply being.", duration: 8 },
        { text: "Allow yourself to become fully present with each inhale and exhale.", duration: 7 },
        { text: "You are exactly where you need to be, doing exactly what you need to do.", duration: 7 },
        { text: "As this meditation comes to a close, slowly begin to bring your awareness back to your body.", duration: 9 },
        { text: "Notice the sounds around you, the feeling of the air on your skin.", duration: 7 },
        { text: "When you are ready, gently open your eyes, carrying this sense of calm focus with you into your day.", duration: 10 }
            ],
            "sleep": [
               { text: "Welcome to this sleep meditation. Prepare your space for rest.", duration: 5 },
        { text: "Lie down comfortably on your back, allowing your arms and legs to extend naturally.", duration: 8 },
        { text: "Feel the entire length of your body sinking into the support of your bed or surface.", duration: 8 },
        { text: "Close your eyes softly, and begin to deepen your breath.", duration: 6 },
        { text: "Inhale slowly and deeply through your nose, drawing peace into every cell.", duration: 8 },
        { text: "Exhale fully through your mouth, releasing all tension, all thoughts of the day.", duration: 9 },
        { text: "Continue this rhythmic breathing, feeling your body grow heavier and more relaxed with each exhale.", duration: 10 },
        { text: "Bring your awareness to your feet. Feel them relax. Let all tension drain away.", duration: 7 },
        { text: "Move up to your calves and thighs. Allow them to soften, becoming heavy.", duration: 7 },
        { text: "Relax your hips and lower back, letting go of any discomfort.", duration: 6 },
        { text: "Soften your belly and your chest. Feel the gentle rise and fall of your breath.", duration: 8 },
        { text: "Relax your shoulders, arms, and hands. Let them melt into the surface.", duration: 7 },
        { text: "Ease the tension in your neck and jaw. Let your tongue rest in your mouth.", duration: 7 },
        { text: "Soften your facial muscles, your forehead, your eyelids.", duration: 6 },
        { text: "Imagine a warm, comforting wave washing over your entire body, from head to toe.", duration: 9 },
        { text: "Allow this wave to carry away any remaining tension, any lingering thoughts.", duration: 8 },
        { text: "You are safe, you are warm, you are ready for deep, restorative sleep.", duration: 8 },
        { text: "Drift gently, effortlessly, into a peaceful and restful slumber.", duration: 8 }
            ],
            "relaxation": [
                { text: "Welcome to this relaxation meditation. Take a moment to settle in.", duration: 6 },
        { text: "Find a posture that feels comfortable and supportive for you, whether sitting or lying down.", duration: 8 },
        { text: "Allow your hands to rest gently, perhaps palms up or down, whatever feels natural.", duration: 7 },
        { text: "Begin to tune into your breath. Notice its natural flow without trying to change it.", duration: 8 },
        { text: "Feel the gentle expansion as you inhale, and the soft release as you exhale.", duration: 7 },
        { text: "With each breath, imagine yourself softening, letting go a little more.", duration: 8 },
        { text: "Now, bring your awareness to your feet. Feel the ground beneath them, supporting you.", duration: 8 },
        { text: "Allow your feet to completely relax. Let go of any tightness.", duration: 7 },
        { text: "Move your attention up to your legs. Feel them becoming heavy and calm.", duration: 7 },
        { text: "Relax your hips and pelvic area. Release any gripping or tension here.", duration: 7 },
        { text: "Softly move your awareness into your abdomen. Let your belly be soft and receptive to your breath.", duration: 9 },
        { text: "Relax your chest and heart space. Feel a sense of openness and ease.", duration: 8 },
        { text: "Let your shoulders drop away from your ears. Release any burdens you might be carrying.", duration: 9 },
        { text: "Allow your arms and hands to become heavy and still. Notice the tingling sensations.", duration: 8 },
        { text: "Relax your neck and throat. Let your jaw soften, and your tongue rest gently.", duration: 8 },
        { text: "Finally, bring awareness to your face. Smooth your forehead, relax your eyebrows, and soften your eyes.", duration: 9 },
        { text: "Feel your entire body completely relaxed, yet alert and present.", duration: 8 },
        { text: "Rest in this state of deep relaxation for a few more breaths.", duration: 7 },
        { text: "When you are ready, gently wiggle your fingers and toes, and slowly bring your awareness back to your surroundings, feeling refreshed and peaceful.", duration: 12 }
            ]
        };

        const scriptDisplay = document.getElementById('scriptDisplay');
        const startButton = document.getElementById('startButton');
        const stopButton = document.getElementById('stopButton');
        const meditationTypeSelect = document.getElementById('meditationTypeSelect');
        const enableVoiceCheckbox = document.getElementById('enableVoice');
        const meditationTimer = document.getElementById('meditationTimer');

        let currentScript = [];
        let scriptIndex = 0;
        let speechSynthesis = window.speechSynthesis;
        let utterance = null;
        let timerInterval = null;
        let secondsElapsed = 0;
        let isSpeaking = false; // Flag to track if speech is active

        // Function to update the timer display
        function updateTimer() {
            secondsElapsed++;
            const minutes = String(Math.floor(secondsElapsed / 60)).padStart(2, '0');
            const seconds = String(secondsElapsed % 60).padStart(2, '0');
            meditationTimer.textContent = `${minutes}:${seconds}`;
        }

        // Function to speak a line
        function speak(text) {
            if (!speechSynthesis) {
                console.warn("SpeechSynthesis API not supported in this browser.");
                return;
            }
            if (speechSynthesis.speaking) {
                speechSynthesis.cancel(); // Stop current speech if any
            }
            utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'en-US'; // You can change this
            // You can set voice, pitch, rate here if needed
            
            utterance.onstart = () => { isSpeaking = true; };
            utterance.onend = () => { isSpeaking = false; nextLine(); };
            utterance.onerror = (event) => {
                console.error("SpeechSynthesisUtterance.onerror", event);
                isSpeaking = false; // Ensure flag is reset on error
                nextLine(); // Attempt to move to next line even on error
            };
            speechSynthesis.speak(utterance);
        }

        // Function to display and speak the next line
        function nextLine() {
            if (scriptIndex < currentScript.length) {
                // Clear previous line highlighting
                const previousLineElement = document.querySelector('.current-line');
                if (previousLineElement) {
                    previousLineElement.classList.remove('current-line');
                }

                const lineData = currentScript[scriptIndex];
                const p = document.createElement('p');
                p.textContent = lineData.text;
                p.classList.add('current-line'); // Add class for highlighting
                scriptDisplay.innerHTML = ''; // Clear previous text
                scriptDisplay.appendChild(p);

                if (enableVoiceCheckbox.checked) {
                    speak(lineData.text);
                } else {
                    // If no voice, wait for the estimated duration
                    setTimeout(nextLine, lineData.duration * 1000);
                }
                scriptIndex++;
            } else {
                // Meditation complete
                scriptDisplay.innerHTML = '<p>Meditation session complete! 🙏</p>';
                stopMeditation(); // Call stop to clean up
            }
        }

        // Function to start meditation
        function startMeditation() {
            const selectedType = meditationTypeSelect.value;
            currentScript = MEDITATION_SCRIPTS[selectedType];
            scriptIndex = 0;
            secondsElapsed = 0;
            meditationTimer.textContent = '00:00';
            
            startButton.style.display = 'none';
            stopButton.style.display = 'block';
            meditationTypeSelect.disabled = true;
            enableVoiceCheckbox.disabled = true;

            timerInterval = setInterval(updateTimer, 1000); // Start timer

            nextLine(); // Start the first line
        }

        // Function to stop meditation
        function stopMeditation() {
            if (speechSynthesis && speechSynthesis.speaking) {
                speechSynthesis.cancel(); // Stop any ongoing speech
            }
            clearInterval(timerInterval); // Stop the timer
            timerInterval = null; // Clear the timer ID
            isSpeaking = false; // Reset speech flag

            startButton.style.display = 'block';
            stopButton.style.display = 'none';
            meditationTypeSelect.disabled = false;
            enableVoiceCheckbox.disabled = false;
            scriptDisplay.innerHTML = '<p>Meditation stopped. Click Start to resume or choose another type.</p>';
            scriptIndex = 0; // Reset script progress
            currentScript = []; // Clear current script
        }

        // Event Listeners
        startButton.addEventListener('click', startMeditation);
        stopButton.addEventListener('click', stopMeditation);
        // Reset state if meditation type changes before starting
        meditationTypeSelect.addEventListener('change', stopMeditation); 
