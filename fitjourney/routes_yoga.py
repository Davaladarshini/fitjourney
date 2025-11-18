from flask import Blueprint, render_template, request, url_for
from datetime import datetime

yoga_bp = Blueprint('yoga', __name__)

def generate_yoga_sequence(goal):
    sequences = {
        'stress_relief': {'title': "Stress Relief Sequence", 'poses': [{'name': 'Child\'s Pose', 'duration': '60 seconds'}]},
        'flexibility': {'title': "Flexibility Flow", 'poses': [{'name': 'Low Lunge', 'duration': '45 seconds each side'}]},
        'energy_boost': {'title': "Energy Boost Flow", 'poses': [{'name': 'Sun Salutations', 'duration': '5 rounds'}]}
    }
    return sequences.get(goal, {"title": "General Sequence", "poses": [{"name": "No goal selected. Please choose a goal."}]})

@yoga_bp.route('/yoga_workouts')
def yoga_workouts():
    options = [
        {"title": "Repetition Counter", "description": "Tracks rounds for Sun Salutations.", "link": url_for('yoga.repetition_counter')},
        {"title": "AI-Personalized Sequence", "description": "AI generates a custom flow based on your goals.", "link": url_for('yoga.ai_personalized_sequence')},
        {"title": "Challenge Mode", "description": "AI suggests daily/weekly yoga challenges.", "link": url_for('yoga.challenge_mode')}
    ]
    return render_template('yoga_options.html', options=options)

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
    challenges = ["Hold Tree Pose for 2 minutes on each leg today.", "Perform 10 cat-cow poses to warm up your spine."]
    day_of_year = datetime.now().timetuple().tm_yday
    daily_challenge = challenges[(day_of_year - 1) % len(challenges)]
    return render_template('challenge_mode.html', daily_challenge=daily_challenge)