# fitjourney/routes_yoga.py

from flask import Blueprint, render_template, request, url_for
from datetime import datetime

yoga_bp = Blueprint('yoga', __name__)

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