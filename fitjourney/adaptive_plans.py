from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import os

adaptive_bp = Blueprint('adaptive_plans', __name__, template_folder='templates')

client = MongoClient(os.getenv('MONGO_URI', "mongodb://localhost:27017/"))
db = client["user_db"]
workout_plans_collection = db["workout_plans"]

@adaptive_bp.route('/start_adaptive_plan', methods=['GET'])
def start_adaptive_plan():
    if 'user_email' not in session:
        flash("Please log in to start an adaptive workout plan.")
        return redirect(url_for('auth.login'))
    return render_template('adaptive_plan_initial_input.html')

@adaptive_bp.route('/generate_initial_adaptive_plan', methods=['POST'])
def generate_initial_adaptive_plan():
    if 'user_email' not in session:
        flash("Please log in to generate an adaptive workout plan.")
        return redirect(url_for('auth.login'))

    user_email = session['user_email']
    workout_days_per_week = request.form.get('workout_days_per_week', type=int)
    fitness_level = request.form.get('fitness_level', '').lower()
    focus_area = request.form.get('focus_area', '').lower()

    if not workout_days_per_week or not fitness_level or not focus_area:
        flash("Please provide all initial adaptive plan details.")
        return redirect(url_for('adaptive_plans.start_adaptive_plan'))

    initial_plan_days = []
    generated_plan_description = ""

    if fitness_level == 'beginner' and focus_area == 'strength':
        generated_plan_description = "Beginner Strength & Full Body"
        initial_plan_days = [
            {"day": 1, "type": "Strength", "workout": "- Bodyweight Squats (3x10)\n- Push-ups (3xMax)\n- Plank (3x30s)", "status": "pending"},
            {"day": 2, "type": "Cardio", "workout": "- 20 min Brisk Walk", "status": "pending"},
            {"day": 3, "type": "Rest", "workout": "Active Recovery / Stretching", "status": "pending"},
            {"day": 4, "type": "Strength", "workout": "- Lunges (3x8 each leg)\n- Incline Push-ups (3xMax)\n- Glute Bridge (3x12)", "status": "pending"},
            {"day": 5, "type": "Cardio", "workout": "- 30 min Light Jog / Cycle", "status": "pending"},
            {"day": 6, "type": "Rest", "workout": "Complete Rest", "status": "pending"},
            {"day": 7, "type": "Rest", "workout": "Complete Rest", "status": "pending"},
        ]
    elif fitness_level == 'intermediate' and focus_area == 'cardio':
         generated_plan_description = "Intermediate Cardio Endurance"
         initial_plan_days = [
            {"day": 1, "type": "Cardio", "workout": "- 40 min Steady-State Run", "status": "pending"},
            {"day": 2, "type": "Strength", "workout": "- Full Body Circuit (Squats, Pushups, Rows - 3 rounds)", "status": "pending"},
            {"day": 3, "type": "Rest", "workout": "Active Recovery (Yoga/Stretch)", "status": "pending"},
            {"day": 4, "type": "Cardio", "workout": "- 30 min Interval Training (1min hard / 2min easy)", "status": "pending"},
            {"day": 5, "type": "Strength", "workout": "- Core & Mobility (Plank, Side Plank, Bird Dog)", "status": "pending"},
            {"day": 6, "type": "Cardio", "workout": "- 60 min Long Run", "status": "pending"},
            {"day": 7, "type": "Rest", "workout": "Complete Rest", "status": "pending"},
        ]
    else:
        generated_plan_description = "General Adaptive Plan (Default)"
        initial_plan_days = [
            {"day": 1, "type": "Strength", "workout": "- Default Strength Workout", "status": "pending"},
            {"day": 2, "type": "Cardio", "workout": "- Default Cardio Workout", "status": "pending"},
            {"day": 3, "type": "Rest", "workout": "Rest", "status": "pending"},
            {"day": 4, "type": "Strength", "workout": "- Default Strength Workout 2", "status": "pending"},
            {"day": 5, "type": "Cardio", "workout": "- Default Cardio Workout 2", "status": "pending"},
            {"day": 6, "type": "Rest", "workout": "Rest", "status": "pending"},
            {"day": 7, "type": "Rest", "workout": "Rest", "status": "pending"},
        ]

    new_adaptive_plan = {
        'user_email': user_email,
        'plan_type': 'adaptive',
        'generated_on': datetime.now(),
        'current_day_index': 0,
        'status': 'active',
        'initial_preferences': {
            'workout_days_per_week': workout_days_per_week,
            'fitness_level': fitness_level,
            'focus_area': focus_area
        },
        'plan_schedule': initial_plan_days,
        'feedback_history': []
    }

    try:
        inserted_plan = workout_plans_collection.insert_one(new_adaptive_plan)
        session['current_adaptive_plan_id'] = str(inserted_plan.inserted_id)
        flash("Your adaptive workout plan has been generated!")
        return redirect(url_for('adaptive_plans.view_current_adaptive_day')) 
    except Exception as e:
        print(f"Error saving initial adaptive plan: {e}")
        flash("Could not generate your adaptive plan. Please try again.")
        return redirect(url_for('adaptive_plans.start_adaptive_plan'))

@adaptive_bp.route('/adaptive_plan/current_day')
def view_current_adaptive_day():
    if 'user_email' not in session:
        flash("Please log in to view your adaptive workout.")
        return redirect(url_for('auth.login'))
    if 'current_adaptive_plan_id' not in session:
        flash("You don't have an active adaptive plan. Please start one.")
        return redirect(url_for('adaptive_plans.start_adaptive_plan')) 

    plan_id = ObjectId(session['current_adaptive_plan_id'])
    current_plan = workout_plans_collection.find_one({'_id': plan_id, 'user_email': session['user_email']})

    if not current_plan:
        flash("Active plan not found. Please start a new one.")
        session.pop('current_adaptive_plan_id', None)
        return redirect(url_for('adaptive_plans.start_adaptive_plan'))

    current_day_index = current_plan.get('current_day_index', 0)
    plan_schedule = current_plan.get('plan_schedule', [])

    if current_day_index >= len(plan_schedule):
        flash("You've completed this phase of your adaptive plan! Great job!")
        workout_plans_collection.update_one({'_id': plan_id}, {'$set': {'status': 'completed'}})
        session.pop('current_adaptive_plan_id', None)
        return redirect(url_for('adaptive_plans.adaptive_plan_history'))

    current_day_workout = plan_schedule[current_day_index]

    return render_template('current_adaptive_day.html',
                           plan=current_plan,
                           current_day_workout=current_day_workout,
                           day_number=current_day_index + 1)

@adaptive_bp.route('/adaptive_plan/log_feedback', methods=['POST'])
def log_adaptive_feedback():
    if 'user_email' not in session or 'current_adaptive_plan_id' not in session:
        flash("You must be logged in and have an active plan to log feedback.")
        return redirect(url_for('auth.login'))

    plan_id = ObjectId(session['current_adaptive_plan_id'])
    current_plan = workout_plans_collection.find_one({'_id': plan_id, 'user_email': session['user_email']})

    if not current_plan:
        flash("Active plan not found. Please start a new one.")
        session.pop('current_adaptive_plan_id', None)
        return redirect(url_for('adaptive_plans.start_adaptive_plan'))

    current_day_index = current_plan.get('current_day_index', 0)
    plan_schedule = current_plan.get('plan_schedule', [])

    if current_day_index >= len(plan_schedule):
        flash("Plan already completed or invalid day for feedback.")
        return redirect(url_for('adaptive_plans.view_current_adaptive_day'))

    workout_status = request.form.get('workout_status')
    difficulty_rating = request.form.get('difficulty_rating', type=int)
    feedback_notes = request.form.get('feedback_notes', '')

    current_workout_data = plan_schedule[current_day_index]

    current_workout_data['status'] = workout_status
    current_workout_data['difficulty_rating'] = difficulty_rating
    current_workout_data['feedback_notes'] = feedback_notes
    current_workout_data['completed_at'] = datetime.now()

    feedback_entry = {
        'day_index': current_day_index,
        'original_workout': current_workout_data['workout'],
        'status': workout_status,
        'difficulty': difficulty_rating,
        'notes': feedback_notes,
        'timestamp': datetime.now()
    }

    workout_plans_collection.update_one(
        {'_id': plan_id},
        {
            '$push': {'feedback_history': feedback_entry},
            '$set': {f'plan_schedule.{current_day_index}': current_workout_data}
        }
    )

    if workout_status == 'skipped' and current_workout_data['type'] == 'Strength' and 'Legs' in current_workout_data['workout']:
        for i in range(current_day_index + 1, len(plan_schedule)):
            if plan_schedule[i]['type'] != 'Rest':
                flash(f"Leg workout was skipped. Adding a lighter leg focus to Day {i+1}!")
                plan_schedule[i]['workout'] += "\n\n(Adaptive addition: Light Leg Focus: 3x15 Bodyweight Lunges)"
                workout_plans_collection.update_one({'_id': plan_id}, {'$set': {'plan_schedule': plan_schedule}})
                break

    if difficulty_rating == 5 and current_workout_data['type'] == 'Strength':
        flash("Workout was very hard. Future similar workouts might be adjusted down.")

    if difficulty_rating == 1 and current_workout_data['type'] == 'Strength':
        flash("Workout was easy. Consider increasing weight/reps next time.")

    new_day_index = current_day_index + 1
    workout_plans_collection.update_one(
        {'_id': plan_id},
        {'$set': {'current_day_index': new_day_index}}
    )

    flash("Workout feedback logged. Your plan has adapted!")
    return redirect(url_for('adaptive_plans.view_current_adaptive_day'))

@adaptive_bp.route('/adaptive_plan/history')
def adaptive_plan_history():
    if 'user_email' not in session:
        flash("Please log in to view your adaptive plan history.")
        return redirect(url_for('auth.login')) 
    user_email = session['user_email']
    past_plans = list(workout_plans_collection.find({'user_email': user_email, 'plan_type': 'adaptive'}).sort('generated_on', -1))
    return render_template('adaptive_plan_history.html', plans=past_plans)