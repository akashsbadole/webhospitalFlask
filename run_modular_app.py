#!/usr/bin/env python3
"""
Hospital Management System - Modular Application Entry Point
Main entry point for the modularized Flask application
"""

import os
import sys

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.user import WebUser
from werkzeug.security import generate_password_hash

def init_modular_db(app):
    """Initialize database with sample data"""
    with app.app_context():
        db.create_all()
        
        # Create admin user if not exists
        admin = WebUser.query.filter_by(username='admin').first()
        if not admin:
            admin = WebUser(
                username='admin',
                email='admin@hospital.com',
                password_hash=generate_password_hash('admin123'),
                full_name='System Administrator',
                role='admin',
                department='Administration',
                employee_id='EMP000001'
            )
            db.session.add(admin)
        
        # Create sample users for different roles
        users_data = [
            {'username': 'doctor', 'email': 'doctor@hospital.com', 'password': 'doctor123', 'full_name': 'Dr. John Smith', 'role': 'doctor', 'department': 'General Medicine', 'specialization': 'Internal Medicine'},
            {'username': 'nurse', 'email': 'nurse@hospital.com', 'password': 'nurse123', 'full_name': 'Sarah Johnson', 'role': 'nurse', 'department': 'General Ward'},
            {'username': 'receptionist', 'email': 'reception@hospital.com', 'password': 'reception123', 'full_name': 'Mary Wilson', 'role': 'receptionist', 'department': 'Front Desk'},
            {'username': 'labtech', 'email': 'lab@hospital.com', 'password': 'lab123', 'full_name': 'David Brown', 'role': 'lab_tech', 'department': 'Laboratory'},
            {'username': 'pharmacist', 'email': 'pharmacy@hospital.com', 'password': 'pharmacy123', 'full_name': 'Lisa Davis', 'role': 'pharmacist', 'department': 'Pharmacy'},
            {'username': 'accountant', 'email': 'accounts@hospital.com', 'password': 'accounts123', 'full_name': 'Robert Miller', 'role': 'accountant', 'department': 'Accounts'}
        ]
        
        for i, user_data in enumerate(users_data, 2):
            existing_user = WebUser.query.filter_by(username=user_data['username']).first()
            if not existing_user:
                user = WebUser(
                    username=user_data['username'],
                    email=user_data['email'],
                    password_hash=generate_password_hash(user_data['password']),
                    full_name=user_data['full_name'],
                    role=user_data['role'],
                    department=user_data['department'],
                    employee_id=f'EMP{i:06d}',
                    specialization=user_data.get('specialization')
                )
                db.session.add(user)
        
        # Create sample departments, services, etc.
        from app.models.admin import Department, Service, Ward, Bed
        
        departments_data = [
            {'name': 'General Medicine', 'code': 'GM'},
            {'name': 'Cardiology', 'code': 'CARD'},
            {'name': 'Neurology', 'code': 'NEURO'},
            {'name': 'Orthopedics', 'code': 'ORTHO'},
            {'name': 'Pediatrics', 'code': 'PEDS'},
            {'name': 'Emergency', 'code': 'ER'},
            {'name': 'Laboratory', 'code': 'LAB'},
            {'name': 'Radiology', 'code': 'RAD'},
            {'name': 'Pharmacy', 'code': 'PHARM'}
        ]
        
        for dept_data in departments_data:
            existing_dept = Department.query.filter_by(code=dept_data['code']).first()
            if not existing_dept:
                dept = Department(
                    name=dept_data['name'],
                    code=dept_data['code'],
                    description=f"{dept_data['name']} Department"
                )
                db.session.add(dept)
        
        # Create sample services
        services_data = [
            {'name': 'General Consultation', 'code': 'CONSULT', 'price': 50.0},
            {'name': 'Emergency Consultation', 'code': 'ER-CONSULT', 'price': 100.0},
            {'name': 'Specialist Consultation', 'code': 'SPEC-CONSULT', 'price': 75.0},
            {'name': 'Procedure - Minor', 'code': 'PROC-MIN', 'price': 150.0},
            {'name': 'Procedure - Major', 'code': 'PROC-MAJ', 'price': 500.0}
        ]
        
        for service_data in services_data:
            existing_service = Service.query.filter_by(code=service_data['code']).first()
            if not existing_service:
                service = Service(
                    name=service_data['name'],
                    code=service_data['code'],
                    price=service_data['price']
                )
                db.session.add(service)
        
        # Create sample wards and beds
        wards_data = [
            {'name': 'General Ward A', 'ward_type': 'general', 'total_beds': 20, 'charge_per_day': 100.0},
            {'name': 'General Ward B', 'ward_type': 'general', 'total_beds': 20, 'charge_per_day': 100.0},
            {'name': 'ICU', 'ward_type': 'icu', 'total_beds': 10, 'charge_per_day': 500.0},
            {'name': 'Emergency Ward', 'ward_type': 'emergency', 'total_beds': 15, 'charge_per_day': 200.0},
            {'name': 'Maternity Ward', 'ward_type': 'maternity', 'total_beds': 12, 'charge_per_day': 150.0}
        ]
        
        for ward_data in wards_data:
            existing_ward = Ward.query.filter_by(name=ward_data['name']).first()
            if not existing_ward:
                ward = Ward(
                    name=ward_data['name'],
                    ward_type=ward_data['ward_type'],
                    total_beds=ward_data['total_beds'],
                    available_beds=ward_data['total_beds'],
                    charge_per_day=ward_data['charge_per_day']
                )
                db.session.add(ward)
                db.session.flush()  # Get ward ID
                
                # Create beds for this ward
                for bed_num in range(1, ward_data['total_beds'] + 1):
                    bed = Bed(
                        bed_number=f"{ward_data['name'][:3].upper()}{bed_num:02d}",
                        ward_id=ward.id,
                        bed_type='general' if ward_data['ward_type'] != 'icu' else 'icu'
                    )
                    db.session.add(bed)
        
        db.session.commit()
        print("Modular database initialized successfully!")

if __name__ == '__main__':
    print("Starting Hospital Management System - Modular Version")
    print("Modular structure loaded")
    print("Initializing database...")
    
    # Create the app
    app = create_app()
    
    # Initialize database
    init_modular_db(app)
    
    print("Starting modular application...")
    print("Server running at: http://localhost:5000")
    print("Hospital Management System - Modular Version Ready!")
    
    # Run the app
    app.run(debug=False, host='0.0.0.0', port=5000)
