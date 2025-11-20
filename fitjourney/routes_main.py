# davaladarshini/fitjourney/fitjourney-e53c093079553197daf0844b57fee768990dab1a/fitjourney/routes_main.py

from flask import Blueprint, render_template, session, redirect, url_for
from . import stats_calculator # Import the new stats module

main_bp = Blueprint('main', __name__)

@main_bp.route('/dashboard')
def dashboard():
    if 'user_name' not in session:
        return redirect(url_for('auth.login'))
    return render_template('welcome.html', name=session['user_name']) 

@main_bp.route('/statistics')
def statistics():
    if 'user_name' not in session:
        return redirect(url_for('auth.login'))
        
    user_email = session['user_email']
    # Call the calculation function from the separate file
    stats = stats_calculator.calculate_user_stats(user_email)

    return render_template('statistics.html', 
                           name=session['user_name'], 
                           stats=stats) # Pass the dynamic data

@main_bp.route('/workouts')
def workouts():
    if 'user_name' not in session:
        return redirect(url_for('auth.login'))
    user_name = session.get('user_name', 'Guest')
    return render_template('workouts.html', name=user_name)

@main_bp.route('/workout_options')
def workout_options():
    if 'user_name' not in session:
        return redirect(url_for('auth.login'))
    return render_template('workout_options.html')