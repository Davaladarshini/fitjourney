import os
from pymongo import MongoClient
from openai import OpenAI

# Global variables
client = None
db = None
users_collection = None
personal_details_collection = None
health_issues_collection = None
workout_history_collection = None
workout_plans_collection = None
mood_entries_collection = None      # Added back
custom_workouts_collection = None   # Added back
openai_client = None

def init_extensions():
    global client, db, users_collection, personal_details_collection, \
           health_issues_collection, workout_history_collection, \
           workout_plans_collection, mood_entries_collection, \
           custom_workouts_collection, openai_client

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

    # 3. Initialize OpenAI
    openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))