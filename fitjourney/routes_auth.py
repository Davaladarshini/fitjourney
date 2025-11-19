# davaladarshini/fitjourney/fitjourney-91d06a9bed6e94f39b02db2c17256440962f8b46/fitjourney/routes_auth.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from .extensions import users_collection, personal_details_collection, health_issues_collection, gemini_client # Updated import
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

# --- Helper: AI Processing for Health Issues ---
def process_health_issues_with_ai(user_text):
    if not user_text or user_text.strip() == "":
        return []
    
    # System prompt is passed as a content part in Gemini's API
    system_prompt = "You are a medical assistant. Extract specific health conditions from the user's text. Return ONLY a comma-separated list of conditions (e.g., 'Hypertension, Knee Injury'). If none, return 'None'."
    
    try:
        response = gemini_client.models.generate_content( # Updated API call
            model="gemini-2.5-flash", # Using the Gemini model
            contents=[
                {"role": "user", "parts": [
                    {"text": system_prompt},
                    {"text": f"User input: {user_text}"}
                ]}
            ],
            config={"temperature": 0.0}
        )
        ai_summary = response.text # Use .text for the response content
        return ai_summary
    except Exception as e:
        print(f"AI Error: {e}")
        return user_text # Fallback to raw text if AI fails

# ... (rest of the file remains the same)
# --- Routes ---

@auth_bp.route('/')
def index():
    # Landing Page
    return render_template('login.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = users_collection.find_one({'email': email, 'password': password})
        if user:
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            flash(f"Welcome back, {user['name']}!")
            return redirect(url_for('auth.welcome')) 
        else:
            flash("Invalid email or password.")
            return redirect(url_for('auth.login'))
    
    # Actual Login Form
    return render_template('Login2.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        if users_collection.find_one({'email': email}):
            flash('Email already registered.')
            return redirect(url_for('auth.register'))

        # 1. Create Login Entry
        users_collection.insert_one({
            'name': name,
            'email': email,
            'password': password, 
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
        height = float(data['height']) 
        weight = float(data['weight']) 
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

    # Update Personal Details
    personal_details_collection.update_one(
        {'email': email},
        {'$set': {
            'DoB': dob_val,
            'age': age,
            'gender': data['gender'],
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