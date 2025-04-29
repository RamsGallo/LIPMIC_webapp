# import cv2
# import dlib
# import math
# import numpy as np
# from collections import deque

# detector = dlib.get_frontal_face_detector()
# predictor = dlib.shape_predictor("face_landmarks.dat")


# class Video(object):
#     def __init__(self):
#         self.video = cv2.VideoCapture(0)
#     def __del__(self):
#         self.video.release()
#     def get_frame(self):        
#         TOTAL_FRAMES = 22
#         VALID_WORD_THRESHOLD = 1
#         NOT_TALKING_THRESHOLD = 10
#         PAST_BUFFER_SIZE = 4
#         LIP_WIDTH = 112
#         LIP_HEIGHT = 80

#         input_shape = (TOTAL_FRAMES, 80, 112, 3)

#         not_talking_counter = 0
#         curr_word_frames = []
#         past_word_frames = deque(maxlen=PAST_BUFFER_SIZE)
#         spoken_already = []
#         label_dict={0: 'can', 1: 'hear', 5: 'hello', 
#                     3: 'help', 4: 'I', 12: 'love', 
#                     6: 'need', 7: 'please', 8: 'see', 
#                     9: 'speak', 10: 'watch', 11: 'we', 
#                     2: 'you'}
#         while True:
#             ret, frame = self.video.read()
#             gray = cv2.cvtColor(src=frame, code=cv2.COLOR_BGR2GRAY)
#             faces = detector(gray)
            

#             for face in faces:
#                 x1 = face.left()  # left point
#                 y1 = face.top()  # top point
#                 x2 = face.right()  # right point
#                 y2 = face.bottom()  # bottom point

#                 Create landmark object
#                 landmarks = predictor(image=gray, box=face)

#                 Calculate the distance between the upper and lower lip landmarks
#                 mouth_top = (landmarks.part(51).x, landmarks.part(51).y)
#                 mouth_bottom = (landmarks.part(57).x, landmarks.part(57).y)
#                 lip_distance = math.hypot(mouth_bottom[0] - mouth_top[0], mouth_bottom[1] - mouth_top[1])

#                 lip_left = landmarks.part(48).x
#                 lip_right = landmarks.part(54).x
#                 lip_top = landmarks.part(50).y
#                 lip_bottom = landmarks.part(58).y

#                 Add padding if necessary to get a frame
#                 width_diff = LIP_WIDTH - (lip_right - lip_left)
#                 height_diff = LIP_HEIGHT - (lip_bottom - lip_top)
#                 pad_left = width_diff // 2
#                 pad_right = width_diff - pad_left
#                 pad_top = height_diff // 2
#                 pad_bottom = height_diff - pad_top

#                 Ensure that the padding doesn't extend beyond the original frame
#                 pad_left = min(pad_left, lip_left)
#                 pad_right = min(pad_right, frame.shape[1] - lip_right)
#                 pad_top = min(pad_top, lip_top)
#                 pad_bottom = min(pad_bottom, frame.shape[0] - lip_bottom)

#                 Create padded lip region
#                 lip_frame = frame[lip_top - pad_top:lip_bottom + pad_bottom, lip_left - pad_left:lip_right + pad_right]
#                 lip_frame = cv2.resize(lip_frame, (LIP_WIDTH, LIP_HEIGHT))

                
#                 lip_frame_lab = cv2.cvtColor(lip_frame, cv2.COLOR_BGR2LAB)
#                 Apply contrast stretching to the L channel of the LAB image
#                 l_channel, a_channel, b_channel = cv2.split(lip_frame_lab)
#                 clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(3,3))
#                 l_channel_eq = clahe.apply(l_channel)

#                 Merge the equalized L channel with the original A and B channels
#                 lip_frame_eq = cv2.merge((l_channel_eq, a_channel, b_channel))
#                 lip_frame_eq = cv2.cvtColor(lip_frame_eq, cv2.COLOR_LAB2BGR)
#                 lip_frame_eq = cv2.GaussianBlur(lip_frame_eq, (7, 7), 0)
#                 lip_frame_eq = cv2.bilateralFilter(lip_frame_eq, 5, 75, 75)
#                 kernel=np.array([[-1,-1,-1],[-1, 9,-1],[-1,-1,-1]])

#                 Apply the kernel to the input image
#                 lip_frame_eq = cv2.filter2D(lip_frame_eq, -1, kernel)
#                 lip_frame_eq = cv2.GaussianBlur(lip_frame_eq, (5, 5), 0)
#                 lip_frame = lip_frame_eq
                
#                 Draw a circle around the mouth
#                 for n in range(48, 60):
#                     x = landmarks.part(n).x
#                     y = landmarks.part(n).y
#                     cv2.circle(img=frame, center=(x, y), radius=2, color=(0, 255, 0), thickness=-1)

#                 if lip_distance > 45: # person is talking
#                     cv2.putText(frame, "Talking", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
#                     curr_word_frames += [lip_frame.tolist()]         
#                     not_talking_counter = 0
#                     draw_prediction = False
#                     print(len(curr_word_frames))
                
#                 else:
#                     cv2.putText(frame, "Not talking", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
#                     not_talking_counter += 1

#                     if not_talking_counter >= NOT_TALKING_THRESHOLD and len(curr_word_frames) + PAST_BUFFER_SIZE == TOTAL_FRAMES: 
#                         curr_word_frames = list(past_word_frames) + curr_word_frames

#                         curr_data = np.array([curr_word_frames[:input_shape[0]]])

#                         print(curr_data)
#                         print(spoken_already)
                        
#                         """
#                         prediction = model.predict(curr_data)

#                         predicted_class_index = np.argmax(prediction)

#                         predicted_word_label = label_dict[predicted_class_index]
#                         spoken_already.append(predicted_word_label)

#                         concat_words += " "+predicted_word_label

#                         print("FINISHED!", predicted_word_label)
#                         draw_prediction = True
#                         count = 0

#                         while label_dict[predicted_class_index] in spoken_already:
#                             If the predicted label has already been spoken,
#                             set its probability to zero and choose the next highest probability
#                             prediction[0][predicted_class_index] = 0
#                             predicted_class_index = np.argmax(prediction)

#                         curr_word_frames = []
#                         not_talking_counter = 0
#                         """

#                     elif not_talking_counter < NOT_TALKING_THRESHOLD and len(curr_word_frames) + PAST_BUFFER_SIZE < TOTAL_FRAMES and len(curr_word_frames) > VALID_WORD_THRESHOLD:
#                         curr_word_frames += [lip_frame.tolist()]
#                         not_talking_counter = 0
                
#                     elif len(curr_word_frames) < VALID_WORD_THRESHOLD or (not_talking_counter >= NOT_TALKING_THRESHOLD and len(curr_word_frames) + PAST_BUFFER_SIZE > TOTAL_FRAMES):
#                         curr_word_frames = []

#                     past_word_frames+= [lip_frame.tolist()]

#                     if len(past_word_frames) > PAST_BUFFER_SIZE:
#                         past_word_frames.pop(0)
#             """
#             if(draw_prediction and count < 20):
#                 count += 1
#                 cv2.putText(frame, predicted_word_label, (50,100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 0, 0), 2)
        
#             if(draw_prediction):
#                 cv2.putText(frame, concat_words, (5,350), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (255, 0, 0), 2)
#             """
                
#             ret, jpg = cv2.imencode('.jpg', frame)
#             data_encode = np.array(jpg)
#             byte_encode = data_encode.tobytes()

#             return byte_encode