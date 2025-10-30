#!/usr/bin/env python3
"""
Test script to check if all endpoints referenced in templates exist
"""

from app import create_app

def test_endpoints():
    app = create_app()
    
    # Get all registered endpoints
    endpoints = []
    for rule in app.url_map.iter_rules():
        endpoints.append(rule.endpoint)
    
    print("Registered endpoints:")
    for endpoint in sorted(endpoints):
        print(f"  {endpoint}")
    
    # Check specific endpoints that are referenced in templates
    required_endpoints = [
        'main.index',
        'main.dashboard', 
        'main.enquiries',
        'main.set_language',
        'patients.index',
        'patients.add',
        'appointments.index',
        'appointments.add',
        'appointments.telemedicine',
        'clinical.lab_orders',
        'clinical.imaging_orders', 
        'clinical.admissions',
        'pharmacy.medicines',
        'pharmacy.orders',
        'billing.index',
        'billing.create_bill',
        'admin.staff_management',
        'admin.attendance',
        'admin.manage_departments',
        'admin.manage_wards',
        'admin.reports',
        'admin.settings',
        'auth.login',
        'auth.logout',
        'auth.switch_branch'
    ]
    
    print("\nChecking required endpoints:")
    missing = []
    for endpoint in required_endpoints:
        if endpoint in endpoints:
            print(f"  ✓ {endpoint}")
        else:
            print(f"  ✗ {endpoint}")
            missing.append(endpoint)
    
    if missing:
        print(f"\nMissing endpoints: {missing}")
    else:
        print("\nAll required endpoints are registered!")

if __name__ == '__main__':
    test_endpoints()