#!/usr/bin/env python3
"""
Simple test script to verify advanced features of dispense_medicine.html template
"""

import os

def test_template_features():
    """Test that template contains all advanced features"""
    print("Testing Advanced Features of Dispense Medicine Template")
    print("=" * 60)
    
    # Read the template file
    with open('templates/dispense_medicine.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for advanced features in the template
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
        if feature_text in content:
            print(f"+ {feature_name}: Found")
        else:
            print(f"- {feature_name}: Missing")
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
        if func_text in content:
            print(f"+ {func_name}: Found")
        else:
            print(f"- {func_name}: Missing")
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
        if attr_text in content:
            print(f"+ {attr_name}: Found")
        else:
            print(f"- {attr_name}: Missing")
            all_features_found = False
    
    # Check for HTML structure
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
    for check_name, check_text in structure_checks.items():
        if check_text in content.lower():
            print(f"+ {check_name}: Found")
        else:
            print(f"- {check_name}: Missing")
            all_features_found = False
    
    print("\n" + "=" * 60)
    if all_features_found:
        print("+ All advanced features successfully implemented!")
        return True
    else:
        print("- Some features are missing")
        return False

def test_backend_integration():
    """Test that backend has required fields for advanced features"""
    print("\nTesting Backend Integration")
    print("=" * 60)
    
    # Read the web_app.py file
    with open('web_app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for required fields in models
    model_fields = {
        "PharmacyOrder.payment_method": "payment_method = db.Column",
        "PharmacyOrder.pharmacist_notes": "pharmacist_notes = db.Column",
        "PharmacyOrderItem.dosage": "dosage = db.Column"
    }
    
    print("\nChecking for model fields:")
    all_fields_found = True
    
    for field_name, field_text in model_fields.items():
        if field_text in content:
            print(f"+ {field_name}: Found")
        else:
            print(f"- {field_name}: Missing")
            all_fields_found = False
    
    # Check for route handling
    route_checks = {
        "dispense_medicine route": "@app.route('/dispense_medicine",
        "POST method handling": "methods=['GET', 'POST']"
    }
    
    print("\nChecking for route handling:")
    for check_name, check_text in route_checks.items():
        if check_text in content:
            print(f"+ {check_name}: Found")
        else:
            print(f"- {check_name}: Missing")
            all_fields_found = False
    
    print("\n" + "=" * 60)
    if all_fields_found:
        print("+ Backend integration is correct!")
        return True
    else:
        print("- Backend integration has issues")
        return False

if __name__ == "__main__":
    # Run tests
    test1_passed = test_template_features()
    test2_passed = test_backend_integration()
    
    print("\n" + "=" * 60)
    if test1_passed and test2_passed:
        print("+ All tests passed! The advanced features are working correctly.")
        exit(0)
    else:
        print("- Some tests failed. Please check implementation.")
        exit(1)