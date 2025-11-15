# breathing_patterns.py

from flask import Blueprint, jsonify, request

# This defines breathing_bp (Blueprint for routes related to breathing)
breathing_bp = Blueprint('breathing', __name__) 

# Define your breathing patterns
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

# Define the route within the Blueprint
@breathing_bp.route('/get-breathing-pattern', methods=['POST'])
def get_breathing_pattern():
    """
    API endpoint to fetch a specific breathing pattern.
    Expects a JSON payload with 'pattern' key.
    """
    data = request.get_json()
    pattern_name = data.get('pattern', 'box') # Default to 'box' if no pattern specified

    # In a real application, you might fetch user preferences from a database here
    # user_id = session.get('user_id') # You'd need to pass session context or fetch user here
    # user = User.query.get(user_id)
    # if user and user.preferred_pattern:
    #    pattern_name = user.preferred_pattern

    pattern = BREATHING_PATTERNS.get(pattern_name)
    if pattern:
        return jsonify(pattern)
    else:
        return jsonify({'error': 'Pattern not found'}), 400
