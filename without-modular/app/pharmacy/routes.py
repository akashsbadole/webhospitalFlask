"""
Pharmacy routes for Hospital Management System
"""

from flask import render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json

from app import db
from app.models.patient import WebPatient
from app.models.clinical import Prescription
from app.models.pharmacy import Medicine, MedicineDispense, PharmacyInventory
from app.models.billing import Bill
from app.utils.language import get_text, get_language
from app.utils.decorators import role_required

# Import blueprint from __init__.py
from app.pharmacy import bp

# =============== PHARMACY DASHBOARD ===============
@bp.route('/')
@login_required
def pharmacy_dashboard():
    """Pharmacy dashboard with overview of medicines, orders, and alerts"""
    
    # Get statistics
    total_medicines = Medicine.query.filter_by(is_active=True).count()
    low_stock_medicines = Medicine.query.filter(
        Medicine.stock_quantity <= Medicine.min_stock_level,
        Medicine.is_active == True
    ).count()
    
    expired_medicines = Medicine.query.filter(
        Medicine.expiry_date <= datetime.now().date(),
        Medicine.is_active == True
    ).count()
    
    # Today's dispenses
    today = datetime.now().date()
    today_dispenses = MedicineDispense.query.filter(
        MedicineDispense.dispense_date >= today,
        MedicineDispense.dispense_date < today + timedelta(days=1)
    ).count()
    
    # Recent dispenses
    recent_dispenses = MedicineDispense.query.order_by(
        MedicineDispense.dispense_date.desc()
    ).limit(10).all()
    
    return render_template('pharmacy_dashboard.html',
                         total_medicines=total_medicines,
                         low_stock_medicines=low_stock_medicines,
                         expired_medicines=expired_medicines,
                         today_dispenses=today_dispenses,
                         recent_dispenses=recent_dispenses)

# =============== MEDICINE INVENTORY ===============
@bp.route('/medicines')
@login_required
def medicines():
    """Display all medicines in inventory"""
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    category = request.args.get('category', '', type=str)
    
    query = Medicine.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(
            Medicine.name.contains(search) |
            Medicine.generic_name.contains(search)
        )
    
    if category:
        query = query.filter_by(category=category)
    
    medicines = query.paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get categories for filter dropdown
    categories = db.session.query(Medicine.category).filter_by(is_active=True).distinct().all()
    categories = [c[0] for c in categories if c[0]]
    
    return render_template('pharmacy_medicines.html',
                         medicines=medicines,
                         categories=categories,
                         search=search,
                         selected_category=category)

# =============== PHARMACY ORDERS ===============
@bp.route('/orders')
@login_required
def orders():
    """Display all prescriptions to be dispensed"""
    
    status = request.args.get('status', 'pending')
    page = request.args.get('page', 1, type=int)
    
    query = Prescription.query
    
    if status == 'pending':
        query = query.filter_by(dispense_status='pending')
    elif status == 'dispensed':
        query = query.filter_by(dispense_status='dispensed')
    elif status == 'partial':
        query = query.filter_by(dispense_status='partial')
    
    prescriptions = query.order_by(
        Prescription.prescription_date.desc()
    ).paginate(page=page, per_page=20, error_out=False)
    
    return render_template('pharmacy_orders.html',
                         prescriptions=prescriptions,
                         current_status=status)

# =============== DISPENSE MEDICINE ===============
@bp.route('/dispense/<int:prescription_id>')
@login_required
def dispense_medicine(prescription_id):
    """Dispense medicine for a prescription"""
    
    prescription = Prescription.query.get_or_404(prescription_id)
    medicines = Medicine.query.filter_by(is_active=True).all()
    
    return render_template('dispense_medicine.html',
                         prescription=prescription,
                         medicines=medicines)

@bp.route('/dispense/<int:prescription_id>', methods=['POST'])
@login_required
def process_dispense(prescription_id):
    """Process medicine dispensing"""
    
    prescription = Prescription.query.get_or_404(prescription_id)
    
    try:
        # Get form data
        medicine_ids = request.form.getlist('medicine_id')
        quantities = request.form.getlist('quantity')
        batch_numbers = request.form.getlist('batch_number')
        unit_prices = request.form.getlist('unit_price')
        
        total_amount = float(request.form.get('total_amount', 0))
        discount = float(request.form.get('discount', 0))
        tax_amount = float(request.form.get('tax_amount', 0))
        final_amount = float(request.form.get('final_amount', 0))
        
        # Process each medicine
        for i, medicine_id in enumerate(medicine_ids):
            if medicine_id and quantities[i]:
                medicine = Medicine.query.get(medicine_id)
                quantity = int(quantities[i])
                
                # Check stock
                if medicine.stock_quantity < quantity:
                    flash(f'Insufficient stock for {medicine.name}. Available: {medicine.stock_quantity}', 'error')
                    return redirect(url_for('pharmacy.dispense_medicine', prescription_id=prescription_id))
                
                # Create dispense record
                dispense = MedicineDispense(
                    prescription_id=prescription.id,
                    medicine_id=medicine.id,
                    quantity=quantity,
                    batch_number=batch_numbers[i] if i < len(batch_numbers) else None,
                    unit_price=float(unit_prices[i]) if i < len(unit_prices) else medicine.selling_price,
                    dispense_date=datetime.now(),
                    dispensed_by=current_user.id
                )
                
                # Update medicine stock
                medicine.stock_quantity -= quantity
                
                db.session.add(dispense)
        
        # Update prescription status
        prescription.dispense_status = 'dispensed'
        prescription.dispense_date = datetime.now()
        
        # Create bill if not exists
        if not hasattr(prescription, 'bill') or not prescription.bill:
            bill = Bill(
                patient_id=prescription.patient_id,
                prescription_id=prescription.id,
                total_amount=total_amount,
                discount_amount=discount,
                tax_amount=tax_amount,
                final_amount=final_amount,
                bill_date=datetime.now(),
                payment_status='pending'
            )
            db.session.add(bill)
        
        db.session.commit()
        
        flash('Medicine dispensed successfully!', 'success')
        return redirect(url_for('pharmacy.orders'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error dispensing medicine: {str(e)}', 'error')
        return redirect(url_for('pharmacy.dispense_medicine', prescription_id=prescription_id))

# =============== LOW STOCK REPORT ===============
@bp.route('/low-stock')
@login_required
def low_stock_report():
    """Generate low stock report"""
    
    low_stock_medicines = Medicine.query.filter(
        Medicine.stock_quantity <= Medicine.min_stock_level,
        Medicine.is_active == True
    ).order_by(Medicine.stock_quantity).all()
    
    return render_template('pharmacy_low_stock_report.html',
                         medicines=low_stock_medicines)

# =============== PURCHASE ORDERS ===============
@bp.route('/purchase-order')
@login_required
def purchase_order():
    """Create purchase order for medicines"""
    
    # Get medicines that need reordering
    medicines_to_order = Medicine.query.filter(
        Medicine.stock_quantity <= Medicine.min_stock_level,
        Medicine.is_active == True
    ).all()
    
    return render_template('purchase_order.html',
                         medicines=medicines_to_order)

@bp.route('/purchase-order', methods=['POST'])
@login_required
def create_purchase_order():
    """Create a new purchase order"""
    
    try:
        medicine_ids = request.form.getlist('medicine_id')
        order_quantities = request.form.getlist('order_quantity')
        supplier_id = request.form.get('supplier_id')
        expected_delivery = request.form.get('expected_delivery')
        
        # Create purchase order logic here
        # This would typically involve creating a purchase order record
        # and updating the inventory when received
        
        flash('Purchase order created successfully!', 'success')
        return redirect(url_for('pharmacy.pharmacy_dashboard'))
        
    except Exception as e:
        flash(f'Error creating purchase order: {str(e)}', 'error')
        return redirect(url_for('pharmacy.purchase_order'))

# =============== API ENDPOINTS ===============
@bp.route('/api/medicine/<int:medicine_id>')
@login_required
def get_medicine_details(medicine_id):
    """API endpoint to get medicine details"""
    
    medicine = Medicine.query.get_or_404(medicine_id)
    
    return jsonify({
        'id': medicine.id,
        'name': medicine.name,
        'generic_name': medicine.generic_name,
        'strength': medicine.strength,
        'form': medicine.form,
        'stock_quantity': medicine.stock_quantity,
        'min_stock_level': medicine.min_stock_level,
        'selling_price': float(medicine.selling_price),
        'expiry_date': medicine.expiry_date.strftime('%Y-%m-%d') if medicine.expiry_date else None,
        'category': medicine.category,
        'manufacturer': medicine.manufacturer
    })

@bp.route('/api/patient-medication-history/<int:patient_id>')
@login_required
def get_patient_medication_history(patient_id):
    """API endpoint to get patient medication history"""
    
    dispenses = db.session.query(
        MedicineDispense,
        Medicine,
        Prescription
    ).join(Medicine, MedicineDispense.medicine_id == Medicine.id)\
     .join(Prescription, MedicineDispense.prescription_id == Prescription.id)\
     .filter(Prescription.patient_id == patient_id)\
     .order_by(MedicineDispense.dispense_date.desc())\
     .limit(20).all()
    
    history = []
    for dispense, medicine, prescription in dispenses:
        history.append({
            'date': dispense.dispense_date.strftime('%Y-%m-%d'),
            'medicine_name': medicine.name,
            'strength': medicine.strength,
            'quantity': dispense.quantity,
            'instructions': prescription.instructions,
            'doctor': prescription.doctor.full_name if prescription.doctor else 'N/A'
        })
    
    return jsonify(history)