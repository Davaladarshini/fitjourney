import cv2
import mediapipe as mp
import numpy as np
import json

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

MIN_DETECTION_CONFIDENCE = 0.5 
MIN_TRACKING_CONFIDENCE = 0.5 
EXERCISE_KEY = 'body_weight_squats'

TARGET_DATA = {
    'measure_joints': {
        'knee_L': (mp_pose.PoseLandmark.LEFT_HIP.value, mp_pose.PoseLandmark.LEFT_KNEE.value, mp_pose.PoseLandmark.LEFT_ANKLE.value),
        'knee_R': (mp_pose.PoseLandmark.RIGHT_HIP.value, mp_pose.PoseLandmark.RIGHT_KNEE.value, mp_pose.PoseLandmark.RIGHT_ANKLE.value),
        'hip_R': (mp_pose.PoseLandmark.RIGHT_SHOULDER.value, mp_pose.PoseLandmark.RIGHT_HIP.value, mp_pose.PoseLandmark.RIGHT_KNEE.value),
        'ankle_R': (mp_pose.PoseLandmark.RIGHT_KNEE.value, mp_pose.PoseLandmark.RIGHT_ANKLE.value, mp_pose.PoseLandmark.RIGHT_HEEL.value),
        'torso_lean': (mp_pose.PoseLandmark.RIGHT_SHOULDER.value, mp_pose.PoseLandmark.RIGHT_HIP.value),
        'shoulder_align': (mp_pose.PoseLandmark.LEFT_SHOULDER.value, mp_pose.PoseLandmark.RIGHT_SHOULDER.value),
    },
    'angle_thresholds': {
        'knee_down': 90,
        'hip_down': 80,
        'torso_lean_down_min': 10,
        'torso_lean_down_max': 45,
        'ankle_stable': 70,
        'shoulder_neutral': 20,
        'knee_up': 150,
        'hip_up': 140,
        'torso_up_neutral': 10,
        'knee_depth_min': 100,
        'hip_pushback_min': 90,
        'torso_lean_max_fb': 45,
        'torso_lean_min_fb': 5,
        'knee_diff_max': 20,
        'ankle_stability_min_fb': 70,
        'shoulder_tilt_max_fb': 15,
        'MIN_KNEE_MOVEMENT': 30 
    }
}

LATEST_FEEDBACK_SQUATS = {
    'feedback': ['Initializing...'], 
    'reps': 0, 
    'state': 'up',
    'knee_L': 0.0, 'knee_R': 0.0, 
    'hip_R': 0.0, 
    'ankle_R': 0.0, 
    'torso_lean': 0.0, 
    'shoulder_align': 0.0,
    'prev_knee_angle': 180.0 
}

def calculate_angle_2d(a, b, c):
    a = np.array(a); b = np.array(b); c = np.array(c) 
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0: angle = 360 - angle
    return round(angle, 2)

def calculate_angle_3d(a, b, c):
    a = np.array(a); b = np.array(b); c = np.array(c)
    ba = a - b; bc = c - b
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
    angle = np.arccos(cosine_angle)
    return round(np.degrees(angle), 2)

def calculate_torso_lean_angle(shoulder, hip):
    p1 = np.array(shoulder); p2 = np.array(hip)
    torso_vector = p1 - p2
    vertical_vector = np.array([0, -1]) 
    dot_product = np.dot(torso_vector[:2], vertical_vector)
    magnitude_product = np.linalg.norm(torso_vector[:2]) * np.linalg.norm(vertical_vector)
    if magnitude_product == 0: return 0.0
    angle = np.degrees(np.arccos(np.clip(dot_product / magnitude_product, -1.0, 1.0)))
    return round(angle, 2)

def calculate_shoulder_tilt_angle(sl, sr):
    sl = np.array(sl); sr = np.array(sr)
    shoulder_vector = sr - sl 
    horizontal_vector = np.array([1, 0])
    dot_product = np.dot(shoulder_vector[:2], horizontal_vector)
    magnitude_product = np.linalg.norm(shoulder_vector[:2]) * np.linalg.norm(horizontal_vector)
    if magnitude_product == 0: return 0.0
    y_diff = sr[1] - sl[1]
    angle_deg = np.degrees(np.arctan2(abs(y_diff), abs(shoulder_vector[0])))
    return round(angle_deg, 2)

def generate_frames_squats():
    rep_count = LATEST_FEEDBACK_SQUATS['reps']; 
    current_state = LATEST_FEEDBACK_SQUATS['state']
    prev_knee_angle = LATEST_FEEDBACK_SQUATS['prev_knee_angle'] 
    
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW) 
    if not camera.isOpened():
        camera = cv2.VideoCapture(0)
    if not camera.isOpened(): 
        LATEST_FEEDBACK_SQUATS['feedback'] = ["FATAL ERROR: Camera could not be opened."]; return 
    
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640); camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480); camera.set(cv2.CAP_PROP_FPS, 60)

    thresholds = TARGET_DATA['angle_thresholds']
    
    with mp_pose.Pose(min_detection_confidence=MIN_DETECTION_CONFIDENCE, min_tracking_confidence=MIN_TRACKING_CONFIDENCE) as pose:
        while True:
            success, frame = camera.read(); 
            if not success: break
            frame = cv2.flip(frame, 1); frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB); frame_rgb.flags.writeable = False
            results = pose.process(frame_rgb); frame_rgb.flags.writeable = True
            frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            
            feedback_list = []; rep_counted = False
            score_color = (0, 255, 255) 
            
            angles = {key: LATEST_FEEDBACK_SQUATS.get(key, 0.0) for key in ['knee_L', 'knee_R', 'hip_R', 'ankle_R', 'torso_lean', 'shoulder_align']}

            if results.pose_landmarks:
                try:
                    landmarks = results.pose_landmarks.landmark
                    def get_coords_2d(idx): return [landmarks[idx].x, landmarks[idx].y]
                    def get_coords_3d(idx): return [landmarks[idx].x, landmarks[idx].y, landmarks[idx].z]

                    j_kL = TARGET_DATA['measure_joints']['knee_L']; angles['knee_L'] = calculate_angle_2d(get_coords_2d(j_kL[0]), get_coords_2d(j_kL[1]), get_coords_2d(j_kL[2]))
                    j_kR = TARGET_DATA['measure_joints']['knee_R']; angles['knee_R'] = calculate_angle_2d(get_coords_2d(j_kR[0]), get_coords_2d(j_kR[1]), get_coords_2d(j_kR[2]))
                    avg_knee_angle = (angles['knee_L'] + angles['knee_R']) / 2
                    
                    j_hR = TARGET_DATA['measure_joints']['hip_R']; angles['hip_R'] = calculate_angle_3d(get_coords_3d(j_hR[0]), get_coords_3d(j_hR[1]), get_coords_3d(j_hR[2]))

                    j_aR = TARGET_DATA['measure_joints']['ankle_R']; angles['ankle_R'] = calculate_angle_2d(get_coords_2d(j_aR[0]), get_coords_2d(j_aR[1]), get_coords_2d(j_aR[2]))
                    
                    j_tL = TARGET_DATA['measure_joints']['torso_lean']; angles['torso_lean'] = calculate_torso_lean_angle(get_coords_2d(j_tL[0]), get_coords_2d(j_tL[1]))

                    j_sA = TARGET_DATA['measure_joints']['shoulder_align']
                    angles['shoulder_align'] = calculate_shoulder_tilt_angle(get_coords_2d(j_sA[0]), get_coords_2d(j_sA[1]))

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

                    skip_counting = abs(prev_knee_angle - avg_knee_angle) < thresholds['MIN_KNEE_MOVEMENT']
                    
                    if down_condition:
                        current_state = 'down'
                        score_color = (0, 255, 255) 

                    if current_state == 'down' and up_condition and not skip_counting:
                        rep_count += 1
                        current_state = 'up'
                        rep_counted = True
                        score_color = (0, 255, 0)
                    
                    if avg_knee_angle > thresholds['knee_depth_min'] and current_state != 'down':
                        feedback_list.append("Go deeper")
                        score_color = (0, 0, 255) 

                    if angles['hip_R'] > thresholds['hip_pushback_min'] and current_state != 'up':
                        feedback_list.append("Push hips back")
                        score_color = (0, 0, 255)
                        
                    if angles['torso_lean'] > thresholds['torso_lean_max_fb']:
                        feedback_list.append("Keep chest up")
                        score_color = (0, 0, 255) 
                    
                    if not feedback_list:
                        if rep_counted: feedback_list.append(f"REP {rep_count}. Excellent!")
                        elif current_state == 'down': feedback_list.append("Drive up!")
                        else: feedback_list.append("Ready to Squat!")

                    mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=score_color, thickness=3, circle_radius=6),
                        mp_drawing.DrawingSpec(color=(0, 255, 255), thickness=2, circle_radius=2))
                        
                except Exception as e:
                    print(f"Tracking error: {e}")
                    feedback_list = ["Tracking Error."]; current_state = 'ERROR'

            else:
                feedback_list = ["No Pose Detected."]; current_state = 'WAIT'
            
            LATEST_FEEDBACK_SQUATS['feedback'] = feedback_list; 
            LATEST_FEEDBACK_SQUATS['reps'] = rep_count; 
            LATEST_FEEDBACK_SQUATS['state'] = current_state; 
            LATEST_FEEDBACK_SQUATS['prev_knee_angle'] = avg_knee_angle 
            
            for key, value in angles.items():
                LATEST_FEEDBACK_SQUATS[key] = value

            ret, buffer = cv2.imencode('.jpg', frame); 
            yield (b'--frame\r\n' + b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\r\n')
        
        camera.release(); cv2.destroyAllWindows()

def get_latest_feedback_squats():
    return json.dumps(LATEST_FEEDBACK_SQUATS)