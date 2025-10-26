from flask import Blueprint, jsonify, request, session
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import jwt
import os

# Create Blueprint for API routes
api_bp = Blueprint('api', __name__)

# Secret key for JWT
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Helper function to generate JWT token
def generate_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

# Authentication endpoints
@api_bp.route('/auth/login', methods=['POST'])
def api_login():
    # Import here to avoid circular import
    from web_app import WebUser, db
    
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    tenant_id = data.get('tenant')
    
    if not all([username, password, tenant_id]):
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Set tenant context
    session['tenant_id'] = tenant_id
    
    # Query user with tenant context
    user = WebUser.query.filter_by(username=username).first()
    
    if user and check_password_hash(user.password_hash, password):
        # Generate JWT token
        token = generate_token(user.id)
        
        # Store token in session for Flask-Login compatibility
        session['token'] = token
        
        return jsonify({
            'token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'email': user.email,
                'role': user.role
            }
        }), 200
    else:
        return jsonify({'message': 'Invalid credentials'}), 401

@api_bp.route('/auth/logout', methods=['POST'])
@login_required
def api_logout():
    session.pop('token', None)
    return jsonify({'message': 'Logged out successfully'}), 200

@api_bp.route('/auth/current_user', methods=['GET'])
@login_required
def api_current_user():
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'full_name': current_user.full_name,
        'email': current_user.email,
        'role': current_user.role
    })

# Tenant endpoints
@api_bp.route('/tenants', methods=['GET'])
def api_tenants():
    # Import here to avoid circular import
    from web_app import Tenant
    
    tenants = Tenant.query.all()
    return jsonify([{
        'id': tenant.id,
        'name': tenant.name,
        'code': tenant.tenant_code,
        'is_active': tenant.is_active
    } for tenant in tenants])

# Dashboard endpoints
@api_bp.route('/dashboard', methods=['GET'])
@login_required
def api_dashboard():
    # Import here to avoid circular import
    from web_app import WebPatient, WebAppointment, WebUser, Payment, Bed, Medicine, LabResult
    
    try:
        # Get dashboard statistics
        total_patients = WebPatient.query.count()
        today = datetime.now().date()
        
        today_appointments = WebAppointment.query.filter(
            WebAppointment.appointment_date >= today,
            WebAppointment.appointment_date < today + timedelta(days=1)
        ).count()
        
        total_staff = WebUser.query.filter(WebUser.role != 'patient').count()
        
        # Calculate today's revenue
        today_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
            Payment.payment_date >= today
        ).scalar() or 0
        
        # Calculate occupancy rate
        total_beds = Bed.query.filter_by(is_active=True).count()
        occupied_beds = Bed.query.filter_by(is_occupied=True).count()
        occupancy_rate = (occupied_beds / total_beds * 100) if total_beds > 0 else 0
        
        # Count pending bills
        from web_app import Bill
        pending_bills = Bill.query.filter(Bill.payment_status.in_(['pending', 'partial'])).count()
        
        # Get recent patients
        recent_patients = WebPatient.query.order_by(WebPatient.created_at.desc()).limit(5).all()
        
        # Get today's appointments
        today_appointments_list = WebAppointment.query.filter(
            WebAppointment.appointment_date >= today,
            WebAppointment.appointment_date < today + timedelta(days=1)
        ).order_by(WebAppointment.appointment_date).limit(5).all()
        
        # Count critical lab results
        critical_lab_results = LabResult.query.filter_by(status='critical').count()
        
        return jsonify({
            'stats': {
                'totalPatients': total_patients,
                'todayAppointments': today_appointments,
                'totalStaff': total_staff,
                'todayRevenue': float(today_revenue),
                'occupancyRate': round(occupancy_rate, 1),
                'pendingBills': pending_bills,
                'criticalLabResults': critical_lab_results,
                'occupiedBeds': occupied_beds,
                'totalBeds': total_beds
            },
            'recentPatients': [{
                'id': p.id,
                'name': f"{p.first_name} {p.last_name}",
                'patient_id': p.patient_id,
                'phone': p.phone,
                'created_at': p.created_at.isoformat() if p.created_at else None
            } for p in recent_patients],
            'todayAppointments': [{
                'id': a.id,
                'patient_name': f"{a.patient.first_name} {a.patient.last_name}" if a.patient else 'Unknown',
                'doctor_name': a.doctor.full_name if a.doctor else 'Unknown',
                'appointment_date': a.appointment_date.isoformat() if a.appointment_date else None,
                'status': a.status,
                'appointment_type': a.appointment_type
            } for a in today_appointments_list]
        }), 200
    except Exception as e:
        return jsonify({'message': f'Error fetching dashboard data: {str(e)}'}), 500

# Patient endpoints
@api_bp.route('/patients', methods=['GET'])
@login_required
def api_patients():
    # Import here to avoid circular import
    from web_app import WebPatient
    
    try:
        patients = WebPatient.query.all()
        return jsonify([{
            'id': p.id,
            'patient_id': p.patient_id,
            'first_name': p.first_name,
            'last_name': p.last_name,
            'name': f"{p.first_name} {p.last_name}",
            'email': p.email,
            'phone': p.phone,
            'date_of_birth': p.date_of_birth.isoformat() if p.date_of_birth else None,
            'gender': p.gender,
            'address': p.address,
            'blood_group': p.blood_group,
            'allergies': p.allergies,
            'medical_history': p.medical_history,
            'created_at': p.created_at.isoformat() if p.created_at else None
        } for p in patients]), 200
    except Exception as e:
        return jsonify({'message': f'Error fetching patients: {str(e)}'}), 500

@api_bp.route('/patients', methods=['POST'])
@login_required
def api_create_patient():
    # Import here to avoid circular import
    from web_app import WebPatient, db, get_tenant, generate_patient_id
    
    try:
        data = request.get_json()
        tenant = get_tenant()
        
        patient = WebPatient(
            tenant_id=tenant.id if tenant else None,
            patient_id=generate_patient_id(tenant.id if tenant else None),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            email=data.get('email'),
            phone=data.get('phone'),
            date_of_birth=datetime.strptime(data.get('date_of_birth'), '%Y-%m-%d').date() if data.get('date_of_birth') else None,
            gender=data.get('gender'),
            address=data.get('address'),
            emergency_contact=data.get('emergency_contact'),
            emergency_phone=data.get('emergency_phone'),
            blood_group=data.get('blood_group'),
            allergies=data.get('allergies'),
            medical_history=data.get('medical_history')
        )
        
        db.session.add(patient)
        db.session.commit()
        
        return jsonify({
            'message': 'Patient created successfully',
            'patient_id': patient.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error creating patient: {str(e)}'}), 500

@api_bp.route('/patients/<int:patient_id>', methods=['GET'])
@login_required
def api_get_patient(patient_id):
    # Import here to avoid circular import
    from web_app import WebPatient
    
    try:
        patient = WebPatient.query.get_or_404(patient_id)
        return jsonify({
            'id': patient.id,
            'patient_id': patient.patient_id,
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'name': f"{patient.first_name} {patient.last_name}",
            'email': patient.email,
            'phone': patient.phone,
            'date_of_birth': patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            'gender': patient.gender,
            'address': patient.address,
            'emergency_contact': patient.emergency_contact,
            'emergency_phone': patient.emergency_phone,
            'blood_group': patient.blood_group,
            'allergies': patient.allergies,
            'medical_history': patient.medical_history,
            'created_at': patient.created_at.isoformat() if patient.created_at else None
        }), 200
    except Exception as e:
        return jsonify({'message': f'Error fetching patient: {str(e)}'}), 500

@api_bp.route('/patients/<int:patient_id>', methods=['PUT'])
@login_required
def api_update_patient(patient_id):
    # Import here to avoid circular import
    from web_app import WebPatient, db
    
    try:
        patient = WebPatient.query.get_or_404(patient_id)
        data = request.get_json()
        
        patient.first_name = data.get('first_name', patient.first_name)
        patient.last_name = data.get('last_name', patient.last_name)
        patient.email = data.get('email', patient.email)
        patient.phone = data.get('phone', patient.phone)
        patient.date_of_birth = datetime.strptime(data.get('date_of_birth'), '%Y-%m-%d').date() if data.get('date_of_birth') else patient.date_of_birth
        patient.gender = data.get('gender', patient.gender)
        patient.address = data.get('address', patient.address)
        patient.emergency_contact = data.get('emergency_contact', patient.emergency_contact)
        patient.emergency_phone = data.get('emergency_phone', patient.emergency_phone)
        patient.blood_group = data.get('blood_group', patient.blood_group)
        patient.allergies = data.get('allergies', patient.allergies)
        patient.medical_history = data.get('medical_history', patient.medical_history)
        
        db.session.commit()
        
        return jsonify({'message': 'Patient updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error updating patient: {str(e)}'}), 500

@api_bp.route('/patients/<int:patient_id>', methods=['DELETE'])
@login_required
def api_delete_patient(patient_id):
    # Import here to avoid circular import
    from web_app import WebPatient, db
    
    try:
        patient = WebPatient.query.get_or_404(patient_id)
        db.session.delete(patient)
        db.session.commit()
        
        return jsonify({'message': 'Patient deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error deleting patient: {str(e)}'}), 500

# Appointment endpoints
@api_bp.route('/appointments', methods=['GET'])
@login_required
def api_appointments():
    # Import here to avoid circular import
    from web_app import WebAppointment
    
    try:
        appointments = WebAppointment.query.all()
        return jsonify([{
            'id': a.id,
            'patient_id': a.patient_id,
            'patient_name': f"{a.patient.first_name} {a.patient.last_name}" if a.patient else 'Unknown',
            'doctor_id': a.doctor_id,
            'doctor_name': a.doctor.full_name if a.doctor else 'Unknown',
            'appointment_date': a.appointment_date.isoformat() if a.appointment_date else None,
            'appointment_type': a.appointment_type,
            'status': a.status,
            'notes': a.notes,
            'created_at': a.created_at.isoformat() if a.created_at else None
        } for a in appointments]), 200
    except Exception as e:
        return jsonify({'message': f'Error fetching appointments: {str(e)}'}), 500

@api_bp.route('/appointments', methods=['POST'])
@login_required
def api_create_appointment():
    # Import here to avoid circular import
    from web_app import WebAppointment, db, get_tenant
    
    try:
        data = request.get_json()
        tenant = get_tenant()
        
        appointment = WebAppointment(
            tenant_id=tenant.id if tenant else None,
            patient_id=data.get('patient_id'),
            doctor_id=data.get('doctor_id'),
            appointment_date=datetime.strptime(data.get('appointment_date'), '%Y-%m-%d %H:%M'),
            appointment_type=data.get('appointment_type'),
            status=data.get('status', 'scheduled'),
            notes=data.get('notes')
        )
        
        # Generate meeting link for telemedicine
        if appointment.appointment_type == 'telemedicine':
            appointment.meeting_link = f"https://meet.google.com/new"
        
        db.session.add(appointment)
        db.session.commit()
        
        return jsonify({
            'message': 'Appointment created successfully',
            'appointment_id': appointment.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error creating appointment: {str(e)}'}), 500

@api_bp.route('/appointments/<int:appointment_id>', methods=['GET'])
@login_required
def api_get_appointment(appointment_id):
    # Import here to avoid circular import
    from web_app import WebAppointment
    
    try:
        appointment = WebAppointment.query.get_or_404(appointment_id)
        return jsonify({
            'id': appointment.id,
            'patient_id': appointment.patient_id,
            'patient_name': f"{appointment.patient.first_name} {appointment.patient.last_name}" if appointment.patient else 'Unknown',
            'doctor_id': appointment.doctor_id,
            'doctor_name': appointment.doctor.full_name if appointment.doctor else 'Unknown',
            'appointment_date': appointment.appointment_date.isoformat() if appointment.appointment_date else None,
            'appointment_type': appointment.appointment_type,
            'status': appointment.status,
            'notes': appointment.notes,
            'meeting_link': appointment.meeting_link,
            'created_at': appointment.created_at.isoformat() if appointment.created_at else None
        }), 200
    except Exception as e:
        return jsonify({'message': f'Error fetching appointment: {str(e)}'}), 500

@api_bp.route('/appointments/<int:appointment_id>', methods=['PUT'])
@login_required
def api_update_appointment(appointment_id):
    # Import here to avoid circular import
    from web_app import WebAppointment, db
    
    try:
        appointment = WebAppointment.query.get_or_404(appointment_id)
        data = request.get_json()
        
        appointment.patient_id = data.get('patient_id', appointment.patient_id)
        appointment.doctor_id = data.get('doctor_id', appointment.doctor_id)
        
        if data.get('appointment_date'):
            appointment.appointment_date = datetime.strptime(data.get('appointment_date'), '%Y-%m-%d %H:%M')
        
        appointment.appointment_type = data.get('appointment_type', appointment.appointment_type)
        appointment.status = data.get('status', appointment.status)
        appointment.notes = data.get('notes', appointment.notes)
        
        db.session.commit()
        
        return jsonify({'message': 'Appointment updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error updating appointment: {str(e)}'}), 500

@api_bp.route('/appointments/<int:appointment_id>', methods=['DELETE'])
@login_required
def api_delete_appointment(appointment_id):
    # Import here to avoid circular import
    from web_app import WebAppointment, db
    
    try:
        appointment = WebAppointment.query.get_or_404(appointment_id)
        db.session.delete(appointment)
        db.session.commit()
        
        return jsonify({'message': 'Appointment deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error deleting appointment: {str(e)}'}), 500

@api_bp.route('/appointments/<int:appointment_id>/status', methods=['PUT'])
@login_required
def api_update_appointment_status(appointment_id):
    # Import here to avoid circular import
    from web_app import WebAppointment, db
    
    try:
        appointment = WebAppointment.query.get_or_404(appointment_id)
        data = request.get_json()
        
        appointment.status = data.get('status', appointment.status)
        
        db.session.commit()
        
        return jsonify({'message': 'Appointment status updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error updating appointment status: {str(e)}'}), 500

# Doctor endpoints
@api_bp.route('/doctors', methods=['GET'])
@login_required
def api_doctors():
    # Import here to avoid circular import
    from web_app import WebUser
    
    try:
        doctors = WebUser.query.filter_by(role='doctor').all()
        return jsonify([{
            'id': d.id,
            'name': d.full_name,
            'specialization': getattr(d, 'specialization', 'General Practitioner'),
            'email': d.email,
            'phone': getattr(d, 'phone', ''),
            'department': getattr(d, 'department', '')
        } for d in doctors]), 200
    except Exception as e:
        return jsonify({'message': f'Error fetching doctors: {str(e)}'}), 500

# Billing endpoints
@api_bp.route('/billing', methods=['GET'])
@login_required
def api_billing():
    # Import here to avoid circular import
    from web_app import Bill, Payment, db
    
    try:
        bills = Bill.query.all()
        payments = Payment.query.all()
        
        return jsonify({
            'bills': [{
                'id': bill.id,
                'patient_id': bill.patient_id,
                'patient_name': f"{bill.patient.first_name} {bill.patient.last_name}" if bill.patient else 'Unknown',
                'total_amount': float(bill.total_amount),
                'paid_amount': float(bill.paid_amount or 0),
                'balance': float(bill.total_amount - (bill.paid_amount or 0)),
                'payment_status': bill.payment_status,
                'bill_date': bill.bill_date.isoformat() if bill.bill_date else None,
                'due_date': bill.due_date.isoformat() if bill.due_date else None
            } for bill in bills],
            'payments': [{
                'id': payment.id,
                'bill_id': payment.bill_id,
                'patient_name': f"{payment.bill.patient.first_name} {payment.bill.patient.last_name}" if payment.bill and payment.bill.patient else 'Unknown',
                'amount': float(payment.amount),
                'payment_method': payment.payment_method,
                'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
                'status': payment.status
            } for payment in payments]
        }), 200
    except Exception as e:
        return jsonify({'message': f'Error fetching billing data: {str(e)}'}), 500

# Pharmacy endpoints
@api_bp.route('/pharmacy/medicines', methods=['GET'])
@login_required
def api_medicines():
    # Import here to avoid circular import
    from web_app import Medicine
    
    try:
        medicines = Medicine.query.all()
        return jsonify([{
            'id': med.id,
            'name': med.name,
            'description': med.description,
            'category': med.category,
            'unit_price': float(med.unit_price),
            'stock_quantity': med.stock_quantity,
            'reorder_level': med.reorder_level,
            'manufacturer': med.manufacturer,
            'expiry_date': med.expiry_date.isoformat() if med.expiry_date else None,
            'is_active': med.is_active
        } for med in medicines]), 200
    except Exception as e:
        return jsonify({'message': f'Error fetching medicines: {str(e)}'}), 500

# Laboratory endpoints
@api_bp.route('/laboratory/tests', methods=['GET'])
@login_required
def api_lab_tests():
    # Import here to avoid circular import
    from web_app import LabTest
    
    try:
        lab_tests = LabTest.query.all()
        return jsonify([{
            'id': test.id,
            'name': test.name,
            'description': test.description,
            'category': test.category,
            'price': float(test.price),
            'is_active': test.is_active
        } for test in lab_tests]), 200
    except Exception as e:
        return jsonify({'message': f'Error fetching lab tests: {str(e)}'}), 500

@api_bp.route('/laboratory/results', methods=['GET'])
@login_required
def api_lab_results():
    # Import here to avoid circular import
    from web_app import LabResult
    
    try:
        lab_results = LabResult.query.all()
        return jsonify([{
            'id': result.id,
            'patient_id': result.patient_id,
            'patient_name': f"{result.patient.first_name} {result.patient.last_name}" if result.patient else 'Unknown',
            'test_id': result.test_id,
            'test_name': result.test.name if result.test else 'Unknown',
            'result_value': result.result_value,
            'reference_range': result.reference_range,
            'status': result.status,
            'test_date': result.test_date.isoformat() if result.test_date else None,
            'doctor_id': result.doctor_id,
            'doctor_name': result.doctor.full_name if result.doctor else 'Unknown'
        } for result in lab_results]), 200
    except Exception as e:
        return jsonify({'message': f'Error fetching lab results: {str(e)}'}), 500

# Staff endpoints
@api_bp.route('/staff', methods=['GET'])
@login_required
def api_staff():
    # Import here to avoid circular import
    from web_app import WebUser
    
    try:
        staff = WebUser.query.filter(WebUser.role != 'patient').all()
        return jsonify([{
            'id': user.id,
            'full_name': user.full_name,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'phone': getattr(user, 'phone', ''),
            'department': getattr(user, 'department', ''),
            'specialization': getattr(user, 'specialization', ''),
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat() if user.created_at else None
        } for user in staff]), 200
    except Exception as e:
        return jsonify({'message': f'Error fetching staff: {str(e)}'}), 500

# Reports endpoints
@api_bp.route('/reports/patients', methods=['GET'])
@login_required
def api_patient_reports():
    # Import here to avoid circular import
    from web_app import WebPatient, db
    
    try:
        # Get patient statistics
        total_patients = WebPatient.query.count()
        gender_stats = db.session.query(
            WebPatient.gender,
            db.func.count(WebPatient.id)
        ).group_by(WebPatient.gender).all()
        
        return jsonify({
            'total_patients': total_patients,
            'gender_distribution': {gender: count for gender, count in gender_stats}
        }), 200
    except Exception as e:
        return jsonify({'message': f'Error generating patient reports: {str(e)}'}), 500

@api_bp.route('/reports/appointments', methods=['GET'])
@login_required
def api_appointment_reports():
    # Import here to avoid circular import
    from web_app import WebAppointment, db
    
    try:
        # Get appointment statistics
        total_appointments = WebAppointment.query.count()
        status_stats = db.session.query(
            WebAppointment.status,
            db.func.count(WebAppointment.id)
        ).group_by(WebAppointment.status).all()
        
        return jsonify({
            'total_appointments': total_appointments,
            'status_distribution': {status: count for status, count in status_stats}
        }), 200
    except Exception as e:
        return jsonify({'message': f'Error generating appointment reports: {str(e)}'}), 500

# Error handlers
@api_bp.errorhandler(404)
def api_not_found(error):
    return jsonify({'message': 'Resource not found'}), 404

@api_bp.errorhandler(500)
def api_internal_error(error):
    return jsonify({'message': 'Internal server error'}), 500