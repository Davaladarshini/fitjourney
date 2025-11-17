from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
from breathing_patterns import breathing_bp
import cv2
import mediapipe as mp
import numpy as np
import collections
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import os
from openai import OpenAI 
from dotenv import load_dotenv; load_dotenv()
import json
from time import time

# --- NEW MODULAR IMPORTS ---
# NOTE: We assume you have saved the four Python files in the same directory.
import body_weight_squat_ohp
import alternate_lunges_rotation
import body_weight_squats
import jumping_jack
# The original line 'from webcam_stream import generate_frames, TARGET_POSE_DATA, LATEST_FEEDBACK' 
# is removed because we now get data from the modular files.
from webcam_stream import get_target_pose_data, LATEST_FEEDBACK
from textblob import TextBlob
from adaptive_plans import adaptive_bp
# --- Central Dispatcher Setup ---
# Maps the URL exercise key to the specific generator and state dictionary
EXERCISE_DISPATCHER = {
    'body_weight_squat_ohp': {
        'generator': body_weight_squat_ohp.generate_frames_squat_ohp,
        'feedback_state': body_weight_squat_ohp.LATEST_FEEDBACK,
        'target_data': body_weight_squat_ohp.TARGET_DATA # New: Get configuration from file
    },
    'alternate_lunges_rotation': {
        'generator': alternate_lunges_rotation.generate_frames_lunge_rotation,
        'feedback_state': alternate_lunges_rotation.LATEST_FEEDBACK,
        'target_data': alternate_lunges_rotation.TARGET_DATA # New: Get configuration from file
    },
    'body_weight_squats': {
        'generator': body_weight_squats.generate_frames_squats, 
        'feedback_state': body_weight_squats.LATEST_FEEDBACK_SQUATS,
        'target_data': body_weight_squats.TARGET_DATA # New: Get configuration from file
    },
    'jumping_jack': {
        'generator': jumping_jack.generate_frames_jumping_jack,
        'feedback_state': jumping_jack.LATEST_FEEDBACK_JUMPING_JACK,
        'target_data': jumping_jack.TARGET_DATA # New: Get configuration from file
    }
} 

# Replace the old loop logic (lines 49-62 in app.py) with the following:

ALL_EXERCISES = {}
for key, data in EXERCISE_DISPATCHER.items():
    target_data = data['target_data']
    
    # 1. Determine the representative target angle for display
    angle = 0.0
    thresholds = target_data.get('angle_thresholds', {})
    
    if key in ['body_weight_squat_ohp', 'body_weight_squats']:
        # Use knee_down for squat-type exercises
        angle = thresholds.get('knee_down', 0)
    elif key == 'alternate_lunges_rotation':
        # Use front_knee_down for lunges
        angle = thresholds.get('front_knee_down', 0)
    elif key == 'jumping_jack':
        # Use arm_open for jumping jacks
        angle = thresholds.get('arm_open', 0)
    
    # 2. Determine the display feedback text
    # Use the old 'feedback' key if available, otherwise use a generic message suitable for multi-angle tracking.
    feedback_text = target_data.get('feedback', "Multi-criteria analysis: Depth, Hips & Posture.")

    ALL_EXERCISES[key] = {
        'target_angle': angle,
        'feedback': feedback_text
    }

app = Flask(__name__)

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)

app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24).hex())
app.register_blueprint(breathing_bp)
app.register_blueprint(adaptive_bp)

# MongoDB Connection
client = MongoClient(os.getenv('MONGO_URI', "mongodb://localhost:27017/"))
db = client["user_db"]
users_collection = db["users"]
profile_collection = db['profiles']
mood_entries_collection = db["mood_entries"]
workout_plans_collection = db["workout_plans"]
custom_workouts_collection = db["custom_workouts"]

# --- Initialize the OpenAI client ---
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

exercise_data = {
    "Squat": {"rep_count": 0, "stage": None},
    "Push-up": {"rep_count": 0, "stage": None},
    "Lunge": {"rep_count": 0, "stage": None},
    "Jumping Jack": {"rep_count": 0, "stage": None},
    "Sit-up": {"rep_count": 0, "stage": None},
}

exercise_lock_buffer = collections.deque(maxlen=15)
lock_threshold = 10

active_exercise = None
last_switch_time = 0
switch_cooldown = 2  # seconds cooldown before switching
no_motion_counter = 0
NO_MOTION_LIMIT = 25

current_exercise = "Unknown"
feedback_text = ""

def calculate_angle(a, b, c):
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians*180.0/np.pi)
    if angle > 180.0:
        angle = 360 - angle
    return angle

def extract_angles(landmarks):
    left_knee = calculate_angle(
        [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y],
        [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x, landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y],
        [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x, landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
    )
    right_knee = calculate_angle(
        [landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y],
        [landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].y],
        [landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y]
    )
    left_elbow = calculate_angle(
        [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y],
        [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x, landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y],
        [landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x, landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y]
    )
    right_elbow = calculate_angle(
        [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y],
        [landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y],
        [landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].y]
    )
    left_hip = calculate_angle(
        [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y],
        [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y],
        [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x, landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
    )
    left_shoulder = calculate_angle(
        [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x, landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y],
        [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y],
        [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]
    )
    return left_knee, right_knee, left_elbow, right_elbow, left_hip, left_shoulder

def robust_classification(angles):
    left_knee, right_knee, left_elbow, right_elbow, left_hip, left_shoulder = angles
    avg_knee_angle = (left_knee + right_knee)/2
    avg_elbow_angle = (left_elbow + right_elbow)/2
    
    detected = "Unknown"
    arms_wide = left_shoulder > 90 and left_elbow > 150 and right_elbow > 150
    legs_wide = avg_knee_angle > 160

    if avg_knee_angle < 100 and 70 < left_hip < 140:
        detected = "Squat"
    elif avg_elbow_angle < 100 and avg_knee_angle > 150:
        detected = "Push-up"
    elif left_hip < 100 and avg_knee_angle < 140:
        detected = "Lunge"
    elif arms_wide and legs_wide:
        detected = "Jumping Jack"
    elif left_hip < 90 and avg_knee_angle < 90:
        detected = "Sit-up"

    return detected

def update_active_exercise():
    global active_exercise, last_switch_time
    now = time()
    if len(exercise_lock_buffer) == 0:
        return
    common_exercise = max(set(exercise_lock_buffer), key=exercise_lock_buffer.count)
    if common_exercise == "Unknown":
        return
    if common_exercise != active_exercise:
        if (now - last_switch_time) > switch_cooldown and exercise_lock_buffer.count(common_exercise) >= lock_threshold:
            active_exercise = common_exercise
            last_switch_time = now

def classify_and_count(angles):
    global current_exercise, feedback_text, active_exercise, no_motion_counter

    detected = robust_classification(angles)
    exercise_lock_buffer.append(detected)
    update_active_exercise()

    if active_exercise is None:
        current_exercise = "Detecting..."
        feedback_text = "Start exercising to lock the exercise."
        return

    current_exercise = active_exercise
    data = exercise_data.get(active_exercise)

    rep_this_frame = False

    left_knee, right_knee, left_elbow, right_elbow, left_hip, left_shoulder = angles
    avg_knee_angle = (left_knee + right_knee) / 2
    avg_elbow_angle = (left_elbow + right_elbow) / 2
    arms_wide = left_shoulder > 90 and left_elbow > 150 and right_elbow > 150
    legs_wide = avg_knee_angle > 160

    if active_exercise == "Jumping Jack":
        if arms_wide and legs_wide:
            if data.get("stage") != "up":
                data["stage"] = "up"
        elif not arms_wide and not legs_wide:
            if data.get("stage") == "up":
                data["stage"] = "down"
                data["rep_count"] += 1
                rep_this_frame = True
                feedback_text = f"Good jumping jack! Reps: {data['rep_count']}"
        else:
            feedback_text = "Keep moving for jumping jack"
    elif active_exercise == "Squat":
        if avg_knee_angle > 160:
            data["stage"] = "up"
        if avg_knee_angle < 90 and data.get("stage") == "up":
            data["stage"] = "down"
            data["rep_count"] += 1
            rep_this_frame = True
            feedback_text = f"Good squat! Reps: {data['rep_count']}"
        elif 90 <= avg_knee_angle <= 160:
            feedback_text = "Go deeper for better form!"
    elif active_exercise == "Push-up":
        if avg_elbow_angle > 160:
            data["stage"] = "up"
        if avg_elbow_angle < 90 and data.get("stage") == "up":
            data["stage"] = "down"
            data["rep_count"] += 1
            rep_this_frame = True
            feedback_text = f"Good push-up! Reps: {data['rep_count']}"
        elif 90 <= avg_elbow_angle <= 160:
            feedback_text = "Keep going!"
    elif active_exercise == "Lunge":
        if left_hip > 160:
            data["stage"] = "up"
        if left_hip < 90 and data.get("stage") == "up":
            data["stage"] = "down"
            data["rep_count"] += 1
            rep_this_frame = True
            feedback_text = f"Good lunge! Reps: {data['rep_count']}"
        elif 90 <= left_hip <= 160:
            feedback_text = "Lower your hips more!"
    elif active_exercise == "Sit-up":
        if left_hip > 160:
            data["stage"] = "up"
        if left_hip < 90 and data.get("stage") == "up":
            data["stage"] = "down"
            data["rep_count"] += 1
            rep_this_frame = True
            feedback_text = f"Good sit-up! Reps: {data['rep_count']}"
        elif 90 <= left_hip <= 160:
            feedback_text = "Keep pushing!"
    else:
        feedback_text = "Exercise not recognized"

    if rep_this_frame:
        no_motion_counter = 0
    else:
        no_motion_counter += 1
        if no_motion_counter >= NO_MOTION_LIMIT:
            active_exercise = None
            exercise_lock_buffer.clear()
            no_motion_counter = 0
            feedback_text = "No reps detected. Unlocking exercise..."

frame_skip = 0
def generate_frames():
    global current_exercise, feedback_text, frame_skip
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_skip += 1
        if frame_skip % 2 == 0:
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(img_rgb)

            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
                angles = extract_angles(landmarks)
                classify_and_count(angles)

        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')



@app.route('/exercise_info')
def exercise_info():
    return jsonify({
        "current_exercise": current_exercise,
        "rep_counts": {ex: data['rep_count'] for ex, data in exercise_data.items()},
        "feedback": feedback_text,
        "active_exercise": active_exercise,
    })

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login2', methods=['GET', 'POST'])
def login2():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        return f"Email: {email}, Password: {password}"
    return render_template('Login2.html')

@app.route('/workouts')
def workouts():
    user_name = session.get('user_name', 'Guest')
    return render_template('workouts.html', name=user_name)

@app.route('/workout_options')
def workout_options():
    return render_template('workout_options.html')

# --- MODIFIED: Yoga routes ---
@app.route('/yoga_workouts')
def yoga_workouts():
    options = [
        {"title": "Repetition Counter", "description": "Tracks how many rounds you complete for Sun Salutations and other repeated poses.", "link": url_for('repetition_counter')},
        {"title": "AI-Personalized Sequence", "description": "AI generates a custom yoga flow based on your goals like stress relief or flexibility.", "link": url_for('ai_personalized_sequence')},
        {"title": "Challenge Mode", "description": "AI suggests daily/weekly yoga challenges and tracks your progress.", "link": url_for('challenge_mode')}
    ]
    return render_template('yoga_options.html', options=options)

@app.route('/repetition_counter')
def repetition_counter():
    return render_template('repetition_counter.html')

@app.route('/ai_personalized_sequence', methods=['GET', 'POST'])
def ai_personalized_sequence():
    if request.method == 'POST':
        goal = request.form.get('yoga_goal')
        generated_plan = generate_yoga_sequence(goal)
        return render_template('ai_personalized_sequence.html', generated_plan=generated_plan)
    return render_template('ai_personalized_sequence.html')

def generate_yoga_sequence(goal):
    sequences = {
        'stress_relief': {'title': "Stress Relief Sequence", 'poses': [{'name': 'Child\'s Pose', 'duration': '60 seconds'}]},
        'flexibility': {'title': "Flexibility Flow", 'poses': [{'name': 'Low Lunge', 'duration': '45 seconds each side'}]},
        'energy_boost': {'title': "Energy Boost Flow", 'poses': [{'name': 'Sun Salutations', 'duration': '5 rounds'}]}
    }
    return sequences.get(goal, {"title": "General Sequence", "poses": [{"name": "No goal selected. Please choose a goal."}]})

@app.route('/challenge_mode')
def challenge_mode():
    challenges = ["Hold Tree Pose for 2 minutes on each leg today.", "Perform 10 cat-cow poses to warm up your spine."]
    day_of_year = datetime.now().timetuple().tm_yday
    daily_challenge = challenges[(day_of_year - 1) % len(challenges)]
    return render_template('challenge_mode.html', daily_challenge=daily_challenge)

@app.route('/auto-classify')
def auto_classify():
    return "Auto-Classify: AI recommends a workout based on your profile."

@app.route('/video-workouts')
def video_workouts():
    return render_template('video_workouts.html')

@app.route('/custom-workout')
def custom_workout():
    return "Custom Workout: Design your own workout plan."

@app.route('/meditation-options')
def meditation_options():
    return render_template('meditation-options.html')

@app.route('/guided-meditation')
def guided_meditation():
    return render_template('guided_meditation.html')

@app.route('/breathing-visualizer')
def breathing_visualizer():
    return render_template('breathing_visualizer.html')

# --- Mood Tracking Routes (Omitted for brevity) ---
@app.route('/track-mood', methods=['GET'])
def track_mood_form():
    if 'user_email' not in session: flash("Please log in to track your mood.")
    return render_template('mood_tracker.html')

@app.route('/save-mood', methods=['POST'])
def save_mood():
    if 'user_email' not in session:
        flash("Please log in to save your mood.")
        return redirect(url_for('login'))
    
    user_email = session['user_email']
    mood_rating = request.form.get('mood_rating')
    mood_notes = request.form.get('mood_notes', '')

    if not mood_rating:
        flash("Please select a mood rating.")
        return redirect(url_for('track_mood_form'))

    sentiment_score = None
    if mood_notes:
        try:
            sentiment_score = analyze_mood_sentiment(mood_notes)
            print(f"Sentiment analysis for notes '{mood_notes}': {sentiment_score}")
        except Exception as e:
            print(f"Error during sentiment analysis with TextBlob: {e}")
            sentiment_score = "N/A"

    mood_entry = {
        'user_email': user_email,
        'mood_rating': int(mood_rating),
        'mood_notes': mood_notes,
        'sentiment_score': sentiment_score,
        'timestamp': datetime.now()
    }

    mood_entries_collection.insert_one(mood_entry)
    flash("Your mood has been logged successfully!")
    return redirect(url_for('mood_history'))

@app.route('/mood-history', methods=['GET'])
def mood_history():
    if 'user_email' not in session:
        flash("Please log in to view your mood history.")
        return redirect(url_for('login'))

    user_email = session['user_email']
    moods = list(mood_entries_collection.find({'user_email': user_email}).sort('timestamp', -1))

    avg_mood = "N/A"
    if moods:
        total_rating = sum(m['mood_rating'] for m in moods if 'mood_rating' in m)
        if moods:
            avg_mood = round(total_rating / len(moods), 2)

    return render_template('mood_history.html', moods=moods, avg_mood=avg_mood)

def analyze_mood_sentiment(text):
    analysis = TextBlob(text)
    if analysis.sentiment.polarity > 0: return "Positive"
    elif analysis.sentiment.polarity < 0: return "Negative"
    else: return "Neutral"

# --- Dashboard, Login/Register Routes (Omitted for brevity) ---
@app.route('/dashboard')
def dashboard():
    return "Dashboard Page"

@app.route('/statistics')
def statistics():
    return render_template('statistics.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = users_collection.find_one({'email': email, 'password': password})
        if user:
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            flash(f"Welcome back, {user['name']}!")
            return redirect(url_for('welcome'))
        else:
            flash("Invalid email or password. Please try again.")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/welcome')
def welcome():
    if 'user_name' in session:
        return render_template('welcome.html', name=session['user_name'])
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        if users_collection.find_one({'email': email}):
            flash('Email already registered. Please login.')
            return redirect(url_for('register'))

        users_collection.insert_one({
            'name': name,
            'email': email,
            'password': password,
            'joining_date': datetime.now()
        })
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/save_profile', methods=['POST'])
def save_profile():
    if 'user_email' not in session:
        flash("Please log in to save your profile.")
        return redirect(url_for('login'))

    data = request.form
    profile_data = {
        'email': session['user_email'],
        'height': int(data['height']),
        'weight': int(data['weight']),
        'age': int(data['age']),
        'gender': data['gender'],
        'bmi': float(data['bmi']) if data['bmi'] else None,
        'health_issues': request.form.getlist('health_issues')
    }
    profile_collection.update_one({'email': session['user_email']}, {'$set': profile_data}, upsert=True)
    flash("Your profile has been saved successfully!")
    return redirect(url_for('welcome'))

@app.route('/start_goal_mapping')
def start_goal_mapping():
    return render_template('goal_input.html')

@app.route('/generate_ai_plan', methods=['POST'])
def generate_ai_plan():
    try:
        user_goal = request.form.get('goal_description', '')
        if not user_goal:
            flash("Please provide a goal!")
            return redirect(url_for('start_goal_mapping'))
        
        system_prompt = """
        You are a highly experienced and motivational fitness coach. 
        Your task is to generate a comprehensive, personalized workout plan in Markdown format. 
        ...
        """
        
        user_prompt = f"Create a workout plan for someone whose goal is: {user_goal}"
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        
        ai_generated_plan = response.choices[0].message.content
        
        if 'user_email' in session:
            plan_entry = {
                'user_email': session['user_email'],
                'goal': user_goal,
                'plan_content': ai_generated_plan,
                'timestamp': datetime.now(),
                'plan_type': 'goal_mapping'
            }
            try:
                workout_plans_collection.insert_one(plan_entry)
                flash("Your workout plan has been saved successfully!")
            except Exception as e:
                print(f"Error saving workout plan to DB: {e}")
                flash("There was an issue saving your plan. Please try again.")
        else:
            flash("You are not logged in. Your workout plan was generated but not saved.")

        return render_template('ai_plan_display.html',
                               goal=user_goal,
                               plan=ai_generated_plan)
    except Exception as e:
        print(f"An error occurred during AI plan generation: {e}")
        flash(f"An error occurred: {e}. Please try again.", "error")
        return redirect(url_for('start_goal_mapping'))


@app.route('/build_workout')
def build_workout():
    if 'user_email' not in session: flash("Please log in to build a workout.")
    return render_template('workout_builder.html')

@app.route('/save_custom_workout', methods=['POST'])
def save_custom_workout():
    if 'user_email' not in session: return jsonify({'success': False, 'message': 'User not logged in'}), 401
    try:
        workout_details = request.json
        user_email = session['user_email']
        workout_document = {
            'user_email': user_email,
            'plan_type': 'custom',
            'created_on': datetime.now(),
            'workout_session': workout_details
        }
        result = custom_workouts_collection.insert_one(workout_document)
        return jsonify({'success': True, 'message': 'Workout saved successfully!', 'workout_id': str(result.inserted_id)})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to save workout: {e}'}), 500

@app.route('/start_custom_workout', methods=['POST'])
def start_custom_workout():
    if 'user_email' not in session: return jsonify({'success': False, 'message': 'Please log in to start a workout.'}), 401
    workout_data = request.json
    if not workout_data: return jsonify({'success': False, 'message': 'No workout data provided to start'}), 400
    session['current_workout_data'] = workout_data
    return jsonify({'success': True, 'redirect_url': url_for('start_workout_page')})

@app.route('/start_workout_page')
def start_workout_page():
    workout_data = session.pop('current_workout_data', None)
    if workout_data is None:
        flash('No workout to start. Please build a workout first.', 'error')
        return redirect(url_for('build_workout'))
    return render_template('start_workout.html', workout_data=workout_data)


# =======================================================================
# --- CLEAN, UNIFIED WEBCAM ROUTES ---
# =======================================================================

@app.route('/webcam_options')
def webcam_options():
    """Renders the webcam selection options page."""
    # OLD, CRASHING LINE: return render_template('webcam_options.html', exercises=TARGET_POSE_DATA)
    
    # NEW, CORRECT LINE: Use the unified ALL_EXERCISES dictionary
    return render_template('webcam_options.html', exercises=ALL_EXERCISES)


@app.route('/webcam_start/<exercise_name>')
def webcam_start(exercise_name):
    """Renders the live webcam streaming template (webcam_streamer.html)."""
    if 'user_email' not in session:
        flash("Please log in to start the webcam trainer.")
        return redirect(url_for('login')) 
    
    return render_template('webcam_streamer.html', exercise=exercise_name)


# NEW API ENDPOINT for JavaScript Polling
@app.route('/get_feedback/<exercise_name>')
def get_feedback(exercise_name):
    """Returns the latest analysis data for a given exercise as JSON."""
    
    # --- LOOKUP LOGIC ---
    dispatcher_info = EXERCISE_DISPATCHER.get(exercise_name)
    if not dispatcher_info:
        return jsonify({'feedback': 'Error: Exercise not registered.', 'reps': 0, 'stage': 'ERROR', 'angle': 'N/A'}), 404

    # Fetch the correct LATEST_FEEDBACK dictionary from the imported module
    feedback_state = dispatcher_info['feedback_state']

    data = feedback_state
    
    return jsonify(data)


@app.route('/video_feed/<exercise_name>')
def video_feed(exercise_name):
    """Yields frames from the OpenCV/MediaPipe analysis."""
    
    dispatcher_info = EXERCISE_DISPATCHER.get(exercise_name)
    if not dispatcher_info:
        # Return a simple error response for the video feed if exercise is not found
        return Response("Exercise not found.", status=404)

    # Get the specific generator function for this exercise
    generator_func = dispatcher_info['generator']
    
    return Response(
        generator_func(), # Call the specific generator function (e.g., generate_frames_squarts())
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

# =======================================================================
# --- END: CLEAN, UNIFIED WEBCAM ROUTES ---
# =======================================================================

if __name__ == '__main__':
    app.run(debug=True)