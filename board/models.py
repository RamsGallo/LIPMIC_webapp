from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Patient(db.Model):
    __tablename__ = 'patient'
    id = db.Column(db.Integer, primary_key=True)

    # Client information
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.String(100), nullable=True)
    sex = db.Column(db.String(25), nullable=True)
    address = db.Column(db.String(100), nullable=True)
    dob = db.Column(db.String(100), nullable=False)
    religion = db.Column(db.String(100), nullable=True)
    diagnosis = db.Column(db.String(100), nullable=True)
    doe = db.Column(db.String(100), nullable=True)
    precautions = db.Column(db.String(100), nullable=True)
    current_medication = db.Column(db.String(100), nullable=True)
    emergency_person = db.Column(db.String(100), nullable=True)
    contact_no = db.Column(db.String(100), nullable=True)
    alt_contact_no = db.Column(db.String(100), nullable=True)
    grade_level = db.Column(db.String(100), nullable=True)
    patient_image = db.Column(db.String(255), nullable=True)

    # Family information
    father_name = db.Column(db.String(100), nullable=True)
    father_contact_no = db.Column(db.String(100), nullable=True)
    father_med_history = db.Column(db.String(100), nullable=True)
    mother_name = db.Column(db.String(100), nullable=True)
    mother_contact_no = db.Column(db.String(100), nullable=True)
    mother_med_history = db.Column(db.String(100), nullable=True)
    sibling = db.Column(db.String(100), nullable=True)
    sibling_med_history = db.Column(db.String(100), nullable=True)


    # Medical information
    complication_preg = db.Column(db.String(100), nullable=True)
    med_taken = db.Column(db.String(100), nullable=True)
    duration_med_taken = db.Column(db.String(100), nullable=True)
    typeOfDelivery = db.Column(db.String(100), nullable=True)
    complication_deli = db.Column(db.String(100), nullable=True)
    birth_weight = db.Column(db.String(100), nullable=True)
    birth_problem = db.Column(db.String(100), nullable=True)
    medication = db.Column(db.String(100), nullable=True)
    immunization = db.Column(db.String(100), nullable=True)
    effects = db.Column(db.String(100), nullable=True)

    # Developmental history
    # GMS
    gms_0 = db.Column(db.String(100), nullable=True)
    gms_1 = db.Column(db.String(100), nullable=True)
    gms_2 = db.Column(db.String(100), nullable=True)
    gms_3 = db.Column(db.String(100), nullable=True)
    gms_4 = db.Column(db.String(100), nullable=True)
    gms_5 = db.Column(db.String(100), nullable=True)
    gms_6 = db.Column(db.String(100), nullable=True)
    gms_7 = db.Column(db.String(100), nullable=True)
    gms_8 = db.Column(db.String(100), nullable=True)
    gms_9 = db.Column(db.String(100), nullable=True)
    gms_10 = db.Column(db.String(100), nullable=True)

    # FMS
    fms_0 = db.Column(db.String(100), nullable=True)
    fms_1 = db.Column(db.String(100), nullable=True)
    fms_2 = db.Column(db.String(100), nullable=True)
    fms_3 = db.Column(db.String(100), nullable=True)
    fms_4 = db.Column(db.String(100), nullable=True)
    fms_5 = db.Column(db.String(100), nullable=True)
    fms_6 = db.Column(db.String(100), nullable=True)
    fms_7 = db.Column(db.String(100), nullable=True)
    fms_8 = db.Column(db.String(100), nullable=True)
    fms_9 = db.Column(db.String(100), nullable=True)

    # ADL
    adl_0 = db.Column(db.String(100), nullable=True)
    adl_1 = db.Column(db.String(100), nullable=True)
    adl_2 = db.Column(db.String(100), nullable=True)
    adl_3 = db.Column(db.String(100), nullable=True)
    adl_4 = db.Column(db.String(100), nullable=True)
    adl_5 = db.Column(db.String(100), nullable=True)
    adl_6 = db.Column(db.String(100), nullable=True)

    # COGNITIVE
    cog_0 = db.Column(db.String(100), nullable=True)
    cog_1 = db.Column(db.String(100), nullable=True)
    cog_2 = db.Column(db.String(100), nullable=True)
    cog_3 = db.Column(db.String(100), nullable=True)
    cog_4 = db.Column(db.String(100), nullable=True)
    cog_5 = db.Column(db.String(100), nullable=True)
    cog_6 = db.Column(db.String(100), nullable=True)

    # ORAL MOTOR
    omd_0 = db.Column(db.String(100), nullable=True)
    omd_1 = db.Column(db.String(100), nullable=True)
    omd_2 = db.Column(db.String(100), nullable=True)
    omd_3 = db.Column(db.String(100), nullable=True)
    omd_4 = db.Column(db.String(100), nullable=True)
    omd_5 = db.Column(db.String(100), nullable=True)
    omd_6 = db.Column(db.String(100), nullable=True)
    omd_7 = db.Column(db.String(100), nullable=True)
    omd_8 = db.Column(db.String(100), nullable=True)
    omd_9 = db.Column(db.String(100), nullable=True)

    slp_id = db.Column(db.Integer, db.ForeignKey('slp.id'), nullable=False)
    goals = db.relationship('Goal', back_populates='patient', lazy=True, cascade="all, delete-orphan")
    sessions = db.relationship('AssessmentResult', back_populates='patient', lazy=True, cascade="all, delete-orphan")

class SLP(UserMixin, db.Model):
    __tablename__ = 'slp'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    patients = db.relationship('Patient', backref='slp', lazy=True)

    @property
    def password(self):
        raise AttributeError("Password is write-only")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class AssessmentResult(db.Model):
    __tablename__ = 'assessment_results'
    id = db.Column(db.Integer, primary_key=True)
    assessment_type = db.Column(db.String(50), nullable=False)  # e.g., 'peabody', 'naming'
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id', ondelete='CASCADE'), nullable=False)
    date_taken = db.Column(db.DateTime, default=datetime.utcnow)
    answers = db.Column(db.JSON, nullable=False)  # { "prompt": ..., "predicted": ..., "correct": ... }
    score = db.Column(db.Integer, nullable=False)
    duration = db.Column(db.Integer, nullable=True)

    patient = db.relationship('Patient', back_populates='sessions')
    goals = db.relationship('Goal', back_populates='assessment_result', lazy=True, cascade="all, delete-orphan")

    def __init__(self, assessment_type, patient_id, answers, score, duration=None):
        self.assessment_type = assessment_type
        self.patient_id = patient_id
        self.answers = answers
        self.score = score
        self.duration = duration

class LipFrame(db.Model):
    __tablename__ = 'lip_frames'
    id = db.Column(db.Integer, primary_key=True)
    assessment_result_id = db.Column(db.Integer, db.ForeignKey('assessment_results.id'), nullable=False)
    question_index = db.Column(db.Integer, nullable=False)
    level = db.Column(db.String(50))
    frame_index = db.Column(db.Integer, nullable=False)
    file_path = db.Column(db.String(256), nullable=False)

    assessment_result = db.relationship("AssessmentResult", backref=db.backref("lip_frames", lazy=True, cascade="all, delete-orphan"))

class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id', ondelete='CASCADE'), nullable=False)
    slp_id = db.Column(db.Integer, db.ForeignKey('slp.id'), nullable=False)
    goal_text = db.Column(db.Text, nullable=False)

    problem_description = db.Column(db.Text, nullable=True)
    intervention_text = db.Column(db.Text, nullable=True)

    assessment_result_id = db.Column(db.Integer, db.ForeignKey('assessment_results.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Status can be 'active', 'achieved', 'on_hold', 'discontinued'
    status = db.Column(db.String(50), default='active', nullable=False)
    achieved_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    patient = db.relationship('Patient', back_populates='goals')
    slp = db.relationship('SLP', backref='goals')
    assessment_result = db.relationship('AssessmentResult', back_populates='goals')
