import os
from flask import Blueprint, render_template, session, redirect, url_for, request, flash 
from . import stats_calculator 
from .extensions import appointment_requests_collection, mail 
from datetime import datetime 
from flask_mail import Message 
import logging 

main_bp = Blueprint('main', __name__)

# --- CONFIGURATION CONSTANT ---
# IMPORTANT: Replace this with the actual Gmail address you want to receive notifications at.
TRAINER_EMAIL_ADDRESS = 'jamforbusinesss@gmail.com' 

# UPDATED HELPER FUNCTION: Sends a real email using Flask-Mail.
def send_booking_notification(recipient_email, user_name, booking_details, is_trainer_notification=False):
    """
    Sends a real email using Flask-Mail for the trainer notification.
    """
    if is_trainer_notification:
        subject = f"ACTION REQUIRED: New Trainer Booking from {user_name}"
        body = f"""
ACTION REQUIRED: A new client has requested an appointment. Please review the details below and contact them to finalize the booking.

Client Name: {user_name}
Client Email: {booking_details['user_email']}
Focus Area: {booking_details['focus_area']}
Preferred Trainer Gender: {booking_details['trainer_gender']}
Preferred Date/Time: {booking_details['preferred_date']} at {booking_details['preferred_time']}
Communication Method: {booking_details['communication_method']}
Specific Help Needed: {booking_details['help_needed'] or 'None'}

Please follow up with the client promptly.
"""
    else:
        # We only send the trainer notification, so this path is not taken.
        return False 

    try:
        msg = Message(
            subject=subject, 
            # Sender is set globally in extensions.py config
            sender=os.getenv('MAIL_USERNAME'), 
            recipients=[recipient_email] 
        )
        msg.body = body
        mail.send(msg) # <<< REAL EMAIL SENDING
        logging.warning(f"--- REAL EMAIL SENT SUCCESSFULLY to {recipient_email} ---")
        return True
    except Exception as e:
        logging.error(f"Failed to send real email via Flask-Mail to {recipient_email}: {e}")
        # Flash an error to the user if the notification fails
        flash(f"Warning: Trainer notification failed to send due to a mail server error. Please check your credentials. Error: {e}", "error")
        return False 

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

# --- APPOINTMENT ROUTES ---
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
    user_name = session.get('user_name', 'FITJourney User') 
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
    
    # 3. Send Email Notification to TRAINER (Action Required)
    send_booking_notification(
        recipient_email=TRAINER_EMAIL_ADDRESS,
        user_name=user_name,
        booking_details=booking_document,
        is_trainer_notification=True
    )

    flash("Appointment request submitted successfully! A trainer has been notified and will contact you shortly.")
    return redirect(url_for('auth.welcome'))

@main_bp.route('/about_us')
def about_us():
    if 'user_name' not in session:
        return redirect(url_for('auth.login'))
    return render_template('about_us.html')