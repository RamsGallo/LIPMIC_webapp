from flask import Blueprint, Flask, Response, render_template, jsonify, session
from board.quiz_data import quiz_sets
# from board import app #comment this line to remove the ML model service
from board import lip_reader
# from board.lip_reader import LipReader
# lip_reader = LipReader()

bp = Blueprint("pages", __name__)

@bp.route("/project-lipmic")
def prediction_page():
    return render_template("pages/project-lipmic.html")

@bp.route("/video_feed")
def video_feed():
    return Response(lip_reader.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# @bp.route("/prediction")
# def get_prediction():
#     return jsonify(prediction=lip_reader.predicted_word_label)

@bp.route("/console/assessments/peabody")
def peabody_page():
    return render_template("pages/lipmic-console/peabody.html")

@bp.route("/design")
def design_page():
    return render_template("pages/design.html")

@bp.route("/aboutus")
def about_page():
    return render_template("pages/aboutus.html")

@bp.route("/console/")
def console_page():
    return render_template("pages/lipmic-console/index.html")

@bp.route("/console/assessments")
def assessments_page():
    return render_template("pages/lipmic-console/assessments.html")

@bp.route("/")
def index_page():
    return render_template("pages/index.html")

@bp.route('/quiz')
def get_quiz():
    if request.args.get("reset") == "1":
        session.clear()
        return render_template("pages/lipmic-console/peabody.html")
    
    if 'level' not in session:
        session['level'] = 'easy'
        session['index'] = 0
        session['score'] = 0

    level = session['level']
    index = session['index']

    current_quiz_set = quiz_sets[level]

    if index >= len(current_quiz_set):
        # Move to next level
        if level == 'easy':
            session['level'] = 'medium'
        elif level == 'medium':
            session['level'] = 'hard'
        else:
            return jsonify({'finished': True, 'score': session['score']})
        session['index'] = 0
        index = 0

    question = quiz_sets[session['level']][index]

    return jsonify({
        'prompt': question['prompt'],
        'images': question['images'],
        'level': session['level'],
        'finished': False
    })

from flask import request

@bp.route("/submit_answer", methods=["POST"])
def submit_answer():
    
    data = request.get_json()
    spoken_direction = data.get("direction")

    level = session['level']
    index = session['index']
    correct = quiz_sets[level][index]['correct']

    if spoken_direction == correct:
        session['score'] += 1

    print("at submit: ", lip_reader.prediction_consumed)
    
    session['index'] += 1

    lip_reader.predicted_word_label = ""
    lip_reader.prediction_consumed = False

    return jsonify({'correct': spoken_direction == correct})

@bp.route("/get_prediction")
def get_prediction():
    if lip_reader.predicted_word_label and not lip_reader.prediction_consumed:
        lip_reader.prediction_consumed = True
        return jsonify({'word': lip_reader.predicted_word_label})
    return jsonify({'word': ""})
