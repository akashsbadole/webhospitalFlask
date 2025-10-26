#!/usr/bin/env python3
"""
Hospital Management System - Web Application
Flask-based web interface with modern responsive design
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, make_response, send_file, render_template_string, abort, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import sqlite3
import json
import os
from functools import wraps
import uuid
import calendar
import threading

# Import our new modules
from backup_manager import BackupManager
from audit_logger import AuditLogger, init_audit_logger, audit_action
from two_factor_auth import TwoFactorAuth, init_2fa, require_2fa
from notification_system import NotificationSystem, init_notification_system
from data_export_import import DataExportImport, create_download_response
from document_management import init_document_management
from advanced_security import init_advanced_security
from payment_gateway import init_payment_gateway
from emergency_management import init_emergency_management
from inventory_management import init_inventory_management
from quality_management import init_quality_management

# Import API routes for React integration
from api_routes import api_bp

# Initialize Flask app
app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital_web.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Register API blueprint for React
app.register_blueprint(api_bp, url_prefix='/api')

# Initialize new systems will be done after models are defined

# Global variables for systems
backup_manager = None
audit_logger = None
two_factor_auth = None
notification_system = None
data_export_import = None
document_management = None
# Role-based access control decorator
def role_required(*roles):
    """Decorator to require specific user roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.role not in roles:
                flash('Access denied! You do not have permission to access this page.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
advanced_security = None
payment_gateway = None
emergency_management = None
inventory_management = None
quality_management = None

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(WebUser, int(user_id))

# Database Models


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

class WebAppointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('web_patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('web_user.id'), nullable=False)
    appointment_date = db.Column(db.DateTime, nullable=False)
    appointment_type = db.Column(db.String(50), nullable=False)  # consultation, telemedicine, follow-up
    status = db.Column(db.String(20), default='scheduled')  # scheduled, completed, cancelled, no-show
    notes = db.Column(db.Text)
    meeting_link = db.Column(db.String(500))  # For telemedicine
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    patient = db.relationship('WebPatient', backref='appointments')
    doctor = db.relationship('WebUser', backref='appointments')

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

class WebAttendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('web_user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    check_in = db.Column(db.DateTime)
    check_out = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='present')  # present, absent, late, half-day
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('WebUser', backref='attendance_records')

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
    
    patient = db.relationship('WebPatient', backref='medical_records')
    doctor = db.relationship('WebUser', backref='medical_records')

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    patient = db.relationship('WebPatient', backref='prescriptions')
    doctor = db.relationship('WebUser', backref='prescriptions')

# Laboratory Management
class LabTest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_name = db.Column(db.String(100), nullable=False)
    test_code = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(50))
    normal_range = db.Column(db.String(100))
    price = db.Column(db.Float)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

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
    
    patient = db.relationship('WebPatient', backref='lab_orders')
    doctor = db.relationship('WebUser', backref='lab_orders')
    test = db.relationship('LabTest', backref='orders')

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
    
    lab_order = db.relationship('LabOrder', backref='results')
    technician = db.relationship('WebUser', foreign_keys=[technician_id])
    verifier = db.relationship('WebUser', foreign_keys=[verified_by])

# Radiology / Imaging
class ImagingTest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_name = db.Column(db.String(100), nullable=False)
    test_code = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(50))  # X-ray, MRI, CT, Ultrasound
    price = db.Column(db.Float)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

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
    
    patient = db.relationship('WebPatient', backref='imaging_orders')
    doctor = db.relationship('WebUser', backref='imaging_orders')
    test = db.relationship('ImagingTest', backref='orders')

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
    
    imaging_order = db.relationship('ImagingOrder', backref='results')
    radiologist = db.relationship('WebUser', backref='imaging_results')

# Pharmacy Management
class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    generic_name = db.Column(db.String(100))
    brand_name = db.Column(db.String(100))
    category = db.Column(db.String(50))
    dosage_form = db.Column(db.String(50))  # tablet, capsule, syrup, injection
    strength = db.Column(db.String(50))
    manufacturer = db.Column(db.String(100))
    batch_number = db.Column(db.String(50))
    expiry_date = db.Column(db.Date)
    purchase_price = db.Column(db.Float)
    selling_price = db.Column(db.Float)
    stock_quantity = db.Column(db.Integer, default=0)
    min_stock_level = db.Column(db.Integer, default=10)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PharmacyOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('web_patient.id'), nullable=False)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescription.id'))
    pharmacist_id = db.Column(db.Integer, db.ForeignKey('web_user.id'))
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Float)
    discount = db.Column(db.Float, default=0)
    tax_amount = db.Column(db.Float, default=0)
    final_amount = db.Column(db.Float)
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid, partial
    status = db.Column(db.String(20), default='pending')  # pending, dispensed, cancelled
    
    patient = db.relationship('WebPatient', backref='pharmacy_orders')
    prescription = db.relationship('Prescription', backref='pharmacy_orders')
    pharmacist = db.relationship('WebUser', backref='pharmacy_orders')

class PharmacyOrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pharmacy_order_id = db.Column(db.Integer, db.ForeignKey('pharmacy_order.id'), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicine.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    
    pharmacy_order = db.relationship('PharmacyOrder', backref='items')
    medicine = db.relationship('Medicine', backref='order_items')

# Inpatient / Admissions
class Ward(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ward_type = db.Column(db.String(50))  # general, icu, emergency, maternity
    total_beds = db.Column(db.Integer, nullable=False)
    available_beds = db.Column(db.Integer, nullable=False)
    charge_per_day = db.Column(db.Float)
    is_active = db.Column(db.Boolean, default=True)

class Bed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bed_number = db.Column(db.String(20), nullable=False)
    ward_id = db.Column(db.Integer, db.ForeignKey('ward.id'), nullable=False)
    bed_type = db.Column(db.String(50))  # general, private, icu
    is_occupied = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    ward = db.relationship('Ward', backref='beds')

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
    
    patient = db.relationship('WebPatient', backref='admissions')
    doctor = db.relationship('WebUser', backref='admissions')
    bed = db.relationship('Bed', backref='admissions')

# Billing System
class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bill_number = db.Column(db.String(50), unique=True, nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('web_patient.id'), nullable=False)
    bill_type = db.Column(db.String(20), nullable=False)  # opd, ipd, lab, pharmacy, imaging
    bill_date = db.Column(db.DateTime, default=datetime.utcnow)
    subtotal = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    tax_amount = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, default=0)
    paid_amount = db.Column(db.Float, default=0)
    balance_amount = db.Column(db.Float, default=0)
    payment_status = db.Column(db.String(20), default='pending')  # pending, partial, paid
    insurance_claim_amount = db.Column(db.Float, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey('web_user.id'))
    
    patient = db.relationship('WebPatient', backref='bills')
    created_by_user = db.relationship('WebUser', backref='created_bills')

class BillItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id'), nullable=False)
    service_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    
    bill = db.relationship('Bill', backref='items')

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id'), nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50))  # cash, card, online, insurance
    transaction_id = db.Column(db.String(100))
    notes = db.Column(db.Text)
    received_by = db.Column(db.Integer, db.ForeignKey('web_user.id'))
    
    bill = db.relationship('Bill', backref='payments')
    received_by_user = db.relationship('WebUser', backref='received_payments')

# Insurance Claims
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
    
    patient = db.relationship('WebPatient', backref='insurance_claims')
    bill = db.relationship('Bill', backref='insurance_claims')

# Settings Management Models
class HospitalSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False)
    setting_value = db.Column(db.Text)
    setting_type = db.Column(db.String(20), default='string')  # string, number, boolean, json
    category = db.Column(db.String(50), default='general')  # general, organization, security, clinical, etc.
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class HospitalBranch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    address = db.Column(db.Text)
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(10))
    country = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    domain = db.Column(db.String(100))  # Custom domain/subdomain for this branch
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class NotificationTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    email_subject = db.Column(db.String(200))
    email_body = db.Column(db.Text)
    sms_content = db.Column(db.Text)
    whatsapp_content = db.Column(db.Text)
    variables = db.Column(db.Text)  # JSON string of available variables
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PaymentGateway(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    gateway_type = db.Column(db.String(50))  # paypal, razorpay, paytm, stripe
    api_key = db.Column(db.Text)
    api_secret = db.Column(db.Text)
    merchant_id = db.Column(db.String(100))
    is_test_mode = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class InsuranceProvider(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    contact_person = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    claim_rules = db.Column(db.Text)  # JSON string of claim rules
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DiscountPolicy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    discount_type = db.Column(db.String(20))  # percentage, fixed
    discount_value = db.Column(db.Float, nullable=False)
    min_amount = db.Column(db.Float, default=0)
    max_discount = db.Column(db.Float)
    applicable_services = db.Column(db.Text)  # JSON string of applicable services
    user_roles = db.Column(db.Text)  # JSON string of eligible user roles
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TaxRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    tax_type = db.Column(db.String(20))  # gst, vat, sales_tax
    tax_percentage = db.Column(db.Float, nullable=False)
    applicable_services = db.Column(db.Text)  # JSON string of applicable services
    exemptions = db.Column(db.Text)  # JSON string of exemptions
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ConsentForm(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    form_type = db.Column(db.String(50))  # treatment, privacy, telemedicine
    description = db.Column(db.Text)
    file_path = db.Column(db.String(500))  # Path to PDF file
    is_required = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserRoleTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    base_role = db.Column(db.String(50))  # admin, doctor, nurse, etc.
    permissions = db.Column(db.Text)  # JSON string of permissions
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AppointmentSlotTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.Integer, default=15)  # Duration in minutes
    buffer_time = db.Column(db.Integer, default=5)  # Buffer time in minutes
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Departments and Services
class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.Text)
    head_of_department = db.Column(db.Integer, db.ForeignKey('web_user.id'))
    is_active = db.Column(db.Boolean, default=True)
    
    hod = db.relationship('WebUser', backref='headed_departments')

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    price = db.Column(db.Float)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    
    department = db.relationship('Department', backref='services')

# Comprehensive Language Support
LANGUAGES = {
    'en': {
        # Navigation & Core
        'title': 'Hospital Management System',
        'welcome': 'Welcome to MediCare Pro',
        'login': 'Login',
        'logout': 'Logout',
        'dashboard': 'Dashboard',
        'home': 'Home',
        'profile': 'Profile',
        'settings': 'Settings',
        'language': 'Language',
        
        # Main Modules
        'patients': 'Patients',
        'appointments': 'Appointments',
        'enquiries': 'Enquiries',
        'attendance': 'Attendance',
        'telemedicine': 'Telemedicine',
        'clinical': 'Clinical',
        'pharmacy': 'Pharmacy',
        'billing': 'Billing',
        'administration': 'Administration',
        'reports': 'Reports',
        
        # Patient Management
        'all_patients': 'All Patients',
        'add_patient': 'Add Patient',
        'patient_details': 'Patient Details',
        'patient_id': 'Patient ID',
        'first_name': 'First Name',
        'last_name': 'Last Name',
        'email': 'Email',
        'phone': 'Phone',
        'date_of_birth': 'Date of Birth',
        'gender': 'Gender',
        'address': 'Address',
        'emergency_contact': 'Emergency Contact',
        'blood_group': 'Blood Group',
        'allergies': 'Allergies',
        'medical_history': 'Medical History',
        
        # Appointments
        'all_appointments': 'All Appointments',
        'schedule_new': 'Schedule New',
        'appointment_date': 'Appointment Date',
        'appointment_time': 'Appointment Time',
        'doctor': 'Doctor',
        'appointment_type': 'Appointment Type',
        'consultation': 'Consultation',
        'follow_up': 'Follow-up',
        'status': 'Status',
        'scheduled': 'Scheduled',
        'completed': 'Completed',
        'cancelled': 'Cancelled',
        'no_show': 'No Show',
        
        # Clinical
        'lab_orders': 'Lab Orders',
        'imaging_orders': 'Imaging Orders',
        'admissions': 'Admissions',
        'medical_records': 'Medical Records',
        'prescriptions': 'Prescriptions',
        'lab_results': 'Lab Results',
        'imaging_results': 'Imaging Results',
        
        # Pharmacy
        'medicines': 'Medicines',
        'pharmacy_orders': 'Pharmacy Orders',
        'dispense_medicine': 'Dispense Medicine',
        'stock_management': 'Stock Management',
        'low_stock_alert': 'Low Stock Alert',
        
        # Billing
        'all_bills': 'All Bills',
        'create_bill': 'Create Bill',
        'payments': 'Payments',
        'invoices': 'Invoices',
        'insurance_claims': 'Insurance Claims',
        'bill_number': 'Bill Number',
        'total_amount': 'Total Amount',
        'paid_amount': 'Paid Amount',
        'balance_amount': 'Balance Amount',
        'payment_status': 'Payment Status',
        'pending': 'Pending',
        'paid': 'Paid',
        'partial': 'Partial',
        
        # Administration
        'staff_management': 'Staff Management',
        'departments': 'Departments',
        'wards_beds': 'Wards & Beds',
        'services': 'Services',
        'user_roles': 'User Roles',
        
        # Common Actions
        'add': 'Add',
        'edit': 'Edit',
        'delete': 'Delete',
        'save': 'Save',
        'cancel': 'Cancel',
        'submit': 'Submit',
        'search': 'Search',
        'filter': 'Filter',
        'export': 'Export',
        'print': 'Print',
        'view': 'View',
        'update': 'Update',
        'create': 'Create',
        
        # Status & States
        'active': 'Active',
        'inactive': 'Inactive',
        'enabled': 'Enabled',
        'disabled': 'Disabled',
        'available': 'Available',
        'unavailable': 'Unavailable',
        'occupied': 'Occupied',
        'vacant': 'Vacant',
        
        # Time & Dates
        'today': 'Today',
        'yesterday': 'Yesterday',
        'tomorrow': 'Tomorrow',
        'this_week': 'This Week',
        'this_month': 'This Month',
        'date': 'Date',
        'time': 'Time',
        'duration': 'Duration',
        
        # Messages
        'success': 'Success',
        'error': 'Error',
        'warning': 'Warning',
        'info': 'Information',
        'loading': 'Loading...',
        'no_data': 'No data available',
        'confirm_delete': 'Are you sure you want to delete?',
        'operation_successful': 'Operation completed successfully',
        'operation_failed': 'Operation failed',
        'sync_data': 'Sync Data',
        'occupancy_rate': 'Occupancy Rate',
        
        # Forms
        'required_field': 'Required field',
        'optional': 'Optional',
        'select_option': 'Select an option',
        'choose_file': 'Choose file',
        'upload': 'Upload',
        'download': 'Download',
        
        # Statistics
        'total': 'Total',
        'count': 'Count',
        'percentage': 'Percentage',
        'average': 'Average',
        'minimum': 'Minimum',
        'maximum': 'Maximum',
        'statistics': 'Statistics',
        'analytics': 'Analytics'
    },
    'hi': {
        # Navigation & Core
        'title': 'अस्पताल प्रबंधन प्रणाली',
        'welcome': 'मेडिकेयर प्रो में आपका स्वागत है',
        'login': 'लॉगिन',
        'logout': 'लॉगआउट',
        'dashboard': 'डैशबोर्ड',
        'home': 'होम',
        'profile': 'प्रोफाइल',
        'settings': 'सेटिंग्स',
        'language': 'भाषा',
        
        # Main Modules
        'patients': 'मरीज़',
        'appointments': 'अपॉइंटमेंट',
        'enquiries': 'पूछताछ',
        'attendance': 'उपस्थिति',
        'telemedicine': 'टेलीमेडिसिन',
        'clinical': 'क्लिनिकल',
        'pharmacy': 'फार्मेसी',
        'billing': 'बिलिंग',
        'administration': 'प्रशासन',
        'reports': 'रिपोर्ट्स',
        
        # Patient Management
        'all_patients': 'सभी मरीज़',
        'add_patient': 'मरीज़ जोड़ें',
        'patient_details': 'मरीज़ विवरण',
        'patient_id': 'मरीज़ आईडी',
        'first_name': 'पहला नाम',
        'last_name': 'अंतिम नाम',
        'email': 'ईमेल',
        'phone': 'फोन',
        'date_of_birth': 'जन्म तिथि',
        'gender': 'लिंग',
        'address': 'पता',
        'emergency_contact': 'आपातकालीन संपर्क',
        'blood_group': 'रक्त समूह',
        'allergies': 'एलर्जी',
        'medical_history': 'चिकित्सा इतिहास',
        
        # Appointments
        'all_appointments': 'सभी अपॉइंटमेंट',
        'schedule_new': 'नया शेड्यूल करें',
        'appointment_date': 'अपॉइंटमेंट तारीख',
        'appointment_time': 'अपॉइंटमेंट समय',
        'doctor': 'डॉक्टर',
        'appointment_type': 'अपॉइंटमेंट प्रकार',
        'consultation': 'परामर्श',
        'follow_up': 'फॉलो-अप',
        'status': 'स्थिति',
        'scheduled': 'निर्धारित',
        'completed': 'पूर्ण',
        'cancelled': 'रद्द',
        'no_show': 'नहीं आया',
        
        # Common Actions
        'add': 'जोड़ें',
        'edit': 'संपादित करें',
        'delete': 'हटाएं',
        'save': 'सेव करें',
        'cancel': 'रद्द करें',
        'submit': 'जमा करें',
        'search': 'खोजें',
        'filter': 'फिल्टर',
        'export': 'निर्यात',
        'print': 'प्रिंट',
        'view': 'देखें',
        'update': 'अपडेट',
        'create': 'बनाएं',
        
        # Messages
        'success': 'सफलता',
        'error': 'त्रुटि',
        'warning': 'चेतावनी',
        'info': 'जानकारी',
        'loading': 'लोड हो रहा है...',
        'no_data': 'कोई डेटा उपलब्ध नहीं',
        'operation_successful': 'ऑपरेशन सफलतापूर्वक पूरा हुआ',
        'operation_failed': 'ऑपरेशन असफल',

         # Clinical
        'lab_orders': 'प्रयोगशाला आदेश',
        'imaging_orders': 'इमेजिंग आदेश',
        'admissions': 'भर्ती',
        'medical_records': 'चिकित्सा रिकॉर्ड',
        'prescriptions': 'पर्चे',
        'lab_results': 'प्रयोगशाला परिणाम',
        'imaging_results': 'इमेजिंग परिणाम',

        # Pharmacy
        'medicines': 'दवाइयां',
        'pharmacy_orders': 'फार्मेसी आदेश',
        'dispense_medicine': 'दवा वितरित करें',
        'stock_management': 'स्टॉक प्रबंधन',
        'low_stock_alert': 'कम स्टॉक चेतावनी',

        # Billing
        'all_bills': 'सभी बिल',
        'create_bill': 'बिल बनाएं',
        'payments': 'भुगतान',
        'invoices': 'चालान',
        'insurance_claims': 'बीमा दावे',
        'bill_number': 'बिल नंबर',
        'total_amount': 'कुल राशि',
        'paid_amount': 'भुगतान की राशि',
        'balance_amount': 'बकाया राशि',
        'payment_status': 'भुगतान की स्थिति',
        'pending': 'लंबित',
        'paid': 'भुगतान किया गया',
        'partial': 'आंशिक',

        # Administration
        'staff_management': 'स्टाफ प्रबंधन',
        'departments': 'विभाग',
        'wards_beds': 'वार्ड और बिस्तर',
        'services': 'सेवाएं',
        'user_roles': 'उपयोगकर्ता भूमिकाएं',

        # Status & Dates
        'active': 'सक्रिय',
        'inactive': 'निष्क्रिय',
        'enabled': 'सक्रिय',
        'disabled': 'अक्षम',
        'available': 'उपलब्ध',
        'unavailable': 'अनुपलब्ध',
        'occupied': 'कब्जा किया',
        'vacant': 'खाली',

        # Time
        'today': 'आज',
        'yesterday': 'कल',
        'tomorrow': 'कल (आने वाला)',
        'this_week': 'इस सप्ताह',
        'this_month': 'इस महीने',
        'date': 'तारीख',
        'time': 'समय',
        'duration': 'अवधि',

        # Forms
        'required_field': 'अनिवार्य फ़ील्ड',
        'optional': 'वैकल्पिक',
        'select_option': 'एक विकल्प चुनें',
        'choose_file': 'फ़ाइल चुनें',
        'upload': 'अपलोड',
        'download': 'डाउनलोड',

        # Stats
        'total': 'कुल',
        'count': 'गिनती',
        'percentage': 'प्रतिशत',
        'average': 'औसत',
        'minimum': 'न्यूनतम',
        'maximum': 'अधिकतम',
        'statistics': 'आँकड़े',
        'analytics': 'विश्लेषण'
    },
    'mr': {
        # Navigation & Core
        'title': 'रुग्णालय व्यवस्थापन प्रणाली',
        'welcome': 'मेडिकेअर प्रो मध्ये आपले स्वागत आहे',
        'login': 'लॉगिन',
        'logout': 'लॉगआउट',
        'dashboard': 'डॅशबोर्ड',
        'home': 'होम',
        'profile': 'प्रोफाइल',
        'settings': 'सेटिंग्स',
        'language': 'भाषा',
        
        # Main Modules
        'patients': 'रुग्ण',
        'appointments': 'भेटी',
        'enquiries': 'चौकशी',
        'attendance': 'उपस्थिती',
        'telemedicine': 'टेलिमेडिसिन',
        'clinical': 'क्लिनिकल',
        'pharmacy': 'फार्मसी',
        'billing': 'बिलिंग',
        'administration': 'प्रशासन',
        'reports': 'अहवाल',
        
        # Patient Management
        'all_patients': 'सर्व रुग्ण',
        'add_patient': 'रुग्ण जोडा',
        'patient_details': 'रुग्ण तपशील',
        'patient_id': 'रुग्ण आयडी',
        'first_name': 'पहिले नाव',
        'last_name': 'आडनाव',
        'email': 'ईमेल',
        'phone': 'फोन',
        'date_of_birth': 'जन्म तारीख',
        'gender': 'लिंग',
        'address': 'पत्ता',
        'emergency_contact': 'आपत्कालीन संपर्क',
        'blood_group': 'रक्त गट',
        'allergies': 'ऍलर्जी',
        'medical_history': 'वैद्यकीय इतिहास',

        # Clinical
        'lab_orders': 'प्रयोगशाळा आदेश',
        'imaging_orders': 'इमेजिंग आदेश',
        'admissions': 'प्रवेश',
        'medical_records': 'वैद्यकीय नोंदी',
        'prescriptions': 'प्रिस्क्रिप्शन',
        'lab_results': 'प्रयोगशाळा निकाल',
        'imaging_results': 'इमेजिंग निकाल',

        # Pharmacy
        'medicines': 'औषधे',
        'pharmacy_orders': 'फार्मसी आदेश',
        'dispense_medicine': 'औषध द्या',
        'stock_management': 'साठा व्यवस्थापन',
        'low_stock_alert': 'कमी साठा चेतावणी',

        # Billing
        'all_bills': 'सर्व बिल',
        'create_bill': 'बिल तयार करा',
        'payments': 'देयके',
        'invoices': 'चलन',
        'insurance_claims': 'विमा दावे',
        'bill_number': 'बिल क्रमांक',
        'total_amount': 'एकूण रक्कम',
        'paid_amount': 'भरणा केलेली रक्कम',
        'balance_amount': 'बाकी रक्कम',
        'payment_status': 'पेमेंट स्थिती',
        'pending': 'प्रलंबित',
        'paid': 'भरणा झाला',
        'partial': 'आंशिक',

        # Administration
        'staff_management': 'कर्मचारी व्यवस्थापन',
        'departments': 'विभाग',
        'wards_beds': 'वार्ड आणि खाट',
        'services': 'सेवा',
        'user_roles': 'वापरकर्ता भूमिका',

        # Status & Dates
        'active': 'सक्रिय',
        'inactive': 'निष्क्रिय',
        'enabled': 'सक्षम',
        'disabled': 'अक्षम',
        'available': 'उपलब्ध',
        'unavailable': 'अनुपलब्ध',
        'occupied': 'व्याप्त',
        'vacant': 'रिक्त',

        # Time
        'today': 'आज',
        'yesterday': 'काल',
        'tomorrow': 'उद्या',
        'this_week': 'या आठवड्यात',
        'this_month': 'या महिन्यात',
        'date': 'तारीख',
        'time': 'वेळ',
        'duration': 'कालावधी',

        # Forms
        'required_field': 'आवश्यक फील्ड',
        'optional': 'पर्यायी',
        'select_option': 'पर्याय निवडा',
        'choose_file': 'फाइल निवडा',
        'upload': 'अपलोड',
        'download': 'डाउनलोड',

        # Stats
        'total': 'एकूण',
        'count': 'संख्या',
        'percentage': 'टक्केवारी',
        'average': 'सरासरी',
        'minimum': 'किमान',
        'maximum': 'कमाल',
        'statistics': 'सांख्यिकी',
        'analytics': 'विश्लेषण',
        'all_appointments': 'सर्व भेटी',
        'schedule_new': 'नवीन वेळापत्रक'
    },
    'te': {
        # Navigation & Core
        'title': 'ఆసుపత్రి నిర్వహణ వ్యవస్థ',
        'welcome': 'మెడికేర్ ప్రోకు స్వాగతం',
        'login': 'లాగిన్',
        'logout': 'లాగ్అవుట్',
        'dashboard': 'డాష్‌బోర్డ్',
        'home': 'హోమ్',
        'profile': 'ప్రొఫైల్',
        'settings': 'సెట్టింగ్స్',
        'language': 'భాష',
        
        # Main Modules
        'patients': 'రోగులు',
        'appointments': 'అపాయింట్‌మెంట్లు',
        'enquiries': 'విచారణలు',
        'attendance': 'హాజరు',
        'telemedicine': 'టెలిమెడిసిన్',
        'clinical': 'క్లినికల్',
        'pharmacy': 'ఫార్మసీ',
        'billing': 'బిల్లింగ్',
        'administration': 'పరిపాలన',
        'reports': 'నివేదికలు',
        
        # Patient Management
        'all_patients': 'అన్ని రోగులు',
        'add_patient': 'రోగిని జోడించండి',
        'patient_details': 'రోగి వివరాలు',
        'patient_id': 'రోగి ID',
        'first_name': 'మొదటి పేరు',
        'last_name': 'చివరి పేరు',
        'email': 'ఇమెయిల్',
        'phone': 'ఫోన్',
        'date_of_birth': 'పుట్టిన తేదీ',
        'gender': 'లింగం',
        'address': 'చిరునామా',
        'emergency_contact': 'అత్యవసర సంప్రదింపు',
        'blood_group': 'రక్త వర్గం',
        'allergies': 'అలెర్జీలు',
        'medical_history': 'వైద్య చరిత్ర',

        'lab_orders': 'ప్రయోగశాల ఆదేశాలు',
        'imaging_orders': 'ఇమేజింగ్ ఆదేశాలు',
        'admissions': 'ప్రవేశాలు',
        'medical_records': 'వైద్య రికార్డులు',
        'prescriptions': 'ప్రిస్క్రిప్షన్లు',
        'lab_results': 'ప్రయోగశాల ఫలితాలు',
        'imaging_results': 'ఇమేజింగ్ ఫలితాలు',

        'medicines': 'మందులు',
        'pharmacy_orders': 'ఫార్మసీ ఆర్డర్లు',
        'dispense_medicine': 'ఔషధం పంపిణీ చేయండి',
        'stock_management': 'స్టాక్ నిర్వహణ',
        'low_stock_alert': 'తక్కువ స్టాక్ హెచ్చరిక',

        'all_bills': 'అన్ని బిల్లులు',
        'create_bill': 'బిల్లు సృష్టించండి',
        'payments': 'చెల్లింపులు',
        'invoices': 'ఇన్వాయిస్‌లు',
        'insurance_claims': 'భీమా క్లెయిమ్‌లు',
        'bill_number': 'బిల్ నంబర్',
        'total_amount': 'మొత్తం మొత్తం',
        'paid_amount': 'చెల్లించిన మొత్తం',
        'balance_amount': 'బాకీ మొత్తం',
        'payment_status': 'చెల్లింపు స్థితి',
        'pending': 'పెండింగ్',
        'paid': 'చెల్లించబడింది',
        'partial': 'పాక్షిక',

        'staff_management': 'సిబ్బంది నిర్వహణ',
        'departments': 'విభాగాలు',
        'wards_beds': 'వార్డులు & బెడ్స్',
        'services': 'సేవలు',
        'user_roles': 'వినియోగదారుల పాత్రలు',

        'active': 'సక్రియం',
        'inactive': 'నిష్క్రియం',
        'enabled': 'ప్రారంభించబడింది',
        'disabled': 'డిసేబుల్ చేయబడింది',
        'available': 'లభిస్తుంది',
        'unavailable': 'లభించదు',
        'occupied': 'పూర్తిగా ఉంది',
        'vacant': 'ఖాళీగా ఉంది',

        'today': 'ఈ రోజు',
        'yesterday': 'నిన్న',
        'tomorrow': 'రేపు',
        'this_week': 'ఈ వారం',
        'this_month': 'ఈ నెల',
        'date': 'తేదీ',
        'time': 'సమయం',
        'duration': 'వ్యవధి',

        'required_field': 'తప్పనిసరి ఫీల్డ్',
        'optional': 'ఐచ్చికం',
        'select_option': 'ఎంపికను ఎంచుకోండి',
        'choose_file': 'ఫైల్ ఎంచుకోండి',
        'upload': 'అప్‌లోడ్',
        'download': 'డౌన్‌లోడ్',

        'total': 'మొత్తం',
        'count': 'ఎన్నిక',
        'percentage': 'శాతం',
        'average': 'సగటు',
        'minimum': 'కనిష్టం',
        'maximum': 'గరిష్టం',
        'statistics': 'గణాంకాలు',
        'analytics': 'విశ్లేషణ',
        'all_appointments': 'అన్ని అపాయింట్‌మెంట్లు',
        'schedule_new': 'కొత్తది షెడ్యూల్ చేయండి'
    },
    'ta': {
        # Navigation & Core
        'title': 'மருத்துவமனை மேலாண்மை அமைப்பு',
        'welcome': 'மெடிகேர் ப்ரோவிற்கு வரவேற்கிறோம்',
        'login': 'உள்நுழைவு',
        'logout': 'வெளியேறு',
        'dashboard': 'டாஷ்போர்டு',
        'home': 'முகப்பு',
        'profile': 'சுயவிவரம்',
        'settings': 'அமைப்புகள்',
        'language': 'மொழி',
        
        # Main Modules
        'patients': 'நோயாளிகள்',
        'appointments': 'சந்திப்புகள்',
        'enquiries': 'விசாரணைகள்',
        'attendance': 'வருகை',
        'telemedicine': 'தொலைமருத்துவம்',
        'clinical': 'மருத்துவ',
        'pharmacy': 'மருந்தகம்',
        'billing': 'பில்லிங்',
        'administration': 'நிர்வாகம்',
        'reports': 'அறிக்கைகள்',
        
        # Patient Management
        'all_patients': 'அனைத்து நோயாளிகள்',
        'add_patient': 'நோயாளியைச் சேர்க்கவும்',
        'patient_details': 'நோயாளி விவரங்கள்',
        'patient_id': 'நோயாளி ID',
        'first_name': 'முதல் பெயர்',
        'last_name': 'கடைசி பெயர்',
        'email': 'மின்னஞ்சல்',
        'phone': 'தொலைபேசி',
        'date_of_birth': 'பிறந்த தேதி',
        'gender': 'பாலினம்',
        'address': 'முகவரி',
        'emergency_contact': 'அவசர தொடர்பு',
        'blood_group': 'இரத்த வகை',
        'allergies': 'ஒவ்வாமைகள்',
        'medical_history': 'மருத்துவ வரலாறு',

        'lab_orders': 'ஆய்வக ஆணைகள்',
        'imaging_orders': 'படமெடுக்கும் ஆணைகள்',
        'admissions': 'சேர்க்கைகள்',
        'medical_records': 'மருத்துவ பதிவுகள்',
        'prescriptions': 'மருத்துவ பரிந்துரைகள்',
        'lab_results': 'ஆய்வக முடிவுகள்',
        'imaging_results': 'படமெடுக்கும் முடிவுகள்',

        'medicines': 'மருந்துகள்',
        'pharmacy_orders': 'மருந்தக ஆணைகள்',
        'dispense_medicine': 'மருந்து வழங்கவும்',
        'stock_management': 'சரக்கு மேலாண்மை',
        'low_stock_alert': 'குறைந்த சரக்கு எச்சரிக்கை',

        'all_bills': 'அனைத்து பில்கள்',
        'create_bill': 'பில் உருவாக்கவும்',
        'payments': 'கொடுப்பனவுகள்',
        'invoices': 'விலைப்பட்டியல்',
        'insurance_claims': 'காப்பீடு கோரிக்கைகள்',
        'bill_number': 'பில் எண்',
        'total_amount': 'மொத்த தொகை',
        'paid_amount': 'செலுத்திய தொகை',
        'balance_amount': 'மீதமுள்ள தொகை',
        'payment_status': 'கொடுப்பனவு நிலை',
        'pending': 'நிலுவையில்',
        'paid': 'செலுத்தப்பட்டது',
        'partial': 'பகுதி',

        'staff_management': 'ஊழியர் மேலாண்மை',
        'departments': 'துறைகள்',
        'wards_beds': 'வார்ட்கள் & படுக்கைகள்',
        'services': 'சேவைகள்',
        'user_roles': 'பயனர் பங்கு',

        'active': 'செயலில்',
        'inactive': 'செயலற்றது',
        'enabled': 'இயக்கப்பட்டது',
        'disabled': 'முடக்கப்பட்டது',
        'available': 'கிடைக்கிறது',
        'unavailable': 'கிடைக்கவில்லை',
        'occupied': 'பிரயோகத்தில் உள்ளது',
        'vacant': 'வெற்று',

        'today': 'இன்று',
        'yesterday': 'நேற்று',
        'tomorrow': 'நாளை',
        'this_week': 'இந்த வாரம்',
        'this_month': 'இந்த மாதம்',
        'date': 'தேதி',
        'time': 'நேரம்',
        'duration': 'கால அளவு',

        'required_field': 'தேவையான புலம்',
        'optional': 'விருப்பத்தேர்வு',
        'select_option': 'ஒரு விருப்பத்தைத் தேர்வுசெய்க',
        'choose_file': 'கோப்பைத் தேர்ந்தெடுக்கவும்',
        'upload': 'பதிவேற்றவும்',
        'download': 'பதிவிறக்கவும்',

        'total': 'மொத்தம்',
        'count': 'எண்ணிக்கை',
        'percentage': 'சதவீதம்',
        'average': 'சராசரி',
        'minimum': 'குறைந்தபட்சம்',
        'maximum': 'அதிகபட்சம்',
        'statistics': 'புள்ளிவிவரங்கள்',
        'analytics': 'பகுப்பாய்வு',
        'all_appointments': 'அனைத்து சந்திப்புகள்',
        'schedule_new': 'புதியதை அட்டவணைப்படுத்தவும்'
    },
    'gu': {
        # Navigation & Core
        'title': 'હોસ્પિટલ મેનેજમેન્ટ સિસ્ટમ',
        'welcome': 'મેડિકેર પ્રોમાં આપનું સ્વાગત છે',
        'login': 'લોગિન',
        'logout': 'લોગઆઉટ',
        'dashboard': 'ડેશબોર્ડ',
        'home': 'હોમ',
        'profile': 'પ્રોફાઇલ',
        'settings': 'સેટિંગ્સ',
        'language': 'ભાષા',
        
        # Main Modules
        'patients': 'દર્દીઓ',
        'appointments': 'મુલાકાતો',
        'enquiries': 'પૂછપરછ',
        'attendance': 'હાજરી',
        'telemedicine': 'ટેલિમેડિસિન',
        'clinical': 'ક્લિનિકલ',
        'pharmacy': 'ફાર્મસી',
        'billing': 'બિલિંગ',
        'administration': 'વહીવટ',
        'reports': 'રિપોર્ટ્સ',

        'lab_orders': 'લેબ ઓર્ડર',
        'imaging_orders': 'ઇમેજિંગ ઓર્ડર',
        'admissions': 'પ્રવેશ',
        'medical_records': 'મેડિકલ રેકોર્ડ્સ',
        'prescriptions': 'પ્રિસ્ક્રિપ્શન',
        'lab_results': 'લેબ પરિણામો',
        'imaging_results': 'ઇમેજિંગ પરિણામો',

        'medicines': 'દવાઓ',
        'pharmacy_orders': 'ફાર્મસી ઓર્ડર',
        'dispense_medicine': 'દવા આપો',
        'stock_management': 'સ્ટોક મેનેજમેન્ટ',
        'low_stock_alert': 'ઓછો સ્ટોક એલર્ટ',

        'all_bills': 'બધા બિલ',
        'create_bill': 'બિલ બનાવો',
        'payments': 'ચુકવણીઓ',
        'invoices': 'ઈન્વૉઇસ',
        'insurance_claims': 'વીમા દાવાઓ',
        'bill_number': 'બિલ નંબર',
        'total_amount': 'કુલ રકમ',
        'paid_amount': 'ચૂકવેલ રકમ',
        'balance_amount': 'બાકી રકમ',
        'payment_status': 'ચુકવણીની સ્થિતિ',
        'pending': 'બાકી',
        'paid': 'ચૂકવેલ',
        'partial': 'આંશિક',

        'staff_management': 'સ્ટાફ મેનેજમેન્ટ',
        'departments': 'વિભાગો',
        'wards_beds': 'વોર્ડ્સ અને પથારી',
        'services': 'સેવાઓ',
        'user_roles': 'વપરાશકર્તા ભૂમિકાઓ',

        'active': 'સક્રિય',
        'inactive': 'નિષ્ક્રિય',
        'enabled': 'સક્રિય કર્યું',
        'disabled': 'અક્ષમ કર્યું',
        'available': 'ઉપલબ્ધ',
        'unavailable': 'અનુપલબ્ધ',
        'occupied': 'ભરાયેલું',
        'vacant': 'ખાલી',

        'today': 'આજે',
        'yesterday': 'ગઈકાલે',
        'tomorrow': 'આવતીકાલે',
        'this_week': 'આ અઠવાડિયે',
        'this_month': 'આ મહિને',
        'date': 'તારીખ',
        'time': 'સમય',
        'duration': 'સમયગાળો',

        'required_field': 'આવશ્યક ફીલ્ડ',
        'optional': 'વૈકલ્પિક',
        'select_option': 'વિકલ્પ પસંદ કરો',
        'choose_file': 'ફાઇલ પસંદ કરો',
        'upload': 'અપલોડ કરો',
        'download': 'ડાઉનલોડ કરો',

        'total': 'કુલ',
        'count': 'ગણતરી',
        'percentage': 'ટકાવારી',
        'average': 'સરેરાશ',
        'minimum': 'ન્યૂનતમ',
        'maximum': 'સર્વોચ્ચ',
        'statistics': 'આંકડા',
        'analytics': 'વિશ્લેષણ',
        'all_appointments': 'બધી મુલાકાતો',
        'schedule_new': 'નવું શેડ્યૂલ કરો'
    },
    'bn': {
        # Navigation & Core
        'title': 'হাসপাতাল ব্যবস্থাপনা সিস্টেম',
        'welcome': 'মেডিকেয়ার প্রোতে আপনাকে স্বাগতম',
        'login': 'লগইন',
        'logout': 'লগআউট',
        'dashboard': 'ড্যাশবোর্ড',
        'home': 'হোম',
        'profile': 'প্রোফাইল',
        'settings': 'সেটিংস',
        'language': 'ভাষা',
        
        # Main Modules
        'patients': 'রোগীরা',
        'appointments': 'অ্যাপয়েন্টমেন্ট',
        'enquiries': 'অনুসন্ধান',
        'attendance': 'উপস্থিতি',
        'telemedicine': 'টেলিমেডিসিন',
        'clinical': 'ক্লিনিক্যাল',
        'pharmacy': 'ফার্মেসি',
        'billing': 'বিলিং',
        'administration': 'প্রশাসন',
        'reports': 'রিপোর্ট',

        'lab_orders': 'ল্যাব অর্ডার',
        'imaging_orders': 'ইমেজিং অর্ডার',
        'admissions': 'ভর্তি',
        'medical_records': 'মেডিকেল রেকর্ড',
        'prescriptions': 'প্রেসক্রিপশন',
        'lab_results': 'ল্যাব ফলাফল',
        'imaging_results': 'ইমেজিং ফলাফল',

        'medicines': 'ওষুধ',
        'pharmacy_orders': 'ফার্মেসি অর্ডার',
        'dispense_medicine': 'ওষুধ বিতরণ করুন',
        'stock_management': 'স্টক ম্যানেজমেন্ট',
        'low_stock_alert': 'কম স্টকের সতর্কতা',

        'all_bills': 'সমস্ত বিল',
        'create_bill': 'বিল তৈরি করুন',
        'payments': 'পেমেন্ট',
        'invoices': 'ইনভয়েস',
        'insurance_claims': 'বীমা দাবি',
        'bill_number': 'বিল নম্বর',
        'total_amount': 'মোট পরিমাণ',
        'paid_amount': 'প্রদত্ত পরিমাণ',
        'balance_amount': 'বাকি পরিমাণ',
        'payment_status': 'পেমেন্টের অবস্থা',
        'pending': 'অপেক্ষমান',
        'paid': 'পরিশোধিত',
        'partial': 'আংশিক',

        'staff_management': 'স্টাফ ম্যানেজমেন্ট',
        'departments': 'বিভাগ',
        'wards_beds': 'ওয়ার্ড এবং বিছানা',
        'services': 'সেবা',
        'user_roles': 'ব্যবহারকারীর ভূমিকা',

        'active': 'সক্রিয়',
        'inactive': 'নিষ্ক্রিয়',
        'enabled': 'সক্রিয় হয়েছে',
        'disabled': 'নিষ্ক্রিয় হয়েছে',
        'available': 'উপলব্ধ',
        'unavailable': 'অনুপলব্ধ',
        'occupied': 'দখল করা হয়েছে',
        'vacant': 'খালি',

        'today': 'আজ',
        'yesterday': 'গতকাল',
        'tomorrow': 'আগামীকাল',
        'this_week': 'এই সপ্তাহে',
        'this_month': 'এই মাসে',
        'date': 'তারিখ',
        'time': 'সময়',
        'duration': 'সময়কাল',

        'required_field': 'প্রয়োজনীয় ক্ষেত্র',
        'optional': 'ঐচ্ছিক',
        'select_option': 'একটি বিকল্প নির্বাচন করুন',
        'choose_file': 'ফাইল নির্বাচন করুন',
        'upload': 'আপলোড করুন',
        'download': 'ডাউনলোড করুন',

        'total': 'মোট',
        'count': 'সংখ্যা',
        'percentage': 'শতাংশ',
        'average': 'গড়',
        'minimum': 'ন্যূনতম',
        'maximum': 'সর্বাধিক',
        'statistics': 'পরিসংখ্যান',
        'analytics': 'বিশ্লেষণ',
        'all_appointments': 'সমস্ত অ্যাপয়েন্টমেন্ট',
        'schedule_new': 'নতুন সময়সূচি তৈরি করুন'
    },
    'kn': {
        # Navigation & Core
        'title': 'ಆಸ್ಪತ್ರೆ ನಿರ್ವಹಣಾ ವ್ಯವಸ್ಥೆ',
        'welcome': 'ಮೆಡಿಕೇರ್ ಪ್ರೋಗೆ ಸ್ವಾಗತ',
        'login': 'ಲಾಗಿನ್',
        'logout': 'ಲಾಗ್‌ಔಟ್',
        'dashboard': 'ಡ್ಯಾಶ್‌ಬೋರ್ಡ್',
        'home': 'ಮುಖಪುಟ',
        'profile': 'ಪ್ರೊಫೈಲ್',
        'settings': 'ಸೆಟ್ಟಿಂಗ್‌ಗಳು',
        'language': 'ಭಾಷೆ',
        
        # Main Modules
        'patients': 'ರೋಗಿಗಳು',
        'appointments': 'ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್‌ಗಳು',
        'enquiries': 'ವಿಚಾರಣೆಗಳು',
        'attendance': 'ಹಾಜರಾತಿ',
        'telemedicine': 'ಟೆಲಿಮೆಡಿಸಿನ್',
        'clinical': 'ಕ್ಲಿನಿಕಲ್',
        'pharmacy': 'ಫಾರ್ಮಸಿ',
        'billing': 'ಬಿಲ್ಲಿಂಗ್',
        'administration': 'ಆಡಳಿತ',
        'reports': 'ವರದಿಗಳು',

        'lab_orders': 'ಪ್ರಯೋಗಾಲಯ ಆದೇಶಗಳು',
        'imaging_orders': 'ಇಮೇಜಿಂಗ್ ಆದೇಶಗಳು',
        'admissions': 'ಪ್ರವೇಶಗಳು',
        'medical_records': 'ವೈದ್ಯಕೀಯ ದಾಖಲೆಗಳು',
        'prescriptions': 'ವೈದ್ಯರ ಚೀಟಿ',
        'lab_results': 'ಪ್ರಯೋಗಾಲಯ ಫಲಿತಾಂಶಗಳು',
        'imaging_results': 'ಇಮೇಜಿಂಗ್ ಫಲಿತಾಂಶಗಳು',

        'medicines': 'ಔಷಧಿಗಳು',
        'pharmacy_orders': 'ಫಾರ್ಮಸಿ ಆದೇಶಗಳು',
        'dispense_medicine': 'ಔಷಧಿ ವಿತರಿಸಿ',
        'stock_management': 'ಸ್ಟಾಕ್ ನಿರ್ವಹಣೆ',
        'low_stock_alert': 'ಕಡಿಮೆ ಸ್ಟಾಕ್ ಎಚ್ಚರಿಕೆ',

        'all_bills': 'ಎಲ್ಲಾ ಬಿಲ್‌ಗಳು',
        'create_bill': 'ಬಿಲ್ ರಚಿಸಿ',
        'payments': 'ಪಾವತಿಗಳು',
        'invoices': 'ಸರಕುಪಟ್ಟಿಗಳು',
        'insurance_claims': 'ವಿಮಾ ದಾವೆಗಳು',
        'bill_number': 'ಬಿಲ್ ಸಂಖ್ಯೆ',
        'total_amount': 'ಒಟ್ಟು ಮೊತ್ತ',
        'paid_amount': 'ಪಾವತಿಸಿದ ಮೊತ್ತ',
        'balance_amount': 'ಉಳಿದ ಮೊತ್ತ',
        'payment_status': 'ಪಾವತಿ ಸ್ಥಿತಿ',
        'pending': 'ಬಾಕಿ',
        'paid': 'ಪಾವತಿಸಲಾಗಿದೆ',
        'partial': 'ಭಾಗಶಃ',

        'staff_management': 'ಸಿಬ್ಬಂದಿ ನಿರ್ವಹಣೆ',
        'departments': 'ವಿಭಾಗಗಳು',
        'wards_beds': 'ವಾರ್ಡ್‌ಗಳು & ಹಾಸಿಗೆಗಳು',
        'services': 'ಸೇವೆಗಳು',
        'user_roles': 'ಬಳಕೆದಾರರ ಪಾತ್ರಗಳು',

        'active': 'ಸಕ್ರಿಯ',
        'inactive': 'ನಿಷ್ಕ್ರಿಯ',
        'enabled': 'ಸಕ್ರಿಯಗೊಳಿಸಲಾಗಿದೆ',
        'disabled': 'ನಿಷ್ಕ್ರಿಯಗೊಳಿಸಲಾಗಿದೆ',
        'available': 'ಲಭ್ಯವಿದೆ',
        'unavailable': 'ಲಭ್ಯವಿಲ್ಲ',
        'occupied': 'ಆಕ್ರಮಿಸಲಾಗಿದೆ',
        'vacant': 'ಖಾಲಿ',

        'today': 'ಇಂದು',
        'yesterday': 'ನಿನ್ನೆ',
        'tomorrow': 'ನಾಳೆ',
        'this_week': 'ಈ ವಾರ',
        'this_month': 'ಈ ತಿಂಗಳು',
        'date': 'ದಿನಾಂಕ',
        'time': 'ಸಮಯ',
        'duration': 'ಅವಧಿ',

        'required_field': 'ಅಗತ್ಯ ಕ್ಷೇತ್ರ',
        'optional': 'ಐಚ್ಛಿಕ',
        'select_option': 'ಆಯ್ಕೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ',
        'choose_file': 'ಫೈಲ್ ಆಯ್ಕೆಮಾಡಿ',
        'upload': 'ಅಪ್‌ಲೋಡ್ ಮಾಡಿ',
        'download': 'ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ',

        'total': 'ಒಟ್ಟು',
        'count': 'ಎಣಿಕೆ',
        'percentage': 'ಶೇಕಡಾವಾರು',
        'average': 'ಸರಾಸರಿ',
        'minimum': 'ಕನಿಷ್ಠ',
        'maximum': 'ಗರಿಷ್ಠ',
        'statistics': 'ಸಾಂಖ್ಯಿಕಗಳು',
        'analytics': 'ವಿಶ್ಲೇಷಣೆ',
        'all_appointments': 'ಎಲ್ಲಾ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್‌ಗಳು',
        'schedule_new': 'ಹೊಸ ವೇಳಾಪಟ್ಟಿ'
    }
}

def get_language():
    return session.get('language', 'en')

def get_text(key):
    lang = get_language()
    return LANGUAGES.get(lang, LANGUAGES['en']).get(key, key)

def generate_patient_id():
    """Generate unique patient ID"""
    count = WebPatient.query.count()
    return f'P{count + 1:06d}'

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = WebUser.query.filter(
            (WebUser.username == username)
        ).first()
        
        if user and check_password_hash(user.password_hash, password):
            # Check if 2FA is enabled and initialized
            if two_factor_auth and two_factor_auth.is_2fa_enabled(user.id):
                # Store user ID in session for 2FA verification
                session['2fa_user_id'] = user.id
                session['2fa_verified'] = False
                session['language'] = session.get('language', 'en')
                return redirect(url_for('verify_2fa'))
            else:
                login_user(user)
                user.last_login = datetime.utcnow()
                db.session.commit()
                session['language'] = session.get('language', 'en')
                
                # Log successful login if audit logger is available
                if audit_logger:
                    audit_logger.log_login_attempt(username, success=True)
                    audit_logger.log_user_activity('login', 'user', user.id)
                
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
        else:
            # Log failed login if audit logger is available
            if audit_logger:
                audit_logger.log_login_attempt(username, success=False, 
                                             failure_reason='Invalid credentials')
            flash('Invalid username or password!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    # Log logout if audit logger is available
    if audit_logger and current_user.is_authenticated:
        audit_logger.log_logout(current_user.username, session.get('session_id', ''))
        audit_logger.log_user_activity('logout', 'user', current_user.id)
    
    # Clear 2FA session data
    session.pop('2fa_verified', None)
    session.pop('2fa_user_id', None)
    session.pop('language', None)
    
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get dashboard statistics
    total_patients = WebPatient.query.count()
    today = datetime.now().date()
    
    # Today's statistics
    today_appointments = WebAppointment.query.filter(
        WebAppointment.appointment_date >= today,
        WebAppointment.appointment_date < today + timedelta(days=1)
    ).count()
    
    today_admissions = Admission.query.filter(
        Admission.admission_date >= today,
        Admission.status == 'admitted'
    ).count()
    
    pending_enquiries = WebEnquiry.query.filter_by(status='new').count()
    
    # Lab and imaging statistics
    pending_lab_orders = LabOrder.query.filter(LabOrder.status.in_(['ordered', 'collected'])).count()
    pending_imaging_orders = ImagingOrder.query.filter(ImagingOrder.status.in_(['ordered', 'scheduled'])).count()
    
    # Financial statistics
    today_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
        Payment.payment_date >= today
    ).scalar() or 0
    
    pending_bills = Bill.query.filter(Bill.payment_status.in_(['pending', 'partial'])).count()
    
    # Bed occupancy
    total_beds = Bed.query.filter_by(is_active=True).count()
    occupied_beds = Bed.query.filter_by(is_occupied=True).count()
    occupancy_rate = (occupied_beds / total_beds * 100) if total_beds > 0 else 0
    
    # Medicine alerts
    low_stock_medicines = Medicine.query.filter(
        Medicine.stock_quantity <= Medicine.min_stock_level,
        Medicine.is_active == True
    ).count()
    
    # Recent activities
    recent_patients = WebPatient.query.order_by(WebPatient.created_at.desc()).limit(5).all()
    upcoming_appointments = WebAppointment.query.filter(
        WebAppointment.appointment_date >= datetime.now()
    ).order_by(WebAppointment.appointment_date).limit(5).all()
    
    recent_admissions = Admission.query.filter_by(status='admitted').order_by(
        Admission.admission_date.desc()
    ).limit(5).all()
    
    # Critical alerts
    critical_lab_results = LabResult.query.filter_by(status='critical').count()
    
    return render_template('dashboard.html',
                         total_patients=total_patients,
                         today_appointments=today_appointments,
                         today_admissions=today_admissions,
                         pending_enquiries=pending_enquiries,
                         pending_lab_orders=pending_lab_orders,
                         pending_imaging_orders=pending_imaging_orders,
                         today_revenue=today_revenue,
                         pending_bills=pending_bills,
                         total_beds=total_beds,
                         occupied_beds=occupied_beds,
                         occupancy_rate=occupancy_rate,
                         low_stock_medicines=low_stock_medicines,
                         critical_lab_results=critical_lab_results,
                         recent_patients=recent_patients,
                         upcoming_appointments=upcoming_appointments,
                         recent_admissions=recent_admissions)

@app.route('/patients')
@login_required
def patients():
    page_str = request.args.get('page', '1')
    search = request.args.get('search', '')
    
    # Handle empty string for page parameter
    try:
        page = int(page_str) if page_str and page_str.strip() else 1
    except (ValueError, TypeError):
        page = 1
    
    query = WebPatient.query
    if search:
        query = query.filter(
            (WebPatient.first_name.contains(search)) |
            (WebPatient.last_name.contains(search)) |
            (WebPatient.patient_id.contains(search)) |
            (WebPatient.phone.contains(search))
        )
    
    patients = query.order_by(WebPatient.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('patients.html',
                         patients=patients,
                         search=search)

@app.route('/patient/add', methods=['GET', 'POST'])
@login_required
def add_patient():
    if request.method == 'POST':
        # Generate patient ID
        patient_id = generate_patient_id()
        
        patient = WebPatient(
            patient_id=patient_id,
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            email=request.form.get('email'),
            phone=request.form['phone'],
            date_of_birth=datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d').date() if request.form.get('date_of_birth') else None,
            gender=request.form.get('gender'),
            address=request.form.get('address'),
            emergency_contact=request.form.get('emergency_contact'),
            emergency_phone=request.form.get('emergency_phone'),
            blood_group=request.form.get('blood_group'),
            allergies=request.form.get('allergies'),
            medical_history=request.form.get('medical_history')
        )
        
        db.session.add(patient)
        db.session.commit()
        flash('Patient added successfully!', 'success')
        return redirect(url_for('patients'))
    
    return render_template('add_patient.html')

@app.route('/patient/edit/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def edit_patient(patient_id):
    patient = WebPatient.query.filter_by(id=patient_id).first_or_404()
    
    if request.method == 'POST':
        # Update patient information
        patient.first_name = request.form['first_name']
        patient.last_name = request.form['last_name']
        patient.email = request.form.get('email')
        patient.phone = request.form['phone']
        patient.date_of_birth = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d').date() if request.form.get('date_of_birth') else None
        patient.gender = request.form.get('gender')
        patient.address = request.form.get('address')
        patient.emergency_contact = request.form.get('emergency_contact')
        patient.emergency_phone = request.form.get('emergency_phone')
        patient.blood_group = request.form.get('blood_group')
        patient.allergies = request.form.get('allergies')
        patient.medical_history = request.form.get('medical_history')
        patient.city = request.form.get('city')
        patient.state = request.form.get('state')
        patient.zip_code = request.form.get('zip_code')
        patient.country = request.form.get('country')
        patient.emergency_relation = request.form.get('emergency_relation')
        patient.id_proof_type = request.form.get('id_proof_type')
        patient.id_proof_number = request.form.get('id_proof_number')
        patient.marital_status = request.form.get('marital_status')
        patient.occupation = request.form.get('occupation')
        patient.insurance_provider = request.form.get('insurance_provider')
        patient.insurance_number = request.form.get('insurance_number')
        patient.insurance_expiry = datetime.strptime(request.form['insurance_expiry'], '%Y-%m-%d').date() if request.form.get('insurance_expiry') else None
        
        patient.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Patient updated successfully!', 'success')
        return redirect(url_for('patients'))
    
    return render_template('edit_patient.html', patient=patient)

@app.route('/appointments')
@login_required
def appointments():
    page = request.args.get('page', 1, type=int)
    date_filter = request.args.get('date', '')
    status_filter = request.args.get('status', '')
    
    query = WebAppointment.query
    
    if date_filter:
        filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
        query = query.filter(WebAppointment.appointment_date >= filter_date,
                           WebAppointment.appointment_date < filter_date + timedelta(days=1))
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    appointments = query.order_by(WebAppointment.appointment_date.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('appointments.html',
                         appointments=appointments,
                         date_filter=date_filter,
                         status_filter=status_filter)

@app.route('/appointment/add', methods=['GET', 'POST'])
@login_required
def add_appointment():
    if request.method == 'POST':
        appointment = WebAppointment(
            patient_id=request.form['patient_id'],
            doctor_id=request.form['doctor_id'],
            appointment_date=datetime.strptime(request.form['appointment_datetime'], '%Y-%m-%dT%H:%M'),
            appointment_type=request.form['appointment_type'],
            notes=request.form.get('notes')
        )
        
        # Generate meeting link for telemedicine
        if appointment.appointment_type == 'telemedicine':
            appointment.meeting_link = f"https://meet.google.com/new"  # In production, integrate with Google Meet API
        
        db.session.add(appointment)
        db.session.commit()
        flash('Appointment scheduled successfully!', 'success')
        return redirect(url_for('appointments'))
    
    patients = WebPatient.query.all()
    doctors = WebUser.query.filter_by(role='doctor').all()
    min_datetime = datetime.now().strftime("%Y-%m-%dT%H:%M")
    
    return render_template('add_appointment.html',
                         patients=patients,
                         doctors=doctors, min_datetime=min_datetime)

@app.route('/enquiries')
@login_required
def enquiries():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = WebEnquiry.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    enquiries = query.order_by(WebEnquiry.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('enquiries.html',
                         enquiries=enquiries,
                         status_filter=status_filter)

@app.route('/captcha/generate')
def generate_captcha():
    """Generate CAPTCHA for enquiry form"""
    try:
        if advanced_security:
            captcha_data = advanced_security.generate_captcha()
            if captcha_data:
                return jsonify({
                    'success': True,
                    'captcha_id': captcha_data['challenge_id'],
                    'captcha_image': captcha_data['image']
                })
        
        # Fallback simple CAPTCHA if advanced_security not available
        import random
        import string
        captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        captcha_id = str(uuid.uuid4())
        
        # Store in session
        session[f'captcha_{captcha_id}'] = captcha_text
        
        # Create simple text-based captcha image
        from PIL import Image, ImageDraw, ImageFont
        import io
        import base64
        
        img = Image.new('RGB', (200, 80), color='white')
        d = ImageDraw.Draw(img)
        
        # Add noise
        for _ in range(100):
            x = random.randint(0, 200)
            y = random.randint(0, 80)
            d.point((x, y), fill='gray')
        
        # Draw text
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except:
            font = ImageFont.load_default()
        
        d.text((50, 20), captcha_text, fill='black', font=font)
        
        # Convert to base64
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        
        return jsonify({
            'success': True,
            'captcha_id': captcha_id,
            'captcha_image': f"data:image/png;base64,{img_base64}"
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/enquiry/submit', methods=['POST'])
def submit_enquiry():
    try:
        # Verify CAPTCHA
        captcha_id = request.form.get('captcha_id')
        captcha_input = request.form.get('captcha', '').upper()
        
        # Check CAPTCHA
        captcha_valid = False
        if advanced_security:
            captcha_valid = advanced_security.verify_captcha(captcha_id, captcha_input)
        else:
            # Fallback verification
            stored_captcha = session.get(f'captcha_{captcha_id}', '').upper()
            captcha_valid = (stored_captcha == captcha_input)
            if captcha_valid:
                session.pop(f'captcha_{captcha_id}', None)
        
        if not captcha_valid:
            return jsonify({'success': False, 'message': 'Invalid security code. Please try again.'}), 400
        
        # Create enquiry
        enquiry = WebEnquiry(
            name=request.form['name'],
            email=request.form['email'],
            phone=request.form['phone'],
            subject=request.form['subject'],
            message=request.form['message'],
            enquiry_type=request.form['enquiry_type']
        )
        
        db.session.add(enquiry)
        db.session.commit()
        
        # Log the action
        if audit_logger:
            audit_logger.log_user_activity(
                action='create',
                resource_type='enquiry',
                resource_id=enquiry.id,
                details={'name': enquiry.name, 'type': enquiry.enquiry_type}
            )
        
        return jsonify({'success': True, 'message': 'Enquiry submitted successfully!'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error submitting enquiry: {str(e)}'}), 500

@app.route('/attendance')
@login_required
def attendance():
    if current_user.role not in ['admin', 'hr']:
        flash('Access denied!', 'error')
        return redirect(url_for('dashboard'))
    
    date_filter = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
    
    # Get all staff and their attendance for the selected date
    staff = WebUser.query.filter(WebUser.role.in_(['doctor', 'nurse', 'staff'])).all()
    attendance_data = []
    
    for user in staff:
        attendance = WebAttendance.query.filter_by(
            user_id=user.id,
            date=filter_date
        ).first()
        
        attendance_data.append({
            'user': user,
            'attendance': attendance
        })
    
    return render_template('attendance.html',
                         attendance_data=attendance_data,
                         date_filter=date_filter)

@app.route('/attendance/mark', methods=['POST'])
@login_required
def mark_attendance():
    user_id = request.form['user_id']
    date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
    status = request.form['status']
    check_in = request.form.get('check_in')
    check_out = request.form.get('check_out')
    
    attendance = WebAttendance.query.filter_by(user_id=user_id, date=date).first()
    
    if not attendance:
        attendance = WebAttendance(user_id=user_id, date=date)
        db.session.add(attendance)
    
    attendance.status = status
    if check_in:
        attendance.check_in = datetime.strptime(f"{date} {check_in}", '%Y-%m-%d %H:%M')
    if check_out:
        attendance.check_out = datetime.strptime(f"{date} {check_out}", '%Y-%m-%d %H:%M')
    
    db.session.commit()
    flash('Attendance updated successfully!', 'success')
    return redirect(url_for('attendance'))

@app.route('/telemedicine')
@login_required
def telemedicine():
    # Get telemedicine appointments
    telemedicine_appointments = WebAppointment.query.filter_by(
        appointment_type='telemedicine'
    ).filter(
        WebAppointment.appointment_date >= datetime.now().date()
    ).order_by(WebAppointment.appointment_date).all()
    
    return render_template('telemedicine.html',
                         appointments=telemedicine_appointments)

# =============== EHR ROUTES ===============
@app.route('/ehr/<int:patient_id>')
@login_required
@role_required('admin', 'doctor', 'nurse')
def patient_ehr(patient_id):
    patient = WebPatient.query.get_or_404(patient_id)
    medical_records = MedicalRecord.query.filter_by(patient_id=patient_id).order_by(MedicalRecord.visit_date.desc()).all()
    prescriptions = Prescription.query.filter_by(patient_id=patient_id).order_by(Prescription.prescription_date.desc()).all()
    lab_orders = LabOrder.query.filter_by(patient_id=patient_id).order_by(LabOrder.order_date.desc()).all()
    imaging_orders = ImagingOrder.query.filter_by(patient_id=patient_id).order_by(ImagingOrder.order_date.desc()).all()
    
    return render_template('ehr.html', 
                         patient=patient,
                         medical_records=medical_records,
                         prescriptions=prescriptions,
                         lab_orders=lab_orders,
                         imaging_orders=imaging_orders)

@app.route('/ehr/add_record/<int:patient_id>', methods=['GET', 'POST'])
@login_required
@role_required('doctor')
def add_medical_record(patient_id):
    if request.method == 'POST':
        record = MedicalRecord(
            patient_id=patient_id,
            doctor_id=current_user.id,
            visit_date=datetime.now(),
            chief_complaint=request.form['chief_complaint'],
            diagnosis=request.form['diagnosis'],
            treatment_plan=request.form['treatment_plan'],
            notes=request.form['notes'],
            vital_signs=request.form.get('vital_signs')
        )
        db.session.add(record)
        db.session.commit()
        flash('Medical record added successfully!', 'success')
        return redirect(url_for('patient_ehr', patient_id=patient_id))
    
    patient = WebPatient.query.get_or_404(patient_id)
    return render_template('add_medical_record.html', patient=patient)

# =============== LABORATORY ROUTES ===============
@app.route('/lab/tests')
@login_required
@role_required('admin', 'lab_tech', 'doctor')
def lab_tests():
    tests = LabTest.query.filter_by(is_active=True).all()
    return render_template('lab_tests.html', tests=tests)

@app.route('/lab/orders')
@login_required
@role_required('admin', 'lab_tech', 'doctor')
def lab_orders():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = LabOrder.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    orders = query.order_by(LabOrder.order_date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('lab_orders.html', orders=orders, status_filter=status_filter)

@app.route('/lab/order/add', methods=['GET', 'POST'])
@login_required
@role_required('doctor')
def add_lab_order():
    if request.method == 'POST':
        order = LabOrder(
            patient_id=request.form['patient_id'],
            doctor_id=current_user.id,
            test_id=request.form['test_id'],
            priority=request.form.get('priority', 'normal'),
            notes=request.form.get('notes')
        )
        db.session.add(order)
        db.session.commit()
        flash('Lab test ordered successfully!', 'success')
        return redirect(url_for('lab_orders'))
    
    patients = WebPatient.query.all()
    tests = LabTest.query.filter_by(is_active=True).all()
    return render_template('add_lab_order.html', patients=patients, tests=tests)

@app.route('/lab/result/add/<int:order_id>', methods=['GET', 'POST'])
@login_required
@role_required('lab_tech')
def add_lab_result(order_id):
    order = LabOrder.query.get_or_404(order_id)
    
    if request.method == 'POST':
        result = LabResult(
            lab_order_id=order_id,
            technician_id=current_user.id,
            result_value=request.form['result_value'],
            result_unit=request.form.get('result_unit'),
            reference_range=request.form.get('reference_range'),
            status=request.form['status'],
            comments=request.form.get('comments')
        )
        
        # Update order status
        order.status = 'completed'
        order.result_date = datetime.now()
        
        db.session.add(result)
        db.session.commit()
        flash('Lab result added successfully!', 'success')
        return redirect(url_for('lab_orders'))
    
    return render_template('add_lab_result.html', order=order)

# =============== IMAGING/RADIOLOGY ROUTES ===============
@app.route('/imaging/tests')
@login_required
@role_required('admin', 'doctor')
def imaging_tests():
    tests = ImagingTest.query.filter_by(is_active=True).all()
    return render_template('imaging_tests.html', tests=tests)

@app.route('/imaging/orders')
@login_required
@role_required('admin', 'doctor', 'radiologist')
def imaging_orders():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = ImagingOrder.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    orders = query.order_by(ImagingOrder.order_date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('imaging_orders.html', orders=orders, status_filter=status_filter)

@app.route('/imaging/order/add', methods=['GET', 'POST'])
@login_required
@role_required('doctor')
def add_imaging_order():
    if request.method == 'POST':
        order = ImagingOrder(
            patient_id=request.form['patient_id'],
            doctor_id=current_user.id,
            test_id=request.form['test_id'],
            scheduled_date=datetime.strptime(request.form['scheduled_date'], '%Y-%m-%dT%H:%M') if request.form.get('scheduled_date') else None,
            priority=request.form.get('priority', 'normal'),
            clinical_notes=request.form.get('clinical_notes')
        )
        db.session.add(order)
        db.session.commit()
        flash('Imaging test ordered successfully!', 'success')
        return redirect(url_for('imaging_orders'))
    
    patients = WebPatient.query.all()
    tests = ImagingTest.query.filter_by(is_active=True).all()
    return render_template('add_imaging_order.html', patients=patients, tests=tests)

# =============== PHARMACY ROUTES ===============
@app.route('/pharmacy/medicines')
@login_required
@role_required('admin', 'pharmacist')
def pharmacy_medicines():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Medicine.query.filter_by(is_active=True)
    if search:
        query = query.filter(
            (Medicine.name.contains(search)) |
            (Medicine.generic_name.contains(search)) |
            (Medicine.brand_name.contains(search))
        )
    
    medicines = query.paginate(page=page, per_page=20, error_out=False)
    return render_template('pharmacy_medicines.html', medicines=medicines, search=search)

@app.route('/pharmacy/orders')
@login_required
@role_required('admin', 'pharmacist')
def pharmacy_orders():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = PharmacyOrder.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    orders = query.order_by(PharmacyOrder.order_date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('pharmacy_orders.html', orders=orders, status_filter=status_filter)

@app.route('/pharmacy/dispense/<int:prescription_id>', methods=['GET', 'POST'])
@login_required
@role_required('pharmacist')
def dispense_medicine(prescription_id):
    prescription = Prescription.query.get_or_404(prescription_id)
    
    if request.method == 'POST':
        # Create pharmacy order
        order = PharmacyOrder(
            patient_id=prescription.patient_id,
            prescription_id=prescription_id,
            pharmacist_id=current_user.id,
            total_amount=float(request.form['total_amount']),
            discount=float(request.form.get('discount', 0)),
            tax_amount=float(request.form.get('tax_amount', 0)),
            final_amount=float(request.form['final_amount']),
            status='dispensed'
        )
        
        db.session.add(order)
        db.session.flush()  # Get the order ID
        
        # Add order items
        medicine_ids = request.form.getlist('medicine_id')
        quantities = request.form.getlist('quantity')
        unit_prices = request.form.getlist('unit_price')
        
        for i, medicine_id in enumerate(medicine_ids):
            if medicine_id:
                item = PharmacyOrderItem(
                    pharmacy_order_id=order.id,
                    medicine_id=int(medicine_id),
                    quantity=int(quantities[i]),
                    unit_price=float(unit_prices[i]),
                    total_price=int(quantities[i]) * float(unit_prices[i])
                )
                db.session.add(item)
                
                # Update medicine stock
                medicine = db.session.get(Medicine, medicine_id)
                medicine.stock_quantity -= int(quantities[i])
        
        prescription.status = 'completed'
        db.session.commit()
        flash('Medicine dispensed successfully!', 'success')
        return redirect(url_for('pharmacy_orders'))
    
    medicines = Medicine.query.filter_by(is_active=True).all()
    return render_template('dispense_medicine.html', prescription=prescription, medicines=medicines)

# =============== ADMISSION/IPD ROUTES ===============
@app.route('/admissions')
@login_required
@role_required('admin', 'doctor', 'nurse')
def admissions():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = Admission.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    admissions = query.order_by(Admission.admission_date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admissions.html', admissions=admissions, status_filter=status_filter)

@app.route('/admission/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'doctor')
def add_admission():
    if request.method == 'POST':
        # Find available bed
        bed = Bed.query.filter_by(id=request.form['bed_id'], is_occupied=False).first()
        if not bed:
            flash('Selected bed is not available!', 'error')
            return redirect(url_for('add_admission'))
        
        admission = Admission(
            patient_id=request.form['patient_id'],
            doctor_id=request.form['doctor_id'],
            bed_id=bed.id,
            admission_type=request.form['admission_type'],
            reason=request.form['reason'],
            diagnosis=request.form.get('diagnosis')
        )
        
        # Mark bed as occupied
        bed.is_occupied = True
        
        # Update ward availability
        ward = bed.ward
        ward.available_beds -= 1
        
        db.session.add(admission)
        db.session.commit()
        flash('Patient admitted successfully!', 'success')
        return redirect(url_for('admissions'))
    
    patients = WebPatient.query.all()
    doctors = WebUser.query.filter_by(role='doctor').all()
    available_beds = Bed.query.filter_by(is_occupied=False, is_active=True).all()
    
    return render_template('add_admission.html', 
                         patients=patients, 
                         doctors=doctors, 
                         available_beds=available_beds)

@app.route('/admission/discharge/<int:admission_id>', methods=['GET', 'POST'])
@login_required
@role_required('doctor')
def discharge_patient(admission_id):
    admission = Admission.query.get_or_404(admission_id)
    
    if request.method == 'POST':
        admission.discharge_date = datetime.now()
        admission.status = 'discharged'
        admission.discharge_summary = request.form['discharge_summary']
        admission.total_charges = float(request.form.get('total_charges', 0))
        
        # Free up the bed
        bed = admission.bed
        bed.is_occupied = False
        
        # Update ward availability
        ward = bed.ward
        ward.available_beds += 1
        
        db.session.commit()
        flash('Patient discharged successfully!', 'success')
        return redirect(url_for('admissions'))
    
    return render_template('discharge_patient.html', admission=admission)

# =============== BILLING ROUTES ===============
@app.route('/billing')
@login_required
@role_required('admin', 'receptionist', 'accountant')
def billing():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = Bill.query
    if status_filter:
        query = query.filter_by(payment_status=status_filter)
    
    bills = query.order_by(Bill.bill_date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('billing.html', bills=bills, status_filter=status_filter)

@app.route('/bill/create', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'receptionist', 'accountant')
def create_bill():
    if request.method == 'POST':
        # Generate bill number
        bill_number = f"BILL{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"
        
        bill = Bill(
            bill_number=bill_number,
            patient_id=request.form['patient_id'],
            bill_type=request.form['bill_type'],
            subtotal=float(request.form['subtotal']),
            discount=float(request.form.get('discount', 0)),
            tax_amount=float(request.form.get('tax_amount', 0)),
            total_amount=float(request.form['total_amount']),
            created_by=current_user.id
        )
        
        bill.balance_amount = bill.total_amount
        
        db.session.add(bill)
        db.session.flush()  # Get bill ID
        
        # Add bill items
        service_names = request.form.getlist('service_name')
        quantities = request.form.getlist('quantity')
        unit_prices = request.form.getlist('unit_price')
        
        for i, service_name in enumerate(service_names):
            if service_name:
                item = BillItem(
                    bill_id=bill.id,
                    service_name=service_name,
                    quantity=int(quantities[i]),
                    unit_price=float(unit_prices[i]),
                    total_price=int(quantities[i]) * float(unit_prices[i])
                )
                db.session.add(item)
        
        db.session.commit()
        flash('Bill created successfully!', 'success')
        return redirect(url_for('billing'))
    
    patients = WebPatient.query.all()
    services = Service.query.filter_by(is_active=True).all()
    return render_template('create_bill.html', patients=patients, services=services)

@app.route('/payment/add/<int:bill_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'receptionist', 'accountant')
def add_payment(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    
    if request.method == 'POST':
        amount = float(request.form['amount'])
        
        payment = Payment(
            bill_id=bill_id,
            amount=amount,
            payment_method=request.form['payment_method'],
            transaction_id=request.form.get('transaction_id'),
            notes=request.form.get('notes'),
            received_by=current_user.id
        )
        
        # Update bill payment status
        bill.paid_amount += amount
        bill.balance_amount = bill.total_amount - bill.paid_amount
        
        if bill.balance_amount <= 0:
            bill.payment_status = 'paid'
        elif bill.paid_amount > 0:
            bill.payment_status = 'partial'
        
        db.session.add(payment)
        db.session.commit()
        flash('Payment recorded successfully!', 'success')
        return redirect(url_for('billing'))
    
    return render_template('add_payment.html', bill=bill)

# =============== STAFF MANAGEMENT ROUTES ===============
@app.route('/staff')
@login_required
@role_required('admin', 'hr')
def staff_management():
    page = request.args.get('page', 1, type=int)
    role_filter = request.args.get('role', '')
    
    query = WebUser.query
    if role_filter:
        query = query.filter_by(role=role_filter)
    
    staff = query.order_by(WebUser.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('staff_management.html', staff=staff, role_filter=role_filter)

@app.route('/staff/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'hr')
def add_staff():
    if request.method == 'POST':
        # Generate employee ID
        last_user = WebUser.query.order_by(WebUser.id.desc()).first()
        employee_id = f"EMP{(last_user.id + 1):06d}" if last_user else "EMP000001"
        
        user = WebUser(
            username=request.form['username'],
            email=request.form['email'],
            password_hash=generate_password_hash(request.form['password']),
            full_name=request.form['full_name'],
            role=request.form['role'],
            department=request.form.get('department'),
            phone=request.form.get('phone'),
            employee_id=employee_id,
            specialization=request.form.get('specialization'),
            license_number=request.form.get('license_number'),
            salary=float(request.form['salary']) if request.form.get('salary') else None,
            hire_date=datetime.strptime(request.form['hire_date'], '%Y-%m-%d').date() if request.form.get('hire_date') else None
        )
        
        db.session.add(user)
        db.session.commit()
        flash('Staff member added successfully!', 'success')
        return redirect(url_for('staff_management'))
    
    departments = Department.query.filter_by(is_active=True).all()
    return render_template('add_staff.html', departments=departments)

# =============== REPORTS & ANALYTICS ROUTES ===============
@app.route('/reports')
@login_required
@role_required('admin', 'doctor', 'accountant')
def reports():
    try:
        # Daily statistics
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        today_patients = WebPatient.query.filter(
            WebPatient.created_at >= today_start
        ).count()
        
        today_appointments = WebAppointment.query.filter(
            WebAppointment.appointment_date >= today_start,
            WebAppointment.appointment_date <= today_end
        ).count()
        
        today_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
            Payment.payment_date >= today_start
        ).scalar() or 0
        
        # Monthly statistics
        month_start = today.replace(day=1)
        month_start_dt = datetime.combine(month_start, datetime.min.time())
        
        monthly_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
            Payment.payment_date >= month_start_dt
        ).scalar() or 0
        
        # Bed occupancy
        total_beds = Bed.query.filter_by(is_active=True).count()
        occupied_beds = Bed.query.filter_by(is_occupied=True).count()
        occupancy_rate = (occupied_beds / total_beds * 100) if total_beds > 0 else 0
        
        return render_template('reports.html',
                             today_patients=today_patients,
                             today_appointments=today_appointments,
                             today_revenue=float(today_revenue),
                             monthly_revenue=float(monthly_revenue),
                             occupancy_rate=occupancy_rate,
                             total_beds=total_beds,
                             occupied_beds=occupied_beds)
    except Exception as e:
        flash(f'Error loading reports: {str(e)}', 'danger')
        return render_template('reports.html',
                             today_patients=0,
                             today_appointments=0,
                             today_revenue=0.0,
                             monthly_revenue=0.0,
                             occupancy_rate=0.0,
                             total_beds=0,
                             occupied_beds=0)

# =============== ADMIN CONFIGURATION ROUTES ===============
@app.route('/admin/departments')
@login_required
@role_required('admin')
def manage_departments():
    departments = Department.query.all()
    return render_template('manage_departments.html', departments=departments)

@app.route('/admin/services')
@login_required
@role_required('admin')
def manage_services():
    services = Service.query.all()
    return render_template('manage_services.html', services=services)

@app.route('/admin/wards')
@login_required
@role_required('admin')
def manage_wards():
    wards = Ward.query.all()
    return render_template('manage_wards.html', wards=wards)

# =============== PATIENT CHECK-IN/CHECK-OUT ROUTES ===============
@app.route('/checkin')
@login_required
@role_required('admin', 'receptionist', 'nurse')
def patient_checkin():
    today = datetime.now().date()
    
    # Get today's appointments
    appointments = WebAppointment.query.filter(
        WebAppointment.appointment_date >= today,
        WebAppointment.appointment_date < today + timedelta(days=1),
        WebAppointment.status.in_(['scheduled', 'checked_in'])
    ).order_by(WebAppointment.appointment_date).all()
    
    return render_template('patient_checkin.html', appointments=appointments)

@app.route('/checkin/<int:appointment_id>', methods=['POST'])
@login_required
@role_required('admin', 'receptionist', 'nurse')
def check_in_patient(appointment_id):
    appointment = WebAppointment.query.get_or_404(appointment_id)
    appointment.status = 'checked_in'
    appointment.check_in_time = datetime.now()
    
    db.session.commit()
    flash(f'Patient {appointment.patient.first_name} {appointment.patient.last_name} checked in successfully!', 'success')
    return redirect(url_for('patient_checkin'))

@app.route('/doctor/queue')
@login_required
@role_required('doctor')
def doctor_queue():
    # Get checked-in patients for current doctor
    checked_in_appointments = WebAppointment.query.filter(
        WebAppointment.doctor_id == current_user.id,
        WebAppointment.status == 'checked_in'
    ).order_by(WebAppointment.check_in_time).all()
    
    return render_template('doctor_queue.html', appointments=checked_in_appointments)

@app.route('/consultation/<int:appointment_id>')
@login_required
@role_required('doctor')
def start_consultation(appointment_id):
    appointment = WebAppointment.query.get_or_404(appointment_id)
    
    # Update appointment status
    appointment.status = 'in_consultation'
    appointment.consultation_start = datetime.now()
    db.session.commit()
    
    # Redirect to patient EHR
    return redirect(url_for('patient_ehr', patient_id=appointment.patient_id))

@app.route('/complete_consultation/<int:appointment_id>', methods=['POST'])
@login_required
@role_required('doctor')
def complete_consultation(appointment_id):
    appointment = WebAppointment.query.get_or_404(appointment_id)
    appointment.status = 'completed'
    appointment.consultation_end = datetime.now()
    
    db.session.commit()
    flash('Consultation completed successfully!', 'success')
    return redirect(url_for('doctor_queue'))

# =============== INVOICE GENERATION ROUTES ===============
@app.route('/invoice/<int:bill_id>')
@login_required
def view_invoice(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    return render_template('invoice.html', bill=bill)

@app.route('/invoice/<int:bill_id>/print')
@login_required
def print_invoice(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    return render_template('invoice_print.html', bill=bill)

@app.route('/invoice/<int:bill_id>/email', methods=['POST'])
@login_required
def email_invoice(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    
    # In a real implementation, this would send email
    # For now, we'll just return success
    return jsonify({
        'success': True, 
        'message': f'Invoice emailed to {bill.patient.email}'
    })

# =============== PRESCRIPTION WORKFLOW ROUTES ===============
@app.route('/prescription/create/<int:patient_id>', methods=['GET', 'POST'])
@login_required
@role_required('doctor')
def create_prescription(patient_id):
    patient = WebPatient.query.get_or_404(patient_id)
    
    if request.method == 'POST':
        # Create prescription
        prescription = Prescription(
            patient_id=patient_id,
            doctor_id=current_user.id,
            medications=request.form['medications'],
            instructions=request.form['instructions']
        )
        
        db.session.add(prescription)
        db.session.commit()
        
        flash('Prescription created successfully!', 'success')
        return redirect(url_for('patient_ehr', patient_id=patient_id))
    
    medicines = Medicine.query.filter_by(is_active=True).all()
    return render_template('create_prescription.html', patient=patient, medicines=medicines)

# =============== FOLLOW-UP REMINDERS ===============
@app.route('/followup/schedule/<int:patient_id>', methods=['POST'])
@login_required
@role_required('doctor', 'nurse')
def schedule_followup(patient_id):
    patient = WebPatient.query.get_or_404(patient_id)
    
    followup_date = datetime.strptime(request.form['followup_date'], '%Y-%m-%d')
    doctor_id = request.form.get('doctor_id', current_user.id)
    
    # Create follow-up appointment
    appointment = WebAppointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        appointment_date=followup_date,
        appointment_type='follow-up',
        notes=f'Follow-up appointment scheduled by {current_user.full_name}'
    )
    
    db.session.add(appointment)
    db.session.commit()
    
    flash('Follow-up appointment scheduled successfully!', 'success')
    return redirect(url_for('patient_ehr', patient_id=patient_id))

# =============== PATIENT PORTAL ROUTES ===============
@app.route('/patient/portal/<patient_id>')
def patient_portal(patient_id):
    patient = WebPatient.query.filter_by(patient_id=patient_id).first_or_404()
    
    # Get patient's data
    appointments = WebAppointment.query.filter_by(patient_id=patient.id).order_by(
        WebAppointment.appointment_date.desc()
    ).limit(10).all()
    
    lab_orders = LabOrder.query.filter_by(patient_id=patient.id).order_by(
        LabOrder.order_date.desc()
    ).limit(10).all()
    
    bills = Bill.query.filter_by(patient_id=patient.id).order_by(
        Bill.bill_date.desc()
    ).limit(10).all()
    
    return render_template('patient_portal.html', 
                         patient=patient,
                         appointments=appointments,
                         lab_orders=lab_orders,
                         bills=bills)

@app.route('/api/sync-offline', methods=['POST'])
@login_required
def sync_offline_data():
    """API endpoint for offline data synchronization"""
    try:
        data = request.get_json()
        
        # Process offline data based on type
        if data.get('type') == 'patient':
            # Sync patient data
            for patient_data in data.get('patients', []):
                existing_patient = WebPatient.query.filter_by(
                    patient_id=patient_data['patient_id']
                ).first()
                
                if not existing_patient:
                    patient = WebPatient(**patient_data)
                    db.session.add(patient)
        
        elif data.get('type') == 'appointment':
            # Sync appointment data
            for appointment_data in data.get('appointments', []):
                appointment = WebAppointment(**appointment_data)
                db.session.add(appointment)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Data synchronized successfully'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/set-language/<language>')
def set_language(language):
    if language in LANGUAGES:
        session['language'] = language
    return redirect(request.referrer or url_for('index'))

# Settings helper functions
def get_all_settings():
    """Get all settings from database as a dictionary"""
    settings = {}
    try:
        for setting in HospitalSetting.query.all():
            # Convert setting value based on type
            if setting.setting_type == 'number':
                try:
                    settings[setting.setting_key] = float(setting.setting_value)
                except (ValueError, TypeError):
                    settings[setting.setting_key] = 0.0
            elif setting.setting_type == 'boolean':
                settings[setting.setting_key] = setting.setting_value.lower() in ('true', '1', 'yes')
            else:
                settings[setting.setting_key] = setting.setting_value
    except Exception as e:
        # If table doesn't exist or query fails, return default settings
        print(f"Warning: Could not load settings from database: {e}")
        settings = {
            'hospital_name': 'MediCare Pro',
            'hospital_tagline': 'Your Health, Our Priority',
            'primary_color': '#0d6efd',
            'secondary_color': '#6c757d',
            'currency': 'USD',
            'password_min_length': 8,
            'password_expiry_days': 90,
            'default_language': 'en',
            'enable_multilingual': False,
        }
    
    # Ensure we always have default values for required settings
    default_values = {
        'hospital_name': 'MediCare Pro',
        'hospital_tagline': 'Your Health, Our Priority',
        'primary_color': '#0d6efd',
        'secondary_color': '#6c757d',
        'currency': 'USD',
        'password_min_length': 8,
        'password_expiry_days': 90,
        'default_language': 'en',
        'enable_multilingual': False,
    }
    
    for key, default_value in default_values.items():
        if key not in settings:
            settings[key] = default_value
    
    return settings

def update_setting(key, value, setting_type='string', category='general', description=''):
    """Update or create a setting"""
    setting = HospitalSetting.query.filter_by(setting_key=key).first()
    if setting:
        setting.setting_value = str(value)
        setting.setting_type = setting_type
        setting.category = category
        setting.description = description
        setting.updated_at = datetime.utcnow()
    else:
        setting = HospitalSetting(
            setting_key=key,
            setting_value=str(value),
            setting_type=setting_type,
            category=category,
            description=description
        )
        db.session.add(setting)
    return setting

def save_uploaded_file(file, upload_dir):
    """Save uploaded file and return the path"""
    if file and file.filename:
        filename = secure_filename(file.filename)
        # Create unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{filename}"
        
        # Ensure upload directory exists
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        return file_path
    return None

# Settings save functions for each category
def save_organization_settings(form_data, files):
    """Save organization-related settings"""
    # Hospital name and branding
    update_setting('hospital_name', form_data.get('hospital_name', 'MediCare Pro'), 'string', 'organization')
    update_setting('hospital_tagline', form_data.get('hospital_tagline', 'Your Health, Our Priority'), 'string', 'organization')
    
    # Handle logo and favicon uploads
    if 'logo' in files and files['logo'].filename:
        logo_path = save_uploaded_file(files['logo'], 'static/uploads')
        if logo_path:
            update_setting('hospital_logo', logo_path, 'string', 'organization')
    
    if 'favicon' in files and files['favicon'].filename:
        favicon_path = save_uploaded_file(files['favicon'], 'static/uploads')
        if favicon_path:
            update_setting('hospital_favicon', favicon_path, 'string', 'organization')
    
    # Theme settings
    update_setting('primary_color', form_data.get('primary_color', '#0d6efd'), 'string', 'organization')
    update_setting('secondary_color', form_data.get('secondary_color', '#6c757d'), 'string', 'organization')
    
    # Domain mapping
    update_setting('custom_domain', form_data.get('custom_domain', ''), 'string', 'organization')
    
    # Login page content
    update_setting('login_welcome_text', form_data.get('login_welcome_text', 'Welcome to MediCare Pro'), 'string', 'organization')
    update_setting('login_hero_image', form_data.get('login_hero_image', ''), 'string', 'organization')
    update_setting('login_help_links', form_data.get('login_help_links', ''), 'string', 'organization')
    
    # Email/SMS settings
    update_setting('email_from_address', form_data.get('email_from_address', 'noreply@hospital.com'), 'string', 'organization')
    update_setting('sms_sender_id', form_data.get('sms_sender_id', 'MEDICAR'), 'string', 'organization')
    
    # Multi-branch management
    branches = form_data.getlist('branch_name')
    for i, branch_name in enumerate(branches):
        if branch_name.strip():
            branch_code = form_data.getlist('branch_code')[i] if i < len(form_data.getlist('branch_code')) else ''
            branch_id = form_data.getlist('branch_id')[i] if i < len(form_data.getlist('branch_id')) else ''
            
            if branch_id and branch_id.isdigit():
                # Update existing branch
                branch = HospitalBranch.query.get(int(branch_id))
                if branch:
                    branch.name = branch_name
                    branch.code = branch_code
                    branch.address = form_data.getlist('branch_address')[i] if i < len(form_data.getlist('branch_address')) else ''
                    branch.city = form_data.getlist('branch_city')[i] if i < len(form_data.getlist('branch_city')) else ''
                    branch.state = form_data.getlist('branch_state')[i] if i < len(form_data.getlist('branch_state')) else ''
                    branch.zip_code = form_data.getlist('branch_zip_code')[i] if i < len(form_data.getlist('branch_zip_code')) else ''
                    branch.country = form_data.getlist('branch_country')[i] if i < len(form_data.getlist('branch_country')) else ''
                    branch.phone = form_data.getlist('branch_phone')[i] if i < len(form_data.getlist('branch_phone')) else ''
                    branch.email = form_data.getlist('branch_email')[i] if i < len(form_data.getlist('branch_email')) else ''
                    branch.domain = form_data.getlist('branch_domain')[i] if i < len(form_data.getlist('branch_domain')) else ''
            else:
                # Add new branch
                branch = HospitalBranch(
                    name=branch_name,
                    code=branch_code or f"BR{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    address=form_data.getlist('branch_address')[i] if i < len(form_data.getlist('branch_address')) else '',
                    city=form_data.getlist('branch_city')[i] if i < len(form_data.getlist('branch_city')) else '',
                    state=form_data.getlist('branch_state')[i] if i < len(form_data.getlist('branch_state')) else '',
                    zip_code=form_data.getlist('branch_zip_code')[i] if i < len(form_data.getlist('branch_zip_code')) else '',
                    country=form_data.getlist('branch_country')[i] if i < len(form_data.getlist('branch_country')) else '',
                    phone=form_data.getlist('branch_phone')[i] if i < len(form_data.getlist('branch_phone')) else '',
                    email=form_data.getlist('branch_email')[i] if i < len(form_data.getlist('branch_email')) else '',
                    domain=form_data.getlist('branch_domain')[i] if i < len(form_data.getlist('branch_domain')) else ''
                )
                db.session.add(branch)
    
    # Language settings
    update_setting('default_language', form_data.get('default_language', 'en'), 'string', 'organization')
    update_setting('enable_multilingual', 'enable_multilingual' in form_data, 'boolean', 'organization')
    
    # Custom CSS
    update_setting('custom_css', form_data.get('custom_css', ''), 'string', 'organization')

def save_security_settings(form_data, files=None):
    """Save security-related settings"""
    # Password policy
    update_setting('password_min_length', form_data.get('password_min_length', '8'), 'number', 'security')
    update_setting('password_require_uppercase', 'password_require_uppercase' in form_data, 'boolean', 'security')
    update_setting('password_require_lowercase', 'password_require_lowercase' in form_data, 'boolean', 'security')
    update_setting('password_require_numbers', 'password_require_numbers' in form_data, 'boolean', 'security')
    update_setting('password_require_special', 'password_require_special' in form_data, 'boolean', 'security')
    update_setting('password_expiry_days', form_data.get('password_expiry_days', '90'), 'number', 'security')
    
    # 2FA settings
    update_setting('enable_2fa', 'enable_2fa' in form_data, 'boolean', 'security')
    update_setting('require_2fa_admins', 'require_2fa_admins' in form_data, 'boolean', 'security')
    update_setting('require_2fa_doctors', 'require_2fa_doctors' in form_data, 'boolean', 'security')
    
    # Session settings
    update_setting('session_timeout_minutes', form_data.get('session_timeout_minutes', '30'), 'number', 'security')
    update_setting('auto_logout_enabled', 'auto_logout_enabled' in form_data, 'boolean', 'security')
    
    # Audit logs
    update_setting('extended_audit_logging', 'extended_audit_logging' in form_data, 'boolean', 'security')
    update_setting('audit_log_retention_days', form_data.get('audit_log_retention_days', '365'), 'number', 'security')
    
    # IP restrictions
    update_setting('enable_ip_restrictions', 'enable_ip_restrictions' in form_data, 'boolean', 'security')
    update_setting('allowed_ip_ranges', form_data.get('allowed_ip_ranges', ''), 'string', 'security')
    update_setting('blocked_ip_ranges', form_data.get('blocked_ip_ranges', ''), 'string', 'security')
    
    # Role/Permission templates
    template_names = form_data.getlist('template_name')
    template_roles = form_data.getlist('template_base_role')
    template_ids = form_data.getlist('template_id')
    
    for i, name in enumerate(template_names):
        if name.strip():
            template_id = template_ids[i] if i < len(template_ids) else ''
            
            if template_id and template_id.isdigit():
                # Update existing template
                template = UserRoleTemplate.query.get(int(template_id))
                if template:
                    template.name = name
                    template.base_role = template_roles[i] if i < len(template_roles) else 'staff'
                    template.description = form_data.getlist('template_description')[i] if i < len(form_data.getlist('template_description')) else ''
                    # Update permissions - convert checkbox data to JSON
                    permissions = {}
                    for key in form_data.keys():
                        if key.startswith(f'permission_{template_id}_'):
                            perm_key = key.replace(f'permission_{template_id}_', '')
                            permissions[perm_key] = True
                    template.permissions = json.dumps(permissions)
            else:
                # Add new template
                template = UserRoleTemplate(
                    name=name,
                    base_role=form_data.getlist('template_base_role')[i] if i < len(form_data.getlist('template_base_role')) else 'staff',
                    description=form_data.getlist('template_description')[i] if i < len(form_data.getlist('template_description')) else '',
                    permissions=json.dumps({})  # Initialize with empty permissions
                )
                db.session.add(template)

def save_clinical_settings(form_data, files=None):
    """Save clinical-related settings"""
    # Patient ID format
    update_setting('patient_id_prefix', form_data.get('patient_id_prefix', 'P'), 'string', 'clinical')
    update_setting('patient_id_length', form_data.get('patient_id_length', '6'), 'number', 'clinical')
    update_setting('patient_id_numbering', form_data.get('patient_id_numbering', 'sequential'), 'string', 'clinical')
    
    # Appointment settings
    update_setting('default_slot_length_minutes', form_data.get('default_slot_length_minutes', '15'), 'number', 'clinical')
    update_setting('appointment_buffer_minutes', form_data.get('appointment_buffer_minutes', '5'), 'number', 'clinical')
    update_setting('enable_online_booking', 'enable_online_booking' in form_data, 'boolean', 'clinical')
    
    # Consent forms
    if files and 'consent_form' in files and files['consent_form'].filename:
        consent_path = save_uploaded_file(files['consent_form'], 'uploads/templates')
        if consent_path:
            consent_form = ConsentForm(
                name=form_data.get('consent_form_name', 'General Consent'),
                form_type=form_data.get('consent_form_type', 'treatment'),
                description=form_data.get('consent_form_description', ''),
                file_path=consent_path,
                is_required='consent_form_required' in form_data
            )
            db.session.add(consent_form)
    
    # Default billing items
    update_setting('default_consultation_fee', form_data.get('default_consultation_fee', '50'), 'number', 'clinical')
    update_setting('default_lab_panel_price', form_data.get('default_lab_panel_price', '25'), 'number', 'clinical')
    update_setting('default_imaging_price', form_data.get('default_imaging_price', '100'), 'number', 'clinical')
    update_setting('default_procedure_price', form_data.get('default_procedure_price', '200'), 'number', 'clinical')
    update_setting('default_emergency_fee', form_data.get('default_emergency_fee', '150'), 'number', 'clinical')
    update_setting('default_followup_fee', form_data.get('default_followup_fee', '30'), 'number', 'clinical')
    
    # Default services
    service_names = form_data.getlist('service_name')
    service_prices = form_data.getlist('service_price')
    
    # First, deactivate all existing services to handle removed items
    Service.query.update({Service.is_active: False})
    
    for i, name in enumerate(service_names):
        if name.strip():
            price = service_prices[i] if i < len(service_prices) else '0'
            try:
                price = float(price)
            except (ValueError, TypeError):
                price = 0.0
                
            # Check if service already exists
            existing_service = Service.query.filter_by(name=name).first()
            if existing_service:
                existing_service.price = price
                existing_service.is_active = True
            else:
                # Create new service
                service = Service(
                    name=name,
                    code=f"SRV{datetime.now().strftime('%Y%m%d%H%M%S')}{i:02d}",
                    price=price
                )
                db.session.add(service)

def save_communication_settings(form_data):
    """Save communication-related settings"""
    # SMS Gateway
    update_setting('sms_gateway_provider', form_data.get('sms_gateway_provider', 'twilio'), 'string', 'communication')
    update_setting('sms_gateway_api_key', form_data.get('sms_gateway_api_key', ''), 'string', 'communication')
    update_setting('sms_gateway_api_secret', form_data.get('sms_gateway_api_secret', ''), 'string', 'communication')
    update_setting('sms_gateway_sender_number', form_data.get('sms_gateway_sender_number', ''), 'string', 'communication')
    
    # Email Gateway
    update_setting('email_gateway_provider', form_data.get('email_gateway_provider', 'smtp'), 'string', 'communication')
    update_setting('email_smtp_server', form_data.get('email_smtp_server', 'smtp.gmail.com'), 'string', 'communication')
    update_setting('email_smtp_port', form_data.get('email_smtp_port', '587'), 'number', 'communication')
    update_setting('email_smtp_username', form_data.get('email_smtp_username', ''), 'string', 'communication')
    update_setting('email_smtp_password', form_data.get('email_smtp_password', ''), 'string', 'communication')
    update_setting('email_use_tls', 'email_use_tls' in form_data, 'boolean', 'communication')
    
    # Notification preferences
    notification_events = ['appointment_reminder', 'appointment_cancelled', 'lab_result_ready',
                         'payment_reminder', 'medicine_refill', 'follow_up_reminder']
    
    for event in notification_events:
        update_setting(f'notify_{event}_email', f'notify_{event}_email' in form_data, 'boolean', 'communication')
        update_setting(f'notify_{event}_sms', f'notify_{event}_sms' in form_data, 'boolean', 'communication')
        update_setting(f'notify_{event}_whatsapp', f'notify_{event}_whatsapp' in form_data, 'boolean', 'communication')
        update_setting(f'notify_{event}_push', f'notify_{event}_push' in form_data, 'boolean', 'communication')
    
    # WhatsApp settings
    update_setting('enable_whatsapp', 'enable_whatsapp' in form_data, 'boolean', 'communication')
    update_setting('whatsapp_api_key', form_data.get('whatsapp_api_key', ''), 'string', 'communication')
    update_setting('whatsapp_webhook_url', form_data.get('whatsapp_webhook_url', ''), 'string', 'communication')

def save_billing_settings(form_data):
    """Save billing-related settings"""
    # Currency
    update_setting('currency', form_data.get('currency', 'USD'), 'string', 'billing')
    update_setting('currency_symbol', form_data.get('currency_symbol', '$'), 'string', 'billing')
    
    # Tax rules
    update_setting('tax_type', form_data.get('tax_type', 'gst'), 'string', 'billing')
    update_setting('tax_percentage', form_data.get('tax_percentage', '0'), 'number', 'billing')
    update_setting('tax_inclusive_pricing', 'tax_inclusive_pricing' in form_data, 'boolean', 'billing')
    
    # Payment gateways
    gateways = ['paypal', 'razorpay', 'paytm', 'stripe']
    for gateway in gateways:
        is_enabled = f'{gateway}_enabled' in form_data
        update_setting(f'{gateway}_enabled', is_enabled, 'boolean', 'billing')
        update_setting(f'{gateway}_api_key', form_data.get(f'{gateway}_api_key', ''), 'string', 'billing')
        update_setting(f'{gateway}_api_secret', form_data.get(f'{gateway}_api_secret', ''), 'string', 'billing')
        update_setting(f'{gateway}_merchant_id', form_data.get(f'{gateway}_merchant_id', ''), 'string', 'billing')
        update_setting(f'{gateway}_test_mode', f'{gateway}_test_mode' in form_data, 'boolean', 'billing')
    
    # Insurance settings
    update_setting('enable_insurance_billing', 'enable_insurance_billing' in form_data, 'boolean', 'billing')
    update_setting('auto_generate_claims', 'auto_generate_claims' in form_data, 'boolean', 'billing')
    
    # Discount policies
    update_setting('enable_early_payment_discount', 'enable_early_payment_discount' in form_data, 'boolean', 'billing')
    update_setting('early_payment_discount_percentage', form_data.get('early_payment_discount_percentage', '5'), 'number', 'billing')
    update_setting('early_payment_discount_days', form_data.get('early_payment_discount_days', '7'), 'number', 'billing')
    
    update_setting('enable_staff_discount', 'enable_staff_discount' in form_data, 'boolean', 'billing')
    update_setting('staff_discount_percentage', form_data.get('staff_discount_percentage', '10'), 'number', 'billing')

def save_telemedicine_settings(form_data, files=None):
    """Save telemedicine-related settings"""
    # Video provider
    update_setting('video_provider', form_data.get('video_provider', 'webrtc'), 'string', 'telemedicine')
    update_setting('webrtc_stun_server', form_data.get('webrtc_stun_server', 'stun:stun.l.google.com:19302'), 'string', 'telemedicine')
    update_setting('webrtc_turn_server', form_data.get('webrtc_turn_server', ''), 'string', 'telemedicine')
    update_setting('webrtc_turn_username', form_data.get('webrtc_turn_username', ''), 'string', 'telemedicine')
    update_setting('webrtc_turn_password', form_data.get('webrtc_turn_password', ''), 'string', 'telemedicine')
    
    # Recording settings
    update_setting('enable_telemedicine_recording', 'enable_telemedicine_recording' in form_data, 'boolean', 'telemedicine')
    update_setting('recording_retention_days', form_data.get('recording_retention_days', '30'), 'number', 'telemedicine')
    
    # E-prescription
    update_setting('enable_eprescription', 'enable_eprescription' in form_data, 'boolean', 'telemedicine')
    
    if files and 'doctor_signature' in files and files['doctor_signature'].filename:
        signature_path = save_uploaded_file(files['doctor_signature'], 'uploads/signatures')
        if signature_path:
            update_setting('doctor_signature_path', signature_path, 'string', 'telemedicine')
    
    # Telehealth consent
    update_setting('require_telehealth_consent', 'require_telehealth_consent' in form_data, 'boolean', 'telemedicine')
    update_setting('telehealth_consent_text', form_data.get('telehealth_consent_text', ''), 'string', 'telemedicine')

def save_data_settings(form_data):
    """Save data & privacy-related settings"""
    # Backup settings
    update_setting('backup_schedule', form_data.get('backup_schedule', 'daily'), 'string', 'data')
    update_setting('backup_time', form_data.get('backup_time', '02:00'), 'string', 'data')
    update_setting('backup_retention_days', form_data.get('backup_retention_days', '30'), 'number', 'data')
    update_setting('enable_auto_backup', 'enable_auto_backup' in form_data, 'boolean', 'data')
    
    # Data retention
    update_setting('patient_data_retention_years', form_data.get('patient_data_retention_years', '7'), 'number', 'data')
    update_setting('inactive_patient_retention_years', form_data.get('inactive_patient_retention_years', '2'), 'number', 'data')
    
    # Data anonymization
    update_setting('enable_data_anonymization', 'enable_data_anonymization' in form_data, 'boolean', 'data')
    update_setting('anonymization_after_years', form_data.get('anonymization_after_years', '10'), 'number', 'data')
    
    # Export/Import settings
    update_setting('enable_data_export', 'enable_data_export' in form_data, 'boolean', 'data')
    update_setting('enable_data_import', 'enable_data_import' in form_data, 'boolean', 'data')
    update_setting('require_export_approval', 'require_export_approval' in form_data, 'boolean', 'data')

def save_ui_settings(form_data):
    """Save UI & accessibility-related settings"""
    # Theme settings
    update_setting('default_theme', form_data.get('default_theme', 'light'), 'string', 'ui')
    update_setting('enable_theme_switcher', 'enable_theme_switcher' in form_data, 'boolean', 'ui')
    
    # Font settings
    update_setting('default_font_size', form_data.get('default_font_size', 'medium'), 'string', 'ui')
    update_setting('enable_font_scaling', 'enable_font_scaling' in form_data, 'boolean', 'ui')
    update_setting('enable_high_contrast', 'enable_high_contrast' in form_data, 'boolean', 'ui')
    
    # UI preferences
    update_setting('sidebar_collapsed', 'sidebar_collapsed' in form_data, 'boolean', 'ui')
    update_setting('compact_mode', 'compact_mode' in form_data, 'boolean', 'ui')
    update_setting('show_tooltips', 'show_tooltips' in form_data, 'boolean', 'ui')

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    # Only allow admin users to access settings
    if current_user.role != 'admin':
        flash('Access denied! Only administrators can access settings.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # Get the action to determine which settings to save
        action = request.form.get('action', 'general')
        
        try:
            if action == 'organization':
                save_organization_settings(request.form, request.files)
                flash('Organization settings saved successfully!', 'success')
            elif action == 'security':
                save_security_settings(request.form, request.files)
                flash('Security settings saved successfully!', 'success')
            elif action == 'clinical':
                save_clinical_settings(request.form, request.files)
                flash('Clinical settings saved successfully!', 'success')
            elif action == 'communication':
                save_communication_settings(request.form)
                flash('Communication settings saved successfully!', 'success')
            elif action == 'billing':
                save_billing_settings(request.form)
                flash('Billing settings saved successfully!', 'success')
            elif action == 'telemedicine':
                save_telemedicine_settings(request.form, request.files)
                flash('Telemedicine settings saved successfully!', 'success')
            elif action == 'data':
                save_data_settings(request.form)
                flash('Data & Privacy settings saved successfully!', 'success')
            elif action == 'ui':
                save_ui_settings(request.form)
                flash('UI & Accessibility settings saved successfully!', 'success')
            else:
                # Save currency for backward compatibility
                currency = request.form.get('currency', 'USD')
                update_setting('currency', currency, 'string', 'billing')
                session['currency'] = currency
                flash(f'Currency updated to {currency}', 'success')
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving settings: {str(e)}', 'error')
        
        return redirect(url_for('settings'))
    
    # Get all settings from database
    all_settings = get_all_settings()
    
    # Get branches for organization settings
    branches = HospitalBranch.query.all()
    
    # Get consent forms for clinical settings
    consent_forms = ConsentForm.query.all()
    
    # Get role templates for security settings
    role_templates = UserRoleTemplate.query.all()
    
    # Get appointment slot templates for clinical settings
    slot_templates = AppointmentSlotTemplate.query.all()
    
    # Get services for clinical settings
    services = Service.query.filter_by(is_active=True).all()
    
    # Currencies for billing settings
    currencies = [
        {"code": "USD", "name": "US Dollar", "symbol": "$"},
        {"code": "EUR", "name": "Euro", "symbol": "€"},
        {"code": "GBP", "name": "British Pound", "symbol": "£"},
        {"code": "INR", "name": "Indian Rupee", "symbol": "₹"},
        {"code": "JPY", "name": "Japanese Yen", "symbol": "¥"},
        {"code": "CAD", "name": "Canadian Dollar", "symbol": "C$"},
        {"code": "AUD", "name": "Australian Dollar", "symbol": "A$"}
    ]
    
    # Languages for organization settings
    languages = [
        {"code": "en", "name": "English"},
        {"code": "hi", "name": "हिन्दी (Hindi)"},
        {"code": "mr", "name": "मराठी (Marathi)"},
        {"code": "te", "name": "తెలుగు (Telugu)"},
        {"code": "ta", "name": "தமிழ் (Tamil)"},
        {"code": "gu", "name": "ગુજરાતી (Gujarati)"},
        {"code": "bn", "name": "বাংলা (Bengali)"},
        {"code": "kn", "name": "ಕನ್ನಡ (Kannada)"}
    ]
    
    # Get selected currency
    selected_currency = session.get('currency', all_settings.get('currency', 'USD'))
    
    return render_template('settings.html',
                         settings=all_settings,
                         branches=branches,
                         consent_forms=consent_forms,
                         role_templates=role_templates,
                         slot_templates=slot_templates,
                         services=services,
                         currencies=currencies,
                         languages=languages,
                         selected_currency=selected_currency)

# Initialize database and create admin user
def init_web_db():
    global backup_manager, audit_logger, two_factor_auth, notification_system
    global data_export_import, document_management, advanced_security, payment_gateway
    global emergency_management, inventory_management, quality_management
    
    with app.app_context():
        db.create_all()
        
        # Initialize all advanced systems within app context
        backup_manager = BackupManager()
        audit_logger = init_audit_logger(app, db)
        two_factor_auth = init_2fa(app, db)
        notification_system = init_notification_system(app, db)
        data_export_import = DataExportImport(db, app)
        document_management = init_document_management(app, db)
        advanced_security = init_advanced_security(app, db)
        payment_gateway = init_payment_gateway(app, db)
        emergency_management = init_emergency_management(app, db)
        inventory_management = init_inventory_management(app, db)
        quality_management = init_quality_management(app, db)
        
        # Store systems in app context for global access
        app.backup_manager = backup_manager
        app.audit_logger = audit_logger
        app.two_factor_auth = two_factor_auth
        app.notification_system = notification_system
        app.data_export_import = data_export_import
        app.document_management = document_management
        app.advanced_security = advanced_security
        app.payment_gateway = payment_gateway
        app.emergency_management = emergency_management
        app.inventory_management = inventory_management
        app.quality_management = quality_management
        
        # Start notification scheduler after all systems are initialized
        notification_system.start_notification_scheduler()
        
       
        # Create admin user if not exists
        admin = WebUser.query.filter_by(username='admin').first()
        if not admin:
            admin = WebUser(
                username='admin',
                email='admin@hospital.com',
                password_hash=generate_password_hash('admin123'),
                full_name='System Administrator',
                role='admin',
                department='Administration',
                employee_id='EMP000001'
            )
            db.session.add(admin)
        
        # Create sample users for different roles
        users_data = [
            {'username': 'doctor', 'email': 'doctor@hospital.com', 'password': 'doctor123', 'full_name': 'Dr. John Smith', 'role': 'doctor', 'department': 'General Medicine', 'specialization': 'Internal Medicine'},
            {'username': 'nurse', 'email': 'nurse@hospital.com', 'password': 'nurse123', 'full_name': 'Sarah Johnson', 'role': 'nurse', 'department': 'General Ward'},
            {'username': 'receptionist', 'email': 'reception@hospital.com', 'password': 'reception123', 'full_name': 'Mary Wilson', 'role': 'receptionist', 'department': 'Front Desk'},
            {'username': 'labtech', 'email': 'lab@hospital.com', 'password': 'lab123', 'full_name': 'David Brown', 'role': 'lab_tech', 'department': 'Laboratory'},
            {'username': 'pharmacist', 'email': 'pharmacy@hospital.com', 'password': 'pharmacy123', 'full_name': 'Lisa Davis', 'role': 'pharmacist', 'department': 'Pharmacy'},
            {'username': 'accountant', 'email': 'accounts@hospital.com', 'password': 'accounts123', 'full_name': 'Robert Miller', 'role': 'accountant', 'department': 'Accounts'}
        ]
        
        for i, user_data in enumerate(users_data, 2):
            existing_user = WebUser.query.filter_by(username=user_data['username']).first()
            if not existing_user:
                user = WebUser(
                    username=user_data['username'],
                    email=user_data['email'],
                    password_hash=generate_password_hash(user_data['password']),
                    full_name=user_data['full_name'],
                    role=user_data['role'],
                    department=user_data['department'],
                    employee_id=f'EMP{i:06d}',
                    specialization=user_data.get('specialization')
                )
                db.session.add(user)
        
        # Create departments
        departments_data = [
            {'name': 'General Medicine', 'code': 'GM'},
            {'name': 'Cardiology', 'code': 'CARD'},
            {'name': 'Neurology', 'code': 'NEURO'},
            {'name': 'Orthopedics', 'code': 'ORTHO'},
            {'name': 'Pediatrics', 'code': 'PEDS'},
            {'name': 'Emergency', 'code': 'ER'},
            {'name': 'Laboratory', 'code': 'LAB'},
            {'name': 'Radiology', 'code': 'RAD'},
            {'name': 'Pharmacy', 'code': 'PHARM'}
        ]
        
        for dept_data in departments_data:
            existing_dept = Department.query.filter_by( code=dept_data['code']).first()
            if not existing_dept:
                dept = Department(
                    name=dept_data['name'],
                    code=dept_data['code'],
                    description=f"{dept_data['name']} Department"
                )
                db.session.add(dept)
        
        # Create wards and beds
        wards_data = [
            {'name': 'General Ward A', 'ward_type': 'general', 'total_beds': 20, 'charge_per_day': 100.0},
            {'name': 'General Ward B', 'ward_type': 'general', 'total_beds': 20, 'charge_per_day': 100.0},
            {'name': 'ICU', 'ward_type': 'icu', 'total_beds': 10, 'charge_per_day': 500.0},
            {'name': 'Emergency Ward', 'ward_type': 'emergency', 'total_beds': 15, 'charge_per_day': 200.0},
            {'name': 'Maternity Ward', 'ward_type': 'maternity', 'total_beds': 12, 'charge_per_day': 150.0}
        ]
        
        for ward_data in wards_data:
            existing_ward = Ward.query.filter_by( name=ward_data['name']).first()
            if not existing_ward:
                ward = Ward(
                    name=ward_data['name'],
                    ward_type=ward_data['ward_type'],
                    total_beds=ward_data['total_beds'],
                    available_beds=ward_data['total_beds'],
                    charge_per_day=ward_data['charge_per_day']
                )
                db.session.add(ward)
                db.session.flush()  # Get ward ID
                
                # Create beds for this ward
                for bed_num in range(1, ward_data['total_beds'] + 1):
                    bed = Bed(
                        bed_number=f"{ward_data['name'][:3]}{bed_num:02d}",
                        ward_id=ward.id,
                        bed_type='general' if ward_data['ward_type'] != 'icu' else 'icu'
                    )
                    db.session.add(bed)
        
        # Create sample lab tests
        lab_tests_data = [
            {'test_name': 'Complete Blood Count', 'test_code': 'CBC', 'category': 'Hematology', 'normal_range': 'WBC: 4-11 K/uL', 'price': 25.0},
            {'test_name': 'Blood Glucose', 'test_code': 'GLU', 'category': 'Chemistry', 'normal_range': '70-100 mg/dL', 'price': 15.0},
            {'test_name': 'Lipid Profile', 'test_code': 'LIPID', 'category': 'Chemistry', 'normal_range': 'Total Cholesterol <200 mg/dL', 'price': 35.0},
            {'test_name': 'Liver Function Test', 'test_code': 'LFT', 'category': 'Chemistry', 'normal_range': 'ALT: 7-56 U/L', 'price': 40.0},
            {'test_name': 'Kidney Function Test', 'test_code': 'KFT', 'category': 'Chemistry', 'normal_range': 'Creatinine: 0.6-1.2 mg/dL', 'price': 30.0}
        ]
        
        for test_data in lab_tests_data:
            existing_test = LabTest.query.filter_by( test_code=test_data['test_code']).first()
            if not existing_test:
                test = LabTest(**test_data)
                db.session.add(test)
        
        # Create sample imaging tests
        imaging_tests_data = [
            {'test_name': 'Chest X-Ray', 'test_code': 'CXR', 'category': 'X-ray', 'price': 50.0},
            {'test_name': 'CT Scan Head', 'test_code': 'CT-HEAD', 'category': 'CT', 'price': 200.0},
            {'test_name': 'MRI Brain', 'test_code': 'MRI-BRAIN', 'category': 'MRI', 'price': 400.0},
            {'test_name': 'Ultrasound Abdomen', 'test_code': 'USG-ABD', 'category': 'Ultrasound', 'price': 75.0},
            {'test_name': 'ECG', 'test_code': 'ECG', 'category': 'Cardiac', 'price': 25.0}
        ]
        
        for test_data in imaging_tests_data:
            existing_test = ImagingTest.query.filter_by(test_code=test_data['test_code']).first()
            if not existing_test:
                test = ImagingTest(**test_data)
                db.session.add(test)
        
        # Create sample medicines
        medicines_data = [
            {'name': 'Paracetamol', 'generic_name': 'Acetaminophen', 'category': 'Analgesic', 'dosage_form': 'Tablet', 'strength': '500mg', 'purchase_price': 0.10, 'selling_price': 0.15, 'stock_quantity': 1000},
            {'name': 'Amoxicillin', 'generic_name': 'Amoxicillin', 'category': 'Antibiotic', 'dosage_form': 'Capsule', 'strength': '250mg', 'purchase_price': 0.25, 'selling_price': 0.40, 'stock_quantity': 500},
            {'name': 'Ibuprofen', 'generic_name': 'Ibuprofen', 'category': 'NSAID', 'dosage_form': 'Tablet', 'strength': '400mg', 'purchase_price': 0.15, 'selling_price': 0.25, 'stock_quantity': 800},
            {'name': 'Metformin', 'generic_name': 'Metformin HCl', 'category': 'Antidiabetic', 'dosage_form': 'Tablet', 'strength': '500mg', 'purchase_price': 0.20, 'selling_price': 0.35, 'stock_quantity': 600},
            {'name': 'Omeprazole', 'generic_name': 'Omeprazole', 'category': 'PPI', 'dosage_form': 'Capsule', 'strength': '20mg', 'purchase_price': 0.30, 'selling_price': 0.50, 'stock_quantity': 400}
        ]
        
        for med_data in medicines_data:
            existing_med = Medicine.query.filter_by(name=med_data['name'], strength=med_data['strength']).first()
            if not existing_med:
                medicine = Medicine(**med_data)
                db.session.add(medicine)
        
        # Create sample services
        services_data = [
            {'name': 'General Consultation', 'code': 'CONSULT', 'price': 50.0},
            {'name': 'Emergency Consultation', 'code': 'ER-CONSULT', 'price': 100.0},
            {'name': 'Specialist Consultation', 'code': 'SPEC-CONSULT', 'price': 75.0},
            {'name': 'Procedure - Minor', 'code': 'PROC-MIN', 'price': 150.0},
            {'name': 'Procedure - Major', 'code': 'PROC-MAJ', 'price': 500.0}
        ]
        
        for service_data in services_data:
            existing_service = Service.query.filter_by(code=service_data['code']).first()
            if not existing_service:
                service = Service(**service_data)
                db.session.add(service)
        
        db.session.commit()

@app.context_processor
def inject_global_vars():
    current_branch = None
    if current_user.is_authenticated and 'current_branch_id' in session:
        current_branch = HospitalBranch.query.get(session['current_branch_id'])
    
    # Get settings for all templates
    all_settings = get_all_settings()
    
    return dict(
        get_text=get_text,
        get_language=get_language,
        datetime=datetime,
        current_branch=current_branch,
        settings=all_settings
    )

@app.route('/switch-branch/<int:branch_id>')
@login_required
def switch_branch(branch_id):
    """Switch to a different branch"""
    if branch_id == 0:
        # Switch to all branches view
        session.pop('current_branch_id', None)
        session.pop('current_branch_name', None)
        session.pop('current_branch_code', None)
        flash('Switched to all branches view', 'success')
    else:
        branch = HospitalBranch.query.get_or_404(branch_id)
        
        # Update session with new branch
        session['current_branch_id'] = branch.id
        session['current_branch_name'] = branch.name
        session['current_branch_code'] = branch.code
        
        flash(f'Switched to {branch.name} branch', 'success')
    
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/settings/delete_branch/<int:branch_id>', methods=['POST'])
@login_required
def delete_branch(branch_id):
    # Only allow admin users to delete branches
    if current_user.role != 'admin':
        flash('Access denied! Only administrators can delete branches.', 'error')
        return redirect(url_for('settings'))
    
    branch = HospitalBranch.query.get_or_404(branch_id)
    
    try:
        # Delete the branch
        db.session.delete(branch)
        db.session.commit()
        
        flash('Branch deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting branch: {str(e)}', 'error')
    
    return redirect(url_for('settings'))

@app.route('/api/branches')
@login_required
def get_branches():
    """API endpoint to get all branches for the dropdown"""
    branches = HospitalBranch.query.filter_by(is_active=True).all()
    return jsonify([{
        'id': branch.id,
        'name': branch.name,
        'code': branch.code,
        'city': branch.city,
        'state': branch.state
    } for branch in branches])

# =============== HTMX API ROUTES ===============
@app.route('/api/patient-info')
@login_required
def api_patient_info():
    patient_id = request.args.get('patient_id')
    if patient_id:
        patient = WebPatient.query.get(patient_id)
        if patient:
            return render_template_string('''
                <h6>Patient Details</h6>
                <p><strong>Name:</strong> {{ patient.first_name }} {{ patient.last_name }}</p>
                <p><strong>ID:</strong> {{ patient.patient_id }}</p>
                <p><strong>Phone:</strong> {{ patient.phone }}</p>
                <p><strong>Blood Group:</strong> {{ patient.blood_group or 'Not specified' }}</p>
                <p><strong>Allergies:</strong> {{ patient.allergies or 'None reported' }}</p>
                <p><strong>Insurance:</strong> {{ patient.insurance_provider or 'Not specified' }}</p>
            ''', patient=patient)
    return '<p class="text-muted">Select a patient to view details</p>'

@app.route('/api/patient-billing-info')
@login_required
def api_patient_billing_info():
    patient_id = request.args.get('patient_id')
    if patient_id:
        patient = WebPatient.query.get(patient_id)
        if patient:
            # Get recent bills
            recent_bills = Bill.query.filter_by(patient_id=patient_id).order_by(Bill.bill_date.desc()).limit(3).all()
            outstanding_amount = sum(bill.balance_amount for bill in recent_bills if bill.balance_amount > 0)
            
            return render_template_string('''
                <h6>Billing Information</h6>
                <p><strong>Patient:</strong> {{ patient.first_name }} {{ patient.last_name }}</p>
                <p><strong>Insurance:</strong> {{ patient.insurance_provider or 'Self Pay' }}</p>
                <p><strong>Policy:</strong> {{ patient.insurance_number or 'N/A' }}</p>
                <p><strong>Outstanding:</strong> <span class="text-danger">${{ "%.2f"|format(outstanding_amount) }}</span></p>
                
                {% if recent_bills %}
                <h6 class="mt-3">Recent Bills</h6>
                <div class="list-group list-group-flush">
                    {% for bill in recent_bills %}
                    <div class="list-group-item d-flex justify-content-between">
                        <span>{{ bill.bill_number }}</span>
                        <span class="text-{{ 'success' if bill.balance_amount == 0 else 'danger' }}">
                            ${{ "%.2f"|format(bill.total_amount) }}
                        </span>
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
            ''', patient=patient, recent_bills=recent_bills, outstanding_amount=outstanding_amount)
    return '<p class="text-muted">Select a patient to view billing information</p>'

# =============== MISSING ROUTES ===============
@app.route('/pharmacy/reports/low-stock')
@login_required
@role_required('admin', 'pharmacist')
def pharmacy_low_stock_report():
    low_stock_medicines = Medicine.query.filter(
        Medicine.stock_quantity <= Medicine.min_stock_level,
        Medicine.is_active == True
    ).all()
    
    return render_template('pharmacy_low_stock_report.html', medicines=low_stock_medicines)

@app.route('/admin/department/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_department():
    if request.method == 'POST':
        department = Department(
            name=request.form['name'],
            code=request.form['code'],
            description=request.form.get('description'),
            head_of_department=request.form.get('head_of_department') or None
        )
        db.session.add(department)
        db.session.commit()
        
        response = make_response(redirect(url_for('manage_departments')))
        response.headers['HX-Success'] = 'Department added successfully!'
        return response
    
    doctors = WebUser.query.filter_by(role='doctor').all()
    return render_template('add_department_modal.html', doctors=doctors)

@app.route('/admin/ward/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_ward():
    if request.method == 'POST':
        ward = Ward(
            name=request.form['name'],
            ward_type=request.form['ward_type'],
            total_beds=int(request.form['total_beds']),
            available_beds=int(request.form['total_beds']),
            charge_per_day=float(request.form['charge_per_day'])
        )
        db.session.add(ward)
        db.session.flush()
        
        # Create beds for the ward
        for i in range(1, int(request.form['total_beds']) + 1):
            bed = Bed(
                bed_number=f"{request.form['name'][:3].upper()}{i:02d}",
                ward_id=ward.id,
                bed_type=request.form.get('bed_type', 'general')
            )
            db.session.add(bed)
        
        db.session.commit()
        
        response = make_response(redirect(url_for('manage_wards')))
        response.headers['HX-Success'] = 'Ward added successfully!'
        return response
    
    return render_template('add_ward_modal.html')

# =============== ENHANCED APPOINTMENT ROUTES WITH HTMX ===============
@app.route('/appointment/<int:appointment_id>/view')
@login_required
def view_appointment_details(appointment_id):
    appointment = WebAppointment.query.get_or_404(appointment_id)
    return render_template('appointment_details_modal.html', appointment=appointment)

@app.route('/appointment/<int:appointment_id>/complete', methods=['POST'])
@login_required
@role_required('doctor', 'nurse', 'admin')
def complete_appointment(appointment_id):
    appointment = WebAppointment.query.get_or_404(appointment_id)
    appointment.status = 'completed'
    db.session.commit()
    
    response = make_response('')
    response.headers['HX-Success'] = 'Appointment marked as completed!'
    response.headers['HX-Refresh'] = 'true'
    return response

@app.route('/appointment/<int:appointment_id>/cancel', methods=['POST'])
@login_required
@role_required('doctor', 'nurse', 'admin', 'receptionist')
def cancel_appointment(appointment_id):
    appointment = WebAppointment.query.get_or_404(appointment_id)
    appointment.status = 'cancelled'
    db.session.commit()
    
    response = make_response('')
    response.headers['HX-Success'] = 'Appointment cancelled!'
    response.headers['HX-Refresh'] = 'true'
    return response

# =============== BACKUP & DISASTER RECOVERY ROUTES ===============
@app.route('/admin/backup')
@login_required
@role_required('admin')
@audit_action('view_backup_management', 'system', 'medium')
def backup_management():
    backups = backup_manager.list_backups()
    return render_template('backup_management.html', backups=backups)

@app.route('/admin/backup/create', methods=['POST'])
@login_required
@role_required('admin')
@audit_action('create_backup', 'system', 'high')
def create_backup():
    try:
        backup_path = backup_manager.create_backup('manual')
        flash('Backup created successfully!', 'success')
        notification_system.send_notification(
            'staff', current_user.id, 'backup_success',
            {'backup_path': backup_path, 'user_name': current_user.full_name}
        )
    except Exception as e:
        flash(f'Backup failed: {str(e)}', 'error')
    
    return redirect(url_for('backup_management'))

@app.route('/admin/backup/restore/<path:backup_path>', methods=['POST'])
@login_required
@role_required('admin')
@audit_action('restore_backup', 'system', 'critical')
def restore_backup(backup_path):
    try:
        backup_manager.restore_backup(backup_path)
        flash('Database restored successfully!', 'success')
        audit_logger.log_security_event(
            'database_restore', 'high',
            f'Database restored from backup by {current_user.username}',
            {'backup_path': backup_path}
        )
    except Exception as e:
        flash(f'Restore failed: {str(e)}', 'error')
    
    return redirect(url_for('backup_management'))

@app.route('/admin/backup/verify/<path:backup_path>')
@login_required
@role_required('admin')
def verify_backup(backup_path):
    try:
        is_valid, message = backup_manager.verify_backup_integrity(backup_path)
        return jsonify({'valid': is_valid, 'message': message})
    except Exception as e:
        return jsonify({'valid': False, 'message': str(e)})

# =============== TWO-FACTOR AUTHENTICATION ROUTES ===============
@app.route('/2fa/setup')
@login_required
def setup_2fa():
    if two_factor_auth.is_2fa_enabled(current_user.id):
        flash('2FA is already enabled for your account.', 'info')
        return redirect(url_for('profile'))
    
    qr_data = two_factor_auth.generate_qr_code(current_user.id, current_user.username)
    return render_template('2fa_setup.html', qr_data=qr_data)

@app.route('/2fa/enable', methods=['POST'])
@login_required
def enable_2fa():
    verification_code = request.form.get('verification_code')
    method = request.form.get('method', 'app')
    
    success, message = two_factor_auth.enable_2fa(
        current_user.id, method, verification_code
    )
    
    if success:
        flash('2FA enabled successfully!', 'success')
        audit_logger.log_user_activity('enable_2fa', 'user', current_user.id, risk_level='medium')
    else:
        flash(f'Failed to enable 2FA: {message}', 'error')
    
    return redirect(url_for('profile'))

@app.route('/2fa/disable', methods=['POST'])
@login_required
def disable_2fa():
    if two_factor_auth.disable_2fa(current_user.id):
        flash('2FA disabled successfully!', 'success')
        audit_logger.log_user_activity('disable_2fa', 'user', current_user.id, risk_level='medium')
    else:
        flash('Failed to disable 2FA.', 'error')
    
    return redirect(url_for('profile'))

@app.route('/2fa/verify', methods=['GET', 'POST'])
def verify_2fa():
    if not session.get('2fa_user_id'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        user_id = session.get('2fa_user_id')
        code = request.form.get('code')
        method = request.form.get('method', 'app')
        
        verified = False
        if method == 'app':
            verified = two_factor_auth.verify_totp_code(user_id, code)
        elif method == 'backup':
            verified = two_factor_auth.verify_backup_code(user_id, code)
        elif method == 'sms':
            verified = two_factor_auth.verify_sms_code(user_id, code)
        elif method == 'email':
            verified = two_factor_auth.verify_email_code(user_id, code)
        
        if verified:
            session['2fa_verified'] = True
            user = WebUser.query.get(user_id)
            login_user(user)
            audit_logger.log_login_attempt(user.username, success=True)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid verification code.', 'error')
    
    user_id = session.get('2fa_user_id')
    methods = two_factor_auth.get_2fa_methods(user_id)
    return render_template('2fa_verify.html', methods=methods)

@app.route('/2fa/send_sms', methods=['POST'])
def send_2fa_sms():
    user_id = session.get('2fa_user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Invalid session'})
    
    user = WebUser.query.get(user_id)
    if user and user.phone:
        success = two_factor_auth.send_sms_code(user_id, user.phone)
        return jsonify({'success': success})
    
    return jsonify({'success': False, 'message': 'Phone number not available'})

@app.route('/2fa/send_email', methods=['POST'])
def send_2fa_email():
    user_id = session.get('2fa_user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Invalid session'})
    
    user = WebUser.query.get(user_id)
    if user and user.email:
        success = two_factor_auth.send_email_code(user_id, user.email)
        return jsonify({'success': success})
    
    return jsonify({'success': False, 'message': 'Email not available'})

# =============== DATA EXPORT/IMPORT ROUTES ===============
@app.route('/admin/export')
@login_required
@role_required('admin')
@audit_action('view_export_page', 'system')
def data_export():
    return render_template('data_export.html')

@app.route('/admin/export/patients/<format>')
@login_required
@role_required('admin')
@audit_action('export_patients', 'patient_data', 'high')
def export_patients(format):
    try:
        patient_ids = request.args.getlist('patient_ids')
        include_sensitive = request.args.get('include_sensitive') == 'true'
        
        if format == 'csv':
            file_path = data_export_import.export_patients_csv(patient_ids, include_sensitive)
        elif format == 'excel':
            include_medical = request.args.get('include_medical') == 'true'
            file_path = data_export_import.export_patients_excel(patient_ids, include_medical)
        elif format == 'pdf':
            file_path = data_export_import.export_patients_pdf(patient_ids)
        elif format == 'fhir':
            file_path = data_export_import.export_hl7_fhir(patient_ids)
        else:
            flash('Invalid export format.', 'error')
            return redirect(url_for('data_export'))
        
        return create_download_response(file_path)
        
    except Exception as e:
        flash(f'Export failed: {str(e)}', 'error')
        return redirect(url_for('data_export'))

@app.route('/admin/export/comprehensive')
@login_required
@role_required('admin')
@audit_action('export_comprehensive_report', 'system', 'medium')
def export_comprehensive_report():
    try:
        report_type = request.args.get('type', 'monthly')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        file_path = data_export_import.generate_comprehensive_report(
            report_type, start_date, end_date
        )
        
        return create_download_response(file_path)
        
    except Exception as e:
        flash(f'Report generation failed: {str(e)}', 'error')
        return redirect(url_for('data_export'))

@app.route('/admin/import')
@login_required
@role_required('admin')
@audit_action('view_import_page', 'system')
def data_import():
    return render_template('data_import.html')

@app.route('/admin/import/patients', methods=['POST'])
@login_required
@role_required('admin')
@audit_action('import_patients', 'patient_data', 'high')
def import_patients():
    try:
        if 'file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(url_for('data_import'))
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(url_for('data_import'))
        
        # Save uploaded file
        import_path = data_export_import.import_dir / file.filename
        file.save(import_path)
        
        # Determine import type
        validate_only = request.form.get('validate_only') == 'true'
        
        if file.filename.endswith('.csv'):
            results = data_export_import.import_patients_csv(import_path, validate_only)
        elif file.filename.endswith('.json'):
            results = data_export_import.import_hl7_fhir(import_path, validate_only)
        else:
            flash('Unsupported file format.', 'error')
            return redirect(url_for('data_import'))
        
        # Clean up uploaded file
        import_path.unlink()
        
        return render_template('import_results.html', results=results)
        
    except Exception as e:
        flash(f'Import failed: {str(e)}', 'error')
        return redirect(url_for('data_import'))

# =============== AUDIT & COMPLIANCE ROUTES ===============
@app.route('/admin/audit')
@login_required
@role_required('admin')
@audit_action('view_audit_logs', 'system', 'medium')
def audit_logs():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # Get user activities
    activities = audit_logger.UserActivityAudit.query.order_by(
        audit_logger.UserActivityAudit.timestamp.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('audit_logs.html', activities=activities)

@app.route('/admin/audit/compliance-report')
@login_required
@role_required('admin')
@audit_action('generate_compliance_report', 'system', 'high')
def compliance_report():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            # Default to last 30 days
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        report = audit_logger.generate_compliance_report(start_date, end_date)
        
        return jsonify(report)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/security-events')
@login_required
@role_required('admin')
@audit_action('view_security_events', 'system', 'medium')
def security_events():
    page = request.args.get('page', 1, type=int)
    per_page = 25
    
    events = audit_logger.SecurityEvent.query.order_by(
        audit_logger.SecurityEvent.timestamp.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('security_events.html', events=events)

# =============== NOTIFICATION MANAGEMENT ROUTES ===============
@app.route('/admin/notifications')
@login_required
@role_required('admin')
def notification_management():
    stats = notification_system.get_notification_statistics()
    return render_template('notification_management.html', stats=stats)

@app.route('/admin/notifications/send', methods=['POST'])
@login_required
@role_required('admin')
@audit_action('send_manual_notification', 'notification', 'medium')
def send_manual_notification():
    try:
        recipient_type = request.form.get('recipient_type')
        recipient_id = int(request.form.get('recipient_id'))
        notification_type = request.form.get('notification_type')
        channels = request.form.getlist('channels')
        
        # Get template data from form
        template_data = {}
        for key, value in request.form.items():
            if key.startswith('template_'):
                template_data[key[9:]] = value  # Remove 'template_' prefix
        
        success = notification_system.send_notification(
            recipient_type, recipient_id, notification_type,
            template_data, channels
        )
        
        if success:
            flash('Notification sent successfully!', 'success')
        else:
            flash('Failed to send notification.', 'error')
            
    except Exception as e:
        flash(f'Error sending notification: {str(e)}', 'error')
    
    return redirect(url_for('notification_management'))

@app.route('/profile/notifications')
@login_required
def notification_preferences():
    user_type = 'patient' if current_user.role == 'patient' else 'staff'
    
    preferences = notification_system.NotificationPreference.query.filter_by(
        user_id=current_user.id,
        user_type=user_type
    ).all()
    
    return render_template('notification_preferences.html', preferences=preferences)

@app.route('/profile/notifications/update', methods=['POST'])
@login_required
def update_notification_preferences():
    try:
        user_type = 'patient' if current_user.role == 'patient' else 'staff'
        
        for key, value in request.form.items():
            if key.startswith('pref_'):
                parts = key.split('_')
                if len(parts) >= 3:
                    notification_type = '_'.join(parts[1:-1])
                    channel = parts[-1]
                    
                    preference = notification_system.NotificationPreference.query.filter_by(
                        user_id=current_user.id,
                        user_type=user_type,
                        notification_type=notification_type
                    ).first()
                    
                    if not preference:
                        preference = notification_system.NotificationPreference(
                            user_id=current_user.id,
                            user_type=user_type,
                            notification_type=notification_type
                        )
                        db.session.add(preference)
                    
                    if channel == 'email':
                        preference.email_enabled = value == 'on'
                    elif channel == 'sms':
                        preference.sms_enabled = value == 'on'
                    elif channel == 'whatsapp':
                        preference.whatsapp_enabled = value == 'on'
                    elif channel == 'push':
                        preference.push_enabled = value == 'on'
        
        db.session.commit()
        flash('Notification preferences updated successfully!', 'success')
        
    except Exception as e:
        flash(f'Error updating preferences: {str(e)}', 'error')
        db.session.rollback()
    
    return redirect(url_for('notification_preferences'))

# =============== ENHANCED LOGIN WITH 2FA ===============
# Login route is already defined above with 2FA support

# Logout route is already defined above with enhanced functionality

# =============== STARTUP TASKS ===============
def start_background_tasks():
    """Start background tasks for backup and notifications"""
    # Start backup scheduler if initialized
    if backup_manager:
        backup_manager.start_scheduler_thread()
    
    # Notification scheduler is already started in init_notification_system

# =============== DASHBOARD API ENDPOINTS ===============
@app.route('/api/critical-alerts')
@login_required
def get_critical_alerts():
    """API endpoint to get critical alerts for dashboard"""
    try:
        # Get critical lab results
        critical_lab_results = db.session.query(
            LabResult.id,
            LabResult.result_value,
            LabResult.comments,
            LabResult.created_at,
            LabTest.test_name,
            WebPatient.first_name,
            WebPatient.last_name,
            WebPatient.patient_id
        ).join(LabOrder, LabResult.lab_order_id == LabOrder.id)\
         .join(LabTest, LabOrder.test_id == LabTest.id)\
         .join(WebPatient, LabOrder.patient_id == WebPatient.id)\
         .filter(LabResult.status == 'critical')\
         .order_by(LabResult.created_at.desc())\
         .limit(5).all()
        
        alerts = []
        for result in critical_lab_results:
            alerts.append({
                'id': result.id,
                'type': 'critical_lab_result',
                'message': f"Critical lab result for {result.first_name} {result.last_name} ({result.patient_id}) - {result.test_name}: {result.result_value}",
                'details': result.comments,
                'timestamp': result.created_at.isoformat(),
                'patient_id': result.patient_id,
                'test_name': result.test_name
            })
        
        return jsonify(alerts)
    
    except Exception as e:
        app.logger.error(f"Error fetching critical alerts: {str(e)}")
        return jsonify([]), 500

@app.route('/api/dashboard-stats')
@login_required
def get_dashboard_stats():
    """API endpoint to get dashboard statistics for real-time updates"""
    try:
        # Get current statistics
        total_patients = WebPatient.query.count()
        today = datetime.now().date()
        
        today_appointments = WebAppointment.query.filter(
            WebAppointment.appointment_date >= today,
            WebAppointment.appointment_date < today + timedelta(days=1)
        ).count()
        
        today_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
            Payment.payment_date >= today
        ).scalar() or 0
        
        pending_bills = Bill.query.filter(Bill.payment_status.in_(['pending', 'partial'])).count()
        
        # Bed occupancy
        total_beds = Bed.query.filter_by(is_active=True).count()
        occupied_beds = Bed.query.filter_by(is_occupied=True).count()
        occupancy_rate = (occupied_beds / total_beds * 100) if total_beds > 0 else 0
        
        # Medicine alerts
        low_stock_medicines = Medicine.query.filter(
            Medicine.stock_quantity <= Medicine.min_stock_level,
            Medicine.is_active == True
        ).count()
        
        # Critical alerts
        critical_lab_results = LabResult.query.filter_by(status='critical').count()
        
        stats = {
            'total_patients': total_patients,
            'today_appointments': today_appointments,
            'today_revenue': float(today_revenue),
            'pending_bills': pending_bills,
            'occupancy_rate': round(occupancy_rate, 1),
            'low_stock_medicines': low_stock_medicines,
            'critical_lab_results': critical_lab_results,
            'occupied_beds': occupied_beds,
            'total_beds': total_beds
        }
        
        return jsonify(stats)
    
    except Exception as e:
        app.logger.error(f"Error fetching dashboard stats: {str(e)}")
        return jsonify({}), 500

# Helper route for deleting consent forms
@app.route('/settings/delete_consent_form/<int:form_id>', methods=['POST'])
@login_required
def delete_consent_form(form_id):
    # Only allow admin users to delete consent forms
    if current_user.role != 'admin':
        flash('Access denied! Only administrators can delete consent forms.', 'error')
        return redirect(url_for('settings'))
    
    consent_form = ConsentForm.query.get_or_404(form_id)
    
    try:
        # Delete the file if it exists
        if consent_form.file_path and os.path.exists(consent_form.file_path):
            os.remove(consent_form.file_path)
        
        # Delete the database record
        db.session.delete(consent_form)
        db.session.commit()
        
        flash('Consent form deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting consent form: {str(e)}', 'error')
    
    return redirect(url_for('settings'))

# Route for adding consent forms
@app.route('/settings/add_consent_form', methods=['POST'])
@login_required
def add_consent_form():
    # Only allow admin users to add consent forms
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied!'}), 403
    
    try:
        name = request.form.get('name')
        form_type = request.form.get('form_type')
        description = request.form.get('description', '')
        is_required = 'is_required' in request.form
        
        if not name or not form_type:
            return jsonify({'success': False, 'message': 'Name and form type are required!'}), 400
        
        # Handle file upload
        file_path = None
        if 'consent_form' in request.files and request.files['consent_form'].filename:
            file_path = save_uploaded_file(request.files['consent_form'], 'uploads/templates')
            if not file_path:
                return jsonify({'success': False, 'message': 'Failed to upload consent form file!'}), 400
        
        # Create new consent form
        consent_form = ConsentForm(
            name=name,
            form_type=form_type,
            description=description,
            file_path=file_path,
            is_required=is_required
        )
        
        db.session.add(consent_form)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Consent form added successfully!',
            'consent_form': {
                'id': consent_form.id,
                'name': consent_form.name,
                'form_type': consent_form.form_type,
                'description': consent_form.description,
                'is_required': consent_form.is_required,
                'is_active': consent_form.is_active,
                'created_at': consent_form.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error adding consent form: {str(e)}'}), 500

# Route for updating consent forms
@app.route('/settings/update_consent_form/<int:form_id>', methods=['POST'])
@login_required
def update_consent_form(form_id):
    # Only allow admin users to update consent forms
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied!'}), 403
    
    try:
        consent_form = ConsentForm.query.get_or_404(form_id)
        
        name = request.form.get('name')
        form_type = request.form.get('form_type')
        description = request.form.get('description', '')
        is_required = 'is_required' in request.form
        is_active = 'is_active' in request.form
        
        if not name or not form_type:
            return jsonify({'success': False, 'message': 'Name and form type are required!'}), 400
        
        # Handle file upload
        if 'consent_form' in request.files and request.files['consent_form'].filename:
            # Delete old file if it exists
            if consent_form.file_path and os.path.exists(consent_form.file_path):
                os.remove(consent_form.file_path)
            
            # Upload new file
            file_path = save_uploaded_file(request.files['consent_form'], 'uploads/templates')
            if file_path:
                consent_form.file_path = file_path
        
        # Update consent form
        consent_form.name = name
        consent_form.form_type = form_type
        consent_form.description = description
        consent_form.is_required = is_required
        consent_form.is_active = is_active
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Consent form updated successfully!',
            'consent_form': {
                'id': consent_form.id,
                'name': consent_form.name,
                'form_type': consent_form.form_type,
                'description': consent_form.description,
                'is_required': consent_form.is_required,
                'is_active': consent_form.is_active,
                'updated_at': consent_form.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating consent form: {str(e)}'}), 500

# Appointment slot template routes
@app.route('/settings/add_slot_template', methods=['POST'])
@login_required
def add_slot_template():
    # Only allow admin users to add slot templates
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied!'}), 403
    
    try:
        name = request.form.get('name')
        duration = int(request.form.get('duration', 15))
        buffer_time = int(request.form.get('buffer_time', 5))
        description = request.form.get('description', '')
        
        if not name:
            return jsonify({'success': False, 'message': 'Template name is required!'}), 400
        
        # Create new slot template
        template = AppointmentSlotTemplate(
            name=name,
            duration=duration,
            buffer_time=buffer_time,
            description=description
        )
        
        db.session.add(template)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Slot template added successfully!',
            'template': {
                'id': template.id,
                'name': template.name,
                'duration': template.duration,
                'buffer_time': template.buffer_time,
                'description': template.description
            }
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error adding slot template: {str(e)}'}), 500

@app.route('/settings/update_slot_template/<int:template_id>', methods=['POST'])
@login_required
def update_slot_template(template_id):
    # Only allow admin users to update slot templates
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied!'}), 403
    
    try:
        template = AppointmentSlotTemplate.query.get_or_404(template_id)
        
        name = request.form.get('name')
        duration = int(request.form.get('duration', 15))
        buffer_time = int(request.form.get('buffer_time', 5))
        description = request.form.get('description', '')
        
        if not name:
            return jsonify({'success': False, 'message': 'Template name is required!'}), 400
        
        # Update template
        template.name = name
        template.duration = duration
        template.buffer_time = buffer_time
        template.description = description
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Slot template updated successfully!',
            'template': {
                'id': template.id,
                'name': template.name,
                'duration': template.duration,
                'buffer_time': template.buffer_time,
                'description': template.description
            }
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating slot template: {str(e)}'}), 500

@app.route('/settings/delete_slot_template/<int:template_id>', methods=['POST'])
@login_required
def delete_slot_template(template_id):
    # Only allow admin users to delete slot templates
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied!'}), 403
    
    try:
        template = AppointmentSlotTemplate.query.get_or_404(template_id)
        
        # Delete the template
        db.session.delete(template)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Slot template deleted successfully!'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting slot template: {str(e)}'}), 500

# =============== PAYMENT GATEWAY ROUTES ===============
@app.route('/payment/online/<int:bill_id>')
@login_required
def online_payment(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    return render_template('payment_gateway.html', bill=bill)

@app.route('/payment/process/<int:bill_id>', methods=['POST'])
@login_required
def process_online_payment(bill_id):
    try:
        bill = Bill.query.get_or_404(bill_id)
        payment_method = request.form.get('payment_method')
        amount = float(request.form.get('payment_amount', bill.balance_amount))
        
        # Process payment through gateway
        if payment_gateway:
            result = payment_gateway.process_payment(
                gateway_type=payment_method,
                amount=amount,
                currency='USD',
                description=f'Bill Payment - {bill.bill_number}',
                customer_email=bill.patient.email if bill.patient.email else None
            )
            
            if result.get('success'):
                # Record payment
                payment = Payment(
                    bill_id=bill.id,
                    amount=amount,
                    payment_method='online',
                    transaction_id=result.get('transaction_id'),
                    received_by=current_user.id
                )
                
                db.session.add(payment)
                
                # Update bill
                bill.paid_amount += amount
                bill.balance_amount = bill.total_amount - bill.paid_amount
                
                if bill.balance_amount <= 0:
                    bill.payment_status = 'paid'
                else:
                    bill.payment_status = 'partial'
                
                db.session.commit()
                
                flash('Payment processed successfully!', 'success')
                return redirect(url_for('view_invoice', bill_id=bill.id))
            else:
                flash(f'Payment failed: {result.get("error")}', 'danger')
        else:
            flash('Payment gateway not configured', 'warning')
        
        return redirect(url_for('online_payment', bill_id=bill_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing payment: {str(e)}', 'danger')
        return redirect(url_for('online_payment', bill_id=bill_id))

# =============== DOCUMENT MANAGEMENT ROUTES ===============
@app.route('/documents')
@login_required
def documents():
    if document_management:
        docs = document_management.list_documents(
            user_id=current_user.id,
            user_type=current_user.role
        )
        return render_template('documents.html', documents=docs)
    else:
        flash('Document management not available', 'warning')
        return redirect(url_for('dashboard'))

@app.route('/document/upload', methods=['POST'])
@login_required
def upload_document():
    try:
        if not document_management:
            return jsonify({'success': False, 'message': 'Document management not available'})
        
        file = request.files.get('file')
        document_type = request.form.get('document_type')
        related_to = request.form.get('related_to')
        related_id = request.form.get('related_id')
        
        if not file:
            return jsonify({'success': False, 'message': 'No file provided'})
        
        result = document_management.upload_document(
            file=file,
            document_type=document_type,
            uploaded_by=current_user.id,
            related_to=related_to,
            related_id=related_id
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# =============== EMERGENCY MANAGEMENT ROUTES ===============
@app.route('/emergency/dashboard')
@login_required
@role_required('admin', 'doctor', 'nurse')
def emergency_dashboard():
    if emergency_management:
        stats = emergency_management.get_emergency_stats()
        return render_template('emergency_dashboard.html', stats=stats)
    else:
        flash('Emergency management not available', 'warning')
        return redirect(url_for('dashboard'))

@app.route('/emergency/triage', methods=['POST'])
@login_required
@role_required('doctor', 'nurse')
def emergency_triage():
    try:
        if not emergency_management:
            return jsonify({'success': False, 'message': 'Emergency management not available'})
        
        patient_id = request.form.get('patient_id')
        triage_level = request.form.get('triage_level')
        symptoms = request.form.get('symptoms')
        
        result = emergency_management.create_triage(
            patient_id=patient_id,
            triage_level=triage_level,
            symptoms=symptoms,
            triaged_by=current_user.id
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/emergency/alert', methods=['POST'])
@login_required
@role_required('admin', 'doctor', 'nurse')
def emergency_alert():
    try:
        if not emergency_management:
            return jsonify({'success': False, 'message': 'Emergency management not available'})
        
        alert_type = request.form.get('alert_type')  # code_blue, code_red, etc.
        location = request.form.get('location')
        details = request.form.get('details')
        
        result = emergency_management.trigger_alert(
            alert_type=alert_type,
            location=location,
            details=details,
            triggered_by=current_user.id
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# =============== INVENTORY MANAGEMENT ROUTES ===============
@app.route('/inventory')
@login_required
@role_required('admin', 'pharmacist')
def inventory():
    if inventory_management:
        items = inventory_management.get_inventory_summary()
        return render_template('inventory.html', items=items)
    else:
        flash('Inventory management not available', 'warning')
        return redirect(url_for('dashboard'))

@app.route('/inventory/purchase-order', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'pharmacist')
def purchase_order():
    if request.method == 'POST':
        try:
            if not inventory_management:
                flash('Inventory management not available', 'warning')
                return redirect(url_for('inventory'))
            
            supplier_id = request.form.get('supplier_id')
            items = request.form.getlist('items')
            
            result = inventory_management.create_purchase_order(
                supplier_id=supplier_id,
                items=items,
                created_by=current_user.id
            )
            
            if result.get('success'):
                flash('Purchase order created successfully!', 'success')
            else:
                flash(f'Error: {result.get("message")}', 'danger')
            
            return redirect(url_for('inventory'))
            
        except Exception as e:
            flash(f'Error creating purchase order: {str(e)}', 'danger')
            return redirect(url_for('inventory'))
    
    suppliers = inventory_management.get_suppliers() if inventory_management else []
    return render_template('purchase_order.html', suppliers=suppliers)

# =============== QUALITY MANAGEMENT ROUTES ===============
@app.route('/quality/dashboard')
@login_required
@role_required('admin', 'doctor')
def quality_dashboard():
    if quality_management:
        metrics = quality_management.get_quality_metrics()
        return render_template('quality_dashboard.html', metrics=metrics)
    else:
        flash('Quality management not available', 'warning')
        return redirect(url_for('dashboard'))

@app.route('/quality/incident/report', methods=['GET', 'POST'])
@login_required
def report_incident():
    if request.method == 'POST':
        try:
            if not quality_management:
                flash('Quality management not available', 'warning')
                return redirect(url_for('dashboard'))
            
            incident_type = request.form.get('incident_type')
            description = request.form.get('description')
            severity = request.form.get('severity')
            location = request.form.get('location')
            
            result = quality_management.report_incident(
                incident_type=incident_type,
                description=description,
                severity=severity,
                location=location,
                reported_by=current_user.id
            )
            
            if result.get('success'):
                flash('Incident reported successfully!', 'success')
            else:
                flash(f'Error: {result.get("message")}', 'danger')
            
            return redirect(url_for('quality_dashboard'))
            
        except Exception as e:
            flash(f'Error reporting incident: {str(e)}', 'danger')
            return redirect(url_for('quality_dashboard'))
    
    return render_template('report_incident.html')

@app.route('/quality/feedback', methods=['POST'])
@login_required
def submit_feedback():
    try:
        if not quality_management:
            return jsonify({'success': False, 'message': 'Quality management not available'})
        
        patient_id = request.form.get('patient_id')
        rating = request.form.get('rating')
        feedback = request.form.get('feedback')
        category = request.form.get('category')
        
        result = quality_management.submit_feedback(
            patient_id=patient_id,
            rating=rating,
            feedback=feedback,
            category=category
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
# =============== REACT APP SERVING ROUTES ===============
@app.route('/react')
def serve_react_app():
    """Serve the React app"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """Catch-all route to serve React app"""
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    init_web_db()
    start_background_tasks()
    app.run(debug=True, host='0.0.0.0', port=5000)
