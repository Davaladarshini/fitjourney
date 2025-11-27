from flask import Blueprint, render_template, request, url_for, session, flash, redirect
from .extensions import gemini_client, personal_details_collection, health_issues_collection
from datetime import datetime

yoga_bp = Blueprint('yoga', __name__)

# --- Helper Function: Generate Static Sequence ---
def generate_yoga_sequence(goal):
    """Generates a multi-pose yoga sequence based on the selected goal."""
    sequences = {
        'stress_relief': {
            'title': "Calming Stress Relief Sequence",
            'poses': [
                {'name': 'Child\'s Pose (Balasana)', 'duration': '90 seconds', 'description': 'Deeply relaxing for the back and nervous system.'},
                {'name': 'Cat-Cow Flow (Marjaryasana-Bitilasana)', 'duration': '60 seconds', 'description': 'Gently warms up the spine and coordinates breath.'},
                {'name': 'Downward-Facing Dog (Adho Mukha Svanasana)', 'duration': '60 seconds', 'description': 'Stretches the shoulders, hamstrings, and calves.'},
                {'name': 'Seated Forward Fold (Paschimottanasana)', 'duration': '60 seconds', 'description': 'Calms the brain and helps relieve stress.'},
                {'name': 'Reclined Bound Angle Pose (Supta Baddha Konasana)', 'duration': '120 seconds', 'description': 'Opens the hips and promotes deep relaxation.'}
            ]
        },
        'flexibility': {
            'title': "Deep Hip & Hamstring Flexibility Flow",
            'poses': [
                {'name': 'Low Lunge (Anjaneyasana)', 'duration': '45 seconds each side', 'description': 'Stretches the hip flexors and quadriceps.'},
                {'name': 'Pyramid Pose (Parsvottanasana)', 'duration': '45 seconds each side', 'description': 'Intense stretch for the hamstrings and calves.'},
                {'name': 'Bound Angle Pose (Baddha Konasana)', 'duration': '60 seconds', 'description': 'Opens inner thighs, groins, and knees.'},
                {'name': 'Pigeon Pose (Eka Pada Rajakapotasana)', 'duration': '60 seconds each side', 'description': 'Deep hip opener targeting the glutes.'},
                {'name': 'Supported Bridge Pose (Setu Bandhasana)', 'duration': '45 seconds', 'description': 'Opens chest and helps lengthen the spine.'}
            ]
        },
        'energy_boost': {
            'title': "Morning Energy Boost Flow",
            'poses': [
                {'name': 'Sun Salutations (Surya Namaskar)', 'duration': '5 rounds', 'description': 'Dynamically links breath and movement for full-body warmth.'},
                {'name': 'Chair Pose (Utkatasana)', 'duration': '30 seconds', 'description': 'Strengthens hips, thighs, and calves.'},
                {'name': 'Warrior II (Virabhadrasana II)', 'duration': '45 seconds each side', 'description': 'Increases stamina and concentration.'},
                {'name': 'Tree Pose (Vrksasana)', 'duration': '30 seconds each side', 'description': 'Improves balance and focus.'},
                {'name': 'Backbend (Urdhva Mukha Svanasana)', 'duration': '45 seconds', 'description': 'Stretches the chest and invigorates the body.'}
            ]
        }
    }
    return sequences.get(goal, {"title": "General Sequence", "poses": [{"name": "No goal selected. Please choose a goal.", "duration": "", "description": ""}]})

# --- Routes ---

@yoga_bp.route('/yoga_workouts')
def yoga_workouts():
    return render_template('yoga_options.html')

@yoga_bp.route('/repetition_counter')
def repetition_counter():
    return render_template('repetition_counter.html')

@yoga_bp.route('/ai_personalized_sequence', methods=['GET', 'POST'])
def ai_personalized_sequence():
    if request.method == 'POST':
        goal = request.form.get('yoga_goal')
        generated_plan = generate_yoga_sequence(goal)
        return render_template('ai_personalized_sequence.html', generated_plan=generated_plan)
    return render_template('ai_personalized_sequence.html')

@yoga_bp.route('/challenge_mode')
def challenge_mode():
    challenges = [
        "Hold Tree Pose for 2 minutes on each leg today.", 
        "Perform 10 cat-cow poses to warm up your spine.",
        "Try a 5-minute meditation after your flow.",
        "Practice 5 rounds of Sun Salutation A."
    ]
    day_of_year = datetime.now().timetuple().tm_yday
    daily_challenge = challenges[(day_of_year - 1) % len(challenges)]
    return render_template('challenge_mode.html', daily_challenge=daily_challenge)

# --- REVERTED: Gemini BMI Recommendation Route (Text Only) ---
@yoga_bp.route('/yoga_bmi_recommendation')
def yoga_bmi_recommendation():
    if 'user_email' not in session:
        flash("Please log in to get personalized recommendations.")
        return redirect(url_for('auth.login'))
        
    user_email = session['user_email']
    
    # Fetch user details
    user_details = personal_details_collection.find_one({'email': user_email}) or {}
    health_info = health_issues_collection.find_one({'email': user_email}) or {}
    
    user_bmi = user_details.get('bmi', 'N/A')
    health_constraints = health_info.get('ai_processed_issues', 'None')
    
    system_prompt = f"""
    You are an expert Yoga Therapist. Create a safe and effective yoga routine for a user with the following profile:
    - BMI: {user_bmi}
    - Health Issues/Injuries: {health_constraints}
    
    1. Suggest 3-5 specific poses that are beneficial for their body type and safe for their conditions.
    2. Explain WHY each pose is chosen.
    3. Provide a modification for each pose to make it accessible.
    
    Format your response in clean HTML (use <h3> for pose names, <ul> for details, <strong> for emphasis). Do NOT use markdown code blocks.
    """
    
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[{"role": "user", "parts": [{"text": system_prompt}]}]
        )
        ai_plan = response.text
    except Exception as e:
        print(f"Gemini Error: {e}")
        ai_plan = "<p>Sorry, our AI yoga instructor is currently unavailable. Please try again later.</p>"

    return render_template('yoga_bmi_recommendation.html', plan=ai_plan)