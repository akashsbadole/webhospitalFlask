"""
Billing routes for Hospital Management System
"""

from flask import render_template, request, redirect, url_for, flash, session, jsonify, make_response
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import io

from app import db
from app.models.patient import WebPatient
from app.models.billing import Bill, BillItem, Payment, InsuranceClaim
from app.models.clinical import Prescription
from app.utils.language import get_text, get_language
from app.utils.decorators import role_required

# Import blueprint from __init__.py
from app.billing import bp

# =============== BILLING DASHBOARD ===============
@bp.route('/')
@login_required
def index():
    """Display billing dashboard"""
    
    # Get statistics
    total_bills = Bill.query.count()
    pending_bills = Bill.query.filter_by(payment_status='pending').count()
    paid_bills = Bill.query.filter_by(payment_status='paid').count()
    
    # Today's revenue
    today = datetime.now().date()
    today_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
        Payment.payment_date >= today
    ).scalar() or 0
    
    # Recent bills
    recent_bills = Bill.query.order_by(Bill.bill_date.desc()).limit(10).all()
    
    return render_template('billing.html',
                         total_bills=total_bills,
                         pending_bills=pending_bills,
                         paid_bills=paid_bills,
                         today_revenue=today_revenue,
                         recent_bills=recent_bills)

# =============== BILLS LIST ===============
@bp.route('/bills')
@login_required
def bills():
    """Display all bills"""
    
    status_filter = request.args.get('status', '')
    patient_filter = request.args.get('patient', '')
    
    query = db.session.query(Bill, WebPatient).join(WebPatient, Bill.patient_id == WebPatient.id)
    
    if status_filter:
        query = query.filter(Bill.payment_status == status_filter)
    
    if patient_filter:
        query = query.filter(
            WebPatient.first_name.contains(patient_filter) |
            WebPatient.last_name.contains(patient_filter) |
            WebPatient.patient_id.contains(patient_filter)
        )
    
    bills = query.order_by(Bill.bill_date.desc()).all()
    
    return render_template('bills.html', bills=bills, status_filter=status_filter, patient_filter=patient_filter)

# =============== CREATE BILL ===============
@bp.route('/create-bill/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def create_bill(patient_id):
    """Create a new bill"""
    
    patient = WebPatient.query.get_or_404(patient_id)
    
    if request.method == 'POST':
        try:
            # Generate bill number
            bill_number = f"BILL-{datetime.now().strftime('%Y%m%d')}-{Bill.query.count() + 1:04d}"
            
            bill = Bill(
                bill_number=bill_number,
                patient_id=patient_id,
                prescription_id=request.form.get('prescription_id') if request.form.get('prescription_id') else None,
                bill_type=request.form.get('bill_type'),
                subtotal=float(request.form.get('subtotal', 0)),
                discount_amount=float(request.form.get('discount_amount', 0)),
                tax_amount=float(request.form.get('tax_amount', 0)),
                total_amount=float(request.form.get('total_amount', 0)),
                final_amount=float(request.form.get('final_amount', 0)),
                created_by=current_user.id
            )
            
            db.session.add(bill)
            db.session.flush()  # Get the bill ID
            
            # Add bill items
            item_names = request.form.getlist('item_name')
            item_quantities = request.form.getlist('item_quantity')
            item_unit_prices = request.form.getlist('item_unit_price')
            
            for i in range(len(item_names)):
                if item_names[i]:
                    bill_item = BillItem(
                        bill_id=bill.id,
                        service_name=item_names[i],
                        quantity=int(item_quantities[i]) if item_quantities[i] else 1,
                        unit_price=float(item_unit_prices[i]),
                        total_price=float(item_unit_prices[i]) * (int(item_quantities[i]) if item_quantities[i] else 1)
                    )
                    db.session.add(bill_item)
            
            db.session.commit()
            
            flash('Bill created successfully!', 'success')
            return redirect(url_for('billing.bill_details', bill_id=bill.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating bill: {str(e)}', 'error')
    
    # Get patient's active prescriptions for pharmacy bills
    prescriptions = Prescription.query.filter_by(patient_id=patient_id, status='active').all()
    
    return render_template('create_bill.html', patient=patient, prescriptions=prescriptions)

# =============== BILL DETAILS ===============
@bp.route('/bill/<int:bill_id>')
@login_required
def bill_details(bill_id):
    """Display bill details"""
    
    bill = Bill.query.get_or_404(bill_id)
    
    return render_template('bill_details.html', bill=bill)

# =============== ADD PAYMENT ===============
@bp.route('/add-payment/<int:bill_id>', methods=['GET', 'POST'])
@login_required
def add_payment(bill_id):
    """Add payment to a bill"""
    
    bill = Bill.query.get_or_404(bill_id)
    
    if request.method == 'POST':
        try:
            payment = Payment(
                bill_id=bill_id,
                amount=float(request.form.get('amount')),
                payment_method=request.form.get('payment_method'),
                transaction_id=request.form.get('transaction_id'),
                notes=request.form.get('notes'),
                received_by=current_user.id
            )
            
            db.session.add(payment)
            
            # Update bill payment status
            total_paid = db.session.query(db.func.sum(Payment.amount)).filter_by(bill_id=bill_id).scalar() or 0
            bill.paid_amount = total_paid
            bill.balance_amount = bill.final_amount - total_paid
            
            if bill.balance_amount <= 0:
                bill.payment_status = 'paid'
            elif total_paid > 0:
                bill.payment_status = 'partial'
            
            db.session.commit()
            
            flash('Payment added successfully!', 'success')
            return redirect(url_for('billing.bill_details', bill_id=bill_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding payment: {str(e)}', 'error')
    
    return render_template('add_payment.html', bill=bill)

# =============== INVOICE ===============
@bp.route('/invoice/<int:bill_id>')
@login_required
def invoice(bill_id):
    """Display invoice"""
    
    bill = Bill.query.get_or_404(bill_id)
    
    return render_template('invoice.html', bill=bill)

# =============== PRINT INVOICE ===============
@bp.route('/print-invoice/<int:bill_id>')
@login_required
def print_invoice(bill_id):
    """Generate PDF invoice"""
    
    bill = Bill.query.get_or_404(bill_id)
    
    # Create PDF
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(inch, height - inch, "INVOICE")
    
    # Hospital info (simplified)
    p.setFont("Helvetica", 12)
    p.drawString(inch, height - 1.5 * inch, "Hospital Management System")
    p.drawString(inch, height - 1.7 * inch, "123 Hospital Street, City, State")
    p.drawString(inch, height - 1.9 * inch, "Phone: (123) 456-7890")
    
    # Bill details
    p.setFont("Helvetica-Bold", 12)
    p.drawString(inch, height - 2.5 * inch, f"Bill Number: {bill.bill_number}")
    p.drawString(inch, height - 2.7 * inch, f"Bill Date: {bill.bill_date.strftime('%Y-%m-%d')}")
    
    # Patient info
    p.drawString(inch, height - 3.1 * inch, f"Patient: {bill.patient.first_name} {bill.patient.last_name}")
    p.drawString(inch, height - 3.3 * inch, f"Patient ID: {bill.patient.patient_id}")
    
    # Table headers
    y_position = height - 4 * inch
    p.setFont("Helvetica-Bold", 10)
    p.drawString(inch, y_position, "Service")
    p.drawString(4 * inch, y_position, "Quantity")
    p.drawString(5 * inch, y_position, "Unit Price")
    p.drawString(6 * inch, y_position, "Total")
    
    # Line
    p.line(inch, y_position - 0.1 * inch, 7 * inch, y_position - 0.1 * inch)
    
    # Bill items
    y_position -= 0.3 * inch
    p.setFont("Helvetica", 10)
    for item in bill.items:
        p.drawString(inch, y_position, item.service_name[:30])
        p.drawString(4 * inch, y_position, str(item.quantity))
        p.drawString(5 * inch, y_position, f"${item.unit_price:.2f}")
        p.drawString(6 * inch, y_position, f"${item.total_price:.2f}")
        y_position -= 0.2 * inch
    
    # Totals
    y_position -= 0.3 * inch
    p.line(inch, y_position, 7 * inch, y_position)
    y_position -= 0.2 * inch
    
    p.setFont("Helvetica-Bold", 10)
    p.drawString(5 * inch, y_position, "Subtotal:")
    p.drawString(6 * inch, y_position, f"${bill.subtotal:.2f}")
    
    y_position -= 0.2 * inch
    p.drawString(5 * inch, y_position, "Discount:")
    p.drawString(6 * inch, y_position, f"-${bill.discount_amount:.2f}")
    
    y_position -= 0.2 * inch
    p.drawString(5 * inch, y_position, "Tax:")
    p.drawString(6 * inch, y_position, f"${bill.tax_amount:.2f}")
    
    y_position -= 0.2 * inch
    p.setFont("Helvetica-Bold", 12)
    p.drawString(5 * inch, y_position, "Total:")
    p.drawString(6 * inch, y_position, f"${bill.final_amount:.2f}")
    
    # Payment status
    y_position -= 0.5 * inch
    p.setFont("Helvetica", 10)
    status_color = (0, 0.7, 0) if bill.payment_status == 'paid' else (0.7, 0, 0)
    p.setFillColorRGB(*status_color)
    p.drawString(inch, y_position, f"Payment Status: {bill.payment_status.upper()}")
    
    p.save()
    
    # Return PDF
    buffer.seek(0)
    pdf = buffer.getvalue()
    buffer.close()
    
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=invoice_{bill.bill_number}.pdf'
    
    return response

# =============== INSURANCE CLAIMS ===============
@bp.route('/insurance-claims')
@login_required
def insurance_claims():
    """Display insurance claims"""
    
    status_filter = request.args.get('status', '')
    
    query = db.session.query(InsuranceClaim, Bill, WebPatient)\
                   .join(Bill, InsuranceClaim.bill_id == Bill.id)\
                   .join(WebPatient, Bill.patient_id == WebPatient.id)
    
    if status_filter:
        query = query.filter(InsuranceClaim.status == status_filter)
    
    claims = query.order_by(InsuranceClaim.claim_date.desc()).all()
    
    return render_template('insurance_claims.html', claims=claims, status_filter=status_filter)

@bp.route('/add-insurance-claim/<int:bill_id>', methods=['GET', 'POST'])
@login_required
def add_insurance_claim(bill_id):
    """Add insurance claim for a bill"""
    
    bill = Bill.query.get_or_404(bill_id)
    
    if request.method == 'POST':
        try:
            # Generate claim number
            claim_number = f"CLAIM-{datetime.now().strftime('%Y%m%d')}-{InsuranceClaim.query.count() + 1:04d}"
            
            claim = InsuranceClaim(
                patient_id=bill.patient_id,
                bill_id=bill_id,
                claim_number=claim_number,
                claim_amount=bill.final_amount,
                insurance_provider=request.form.get('insurance_provider'),
                policy_number=request.form.get('policy_number'),
                notes=request.form.get('notes'),
                status='submitted'
            )
            
            db.session.add(claim)
            db.session.commit()
            
            flash('Insurance claim submitted successfully!', 'success')
            return redirect(url_for('billing.insurance_claims'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error submitting insurance claim: {str(e)}', 'error')
    
    return render_template('add_insurance_claim.html', bill=bill)

# =============== API ENDPOINTS ===============
@bp.route('/api/patient-bills/<int:patient_id>')
@login_required
def get_patient_bills(patient_id):
    """API endpoint to get patient bills"""
    
    bills = Bill.query.filter_by(patient_id=patient_id).order_by(Bill.bill_date.desc()).all()
    
    results = []
    for bill in bills:
        results.append({
            'id': bill.id,
            'bill_number': bill.bill_number,
            'bill_date': bill.bill_date.strftime('%Y-%m-%d'),
            'bill_type': bill.bill_type,
            'total_amount': float(bill.total_amount),
            'final_amount': float(bill.final_amount),
            'payment_status': bill.payment_status,
            'balance_amount': float(bill.balance_amount)
        })
    
    return jsonify(results)