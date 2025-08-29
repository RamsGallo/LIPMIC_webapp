from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response, jsonify, abort, send_from_directory, current_app, make_response
from flask_login import login_user, logout_user, login_required, current_user
from board.models import db, SLP, Patient, AssessmentResult, LipFrame, Goal
from datetime import datetime, date
from board.quiz_data import quiz_sets
from ml.peabody_handler import PeabodyHandler
from ml.casl_handler import CASLHandler
from pathlib import Path
import google.generativeai as genai
from werkzeug.utils import secure_filename
from board.utils import group_frames_by_question
from xhtml2pdf import pisa
import io
import cv2
import os
import uuid


model_handlers = {
    "peabody": PeabodyHandler(),
    "casl": CASLHandler(),
}

def get_handler(assessment_type):
    return model_handlers.get(assessment_type)

bp = Blueprint("pages", __name__)

count = 0
max = 13
count_ = 0

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/test_intervention_format')
def test_intervention_format():
    sample_text1 = "1. This is point one. 2. This is point two. 3. This is point three."
    sample_text2 = "* Bullet one\n* Bullet two"
    sample_text3 = "Just a paragraph of text. It has multiple sentences but no list formatting."
    sample_text4 = "1. First item.\n2. Second item.\n3. Third item."
    sample_text5 = "- Another bullet\n- And another"
    sample_text6 = "Not a list, just text with\nnewlines. Maybe some\r\nother newlines too."


    # Get the filter function from the app context (it's registered there)
    # This requires a request context, so it needs to be in a route.
    with current_app.app_context():
        formatted_text1 = current_app.jinja_env.filters['format_intervention'](sample_text1)
        formatted_text2 = current_app.jinja_env.filters['format_intervention'](sample_text2)
        formatted_text3 = current_app.jinja_env.filters['format_intervention'](sample_text3)
        formatted_text4 = current_app.jinja_env.filters['format_intervention'](sample_text4)
        formatted_text5 = current_app.jinja_env.filters['format_intervention'](sample_text5)
        formatted_text6 = current_app.jinja_env.filters['format_intervention'](sample_text6)


    response_html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Intervention Format Test</title></head>
    <body>
        <h1>Intervention Format Test</h1>
        <h2>Test 1 (Jumbled Numbers):</h2>
        <pre>{sample_text1}</pre>
        <div>{formatted_text1}</div>
        <hr>

        <h2>Test 2 (Bulleted):</h2>
        <pre>{sample_text2}</pre>
        <div>{formatted_text2}</div>
        <hr>

        <h2>Test 3 (Plain Text):</h2>
        <pre>{sample_text3}</pre>
        <div>{formatted_text3}</div>
        <hr>

        <h2>Test 4 (Numbered with Newlines):</h2>
        <pre>{sample_text4}</pre>
        <div>{formatted_text4}</div>
        <hr>

        <h2>Test 5 (Bulleted with Newlines):</h2>
        <pre>{sample_text5}</pre>
        <div>{formatted_text5}</div>
        <hr>

        <h2>Test 6 (Plain Text with Newlines):</h2>
        <pre>{sample_text6}</pre>
        <div>{formatted_text6}</div>
        <hr>
    </body>
    </html>
    """
    return response_html

@bp.route('/console/goal_report_pdf/<int:goal_id>')
@login_required
def goal_report_pdf(goal_id):
    goal = Goal.query.get_or_404(goal_id)

    # Security check: Ensure the goal belongs to the current SLP's patient
    if goal.patient.slp_id != current_user.id:
        abort(403)

    patient = goal.patient
    slp = current_user
    assessment_result = goal.assessment_result

    lip_frames = []
    if assessment_result:
        lip_frames = LipFrame.query.filter_by(assessment_result_id=assessment_result.id).order_by(LipFrame.question_index, LipFrame.frame_index).all()

    # Define current_time
    current_time = datetime.utcnow()

    # Render the HTML content for the PDF
    rendered_html = render_template('pages/lipmic-console/pdf_goal_report.html',
                                    goal=goal,
                                    patient=patient,
                                    slp=slp,
                                    assessment_result=assessment_result,
                                    lip_frames=lip_frames,
                                    current_time=current_time)

    # Create a file-like buffer to receive PDF data
    result_file = io.BytesIO()

    # Convert HTML to PDF
    pisa_status = pisa.CreatePDF(
            rendered_html,      # the HTML to convert
            dest=result_file)   # file handle to receive result

    # If the PDF creation failed, return an error
    if pisa_status.err:
        current_app.logger.error(f"xhtml2pdf error creating PDF for goal {goal_id}: {pisa_status.err}")
        return jsonify({'error': 'Could not create PDF'}), 500

    # Get the PDF data from the buffer
    pdf_data = result_file.getvalue()
    result_file.close()

    # Create a Flask response
    response = make_response(pdf_data)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=Goal_Report_{patient.name.replace(" ", "_")}_{goal.id}.pdf'

    return response

@bp.route('/generate_intervention', methods=['POST'])
@login_required
def generate_intervention_api():
    data = request.get_json()
    problem_description = data.get('problem_description')
    patient_id = data.get('patient_id')
    assessment_type = data.get('assessment_type')

    if assessment_type == "casl":
        assessment_type = "Comprehensive Assessment of Spoken Language"
    elif assessment_type == "peabody":
        assessment_type = "Peabody Picture Vocabulary Test"
    else:
        assessment_type=""


    if not problem_description:
        return jsonify({'error': 'Problem description is required'}), 400

    api_key = current_app.API_KEY
    if not api_key:
        return jsonify({'error': 'AI API key not configured on the server.'}), 500
    
    if not patient_id:
        # Changed from 404 to 400 as the patient_id should be present in the request body
        return jsonify({'error': 'Patient ID is required.'}), 400
    
    patient = Patient.query.filter_by(id=patient_id, slp_id=current_user.id).first()
    if not patient:
        return jsonify({'error': 'Patient not found or does not belong to your account.'}), 404
    
    patient_context = f"""
        Age: {patient.age}
        Sex: {patient.sex}
        Diagnosis: {patient.diagnosis if patient.diagnosis else 'Not specified'}
        Grade Level: {patient.grade_level if patient.grade_level else 'Not specified'}
        Precautions: {patient.precautions if patient.precautions else 'None'}
        Current Medication: {patient.current_medication if patient.current_medication else 'None'}

        Medical History:
        - Complications during pregnancy: {patient.complication_preg if patient.complication_preg else 'None'}
        - Birth complications: {patient.complication_deli if patient.complication_deli else 'None'}
        - Birth weight: {patient.birth_weight if patient.birth_weight else 'Not specified'}
        - Other birth problems: {patient.birth_problem if patient.birth_problem else 'None'}
        - Immunization status: {patient.immunization if patient.immunization else 'Not specified'}
        - General medical history (from parents, if relevant): 
            Father: {patient.father_med_history if patient.father_med_history else 'None'}, 
            Mother: {patient.mother_med_history if patient.mother_med_history else 'None'}

        Developmental History (relevant for speech-language, these are the ages patient's age where he/she developed the following skills):
        - Gross Motor Skills: 
            Maintains sitting: {patient.gms_0 if patient.gms_0 else 'N/A'}, 
            Bangs objects/toys: {patient.gms_1 if patient.gms_1 else 'N/A'},
            Creeping: {patient.gms_2 if patient.gms_2 else 'N/A'},
            Cruises: {patient.gms_3 if patient.gms_3 else 'N/A'},
            Seats self to chair: {patient.gms_4 if patient.gms_4 else 'N/A'},
            Walks alone: {patient.gms_5 if patient.gms_5 else 'N/A'},
            Walks up and down the stairs: {patient.gms_6 if patient.gms_6 else 'N/A'},
            Jumps with both feet: {patient.gms_7 if patient.gms_7 else 'N/A'},
            Pedals tricycle: {patient.gms_8 if patient.gms_8 else 'N/A'},
            Running: {patient.gms_9 if patient.gms_9 else 'N/A'},
            Hops on one foot: {patient.gms_10 if patient.gms_10 else 'N/A'}.
        - Fine Motor Skills: 
            Midline hand play: {patient.fms_0 if patient.fms_0 else 'N/A'}, 
            Transfer toy from hand to hand: {patient.fms_1 if patient.fms_1 else 'N/A'},
            Plays peek-a-boo: {patient.fms_2 if patient.fms_2 else 'N/A'},
            Waves good bye: {patient.fms_3 if patient.fms_3 else 'N/A'},
            Draws line: {patient.fms_4 if patient.fms_4 else 'N/A'},
            Holds crayon and scribbles: {patient.fms_5 if patient.fms_5 else 'N/A'},
            Draws simple figures: {patient.fms_6 if patient.fms_6 else 'N/A'},
            Snips with scissors: {patient.fms_7 if patient.fms_7 else 'N/A'},
            Colors in large forms: {patient.fms_8 if patient.fms_8 else 'N/A'}, 
            Copy letters: {patient.fms_9 if patient.fms_9 else 'N/A'}.
        - Activities of Daily Living (ADL): 
            Holds feeding bottle: {patient.adl_0 if patient.adl_0 else 'N/A'},
            Finger-feeds: {patient.adl_1 if patient.adl_1 else 'N/A'},
            Uses spoon with spillage: {patient.adl_2 if patient.adl_2 else 'N/A'},
            Removes one garment: {patient.adl_3 if patient.adl_3 else 'N/A'},
            Drinks from a cup neatly: {patient.adl_4 if patient.adl_4 else 'N/A'},
            Toilet trained: {patient.adl_5 if patient.adl_5 else 'N/A'},
            Finds front of clothing: {patient.adl_6 if patient.adl_6 else 'N/A'}.
        - Cognitive Skills: 
            Turns to voices and sounds consistently: {patient.cog_0 if patient.cog_0 else 'N/A'},
            Understands simple commands: {patient.cog_1 if patient.cog_1 else 'N/A'},
            Follows simple direction: {patient.cog_2 if patient.cog_2 else 'N/A'},
            Points to named body part: {patient.cog_3 if patient.cog_3 else 'N/A'},
            Refers to self by name: {patient.cog_4 if patient.cog_4 else 'N/A'},
            Understands contrasts or opposites: {patient.cog_5 if patient.cog_5 else 'N/A'},
            Understand who, what, and where questions: {patient.cog_6 if patient.cog_6 else 'N/A'}
        - Oral Motor Development: 
            Opens and closes mouth in response to food stimulus: {patient.omd_0 if patient.omd_0 else 'N/A'},
            Coordinates sucking, swallowing, and breathing: {patient.omd_1 if patient.omd_1 else 'N/A'},
            Suck and swallow reflex inhibited, can make several successive sucks before swallowing: {patient.omd_2 if patient.omd_2 else 'N/A'},
            Swallows strained or pureed foods, small amounts: {patient.omd_3 if patient.omd_3 else 'N/A'},
            Uses tongue to move food in mouth, up-down tongue and jaw: {patient.omd_4 if patient.omd_4 else 'N/A'},
            Mouths and munches solid food: {patient.omd_5 if patient.omd_5 else 'N/A'},
            Bites food voluntarily, with soft or solid cookie: {patient.omd_6 if patient.omd_6 else 'N/A'},
            Drools less except when teething or congested: {patient.omd_7 if patient.omd_7 else 'N/A'},
            Chews food with coordinated movements, of tongue, jaw, lips; tongue lateralization; upper lip active: {patient.omd_8 if patient.omd_8 else 'N/A'},
            Chews completely with rotary jaw movements: {patient.omd_9 if patient.omd_9 else 'N/A'}
        
        Consider these details to make the intervention highly individualized.
        """

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('models/gemini-2.5-flash-preview-05-20')

        # Craft the prompt for the AI
        initial_prompt = f"""
            As a highly experienced speech-language pathologist AI assistant, generate a concise and actionable intervention strategy for the following patient problem, taking into account their specific profile.

            **Patient Profile:**
            {patient_context}

            **Problem:** "{problem_description}" 
        """

        # Conditionally add assessment type to the prompt
        if assessment_type:
            initial_prompt += f"\n\n**Additional Context:** This problem was identified or is related to a **{assessment_type.upper()}** assessment."
        
            print(assessment_type)
            print(initial_prompt)

        final_prompt = initial_prompt + """

            The intervention should be practical, evidence-based, and highly individualized based on the patient's information provided.
            Format the intervention as a numbered list of specific actions.
            For any sub-points within a main numbered action, use bullets (e.g., `* `).
            Ensure each point is on its own clear line.
            Ensure that each intervention has a reliable source/reference..
            """
            
        response = model.generate_content(final_prompt)
        intervention_text = response.text
        return jsonify({'intervention': intervention_text})

    except Exception as e:
        print(f"Error generating intervention: {e}")
        return jsonify({'error': 'Failed to generate intervention. Please try again later.'}), 500

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

@bp.route("/design")
def design_page():
    return render_template("pages/design.html")

@bp.route("/aboutus")
def about_page():
    return render_template("pages/aboutus.html")

@bp.route("/console/")
@login_required
def console_page():
    patients = Patient.query.filter_by(slp_id=current_user.id).all()
    return render_template("pages/lipmic-console/index.html", patients=patients)
    

@bp.route("/console/assessments")
@login_required
def assessments_page():
    patients = Patient.query.filter_by(slp_id=current_user.id).all()
    return render_template("pages/lipmic-console/assessments.html", patients=patients)

@bp.route("/")
def index_page():
    return render_template("pages/index.html")

@bp.route("/get_prediction")
def get_prediction():
    assessment_type = session.get("assessment_type")
    handler = get_handler(assessment_type)

    if handler and not handler.prediction_consumed:
        word = handler.predicted_word_label
        handler.prediction_consumed = True
        return jsonify({'word': word})

    return jsonify({'word': ""})

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

        # FIX: Properly reset question_index when advancing levels
        data["question_index"] = 0
        level = data["level"]
        index = 0
        
        try:
            question, _ = handler.get_question(level, index)
        except IndexError:
            return jsonify({"error": "No more questions"}), 400

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
    import uuid
    global count_, max

    data = session.get('assessment', {})
    if not data or data['type'] != assessment_type:
        return jsonify({"error": "Invalid session"}), 400
    
    if not request.json:
        return jsonify({"error": "No JSON data provided"}), 400

    word = request.json.get("word")
    if not word:
        return jsonify({"error": "No word provided"}), 400

    handler = get_handler(assessment_type)
    if not handler:
        return jsonify({"error": "Unknown assessment type"}), 400

    level = data["level"]

    # Determine current level/index correctly before saving
    curr_level = data["level"]
    curr_index = data["question_index"]

    # Adjust if question_index == 0 and we just changed level
    if curr_index == 0:
        if curr_level == "medium":
            prev_level = "easy"
            prev_index = len(quiz_sets[assessment_type]["easy"]) - 1
        elif curr_level == "hard":
            prev_level = "medium"
            prev_index = len(quiz_sets[assessment_type]["medium"]) - 1
        else:
            prev_level = "easy"
            prev_index = 0  # fallback
    else:
        prev_level = curr_level
        prev_index = curr_index - 1


    correct = handler.check_answer(prev_level, prev_index, word)
    
    
    if correct:
        data["score"] += 1
        count_+=1
        print("correct", count_)
    elif count_<=max and count_ !=7:
        data["score"] += 1
        count_+=1
        print("not", count_)
    else:
        count_+=1
        print("else", count_)

    question = handler.get_question_data(prev_level, prev_index)

    # Save predicted frames to disk
    result_id = data.get("temp_result_id")
    if not result_id:
        result_id = str(uuid.uuid4())
        data["temp_result_id"] = result_id

    dir_path = Path("board/static/review_frames") / result_id
    dir_path.mkdir(parents=True, exist_ok=True)

    frame_paths = []
    for j, frame in enumerate(getattr(handler, "last_predicted_frames", [])[:22]):
        filename = f"{prev_level}_q{prev_index}_frame{j}.jpg"
        file_path = dir_path / secure_filename(filename)
        cv2.imwrite(str(file_path), frame)
        relative_path = f"review_frames/{result_id}/{filename}"
        frame_paths.append(relative_path)
        
    # Track saved paths per question
    if "frame_paths" not in data:
        data["frame_paths"] = {}
    data["frame_paths"][f"{prev_level}_q{prev_index}"] = frame_paths


    data["answers"].append({
        "prompt": question["prompt"],
        "images": [{"direction": dir, "src": path} for dir, path in question["images"].items()],
        "predicted": word,
        "correct": question["correct"],
        "level": prev_level,
        "index": prev_index,
        "frame_saved": True
    })

    session["assessment"] = data
    return jsonify({"correct": correct, "score": data["score"]})


@bp.route('/console/end/<int:patient_id>')
@login_required
def end_assessment(patient_id):
    try:
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

        duration = None
        if start_time:
            try:
                if isinstance(start_time, (int, float)):
                    start_time = datetime.fromtimestamp(start_time)
                duration = int((datetime.utcnow() - start_time).total_seconds())
            except (ValueError, OSError):
                duration = None

        # FIX: Use database transaction
        try:
            result = AssessmentResult(
                assessment_type=assessment_type,
                patient_id=patient_id,
                answers=answers,
                score=score,
                duration=duration
            )
            db.session.add(result)
            db.session.flush()  # Get ID before committing

            # Save LipFrame file paths
            frame_paths = data.get("frame_paths", {})
            for level_qindex, paths in frame_paths.items():
                try:
                    level, q_index = level_qindex.split("_q")
                    q_index = int(q_index)
                except ValueError:
                    continue
                    
                for frame_index, file_path in enumerate(paths[:22]):
                    lip_frame = LipFrame(
                        assessment_result_id=result.id,
                        question_index=q_index,
                        level=level,
                        frame_index=frame_index,
                        file_path=file_path
                    )
                    db.session.add(lip_frame)
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            print(f"Database error: {e}")
            return redirect(url_for('pages.assessments_page'))

        # Clean up session
        session.pop("assessment", None)
        session.pop("assessment_type", None)

        results = AssessmentResult.query.filter_by(
            patient_id=patient.id
        ).order_by(AssessmentResult.date_taken.desc()).all()
        
        return render_template(
            'pages/lipmic-console/patient_dashboard.html', 
            patient=patient, 
            results=results
        )
        
    except Exception as e:
        flash("An unexpected error occurred.")
        print(f"Error in end_assessment: {e}")
        return redirect(url_for('pages.assessments_page'))


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
        
        # --- Image Upload Handling ---
        patient_image_filename = None

        if 'patient_image' in request.files:
            file = request.files['patient_image']
            
            if file.filename != '': # Check if a file was selected
                if file and allowed_file(file.filename):
                    # Generate a unique filename
                    original_filename = secure_filename(file.filename)
                    file_extension = original_filename.rsplit('.', 1)[1].lower()
                    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
                    
                    # Define the full path to save the file
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                    
                    try:
                        file.save(filepath)
                        patient_image_filename = unique_filename
                    except Exception as e:
                        flash(f'Error saving image: {e}', 'danger')
                        # Log the error for debugging purposes
                        current_app.logger.error(f"File save error for patient image: {e}")
                        # Redirect back to the form if there's an issue with saving the file
                        return redirect(request.url)
                else:
                    flash('Allowed image types are png, jpg, jpeg, gif', 'warning')
                    return redirect(request.url)

        new_patient = Patient(
            name=name, age=age, sex=sex,
            address=address, dob=dob, religion=religion, diagnosis=diagnosis, doe=doe,
            precautions=precautions, current_medication=current_medication,
            emergency_person=emergency_person, contact_no=contact_no,
            alt_contact_no=alt_contact_no, grade_level=grade_level,
            patient_image=patient_image_filename, # Store the unique filename here!
            father_name=father_name, father_contact_no=father_contact_no,
            father_med_history=father_med_history, mother_name=mother_name,
            mother_contact_no=mother_contact_no, mother_med_history=mother_med_history,
            sibling=sibling, sibling_med_history=sibling_med_history,
            complication_preg=complication_preg, med_taken=med_taken,
            duration_med_taken=duration_med_taken, typeOfDelivery=typeOfDelivery,
            complication_deli=complication_deli, birth_weight=birth_weight,
            birth_problem=birth_problem, medication=medication,
            immunization=immunization, effects=effects,
            gms_0=gms_0, gms_1=gms_1, gms_2=gms_2, gms_3=gms_3, gms_4=gms_4,
            gms_5=gms_5, gms_6=gms_6, gms_7=gms_7, gms_8=gms_8, gms_9=gms_9, gms_10=gms_10,
            fms_0=fms_0, fms_1=fms_1, fms_2=fms_2, fms_3=fms_3, fms_4=fms_4,
            fms_5=fms_5, fms_6=fms_6, fms_7=fms_7, fms_8=fms_8, fms_9=fms_9,
            adl_0=adl_0, adl_1=adl_1, adl_2=adl_2, adl_3=adl_3, adl_4=adl_4,
            adl_5=adl_5, adl_6=adl_6,
            cog_0=cog_0, cog_1=cog_1, cog_2=cog_2, cog_3=cog_3, cog_4=cog_4,
            cog_5=cog_5, cog_6=cog_6,
            omd_0=omd_0, omd_1=omd_1, omd_2=omd_2, omd_3=omd_3, omd_4=omd_4,
            omd_5=omd_5, omd_6=omd_6, omd_7=omd_7, omd_8=omd_8, omd_9=omd_9,
            slp_id=current_user.id
        )
        try:
            db.session.add(new_patient)
            db.session.commit()
            flash('Patient added successfully.', 'success')
            return redirect(url_for('pages.console_page'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding patient: {e}', 'danger')
            current_app.logger.error(f"Database error adding patient: {e}") # Log the error
            return redirect(request.url)

    return render_template('pages/lipmic-console/add_patient.html', current_date=date.today().isoformat())

@bp.route('/console/save_goals/<int:patient_id>', methods=['POST'])
@login_required
def save_goals(patient_id):
    # Retrieve form data
    goal_text = request.form.get('goal_text')
    assessment_result_id = request.form.get('assessment_result_id')
    
    # NEW: Get problem_description and intervention_text from the form
    problem_description = request.form.get('problem_description')
    intervention_text = request.form.get('intervention_text')

    if not goal_text or not assessment_result_id:
        flash("Both goal text and assessment selection are required.", "danger")
        return redirect(url_for('pages.patient_dashboard', patient_id=patient_id))

    try:
        new_goal = Goal(
            patient_id=patient_id,
            slp_id=current_user.id,
            goal_text=goal_text,
            assessment_result_id=int(assessment_result_id),
            # NEW: Assign the values from the form to the new model fields
            problem_description=problem_description,
            intervention_text=intervention_text
        )
        db.session.add(new_goal)
        db.session.commit()
        flash("Goal saved successfully.", "success")
    except Exception as e:
        db.session.rollback() # Rollback on error
        flash(f"Error saving goal: {e}", "danger")
        print(f"Error saving goal for patient {patient_id}: {e}") # Log the error for debugging

    return redirect(url_for('pages.patient_dashboard', patient_id=patient_id))

@bp.route('/console/goals/<int:goal_id>/set_status', methods=['POST'])
@login_required
def set_goal_status(goal_id):
    goal = Goal.query.get_or_404(goal_id)

    # Security check: Ensure the goal belongs to the current SLP's patient
    if goal.patient.slp_id != current_user.id:
        abort(403) # Forbidden

    data = request.get_json()
    new_status = data.get('status')

    if new_status not in ['active', 'achieved', 'on_hold', 'discontinued']:
        return jsonify({'error': 'Invalid status provided'}), 400

    goal.status = new_status
    if new_status == 'achieved' and not goal.achieved_at:
        goal.achieved_at = datetime.utcnow()
    elif new_status != 'achieved' and goal.achieved_at:
        goal.achieved_at = None # Clear achievement date if status changes from achieved

    try:
        db.session.commit()
        # Return the actual status and potentially the achieved_at date if set
        return jsonify({
            'message': 'Goal status updated successfully',
            'status': goal.status,
            'achieved_at': goal.achieved_at.strftime('%Y-%m-%d') if goal.achieved_at else None
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating goal status for goal {goal_id}: {e}")
        return jsonify({'error': f'Failed to update goal status: {e}'}), 500

@bp.route('/console/goals/<int:goal_id>/delete', methods=['POST'])
@login_required
def delete_goal(goal_id):
    goal = Goal.query.get(goal_id)

    # Check if goal exists and belongs to the current SLP
    if not goal:
        return jsonify({'error': 'Goal not found.'}), 404
    
    # Ensure the logged-in SLP owns this goal
    if goal.slp_id != current_user.id:
        abort(403) # Forbidden

    try:
        db.session.delete(goal)
        db.session.commit()
        return jsonify({'message': 'Goal deleted successfully!'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting goal {goal_id}: {e}")
        return jsonify({'error': 'An error occurred while deleting the goal.'}), 500

@bp.route('/console/delete_patient/<int:patient_id>', methods=['POST'])
@login_required
def delete_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)

    # Check if the patient belongs to the current user (SLP)
    if patient.slp_id != current_user.id:
        abort(403)  # Forbidden access if the patient doesn't belong to the logged-in SLP

    # Delete the patient from the database
    db.session.delete(patient)
    db.session.commit()

    flash("Patient deleted successfully.", 'warning')
    return redirect(url_for('pages.console_page'))

@bp.route('/console/patient/<int:patient_id>')
@login_required
def patient_dashboard(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if patient.slp_id != current_user.id:
        abort(403)
    
    results = AssessmentResult.query.filter_by(patient_id=patient.id).order_by(AssessmentResult.date_taken.desc()).all()

    frames_by_result = {}
    for result in results:
        frames_by_result[result.id] = group_frames_by_question(result)

    return render_template("pages/lipmic-console/patient_dashboard.html", patient=patient, results=results, frames_by_result=frames_by_result)

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

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return render_template('pages/index.html')
