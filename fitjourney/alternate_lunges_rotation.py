import cv2
import mediapipe as mp
import numpy as np
import json

# Initialize MediaPipe Pose Model (Required in every file)
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

# --- CONFIGURATION ---
MIN_DETECTION_CONFIDENCE = 0.5 
MIN_TRACKING_CONFIDENCE = 0.5 
EXERCISE_KEY = 'alternate_lunges_rotation'

# --- TARGET DATA for Alternate Lunge with Rotation ---
TARGET_DATA = {
    # --- Joints to Measure ---
    'measure_joints': {
        # Knee Angle (L/R): Hip - KNEE (V) - Ankle (2D)
        'knee_L': (mp_pose.PoseLandmark.LEFT_HIP.value, mp_pose.PoseLandmark.LEFT_KNEE.value, mp_pose.PoseLandmark.LEFT_ANKLE.value),
        'knee_R': (mp_pose.PoseLandmark.RIGHT_HIP.value, mp_pose.PoseLandmark.RIGHT_KNEE.value, mp_pose.PoseLandmark.RIGHT_ANKLE.value),
        # Hip Angle (L/R): Shoulder - HIP (V) - Knee (3D)
        'hip_L': (mp_pose.PoseLandmark.LEFT_SHOULDER.value, mp_pose.PoseLandmark.LEFT_HIP.value, mp_pose.PoseLandmark.LEFT_KNEE.value),
        'hip_R': (mp_pose.PoseLandmark.RIGHT_SHOULDER.value, mp_pose.PoseLandmark.RIGHT_HIP.value, mp_pose.PoseLandmark.RIGHT_KNEE.value),
        # Ankle Angle (L/R): Knee - ANKLE (V) - Heel (2D)
        'ankle_L': (mp_pose.PoseLandmark.LEFT_KNEE.value, mp_pose.PoseLandmark.LEFT_ANKLE.value, mp_pose.PoseLandmark.LEFT_HEEL.value),
        'ankle_R': (mp_pose.PoseLandmark.RIGHT_KNEE.value, mp_pose.PoseLandmark.RIGHT_ANKLE.value, mp_pose.PoseLandmark.RIGHT_HEEL.value),
        # Torso Misalignment (Rotation proxy): Angle between Shoulder Line and Hip Line (3D)
        'torso_misalignment': (mp_pose.PoseLandmark.LEFT_SHOULDER.value, mp_pose.PoseLandmark.RIGHT_SHOULDER.value, 
                               mp_pose.PoseLandmark.LEFT_HIP.value, mp_pose.PoseLandmark.RIGHT_HIP.value),
        # Torso Lean: Angle of R-Shoulder -> R-Hip line relative to Vertical (2D)
        'torso_lean': (mp_pose.PoseLandmark.RIGHT_SHOULDER.value, mp_pose.PoseLandmark.RIGHT_HIP.value),
    },
    # --- Rep Boundaries and Feedback Thresholds ---
    'angle_thresholds': {
        # Rep Counting Thresholds (Down)
        'front_knee_down': 90,
        'back_knee_down': 130,
        'hip_down': 90,
        'rotation_down': 20, # Misalignment angle > 20 (assuming this represents rotation)
        # Rep Counting Thresholds (Up)
        'front_knee_up': 150,
        'back_knee_up': 150,
        'rotation_up': 10,  # Misalignment angle < 10 (hips/shoulders square)
        'hip_up': 140,
        # Feedback thresholds
        'front_knee_depth': 100, # Front knee > 100 -> Go deeper
        'back_knee_depth': 150, # Back knee > 150 -> Bend back knee more
        'hip_diff_max': 25,     # abs(front_hip - back_hip) > 25 -> Keep hips square
        'rotation_min': 20,     # Rotation < 20 in DOWN state -> Rotate more
        'rotation_max': 50,     # Rotation > 50 -> Reduce rotation
        'torso_lean_forward': 40, # Torso lean > 40 -> Keep chest upright
        'torso_lean_backward': -10, # Torso lean < -10 -> Don't lean backward
        'knee_diff_max': 20,    # abs(L_knee - R_knee) > 20 -> Align knees
        'ankle_stability_min': 70 # Ankle < 70 -> Keep foot stable
    }
}

# --- GLOBAL STATE (Unique to this file, required for Flask API Polling) ---
LATEST_FEEDBACK = {
    'feedback': ['Initializing...'], 
    'reps': 0, 
    'state': 'up', # FSM state: 'up' or 'down'
    # Track all required angles
    'knee_L': 0.0, 'knee_R': 0.0, 
    'hip_L': 0.0, 'hip_R': 0.0,
    'ankle_L': 0.0, 'ankle_R': 0.0,
    'rotation': 0.0, 'lean': 0.0,
    'front_leg': 'N/A'
}

# --- Utility Functions (Including 3D and Custom Angles) ---

def calculate_angle_2d(a, b, c):
    """Calculates the 2D angle (in degrees) between three points (a, b, c). Suitable for Knee/Ankle."""
    a = np.array(a); b = np.array(b); c = np.array(c) 
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0: angle = 360 - angle
    return round(angle, 2)

def calculate_angle_3d(a, b, c):
    """Calculates the 3D angle (in degrees) between three points (a, b, c). Better for Hip/Shoulder."""
    a = np.array(a); b = np.array(b); c = np.array(c)
    ba = a - b; bc = c - b
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
    angle = np.arccos(cosine_angle)
    return round(np.degrees(angle), 2)

def calculate_torso_lean_angle(shoulder, hip):
    """Calculates the 2D angle of the torso (Shoulder-Hip line) relative to the vertical (Y-axis)."""
    p1 = np.array(shoulder); p2 = np.array(hip)
    torso_vector = p1 - p2 # Vector pointing up
    vertical_vector = np.array([0, -1]) 
    dot_product = np.dot(torso_vector[:2], vertical_vector)
    magnitude_product = np.linalg.norm(torso_vector[:2]) * np.linalg.norm(vertical_vector)
    
    if magnitude_product == 0: return 0.0
    
    angle = np.degrees(np.arccos(np.clip(dot_product / magnitude_product, -1.0, 1.0)))
    return round(angle, 2)


def calculate_torso_misalignment_angle(sl, sr, hl, hr):
    """Calculates the 3D angle (in degrees) between the shoulder line (SL->SR) and the hip line (HL->HR).
       0 degrees means hips and shoulders are perfectly square."""
    sl = np.array(sl); sr = np.array(sr); hl = np.array(hl); hr = np.array(hr)
    shoulder_vector = sr - sl 
    hip_vector = hr - hl 

    dot_product = np.dot(shoulder_vector, hip_vector)
    magnitude_product = np.linalg.norm(shoulder_vector) * np.linalg.norm(hip_vector)
    
    if magnitude_product == 0: return 0.0
    
    cosine_angle = dot_product / magnitude_product
    cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
    angle = np.arccos(cosine_angle)
    return round(np.degrees(angle), 2) 

# --- MAIN GENERATOR FUNCTION ---
def generate_frames_lunge_rotation():
    """Generates frames specifically for the Alternate Lunges with Rotation analysis."""
    
    # Initialize variables from the current global state of this file
    rep_count = LATEST_FEEDBACK['reps']; current_state = LATEST_FEEDBACK['state']
    
    # --- CAMERA INITIALIZATION (IMPROVED RELIABILITY) ---
    # Try multiple backends (CAP_DSHOW for Windows, CAP_ANY for general) or different indices
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW) 
    
    if not camera.isOpened():
        # Fallback 1: Try without a specific backend
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            # Fallback 2: Try index 1
            camera = cv2.VideoCapture(1)
            
    if not camera.isOpened(): 
        LATEST_FEEDBACK['feedback'] = ["FATAL ERROR: Camera could not be opened. Check drivers, permissions, and ensure no other application is using the camera."]; 
        return 
    
    # Set camera properties
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640); camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480); camera.set(cv2.CAP_PROP_FPS, 60)
    # ---------------------------------------------------
    
    with mp_pose.Pose(min_detection_confidence=MIN_DETECTION_CONFIDENCE, min_tracking_confidence=MIN_TRACKING_CONFIDENCE) as pose:
        while True:
            success, frame = camera.read(); 
            if not success: break
            frame = cv2.flip(frame, 1); frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB); frame_rgb.flags.writeable = False
            results = pose.process(frame_rgb); frame_rgb.flags.writeable = True
            frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            
            feedback_list = []; rep_counted = False
            thresholds = TARGET_DATA['angle_thresholds']
            score_color = (0, 255, 255) # Yellow/Cyan default
            angles = LATEST_FEEDBACK.copy() # Use a local copy to update angles before setting global state

            if results.pose_landmarks:
                try:
                    landmarks = results.pose_landmarks.landmark
                    
                    # Helper functions for landmarks
                    def get_coords_2d(idx): return [landmarks[idx].x, landmarks[idx].y]
                    def get_coords_3d(idx): return [landmarks[idx].x, landmarks[idx].y, landmarks[idx].z]

                    # 1. CALCULATE ALL BASE ANGLES
                    # Knee Angles
                    j_L = TARGET_DATA['measure_joints']['knee_L']; angles['knee_L'] = calculate_angle_2d(get_coords_2d(j_L[0]), get_coords_2d(j_L[1]), get_coords_2d(j_L[2]))
                    j_R = TARGET_DATA['measure_joints']['knee_R']; angles['knee_R'] = calculate_angle_2d(get_coords_2d(j_R[0]), get_coords_2d(j_R[1]), get_coords_2d(j_R[2]))
                    
                    # Hip Angles
                    j_hL = TARGET_DATA['measure_joints']['hip_L']; angles['hip_L'] = calculate_angle_3d(get_coords_3d(j_hL[0]), get_coords_3d(j_hL[1]), get_coords_3d(j_hL[2]))
                    j_hR = TARGET_DATA['measure_joints']['hip_R']; angles['hip_R'] = calculate_angle_3d(get_coords_3d(j_hR[0]), get_coords_3d(j_hR[1]), get_coords_3d(j_hR[2]))

                    # Ankle Angles
                    j_aL = TARGET_DATA['measure_joints']['ankle_L']; angles['ankle_L'] = calculate_angle_2d(get_coords_2d(j_aL[0]), get_coords_2d(j_aL[1]), get_coords_2d(j_aL[2]))
                    j_aR = TARGET_DATA['measure_joints']['ankle_R']; angles['ankle_R'] = calculate_angle_2d(get_coords_2d(j_aR[0]), get_coords_2d(j_aR[1]), get_coords_2d(j_aR[2]))
                    
                    # Torso Lean Angle
                    j_tL = TARGET_DATA['measure_joints']['torso_lean']; angles['lean'] = calculate_torso_lean_angle(get_coords_2d(j_tL[0]), get_coords_2d(j_tL[1]))

                    # Torso Misalignment Angle (Rotation Proxy)
                    j_rot = TARGET_DATA['measure_joints']['torso_misalignment']
                    sl = get_coords_3d(j_rot[0]); sr = get_coords_3d(j_rot[1]); hl = get_coords_3d(j_rot[2]); hr = get_coords_3d(j_rot[3])
                    angles['rotation'] = calculate_torso_misalignment_angle(sl, sr, hl, hr)

                    
                    # 2. DYNAMICALLY IDENTIFY FRONT/BACK LEG
                    # The front leg has the smallest knee angle (most bent) when lunging
                    if angles['knee_L'] < angles['knee_R']:
                        is_left_front = True
                        angles['front_leg'] = 'LEFT'
                        front_knee = angles['knee_L']; back_knee = angles['knee_R']
                        front_hip = angles['hip_L']; back_hip = angles['hip_R']
                        front_ankle = angles['ankle_L']; back_ankle = angles['ankle_R']
                    else:
                        is_left_front = False
                        angles['front_leg'] = 'RIGHT'
                        front_knee = angles['knee_R']; back_knee = angles['knee_L']
                        front_hip = angles['hip_R']; back_hip = angles['hip_L']
                        front_ankle = angles['ankle_R']; back_ankle = angles['ankle_L']
                        
                    # 3. REP COUNTING LOGIC (FSM: up -> down -> up)
                    
                    # Down detection
                    is_down_position = (front_knee < thresholds['front_knee_down'] and 
                                        back_knee < thresholds['back_knee_down'] and 
                                        angles['rotation'] > thresholds['rotation_down']) # Rotation check
                    
                    if is_down_position:
                        current_state = 'down'
                        score_color = (0, 255, 255) # Yellow/Cyan for bottom hold

                    # Up detection (Count Rep)
                    is_up_position = (front_knee > thresholds['front_knee_up'] and 
                                      back_knee > thresholds['back_knee_up'] and 
                                      angles['rotation'] < thresholds['rotation_up']) # Return to squared (Rotation < 10)

                    if current_state == 'down' and is_up_position:
                        rep_count += 1
                        current_state = 'up'
                        rep_counted = True
                        score_color = (0, 255, 0) # Green for Rep Completion
                    

                    # 4. DETAILED FEEDBACK LOGIC
                    
                    # A. Squat depth feedback
                    if front_knee > thresholds['front_knee_depth'] and current_state == 'up':
                        feedback_list.append(f"Go deeper on your front ({angles['front_leg']}) knee")
                        score_color = (0, 0, 255) # Red for form error

                    if back_knee > thresholds['back_knee_depth'] and current_state == 'down':
                        feedback_list.append("Bend your back knee more")
                        score_color = (0, 0, 255) # Red for form error
                        
                    # B. Torso rotation feedback
                    if angles['rotation'] < thresholds['rotation_min'] and current_state == 'down':
                        feedback_list.append("Rotate your torso more toward your front leg")
                        score_color = (0, 0, 255) 
                    
                    if angles['rotation'] > thresholds['rotation_max']:
                        feedback_list.append("Reduce torso rotation to avoid strain")
                        score_color = (0, 0, 255) 

                    # C. Torso lean (spine angle)
                    if angles['lean'] > thresholds['torso_lean_forward']:
                        feedback_list.append("Keep your chest more upright")
                        score_color = (0, 0, 255) 
                    
                    # D. Knee alignment left vs right
                    if abs(angles['knee_L'] - angles['knee_R']) > thresholds['knee_diff_max']:
                        feedback_list.append("Align your knees better (side view)")
                        score_color = (0, 0, 255) 
                        
                    # E. Hip alignment (using the hip difference as a proxy for squaring)
                    if abs(front_hip - back_hip) > thresholds['hip_diff_max']:
                        feedback_list.append("Keep your hips square")
                        score_color = (0, 0, 255)
                        
                    # F. Foot (ankle) stability (Front foot only)
                    if front_ankle < thresholds['ankle_stability_min']:
                        feedback_list.append("Keep your front foot stable and flat")
                        score_color = (0, 0, 255)

                    # Default State Feedback
                    if not feedback_list:
                        if rep_counted:
                             feedback_list.append(f"REP {rep_count}. Good lunge and rotation!")
                        elif current_state == 'down':
                             feedback_list.append("Bottom achieved. Drive up and unsquare torso!")
                        else:
                             feedback_list.append("Ready to Lunge! Step forward and rotate.")


                    # DRAW LANDMARKS (Uses the color determined by the feedback loop)
                    mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=score_color, thickness=3, circle_radius=6),
                        mp_drawing.DrawingSpec(color=(0, 255, 255), thickness=2, circle_radius=2))
                        
                except Exception as e:
                    print(f"Tracking error: {e}")
                    feedback_list = ["Tracking Error. Check joint visibility."]; current_state = 'ERROR'

            else:
                feedback_list = ["No Pose Detected. Step back or adjust camera."]; current_state = 'WAIT'
            
            # Update GLOBAL FEEDBACK STATE
            LATEST_FEEDBACK['feedback'] = feedback_list; 
            LATEST_FEEDBACK['reps'] = rep_count; 
            LATEST_FEEDBACK['state'] = current_state; 
            
            # Update all angles in global state
            LATEST_FEEDBACK.update(angles)

            
            ret, buffer = cv2.imencode('.jpg', frame); 
            yield (b'--frame\r\n' + b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\r\n')
        
        camera.release(); cv2.destroyAllWindows()

# --- Utility to get latest feedback state for a separate API endpoint ---
def get_latest_feedback_lunge_rotation():
    return json.dumps(LATEST_FEEDBACK)