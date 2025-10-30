#!/usr/bin/env python3
"""
Create Doctor, Staff, Admin, and Customer Accounts
This script creates sample accounts for different user roles in the hospital management system
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash
from datetime import datetime, date

def create_accounts():
    """Create sample accounts for different user roles"""
    
    # Use the instance database which has existing users
    db_file = 'instance/hospital_web.db'
    
    if not os.path.exists(db_file):
        print(f"Database file {db_file} does not exist")
        return
    
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Check current users
        cursor.execute("SELECT username, role FROM web_user")
        existing_users = cursor.fetchall()
        print("Existing users:")
        for username, role in existing_users:
            print(f"  {username} ({role})")
        
        print("\nCreating new accounts...")
        
        # Sample accounts to create
        accounts = [
            # Admin Accounts
            {
                'username': 'superadmin',
                'email': 'superadmin@hospital.com',
                'password': 'admin123',
                'full_name': 'Super Administrator',
                'role': 'admin',
                'department': 'Administration',
                'phone': '+1-555-0101',
                'employee_id': 'ADM001'
            },
            {
                'username': 'hradmin',
                'email': 'hr@hospital.com',
                'password': 'hr123',
                'full_name': 'HR Administrator',
                'role': 'admin',
                'department': 'Human Resources',
                'phone': '+1-555-0102',
                'employee_id': 'HR001'
            },
            
            # Doctor Accounts
            {
                'username': 'dr.smith',
                'email': 'dr.smith@hospital.com',
                'password': 'doctor123',
                'full_name': 'Dr. John Smith',
                'role': 'doctor',
                'department': 'Cardiology',
                'phone': '+1-555-0201',
                'employee_id': 'DOC001',
                'specialization': 'Cardiologist',
                'license_number': 'MD12345'
            },
            {
                'username': 'dr.johnson',
                'email': 'dr.johnson@hospital.com',
                'password': 'doctor123',
                'full_name': 'Dr. Sarah Johnson',
                'role': 'doctor',
                'department': 'Pediatrics',
                'phone': '+1-555-0202',
                'employee_id': 'DOC002',
                'specialization': 'Pediatrician',
                'license_number': 'MD12346'
            },
            {
                'username': 'dr.williams',
                'email': 'dr.williams@hospital.com',
                'password': 'doctor123',
                'full_name': 'Dr. Michael Williams',
                'role': 'doctor',
                'department': 'Orthopedics',
                'phone': '+1-555-0203',
                'employee_id': 'DOC003',
                'specialization': 'Orthopedic Surgeon',
                'license_number': 'MD12347'
            },
            
            # Staff Accounts (Nurses)
            {
                'username': 'nurse.mary',
                'email': 'mary.nurse@hospital.com',
                'password': 'nurse123',
                'full_name': 'Mary Wilson',
                'role': 'nurse',
                'department': 'Emergency',
                'phone': '+1-555-0301',
                'employee_id': 'NUR001',
                'license_number': 'RN12345'
            },
            {
                'username': 'nurse.david',
                'email': 'david.nurse@hospital.com',
                'password': 'nurse123',
                'full_name': 'David Brown',
                'role': 'nurse',
                'department': 'ICU',
                'phone': '+1-555-0302',
                'employee_id': 'NUR002',
                'license_number': 'RN12346'
            },
            
            # Staff Accounts (Receptionist)
            {
                'username': 'receptionist1',
                'email': 'reception@hospital.com',
                'password': 'staff123',
                'full_name': 'Lisa Anderson',
                'role': 'receptionist',
                'department': 'Front Desk',
                'phone': '+1-555-0401',
                'employee_id': 'REC001'
            },
            {
                'username': 'receptionist2',
                'email': 'reception2@hospital.com',
                'password': 'staff123',
                'full_name': 'James Miller',
                'role': 'receptionist',
                'department': 'Front Desk',
                'phone': '+1-555-0402',
                'employee_id': 'REC002'
            },
            
            # Staff Accounts (Lab Technician)
            {
                'username': 'lab.tech1',
                'email': 'lab1@hospital.com',
                'password': 'lab123',
                'full_name': 'Robert Davis',
                'role': 'lab_tech',
                'department': 'Laboratory',
                'phone': '+1-555-0501',
                'employee_id': 'LAB001',
                'license_number': 'LT12345'
            },
            {
                'username': 'lab.tech2',
                'email': 'lab2@hospital.com',
                'password': 'lab123',
                'full_name': 'Jennifer Garcia',
                'role': 'lab_tech',
                'department': 'Laboratory',
                'phone': '+1-555-0502',
                'employee_id': 'LAB002',
                'license_number': 'LT12346'
            },
            
            # Customer/Patient Accounts
            {
                'username': 'patient1',
                'email': 'john.doe@email.com',
                'password': 'patient123',
                'full_name': 'John Doe',
                'role': 'patient',
                'department': None,
                'phone': '+1-555-0601',
                'employee_id': None
            },
            {
                'username': 'patient2',
                'email': 'jane.smith@email.com',
                'password': 'patient123',
                'full_name': 'Jane Smith',
                'role': 'patient',
                'department': None,
                'phone': '+1-555-0602',
                'employee_id': None
            },
            {
                'username': 'patient3',
                'email': 'bob.johnson@email.com',
                'password': 'patient123',
                'full_name': 'Bob Johnson',
                'role': 'patient',
                'department': None,
                'phone': '+1-555-0603',
                'employee_id': None
            }
        ]
        
        # Insert accounts
        created_count = 0
        skipped_count = 0
        
        for account in accounts:
            # Check if user already exists
            cursor.execute("SELECT id FROM web_user WHERE username = ? OR email = ?", 
                         (account['username'], account['email']))
            existing = cursor.fetchone()
            
            if existing:
                print(f"  Skipped {account['username']} - already exists")
                skipped_count += 1
                continue
            
            # Hash the password
            password_hash = generate_password_hash(account['password'])
            
            # Insert the user
            cursor.execute("""
                INSERT INTO web_user (
                    username, email, password_hash, full_name, role, 
                    department, phone, employee_id, specialization, 
                    license_number, is_active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                account['username'],
                account['email'],
                password_hash,
                account['full_name'],
                account['role'],
                account.get('department'),
                account['phone'],
                account.get('employee_id'),
                account.get('specialization'),
                account.get('license_number'),
                True,
                datetime.utcnow()
            ))
            
            print(f"  Created {account['username']} ({account['role']})")
            created_count += 1
        
        # Commit changes
        conn.commit()
        
        print(f"\nAccount creation summary:")
        print(f"  Created: {created_count} accounts")
        print(f"  Skipped: {skipped_count} accounts (already exist)")
        
        # Show final user list
        cursor.execute("SELECT username, role, full_name FROM web_user ORDER BY role, username")
        all_users = cursor.fetchall()
        
        print(f"\nAll users in database ({len(all_users)} total):")
        current_role = None
        for username, role, full_name in all_users:
            if role != current_role:
                print(f"\n{role.upper()}S:")
                current_role = role
            print(f"  {username} - {full_name}")
        
        conn.close()
        
        print("\n" + "="*50)
        print("LOGIN CREDENTIALS:")
        print("="*50)
        print("ADMIN ACCOUNTS:")
        print("  Username: superadmin | Password: admin123")
        print("  Username: hradmin    | Password: hr123")
        print("\nDOCTOR ACCOUNTS:")
        print("  Username: dr.smith    | Password: doctor123")
        print("  Username: dr.johnson  | Password: doctor123")
        print("  Username: dr.williams | Password: doctor123")
        print("\nSTAFF ACCOUNTS:")
        print("  Username: nurse.mary     | Password: nurse123")
        print("  Username: nurse.david    | Password: nurse123")
        print("  Username: receptionist1  | Password: staff123")
        print("  Username: receptionist2  | Password: staff123")
        print("  Username: lab.tech1      | Password: lab123")
        print("  Username: lab.tech2      | Password: lab123")
        print("\nPATIENT/CUSTOMER ACCOUNTS:")
        print("  Username: patient1 | Password: patient123")
        print("  Username: patient2 | Password: patient123")
        print("  Username: patient3 | Password: patient123")
        print("="*50)
        
    except Exception as e:
        print(f"Error: {e}")
        if 'conn' in locals():
            conn.rollback()

if __name__ == "__main__":
    create_accounts()