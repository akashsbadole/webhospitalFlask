"""
User-related database models
"""

from flask_login import UserMixin
from datetime import datetime
from app import db

class WebUser(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='staff')  # admin, doctor, nurse, receptionist, lab_tech, patient, superadmin
    department = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    employee_id = db.Column(db.String(20), unique=True)
    specialization = db.Column(db.String(100))  # For doctors
    license_number = db.Column(db.String(50))  # For medical staff
    shift_start = db.Column(db.Time)
    shift_end = db.Column(db.Time)
    salary = db.Column(db.Float)
    hire_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    appointments = db.relationship('WebAppointment', backref='doctor', lazy='dynamic')
    attendance_records = db.relationship('WebAttendance', backref='user', lazy='dynamic')
    medical_records = db.relationship('MedicalRecord', backref='doctor', lazy='dynamic')
    prescriptions = db.relationship('Prescription', backref='doctor', lazy='dynamic')
    lab_orders = db.relationship('LabOrder', backref='doctor', lazy='dynamic')
    imaging_orders = db.relationship('ImagingOrder', backref='doctor', lazy='dynamic')
    pharmacy_orders = db.relationship('PharmacyOrder', backref='pharmacist', lazy='dynamic')
    admissions = db.relationship('Admission', backref='doctor', lazy='dynamic')
    created_bills = db.relationship('Bill', backref='created_by_user', lazy='dynamic')
    received_payments = db.relationship('Payment', backref='received_by_user', lazy='dynamic')
    imaging_results = db.relationship('ImagingResult', backref='radiologist', lazy='dynamic')
    headed_departments = db.relationship('Department', backref='hod', lazy='dynamic')

    def __repr__(self):
        return f'<WebUser {self.username}>'
    
    def has_role(self, role):
        """Check if user has specific role"""
        return self.role == role
    
    def has_any_role(self, *roles):
        """Check if user has any of the specified roles"""
        return self.role in roles
