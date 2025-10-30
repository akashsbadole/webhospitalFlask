"""
Patients routes for Hospital Management System
"""

from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime

from app import db
from . import bp
from app.models.patient import WebPatient
from app.models.appointment import WebAppointment
from app.models.attendance import WebAttendance, WebEnquiry
from app.models.admission import Admission
from app.models.billing import Bill, Payment
from app.models.clinical import LabOrder, ImagingOrder, LabResult
from app.models.clinical import LabTest
from app.models.pharmacy import Medicine
from app.models.admin import Bed, Ward
from app.utils.language import get_text, get_language
from app.utils.decorators import role_required

# =============== PATIENT MANAGEMENT ROUTES ===============
@bp.route('/')
def index():
    """Display all patients"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = WebPatient.query
    if search:
        query = query.filter(
            (WebPatient.first_name.contains(search)) |
            (WebPatient.last_name.contains(search)) |
            (WebPatient.patient_id.contains(search)) |
            (WebPatient.email.contains(search)) |
            (WebPatient.phone.contains(search))
        )
    
    patients = query.order_by(WebPatient.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('patients.html', patients=patients, search=search)

@bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'receptionist')
def add():
    """Add new patient"""
    if request.method == 'POST':
        # Generate unique patient ID
        from app.utils.helpers import generate_patient_id
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
            city=request.form.get('city'),
            state=request.form.get('state'),
            zip_code=request.form.get('zip_code'),
            country=request.form.get('country'),
            emergency_contact=request.form.get('emergency_contact'),
            emergency_phone=request.form.get('emergency_phone'),
            blood_group=request.form.get('blood_group'),
            allergies=request.form.get('allergies'),
            medical_history=request.form.get('medical_history'),
            insurance_provider=request.form.get('insurance_provider'),
            insurance_number=request.form.get('insurance_number'),
            insurance_expiry=datetime.strptime(request.form['insurance_expiry'], '%Y-%m-%d').date() if request.form.get('insurance_expiry') else None,
            id_proof_type=request.form.get('id_proof_type'),
            id_proof_number=request.form.get('id_proof_number'),
            marital_status=request.form.get('marital_status'),
            occupation=request.form.get('occupation')
        )
        
        db.session.add(patient)
        db.session.commit()
        flash('Patient added successfully!', 'success')
        return redirect(url_for('patients.index'))
    
    return render_template('add_patient.html')

@bp.route('/edit/<int:patient_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'receptionist')
def edit_patient(patient_id):
    """Edit patient details"""
    patient = WebPatient.query.get_or_404(patient_id)
    
    if request.method == 'POST':
        patient.first_name = request.form['first_name']
        patient.last_name = request.form['last_name']
        patient.email = request.form.get('email')
        patient.phone = request.form['phone']
        patient.date_of_birth = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d').date() if request.form.get('date_of_birth') else None
        patient.gender = request.form.get('gender')
        patient.address = request.form.get('address')
        patient.city = request.form.get('city')
        patient.state = request.form.get('state')
        patient.zip_code = request.form.get('zip_code')
        patient.country = request.form.get('country')
        patient.emergency_contact = request.form.get('emergency_contact')
        patient.emergency_phone = request.form.get('emergency_phone')
        patient.blood_group = request.form.get('blood_group')
        patient.allergies = request.form.get('allergies')
        patient.medical_history = request.form.get('medical_history')
        patient.insurance_provider = request.form.get('insurance_provider')
        patient.insurance_number = request.form.get('insurance_number')
        patient.insurance_expiry = datetime.strptime(request.form['insurance_expiry'], '%Y-%m-%d').date() if request.form.get('insurance_expiry') else None
        patient.id_proof_type = request.form.get('id_proof_type')
        patient.id_proof_number = request.form.get('id_proof_number')
        patient.marital_status = request.form.get('marital_status')
        patient.occupation = request.form.get('occupation')
        patient.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Patient updated successfully!', 'success')
        return redirect(url_for('patients.index'))
    
    return render_template('edit_patient.html', patient=patient)

@bp.route('/view/<int:patient_id>')
@login_required
def view_patient(patient_id):
    """View patient details"""
    patient = WebPatient.query.get_or_404(patient_id)
    return render_template('view_patient.html', patient=patient)

@bp.route('/delete/<int:patient_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_patient(patient_id):
    """Delete patient"""
    patient = WebPatient.query.get_or_404(patient_id)
    
    # Check if patient has active appointments or bills
    has_appointments = WebAppointment.query.filter_by(patient_id=patient_id).first()
    has_bills = Bill.query.filter_by(patient_id=patient_id).first()
    
    if has_appointments or has_bills:
        flash('Cannot delete patient with active appointments or bills!', 'error')
        return redirect(url_for('patients.index'))
    
    db.session.delete(patient)
    db.session.commit()
    flash('Patient deleted successfully!', 'success')
    return redirect(url_for('patients.index'))
