# webcam_stream.py - Collection of shared utilities
import numpy as np
import mediapipe as mp

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

# Configuration
MIN_DETECTION_CONFIDENCE = 0.5 
MIN_TRACKING_CONFIDENCE = 0.5 

# Global State Placeholder
LATEST_FEEDBACK = {} 

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