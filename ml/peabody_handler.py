from .base_model_handler import BaseLipModelHandler
from board.quiz_data import quiz_sets
import cv2
import math

class PeabodyHandler(BaseLipModelHandler):
    def __init__(self):
        label_dict = {0: 'down', 1: 'left', 2: 'right', 3: 'up'}
        super().__init__(model_path="Ref/directions_1.keras", label_dict=label_dict)

    def is_talking(self, landmarks):
        mouth_top = (landmarks.part(51).x, landmarks.part(51).y)
        mouth_bottom = (landmarks.part(57).x, landmarks.part(57).y)
        distance = math.hypot(mouth_bottom[0] - mouth_top[0], mouth_bottom[1] - mouth_top[1])
        return distance > 45

    def postprocess_prediction(self, prediction):
        import numpy as np
        idx = np.argmax(prediction)
        word = self.label_dict[idx]
        if word in self.spoken_already:
            prediction[0][idx] = 0
            idx = np.argmax(prediction)
            word = self.label_dict[idx]
        if len(self.spoken_already):
            self.spoken_already.pop(0)
        self.spoken_already.append(word)
        self.predicted_word_label = word
        print("Peabody prediction:", word)

    def get_question(self, level, index):
        questions = quiz_sets["peabody"][level]
        if index >= len(questions):
            return None, True  # advance level
        return questions[index], False

    def check_answer(self, level, index, answer):
        try:
            correct = quiz_sets["peabody"][level][index]["correct"]
            return correct == answer
        except (KeyError, IndexError) as e:
            print(f"[check_answer] Invalid level/index: {level}/{index} - {e}")
            return False

    def get_question_data(self, level, index):
        return quiz_sets["peabody"][level][index]
    
    def generate_frames(self):
        cap = cv2.VideoCapture(0)
        while True:
            success, frame = cap.read()
            if not success:
                break
            frame = self.process_frame(frame)
            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        cap.release()
