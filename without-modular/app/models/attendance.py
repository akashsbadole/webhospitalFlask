"""
Attendance and Enquiry database models
"""

from datetime import datetime
from app import db

class WebAttendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('web_user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    check_in = db.Column(db.DateTime)
    check_out = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='present')  # present, absent, late, half-day
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<WebAttendance {self.user_id}-{self.date}>'

class WebEnquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    enquiry_type = db.Column(db.String(50), nullable=False)  # general, appointment, emergency
    status = db.Column(db.String(20), default='new')  # new, in-progress, resolved
    assigned_to = db.Column(db.Integer, db.ForeignKey('web_user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<WebEnquiry {self.id}>'
