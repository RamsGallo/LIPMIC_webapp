# Create a new file: services.py or utils.py
def group_frames_by_question(assessment_result):
    """Group lip frames by question index"""
    frames_by_question = {}
    for frame in assessment_result.lip_frames:
        if frame.question_index not in frames_by_question:
            frames_by_question[frame.question_index] = []
        frames_by_question[frame.question_index].append(frame)
    
    # Sort frames within each question by frame_index
    for question_idx in frames_by_question:
        frames_by_question[question_idx].sort(key=lambda f: f.frame_index)
    
    return frames_by_question
