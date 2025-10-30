"""
API Routes for Hospital Management System
"""

from flask import jsonify, request, current_app
from flask_login import login_required, current_user
from app.api import api_bp
from app import db
from datetime import datetime, timedelta
import json

# Import models
from app.models.patient import WebPatient
from app.models.clinical import Prescription, MedicalRecord, LabOrder, ImagingOrder
from app.models.pharmacy import Medicine, MedicineDispense
from app.models.billing import Bill, Payment
from app.models.user import WebUser
from app.models.admin import Department

# ==================== API Authentication ====================

@api_bp.before_request
def api_authentication():
    """API authentication check"""
    # Skip authentication for public endpoints
    public_endpoints = ['api.health', 'api.login']
    if request.endpoint in public_endpoints:
        return None
    
    # Check for API key or session authentication
    api_key = request.headers.get('X-API-Key')
    if api_key and api_key == current_app.config.get('API_KEY'):
        return None
    
    # Fall back to session authentication
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required'}), 401

@api_bp.route('/health', methods=['GET'])
def health():
    """API health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

# ==================== Patients API ====================

@api_bp.route('/patients', methods=['GET'])
def get_patients():
    """Get all patients with pagination and filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    
    query = WebPatient.query
    
    if search:
        query = query.filter(
            WebPatient.first_name.ilike(f'%{search}%') |
            WebPatient.last_name.ilike(f'%{search}%') |
            WebPatient.patient_id.ilike(f'%{search}%') |
            WebPatient.phone.ilike(f'%{search}%')
        )
    
    patients = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'patients': [patient.to_dict() for patient in patients.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': patients.total,
            'pages': patients.pages,
            'has_next': patients.has_next,
            'has_prev': patients.has_prev
        }
    })

@api_bp.route('/patients/<int:patient_id>', methods=['GET'])
def get_patient(patient_id):
    """Get specific patient details"""
    patient = WebPatient.query.get_or_404(patient_id)
    return jsonify(patient.to_dict())

@api_bp.route('/patients', methods=['POST'])
def create_patient():
    """Create a new patient"""
    data = request.get_json()
    
    try:
        patient = WebPatient(
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            email=data.get('email'),
            phone=data.get('phone'),
            date_of_birth=datetime.strptime(data.get('date_of_birth'), '%Y-%m-%d').date() if data.get('date_of_birth') else None,
            gender=data.get('gender'),
            address=data.get('address'),
            emergency_contact=data.get('emergency_contact'),
            blood_group=data.get('blood_group'),
            allergies=data.get('allergies')
        )
        
        db.session.add(patient)
        db.session.commit()
        
        return jsonify(patient.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api_bp.route('/patients/<int:patient_id>', methods=['PUT'])
def update_patient(patient_id):
    """Update patient information"""
    patient = WebPatient.query.get_or_404(patient_id)
    data = request.get_json()
    
    try:
        for key, value in data.items():
            if hasattr(patient, key) and key != 'id':
                if key == 'date_of_birth' and value:
                    setattr(patient, key, datetime.strptime(value, '%Y-%m-%d').date())
                else:
                    setattr(patient, key, value)
        
        db.session.commit()
        return jsonify(patient.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api_bp.route('/patients/<int:patient_id>/medical-records', methods=['GET'])
def get_patient_medical_records(patient_id):
    """Get patient medical records"""
    patient = WebPatient.query.get_or_404(patient_id)
    records = MedicalRecord.query.filter_by(patient_id=patient_id).order_by(MedicalRecord.created_at.desc()).all()
    
    return jsonify({
        'patient': patient.to_dict(),
        'records': [record.to_dict() for record in records]
    })

@api_bp.route('/patients/<int:patient_id>/prescriptions', methods=['GET'])
def get_patient_prescriptions(patient_id):
    """Get patient prescriptions"""
    patient = WebPatient.query.get_or_404(patient_id)
    prescriptions = Prescription.query.filter_by(patient_id=patient_id).order_by(Prescription.prescription_date.desc()).all()
    
    return jsonify({
        'patient': patient.to_dict(),
        'prescriptions': [prescription.to_dict() for prescription in prescriptions]
    })

# ==================== Medical Records API ====================

@api_bp.route('/medical-records', methods=['GET'])
def get_medical_records():
    """Get medical records with filtering"""
    patient_id = request.args.get('patient_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = MedicalRecord.query
    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    
    records = query.order_by(MedicalRecord.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'records': [record.to_dict() for record in records.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': records.total,
            'pages': records.pages
        }
    })

@api_bp.route('/medical-records', methods=['POST'])
def create_medical_record():
    """Create a new medical record"""
    data = request.get_json()
    
    try:
        record = MedicalRecord(
            patient_id=data.get('patient_id'),
            doctor_id=data.get('doctor_id'),
            diagnosis=data.get('diagnosis'),
            symptoms=data.get('symptoms'),
            treatment=data.get('treatment'),
            notes=data.get('notes'),
            vital_signs=data.get('vital_signs')
        )
        
        db.session.add(record)
        db.session.commit()
        
        return jsonify(record.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# ==================== Prescriptions API ====================

@api_bp.route('/prescriptions', methods=['GET'])
def get_prescriptions():
    """Get prescriptions with filtering"""
    patient_id = request.args.get('patient_id', type=int)
    doctor_id = request.args.get('doctor_id', type=int)
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Prescription.query
    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    if doctor_id:
        query = query.filter_by(doctor_id=doctor_id)
    if status:
        query = query.filter_by(status=status)
    
    prescriptions = query.order_by(Prescription.prescription_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'prescriptions': [prescription.to_dict() for prescription in prescriptions.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': prescriptions.total,
            'pages': prescriptions.pages
        }
    })

@api_bp.route('/prescriptions/<int:prescription_id>', methods=['GET'])
def get_prescription(prescription_id):
    """Get specific prescription details"""
    prescription = Prescription.query.get_or_404(prescription_id)
    return jsonify(prescription.to_dict())

@api_bp.route('/prescriptions', methods=['POST'])
def create_prescription():
    """Create a new prescription"""
    data = request.get_json()
    
    try:
        prescription = Prescription(
            patient_id=data.get('patient_id'),
            doctor_id=data.get('doctor_id'),
            medications=data.get('medications'),
            instructions=data.get('instructions'),
            diagnosis=data.get('diagnosis'),
            prescription_date=datetime.strptime(data.get('prescription_date'), '%Y-%m-%d').date() if data.get('prescription_date') else datetime.now().date(),
            status=data.get('status', 'active')
        )
        
        db.session.add(prescription)
        db.session.commit()
        
        return jsonify(prescription.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# ==================== Pharmacy API ====================

@api_bp.route('/medicines', methods=['GET'])
def get_medicines():
    """Get medicines with filtering and search"""
    search = request.args.get('search', '')
    category = request.args.get('category')
    low_stock = request.args.get('low_stock', type=bool)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Medicine.query
    
    if search:
        query = query.filter(
            Medicine.name.ilike(f'%{search}%') |
            Medicine.generic_name.ilike(f'%{search}%') |
            Medicine.manufacturer.ilike(f'%{search}%')
        )
    
    if category:
        query = query.filter_by(category=category)
    
    if low_stock:
        query = query.filter(Medicine.stock_quantity <= Medicine.reorder_level)
    
    medicines = query.order_by(Medicine.name).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'medicines': [medicine.to_dict() for medicine in medicines.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': medicines.total,
            'pages': medicines.pages
        }
    })

@api_bp.route('/medicines/<int:medicine_id>', methods=['GET'])
def get_medicine(medicine_id):
    """Get specific medicine details"""
    medicine = Medicine.query.get_or_404(medicine_id)
    return jsonify(medicine.to_dict())

@api_bp.route('/medicines', methods=['POST'])
def create_medicine():
    """Create a new medicine"""
    data = request.get_json()
    
    try:
        medicine = Medicine(
            name=data.get('name'),
            generic_name=data.get('generic_name'),
            manufacturer=data.get('manufacturer'),
            category=data.get('category'),
            strength=data.get('strength'),
            unit=data.get('unit'),
            description=data.get('description'),
            stock_quantity=data.get('stock_quantity', 0),
            reorder_level=data.get('reorder_level', 10),
            cost_price=data.get('cost_price'),
            selling_price=data.get('selling_price'),
            expiry_date=datetime.strptime(data.get('expiry_date'), '%Y-%m-%d').date() if data.get('expiry_date') else None,
            batch_number=data.get('batch_number'),
            storage_conditions=data.get('storage_conditions'),
            side_effects=data.get('side_effects'),
            contraindications=data.get('contraindications'),
            dosage_info=data.get('dosage_info')
        )
        
        db.session.add(medicine)
        db.session.commit()
        
        return jsonify(medicine.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api_bp.route('/medicines/<int:medicine_id>', methods=['PUT'])
def update_medicine(medicine_id):
    """Update medicine information"""
    medicine = Medicine.query.get_or_404(medicine_id)
    data = request.get_json()
    
    try:
        for key, value in data.items():
            if hasattr(medicine, key) and key != 'id':
                if key == 'expiry_date' and value:
                    setattr(medicine, key, datetime.strptime(value, '%Y-%m-%d').date())
                else:
                    setattr(medicine, key, value)
        
        db.session.commit()
        return jsonify(medicine.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api_bp.route('/medicines/low-stock', methods=['GET'])
def get_low_stock_medicines():
    """Get medicines with low stock"""
    medicines = Medicine.query.filter(
        Medicine.stock_quantity <= Medicine.reorder_level
    ).order_by(Medicine.stock_quantity.asc()).all()
    
    return jsonify({
        'medicines': [medicine.to_dict() for medicine in medicines],
        'count': len(medicines)
    })

@api_bp.route('/medicines/expiring-soon', methods=['GET'])
def get_expiring_medicines():
    """Get medicines expiring within 30 days"""
    thirty_days_from_now = datetime.now() + timedelta(days=30)
    medicines = Medicine.query.filter(
        Medicine.expiry_date <= thirty_days_from_now,
        Medicine.expiry_date >= datetime.now().date()
    ).order_by(Medicine.expiry_date.asc()).all()
    
    return jsonify({
        'medicines': [medicine.to_dict() for medicine in medicines],
        'count': len(medicines)
    })

@api_bp.route('/dispense', methods=['POST'])
def dispense_medicine():
    """Dispense medicine from prescription"""
    data = request.get_json()
    
    try:
        dispense = MedicineDispense(
            prescription_id=data.get('prescription_id'),
            medicine_id=data.get('medicine_id'),
            quantity_dispensed=data.get('quantity_dispensed'),
            batch_number=data.get('batch_number'),
            dispensed_by=current_user.id if current_user.is_authenticated else None,
            notes=data.get('notes')
        )
        
        # Update medicine stock
        medicine = Medicine.query.get(data.get('medicine_id'))
        if medicine.stock_quantity < data.get('quantity_dispensed'):
            return jsonify({'error': 'Insufficient stock'}), 400
        
        medicine.stock_quantity -= data.get('quantity_dispensed')
        
        # Update prescription status
        prescription = Prescription.query.get(data.get('prescription_id'))
        prescription.dispense_status = 'dispensed'
        prescription.dispense_date = datetime.now()
        
        db.session.add(dispense)
        db.session.commit()
        
        return jsonify(dispense.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# ==================== Billing API ====================

@api_bp.route('/bills', methods=['GET'])
def get_bills():
    """Get bills with filtering"""
    patient_id = request.args.get('patient_id', type=int)
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Bill.query
    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    if status:
        query = query.filter_by(status=status)
    
    bills = query.order_by(Bill.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'bills': [bill.to_dict() for bill in bills.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': bills.total,
            'pages': bills.pages
        }
    })

@api_bp.route('/bills', methods=['POST'])
def create_bill():
    """Create a new bill"""
    data = request.get_json()
    
    try:
        bill = Bill(
            patient_id=data.get('patient_id'),
            total_amount=data.get('total_amount'),
            discount_amount=data.get('discount_amount', 0),
            final_amount=data.get('final_amount'),
            description=data.get('description'),
            prescription_id=data.get('prescription_id'),
            status=data.get('status', 'pending')
        )
        
        db.session.add(bill)
        db.session.commit()
        
        return jsonify(bill.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api_bp.route('/bills/<int:bill_id>/payments', methods=['GET'])
def get_bill_payments(bill_id):
    """Get payments for a specific bill"""
    bill = Bill.query.get_or_404(bill_id)
    payments = Payment.query.filter_by(bill_id=bill_id).order_by(Payment.payment_date.desc()).all()
    
    return jsonify({
        'bill': bill.to_dict(),
        'payments': [payment.to_dict() for payment in payments]
    })

@api_bp.route('/payments', methods=['POST'])
def create_payment():
    """Create a new payment"""
    data = request.get_json()
    
    try:
        payment = Payment(
            bill_id=data.get('bill_id'),
            amount=data.get('amount'),
            payment_method=data.get('payment_method'),
            payment_date=datetime.strptime(data.get('payment_date'), '%Y-%m-%d').date() if data.get('payment_date') else datetime.now().date(),
            transaction_id=data.get('transaction_id'),
            notes=data.get('notes')
        )
        
        db.session.add(payment)
        
        # Update bill status
        bill = Bill.query.get(data.get('bill_id'))
        total_paid = sum(p.amount for p in Payment.query.filter_by(bill_id=data.get('bill_id')).all()) + data.get('amount')
        
        if total_paid >= bill.final_amount:
            bill.status = 'paid'
        elif total_paid > 0:
            bill.status = 'partial'
        
        db.session.commit()
        
        return jsonify(payment.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# ==================== Lab Orders API ====================

@api_bp.route('/lab-orders', methods=['GET'])
def get_lab_orders():
    """Get lab orders with filtering"""
    patient_id = request.args.get('patient_id', type=int)
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = LabOrder.query
    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    if status:
        query = query.filter_by(status=status)
    
    orders = query.order_by(LabOrder.order_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'orders': [order.to_dict() for order in orders.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': orders.total,
            'pages': orders.pages
        }
    })

@api_bp.route('/lab-orders', methods=['POST'])
def create_lab_order():
    """Create a new lab order"""
    data = request.get_json()
    
    try:
        order = LabOrder(
            patient_id=data.get('patient_id'),
            doctor_id=data.get('doctor_id'),
            test_id=data.get('test_id'),
            test_type=data.get('test_type'),
            order_date=datetime.strptime(data.get('order_date'), '%Y-%m-%d').date() if data.get('order_date') else datetime.now().date(),
            status=data.get('status', 'pending'),
            notes=data.get('notes')
        )
        
        db.session.add(order)
        db.session.commit()
        
        return jsonify(order.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# ==================== Imaging Orders API ====================

@api_bp.route('/imaging-orders', methods=['GET'])
def get_imaging_orders():
    """Get imaging orders with filtering"""
    patient_id = request.args.get('patient_id', type=int)
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = ImagingOrder.query
    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    if status:
        query = query.filter_by(status=status)
    
    orders = query.order_by(ImagingOrder.order_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'orders': [order.to_dict() for order in orders.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': orders.total,
            'pages': orders.pages
        }
    })

@api_bp.route('/imaging-orders', methods=['POST'])
def create_imaging_order():
    """Create a new imaging order"""
    data = request.get_json()
    
    try:
        order = ImagingOrder(
            patient_id=data.get('patient_id'),
            doctor_id=data.get('doctor_id'),
            test_id=data.get('test_id'),
            order_date=datetime.strptime(data.get('order_date'), '%Y-%m-%d').date() if data.get('order_date') else datetime.now().date(),
            status=data.get('status', 'pending'),
            notes=data.get('notes')
        )
        
        db.session.add(order)
        db.session.commit()
        
        return jsonify(order.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# ==================== Dashboard Statistics API ====================

@api_bp.route('/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        # Patient statistics
        total_patients = WebPatient.query.count()
        new_patients_today = WebPatient.query.filter(
            WebPatient.created_at >= datetime.now().date()
        ).count()
        
        # Appointment statistics
        from app.models.appointment import Appointment
        total_appointments = Appointment.query.count()
        appointments_today = Appointment.query.filter(
            Appointment.appointment_date >= datetime.now().date(),
            Appointment.appointment_date < datetime.now().date() + timedelta(days=1)
        ).count()
        
        # Prescription statistics
        total_prescriptions = Prescription.query.count()
        prescriptions_today = Prescription.query.filter(
            Prescription.prescription_date >= datetime.now().date()
        ).count()
        
        # Medicine statistics
        total_medicines = Medicine.query.count()
        low_stock_medicines = Medicine.query.filter(
            Medicine.stock_quantity <= Medicine.reorder_level
        ).count()
        
        # Billing statistics
        total_bills = Bill.query.count()
        pending_payments = Bill.query.filter_by(status='pending').count()
        
        return jsonify({
            'patients': {
                'total': total_patients,
                'new_today': new_patients_today
            },
            'appointments': {
                'total': total_appointments,
                'today': appointments_today
            },
            'prescriptions': {
                'total': total_prescriptions,
                'today': prescriptions_today
            },
            'medicines': {
                'total': total_medicines,
                'low_stock': low_stock_medicines
            },
            'billing': {
                'total_bills': total_bills,
                'pending_payments': pending_payments
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== Error Handlers ====================

@api_bp.errorhandler(404)
def api_not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Resource not found'}), 404

@api_bp.errorhandler(500)
def api_internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

@api_bp.errorhandler(400)
def api_bad_request(error):
    """Handle 400 errors"""
    return jsonify({'error': 'Bad request'}), 400