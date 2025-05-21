from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response, jsonify, abort
from flask_login import login_user, logout_user, login_required, current_user
from board.models import db, SLP, Patient, AssessmentResult
from datetime import datetime
from board.quiz_data import quiz_sets
# from board import lip_reader #<-- comment when testing
from ml.peabody_handler import PeabodyHandler

model_handlers = {
    "peabody": PeabodyHandler(),
    # "emotion": EmotionHandler(),
}

def get_handler(assessment_type):
    return model_handlers.get(assessment_type)

bp = Blueprint("pages", __name__)

@bp.route("/project-lipmic")
def prediction_page():
    return render_template("pages/project-lipmic.html")

@bp.route("/video_feed")
def video_feed():
    assessment_type = session.get("assessment_type")
    handler = get_handler(assessment_type)

    if handler and hasattr(handler, "generate_frames"):
        return Response(handler.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    
    return abort(404, description="Video feed not available for this assessment.")

@bp.route("/get_prediction")
def get_prediction():
    assessment_type = session.get("assessment_type")
    handler = get_handler(assessment_type)

    if handler and not handler.prediction_consumed:
        word = handler.predicted_word_label
        handler.prediction_consumed = True
        return jsonify({'word': word})

    return jsonify({'word': ""})

# @bp.route("/video_feed")
# def video_feed():
#     return Response(lip_reader.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

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


@bp.route('/quiz/<assessment_type>')
def get_question(assessment_type):
    data = session.get('assessment', {})
    if not data or data['type'] != assessment_type:
        return jsonify({"error": "Invalid session"}), 400

    handler = get_handler(assessment_type)
    if not handler:
        return jsonify({"error": "Unknown assessment type"}), 400

    level = data["level"]
    index = data["question_index"]

    try:
        question, should_advance = handler.get_question(level, index)
    except IndexError:
        return jsonify({"error": "No more questions"}), 400

    if should_advance:
        if level == "easy":
            data["level"] = "medium"
        elif level == "medium":
            data["level"] = "hard"
        else:
            data["finished"] = True
            session["assessment"] = data
            return jsonify({"finished": True, "score": data["score"]})

        # ✅ Reset index and call get_question for next level
        data["question_index"] = 0
        level = data["level"]
        index = data["question_index"]
        try:
            question, _ = handler.get_question(level, index)
        except IndexError:
            return jsonify({"error": "No more questions"}), 400

    # ✅ Increment question index AFTER getting the current one
    data["question_index"] += 1
    session["assessment"] = data

    return jsonify({
        "prompt": question["prompt"],
        "images": question["images"],
        "finished": False,
        "score": data["score"]
    })

@bp.route('/submit_answer/<assessment_type>', methods=["POST"])
def submit_answer(assessment_type):
    data = session.get('assessment', {})
    if not data or data['type'] != assessment_type:
        return jsonify({"error": "Invalid session"}), 400

    word = request.json.get("word")
    handler = get_handler(assessment_type)
    if not handler: 
        return jsonify({"error": "Unknown assessment type"}), 400

    level = data["level"]
    index = data["question_index"] - 1

    correct = handler.check_answer(level, index, word)
    if correct:
        data["score"] += 1

    question = handler.get_question_data(level, index)  # returns static info like correct label
    data["answers"].append({
        "prompt": question["prompt"],
        "predicted": word,
        "correct": question["correct"]
    })

    session["assessment"] = data

    return jsonify({"correct": correct, "score": data["score"]})


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
        # CLIENT data 
        name = request.form['name']
        age = request.form['age']
        sex = request.form['sex']
        address = request.form['address']
        dob = request.form['dob']
        religion = request.form['religion']
        diagnosis = request.form['diagnosis']
        doe = request.form['doe']
        precautions = request.form['precautions']
        current_medication = request.form['current_medication']
        emergency_person = request.form['emergency_person']
        contact_no = request.form['contact_no']
        alt_contact_no = request.form['alt_contact_no']
        grade_level = request.form['grade_level']

        # FAMILY data
        father_name = request.form['father_name']
        father_contact_no = request.form['father_contact_no']
        father_med_history = request.form['father_med_history']
        mother_name = request.form['mother_name']
        mother_contact_no = request.form['mother_contact_no']
        mother_med_history = request.form['mother_med_history']
        sibling = request.form['sibling']
        sibling_med_history = request.form['sibling_med_history']

        # MEDICAL data
        complication_preg = request.form['complication_preg']
        med_taken = request.form['med_taken']
        duration_med_taken = request.form['duration_med_taken']
        typeOfDelivery = request.form['typeOfDelivery']
        complication_deli = request.form['complication_deli']
        birth_weight = request.form['birth_weight']
        birth_problem = request.form['birth_problem']
        medication = request.form['medication']
        immunization = request.form['immunization']
        effects = request.form['effects']
        
        # DEV'T data
        # GMS data
        gms_0 = request.form['gms_0']
        gms_1 = request.form['gms_1']
        gms_2 = request.form['gms_2']
        gms_3 = request.form['gms_3']
        gms_4 = request.form['gms_4']
        gms_5 = request.form['gms_5']
        gms_6 = request.form['gms_6']
        gms_7 = request.form['gms_7']
        gms_8 = request.form['gms_8']
        gms_9 = request.form['gms_9']
        gms_10 = request.form['gms_10']

        # FMS data
        fms_0 = request.form['fms_0']
        fms_1 = request.form['fms_1']
        fms_2 = request.form['fms_2']
        fms_3 = request.form['fms_3']
        fms_4 = request.form['fms_4']
        fms_5 = request.form['fms_5']
        fms_6 = request.form['fms_6']
        fms_7 = request.form['fms_7']
        fms_8 = request.form['fms_8']
        fms_9 = request.form['fms_9']

        # ADL data
        adl_0 = request.form['adl_0']
        adl_1 = request.form['adl_1']
        adl_2 = request.form['adl_2']
        adl_3 = request.form['adl_3']
        adl_4 = request.form['adl_4']
        adl_5 = request.form['adl_5']
        adl_6 = request.form['adl_6']

        # COGNITIVE data
        cog_0 = request.form['cog_0']
        cog_1 = request.form['cog_1']
        cog_2 = request.form['cog_2']
        cog_3 = request.form['cog_3']
        cog_4 = request.form['cog_4']
        cog_5 = request.form['cog_5']
        cog_6 = request.form['cog_6']

        # ORAL data
        omd_0 = request.form['omd_0']
        omd_1 = request.form['omd_1']
        omd_2 = request.form['omd_2']
        omd_3 = request.form['omd_3']
        omd_4 = request.form['omd_4']
        omd_5 = request.form['omd_5']
        omd_6 = request.form['omd_6']
        omd_7 = request.form['omd_7']
        omd_8 = request.form['omd_8']
        omd_9 = request.form['omd_9']

        new_patient = Patient(name=name, age=age, sex=sex, 
                              address=address, dob=dob, religion=religion, diagnosis=diagnosis, doe=doe, precautions=precautions, current_medication=current_medication, emergency_person=emergency_person, contact_no=contact_no, alt_contact_no=alt_contact_no, grade_level=grade_level, father_name=father_name, father_contact_no=father_contact_no, father_med_history=father_med_history, mother_name=mother_name, mother_contact_no=mother_contact_no, mother_med_history=mother_med_history, sibling=sibling, sibling_med_history=sibling_med_history, complication_preg=complication_preg, med_taken=med_taken, duration_med_taken=duration_med_taken, typeOfDelivery=typeOfDelivery, complication_deli=complication_deli, birth_weight=birth_weight, birth_problem=birth_problem, medication=medication, immunization=immunization, effects=effects, gms_0=gms_0,gms_1=gms_1,gms_2=gms_2,gms_3=gms_3,gms_4=gms_4,gms_5=gms_5,gms_6=gms_6,gms_7=gms_7,gms_8=gms_8,gms_9=gms_9,gms_10=gms_10, fms_0=fms_0,fms_1=fms_1,fms_2=fms_2,fms_3=fms_3,fms_4=fms_4,fms_5=fms_5,fms_6=fms_6,fms_7=fms_7,fms_8=fms_8,fms_9=fms_9, adl_0=adl_0,adl_1=adl_1,adl_2=adl_2,adl_3=adl_3,adl_4=adl_4,adl_5=adl_5,adl_6=adl_6, cog_0=cog_0,cog_1=cog_1,cog_2=cog_2,cog_3=cog_3,cog_4=cog_4,cog_5=cog_5,cog_6=cog_6, omd_0=omd_0,omd_1=omd_1,omd_2=omd_2,omd_3=omd_3,omd_4=omd_4,omd_5=omd_5,omd_6=omd_6,omd_7=omd_7,omd_8=omd_8,omd_9=omd_9, slp_id=current_user.id)
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
