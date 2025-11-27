from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from .extensions import mood_entries_collection, gemini_client
from textblob import TextBlob
from datetime import datetime

mindfulness_bp = Blueprint('mindfulness', __name__)

# --- Breathing Patterns Data ---
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

# --- Helper Function ---
def analyze_mood_sentiment(text):
    """Analyzes text to determine if it's Positive, Negative, or Neutral."""
    if not text: 
        return "N/A"
    try:
        analysis = TextBlob(text)
        if analysis.sentiment.polarity > 0: return "Positive"
        elif analysis.sentiment.polarity < 0: return "Negative"
        else: return "Neutral"
    except:
        return "N/A"

# --- Routes ---

@mindfulness_bp.route('/get-breathing-pattern', methods=['POST'])
def get_breathing_pattern():
    data = request.get_json()
    pattern_name = data.get('pattern', 'box')
    pattern = BREATHING_PATTERNS.get(pattern_name)
    if pattern:
        return jsonify(pattern)
    else:
        return jsonify({'error': 'Pattern not found'}), 400

@mindfulness_bp.route('/meditation-options')
def meditation_options():
    return render_template('meditation-options.html')

@mindfulness_bp.route('/guided-meditation')
def guided_meditation():
    return render_template('guided_meditation.html')

@mindfulness_bp.route('/breathing-visualizer')
def breathing_visualizer():
    return render_template('breathing_visualizer.html')

@mindfulness_bp.route('/track-mood', methods=['GET'])
def track_mood_form():
    # LOGIN CHECK REMOVED: Now accessible to everyone
    return render_template('mood_tracker.html')

@mindfulness_bp.route('/save-mood', methods=['POST'])
def save_mood():
    # LOGIN CHECK REMOVED: Now accessible to everyone
    
    # Check if user is logged in (optional)
    user_email = session.get('user_email')
    user_name = session.get('user_name', 'Friend') # Default to 'Friend' if not logged in
    
    mood_rating = request.form.get('mood_rating')
    mood_notes = request.form.get('mood_notes', '')

    if not mood_rating:
        flash("Please tell us how you're feeling.")
        return redirect(url_for('mindfulness.track_mood_form'))

    # 1. Calculate Sentiment
    sentiment_score = analyze_mood_sentiment(mood_notes)

    # 2. Save Entry to Database (ONLY IF LOGGED IN)
    if user_email:
        mood_entry = {
            'user_email': user_email,
            'mood_rating': int(mood_rating),
            'mood_notes': mood_notes,
            'sentiment_score': sentiment_score,
            'timestamp': datetime.now()
        }
        mood_entries_collection.insert_one(mood_entry)

    # 3. Generate AI Friend Response (Gemini)
    mood_labels = {
        1: "Having a rough day", 
        2: "Feeling a bit low", 
        3: "Just okay", 
        4: "Feeling good", 
        5: "Feeling amazing"
    }
    current_mood_label = mood_labels.get(int(mood_rating), "Unknown")
    
    ai_message = f"Thanks for sharing, {user_name}. Remember, I'm here whenever you need to talk." 
    
    try:
        # The "FitBot" Friend Persona
        system_prompt = f"""
        You are FitBot, a warm, empathetic, and supportive best friend. 
        Your friend, {user_name}, just told you they are: {current_mood_label} (Rating: {mood_rating}/5).
        They said: "{mood_notes}"
        
        Task: Reply as a supportive friend to {user_name}. 
        1. Address them by name ({user_name}) naturally in the conversation.
        2. Validate their feelings immediately.
        3. If they are sad/low: Offer comfort and maybe a small, easy suggestion (like drinking tea, taking a nap, or a specific breathing exercise).
        4. If they are happy: Be excited for them!
        5. Keep it short, conversational, and caring (under 60 words). Do NOT sound like a robot or doctor.
        """
        
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[{"role": "user", "parts": [{"text": system_prompt}]}]
        )
        ai_message = response.text
    except Exception as e:
        print(f"Gemini API Error: {e}")

    # 4. Render the "Chat Reply" Page
    return render_template('mood_response.html', 
                           message=ai_message, 
                           mood=current_mood_label,
                           rating=mood_rating)

@mindfulness_bp.route('/mood-history', methods=['GET'])
def mood_history():
    # History still requires login because it's personal data
    if 'user_email' not in session:
        flash("Please log in to view your history.")
        return redirect(url_for('auth.login'))

    user_email = session['user_email']
    moods = list(mood_entries_collection.find({'user_email': user_email}).sort('timestamp', -1))

    avg_mood = "N/A"
    if moods:
        total_rating = sum(m['mood_rating'] for m in moods if 'mood_rating' in m)
        if len(moods) > 0:
            avg_mood = round(total_rating / len(moods), 2)

    return render_template('mood_history.html', moods=moods, avg_mood=avg_mood)