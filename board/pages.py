from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response, jsonify, abort
from flask_login import login_user, logout_user, login_required, current_user
from board.models import db, SLP, Patient, AssessmentSession, PeabodyResult
from datetime import datetime
from board.quiz_data import quiz_sets
# from board import lip_reader


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

@bp.route("/console/assessments/peabody")
@login_required
def peabody_page():
    if "patient_id" not in session:
        flash("Please select a patient before starting the assessment.")
        return redirect(url_for("pages.assessment"))
    patients = current_user.patients
    return render_template("pages/lipmic-console/peabody.html", patients=patients)

@bp.route('/quiz')
@login_required
def get_quiz():
    if request.args.get("reset") == "1":
        session.pop('level', None)
        session.pop('index', None)
        session.pop('score', None)
        session.pop('answers', None)
        return render_template("pages/lipmic-console/peabody.html")

    if 'level' not in session:
        session['level'] = 'easy'
        session['index'] = 0
        session['score'] = 0
        session['answers'] = []

    level = session['level']
    index = session['index']
    current_quiz_set = quiz_sets[level]

    if index >= len(current_quiz_set):
        # Advance level or finish
        if level == 'easy':
            session['level'] = 'medium'
        elif level == 'medium':
            session['level'] = 'hard'
        else:
            # All levels complete – save to DB
            patient_id = session.get("patient_id")
            if not patient_id:
                return jsonify({'finished': True, 'error': 'No patient selected'})

            result = PeabodyResult(
                patient_id=patient_id,
                answers=session.get("answers", []),
                score=session.get("score", 0),
                duration=20 * 60
            )
            db.session.add(result)
            db.session.commit()

            # Optionally clear quiz session state
            session.pop('level', None)
            session.pop('index', None)
            session.pop('score', None)
            session.pop('answers', None)

            return jsonify({
                'finished': True,
                'score': result.score,
                'answers': result.answers,
                'duration': result.duration,
                'saved': True
            })

        # Reset index for new level
        session['index'] = 0
        index = 0
        current_quiz_set = quiz_sets[session['level']]

    question = current_quiz_set[index]

    return jsonify({
        'prompt': question['prompt'],
        'images': question['images'],
        'level': session['level'],
        'finished': False
    })


@bp.route("/submit_answer", methods=["POST"])
def submit_answer():
    data = request.get_json()
    spoken_direction = data.get("word")

    level = session['level']
    index = session['index']
    question = quiz_sets[level][index]
    correct = question['correct']

    if 'answers' not in session:
        session['answers'] = []

    # Record this answer
    session['answers'].append({
        'level': level,
        'index': index,
        'prompt': question['prompt'],
        'images': question['images'],
        'predicted': spoken_direction,
        'correct': correct,
        'is_correct': spoken_direction == correct,
        'timestamp': datetime.utcnow().isoformat()
    })

    # Scoring
    if spoken_direction == correct:
        session['score'] += 1

    session['index'] += 1

    # Reset lip_reader prediction
    lip_reader.predicted_word_label = ""
    lip_reader.prediction_consumed = False

    return jsonify({'correct': spoken_direction == correct})


@bp.route("/get_prediction")
def get_prediction():
    if lip_reader.predicted_word_label and not lip_reader.prediction_consumed:
        lip_reader.prediction_consumed = True
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

@bp.route('/console/patient/<int:patient_id>')
@login_required
def patient_dashboard(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if patient.slp_id != current_user.id:
        abort(403)
    
    peabody_results = PeabodyResult.query.filter_by(patient_id=patient.id).order_by(PeabodyResult.date_taken.desc()).all()
    return render_template("pages/lipmic-console/patient_dashboard.html", patient=patient, peabody_results=peabody_results)

@bp.route("/set_patient_by_id", methods=["POST"])
@login_required
def set_patient_by_id():
    data = request.get_json()
    patient_id = data.get("patient_id")
    if not patient_id:
        return jsonify(success=False)

    patient = Patient.query.filter_by(id=patient_id, slp_id=current_user.id).first()
    if not patient:
        return jsonify(success=False)

    session["patient_id"] = patient.id
    return jsonify(success=True)

@bp.route("/save_peabody_result", methods=["POST"])
@login_required
def save_peabody_result():
    data = request.get_json()
    
    patient_id = data.get('patient_id')
    answers = data.get('answers')  # This should be a JSON object containing the patient's answers and maybe some other data.
    score = data.get('score')      # The final score
    duration = data.get('duration')  # Optionally, the time taken for the assessment in seconds.

    if not patient_id or not answers or score is None:
        return jsonify(success=False, message="Missing data")

    # Create a new PeabodyResult object
    result = PeabodyResult(patient_id=patient_id, answers=answers, score=score, duration=duration)

    # Add to the session and commit to the database
    db.session.add(result)
    db.session.commit()

    return jsonify(success=True, message="Assessment results saved successfully")

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return render_template('pages/index.html')
