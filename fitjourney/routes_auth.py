from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from .extensions import users_collection, personal_details_collection, health_issues_collection, gemini_client
from datetime import datetime
import re
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__)

# --- Helper: AI Processing for Health Issues ---
def process_health_issues_with_ai(user_text):
    if not user_text or user_text.strip() == "":
        return []
    
    # System prompt is passed as a content part in Gemini's API
    system_prompt = "You are a medical assistant. Extract specific health conditions from the user's text. Return ONLY a comma-separated list of conditions (e.g., 'Hypertension, Knee Injury'). If none, return 'None'."
    
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                {"role": "user", "parts": [
                    {"text": system_prompt},
                    {"text": f"User input: {user_text}"}
                ]}
            ],
            config={"temperature": 0.0}
        )
        ai_summary = response.text
        return ai_summary
    except Exception as e:
        print(f"AI Error: {e}")
        return user_text  # Fallback to raw text if AI fails

# --- Routes ---

@auth_bp.route('/')
def index():
    # Landing Page
    return render_template('login.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']

        # Find user by email
        user = users_collection.find_one({'email': email})
        if user and 'password' in user and check_password_hash(user['password'], password):
            session['user_name'] = user.get('name')
            session['user_email'] = user.get('email')
            flash(f"Welcome back, {user.get('name')}!")
            return redirect(url_for('auth.welcome'))
        else:
            flash("Invalid email or password.")
            return redirect(url_for('auth.login'))
    
    # Actual Login Form
    return render_template('Login2.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        # Basic field validation
        if not name or not email or not password:
            flash('Please fill all required fields.', 'danger')
            return render_template('register.html', name=name, email=email)

        # Password policy: lowercase, uppercase, digit, special char, min length 8
        PASSWORD_REGEX = re.compile(
            r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};\'":\\|,.<>\/?]).{8,64}$'
        )
        if not PASSWORD_REGEX.fullmatch(password):
            flash("Password must contain lowercase, uppercase, number, special character and be 8–64 characters long.", "danger")
            return render_template('register.html', name=name, email=email)

        # Check if email already registered
        if users_collection.find_one({'email': email}):
            flash('Email already registered.')
            return redirect(url_for('auth.register'))

        # Hash password before storing
        hashed_password = generate_password_hash(password)

        # 1. Create Login Entry (store hashed password)
        users_collection.insert_one({
            'name': name,
            'email': email,
            'password': hashed_password,
            'created_at': datetime.now()
        })

        # 2. Create Initial Personal Details Entry
        personal_details_collection.insert_one({
            'name': name,
            'email': email,
            'DoB': None,
            'age': None, 
            'gender': None,
            'height': None,
            'weight': None,
            'bmi': None
        })

        flash('Registration successful. Please log in.')
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/welcome')
def welcome():
    if 'user_name' not in session:
        return redirect(url_for('auth.login'))
    
    # Fetch existing data to pre-fill the dashboard
    details = personal_details_collection.find_one({'email': session['user_email']})
    return render_template('welcome.html', name=session['user_name'], user_details=details)

# --- PROFILE ROUTES ---

# 1. VIEW Profile (Read-Only)
@auth_bp.route('/profile')
def profile():
    if 'user_email' not in session:
        return redirect(url_for('auth.login'))
    
    details = personal_details_collection.find_one({'email': session['user_email']})
    health = health_issues_collection.find_one({'email': session['user_email']})
    
    return render_template('profile.html', user_details=details, health_info=health)

# 2. EDIT Profile (The Form)
@auth_bp.route('/edit_profile')
def edit_profile():
    if 'user_email' not in session:
        return redirect(url_for('auth.login'))
    
    details = personal_details_collection.find_one({'email': session['user_email']})
    health = health_issues_collection.find_one({'email': session['user_email']})
    
    return render_template('edit_profile.html', user_details=details, health_info=health)

# 3. SAVE Profile (Updates DB and redirects to View)
@auth_bp.route('/save_profile', methods=['POST'])
def save_profile():
    if 'user_email' not in session:
        return redirect(url_for('auth.login'))

    email = session['user_email']
    data = request.form

    # Calculate BMI
    height = None
    weight = None
    bmi = None
    try:
        height = float(data.get('height')) if data.get('height') else None
        weight = float(data.get('weight')) if data.get('weight') else None
        if height and weight:
            bmi = round(weight / ((height / 100) ** 2), 2)
    except (ValueError, TypeError):
        pass

    # Calculate Age
    age = None
    dob_val = data.get('dob')
    if dob_val:
        try:
            dob_date = datetime.strptime(dob_val, '%Y-%m-%d')
            today = datetime.now()
            age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
        except ValueError:
            pass 

    # --- NEW SERVER-SIDE AGE VALIDATION ---
    MIN_AGE = 10 
    if dob_val and age is not None and age < MIN_AGE:
        # Flash an error and redirect to prevent saving the profile.
        flash(f"You must be at least {MIN_AGE} years old to create a profile. Please provide a valid Date of Birth.", "danger")
        return redirect(url_for('auth.edit_profile'))
    # --- END NEW VALIDATION ---

    # Update Personal Details
    personal_details_collection.update_one(
        {'email': email},
        {'$set': {
            'DoB': dob_val,
            'age': age,
            'gender': data.get('gender'),
            'height': height,
            'weight': weight,
            'bmi': bmi
        }},
        upsert=True
    )

    # Process Health Issues with AI
    raw_health_input = data.get('health_issues_input', '')
    if raw_health_input:
        ai_processed_issues = process_health_issues_with_ai(raw_health_input)
        
        health_issues_collection.update_one(
            {'email': email},
            {'$set': {
                'raw_input': raw_health_input,
                'ai_processed_issues': ai_processed_issues,
                'last_updated': datetime.now()
            }},
            upsert=True
        )

    flash("Profile updated successfully!")
    return redirect(url_for('auth.profile'))