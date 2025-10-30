"""
Clinical routes for Hospital Management System
"""

from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from datetime import datetime

from app import db
from . import bp
from app.models.patient import WebPatient
from app.models.appointment import WebAppointment
from app.models.user import WebUser

# Temporary import to fix circular dependency
# from app.models.clinical import LabOrder, ImagingOrder, Medicine, LabResult

@bp.route('/patient-ehr/<int:patient_id>')
@login_required
def patient_ehr(patient_id):
    """Patient Electronic Health Records"""
    patient = WebPatient.query.get_or_404(patient_id)
    if not patient:
        flash('Patient not found!', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get medical records for this patient
    medical_records = db.session.query('MedicalRecord').filter_by(patient_id=patient.id).order_by(MedicalRecord.visit_date.desc()).all()
    
    return render_template('ehr.html', patient=patient, medical_records=medical_records)

# =============== LAB ORDERS ===============
@bp.route('/lab-orders')
@login_required
def lab_orders():
    """Lab orders management"""
    from app.models.clinical import LabOrder
    lab_orders = LabOrder.query.order_by(LabOrder.order_date.desc()).all()
    return render_template('lab_orders.html', lab_orders=lab_orders)

# =============== IMAGING ORDERS ===============
@bp.route('/imaging-orders')
@login_required
def imaging_orders():
    """Imaging orders management"""
    from app.models.clinical import ImagingOrder
    imaging_orders = ImagingOrder.query.order_by(ImagingOrder.order_date.desc()).all()
    return render_template('imaging_orders.html', imaging_orders=imaging_orders)

# =============== ADMISSIONS ===============
@bp.route('/admissions')
@login_required
def admissions():
    """Patient admissions management"""
    from app.models.admission import Admission
    admissions = Admission.query.order_by(Admission.admission_date.desc()).all()
    return render_template('admissions.html', admissions=admissions)
