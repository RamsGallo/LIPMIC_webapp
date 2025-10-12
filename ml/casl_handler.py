from .base_model_handler import BaseLipModelHandler
from board.quiz_data import quiz_sets
import cv2
import math
import numpy as np

class CASLHandler(BaseLipModelHandler):
    def __init__(self):
        label_dict = {0: 'down', 1: 'left', 2: 'right', 3: 'up'}
        super().__init__(model_path="C:/Users/zergs/Desktop/LIPMIC_webapp/Ref/directions_2.keras", label_dict=label_dict)
        self.suppression_window_size = 2
        self.penalty_factor = 0.5

    def is_talking(self, landmarks):
        mouth_top = (landmarks.part(51).x, landmarks.part(51).y)
        mouth_bottom = (landmarks.part(57).x, landmarks.part(57).y)
        distance = math.hypot(mouth_bottom[0] - mouth_top[0], mouth_bottom[1] - mouth_top[1])
        return distance > 45

    def postprocess_prediction(self, prediction):
        current_prediction_scores = np.copy(prediction[0])
        initial_idx = np.argmax(current_prediction_scores)
        initial_word = self.label_dict[initial_idx]
        recent_spoken_already = list(self.spoken_already)[-self.suppression_window_size:]
        if initial_word in recent_spoken_already:
            # Apply a penalty to its score
            current_prediction_scores[initial_idx] *= self.penalty_factor
        
        # Now find the new best prediction after potential penalty
        idx = np.argmax(current_prediction_scores)
        word = self.label_dict[idx]

        # Manage the spoken_already list (fixed size deque-like behavior)
        if len(self.spoken_already) >= self.suppression_window_size:
            self.spoken_already.pop(0) # Remove the oldest
        self.spoken_already.append(word)

        self.predicted_word_label = word
        # print("CASL prediction:", word)
    
    def generate_frames(self):
        cap = cv2.VideoCapture(0)
        try:
            while True:
                success, frame = cap.read()
                if not success:
                    break
                frame = self.process_frame(frame)
                _, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        finally:
            cap.release()