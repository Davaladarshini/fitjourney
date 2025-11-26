from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
# UPDATED IMPORT: Added health_issues_collection
from .extensions import gemini_client, workout_plans_collection, custom_workouts_collection, personal_details_collection, health_issues_collection 
from datetime import datetime
import re # Used for keyword matching

ai_workouts_bp = Blueprint('ai_workouts', __name__)

# --- UPDATED: Static Exercise Library for Workout Builder (COMPREHENSIVE LIST) ---
STATIC_EXERCISE_LIBRARY = [
    # Strength/Reps-Sets
    {"name": "Bodyweight Squats", "type": "reps_sets"},
    {"name": "Push Ups", "type": "reps_sets"},
    {"name": "Crunches", "type": "reps_sets"},
    {"name": "Pull-ups", "type": "reps_sets"},


    
    # Cardio/Reps-Sets or Duration
    {"name": "Jumping Jacks", "type": "reps_sets"},
    {"name": "Running (Jog)", "type": "duration"},
    {"name": "Rope Skipping", "type": "duration"},
    {"name": "Cycling", "type": "duration"},
    
    # Core/Hold/Flexibility (Duration)
    {"name": "Plank Hold", "type": "duration"},
    {"name": "Wall Sit", "type": "duration"},
    {"name": "Stretch (Warmup)", "type": "duration"},
    {"name": "Stretch (Cooldown)", "type": "duration"},
]
# --- END UPDATED ---


def generate_bmi_workout_with_ai(user_email, user_bmi):
    """Generates a personalized workout and tips based on BMI using Gemini."""
    
    # FIX: Access health_issues_collection directly
    health_info = health_issues_collection.find_one({'email': user_email}) or {}
    health_constraints = health_info.get('ai_processed_issues', 'None')
    
    bmi_category = "Healthy Weight"
    if user_bmi < 18.5: bmi_category = "Underweight"
    elif user_bmi >= 25.0 and user_bmi < 30.0: bmi_category = "Overweight"
    elif user_bmi >= 30.0: bmi_category = "Obese"

    system_instruction = f"""
    You are an expert fitness coach specializing in BMI-based recommendations. 
    The user's current BMI is {user_bmi}, categorized as {bmi_category}.
    User's Health Constraints: {health_constraints}. Ensure the plan is safe given these constraints.
    
    Generate a concise, 3-day workout plan (Workout 1: Full Body, Workout 2: Cardio Focus, Workout 3: Flexibility/Mobility) and a section for essential tips.
    
    Your response MUST be formatted cleanly with clear headings but avoid complex markdown (like tables). Use #### for main headings and - for list items.

    Example structure:
    #### BMI Category: {bmi_category}
    #### Goal: [Specific Goal based on category]
    
    #### Workout 1: Full Body
    - Exercise 1: [Details]
    - Exercise 2: [Details]
    
    #### Essential Tips
    - Tip 1
    - Tip 2
    """
    
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[{"role": "user", "parts": [{"text": system_instruction}]}],
            config={"temperature": 0.8}
        )
        return response.text
        
    except Exception as e:
        print(f"Gemini BMI Plan Generation Error: {e}")
        return "AI plan generation failed. Check your API key and network connection."


# --- NEW AJAX ROUTE FOR MODAL CONTENT ---
@ai_workouts_bp.route('/fetch_bmi_recommendation_content', methods=['POST'])
def fetch_bmi_recommendation_content():
    if 'user_email' not in session:
        return jsonify({'error': 'Please log in to get recommendations.'}), 401
        
    user_email = session['user_email']
    
    user_details = personal_details_collection.find_one({'email': user_email}) or {}
    user_bmi = user_details.get('bmi')
    
    if user_bmi is None or user_bmi <= 0:
        return jsonify({'error': "BMI not found. Please update your weight and height in your profile."}), 400
        
    # Generate the plan (calls the helper function)
    ai_recommendation = generate_bmi_workout_with_ai(user_email, user_bmi)
    
    # Return the recommendation and BMI in a JSON object for the modal
    return jsonify({
        'success': True,
        'bmi': user_bmi,
        'recommendation': ai_recommendation
    }), 200

# --- Existing bmi_recommendation route (kept as a full-page fallback) ---
@ai_workouts_bp.route('/bmi_recommendation')
def bmi_recommendation():
    if 'user_email' not in session:
        flash("Please log in to get BMI recommendations.")
        return redirect(url_for('auth.login'))
        
    user_email = session['user_email']
    
    # Fetch user details (including BMI)
    user_details = personal_details_collection.find_one({'email': user_email}) or {}
    user_bmi = user_details.get('bmi')
    
    if user_bmi is None or user_bmi <= 0:
        flash("Please update your weight and height in your profile to calculate your BMI first.")
        return redirect(url_for('auth.edit_profile'))
        
    # Generate the plan (calls the helper function)
    ai_recommendation = generate_bmi_workout_with_ai(user_email, user_bmi)
    
    return render_template('bmi_recommendation.html', 
                           bmi=user_bmi, 
                           recommendation=ai_recommendation)
# --- End existing bmi_recommendation route ---


@ai_workouts_bp.route('/start_goal_mapping')
def start_goal_mapping():
    return render_template('goal_input.html')

@ai_workouts_bp.route('/generate_ai_plan', methods=['POST'])
def generate_ai_plan():
    try:
        user_goal = request.form.get('goal_description', '')
        if not user_goal:
            flash("Please provide a goal!")
            return redirect(url_for('ai_workouts.start_goal_mapping'))
        
        # --- NEW LOGIC: FETCH USER PROFILE AND APPLY HEALTH CHECK ---
        ai_warning_message = None
        user_details = personal_details_collection.find_one({'email': session.get('user_email')})
        # BMI is calculated and saved on profile update (routes_auth.py)
        user_bmi = user_details.get('bmi') if user_details else None

        # Simple check for common weight loss keywords
        # Checks if phrases like 'lose weight', 'reduce 5kg', etc., are present
        is_weight_loss_goal = bool(re.search(r'\b(lose|reduce|drop|cut)\b.*(\d+\s*kg|weight|fat|mass)', user_goal, re.IGNORECASE))
        
        # Check if user is underweight (BMI < 18.5) and is trying to lose weight
        if user_bmi is not None and user_bmi < 18.5 and is_weight_loss_goal:
            
            # 1. Create a strong warning message for the display
            ai_warning_message = f"""
***HEALTH WARNING: Goal Adjustment Recommended***

Based on your profile, your current BMI is **{user_bmi}**, which is classified as **Underweight**.

Your stated goal of "{user_goal}" is **not recommended** for your current health status. 
The priority should be **safe weight gain, muscle building, and improving foundational strength**.

The plan generated below is **ADJUSTED** to focus on healthy **muscle gain and balanced nutrition** rather than weight loss. Please consult a healthcare professional before pursuing weight loss.
---
"""
            # 2. Re-phrase the user prompt to force the AI to generate a SAFE plan
            modified_goal = f"My user is underweight (BMI {user_bmi}) and initially asked to lose weight. IGNORE that request and instead, generate a comprehensive workout plan focused purely on safe weight gain, muscle hypertrophy, and building core strength. Emphasize a calorie-surplus diet. The user's original input was: '{user_goal}'."
            user_prompt_to_use = modified_goal
        
        else:
            # Use the original prompt/goal if the health check passes or is irrelevant
            user_prompt_to_use = f"Create a workout plan for someone whose goal is: {user_goal}"
            
        # --- END NEW LOGIC ---

        # UPDATED SYSTEM PROMPT: Forbids Markdown and focuses on clean text formatting.
        system_prompt = """
You are a highly experienced and motivational fitness coach. 
Your task is to generate a comprehensive, personalized workout plan. 
Format the response using only line breaks and simple punctuation, like dashes or parentheses. 
DO NOT use Markdown, Hashtags (#), Asterisks (*), or bold formatting unless specifically requested in the user prompt (e.g., if the user prompt includes the health warning message).
"""
        
        # --- GEMINI API CALL for Plan Generation ---
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                {"role": "user", "parts": [
                    {"text": system_prompt},
                    {"text": user_prompt_to_use}
                ]}
            ],
            config={"temperature": 0.7}
        )
        # --- END GEMINI API CALL ---
        
        ai_generated_plan = response.text 
        
        # Prepend the warning message if the safety check was triggered
        if ai_warning_message:
            ai_generated_plan = ai_warning_message + ai_generated_plan
            
        if 'user_email' in session:
            plan_entry = {
                'user_email': session['user_email'],
                'goal': user_goal,
                'plan_content': ai_generated_plan,
                'timestamp': datetime.now(),
                'plan_type': 'goal_mapping',
                'safety_check_applied': bool(ai_warning_message)
            }
            workout_plans_collection.insert_one(plan_entry)
            flash("Your workout plan has been saved successfully!")
        else:
            flash("Plan generated but not saved. Please log in.")

        return render_template('ai_plan_display.html',
                               goal=user_goal,
                               plan=ai_generated_plan)
    except Exception as e:
        print(f"An error occurred during AI plan generation: {e}")
        flash(f"An error occurred: {e}. Please try again.", "error")
        return redirect(url_for('ai_workouts.start_goal_mapping'))

# --- CORRECTED CHATBOT ROUTE (using generate_content for history) ---
@ai_workouts_bp.route('/chat_with_ai', methods=['POST'])
def chat_with_ai():
    data = request.get_json()
    user_message = data.get('message')
    conversation_history = data.get('history', [])

    if not user_message:
        return jsonify({'response': 'Please enter a message.'}), 400

    system_instruction = """
    You are 'FitBot', a friendly, highly knowledgeable, and motivating fitness and health coach. 
    Your goal is to provide concise, safe, and helpful advice on fitness, workouts, nutrition, and well-being. 
    Keep your responses encouraging and under 100 words. Do not provide medical advice.
    """
    
    # Manually build the contents list, including the system instruction
    contents = [
        {"role": "user", "parts": [{"text": system_instruction}]}
    ]

    # Reconstruct history for the request
    for msg in conversation_history:
        # Gemini uses 'model' for its responses, not 'assistant' or 'ai'
        role = "user" if msg['sender'] == 'user' else "model"
        contents.append({"role": role, "parts": [{"text": msg['text']}]})

    # Add the current user message
    contents.append({"role": "user", "parts": [{"text": user_message}]})

    try:
        # Use generate_content with the full history
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config={"temperature": 0.7}
        )
        ai_response = response.text
        return jsonify({'response': ai_response})
    except Exception as e:
        # Now we print the actual error if the API key or connection fails
        print(f"Gemini Chatbot Error: {e}") 
        return jsonify({'response': 'Sorry, FitBot is resting right now. Try again later!'}), 500
# --- END CHATBOT ROUTE ---

@ai_workouts_bp.route('/build_workout')
def build_workout():
    if 'user_email' not in session: 
        flash("Please log in to build a workout.")
        return redirect(url_for('auth.login'))
    
    # Pass the static library data to the template
    return render_template('workout_builder.html', exercise_library_data=STATIC_EXERCISE_LIBRARY)

@ai_workouts_bp.route('/save_custom_workout', methods=['POST'])
def save_custom_workout():
    if 'user_email' not in session: return jsonify({'success': False, 'message': 'User not logged in'}), 401
    try:
        workout_details = request.json
        workout_document = {
            'user_email': session['user_email'],
            'plan_type': 'custom',
            'created_on': datetime.now(),
            'workout_session': workout_details
        }
        result = custom_workouts_collection.insert_one(workout_document)
        return jsonify({'success': True, 'message': 'Workout saved successfully!', 'workout_id': str(result.inserted_id)})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to save workout: {e}'}), 500

@ai_workouts_bp.route('/start_custom_workout', methods=['POST'])
def start_custom_workout():
    if 'user_email' not in session: return jsonify({'success': False, 'message': 'Please log in to start a workout.'}), 401
    workout_data = request.json
    if not workout_data: return jsonify({'success': False, 'message': 'No workout data provided'}), 400
    session['current_workout_data'] = workout_data
    return jsonify({'success': True, 'redirect_url': url_for('ai_workouts.start_workout_page')})

@ai_workouts_bp.route('/start_workout_page')
def start_workout_page():
    workout_data = session.pop('current_workout_data', None)
    if workout_data is None:
        flash('No workout to start. Please build one first.', 'error')
        return redirect(url_for('ai_workouts.build_workout'))
    return render_template('start_workout.html', workout_data=workout_data)

@ai_workouts_bp.route('/custom-workout')
def custom_workout():
    return "Custom Workout: Design your own workout plan."