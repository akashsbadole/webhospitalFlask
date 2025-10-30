#!/usr/bin/env python3
"""
Test script to verify dispense_medicine functionality
"""

import sys
import os

# Add current directory to path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web_app import app, db, PharmacyOrder, PharmacyOrderItem, Medicine, Prescription, WebPatient, WebUser
from datetime import datetime

def test_models():
    """Test that our models have the required fields"""
    with app.app_context():
        print("Testing PharmacyOrder model fields...")
        
        # Check if payment_method field exists
        if hasattr(PharmacyOrder, 'payment_method'):
            print("+ PharmacyOrder.payment_method field exists")
        else:
            print("- PharmacyOrder.payment_method field missing")
            
        # Check if pharmacist_notes field exists
        if hasattr(PharmacyOrder, 'pharmacist_notes'):
            print("+ PharmacyOrder.pharmacist_notes field exists")
        else:
            print("- PharmacyOrder.pharmacist_notes field missing")
            
        print("\nTesting PharmacyOrderItem model fields...")
        
        # Check if dosage field exists
        if hasattr(PharmacyOrderItem, 'dosage'):
            print("+ PharmacyOrderItem.dosage field exists")
        else:
            print("- PharmacyOrderItem.dosage field missing")

def test_template_render():
    """Test that the template can be rendered without errors"""
    with app.app_context():
        try:
            # Create test data
            from flask import render_template
            
            # Mock current_user
            class MockUser:
                def __init__(self):
                    self.full_name = "Dr. Test"
                    self.is_authenticated = True
                    
            # Create test patient
            patient = WebPatient(
                patient_id='TEST001',
                first_name='Test',
                last_name='Patient',
                phone='1234567890',
                allergies='Penicillin',
                date_of_birth=datetime(1990, 1, 1)
            )
            
            # Create test doctor
            doctor = WebUser(
                username='testdoctor',
                email='doctor@test.com',
                password_hash='test',
                full_name='Dr. Test',
                role='doctor'
            )
            
            # Create test prescription
            prescription = Prescription(
                patient_id=patient.id,
                doctor_id=doctor.id,
                medications='Test Medicine 1, Test Medicine 2',
                instructions='Take as directed',
                prescription_date=datetime.now()
            )
            
            # Set the relationships manually for testing
            prescription.patient = patient
            prescription.doctor = doctor
            
            # Create test medicines
            medicines = [
                Medicine(
                    name='Test Medicine 1',
                    strength='500mg',
                    selling_price=10.0,
                    stock_quantity=100,
                    batch_number='B001',
                    expiry_date=datetime(2025, 12, 31),
                    category='Test Category'
                ),
                Medicine(
                    name='Test Medicine 2',
                    strength='250mg',
                    selling_price=5.0,
                    stock_quantity=50,
                    batch_number='B002',
                    expiry_date=datetime(2025, 6, 30),
                    category='Another Category'
                )
            ]
            
            # Try to render the template
            with app.test_request_context():
                # Set mock user in context
                from flask import g
                g.current_user = MockUser()
                
                # Mock translation function
                def mock_get_text(key):
                    # Return some common translations for testing
                    translations = {
                        'Dispense Medicine': 'Dispense Medicine',
                        'Prescription Information': 'Prescription Information',
                        'Patient Information': 'Patient Information',
                        'Dispensing Notes': 'Dispensing Notes',
                        'Medicine': 'Medicine',
                        'Quantity': 'Quantity',
                        'Unit Price': 'Unit Price',
                        'Total': 'Total',
                        'Discount (%)': 'Discount (%)',
                        'Tax Amount': 'Tax Amount',
                        'Bill Summary': 'Bill Summary',
                        'Subtotal:': 'Subtotal:',
                        'Discount:': 'Discount:',
                        'Tax:': 'Tax:',
                        'Total:': 'Total:',
                        'Dosage Instructions': 'Dosage Instructions',
                        'Payment Method': 'Payment Method',
                        'Pharmacist Notes': 'Pharmacist Notes',
                        'Patient Signature': 'Patient Signature',
                        'Cancel': 'Cancel',
                        'title': 'Dispense Medicine'
                    }
                    return translations.get(key, key)
                
                with app.app_context():
                    app.jinja_env.globals.update(
                        get_text=mock_get_text,
                        get_language=lambda: 'en',
                        hasattr=hasattr  # Add hasattr to globals
                    )
                    
                    rendered = render_template(
                        'dispense_medicine.html',
                        prescription=prescription,
                        medicines=medicines
                    )
            
            if "Dispense Medicine" in rendered:
                print("\n+ Template renders successfully")
                return True
            else:
                print("\n- Template rendering failed")
                return False
                
        except Exception as e:
            print(f"\n- Template rendering error: {str(e)}")
            return False

if __name__ == '__main__':
    print("Testing dispense_medicine implementation...")
    
    # Test model fields
    test_models()
    
    # Test template rendering
    if test_template_render():
        print("\nAll tests passed successfully!")
    else:
        print("\nSome tests failed.")