"""
Appointments routes for Hospital Management System
"""

from flask import render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta, date
import json

from app import db
from app.models.patient import WebPatient
from app.models.appointment import WebAppointment
from app.models.user import WebUser
from app.utils.language import get_text, get_language
from app.utils.decorators import role_required

# Import blueprint from __init__.py
from app.appointments import bp

# =============== APPOINTMENTS LIST ===============
@bp.route('/')
@login_required
def index():
    """Display all appointments"""
    
    date_filter = request.args.get('date', '')
    status_filter = request.args.get('status', '')
    doctor_filter = request.args.get('doctor', '')
    
    query = WebAppointment.query
    
    # Apply filters
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            next_day = filter_date + timedelta(days=1)
            query = query.filter(WebAppointment.appointment_date >= filter_date,
                                WebAppointment.appointment_date < next_day)
        except ValueError:
            flash('Invalid date format', 'error')
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    if doctor_filter:
        query = query.filter_by(doctor_id=doctor_filter)
    
    # Get doctors for filter dropdown
    doctors = WebUser.query.filter_by(role='doctor').all()
    
    appointments = query.order_by(WebAppointment.appointment_date).all()
    
    return render_template('appointments.html',
                         appointments=appointments,
                         doctors=doctors,
                         date_filter=date_filter,
                         status_filter=status_filter,
                         doctor_filter=doctor_filter)

# =============== ADD APPOINTMENT ===============
@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add a new appointment"""
    
    if request.method == 'POST':
        try:
            appointment_date = datetime.strptime(
                f"{request.form.get('appointment_date')} {request.form.get('appointment_time')}",
                '%Y-%m-%d %H:%M'
            )
            
            appointment = WebAppointment(
                patient_id=request.form.get('patient_id'),
                doctor_id=request.form.get('doctor_id'),
                appointment_date=appointment_date,
                appointment_type=request.form.get('appointment_type'),
                notes=request.form.get('notes'),
                status='scheduled'
            )
            
            db.session.add(appointment)
            db.session.commit()
            
            flash('Appointment scheduled successfully!', 'success')
            return redirect(url_for('appointments.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error scheduling appointment: {str(e)}', 'error')
    
    # Get patients and doctors for dropdowns
    patients = WebPatient.query.all()
    doctors = WebUser.query.filter_by(role='doctor').all()
    
    return render_template('add_appointment.html', patients=patients, doctors=doctors)

# =============== APPOINTMENT DETAILS ===============
@bp.route('/details/<int:appointment_id>')
@login_required
def appointment_details(appointment_id):
    """Display appointment details"""
    
    appointment = WebAppointment.query.get_or_404(appointment_id)
    
    return render_template('appointment_details.html', appointment=appointment)

# =============== EDIT APPOINTMENT ===============
@bp.route('/edit/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
def edit_appointment(appointment_id):
    """Edit appointment"""
    
    appointment = WebAppointment.query.get_or_404(appointment_id)
    
    if request.method == 'POST':
        try:
            appointment_date = datetime.strptime(
                f"{request.form.get('appointment_date')} {request.form.get('appointment_time')}",
                '%Y-%m-%d %H:%M'
            )
            
            appointment.patient_id = request.form.get('patient_id', appointment.patient_id)
            appointment.doctor_id = request.form.get('doctor_id', appointment.doctor_id)
            appointment.appointment_date = appointment_date
            appointment.appointment_type = request.form.get('appointment_type', appointment.appointment_type)
            appointment.notes = request.form.get('notes', appointment.notes)
            
            db.session.commit()
            
            flash('Appointment updated successfully!', 'success')
            return redirect(url_for('appointments.appointment_details', appointment_id=appointment.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating appointment: {str(e)}', 'error')
    
    # Get patients and doctors for dropdowns
    patients = WebPatient.query.all()
    doctors = WebUser.query.filter_by(role='doctor').all()
    
    return render_template('edit_appointment.html', 
                         appointment=appointment, 
                         patients=patients, 
                         doctors=doctors)

# =============== CANCEL APPOINTMENT ===============
@bp.route('/cancel/<int:appointment_id>', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    """Cancel appointment"""
    
    appointment = WebAppointment.query.get_or_404(appointment_id)
    appointment.status = 'cancelled'
    appointment.cancellation_reason = request.form.get('reason')
    appointment.cancelled_at = datetime.now()
    
    db.session.commit()
    
    flash('Appointment cancelled successfully!', 'success')
    return redirect(url_for('appointments.index'))

# =============== TODAY'S APPOINTMENTS ===============
@bp.route('/today')
@login_required
def todays_appointments():
    """Display today's appointments"""
    
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    appointments = WebAppointment.query.filter(
        WebAppointment.appointment_date >= today,
        WebAppointment.appointment_date < tomorrow
    ).order_by(WebAppointment.appointment_date).all()
    
    return render_template('todays_appointments.html', appointments=appointments)

# =============== DOCTOR'S APPOINTMENTS ===============
@bp.route('/doctor/<int:doctor_id>')
@login_required
def doctor_appointments(doctor_id):
    """Display appointments for a specific doctor"""
    
    doctor = WebUser.query.get_or_404(doctor_id)
    
    date_filter = request.args.get('date', '')
    
    query = WebAppointment.query.filter_by(doctor_id=doctor_id)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            next_day = filter_date + timedelta(days=1)
            query = query.filter(WebAppointment.appointment_date >= filter_date,
                                WebAppointment.appointment_date < next_day)
        except ValueError:
            flash('Invalid date format', 'error')
    
    appointments = query.order_by(WebAppointment.appointment_date).all()
    
    return render_template('doctor_appointments.html',
                         doctor=doctor,
                         appointments=appointments,
                         date_filter=date_filter)

# =============== TELEMEDICINE ===============
@bp.route('/telemedicine')
@login_required
def telemedicine():
    """Telemedicine appointments"""
    telemedicine_appointments = WebAppointment.query.filter_by(appointment_type='telemedicine').all()
    return render_template('telemedicine.html', appointments=telemedicine_appointments)

# =============== API ENDPOINTS ===============
@bp.route('/api/available-slots')
@login_required
def get_available_slots():
    """API endpoint to get available appointment slots"""
    
    doctor_id = request.args.get('doctor_id', type=int)
    date_str = request.args.get('date')
    
    if not doctor_id or not date_str:
        return jsonify({'error': 'Missing parameters'})
    
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'})
    
    # Get existing appointments for the doctor on the selected date
    start_of_day = datetime.combine(selected_date, datetime.min.time())
    end_of_day = start_of_day + timedelta(days=1)
    
    existing_appointments = WebAppointment.query.filter(
        WebAppointment.doctor_id == doctor_id,
        WebAppointment.appointment_date >= start_of_day,
        WebAppointment.appointment_date < end_of_day,
        WebAppointment.status.in_(['scheduled', 'confirmed'])
    ).all()
    
    # Generate time slots (9 AM to 5 PM, 30-minute intervals)
    available_slots = []
    start_time = 9  # 9 AM
    end_time = 17   # 5 PM
    
    for hour in range(start_time, end_time):
        for minute in [0, 30]:
            slot_time = datetime.combine(selected_date, datetime.min.time()).replace(hour=hour, minute=minute)
            
            # Check if slot is available
            is_available = True
            for apt in existing_appointments:
                apt_time = apt.appointment_date
                if abs((slot_time - apt_time).total_seconds()) < 30 * 60:  # Within 30 minutes
                    is_available = False
                    break
            
            if is_available:
                available_slots.append({
                    'time': slot_time.strftime('%H:%M'),
                    'display': slot_time.strftime('%I:%M %p')
                })
    
    return jsonify(available_slots)

@bp.route('/api/search')
@login_required
def search_appointments():
    """API endpoint to search appointments"""
    
    query = request.args.get('q', '')
    
    if len(query) < 2:
        return jsonify([])
    
    appointments = db.session.query(
        WebAppointment, WebPatient, WebUser
    ).join(WebPatient, WebAppointment.patient_id == WebPatient.id)\
     .join(WebUser, WebAppointment.doctor_id == WebUser.id)\
     .filter(
         WebPatient.first_name.contains(query) |
         WebPatient.last_name.contains(query) |
         WebPatient.patient_id.contains(query)
     ).limit(20).all()
    
    results = []
    for appointment, patient, doctor in appointments:
        results.append({
            'id': appointment.id,
            'patient_name': f"{patient.first_name} {patient.last_name}",
            'patient_id': patient.patient_id,
            'doctor_name': doctor.full_name,
            'date': appointment.appointment_date.strftime('%Y-%m-%d'),
            'time': appointment.appointment_date.strftime('%H:%M'),
            'status': appointment.status
        })
    
    return jsonify(results)