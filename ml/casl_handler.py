from .base_model_handler import BaseLipModelHandler
from board.quiz_data import quiz_sets
import cv2
import math
import numpy as np

class CASLHandler(BaseLipModelHandler):
    def __init__(self):
        label_dict = {0: 'down', 1: 'left', 2: 'right', 3: 'up'}
        super().__init__(model_path="Ref/directions_1.keras", label_dict=label_dict)
        # Add these new parameters to control the prediction logic
        self.suppression_window_size = 2  # How many recent words to consider for suppression
        self.penalty_factor = 0.5         # How much to penalize a suppressed word's score

    def is_talking(self, landmarks):
        mouth_top = (landmarks.part(51).x, landmarks.part(51).y)
        mouth_bottom = (landmarks.part(57).x, landmarks.part(57).y)
        distance = math.hypot(mouth_bottom[0] - mouth_top[0], mouth_bottom[1] - mouth_top[1])
        return distance > 45

    def postprocess_prediction(self, prediction):
        # Ensure prediction is a 1D array of scores (e.g., from model.predict)
        # prediction[0] is typically what you get from model.predict for a single sample
        current_prediction_scores = np.copy(prediction[0])

        # Get the index and word of the top prediction before any modification
        initial_idx = np.argmax(current_prediction_scores)
        initial_word = self.label_dict[initial_idx]

        # Get the recent spoken words based on the suppression window
        recent_spoken_already = list(self.spoken_already)[-self.suppression_window_size:]

        # If the top predicted word is in the recent suppression window
        if initial_word in recent_spoken_already:
            # Apply a penalty to its score
            current_prediction_scores[initial_idx] *= self.penalty_factor
        
        # Now find the new best prediction after potential penalty
        idx = np.argmax(current_prediction_scores)
        word = self.label_dict[idx]

        # Manage the spoken_already list (fixed size deque-like behavior)
        if len(self.spoken_already) >= self.suppression_window_size:
            self.spoken_already.pop(0) # Remove the oldest
        self.spoken_already.append(word) # Add the newest predicted word

        self.predicted_word_label = word
        print("CASL prediction:", word)

    def get_question(self, level, index):
        questions = quiz_sets["casl"][level]
        if index >= len(questions):
            return None, True  # advance level
        return questions[index], False

    def check_answer(self, level, index, answer):
        try:
            correct = quiz_sets["casl"][level][index]["correct"]
            return correct == answer
        except (KeyError, IndexError) as e:
            print(f"[check_answer] Invalid level/index: {level}/{index} - {e}")
            return False

    def get_question_data(self, level, index):
        return quiz_sets["casl"][level][index]
    
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