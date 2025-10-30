"""
Patient-related database models
"""

from datetime import datetime
from app import db

class WebPatient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(20), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20), nullable=False)
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))
    address = db.Column(db.Text)
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(10))
    country = db.Column(db.String(50))
    emergency_contact = db.Column(db.String(100))
    emergency_phone = db.Column(db.String(20))
    emergency_relation = db.Column(db.String(50))
    blood_group = db.Column(db.String(5))
    allergies = db.Column(db.Text)
    medical_history = db.Column(db.Text)
    insurance_provider = db.Column(db.String(100))
    insurance_number = db.Column(db.String(50))
    insurance_expiry = db.Column(db.Date)
    id_proof_type = db.Column(db.String(50))
    id_proof_number = db.Column(db.String(50))
    marital_status = db.Column(db.String(20))
    occupation = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    appointments = db.relationship('WebAppointment', backref='patient', lazy='dynamic')
    medical_records = db.relationship('MedicalRecord', backref='patient', lazy='dynamic')
    prescriptions = db.relationship('Prescription', backref='patient', lazy='dynamic')
    lab_orders = db.relationship('LabOrder', backref='patient', lazy='dynamic')
    imaging_orders = db.relationship('ImagingOrder', backref='patient', lazy='dynamic')
    admissions = db.relationship('Admission', backref='patient', lazy='dynamic')
    bills = db.relationship('Bill', backref='patient', lazy='dynamic')
    insurance_claims = db.relationship('InsuranceClaim', backref='patient', lazy='dynamic')

    def __repr__(self):
        return f'<WebPatient {self.patient_id}>'
    
    @property
    def full_name(self):
        """Return full name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self):
        """Calculate age from date of birth"""
        if self.date_of_birth:
            today = datetime.now().date()
            return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return None
    
    def to_dict(self):
        """Convert patient object to dictionary for API responses"""
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'email': self.email,
            'phone': self.phone,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'age': self.age,
            'gender': self.gender,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'country': self.country,
            'emergency_contact': self.emergency_contact,
            'emergency_phone': self.emergency_phone,
            'emergency_relation': self.emergency_relation,
            'blood_group': self.blood_group,
            'allergies': self.allergies,
            'medical_history': self.medical_history,
            'insurance_provider': self.insurance_provider,
            'insurance_number': self.insurance_number,
            'insurance_expiry': self.insurance_expiry.isoformat() if self.insurance_expiry else None,
            'id_proof_type': self.id_proof_type,
            'id_proof_number': self.id_proof_number,
            'marital_status': self.marital_status,
            'occupation': self.occupation,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
