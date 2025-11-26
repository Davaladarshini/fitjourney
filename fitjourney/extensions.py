# davaladarshini/fitjourney/fitjourney-91d06a9bed6e94f39b02db2c17256440962f8b46/fitjourney/extensions.py
import os
from pymongo import MongoClient
from google import genai 

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
# NEW GLOBAL VARIABLE

def init_extensions():
    global client, db, users_collection, personal_details_collection, \
           health_issues_collection, workout_history_collection, \
           workout_plans_collection, mood_entries_collection, \
           custom_workouts_collection, gemini_client, appointment_requests_collection # UPDATED global variable

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