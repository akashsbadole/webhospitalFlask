"""
Billing and payment database models
"""

from datetime import datetime
from app import db

class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bill_number = db.Column(db.String(50), unique=True, nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('web_patient.id'), nullable=False)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescription.id'))
    bill_type = db.Column(db.String(20), nullable=False)  # opd, ipd, lab, pharmacy, imaging
    bill_date = db.Column(db.DateTime, default=datetime.utcnow)
    subtotal = db.Column(db.Float, default=0)
    discount_amount = db.Column(db.Float, default=0)
    tax_amount = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, default=0)
    final_amount = db.Column(db.Float, default=0)
    paid_amount = db.Column(db.Float, default=0)
    balance_amount = db.Column(db.Float, default=0)
    payment_status = db.Column(db.String(20), default='pending')  # pending, partial, paid
    insurance_claim_amount = db.Column(db.Float, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey('web_user.id'))
    
    # Relationships
    prescription = db.relationship('Prescription', backref='bill')

    # Relationships
    items = db.relationship('BillItem', backref='bill', lazy='dynamic')
    payments = db.relationship('Payment', backref='bill', lazy='dynamic')
    insurance_claims = db.relationship('InsuranceClaim', backref='bill', lazy='dynamic')

    def __repr__(self):
        return f'<Bill {self.bill_number}>'
    def to_dict(self):
        """Convert bill to dictionary for API responses"""
        return {
            'id': self.id,
            'bill_number': self.bill_number,
            'patient_id': self.patient_id,
            'prescription_id': self.prescription_id,
            'bill_type': self.bill_type,
            'bill_date': self.bill_date.isoformat() if self.bill_date else None,
            'subtotal': self.subtotal,
            'discount_amount': self.discount_amount,
            'tax_amount': self.tax_amount,
            'total_amount': self.total_amount,
            'final_amount': self.final_amount,
            'paid_amount': self.paid_amount,
            'balance_amount': self.balance_amount,
            'payment_status': self.payment_status,
            'insurance_claim_amount': self.insurance_claim_amount,
            'created_by': self.created_by,
            'is_paid': self.is_paid,
            'is_overdue': self.is_overdue
        }
    
    @property
    def is_paid(self):
        """Check if bill is fully paid"""
        return self.balance_amount <= 0
    
    @property
    def is_overdue(self):
        """Check if bill is overdue (30 days)"""
        if self.is_paid:
            return False
        return (datetime.now() - self.bill_date).days > 30

class BillItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id'), nullable=False)
    service_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<BillItem {self.id}>'

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id'), nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50))  # cash, card, online, insurance
    transaction_id = db.Column(db.String(100))
    notes = db.Column(db.Text)
    received_by = db.Column(db.Integer, db.ForeignKey('web_user.id'))

    def __repr__(self):
        return f'<Payment {self.id}>'
    
    def to_dict(self):
        """Convert payment to dictionary for API responses"""
        return {
            'id': self.id,
            'bill_id': self.bill_id,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'amount': self.amount,
            'payment_method': self.payment_method,
            'transaction_id': self.transaction_id,
            'notes': self.notes,
            'received_by': self.received_by
        }

class InsuranceClaim(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('web_patient.id'), nullable=False)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id'), nullable=False)
    claim_number = db.Column(db.String(50), unique=True, nullable=False)
    claim_date = db.Column(db.DateTime, default=datetime.utcnow)
    claim_amount = db.Column(db.Float, nullable=False)
    approved_amount = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='submitted')  # submitted, approved, rejected, paid
    insurance_provider = db.Column(db.String(100))
    policy_number = db.Column(db.String(50))
    notes = db.Column(db.Text)

    def __repr__(self):
        return f'<InsuranceClaim {self.claim_number}>'
    
    @property
    def is_approved(self):
        """Check if claim is approved"""
        return self.status == 'approved'
    
    @property
    def approval_amount(self):
        """Get the amount that was approved"""
        if self.is_approved:
            return self.approved_amount or self.claim_amount
        return 0
