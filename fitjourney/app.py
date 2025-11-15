from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from breathing_patterns import breathing_bp
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import os
from openai import OpenAI # Make sure this is imported
from dotenv import load_dotenv; load_dotenv()
import json

# From TextBlob for mood sentiment (assuming it's installed: pip install textblob)
from textblob import TextBlob

# --- Import your adaptive plans blueprint ---
from adaptive_plans import adaptive_bp

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24).hex())

app.register_blueprint(breathing_bp)
# --- Register the adaptive plans blueprint ---
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

# --- MODIFIED: The main yoga workout route now shows the new options ---
@app.route('/yoga_workouts')
def yoga_workouts():
    options = [
        {
            "title": "Repetition Counter",
            "description": "Tracks how many rounds you complete for Sun Salutations and other repeated poses.",
            "link": url_for('repetition_counter'),
        },
        {
            "title": "AI-Personalized Sequence",
            "description": "AI generates a custom yoga flow based on your goals like stress relief or flexibility.",
            "link": url_for('ai_personalized_sequence'),
        },
        {
            "title": "Challenge Mode",
            "description": "AI suggests daily/weekly yoga challenges and tracks your progress.",
            "link": url_for('challenge_mode'),
        }
    ]
    return render_template('yoga_options.html', options=options)

# NEW: Route for the Repetition Counter feature
@app.route('/repetition_counter')
def repetition_counter():
    return render_template('repetition_counter.html')

# NEW: Route for the AI Personalized Sequence feature
@app.route('/ai_personalized_sequence', methods=['GET', 'POST'])
def ai_personalized_sequence():
    if request.method == 'POST':
        goal = request.form.get('yoga_goal')
        generated_plan = generate_yoga_sequence(goal)
        return render_template('ai_personalized_sequence.html', generated_plan=generated_plan)
    return render_template('ai_personalized_sequence.html')

# Simple AI logic for demonstration
def generate_yoga_sequence(goal):
    sequences = {
        'stress_relief': {
            'title': "Stress Relief Sequence",
            'poses': [
                {'name': 'Child\'s Pose', 'duration': '60 seconds', 'description': 'Calms the mind, releases tension.'},
                {'name': 'Cat-Cow Pose', 'duration': '5 rounds', 'description': 'Stretches the spine, soothes the nervous system.'},
                {'name': 'Downward-Facing Dog', 'duration': '30 seconds', 'description': 'Full body stretch, calms the brain.'},
                {'name': 'Forward Fold', 'duration': '45 seconds', 'description': 'Releases tension in the hamstrings and lower back.'},
                {'name': 'Corpse Pose', 'duration': '5 minutes', 'description': 'The final resting pose for deep relaxation.'},
            ]
        },
        'flexibility': {
            'title': "Flexibility Flow",
            'poses': [
                {'name': 'Low Lunge', 'duration': '45 seconds each side', 'description': 'Deep stretch for the hips and legs.'},
                {'name': 'Pigeon Pose', 'duration': '60 seconds each side', 'description': 'Opens the hips and outer thighs.'},
                {'name': 'Bound Angle Pose', 'duration': '60 seconds', 'description': 'Improves flexibility in the inner thighs and groin.'},
                {'name': 'Seated Forward Bend', 'duration': '60 seconds', 'description': 'Stretches the hamstrings and spine.'},
                {'name': 'Spinal Twist', 'duration': '45 seconds each side', 'description': 'Releases tension in the back and hips.'},
            ]
        },
        'energy_boost': {
            'title': "Energy Boost Flow",
            'poses': [
                {'name': 'Sun Salutations', 'duration': '5 rounds', 'description': 'Warms up the body, builds heat and energy.'},
                {'name': 'Warrior II', 'duration': '30 seconds each side', 'description': 'Builds strength and focus.'},
                {'name': 'Chair Pose', 'duration': '30 seconds', 'description': 'Strengthens legs and core.'},
                {'name': 'Plank Pose', 'duration': '45 seconds', 'description': 'Engages the entire body.'},
                {'name': 'Cobra Pose', 'duration': '30 seconds', 'description': 'Opens the chest and energizes the spine.'},
            ]
        }
    }
    return sequences.get(goal, {"title": "General Sequence", "poses": [{"name": "No goal selected. Please choose a goal."}]})


# --- MODIFIED: The Challenge Mode route now selects a daily challenge from a list ---
@app.route('/challenge_mode')
def challenge_mode():
    challenges = [
        "Hold Tree Pose for 2 minutes on each leg today.",
        "Perform 10 cat-cow poses to warm up your spine.",
        "Practice a 5-minute seated meditation with conscious breathing.",
        "Complete 3 rounds of Sun Salutation A.",
        "Hold a plank pose for 60 seconds."
    ]
    # Get the day of the year (1-366)
    day_of_year = datetime.now().timetuple().tm_yday
    # Use the day to get an index within the list
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

@app.route('/webcam-trainer')
def webcam_trainer():
    return "Webcam Trainer: Real-time form feedback via webcam."

@app.route('/meditation-options')
def meditation_options():
    return render_template('meditation-options.html')

@app.route('/guided-meditation')
def guided_meditation():
    return render_template('guided_meditation.html')

@app.route('/breathing-visualizer')
def breathing_visualizer():
    return render_template('breathing_visualizer.html')

@app.route('/track-mood', methods=['GET'])
def track_mood_form():
    if 'user_email' not in session:
        flash("Please log in to track your mood.")
        return redirect(url_for('login'))
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
    if analysis.sentiment.polarity > 0:
        return "Positive"
    elif analysis.sentiment.polarity < 0:
        return "Negative"
    else:
        return "Neutral"

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

# --- MODIFIED: This function now uses the OpenAI API to generate the plan ---
@app.route('/generate_ai_plan', methods=['POST'])
def generate_ai_plan():
    try:
        user_goal = request.form.get('goal_description', '')
        if not user_goal:
            flash("Please provide a goal!")
            return redirect(url_for('start_goal_mapping'))
        
        # Define the system prompt for the AI
        system_prompt = """
        You are a highly experienced and motivational fitness coach. 
        Your task is to generate a comprehensive, personalized workout plan in Markdown format. 
        The plan should be well-structured, easy to follow, and specifically tailored to the user's goal. 
        Do not include any pre- or post-text, just the plan itself.

        Use the following structure for the workout plan:

        **Month 1: [Focus]**
        
        * **Week 1: [Specific Focus]**
            * [Daily workout 1]
            * [Daily workout 2]
        * **Week 2: [Specific Focus]**
            * [Daily workout 1]
            * [Daily workout 2]
        ... and so on for the rest of the plan.

        Make sure the entire plan is detailed and spans several weeks or months, depending on the goal.
        """
        
        # Combine system prompt and user's goal into a message for the AI
        user_prompt = f"Create a workout plan for someone whose goal is: {user_goal}"
        
        # Call the OpenAI API to generate the workout plan
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        
        # Extract the generated plan text
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
    if 'user_email' not in session:
        flash("Please log in to build a workout.")
        return redirect(url_for('login'))
    return render_template('workout_builder.html')

@app.route('/save_custom_workout', methods=['POST'])
def save_custom_workout():
    if 'user_email' not in session:
        return jsonify({'success': False, 'message': 'User not logged in'}), 401
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
    if 'user_email' not in session:
        return jsonify({'success': False, 'message': 'Please log in to start a workout.'}), 401
    workout_data = request.json
    if not workout_data:
        return jsonify({'success': False, 'message': 'No workout data provided to start'}), 400
    session['current_workout_data'] = workout_data
    return jsonify({'success': True, 'redirect_url': url_for('start_workout_page')})

@app.route('/start_workout_page')
def start_workout_page():
    workout_data = session.pop('current_workout_data', None)
    if workout_data is None:
        flash('No workout to start. Please build a workout first.', 'error')
        return redirect(url_for('build_workout'))
    return render_template('start_workout.html', workout_data=workout_data)

if __name__ == '__main__':
    app.run(debug=True)
