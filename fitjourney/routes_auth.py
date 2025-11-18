from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from .extensions import users_collection, profile_collection
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    return redirect(url_for('auth.login'))

@auth_bp.route('/login2', methods=['GET', 'POST'])
def login2():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        return f"Email: {email}, Password: {password}"
    return render_template('Login2.html')

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
            flash("Invalid email or password. Please try again.")
            return redirect(url_for('auth.login'))
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        if users_collection.find_one({'email': email}):
            flash('Email already registered. Please login.')
            return redirect(url_for('auth.register'))

        users_collection.insert_one({
            'name': name,
            'email': email,
            'password': password,
            'joining_date': datetime.now()
        })
        flash('Registration successful. Please log in.')
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('auth.login'))

@auth_bp.route('/welcome')
def welcome():
    if 'user_name' in session:
        return render_template('welcome.html', name=session['user_name'])
    return redirect(url_for('auth.login'))

@auth_bp.route('/save_profile', methods=['POST'])
def save_profile():
    if 'user_email' not in session:
        flash("Please log in to save your profile.")
        return redirect(url_for('auth.login'))

    data = request.form
    profile_data = {
        'email': session['user_email'],
        'height': int(data['height']),
        'weight': int(data['weight']),
        'age': int(data['age']),
        'gender': data['gender'],
        'bmi': float(data['bmi']) if data['bmi'] else None,
        'health_issues': request.form.getlist('health_issues')
    }
    profile_collection.update_one({'email': session['user_email']}, {'$set': profile_data}, upsert=True)
    flash("Your profile has been saved successfully!")
    return redirect(url_for('auth.welcome'))