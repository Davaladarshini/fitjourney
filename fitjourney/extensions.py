import os
from pymongo import MongoClient
from openai import OpenAI

# Global variables for extensions
client = None
db = None
users_collection = None
profile_collection = None
mood_entries_collection = None
workout_plans_collection = None
custom_workouts_collection = None
openai_client = None

def init_extensions():
    global client, db, users_collection, profile_collection, mood_entries_collection, workout_plans_collection, custom_workouts_collection, openai_client

    # MongoDB Connection
    client = MongoClient(os.getenv('MONGO_URI', "mongodb://localhost:27017/"))
    db = client["user_db"]

    # Collections
    users_collection = db["users"]
    profile_collection = db['profiles']
    mood_entries_collection = db["mood_entries"]
    workout_plans_collection = db["workout_plans"]
    custom_workouts_collection = db["custom_workouts"]

    # OpenAI Client
    openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))