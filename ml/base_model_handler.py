import cv2
import dlib
import math
import numpy as np
from collections import deque
from abc import ABC, abstractmethod

class BaseLipModelHandler(ABC):
    def __init__(self, model_path,label_dict,total_frames=22,lip_size=(112, 80),past_buffer_size=4,valid_threshold=1,not_talking_thres=10):
        import tensorflow as tf
        self.model = tf.keras.models.load_model(model_path)
        self.label_dict = label_dict
        self.TOTAL_FRAMES = total_frames
        self.LIP_WIDTH, self.LIP_HEIGHT = lip_size
        self.PAST_BUFFER_SIZE = past_buffer_size
        self.VALID_WORD_THRESHOLD = valid_threshold
        self.NOT_TALKING_THRESHOLD = not_talking_thres

        self.curr_word_frames = []
        self.past_word_frames = deque(maxlen=past_buffer_size)
        self.predicted_word_label = ""
        self.prediction_consumed = False
        self.spoken_already = []
        self.not_talking_counter = 0

        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor("face_landmarks.dat")

    @abstractmethod
    def is_talking(self, landmarks):
        """Returns True if the person is currently talking."""
        pass

    @abstractmethod
    def postprocess_prediction(self, prediction):
        """Handles what to do with the model prediction."""
        pass

    def process_frame(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detector(gray)

        if len(faces) == 0:
            print("No face found")
            return frame

        for face in faces:
            landmarks = self.predictor(image=gray, box=face)
            lip_frame = self.extract_lip(frame, landmarks)

            for n in range(48, 60):
                x = landmarks.part(n).x
                y = landmarks.part(n).y
                cv2.circle(frame, (x, y), 3, (0, 255, 0), -1)

            if self.is_talking(landmarks):
                self.curr_word_frames.append(lip_frame)
                self.not_talking_counter = 0
            else:
                cv2.putText(frame, "Not talking", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                self.not_talking_counter += 1

                if self.not_talking_counter >= self.NOT_TALKING_THRESHOLD and len(self.curr_word_frames) + self.PAST_BUFFER_SIZE == self.TOTAL_FRAMES:
                    cv2.putText(frame, "Talking", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    self.predict_word()

                elif self.not_talking_counter < self.NOT_TALKING_THRESHOLD and len(self.curr_word_frames) + self.PAST_BUFFER_SIZE < self.TOTAL_FRAMES and len(self.curr_word_frames) > self.VALID_WORD_THRESHOLD:
                    #print("Reset not talking counter")
                    self.curr_word_frames.append(lip_frame)
                    self.not_talking_counter = 0

                elif len(self.curr_word_frames) < self.VALID_WORD_THRESHOLD or (self.not_talking_counter >= self.NOT_TALKING_THRESHOLD and len(self.curr_word_frames) + self.PAST_BUFFER_SIZE > self.TOTAL_FRAMES):
                    #print("Reset Frames")
                    self.curr_word_frames = []
                
                else:
                    #print("pass")
                    pass

                self.past_word_frames.append(lip_frame)
                if len(self.past_word_frames) > self.PAST_BUFFER_SIZE:
                   self.past_word_frames.pop(0)
        return frame

    def extract_lip(self, frame, landmarks):
        lip_left = landmarks.part(48).x
        lip_right = landmarks.part(54).x
        lip_top = landmarks.part(50).y
        lip_bottom = landmarks.part(58).y

        width_diff = self.LIP_WIDTH - (lip_right - lip_left)
        height_diff = self.LIP_HEIGHT - (lip_bottom - lip_top)
        pad_left = max(0, min(width_diff // 2, lip_left))
        pad_right = max(0, min(width_diff - pad_left, frame.shape[1] - lip_right))
        pad_top = max(0, min(height_diff // 2, lip_top))
        pad_bottom = max(0, min(height_diff - pad_top, frame.shape[0] - lip_bottom))

        lip_frame = frame[lip_top - pad_top:lip_bottom + pad_bottom, lip_left - pad_left:lip_right + pad_right]
        lip_frame = cv2.resize(lip_frame, (self.LIP_WIDTH, self.LIP_HEIGHT))
        return lip_frame

    def predict_word(self):
        self.curr_word_frames = list(self.past_word_frames) + self.curr_word_frames
        data = np.array([self.curr_word_frames[:self.TOTAL_FRAMES]])
        prediction = self.model.predict(data)
        self.postprocess_prediction(prediction)
        self.last_predicted_frames = self.curr_word_frames[:self.TOTAL_FRAMES]
        self.curr_word_frames = []
        self.prediction_consumed = False