# webcam_stream.py - Reverted to Stable Detection (Fixed-Angle Logic)

import cv2
import time
import mediapipe as mp
import numpy as np 
import sys 
import json 
# webcam_stream.py - Now a collection of shared utilities.

import numpy as np 
# Keep mediapipe imports if they are needed for constants in the other files.
import mediapipe as mp 
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

# --- CONFIGURATION (Keep these if other files reference them) ---
MIN_DETECTION_CONFIDENCE = 0.5 
MIN_TRACKING_CONFIDENCE = 0.5 

# --- GLOBAL STATE for Real-Time Communication (TTS and Frontend ready) ---
# NOTE: LATEST_FEEDBACK, SMOOTHED_ANGLES, REFERENCE_ANGLES 
# are no longer used here, but keeping them as empty dictionaries for now 
# in case other parts of the system rely on importing them.
LATEST_FEEDBACK = {} 
SMOOTHED_ANGLES = {} 
REFERENCE_ANGLES = {} 

# --- TARGET POSE DATA DEFINITION (REMOVED: Now in individual exercise files) ---
# The large TARGET_POSE_DATA dictionary from the original file is removed here.

# --- HELPER FUNCTIONS ---
# Keep the helper function to be imported by app.py or others.
def get_target_pose_data(exercise_name):
    # This function is now redundant or needs to be adapted to look up data in app.py's ALL_EXERCISES
    # For now, it is safe to keep it stubbed or removed if unused, but removing it might break other parts.
    # Since app.py now uses EXERCISE_DISPATCHER, we will remove the redundant TARGET_POSE_DATA and 
    # keep the function definition as a stub in case any other file still imports it.
    print("Warning: get_target_pose_data in webcam_stream.py is a stub and should be removed if unused.")
    return None 

def calculate_angle(a, b, c):
    """Calculates the 2D angle (in degrees) between three points (a, b, c)."""
    a = np.array(a) 
    b = np.array(b) 
    c = np.array(c) 
    
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    
    if angle > 180.0:
        angle = 360 - angle
        
    return round(angle, 2)

# --- MAIN FRAME GENERATION FUNCTION (REMOVED: Now in individual exercise files) ---
# The generate_frames function from the original file is removed here.


# --- MAIN EXECUTION BLOCK (For local testing only) ---
# Removed the __name__ == '__main__' block as it depends on generate_frames.
# A small modification to keep it functional for console output if needed.
if __name__ == '__main__':
    # Add a print statement to indicate this is a utility file now.
    print("webcam_stream.py is now a utility file and should be run via the Flask app (app.py).")