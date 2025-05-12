from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Patient(db.Model):
    __tablename__ = 'patient'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
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
