import cv2
import mediapipe as mp
import numpy as np
import json

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

MIN_DETECTION_CONFIDENCE = 0.5 
MIN_TRACKING_CONFIDENCE = 0.5 
EXERCISE_KEY = 'body_weight_squat_ohp'

TARGET_DATA = {
    'measure_joints': {
        'knee_L': (mp_pose.PoseLandmark.LEFT_HIP.value, mp_pose.PoseLandmark.LEFT_KNEE.value, mp_pose.PoseLandmark.LEFT_ANKLE.value),
        'knee_R': (mp_pose.PoseLandmark.RIGHT_HIP.value, mp_pose.PoseLandmark.RIGHT_KNEE.value, mp_pose.PoseLandmark.RIGHT_ANKLE.value),
        'hip_R': (mp_pose.PoseLandmark.RIGHT_SHOULDER.value, mp_pose.PoseLandmark.RIGHT_HIP.value, mp_pose.PoseLandmark.RIGHT_KNEE.value),
        'shoulder_R': (mp_pose.PoseLandmark.RIGHT_HIP.value, mp_pose.PoseLandmark.RIGHT_SHOULDER.value, mp_pose.PoseLandmark.RIGHT_ELBOW.value),
        'elbow_R': (mp_pose.PoseLandmark.RIGHT_SHOULDER.value, mp_pose.PoseLandmark.RIGHT_ELBOW.value, mp_pose.PoseLandmark.RIGHT_WRIST.value),
        'torso': (mp_pose.PoseLandmark.RIGHT_SHOULDER.value, mp_pose.PoseLandmark.RIGHT_HIP.value),
    },
    'angle_thresholds': {
        'knee_down': 90,
        'hip_down': 80,
        'shoulder_down': 90,
        'knee_up': 150,
        'hip_up': 140,
        'shoulder_up': 160,
        'elbow_up': 150,
        'torso_lean_min': 10,
        'torso_lean_max': 40,   
        'torso_too_straight': 5,
        'knee_depth_min': 100,
        'hip_pushback_min': 90,
        'torso_straightness_max': 45,
        'knee_diff_max': 20
    }
}

LATEST_FEEDBACK = {
    'feedback': ['Initializing...'], 
    'reps': 0, 
    'state': 'up',
    'knee_L': 0.0, 'knee_R': 0.0, 
    'hip_R': 0.0, 
    'shoulder_R': 0.0, 
    'elbow_R': 0.0, 
    'torso': 0.0
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
    cosine_angle = dot_product / magnitude_product
    cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
    angle = np.arccos(cosine_angle)
    return round(np.degrees(angle), 2)

def generate_frames_squat_ohp():
    rep_count = LATEST_FEEDBACK['reps']; current_state = LATEST_FEEDBACK['state']
    
    with mp_pose.Pose(min_detection_confidence=MIN_DETECTION_CONFIDENCE, min_tracking_confidence=MIN_TRACKING_CONFIDENCE) as pose:
        camera = cv2.VideoCapture(0, cv2.CAP_DSHOW) 
        if not camera.isOpened(): 
            camera = cv2.VideoCapture(0)
        if not camera.isOpened(): LATEST_FEEDBACK['feedback'] = ["FATAL ERROR: Camera could not be opened."]; return 

        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640); camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480); camera.set(cv2.CAP_PROP_FPS, 60)
        
        while True:
            success, frame = camera.read(); 
            if not success: break
            frame = cv2.flip(frame, 1)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB); frame_rgb.flags.writeable = False
            results = pose.process(frame_rgb); frame_rgb.flags.writeable = True
            frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            
            feedback_list = []; rep_counted = False
            thresholds = TARGET_DATA['angle_thresholds']
            score_color = (0, 255, 255) 
            angles = {'knee_L': 0.0, 'knee_R': 0.0, 'hip_R': 0.0, 'shoulder_R': 0.0, 'elbow_R': 0.0, 'torso': 0.0}

            if results.pose_landmarks:
                try:
                    landmarks = results.pose_landmarks.landmark
                    def get_coords_2d(idx): return [landmarks[idx].x, landmarks[idx].y]
                    def get_coords_3d(idx): return [landmarks[idx].x, landmarks[idx].y, landmarks[idx].z]

                    j_L = TARGET_DATA['measure_joints']['knee_L']; angles['knee_L'] = calculate_angle_2d(get_coords_2d(j_L[0]), get_coords_2d(j_L[1]), get_coords_2d(j_L[2]))
                    j_R = TARGET_DATA['measure_joints']['knee_R']; angles['knee_R'] = calculate_angle_2d(get_coords_2d(j_R[0]), get_coords_2d(j_R[1]), get_coords_2d(j_R[2]))
                    avg_knee_angle = (angles['knee_L'] + angles['knee_R']) / 2
                    
                    j_hip = TARGET_DATA['measure_joints']['hip_R']; angles['hip_R'] = calculate_angle_3d(get_coords_3d(j_hip[0]), get_coords_3d(j_hip[1]), get_coords_3d(j_hip[2]))
                    j_shld = TARGET_DATA['measure_joints']['shoulder_R']; angles['shoulder_R'] = calculate_angle_3d(get_coords_3d(j_shld[0]), get_coords_3d(j_shld[1]), get_coords_3d(j_shld[2]))
                    j_elb = TARGET_DATA['measure_joints']['elbow_R']; angles['elbow_R'] = calculate_angle_2d(get_coords_2d(j_elb[0]), get_coords_2d(j_elb[1]), get_coords_2d(j_elb[2]))
                    j_torso = TARGET_DATA['measure_joints']['torso']; angles['torso'] = calculate_torso_lean_angle(get_coords_2d(j_torso[0]), get_coords_2d(j_torso[1]))

                    is_down_position = (avg_knee_angle < thresholds['knee_down'] and 
                                        angles['hip_R'] < thresholds['hip_down'] and 
                                        angles['shoulder_R'] < thresholds['shoulder_down'])
                    
                    if is_down_position:
                        current_state = 'down'
                        score_color = (0, 255, 255) 

                    is_up_position = (avg_knee_angle > thresholds['knee_up'] and 
                                      angles['hip_R'] > thresholds['hip_up'] and 
                                      angles['shoulder_R'] > thresholds['shoulder_up'] and
                                      angles['elbow_R'] > thresholds['elbow_up'])

                    if current_state == 'down' and is_up_position:
                        rep_count += 1
                        current_state = 'up'
                        rep_counted = True
                        score_color = (0, 255, 0) 
                        
                    if avg_knee_angle > thresholds['knee_depth_min'] and current_state == 'up':
                        feedback_list.append("Go deeper")
                        score_color = (0, 0, 255) 
                        
                    if angles['shoulder_R'] < thresholds['shoulder_up'] and current_state == 'up':
                        feedback_list.append("Raise arms fully")
                        score_color = (0, 0, 255) 

                    if not feedback_list:
                        if rep_counted: feedback_list.append(f"REP {rep_count}. Excellent!")
                        elif current_state == 'down': feedback_list.append("Drive up & Press!")
                        else: feedback_list.append("Start Squatting!")

                    mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=score_color, thickness=3, circle_radius=6),
                        mp_drawing.DrawingSpec(color=(0, 255, 255), thickness=2, circle_radius=2))
                        
                except Exception as e:
                    print(f"Tracking error: {e}")
                    feedback_list = ["Tracking Error."]; current_state = 'ERROR'

            else:
                feedback_list = ["No Pose Detected."]; current_state = 'WAIT'
            
            LATEST_FEEDBACK['feedback'] = feedback_list; 
            LATEST_FEEDBACK['reps'] = rep_count; 
            LATEST_FEEDBACK['state'] = current_state; 
            
            for key, value in angles.items():
                LATEST_FEEDBACK[key] = value
            
            ret, buffer = cv2.imencode('.jpg', frame); 
            yield (b'--frame\r\n' + b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\r\n')
        
        camera.release(); cv2.destroyAllWindows()

def get_latest_feedback_squat_ohp():
    return json.dumps(LATEST_FEEDBACK)