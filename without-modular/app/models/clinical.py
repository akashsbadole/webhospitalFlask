"""
Clinical database models - EHR, Lab, Imaging
"""

from datetime import datetime
from app import db

# EHR - Electronic Health Records
class MedicalRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('web_patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('web_user.id'), nullable=False)
    visit_date = db.Column(db.DateTime, nullable=False)
    chief_complaint = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    treatment_plan = db.Column(db.Text)
    notes = db.Column(db.Text)
    vital_signs = db.Column(db.Text)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<MedicalRecord {self.id}>'
    def to_dict(self):
        """Convert medical record to dictionary for API responses"""
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'doctor_id': self.doctor_id,
            'visit_date': self.visit_date.isoformat() if self.visit_date else None,
            'chief_complaint': self.chief_complaint,
            'diagnosis': self.diagnosis,
            'treatment_plan': self.treatment_plan,
            'notes': self.notes,
            'vital_signs': self.vital_signs,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Prescriptions
class Prescription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('web_patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('web_user.id'), nullable=False)
    medical_record_id = db.Column(db.Integer, db.ForeignKey('medical_record.id'))
    prescription_date = db.Column(db.DateTime, default=datetime.utcnow)
    medications = db.Column(db.Text)  # JSON string
    instructions = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')  # active, completed, cancelled
    dispense_status = db.Column(db.String(20), default='pending')  # pending, partial, dispensed
    dispense_date = db.Column(db.DateTime)
    def to_dict(self):
        """Convert prescription to dictionary for API responses"""
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'doctor_id': self.doctor_id,
            'medical_record_id': self.medical_record_id,
            'prescription_date': self.prescription_date.isoformat() if self.prescription_date else None,
            'medications': self.medications,
            'instructions': self.instructions,
            'status': self.status,
            'dispense_status': self.dispense_status,
            'dispense_date': self.dispense_date.isoformat() if self.dispense_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    medical_record = db.relationship('MedicalRecord', backref='prescriptions')

    def __repr__(self):
        return f'<Prescription {self.id}>'

# Laboratory Management
class LabTest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_name = db.Column(db.String(100), nullable=False)
    test_code = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(50))
    normal_range = db.Column(db.String(100))
    def to_dict(self):
        """Convert lab order to dictionary for API responses"""
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'doctor_id': self.doctor_id,
            'test_id': self.test_id,
            'test_name': self.lab_test.test_name if hasattr(self, 'lab_test') and self.lab_test else None,
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'sample_collected_date': self.sample_collected_date.isoformat() if self.sample_collected_date else None,
            'result_date': self.result_date.isoformat() if self.result_date else None,
            'status': self.status,
            'priority': self.priority,
            'notes': self.notes
        }
    price = db.Column(db.Float)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<LabTest {self.test_code}>'

class LabOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('web_patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('web_user.id'), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey('lab_test.id'), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    sample_collected_date = db.Column(db.DateTime)
    result_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='ordered')  # ordered, collected, processing, completed
    priority = db.Column(db.String(20), default='normal')  # urgent, normal, routine
    notes = db.Column(db.Text)

    def __repr__(self):
        return f'<LabOrder {self.id}>'

class LabResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lab_order_id = db.Column(db.Integer, db.ForeignKey('lab_order.id'), nullable=False)
    technician_id = db.Column(db.Integer, db.ForeignKey('web_user.id'))
    result_value = db.Column(db.String(100))
    result_unit = db.Column(db.String(20))
    reference_range = db.Column(db.String(100))
    status = db.Column(db.String(20))  # normal, abnormal, critical
    comments = db.Column(db.Text)
    verified_by = db.Column(db.Integer, db.ForeignKey('web_user.id'))
    verified_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    technician = db.relationship('WebUser', foreign_keys=[technician_id])
    verifier = db.relationship('WebUser', foreign_keys=[verified_by])

    def __repr__(self):
        return f'<LabResult {self.id}>'

# Radiology / Imaging
class ImagingTest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_name = db.Column(db.String(100), nullable=False)
    test_code = db.Column(db.String(20), nullable=False)
    def to_dict(self):
        """Convert imaging order to dictionary for API responses"""
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'doctor_id': self.doctor_id,
            'test_id': self.test_id,
            'procedure_type': self.imaging_test.test_name if hasattr(self, 'imaging_test') and self.imaging_test else None,
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'status': self.status,
            'notes': self.clinical_notes
        }
    category = db.Column(db.String(50))  # X-ray, MRI, CT, Ultrasound
    price = db.Column(db.Float)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<ImagingTest {self.test_code}>'

class ImagingOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('web_patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('web_user.id'), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey('imaging_test.id'), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    scheduled_date = db.Column(db.DateTime)
    completed_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='ordered')  # ordered, scheduled, completed
    priority = db.Column(db.String(20), default='normal')
    clinical_notes = db.Column(db.Text)

    def __repr__(self):
        return f'<ImagingOrder {self.id}>'

class ImagingResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    imaging_order_id = db.Column(db.Integer, db.ForeignKey('imaging_order.id'), nullable=False)
    radiologist_id = db.Column(db.Integer, db.ForeignKey('web_user.id'))
    findings = db.Column(db.Text)
    impression = db.Column(db.Text)
    recommendations = db.Column(db.Text)
    image_path = db.Column(db.String(500))
    report_path = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ImagingResult {self.id}>'
