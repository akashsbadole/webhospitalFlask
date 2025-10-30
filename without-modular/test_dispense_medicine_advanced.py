#!/usr/bin/env python3
"""
Test script to verify the advanced features of the dispense_medicine.html template
"""

import sys
import os

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import unittest.mock

# Create a minimal Flask app for testing
app = Flask(__name__)
app.config['SECRET_KEY'] = 'test_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Mock models for testing
class User:
    def __init__(self, id=1, full_name="Test Pharmacist"):
        self.id = id
        self.full_name = full_name

class Patient:
    def __init__(self, id=1, first_name="John", last_name="Doe", patient_id="P12345", phone="555-1234"):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.patient_id = patient_id
        self.phone = phone
        self.allergies = "Penicillin, Peanuts"

class Doctor:
    def __init__(self, id=1, full_name="Dr. Smith"):
        self.id = id
        self.full_name = full_name

class Medicine:
    def __init__(self, id=1, name="Amoxicillin", generic_name="Amoxicillin", brand_name="Amoxil", 
                 category="Antibiotic", strength="500mg", stock_quantity=50, 
                 selling_price=10.50, batch_number="B12345", expiry_date=datetime(2024, 12, 31)):
        self.id = id
        self.name = name
        self.generic_name = generic_name
        self.brand_name = brand_name
        self.category = category
        self.strength = strength
        self.stock_quantity = stock_quantity
        self.selling_price = selling_price
        self.batch_number = batch_number
        self.expiry_date = expiry_date

class Prescription:
    def __init__(self, id=1, patient=None, doctor=None, medications="Amoxicillin 500mg", 
                 instructions="Take twice daily with food", status="pending"):
        self.id = id
        self.patient = patient or Patient()
        self.doctor = doctor or Doctor()
        self.medications = medications
        self.instructions = instructions
        self.status = status
        self.prescription_date = datetime.now()

# Mock the get_text function
def mock_get_text(key, default=None):
    return default or key

# Create test route
@app.route('/test_dispense_medicine')
def test_dispense_medicine():
    # Create test data
    patient = Patient()
    doctor = Doctor()
    prescription = Prescription(patient=patient, doctor=doctor)
    
    # Create a list of medicines
    medicines = [
        Medicine(id=1, name="Amoxicillin", generic_name="Amoxicillin", brand_name="Amoxil"),
        Medicine(id=2, name="Amoxicillin", generic_name="Amoxicillin", brand_name="GenericAmox"),
        Medicine(id=3, name="Ibuprofen", generic_name="Ibuprofen", brand_name="Advil"),
        Medicine(id=4, name="Paracetamol", generic_name="Paracetamol", brand_name="Tylenol"),
    ]
    
    # Mock current_user
    current_user = User()
    
    # Render the template with test data
    with app.test_request_context():
        with unittest.mock.patch('jinja2.ext.do.gettext', mock_get_text):
            with unittest.mock.patch('flask_login.current_user', current_user):
                return render_template('dispense_medicine.html', 
                                  prescription=prescription, 
                                  medicines=medicines)

def test_template_rendering():
    """Test that the template renders without errors"""
    print("Testing template rendering...")
    
    with app.app_context():
        try:
            html = test_dispense_medicine()
            
            # Check for advanced features in the rendered HTML
            features = {
                "Medicine Substitution": "Show Alternatives",
                "Batch & Expiry Management": "Batch & Expiry Management",
                "Medication History": "Medication History",
                "Digital Receipt Generation": "Preview Receipt",
                "Payment Gateway Integration": "Payment Gateway Integration",
                "Barcode Scanner": "Scan Barcode",
                "Drug Interaction Checking": "Check Interactions",
                "Patient Signature Capture": "signature-pad",
                "Expiry Date Warnings": "expiry-alert",
                "Generic Name Display": "generic-name"
            }
            
            print("\nChecking for advanced features:")
            all_features_found = True
            
            for feature_name, feature_text in features.items():
                if feature_text in html:
                    print(f"✓ {feature_name}: Found")
                else:
                    print(f"✗ {feature_name}: Missing")
                    all_features_found = False
            
            # Check for JavaScript functions
            js_functions = {
                "showSubstitutions": "function showSubstitutions",
                "selectSubstitution": "function selectSubstitution",
                "checkExpiryDate": "function checkExpiryDate",
                "updateBatchInfo": "function updateBatchInfo",
                "toggleMedicationHistory": "function toggleMedicationHistory",
                "loadMedicationHistory": "function loadMedicationHistory",
                "generateDigitalReceipt": "function generateDigitalReceipt",
                "processPayment": "function processPayment",
                "handlePaymentMethodChange": "function handlePaymentMethodChange"
            }
            
            print("\nChecking for JavaScript functions:")
            for func_name, func_text in js_functions.items():
                if func_text in html:
                    print(f"✓ {func_name}: Found")
                else:
                    print(f"✗ {func_name}: Missing")
                    all_features_found = False
            
            # Check for data attributes
            data_attributes = {
                "data-generic": 'data-generic="',
                "data-brand": 'data-brand="',
                "data-batch": 'data-batch="',
                "data-expiry": 'data-expiry="'
            }
            
            print("\nChecking for data attributes:")
            for attr_name, attr_text in data_attributes.items():
                if attr_text in html:
                    print(f"✓ {attr_name}: Found")
                else:
                    print(f"✗ {attr_name}: Missing")
                    all_features_found = False
            
            if all_features_found:
                print("\n✓ All advanced features successfully implemented!")
                return True
            else:
                print("\n✗ Some features are missing")
                return False
                
        except Exception as e:
            print(f"✗ Error rendering template: {e}")
            return False

def test_html_structure():
    """Test the HTML structure of the template"""
    print("\nTesting HTML structure...")
    
    with app.app_context():
        try:
            html = test_dispense_medicine()
            
            # Check for proper structure
            structure_checks = {
                "HTML5 Doctype": "<!DOCTYPE html>",
                "Bootstrap CSS": "bootstrap",
                "Font Awesome Icons": "fas fa-",
                "Form Element": "<form",
                "Table Elements": "<table",
                "Modal Elements": "modal",
                "Canvas Element": "<canvas",
                "JavaScript Section": "<script"
            }
            
            print("\nChecking HTML structure:")
            all_structure_correct = True
            
            for check_name, check_text in structure_checks.items():
                if check_text in html.lower():
                    print(f"✓ {check_name}: Found")
                else:
                    print(f"✗ {check_name}: Missing")
                    all_structure_correct = False
            
            if all_structure_correct:
                print("\n✓ HTML structure is correct!")
                return True
            else:
                print("\n✗ HTML structure has issues")
                return False
                
        except Exception as e:
            print(f"✗ Error checking HTML structure: {e}")
            return False

if __name__ == "__main__":
    print("Testing Advanced Features of Dispense Medicine Template")
    print("=" * 60)
    
    # Run tests
    test1_passed = test_template_rendering()
    test2_passed = test_html_structure()
    
    print("\n" + "=" * 60)
    if test1_passed and test2_passed:
        print("✓ All tests passed! The advanced features are working correctly.")
        exit(0)
    else:
        print("✗ Some tests failed. Please check the implementation.")
        exit(1)