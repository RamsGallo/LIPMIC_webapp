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
    age = db.Column(db.String(100), nullable=False)
    sex = db.Column(db.String(25), nullable=False)
    address = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.String(100), nullable=False)
    religion = db.Column(db.String(100), nullable=False)
    diagnosis = db.Column(db.String(100), nullable=False)
    doe = db.Column(db.String(100), nullable=False)
    precautions = db.Column(db.String(100), nullable=False)
    current_medication = db.Column(db.String(100), nullable=False)
    emergency_person = db.Column(db.String(100), nullable=False)
    contact_no = db.Column(db.String(100), nullable=False)
    alt_contact_no = db.Column(db.String(100), nullable=False)
    grade_level = db.Column(db.String(100), nullable=False)

    # Family information
    father_name = db.Column(db.String(100), nullable=False)
    father_contact_no = db.Column(db.String(100), nullable=False)
    father_med_history = db.Column(db.String(100), nullable=False)
    mother_name = db.Column(db.String(100), nullable=False)
    mother_contact_no = db.Column(db.String(100), nullable=False)
    mother_med_history = db.Column(db.String(100), nullable=False)
    sibling = db.Column(db.String(100), nullable=False)
    sibling_med_history = db.Column(db.String(100), nullable=False)


    # Medical information
    complication_preg = db.Column(db.String(100), nullable=False)
    med_taken = db.Column(db.String(100), nullable=False)
    duration_med_taken = db.Column(db.String(100), nullable=False)
    typeOfDelivery = db.Column(db.String(100), nullable=False)
    complication_deli = db.Column(db.String(100), nullable=False)
    birth_weight = db.Column(db.String(100), nullable=False)
    birth_problem = db.Column(db.String(100), nullable=False)
    medication = db.Column(db.String(100), nullable=False)
    immunization = db.Column(db.String(100), nullable=False)
    effects = db.Column(db.String(100), nullable=False)

    # Developmental history
    # GMS
    gms_0 = db.Column(db.String(100), nullable=False)
    gms_1 = db.Column(db.String(100), nullable=False)
    gms_2 = db.Column(db.String(100), nullable=False)
    gms_3 = db.Column(db.String(100), nullable=False)
    gms_4 = db.Column(db.String(100), nullable=False)
    gms_5 = db.Column(db.String(100), nullable=False)
    gms_6 = db.Column(db.String(100), nullable=False)
    gms_7 = db.Column(db.String(100), nullable=False)
    gms_8 = db.Column(db.String(100), nullable=False)
    gms_9 = db.Column(db.String(100), nullable=False)
    gms_10 = db.Column(db.String(100), nullable=False)

    # FMS
    fms_0 = db.Column(db.String(100), nullable=False)
    fms_1 = db.Column(db.String(100), nullable=False)
    fms_2 = db.Column(db.String(100), nullable=False)
    fms_3 = db.Column(db.String(100), nullable=False)
    fms_4 = db.Column(db.String(100), nullable=False)
    fms_5 = db.Column(db.String(100), nullable=False)
    fms_6 = db.Column(db.String(100), nullable=False)
    fms_7 = db.Column(db.String(100), nullable=False)
    fms_8 = db.Column(db.String(100), nullable=False)
    fms_9 = db.Column(db.String(100), nullable=False)

    # ADL
    adl_0 = db.Column(db.String(100), nullable=False)
    adl_1 = db.Column(db.String(100), nullable=False)
    adl_2 = db.Column(db.String(100), nullable=False)
    adl_3 = db.Column(db.String(100), nullable=False)
    adl_4 = db.Column(db.String(100), nullable=False)
    adl_5 = db.Column(db.String(100), nullable=False)
    adl_6 = db.Column(db.String(100), nullable=False)

    # COGNITIVE
    cog_0 = db.Column(db.String(100), nullable=False)
    cog_1 = db.Column(db.String(100), nullable=False)
    cog_2 = db.Column(db.String(100), nullable=False)
    cog_3 = db.Column(db.String(100), nullable=False)
    cog_4 = db.Column(db.String(100), nullable=False)
    cog_5 = db.Column(db.String(100), nullable=False)
    cog_6 = db.Column(db.String(100), nullable=False)

    # ORAL MOTOR
    omd_0 = db.Column(db.String(100), nullable=False)
    omd_1 = db.Column(db.String(100), nullable=False)
    omd_2 = db.Column(db.String(100), nullable=False)
    omd_3 = db.Column(db.String(100), nullable=False)
    omd_4 = db.Column(db.String(100), nullable=False)
    omd_5 = db.Column(db.String(100), nullable=False)
    omd_6 = db.Column(db.String(100), nullable=False)
    omd_7 = db.Column(db.String(100), nullable=False)
    omd_8 = db.Column(db.String(100), nullable=False)
    omd_9 = db.Column(db.String(100), nullable=False)

    slp_id = db.Column(db.Integer, db.ForeignKey('slp.id'), nullable=False)
    sessions = db.relationship('AssessmentResult', backref='patient', lazy=True)

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
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    date_taken = db.Column(db.DateTime, default=datetime.utcnow)
    answers = db.Column(db.JSON, nullable=False)  # { "prompt": ..., "predicted": ..., "correct": ... }
    score = db.Column(db.Integer, nullable=False)
    duration = db.Column(db.Integer, nullable=True)

    def __init__(self, assessment_type, patient_id, answers, score, duration=None):
        self.assessment_type = assessment_type
        self.patient_id = patient_id
        self.answers = answers
        self.score = score
        self.duration = duration
