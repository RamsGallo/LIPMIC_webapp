from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response, jsonify, abort
from flask_login import login_user, logout_user, login_required, current_user
from board.models import db, SLP, Patient, AssessmentResult
from datetime import datetime
from board.quiz_data import quiz_sets
from board import lip_reader #<-- comment when testing


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

@bp.route("/design")
def design_page():
    return render_template("pages/design.html")

@bp.route("/aboutus")
def about_page():
    return render_template("pages/aboutus.html")

@bp.route("/console/")
@login_required
def console_page():
    patients = current_user.patients
    return render_template("pages/lipmic-console/index.html", patients=patients)

@bp.route("/console/assessments")
@login_required
def assessments_page():
    patients = Patient.query.filter_by(slp_id=current_user.id).all()
    return render_template("pages/lipmic-console/assessments.html", patients=patients)

@bp.route("/")
def index_page():
    return render_template("pages/index.html")

# @bp.route("/console/assessments/peabody")
# @login_required
# def peabody_page():
#     if "patient_id" not in session:
#         flash("Please select a patient before starting the assessment.")
#         return redirect(url_for("pages.assessment"))
#     patients = current_user.patients
#     return render_template("pages/lipmic-console/peabody.html", patients=patients)

@bp.route("/console/assessments/<assessment_type>")
@login_required
def assessment_page(assessment_type):
    patient_id = session.get("selected_patient_id")
    if not patient_id:
        flash("Please select a patient before starting the assessment.")
        return redirect(url_for("pages.assessments_page"))

    if assessment_type not in quiz_sets:
        abort(404)

    session["assessment"] = {
        "type": assessment_type,
        "level": "easy",
        "question_index": 0,
        "score": 0,
        "answers": [],
        "start_time": datetime.utcnow().timestamp(),
        "finished": False
    }
    session["assessment_type"] = assessment_type
    title = str(assessment_type).capitalize()
    return render_template(f"pages/lipmic-console/{assessment_type}.html", patient_id=patient_id, assessment_type=assessment_type, assessment_title=title)

# @bp.route('/quiz')
# @login_required
# def get_quiz():
#     if request.args.get("reset") == "1":
#         session.pop('level', None)
#         session.pop('index', None)
#         session.pop('score', None)
#         session.pop('answers', None)
#         return render_template("pages/lipmic-console/peabody.html")

#     if 'level' not in session:
#         session['level'] = 'easy'
#         session['index'] = 0
#         session['score'] = 0
#         session['answers'] = []

#     level = session['level']
#     index = session['index']
#     current_quiz_set = quiz_sets[level]

#     if index >= len(current_quiz_set):
#         # Advance level or finish
#         if level == 'easy':
#             session['level'] = 'medium'
#         elif level == 'medium':
#             session['level'] = 'hard'
#         else:
#             # All levels complete – save to DB
#             patient_id = session.get("patient_id")
#             if not patient_id:
#                 return jsonify({'finished': True, 'error': 'No patient selected'})

#             result = PeabodyResult(
#                 patient_id=patient_id,
#                 answers=session.get("answers", []),
#                 score=session.get("score", 0),
#                 duration=20 * 60
#             )
#             db.session.add(result)
#             db.session.commit()

#             # Optionally clear quiz session state
#             session.pop('level', None)
#             session.pop('index', None)
#             session.pop('score', None)
#             session.pop('answers', None)

#             return jsonify({
#                 'finished': True,
#                 'score': result.score,
#                 'answers': result.answers,
#                 'duration': result.duration,
#                 'saved': True
#             })

#         # Reset index for new level
#         session['index'] = 0
#         index = 0
#         current_quiz_set = quiz_sets[session['level']]

#     question = current_quiz_set[index]

#     return jsonify({
#         'prompt': question['prompt'],
#         'images': question['images'],
#         'level': session['level'],
#         'finished': False
#     })

@bp.route('/quiz/<assessment_type>')
def get_question(assessment_type):
    data = session.get('assessment', {})
    if not data or data['type'] != assessment_type:
        return jsonify({"error": "Invalid session"}), 400

    level = data["level"]
    index = data["question_index"]
    questions = quiz_sets[assessment_type][level]

    if index >= len(questions):
        # Escalate level or finish
        if level == "easy":
            level = "medium"
        elif level == "medium":
            level = "hard"
        else:
            data["finished"] = True
            session["assessment"] = data
            return jsonify({"finished": True, "score": data["score"]})

        # Reset index and fetch new level
        index = 0
        data["level"] = level
        data["question_index"] = index
        session["assessment"] = data
        
        questions = quiz_sets[assessment_type][level]

    question = questions[index]

    # print("Current level:", level)
    # print("Question index:", index) 
    # print("Question prompt:", question["prompt"])


    return jsonify({
        "prompt": question["prompt"],
        "images": question["images"],
        "finished": False,
        "score": data["score"]
    })



@bp.route('/submit_answer/<assessment_type>', methods=["POST"])
def submit_answer(assessment_type):
    data = session['assessment']
    word = request.json.get("word")

    level = data["level"]
    index = data["question_index"]
    questions = quiz_sets[assessment_type][level]

    # Avoid index error
    if index >= len(questions):
        return jsonify({"error": "No more questions at this level"}), 400

    question = questions[index]

    correct = question["correct"] == word
    if correct:
        data["score"] += 1

    data["answers"].append({
        "prompt": question["prompt"],
        "predicted": word,
        "correct": question["correct"]
    })

    data["question_index"] += 1
    session['assessment'] = data

    return jsonify({"correct": correct, "score": data["score"]})


@bp.route("/get_prediction")
def get_prediction():
    if lip_reader.predicted_word_label and not lip_reader.prediction_consumed:
        lip_reader.prediction_consumed = True
        print("hello rams")
        return jsonify({'word': lip_reader.predicted_word_label})
    return jsonify({'word': ""})

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if SLP.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('pages.register'))

        new_slp = SLP(username=username)
        new_slp.password = password
        db.session.add(new_slp)
        db.session.commit()
        flash('Registration successful. Please log in.')
        return redirect(url_for('pages.login'))

    return render_template('auth/register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        slp = SLP.query.filter_by(username=username).first()
        if slp and slp.check_password(password):
            login_user(slp)
            return redirect(url_for('pages.console_page'))

        flash('Invalid credentials')
        return redirect(url_for('pages.login'))

    return render_template('auth/login.html')

@bp.route('/console/add_patient', methods=['GET', 'POST'])
@login_required
def add_patient():
    if request.method == 'POST':
        name = request.form['name']
        new_patient = Patient(name=name, slp_id=current_user.id)
        db.session.add(new_patient)
        db.session.commit()
        flash('Patient added successfully.')
        return redirect(url_for('pages.console_page'))
    return render_template('pages/lipmic-console/add_patient.html')

@bp.route('/console/end/<int:patient_id>')
@login_required
def end_assessment(patient_id):
    assessment_type = session.get("assessment_type")
    data = session.get("assessment", {})
    patient = Patient.query.get_or_404(patient_id)
    if patient.slp_id != current_user.id:
        abort(403)
    
    if not assessment_type or not data:
        flash("No assessment in session.")
        return redirect(url_for('pages.assessments_page'))

    score = data.get("score", 0)
    answers = data.get("answers", [])
    start_time = data.get("start_time")

    print("Saving result for patient ID:", patient_id)
    print("Answers:", answers)
    print("Score:", score)
    
    duration = None
    if start_time:
        if isinstance(start_time, (int, float)):
            start_time = datetime.fromtimestamp(start_time)
        duration = int((datetime.utcnow() - start_time).total_seconds())

    result = AssessmentResult(
        assessment_type=assessment_type,
        patient_id=patient_id,
        answers=answers,
        score=score,
        duration=duration
    )
    db.session.add(result)
    db.session.commit()

    # Optional: clear the session data
    session.pop("assessment", None)
    session.pop("assessment_type", None)

    results = AssessmentResult.query.filter_by(patient_id=patient.id).order_by(AssessmentResult.date_taken.desc()).all()

    return render_template('pages/lipmic-console/patient_dashboard.html', patient=patient, results=results)


@bp.route('/console/patient/<int:patient_id>')
@login_required
def patient_dashboard(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if patient.slp_id != current_user.id:
        abort(403)
    
    results = AssessmentResult.query.filter_by(patient_id=patient.id).order_by(AssessmentResult.date_taken.desc()).all()
    return render_template("pages/lipmic-console/patient_dashboard.html", patient=patient, results=results)

@bp.route("/set_patient_by_id", methods=["POST"])
@login_required
def set_patient_by_id():
    data = request.get_json()
    patient_id = data.get("patient_id")

    if patient_id:
        session["selected_patient_id"] = patient_id
        return jsonify({"success": True})
    else:
        return jsonify({"success": False}), 400

# @bp.route("/save_peabody_result", methods=["POST"])
# @login_required
# def save_peabody_result():
#     data = request.get_json()
    
#     patient_id = data.get('patient_id')
#     answers = data.get('answers')  # This should be a JSON object containing the patient's answers and maybe some other data.
#     score = data.get('score')      # The final score
#     duration = data.get('duration')  # Optionally, the time taken for the assessment in seconds.

#     if not patient_id or not answers or score is None:
#         return jsonify(success=False, message="Missing data")

#     # Create a new PeabodyResult object
#     result = PeabodyResult(patient_id=patient_id, answers=answers, score=score, duration=duration)

#     # Add to the session and commit to the database
#     db.session.add(result)
#     db.session.commit()

#     return jsonify(success=True, message="Assessment results saved successfully")

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return render_template('pages/index.html')
