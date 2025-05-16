import os
import cv2
import dlib
import math
import numpy as np
import tensorflow as tf
from collections import deque

# Constants
VALID_WORD_THRESHOLD = 1
LIP_WIDTH = 112
LIP_HEIGHT = 80
NOT_TALKING_THRESHOLD = 10
TOTAL_FRAMES = 22
PAST_BUFFER_SIZE = 4

# Load the pre-trained model
MODEL_PATH = os.environ.get("MODEL_PATH", "Ref/directions_1.keras")
model = tf.keras.models.load_model(MODEL_PATH)

# Dlib setup
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("face_landmarks.dat")

# Labels
# label_dict = {0: 'can', 1: 'hear', 5: 'hello', 
#               3: 'help', 4: 'I', 10: 'love', 
#               6: 'need', 7: 'please', 8: 'see', 
#               9: 'speak', 12: 'watch', 11: 'we', 
#               2: 'you'}

label_dict = {0: 'down', 1: 'left', 2: 'right', 3: 'up'}

# Global variables for lip ROI and predictions
curr_word_frames = []
not_talking_counter = 0
concat_words = ""
predicted_word_label = ""
prediction_consumed = False
draw_prediction = False
past_word_frames = deque(maxlen=PAST_BUFFER_SIZE)
input_shape = (TOTAL_FRAMES, 80, 112, 3)
spoken_already = []

# Helper functions
def process_frame(frame):
    """
    Process the frame to extract the lip region and prepare for prediction.
    """
    global curr_word_frames, not_talking_counter, predicted_word_label, concat_words, draw_prediction

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = detector(gray)

    for face in faces:
        x1, y1, x2, y2 = face.left(), face.top(), face.right(), face.bottom()

        # Get landmarks
        landmarks = predictor(image=gray, box=face)

        mouth_top = (landmarks.part(51).x, landmarks.part(51).y)
        mouth_bottom = (landmarks.part(57).x, landmarks.part(57).y)
        lip_distance = math.hypot(mouth_bottom[0] - mouth_top[0], mouth_bottom[1] - mouth_top[1])

        # Extract lip region
        lip_frame = extract_and_preprocess_lip(frame, landmarks)

        if lip_distance > 45:  # Talking
            cv2.putText(frame, "Talking", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            curr_word_frames.append(lip_frame)
            not_talking_counter = 0
            
        else:  # Not talking
            cv2.putText(frame, "Not talking", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            not_talking_counter += 1

            if not_talking_counter >= NOT_TALKING_THRESHOLD and len(curr_word_frames) + PAST_BUFFER_SIZE == TOTAL_FRAMES:
                predict_word()

            elif not_talking_counter < NOT_TALKING_THRESHOLD and len(curr_word_frames) + PAST_BUFFER_SIZE < TOTAL_FRAMES and len(curr_word_frames) > VALID_WORD_THRESHOLD:
                curr_word_frames.append(lip_frame)
                not_talking_counter = 0
            
            elif len(curr_word_frames) < VALID_WORD_THRESHOLD or (not_talking_counter >= NOT_TALKING_THRESHOLD and len(curr_word_frames) + PAST_BUFFER_SIZE > TOTAL_FRAMES):
                curr_word_frames = []
            
            past_word_frames.append(lip_frame)
            if len(past_word_frames) > PAST_BUFFER_SIZE:
                past_word_frames.pop(0)

        # Visualize the landmarks on the frame
        for n in range(48, 60):
            x = landmarks.part(n).x
            y = landmarks.part(n).y
            cv2.circle(frame, (x, y), 3, (0, 255, 0), -1)

    # OpenCV overlay predictions
    """
    if draw_prediction:
        cv2.putText(frame, predicted_word_label, (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 0, 0), 2)
        # cv2.putText(frame, concat_words, (5, 450), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (255, 0, 0), 2)
    """
    return frame


def extract_and_preprocess_lip(frame, landmarks):    
    lip_left = landmarks.part(48).x
    lip_right = landmarks.part(54).x
    lip_top = landmarks.part(50).y
    lip_bottom = landmarks.part(58).y

    # Calculate padding
    width_diff = LIP_WIDTH - (lip_right - lip_left)
    height_diff = LIP_HEIGHT - (lip_bottom - lip_top)
    pad_left = max(0, min(width_diff // 2, lip_left))
    pad_right = max(0, min(width_diff - pad_left, frame.shape[1] - lip_right))
    pad_top = max(0, min(height_diff // 2, lip_top))
    pad_bottom = max(0, min(height_diff - pad_top, frame.shape[0] - lip_bottom))

    # Extract and resize lip region
    lip_frame = frame[
        lip_top - pad_top:lip_bottom + pad_bottom,
        lip_left - pad_left:lip_right + pad_right
    ]
    lip_frame = cv2.resize(lip_frame, (LIP_WIDTH, LIP_HEIGHT))

    # Preprocess the lip frame
    lip_frame_lab = cv2.cvtColor(lip_frame, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lip_frame_lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(3, 3))
    l_channel_eq = clahe.apply(l_channel)
    lip_frame_eq = cv2.merge((l_channel_eq, a_channel, b_channel))
    lip_frame_eq = cv2.cvtColor(lip_frame_eq, cv2.COLOR_LAB2BGR)
    lip_frame_eq = cv2.GaussianBlur(lip_frame_eq, (7, 7), 0)
    lip_frame_eq = cv2.bilateralFilter(lip_frame_eq, 5, 75, 75)
    kernel=np.array([
                    [-1,-1,-1],
                    [-1, 9,-1],
                    [-1,-1,-1]
                    ])

    lip_frame_eq = cv2.filter2D(lip_frame_eq, -1, kernel)
    lip_frame_eq= cv2.GaussianBlur(lip_frame_eq, (5, 5), 0)
    lip_frame = lip_frame_eq

    return lip_frame

def predict_word():
    global curr_word_frames, predicted_word_label, concat_words, draw_prediction, spoken_already, prediction_consumed
    curr_word_frames = list(past_word_frames) + curr_word_frames
    curr_data = np.array([curr_word_frames[:input_shape[0]]])
    prediction = model.predict(curr_data)
    predicted_class_index = np.argmax(prediction)
    while label_dict[predicted_class_index] in spoken_already:
        # If the predicted label has already been spoken,
        # set its probability to zero and choose the next highest probability
        prediction[0][predicted_class_index] = 0
        predicted_class_index = np.argmax(prediction)
    if len(spoken_already):
        spoken_already.pop(0)
    predicted_word_label = label_dict[predicted_class_index]
    spoken_already.append(predicted_word_label)
    print(spoken_already)
    concat_words += f" {predicted_word_label}"
    curr_word_frames = []
    prediction_consumed = False
    draw_prediction = True
    
def generate_frames():
    cap = cv2.VideoCapture(0)
    while True:
        success, frame = cap.read()
        if not success:
            break
        frame = process_frame(frame)
        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    cap.release()