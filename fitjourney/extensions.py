# davaladarshini/fitjourney/fitjourney-91d06a9bed6e94f39b02db2c17256440962f8b46/fitjourney/extensions.py
import os
from pymongo import MongoClient
from google import genai 
from flask_mail import Mail # <<< NEW: Import Flask-Mail

# Global variables
client = None
db = None
users_collection = None
personal_details_collection = None
health_issues_collection = None
workout_history_collection = None
workout_plans_collection = None
mood_entries_collection = None      
custom_workouts_collection = None   
gemini_client = None 
appointment_requests_collection = None 
mail = None # <<< NEW: Global Mail object for Flask-Mail

# MODIFIED: Now accepts the Flask application instance 'app'
def init_extensions(app): 
    global client, db, users_collection, personal_details_collection, \
           health_issues_collection, workout_history_collection, \
           workout_plans_collection, mood_entries_collection, \
           custom_workouts_collection, gemini_client, appointment_requests_collection, \
           mail # <<< UPDATED: Add mail to global list

    # 1. Connect to MongoDB Atlas
    client = MongoClient(os.getenv('MONGO_URI'))
    db = client["fitjourney_db"]

    # 2. Define Collections
    users_collection = db["users"]
    personal_details_collection = db["personal_details"]
    health_issues_collection = db["health_issues"]
    workout_history_collection = db["workout_history"]
    workout_plans_collection = db["workout_plans"]
    
    # Restored collections to prevent ImportErrors
    mood_entries_collection = db["mood_entries"]
    custom_workouts_collection = db["custom_workouts"]
  
    
    # NEW Collection for appointments
    appointment_requests_collection = db["appointment_requests"]

    # 3. Initialize Gemini Client
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY") 
    gemini_client = genai.Client(api_key=api_key)
    
    # 4. Initialize Flask-Mail (NEW CONFIGURATION)
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME') # Reads from .env
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD') # Reads from .env (your App Password)
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME') # The address the email comes from
    
    mail = Mail(app) # Initialize mail with the Flask app