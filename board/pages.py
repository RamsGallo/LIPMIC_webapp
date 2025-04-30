from flask import Blueprint, Flask, Response, render_template, jsonify
# from board import app #comment this line to remove the ML model service

bp = Blueprint("pages", __name__)

@bp.route("/project-lipmic")
def prediction_page():
    return render_template("pages/project-lipmic.html")

@bp.route("/video_feed")
def video_feed():
    return Response(app.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@bp.route("/prediction")
def get_prediction():
    """
    Serve the current prediction and full concatenated text as JSON.
    """
    return jsonify(prediction=app.predicted_word_label, full_text=app.concat_words)

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