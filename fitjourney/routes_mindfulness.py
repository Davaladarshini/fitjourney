from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from .extensions import mood_entries_collection
from textblob import TextBlob
from datetime import datetime

mindfulness_bp = Blueprint('mindfulness', __name__)

# --- Breathing Patterns Logic ---
BREATHING_PATTERNS = {
    'box': [
        {'text': 'Inhale', 'duration': 4, 'className': 'expand'},
        {'text': 'Hold', 'duration': 4, 'className': 'hold'},
        {'text': 'Exhale', 'duration': 4, 'className': 'contract'},
        {'text': 'Hold', 'duration': 4, 'className': 'hold'}
    ],
    '4-7-8': [
        {'text': 'Inhale', 'duration': 4, 'className': 'expand'},
        {'text': 'Hold', 'duration': 7, 'className': 'hold'},
        {'text': 'Exhale', 'duration': 8, 'className': 'contract'}
    ],
    'energizer': [
        {'text': 'Inhale', 'duration': 3, 'className': 'expand'},
        {'text': 'Hold', 'duration': 1, 'className': 'hold'},
        {'text': 'Exhale', 'duration': 6, 'className': 'contract'}
    ],
    'calming': [
        {'text': 'Inhale', 'duration': 5, 'className': 'expand'},
        {'text': 'Hold', 'duration': 5, 'className': 'hold'},
        {'text': 'Exhale', 'duration': 5, 'className': 'contract'},
        {'text': 'Hold', 'duration': 5, 'className': 'hold'}
    ]
}

@mindfulness_bp.route('/get-breathing-pattern', methods=['POST'])
def get_breathing_pattern():
    data = request.get_json()
    pattern_name = data.get('pattern', 'box')
    pattern = BREATHING_PATTERNS.get(pattern_name)
    if pattern:
        return jsonify(pattern)
    else:
        return jsonify({'error': 'Pattern not found'}), 400

# --- Mindfulness Routes ---

@mindfulness_bp.route('/meditation-options')
def meditation_options():
    return render_template('meditation-options.html')

@mindfulness_bp.route('/guided-meditation')
def guided_meditation():
    return render_template('guided_meditation.html')

@mindfulness_bp.route('/breathing-visualizer')
def breathing_visualizer():
    return render_template('breathing_visualizer.html')

# --- Mood Tracking Routes ---

def analyze_mood_sentiment(text):
    analysis = TextBlob(text)
    if analysis.sentiment.polarity > 0: return "Positive"
    elif analysis.sentiment.polarity < 0: return "Negative"
    else: return "Neutral"

@mindfulness_bp.route('/track-mood', methods=['GET'])
def track_mood_form():
    if 'user_email' not in session: 
        flash("Please log in to track your mood.")
        return redirect(url_for('auth.login'))
    return render_template('mood_tracker.html')

@mindfulness_bp.route('/save-mood', methods=['POST'])
def save_mood():
    if 'user_email' not in session:
        flash("Please log in to save your mood.")
        return redirect(url_for('auth.login'))
    
    user_email = session['user_email']
    mood_rating = request.form.get('mood_rating')
    mood_notes = request.form.get('mood_notes', '')

    if not mood_rating:
        flash("Please select a mood rating.")
        return redirect(url_for('mindfulness.track_mood_form'))

    sentiment_score = None
    if mood_notes:
        try:
            sentiment_score = analyze_mood_sentiment(mood_notes)
        except Exception as e:
            print(f"Error during sentiment analysis: {e}")
            sentiment_score = "N/A"

    mood_entry = {
        'user_email': user_email,
        'mood_rating': int(mood_rating),
        'mood_notes': mood_notes,
        'sentiment_score': sentiment_score,
        'timestamp': datetime.now()
    }

    mood_entries_collection.insert_one(mood_entry)
    flash("Your mood has been logged successfully!")
    return redirect(url_for('mindfulness.mood_history'))

@mindfulness_bp.route('/mood-history', methods=['GET'])
def mood_history():
    if 'user_email' not in session:
        flash("Please log in to view your mood history.")
        return redirect(url_for('auth.login'))

    user_email = session['user_email']
    moods = list(mood_entries_collection.find({'user_email': user_email}).sort('timestamp', -1))

    avg_mood = "N/A"
    if moods:
        total_rating = sum(m['mood_rating'] for m in moods if 'mood_rating' in m)
        if moods:
            avg_mood = round(total_rating / len(moods), 2)

    return render_template('mood_history.html', moods=moods, avg_mood=avg_mood)