import cv2
import mediapipe as mp
import numpy as np
import collections
from time import time
from flask import Blueprint, render_template, redirect, url_for, session, flash, jsonify, Response

# --- Import modular exercise logic ---
from . import body_weight_squat_ohp
from . import alternate_lunges_rotation
from . import body_weight_squats
from . import jumping_jack

webcam_bp = Blueprint('webcam', __name__)

# --- Central Dispatcher Setup ---
EXERCISE_DISPATCHER = {
    'body_weight_squat_ohp': {
        'generator': body_weight_squat_ohp.generate_frames_squat_ohp,
        'feedback_state': body_weight_squat_ohp.LATEST_FEEDBACK,
        'target_data': body_weight_squat_ohp.TARGET_DATA
    },
    'alternate_lunges_rotation': {
        'generator': alternate_lunges_rotation.generate_frames_lunge_rotation,
        'feedback_state': alternate_lunges_rotation.LATEST_FEEDBACK,
        'target_data': alternate_lunges_rotation.TARGET_DATA
    },
    'body_weight_squats': {
        'generator': body_weight_squats.generate_frames_squats, 
        'feedback_state': body_weight_squats.LATEST_FEEDBACK_SQUATS,
        'target_data': body_weight_squats.TARGET_DATA
    },
    'jumping_jack': {
        'generator': jumping_jack.generate_frames_jumping_jack,
        'feedback_state': jumping_jack.LATEST_FEEDBACK_JUMPING_JACK,
        'target_data': jumping_jack.TARGET_DATA
    }
} 

ALL_EXERCISES = {}
for key, data in EXERCISE_DISPATCHER.items():
    target_data = data['target_data']
    angle = 0.0
    thresholds = target_data.get('angle_thresholds', {})
    if key in ['body_weight_squat_ohp', 'body_weight_squats']:
        angle = thresholds.get('knee_down', 0)
    elif key == 'alternate_lunges_rotation':
        angle = thresholds.get('front_knee_down', 0)
    elif key == 'jumping_jack':
        angle = thresholds.get('arm_open', 0)
    feedback_text = target_data.get('feedback', "Multi-criteria analysis.")
    ALL_EXERCISES[key] = {'target_angle': angle, 'feedback': feedback_text}

# --- Auto-Classifier Globals ---
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils

# NOTE: 'cap' is REMOVED from global scope to prevent locking the camera
# when other exercises try to use it.

exercise_data = {
    "Squat": {"rep_count": 0, "stage": None},
    "Push-up": {"rep_count": 0, "stage": None},
    "Lunge": {"rep_count": 0, "stage": None},
    "Jumping Jack": {"rep_count": 0, "stage": None},
    "Sit-up": {"rep_count": 0, "stage": None},
}
exercise_lock_buffer = collections.deque(maxlen=15)
lock_threshold = 10
active_exercise = None
last_switch_time = 0
switch_cooldown = 2
no_motion_counter = 0
NO_MOTION_LIMIT = 25
current_exercise = "Unknown"
feedback_text = ""

def calculate_angle(a, b, c):
    a = np.array(a); b = np.array(b); c = np.array(c)
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians*180.0/np.pi)
    if angle > 180.0: angle = 360 - angle
    return angle

def extract_angles(landmarks):
    left_knee = calculate_angle([landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y], [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x, landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y], [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x, landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y])
    right_knee = calculate_angle([landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y], [landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].y], [landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y])
    left_elbow = calculate_angle([landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y], [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x, landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y], [landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x, landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y])
    right_elbow = calculate_angle([landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y], [landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y], [landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].y])
    left_hip = calculate_angle([landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y], [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y], [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x, landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y])
    left_shoulder = calculate_angle([landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x, landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y], [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y], [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y])
    return left_knee, right_knee, left_elbow, right_elbow, left_hip, left_shoulder

def robust_classification(angles):
    left_knee, right_knee, left_elbow, right_elbow, left_hip, left_shoulder = angles; avg_knee_angle = (left_knee + right_knee)/2; avg_elbow_angle = (left_elbow + right_elbow)/2
    detected = "Unknown"; arms_wide = left_shoulder > 90 and left_elbow > 150 and right_elbow > 150; legs_wide = avg_knee_angle > 160
    if avg_knee_angle < 100 and 70 < left_hip < 140: detected = "Squat"
    elif avg_elbow_angle < 100 and avg_knee_angle > 150: detected = "Push-up"
    elif left_hip < 100 and avg_knee_angle < 140: detected = "Lunge"
    elif arms_wide and legs_wide: detected = "Jumping Jack"
    elif left_hip < 90 and avg_knee_angle < 90: detected = "Sit-up"
    return detected

def update_active_exercise():
    global active_exercise, last_switch_time; now = time()
    if len(exercise_lock_buffer) == 0: return
    common_exercise = max(set(exercise_lock_buffer), key=exercise_lock_buffer.count)
    if common_exercise == "Unknown": return
    if common_exercise != active_exercise:
        if (now - last_switch_time) > switch_cooldown and exercise_lock_buffer.count(common_exercise) >= lock_threshold:
            active_exercise = common_exercise; last_switch_time = now

def classify_and_count(angles):
    global current_exercise, feedback_text, active_exercise, no_motion_counter
    detected = robust_classification(angles); exercise_lock_buffer.append(detected); update_active_exercise()
    if active_exercise is None: current_exercise = "Detecting..."; feedback_text = "Start exercising to lock."; return
    current_exercise = active_exercise; data = exercise_data.get(active_exercise); rep_this_frame = False
    left_knee, right_knee, left_elbow, right_elbow, left_hip, left_shoulder = angles; avg_knee_angle = (left_knee + right_knee) / 2; avg_elbow_angle = (left_elbow + right_elbow) / 2; arms_wide = left_shoulder > 90 and left_elbow > 150 and right_elbow > 150; legs_wide = avg_knee_angle > 160
    if active_exercise == "Jumping Jack":
        if arms_wide and legs_wide:
            if data.get("stage") != "up": data["stage"] = "up"
        elif not arms_wide and not legs_wide:
            if data.get("stage") == "up": data["stage"] = "down"; data["rep_count"] += 1; rep_this_frame = True; feedback_text = f"Good jack! Reps: {data['rep_count']}"
        else: feedback_text = "Keep moving"
    elif active_exercise == "Squat":
        if avg_knee_angle > 160: data["stage"] = "up"
        if avg_knee_angle < 90 and data.get("stage") == "up": data["stage"] = "down"; data["rep_count"] += 1; rep_this_frame = True; feedback_text = f"Good squat! Reps: {data['rep_count']}"
        elif 90 <= avg_knee_angle <= 160: feedback_text = "Go deeper!"
    elif active_exercise == "Push-up":
        if avg_elbow_angle > 160: data["stage"] = "up"
        if avg_elbow_angle < 90 and data.get("stage") == "up": data["stage"] = "down"; data["rep_count"] += 1; rep_this_frame = True; feedback_text = f"Good push-up! Reps: {data['rep_count']}"
        elif 90 <= avg_elbow_angle <= 160: feedback_text = "Keep going!"
    elif active_exercise == "Lunge":
        if left_hip > 160: data["stage"] = "up"
        if left_hip < 90 and data.get("stage") == "up": data["stage"] = "down"; data["rep_count"] += 1; rep_this_frame = True; feedback_text = f"Good lunge! Reps: {data['rep_count']}"
        elif 90 <= left_hip <= 160: feedback_text = "Lower your hips more!"
    elif active_exercise == "Sit-up":
        if left_hip > 160: data["stage"] = "up"
        if left_hip < 90 and data.get("stage") == "up": data["stage"] = "down"; data["rep_count"] += 1; rep_this_frame = True; feedback_text = f"Good sit-up! Reps: {data['rep_count']}"
        elif 90 <= left_hip <= 160: feedback_text = "Keep pushing!"
    else: feedback_text = "Exercise not recognized"
    if rep_this_frame: no_motion_counter = 0
    else:
        no_motion_counter += 1
        if no_motion_counter >= NO_MOTION_LIMIT: active_exercise = None; exercise_lock_buffer.clear(); no_motion_counter = 0; feedback_text = "No reps detected. Unlocking..."

def generate_frames():
    global current_exercise, feedback_text
    
    # Initialize camera locally for this specific stream request
    cap = cv2.VideoCapture(0)
    frame_skip = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret: break
            
            frame_skip += 1
            if frame_skip % 2 == 0:
                img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB); results = pose.process(img_rgb)
                if results.pose_landmarks:
                    landmarks = results.pose_landmarks.landmark; mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS); angles = extract_angles(landmarks); classify_and_count(angles)
            _, buffer = cv2.imencode('.jpg', frame); frame_bytes = buffer.tobytes()
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    finally:
        # Ensure camera is released when client disconnects
        cap.release()

# --- Webcam Routes ---

@webcam_bp.route('/exercise_info')
def exercise_info():
    return jsonify({
        "current_exercise": current_exercise,
        "rep_counts": {ex: data['rep_count'] for ex, data in exercise_data.items()},
        "feedback": feedback_text,
        "active_exercise": active_exercise,
    })

@webcam_bp.route('/auto_classify_video_feed')
def auto_classify_video_feed():
    return Response(
        generate_frames(), 
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@webcam_bp.route('/auto-classify')
def auto_classify():
    return render_template('auto_classify.html')

@webcam_bp.route('/video-workouts')
def video_workouts():
    return render_template('video_workouts.html')

@webcam_bp.route('/webcam_options')
def webcam_options():
    return render_template('webcam_options.html', exercises=ALL_EXERCISES)

@webcam_bp.route('/webcam_start/<exercise_name>')
def webcam_start(exercise_name):
    if 'user_email' not in session:
        flash("Please log in to start the webcam trainer.")
        return redirect(url_for('auth.login')) 
    return render_template('webcam_streamer.html', exercise=exercise_name)

@webcam_bp.route('/get_feedback/<exercise_name>')
def get_feedback(exercise_name):
    dispatcher_info = EXERCISE_DISPATCHER.get(exercise_name)
    if not dispatcher_info:
        return jsonify({'feedback': 'Error: Exercise not registered.', 'reps': 0, 'stage': 'ERROR', 'angle': 'N/A'}), 404
    feedback_state = dispatcher_info['feedback_state']
    return jsonify(feedback_state)

@webcam_bp.route('/video_feed/<exercise_name>')
def video_feed(exercise_name):
    dispatcher_info = EXERCISE_DISPATCHER.get(exercise_name)
    if not dispatcher_info:
        return Response("Exercise not found.", status=404)
    generator_func = dispatcher_info['generator']
    return Response(
        generator_func(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )