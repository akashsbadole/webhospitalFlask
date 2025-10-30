"""
Admission and inpatient database models
"""

from datetime import datetime
from app import db

class Admission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('web_patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('web_user.id'), nullable=False)
    bed_id = db.Column(db.Integer, db.ForeignKey('bed.id'), nullable=False)
    admission_date = db.Column(db.DateTime, default=datetime.utcnow)
    discharge_date = db.Column(db.DateTime)
    admission_type = db.Column(db.String(50))  # emergency, planned, transfer
    reason = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    status = db.Column(db.String(20), default='admitted')  # admitted, discharged, transferred
    discharge_summary = db.Column(db.Text)
    total_charges = db.Column(db.Float, default=0)

    def __repr__(self):
        return f'<Admission {self.id}>'
    
    @property
    def duration_days(self):
        """Calculate admission duration in days"""
        if self.discharge_date:
            delta = self.discharge_date - self.admission_date
            return delta.days
        else:
            delta = datetime.now() - self.admission_date
            return delta.days
    
    @property
    def is_discharged(self):
        """Check if patient is discharged"""
        return self.status == 'discharged'
    
    @property
    def current_charges_per_day(self):
        """Calculate average charges per day"""
        if self.duration_days > 0:
            return self.total_charges / self.duration_days
        return 0
