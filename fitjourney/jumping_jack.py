import cv2
import mediapipe as mp
import numpy as np
import json

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

MIN_DETECTION_CONFIDENCE = 0.5 
MIN_TRACKING_CONFIDENCE = 0.5 
EXERCISE_KEY = 'jumping_jack'

TARGET_DATA = {
    'measure_joints_arm': {
        'A': mp_pose.PoseLandmark.RIGHT_HIP.value,
        'B': mp_pose.PoseLandmark.RIGHT_SHOULDER.value,
        'C': mp_pose.PoseLandmark.RIGHT_ELBOW.value
    },
    'measure_joints_leg': {
        'A': mp_pose.PoseLandmark.RIGHT_KNEE.value,
        'B': mp_pose.PoseLandmark.RIGHT_HIP.value,
        'C': mp_pose.PoseLandmark.LEFT_HIP.value
    },
    'angle_thresholds': {
        'arm_open': 135,           # AGGRESSIVELY RELAXED (Was 160)
        'arm_close': 50,           # AGGRESSIVELY RELAXED (Was 30)
        'leg_open': 25,            # AGGRESSIVELY RELAXED (Was 45)
        'leg_close': 35,           # AGGRESSIVELY RELAXED (Was 20)
        'arm_low_feedback': 140,
        'arm_high_feedback': 180,
        'leg_low_feedback': 35,
        'knee_bend_feedback': 160
    },
    'measure_joints_knee': {
        'A': mp_pose.PoseLandmark.RIGHT_HIP.value,
        'B': mp_pose.PoseLandmark.RIGHT_KNEE.value,
        'C': mp_pose.PoseLandmark.RIGHT_ANKLE.value
    }
}

LATEST_FEEDBACK_JUMPING_JACK = {
    'feedback': ['Initializing...'], 
    'reps': 0, 
    'state': 'close',
    'arm_angle': 0.0,
    'leg_angle': 0.0,
    'knee_angle': 0.0
}

def calculate_angle_2d(a, b, c):
    a = np.array(a); b = np.array(b); c = np.array(c) 
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0: angle = 360 - angle
    return round(angle, 2)

def calculate_angle_3d(a, b, c):
    a = np.array(a); b = np.array(b); c = np.array(c)
    ba = a - b
    bc = c - b
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
    angle = np.arccos(cosine_angle)
    return round(np.degrees(angle), 2)

def generate_frames_jumping_jack():
    rep_count = LATEST_FEEDBACK_JUMPING_JACK['reps']; current_state = LATEST_FEEDBACK_JUMPING_JACK['state']
    
    with mp_pose.Pose(min_detection_confidence=MIN_DETECTION_CONFIDENCE, min_tracking_confidence=MIN_TRACKING_CONFIDENCE) as pose:
        camera = cv2.VideoCapture(0, cv2.CAP_DSHOW) 
        if not camera.isOpened(): 
            camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            LATEST_FEEDBACK_JUMPING_JACK['feedback'] = ["FATAL ERROR: Camera could not be opened."]; return 
        
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640); camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480); camera.set(cv2.CAP_PROP_FPS, 60)
        
        while True:
            success, frame = camera.read(); 
            if not success: break
            frame = cv2.flip(frame, 1); frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB); frame_rgb.flags.writeable = False
            results = pose.process(frame_rgb); frame_rgb.flags.writeable = True
            frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            
            feedback_list = []; rep_counted = False
            user_arm_angle = LATEST_FEEDBACK_JUMPING_JACK['arm_angle']
            user_leg_angle = LATEST_FEEDBACK_JUMPING_JACK['leg_angle']
            user_knee_angle = LATEST_FEEDBACK_JUMPING_JACK['knee_angle']
            
            score_color = (0, 255, 255) 

            if results.pose_landmarks:
                try:
                    landmarks = results.pose_landmarks.landmark
                    arm_j = TARGET_DATA['measure_joints_arm']
                    arm_coords_A = [landmarks[arm_j['A']].x, landmarks[arm_j['A']].y, landmarks[arm_j['A']].z]
                    arm_coords_B = [landmarks[arm_j['B']].x, landmarks[arm_j['B']].y, landmarks[arm_j['B']].z]
                    arm_coords_C = [landmarks[arm_j['C']].x, landmarks[arm_j['C']].y, landmarks[arm_j['C']].z]
                    user_arm_angle = calculate_angle_3d(arm_coords_A, arm_coords_B, arm_coords_C)
                    
                    leg_j = TARGET_DATA['measure_joints_leg']
                    leg_coords_A = [landmarks[leg_j['A']].x, landmarks[leg_j['A']].y]
                    leg_coords_B = [landmarks[leg_j['B']].x, landmarks[leg_j['B']].y]
                    leg_coords_C = [landmarks[leg_j['C']].x, landmarks[leg_j['C']].y]
                    user_leg_angle = calculate_angle_2d(leg_coords_A, leg_coords_B, leg_coords_C)

                    knee_j = TARGET_DATA['measure_joints_knee']
                    knee_coords_A = [landmarks[knee_j['A']].x, landmarks[knee_j['A']].y]
                    knee_coords_B = [landmarks[knee_j['B']].x, landmarks[knee_j['B']].y]
                    knee_coords_C = [landmarks[knee_j['C']].x, landmarks[knee_j['C']].y]
                    user_knee_angle = calculate_angle_2d(knee_coords_A, knee_coords_B, knee_coords_C)

                    thresholds = TARGET_DATA['angle_thresholds']
                    
                    if user_arm_angle > thresholds['arm_open'] and user_leg_angle > thresholds['leg_open']:
                        current_state = 'open'
                        score_color = (0, 255, 0)

                    elif current_state == 'open' and user_arm_angle < thresholds['arm_close'] and user_leg_angle < thresholds['leg_close']:
                        rep_count += 1
                        current_state = 'close'
                        rep_counted = True
                        score_color = (0, 255, 0)
                        feedback_list.append(f"REP {rep_count}. Good form!")
                    
                    if not feedback_list and current_state == 'close':
                        feedback_list.append("ARMS DOWN! READY!")
                    elif not feedback_list and current_state == 'open':
                        feedback_list.append("HOLD OPEN! Return to close.")
                    
                    if user_arm_angle < thresholds['arm_low_feedback']:
                        feedback_list.append("Raise your arms higher")
                        score_color = (0, 0, 255) 
                    if user_arm_angle > thresholds['arm_high_feedback']:
                        feedback_list.append("Do not overextend shoulders")
                        score_color = (0, 0, 255) 
                    
                    if current_state != 'close' and user_leg_angle < thresholds['leg_low_feedback']:
                        feedback_list.append("Spread your legs more")
                        score_color = (0, 0, 255) 
                    
                    if user_knee_angle < thresholds['knee_bend_feedback']:
                        feedback_list.append("Keep knees straighter")
                        score_color = (0, 0, 255) 

                    if not feedback_list: 
                        if rep_counted: feedback_list.append(f"REP {rep_count}. Good job!")
                        elif current_state == 'open': feedback_list.append("Arms and Legs OPEN!")
                        else: feedback_list.append("Start the next rep!")

                    mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=score_color, thickness=3, circle_radius=6),
                        mp_drawing.DrawingSpec(color=(0, 255, 255), thickness=2, circle_radius=2))
                        
                except Exception as e:
                    print(f"Tracking error: {e}")
                    feedback_list = ["Tracking Error."]; current_state = 'ERROR'; user_arm_angle = 0.0

            else:
                feedback_list = ["No Pose Detected."]; current_state = 'WAIT'; user_arm_angle = 0.0
            
            LATEST_FEEDBACK_JUMPING_JACK['feedback'] = feedback_list; 
            LATEST_FEEDBACK_JUMPING_JACK['reps'] = rep_count; 
            LATEST_FEEDBACK_JUMPING_JACK['state'] = current_state; 
            LATEST_FEEDBACK_JUMPING_JACK['arm_angle'] = user_arm_angle
            LATEST_FEEDBACK_JUMPING_JACK['leg_angle'] = user_leg_angle
            LATEST_FEEDBACK_JUMPING_JACK['knee_angle'] = user_knee_angle

            ret, buffer = cv2.imencode('.jpg', frame); 
            yield (b'--frame\r\n' + b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\r\n')
        
        camera.release(); cv2.destroyAllWindows()