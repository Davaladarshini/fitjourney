from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from .extensions import workout_plans_collection, gemini_client, personal_details_collection, health_issues_collection 
from bson.objectid import ObjectId
from datetime import datetime
import json
import os

adaptive_bp = Blueprint('adaptive_plans', __name__, template_folder='templates')

# --- AI Helper Functions (Retained from previous step) ---

def generate_plan_with_ai(user_email, workout_days, level, focus):
    """Generates a 7-day workout plan dynamically using Gemini."""
    user_details = personal_details_collection.find_one({'email': user_email}) or {}
    health_info = health_issues_collection.find_one({'email': user_email}) or {}
    
    user_bmi = user_details.get('bmi', 'N/A')
    health_constraints = health_info.get('ai_processed_issues', 'None')
    user_age = user_details.get('age', 'N/A')
    
    system_instruction = f"""
    You are an expert fitness planner. Generate a comprehensive 7-day workout plan tailored to the user's profile.
    
    User Profile:
    - Fitness Level: {level}
    - Primary Focus: {focus}
    - Workouts Per Week: {workout_days}
    - Age: {user_age}
    - BMI: {user_bmi}
    - Health Constraints: {health_constraints}. EXCLUDE all exercises that could aggravate these constraints.
    
    Generate a 7-day schedule. Designate each day's 'type' as 'Strength', 'Cardio', 'Flexibility', or 'Rest'. Use 'Rest' for days without dedicated activity. Ensure the number of non-rest days roughly matches the Workouts Per Week preference.
    
    CRITICAL: Respond ONLY with a single JSON array that follows this strict schema. DO NOT include any text, markdown, or explanation outside of the JSON array.
    
    [
        {{
            "day": 1, 
            "type": "Strength", 
            "workout": "Warmup (5min). Bodyweight Squats (3x15). Push-ups (3xMax). Plank (3x45s). Cooldown (5min).", 
            "status": "pending"
        }},
        // ... all 7 days with sequential 'day' numbers ...
    ]
    """
    
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[{"role": "user", "parts": [{"text": system_instruction}]}],
            config={"temperature": 0.8}
        )
        json_string = response.text.strip().lstrip('`json').rstrip('`').strip()
        return json.loads(json_string)
        
    except Exception as e:
        print(f"Gemini Plan Generation Error: {e}")
        flash("AI plan generation failed. Using default plan as a fallback.")
        # Robust Fallback Plan
        return [
            {"day": 1, "type": "Strength", "workout": "Fallback: Full Body Circuit (3x10)", "status": "pending"},
            {"day": 2, "type": "Cardio", "workout": "Fallback: 20 min Steady Cardio", "status": "pending"},
            {"day": 3, "type": "Rest", "workout": "Rest Day", "status": "pending"},
            {"day": 4, "type": "Strength", "workout": "Fallback: Upper Body (3x10)", "status": "pending"},
            {"day": 5, "type": "Rest", "workout": "Rest Day", "status": "pending"},
            {"day": 6, "type": "Flexibility", "workout": "Fallback: 30 min Yoga/Stretch", "status": "pending"},
            {"day": 7, "type": "Rest", "workout": "Rest Day", "status": "pending"},
        ]

def adapt_plan_with_ai(plan_context, remaining_schedule, feedback_entry):
    """Adapts the remaining plan days based on the latest feedback using Gemini."""
    
    # Context for the AI
    context_string = f"""
    Initial Preferences: Level={plan_context['fitness_level']}, Focus={plan_context['focus_area']}
    Last Workout Day: {feedback_entry['day_index'] + 1}
    Feedback Logged: Status={feedback_entry['status']}, Difficulty={feedback_entry['difficulty']}/5, Notes='{feedback_entry['notes']}'
    
    Goal: Rewrite the remaining plan based on this feedback.
    - If difficulty was 4 or 5, slightly reduce intensity for similar upcoming days.
    - If difficulty was 1 or 2, increase intensity (reps/duration) for similar upcoming days.
    - If status was 'skipped', consider rescheduling or replacing the skipped type.
    - If status was 'modified', use the notes to inform future changes.
    """
    
    # Provide the remaining schedule in JSON format for the AI to modify
    remaining_json_string = json.dumps(remaining_schedule)
    
    system_instruction = f"""
    You are an adaptive fitness coach. Review the context and the remaining workout plan below.
    You MUST modify the remaining plan to ADAPT to the user's latest feedback.
    
    CRITICAL: Respond ONLY with a single JSON array that represents the MODIFIED remaining schedule. DO NOT include any text, markdown, or explanation outside of the JSON array.
    
    CONTEXT: {context_string}
    
    REMAINING SCHEDULE TO MODIFY (JSON Array): {remaining_json_string}
    """
    
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[{"role": "user", "parts": [{"text": system_instruction}]}],
            config={"temperature": 0.5}
        )
        json_string = response.text.strip().lstrip('`json').rstrip('`').strip()
        modified_schedule = json.loads(json_string)
        
        # Simple validation: ensure the modified schedule is an array and keeps the same structure
        if not isinstance(modified_schedule, list) or not all(isinstance(d, dict) and 'day' in d for d in modified_schedule):
            raise ValueError("AI returned an invalid JSON schedule structure.")
            
        return modified_schedule
        
    except Exception as e:
        print(f"Gemini Plan Adaptation Error: {e}. Reverting to original remaining plan.")
        flash("Adaptive update failed. Continuing with the original future schedule.")
        return remaining_schedule # Return original un-adapted schedule as a safe fallback


# --- Routes ---

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

    # --- AI PLAN GENERATION ---
    initial_plan_days = generate_plan_with_ai(user_email, workout_days_per_week, fitness_level, focus_area)
    # -------------------------

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

    # 1. Update the completed day's data
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
    
    # 2. Get the remaining schedule that needs adaptation
    remaining_schedule = plan_schedule[current_day_index + 1:]
    
    # --- AI ADAPTATION LOGIC ---
    if remaining_schedule:
        plan_context = current_plan.get('initial_preferences', {})
        modified_remaining_schedule = adapt_plan_with_ai(plan_context, remaining_schedule, feedback_entry)
        
        # Reconstruct the full plan schedule
        new_plan_schedule = plan_schedule[:current_day_index] + [current_workout_data] + modified_remaining_schedule
    else:
        new_plan_schedule = plan_schedule[:current_day_index] + [current_workout_data]
    # --------------------------

    # 3. Update DB with new plan, feedback, and advance the day index
    new_day_index = current_day_index + 1
    
    workout_plans_collection.update_one(
        {'_id': plan_id},
        {
            '$push': {'feedback_history': feedback_entry},
            '$set': {
                'plan_schedule': new_plan_schedule, # Save the new, adapted schedule
                'current_day_index': new_day_index
            }
        }
    )

    flash("Workout feedback logged. Your plan has adapted!")
    return redirect(url_for('adaptive_plans.view_current_adaptive_day'))

# --- NEW ROUTE: DELETE PLAN ---
@adaptive_bp.route('/adaptive_plan/delete/<plan_id>', methods=['POST'])
def delete_adaptive_plan(plan_id):
    if 'user_email' not in session:
        flash("Please log in to delete plans.")
        return redirect(url_for('auth.login')) 
    
    try:
        # 1. Ensure the plan belongs to the logged-in user
        result = workout_plans_collection.delete_one({
            '_id': ObjectId(plan_id),
            'user_email': session['user_email']
        })
        
        if result.deleted_count == 1:
            # 2. If the deleted plan was the user's active plan, clear the session variable
            if session.get('current_adaptive_plan_id') == plan_id:
                session.pop('current_adaptive_plan_id', None)
            
            flash("Adaptive workout plan deleted successfully!", "success")
        else:
            flash("Error: Plan not found or you do not have permission to delete it.", "error")
            
    except Exception as e:
        print(f"Error deleting plan {plan_id}: {e}")
        flash("An error occurred during plan deletion.", "error")

    return redirect(url_for('adaptive_plans.adaptive_plan_history'))
# -----------------------------

@adaptive_bp.route('/adaptive_plan/history')
def adaptive_plan_history():
    if 'user_email' not in session:
        flash("Please log in to view your adaptive plan history.")
        return redirect(url_for('auth.login')) 
    user_email = session['user_email']
    past_plans = list(workout_plans_collection.find({'user_email': user_email, 'plan_type': 'adaptive'}).sort('generated_on', -1))
    return render_template('adaptive_plan_history.html', plans=past_plans)