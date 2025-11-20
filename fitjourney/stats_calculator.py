# fitjourney/stats_calculator.py

from datetime import datetime, date, timedelta
# FIX: Import the entire extensions module to access updated, initialized collections
from . import extensions 

# --- Helper Function to Calculate User Statistics ---
def calculate_user_stats(user_email):
    """
    Calculates various fitness statistics for the user based on their registration 
    and workout history.
    """
    # Initialize variables
    today = datetime.combine(date.today(), datetime.min.time())
    
    # 1. Journey Started (Registration Date)
    # CRITICAL FIX: Reference the collection via the extensions module
    user_data = extensions.users_collection.find_one({'email': user_email})
    
    # Default to today if user data is missing, but return formatted date if present
    journey_start_date = user_data.get('created_at', today).strftime('%d/%m/%Y') if user_data and user_data.get('created_at') else today.strftime('%d/%m/%Y')
    
    # 2. Workout Sessions & Distribution Setup
    start_of_month = today.replace(day=1)
    monthly_workouts_count = 0
    
    # Simple classification for workout distribution
    workout_types = {'Cardio': 0, 'Strength': 0, 'Yoga': 0}
    workout_dates = set() # Stores dates of completed workouts for streak calculation
    
    # Find all plans for the user (adaptive plans log their completions here)
    # CRITICAL FIX: Reference the collection via the extensions module
    all_plans = extensions.workout_plans_collection.find({'user_email': user_email})
    
    # Process all plan completions (adaptive, goal mapping, custom)
    for plan in all_plans:
        # Determine the primary type hint for the entire plan/goal if feedback doesn't specify
        plan_type_hint = 'Strength' 
        if plan.get('initial_preferences', {}).get('focus_area') == 'cardio':
            plan_type_hint = 'Cardio'
        elif 'yoga' in plan.get('plan_type', ''): 
            plan_type_hint = 'Yoga'
        
        for feedback in plan.get('feedback_history', []):
            if feedback.get('status') == 'completed' and feedback.get('timestamp'):
                ts = feedback['timestamp']
                
                # Monthly Workout Count
                if ts >= start_of_month:
                    monthly_workouts_count += 1
                
                # Workout Dates for Streak
                workout_dates.add(ts.date())
                
                # Workout Distribution Classification
                if plan.get('plan_type') == 'adaptive' and feedback.get('day_index') is not None and plan.get('plan_schedule'):
                    # Use the specific type of the day from the adaptive plan's schedule
                    day_schedule = plan['plan_schedule'][feedback['day_index']]
                    day_type = day_schedule.get('type', 'Strength')
                    if day_type in workout_types:
                        workout_types[day_type] += 1
                    else:
                        workout_types['Strength'] += 1 # Default
                elif plan_type_hint in workout_types:
                    workout_types[plan_type_hint] += 1
                else:
                    workout_types['Strength'] += 1 # Fallback for unknown/custom
                    
    # 3. Current Streak (Consecutive days with a workout)
    current_streak = 0
    check_day = date.today()
    
    while check_day in workout_dates:
        current_streak += 1
        check_day -= timedelta(days=1)
    
    # 4. Mock Milestones/Goals
    milestones_completed = 0

    # 5. Workout Distribution Data for Chart.js (Filter out types with zero count)
    chart_labels = [k for k, v in workout_types.items() if v > 0]
    chart_data = [v for v in workout_types.values() if v > 0]
    
    return {
        'journey_start_date': journey_start_date,
        'current_streak': current_streak,
        'monthly_workouts_count': monthly_workouts_count,
        'milestones_completed': milestones_completed,
        'chart_labels': chart_labels,
        'chart_data': chart_data
    }