# davaladarshini/fitjourney/fitjourney-e53c093079553197daf0844b57fee768990dab1a/fitjourney/routes_main.py

from flask import Blueprint, render_template, session, redirect, url_for, request, flash # Added request, flash
from . import stats_calculator 
from .extensions import appointment_requests_collection # NEW Import
from datetime import datetime # NEW Import

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
    stats = stats_calculator.calculate_user_stats(user_email)

    return render_template('statistics.html', 
                           name=session['user_name'], 
                           stats=stats) 

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

# --- NEW APPOINTMENT ROUTES ---
@main_bp.route('/appointments', methods=['GET'])
def appointments():
    if 'user_name' not in session:
        return redirect(url_for('auth.login'))
    return render_template('book_trainer.html')

@main_bp.route('/save_appointment', methods=['POST'])
def save_appointment():
    if 'user_email' not in session:
        flash("You must be logged in to book an appointment.")
        return redirect(url_for('auth.login'))
    
    user_email = session['user_email']
    form_data = request.form
    
    # 1. Create the booking document
    booking_document = {
        'user_email': user_email,
        'trainer_gender': form_data.get('trainer_gender'),
        'focus_area': form_data.get('focus_area'),
        'help_needed': form_data.get('help_needed'),
        'preferred_date': form_data.get('preferred_date'),
        'preferred_time': form_data.get('preferred_time'),
        'communication_method': form_data.get('communication_method'),
        'status': 'pending_review',
        'submitted_at': datetime.now()
    }
    
    # 2. Save to MongoDB
    appointment_requests_collection.insert_one(booking_document)
    
    flash("Appointment request submitted successfully! A trainer will be in touch soon.")
    return redirect(url_for('auth.welcome')) # Redirects to the Dashboard

@main_bp.route('/about_us')
def about_us():
    if 'user_name' not in session:
        return redirect(url_for('auth.login'))
    # This will render the new about_us.html template
    return render_template('about_us.html')