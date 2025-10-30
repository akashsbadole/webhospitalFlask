"""
Pharmacy database models
"""

from datetime import datetime
from app import db

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
    reorder_level = db.Column(db.Integer, default=10)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    order_items = db.relationship('PharmacyOrderItem', backref='medicine', lazy='dynamic')

    def __repr__(self):
        return f'<Medicine {self.name}>'
    def to_dict(self):
        """Convert medicine to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'generic_name': self.generic_name,
            'brand_name': self.brand_name,
            'category': self.category,
            'dosage_form': self.dosage_form,
            'strength': self.strength,
            'manufacturer': self.manufacturer,
            'batch_number': self.batch_number,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'purchase_price': self.purchase_price,
            'selling_price': self.selling_price,
            'stock_quantity': self.stock_quantity,
            'reorder_level': self.reorder_level,
            'is_low_stock': self.stock_quantity <= self.reorder_level,
            'is_expired': self.is_expired,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @property
    def is_low_stock(self):
        """Check if medicine is below minimum stock level"""
        return self.stock_quantity <= self.reorder_level
    
    @property
    def is_expired(self):
        """Check if medicine is expired"""
        if self.expiry_date:
            return datetime.now().date() > self.expiry_date
        return False

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
    payment_method = db.Column(db.String(50))  # cash, card, online, insurance
    pharmacist_notes = db.Column(db.Text)
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid, partial
    status = db.Column(db.String(20), default='pending')  # pending, dispensed, cancelled

    # Relationships
    items = db.relationship('PharmacyOrderItem', backref='pharmacy_order', lazy='dynamic')
    prescription = db.relationship('Prescription', backref='pharmacy_orders')

    def __repr__(self):
        return f'<PharmacyOrder {self.id}>'

class PharmacyOrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pharmacy_order_id = db.Column(db.Integer, db.ForeignKey('pharmacy_order.id'), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicine.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    dosage = db.Column(db.String(200))  # Dosage instructions for this medicine

    def __repr__(self):
        return f'<PharmacyOrderItem {self.id}>'

class MedicineDispense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescription.id'), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicine.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    batch_number = db.Column(db.String(50))
    def to_dict(self):
        """Convert medicine dispense to dictionary for API responses"""
        return {
            'id': self.id,
            'prescription_id': self.prescription_id,
            'medicine_id': self.medicine_id,
            'quantity': self.quantity,
            'batch_number': self.batch_number,
            'unit_price': self.unit_price,
            'dispense_date': self.dispense_date.isoformat() if self.dispense_date else None,
            'dispensed_by': self.dispensed_by,
            'notes': self.notes
        }
    unit_price = db.Column(db.Float, nullable=False)
    dispense_date = db.Column(db.DateTime, default=datetime.utcnow)
    dispensed_by = db.Column(db.Integer, db.ForeignKey('web_user.id'))
    notes = db.Column(db.Text)
    
    # Relationships
    medicine = db.relationship('Medicine', backref='dispenses')
    dispenser = db.relationship('WebUser', backref='dispensed_medicines')
    
    def __repr__(self):
        return f'<MedicineDispense {self.id}>'

class PharmacyInventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicine.id'), nullable=False)
    batch_number = db.Column(db.String(50), nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    quantity = db.Column(db.Integer, default=0)
    cost_price = db.Column(db.Float)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    location = db.Column(db.String(100))  # Storage location
    received_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    medicine = db.relationship('Medicine', backref='inventory_batches')
    
    def __repr__(self):
        return f'<PharmacyInventory {self.medicine.name} - {self.batch_number}>'

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact_person = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    address = db.Column(db.Text)
    license_number = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    inventory = db.relationship('PharmacyInventory', backref='supplier', lazy='dynamic')
    
    def __repr__(self):
        return f'<Supplier {self.name}>'
