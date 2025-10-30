"""
Main routes for Hospital Management System - Dashboard, Home
"""

from flask import render_template, request, redirect, url_for, flash, session, jsonify, make_response
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import calendar
from flask import Blueprint

from app import db
from app.models.patient import WebPatient
from app.models.appointment import WebAppointment
from app.models.attendance import WebAttendance, WebEnquiry
from app.models.admission import Admission
from app.models.billing import Bill, Payment
from app.models.clinical import LabOrder, ImagingOrder, LabResult, LabTest
from app.models.pharmacy import Medicine
from app.models.admin import Bed, Ward
from app.utils.language import get_text, get_language
from app.utils.decorators import role_required

# Import the blueprint from the __init__.py file
from . import bp

# =============== HOME/INDEX ROUTES ===============
@bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

# =============== DASHBOARD ROUTE ===============
@bp.route('/dashboard')
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
        Medicine.stock_quantity <= Medicine.reorder_level,
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

# =============== API ENDPOINTS FOR REAL-TIME UPDATES ===============
@bp.route('/api/critical-alerts')
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
        return jsonify([]), 500

@bp.route('/api/dashboard-stats')
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
            Medicine.stock_quantity <= Medicine.reorder_level,
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
            'occupied_beds': occupied_beds,
            'total_beds': total_beds,
            'low_stock_medicines': low_stock_medicines,
            'critical_lab_results': critical_lab_results
        }
        
        return jsonify(stats)
    
    except Exception as e:
        return jsonify({}), 500

# =============== PATIENT CHECK-IN/CHECK-OUT WORKFLOW ===============
@bp.route('/checkin')
@login_required
def patient_checkin():
    today = datetime.now().date()
    
    # Get today's appointments
    appointments = WebAppointment.query.filter(
        WebAppointment.appointment_date >= today,
        WebAppointment.appointment_date < today + timedelta(days=1),
        WebAppointment.status.in_(['scheduled', 'checked_in'])
    ).order_by(WebAppointment.appointment_date).all()
    
    return render_template('patient_checkin.html', appointments=appointments)

@bp.route('/checkin/<int:appointment_id>', methods=['POST'])
@login_required
def check_in_patient(appointment_id):
    from app.utils.decorators import role_required
    if not current_user.has_any_role('admin', 'receptionist', 'nurse'):
        flash('Access denied! You do not have permission to check in patients.', 'error')
        return redirect(url_for('main.dashboard'))
    
    appointment = WebAppointment.query.get_or_404(appointment_id)
    appointment.status = 'checked_in'
    appointment.check_in_time = datetime.now()
    
    db.session.commit()
    flash(f'Patient {appointment.patient.first_name} {appointment.patient.last_name} checked in successfully!', 'success')
    return redirect(url_for('main.patient_checkin'))

# =============== DOCTOR QUEUE ===============
@bp.route('/doctor/queue')
@login_required
def doctor_queue():
    if not current_user.has_role('doctor'):
        flash('Access denied! Only doctors can access this page.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get checked-in patients for current doctor
    checked_in_appointments = WebAppointment.query.filter(
        WebAppointment.doctor_id == current_user.id,
        WebAppointment.status == 'checked_in'
    ).order_by(WebAppointment.check_in_time).all()
    
    return render_template('doctor_queue.html', appointments=checked_in_appointments)

@bp.route('/consultation/<int:appointment_id>')
@login_required
def start_consultation(appointment_id):
    if not current_user.has_role('doctor'):
        flash('Access denied! Only doctors can start consultations.', 'error')
        return redirect(url_for('main.dashboard'))
    
    appointment = WebAppointment.query.get_or_404(appointment_id)
    
    # Update appointment status
    appointment.status = 'in_consultation'
    appointment.consultation_start = datetime.now()
    db.session.commit()
    
    # Redirect to patient EHR
    return redirect(url_for('clinical.patient_ehr', patient_id=appointment.patient_id))

@bp.route('/complete_consultation/<int:appointment_id>', methods=['POST'])
@login_required
def complete_consultation(appointment_id):
    if not current_user.has_role('doctor'):
        flash('Access denied! Only doctors can complete consultations.', 'error')
        return redirect(url_for('main.dashboard'))
    
    appointment = WebAppointment.query.get_or_404(appointment_id)
    appointment.status = 'completed'
    appointment.consultation_end = datetime.now()
    
    db.session.commit()
    flash('Consultation completed successfully!', 'success')
    return redirect(url_for('main.doctor_queue'))

# =============== ENQUIRIES ===============
@bp.route('/enquiries')
@login_required
def enquiries():
    """Display enquiries"""
    from app.models.attendance import WebEnquiry
    enquiries = WebEnquiry.query.order_by(WebEnquiry.created_at.desc()).all()
    return render_template('enquiries.html', enquiries=enquiries)

# =============== LANGUAGE SETTINGS ===============
@bp.route('/set-language/<language>')
def set_language(language):
    """Set user language preference"""
    session['language'] = language
    return redirect(request.referrer or url_for('main.index'))
