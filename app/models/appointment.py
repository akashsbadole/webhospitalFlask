"""
Appointment database model
"""

from datetime import datetime
from app import db

class WebAppointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('web_patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('web_user.id'), nullable=False)
    appointment_date = db.Column(db.DateTime, nullable=False)
    appointment_type = db.Column(db.String(50), nullable=False)  # consultation, telemedicine, follow-up
    status = db.Column(db.String(20), default='scheduled')  # scheduled, completed, cancelled, no-show, checked_in, in_consultation
    notes = db.Column(db.Text)
    meeting_link = db.Column(db.String(500))  # For telemedicine
    check_in_time = db.Column(db.DateTime)
    consultation_start = db.Column(db.DateTime)
    consultation_end = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<WebAppointment {self.id}>'
    
    @property
    def duration_minutes(self):
        """Calculate appointment duration in minutes"""
        if self.consultation_start and self.consultation_end:
            delta = self.consultation_end - self.consultation_start
            return int(delta.total_seconds() / 60)
        return None
    
    def can_be_checked_in(self):
        """Check if appointment can be checked in"""
        return self.status == 'scheduled' and self.appointment_date <= datetime.now()
    
    def can_start_consultation(self):
        """Check if consultation can be started"""
        return self.status == 'checked_in'
