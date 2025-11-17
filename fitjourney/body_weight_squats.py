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
EXERCISE_KEY = 'body_weight_squats'

# --- TARGET DATA for Squats (Full-Body Multi-Angle Logic) ---
TARGET_DATA = {
    # --- Joints to Measure ---
    'measure_joints': {
        # Knee Angle (L/R): Hip - KNEE (V) - Ankle (2D)
        'knee_L': (mp_pose.PoseLandmark.LEFT_HIP.value, mp_pose.PoseLandmark.LEFT_KNEE.value, mp_pose.PoseLandmark.LEFT_ANKLE.value),
        'knee_R': (mp_pose.PoseLandmark.RIGHT_HIP.value, mp_pose.PoseLandmark.RIGHT_KNEE.value, mp_pose.PoseLandmark.RIGHT_ANKLE.value),
        # Hip Angle (R): Shoulder - HIP (V) - Knee (3D preferred for depth/stability)
        'hip_R': (mp_pose.PoseLandmark.RIGHT_SHOULDER.value, mp_pose.PoseLandmark.RIGHT_HIP.value, mp_pose.PoseLandmark.RIGHT_KNEE.value),
        # Ankle Angle (R): Knee - ANKLE (V) - Heel (2D)
        'ankle_R': (mp_pose.PoseLandmark.RIGHT_KNEE.value, mp_pose.PoseLandmark.RIGHT_ANKLE.value, mp_pose.PoseLandmark.RIGHT_HEEL.value),
        # Torso Lean: Angle of R-Shoulder -> R-Hip line relative to Vertical (2D)
        'torso_lean': (mp_pose.PoseLandmark.RIGHT_SHOULDER.value, mp_pose.PoseLandmark.RIGHT_HIP.value),
        # Shoulder Alignment: Angle between Shoulder line and horizontal (2D, used to detect sideways lean)
        'shoulder_align': (mp_pose.PoseLandmark.LEFT_SHOULDER.value, mp_pose.PoseLandmark.RIGHT_SHOULDER.value),
    },
    # --- Angle Thresholds for Repetition and Feedback ---
    'angle_thresholds': {
        # Rep Counting Thresholds (Full-Body Check)
        'knee_down': 90,        # Knee angle < 90
        'hip_down': 80,         # Hip angle < 80
        'torso_lean_down_min': 10, # Torso lean >= 10
        'torso_lean_down_max': 45, # Torso lean <= 45
        'ankle_stable': 70,     # Ankle angle > 70
        'shoulder_neutral': 20, # Shoulder tilt < 20 (Allows some tilt, but prevents large hand movements from being dominant)
        
        'knee_up': 150,         # Knee angle > 150
        'hip_up': 140,          # Hip angle > 140
        'torso_up_neutral': 10, # Torso lean < 10 (Back to standing straight)
        
        # Feedback thresholds
        'knee_depth_min': 100,  # Knee angle > 100 -> Go deeper
        'hip_pushback_min': 90, # Hip angle > 90 -> Push hips back more
        'torso_lean_max_fb': 45,   # Torso angle > 45 -> Keep back straighter (Same as down max)
        'torso_lean_min_fb': 5,    # Torso angle < 5 -> Lean slightly forward
        'knee_diff_max': 20,    # abs(L_knee - R_knee) > 20 -> Keep knees aligned
        'ankle_stability_min_fb': 70, # Ankle < 70 -> Keep heels down (Same as stable check)
        'shoulder_tilt_max_fb': 15, # Shoulder angle (from horizontal) > 15 -> Avoid leaning sideways
        
        # Optional Safety Check
        'MIN_KNEE_MOVEMENT': 30 # Minimum knee angle change to allow counting (to block micro-movements)
    }
}

# --- GLOBAL STATE (Unique Name for Dispatcher) ---
LATEST_FEEDBACK_SQUATS = {
    'feedback': ['Initializing...'], 
    'reps': 0, 
    'state': 'up', # FSM state: 'up' or 'down'
    'knee_L': 0.0, 'knee_R': 0.0, 
    'hip_R': 0.0, 
    'ankle_R': 0.0, 
    'torso_lean': 0.0, 
    'shoulder_align': 0.0,
    'prev_knee_angle': 180.0 # Track previous angle for movement check
}

# --- Utility Functions ---

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

def calculate_shoulder_tilt_angle(sl, sr):
    """Calculates the 2D angle of the shoulder line (SL->SR) relative to the horizontal (X-axis)."""
    sl = np.array(sl); sr = np.array(sr)
    shoulder_vector = sr - sl 
    horizontal_vector = np.array([1, 0])

    dot_product = np.dot(shoulder_vector[:2], horizontal_vector)
    magnitude_product = np.linalg.norm(shoulder_vector[:2]) * np.linalg.norm(horizontal_vector)
    
    if magnitude_product == 0: return 0.0
    
    # Calculate the angle of the line segment from the X-axis
    y_diff = sr[1] - sl[1]
    angle_deg = np.degrees(np.arctan2(abs(y_diff), abs(shoulder_vector[0])))
    return round(angle_deg, 2)


# --- MAIN GENERATOR FUNCTION ---
def generate_frames_squats():
    """Generates frames specifically for the Body Weight Squats analysis using full-body logic."""
    
    # Initialize variables from the current global state of this file
    rep_count = LATEST_FEEDBACK_SQUATS['reps']; 
    current_state = LATEST_FEEDBACK_SQUATS['state']
    prev_knee_angle = LATEST_FEEDBACK_SQUATS['prev_knee_angle'] # Load previous knee angle
    
    # --- CAMERA INITIALIZATION (IMPROVED RELIABILITY) ---
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW) # Try default index 0 with DSHOW backend (Windows)
    
    if not camera.isOpened():
        camera = cv2.VideoCapture(0) # Fallback 1: Try index 0 without specific backend
        if not camera.isOpened():
            camera = cv2.VideoCapture(1, cv2.CAP_DSHOW) # Fallback 2: Try index 1 with DSHOW
            if not camera.isOpened():
                 camera = cv2.VideoCapture(1) # Fallback 3: Try index 1 without specific backend
                 
    if not camera.isOpened(): 
        # Final failure state: update feedback and exit
        LATEST_FEEDBACK_SQUATS['feedback'] = ["FATAL ERROR: Camera could not be opened. Checked indices 0 and 1. Please verify camera is not in use by another program."]; 
        return 
    
    # Set camera properties
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640); camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480); camera.set(cv2.CAP_PROP_FPS, 60)
    # ---------------------------------------------------

    thresholds = TARGET_DATA['angle_thresholds']
    
    with mp_pose.Pose(min_detection_confidence=MIN_DETECTION_CONFIDENCE, min_tracking_confidence=MIN_TRACKING_CONFIDENCE) as pose:
        while True:
            success, frame = camera.read(); 
            if not success: break
            frame = cv2.flip(frame, 1); frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB); frame_rgb.flags.writeable = False
            results = pose.process(frame_rgb); frame_rgb.flags.writeable = True
            frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            
            feedback_list = []; rep_counted = False
            score_color = (0, 255, 255) # Yellow/Cyan default
            
            # Local angle variables updated in the loop
            angles = {key: LATEST_FEEDBACK_SQUATS.get(key, 0.0) for key in ['knee_L', 'knee_R', 'hip_R', 'ankle_R', 'torso_lean', 'shoulder_align']}

            if results.pose_landmarks:
                try:
                    landmarks = results.pose_landmarks.landmark
                    
                    # Helper functions for landmarks
                    # NOTE: Fixed an issue in the original code's get_coords_2d helper function
                    def get_coords_2d(idx): return [landmarks[idx].x, landmarks[idx].y]
                    def get_coords_3d(idx): return [landmarks[idx].x, landmarks[idx].y, landmarks[idx].z]

                    # 1. CALCULATE ALL BASE ANGLES
                    # Knee Angles (2D)
                    j_kL = TARGET_DATA['measure_joints']['knee_L']; angles['knee_L'] = calculate_angle_2d(get_coords_2d(j_kL[0]), get_coords_2d(j_kL[1]), get_coords_2d(j_kL[2]))
                    j_kR = TARGET_DATA['measure_joints']['knee_R']; angles['knee_R'] = calculate_angle_2d(get_coords_2d(j_kR[0]), get_coords_2d(j_kR[1]), get_coords_2d(j_kR[2]))
                    avg_knee_angle = (angles['knee_L'] + angles['knee_R']) / 2
                    
                    # Hip Angle (3D)
                    j_hR = TARGET_DATA['measure_joints']['hip_R']; angles['hip_R'] = calculate_angle_3d(get_coords_3d(j_hR[0]), get_coords_3d(j_hR[1]), get_coords_3d(j_hR[2]))

                    # Ankle Angle (2D)
                    j_aR = TARGET_DATA['measure_joints']['ankle_R']; angles['ankle_R'] = calculate_angle_2d(get_coords_2d(j_aR[0]), get_coords_2d(j_aR[1]), get_coords_2d(j_aR[2]))
                    
                    # Torso Lean Angle (2D against Vertical)
                    j_tL = TARGET_DATA['measure_joints']['torso_lean']; angles['torso_lean'] = calculate_torso_lean_angle(get_coords_2d(j_tL[0]), get_coords_2d(j_tL[1]))

                    # Shoulder Alignment Angle (2D tilt from horizontal)
                    j_sA = TARGET_DATA['measure_joints']['shoulder_align']
                    angles['shoulder_align'] = calculate_shoulder_tilt_angle(get_coords_2d(j_sA[0]), get_coords_2d(j_sA[1]))

                    
                    # 2. REP COUNTING LOGIC (FSM: up -> down -> up)
                    
                    # --- Define Full-Body Conditions ---
                    
                    down_condition = (
                        avg_knee_angle < thresholds['knee_down'] and
                        angles['hip_R'] < thresholds['hip_down'] and
                        thresholds['torso_lean_down_min'] <= angles['torso_lean'] <= thresholds['torso_lean_down_max'] and
                        angles['ankle_R'] > thresholds['ankle_stable'] and
                        angles['shoulder_align'] < thresholds['shoulder_neutral']
                    )
                    
                    up_condition = (
                        avg_knee_angle > thresholds['knee_up'] and
                        angles['hip_R'] > thresholds['hip_up'] and
                        angles['torso_lean'] < thresholds['torso_up_neutral'] and
                        angles['ankle_R'] > thresholds['ankle_stable'] and
                        angles['shoulder_align'] < thresholds['shoulder_neutral']
                    )

                    # --- Optional Safety Check: Ensure significant knee movement (30 degrees) has occurred ---
                    skip_counting = abs(prev_knee_angle - avg_knee_angle) < thresholds['MIN_KNEE_MOVEMENT']
                    
                    # State transition logic
                    if down_condition:
                        current_state = 'down'
                        score_color = (0, 255, 255) # Yellow/Cyan for bottom hold

                    if current_state == 'down' and up_condition and not skip_counting:
                        rep_count += 1
                        current_state = 'up'
                        rep_counted = True
                        score_color = (0, 255, 0) # Green for Rep Completion
                    
                    
                    # 3. FULL-BODY FEEDBACK LOGIC (Runs independent of FSM state)
                    
                    # A. Squat Depth Feedback
                    if avg_knee_angle > thresholds['knee_depth_min'] and current_state != 'down':
                        feedback_list.append("Go deeper into the squat")
                        score_color = (0, 0, 255) # Red for form error

                    if angles['hip_R'] > thresholds['hip_pushback_min'] and current_state != 'up':
                        feedback_list.append("Push your hips back more")
                        score_color = (0, 0, 255)
                        
                    # B. Torso Posture Feedback
                    if angles['torso_lean'] > thresholds['torso_lean_max_fb']:
                        feedback_list.append("Keep your chest up and back straighter")
                        score_color = (0, 0, 255) 
                    
                    if angles['torso_lean'] < thresholds['torso_lean_min_fb'] and current_state != 'up':
                        feedback_list.append("Lean slightly forward for balance")
                        score_color = (0, 0, 255)

                    # C. Knee Alignment (Symmetry)
                    if abs(angles['knee_L'] - angles['knee_R']) > thresholds['knee_diff_max']:
                        feedback_list.append("Keep both knees aligned (Avoid caving)")
                        score_color = (0, 0, 255)
                        
                    # D. Foot/Ankle Stability
                    if angles['ankle_R'] < thresholds['ankle_stability_min_fb']:
                        feedback_list.append("Keep your heels down and feet stable")
                        score_color = (0, 0, 255)
                        
                    # E. Shoulder Stability (Leaning Sideways)
                    if angles['shoulder_align'] > thresholds['shoulder_tilt_max_fb']:
                        feedback_list.append("Avoid leaning sideways")
                        score_color = (0, 0, 255)
                        
                    # Default State Feedback
                    if not feedback_list:
                        if rep_counted:
                             feedback_list.append(f"REP {rep_count}. Excellent squat form!")
                        elif current_state == 'down':
                             feedback_list.append("Maximum depth achieved. Drive up!")
                        else:
                             feedback_list.append("Ready to Squat! Lower your hips.")
                    elif skip_counting and current_state == 'down':
                         feedback_list.append(f"HOLD: Knee angle changed less than {thresholds['MIN_KNEE_MOVEMENT']} degrees.")


                    # DRAW LANDMARKS (Uses the color determined by the feedback loop)
                    mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=score_color, thickness=3, circle_radius=6),
                        mp_drawing.DrawingSpec(color=(0, 255, 255), thickness=2, circle_radius=2))
                        
                except Exception as e:
                    print(f"Tracking error: {e}")
                    feedback_list = ["Tracking Error. Check joint visibility."]; current_state = 'ERROR'

            else:
                feedback_list = ["No Pose Detected. Step back or adjust camera."]; current_state = 'WAIT'
            
            # Update GLOBAL FEEDBACK STATE and persist previous knee angle
            LATEST_FEEDBACK_SQUATS['feedback'] = feedback_list; 
            LATEST_FEEDBACK_SQUATS['reps'] = rep_count; 
            LATEST_FEEDBACK_SQUATS['state'] = current_state; 
            LATEST_FEEDBACK_SQUATS['prev_knee_angle'] = avg_knee_angle # Update for the next frame
            
            # Update all angles in global state
            for key, value in angles.items():
                LATEST_FEEDBACK_SQUATS[key] = value

            
            ret, buffer = cv2.imencode('.jpg', frame); 
            yield (b'--frame\r\n' + b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\r\n')
        
        camera.release(); cv2.destroyAllWindows()

# --- Utility to get latest feedback state for a separate API endpoint ---
def get_latest_feedback_squats():
    return json.dumps(LATEST_FEEDBACK_SQUATS)