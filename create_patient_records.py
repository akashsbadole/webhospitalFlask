#!/usr/bin/env python3
"""
Create Patient Records for Customer Accounts
This script creates detailed patient records for the customer accounts
"""

import sqlite3
import os
from datetime import datetime

def create_patient_records():
    """Create detailed patient records for customer accounts"""
    
    db_file = 'instance/hospital_web.db'
    
    if not os.path.exists(db_file):
        print(f"Database file {db_file} does not exist")
        return
    
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Check if web_patient table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='web_patient';")
        result = cursor.fetchone()
        
        if not result:
            print("web_patient table does not exist. Creating it...")
            # Create the table if it doesn't exist
            cursor.execute("""
                CREATE TABLE web_patient (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id INTEGER,
                    patient_id VARCHAR(20) NOT NULL,
                    first_name VARCHAR(50) NOT NULL,
                    last_name VARCHAR(50) NOT NULL,
                    email VARCHAR(120),
                    phone VARCHAR(20) NOT NULL,
                    date_of_birth DATE,
                    gender VARCHAR(10),
                    address TEXT,
                    city VARCHAR(50),
                    state VARCHAR(50),
                    zip_code VARCHAR(10),
                    country VARCHAR(50),
                    emergency_contact VARCHAR(100),
                    emergency_phone VARCHAR(20),
                    emergency_relation VARCHAR(50),
                    blood_group VARCHAR(5),
                    allergies TEXT,
                    medical_history TEXT,
                    insurance_provider VARCHAR(100),
                    insurance_number VARCHAR(50),
                    insurance_expiry DATE,
                    id_proof_type VARCHAR(50),
                    id_proof_number VARCHAR(50),
                    marital_status VARCHAR(20),
                    occupation VARCHAR(100),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("Created web_patient table")
        
        # Sample patient records
        patients = [
            {
                'patient_id': 'PAT001',
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john.doe@email.com',
                'phone': '+1-555-0601',
                'date_of_birth': '1985-03-15',
                'gender': 'Male',
                'address': '123 Main Street, Apt 4B',
                'city': 'New York',
                'state': 'NY',
                'zip_code': '10001',
                'country': 'USA',
                'emergency_contact': 'Jane Doe',
                'emergency_phone': '+1-555-0611',
                'emergency_relation': 'Spouse',
                'blood_group': 'O+',
                'allergies': 'Penicillin, Shellfish',
                'medical_history': 'Hypertension, Diabetes Type 2',
                'insurance_provider': 'Blue Cross Blue Shield',
                'insurance_number': 'BC123456789',
                'insurance_expiry': '2024-12-31',
                'id_proof_type': 'Driver License',
                'id_proof_number': 'DL123456789',
                'marital_status': 'Married',
                'occupation': 'Software Engineer'
            },
            {
                'patient_id': 'PAT002',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'email': 'jane.smith@email.com',
                'phone': '+1-555-0602',
                'date_of_birth': '1990-07-22',
                'gender': 'Female',
                'address': '456 Oak Avenue',
                'city': 'Los Angeles',
                'state': 'CA',
                'zip_code': '90210',
                'country': 'USA',
                'emergency_contact': 'Robert Smith',
                'emergency_phone': '+1-555-0612',
                'emergency_relation': 'Father',
                'blood_group': 'A+',
                'allergies': 'None known',
                'medical_history': 'Asthma, Seasonal allergies',
                'insurance_provider': 'Aetna',
                'insurance_number': 'AET987654321',
                'insurance_expiry': '2024-11-30',
                'id_proof_type': 'Passport',
                'id_proof_number': 'P123456789',
                'marital_status': 'Single',
                'occupation': 'Teacher'
            },
            {
                'patient_id': 'PAT003',
                'first_name': 'Bob',
                'last_name': 'Johnson',
                'email': 'bob.johnson@email.com',
                'phone': '+1-555-0603',
                'date_of_birth': '1978-11-08',
                'gender': 'Male',
                'address': '789 Pine Street',
                'city': 'Chicago',
                'state': 'IL',
                'zip_code': '60601',
                'country': 'USA',
                'emergency_contact': 'Mary Johnson',
                'emergency_phone': '+1-555-0613',
                'emergency_relation': 'Wife',
                'blood_group': 'B+',
                'allergies': 'Latex, Peanuts',
                'medical_history': 'High cholesterol, Previous heart surgery (2020)',
                'insurance_provider': 'Cigna',
                'insurance_number': 'CIG456789123',
                'insurance_expiry': '2025-01-31',
                'id_proof_type': 'Driver License',
                'id_proof_number': 'DL987654321',
                'marital_status': 'Married',
                'occupation': 'Accountant'
            }
        ]
        
        created_count = 0
        skipped_count = 0
        
        for patient in patients:
            # Check if patient already exists
            cursor.execute("SELECT id FROM web_patient WHERE patient_id = ? OR email = ?", 
                         (patient['patient_id'], patient['email']))
            existing = cursor.fetchone()
            
            if existing:
                print(f"  Skipped {patient['first_name']} {patient['last_name']} - already exists")
                skipped_count += 1
                continue
            
            # Insert the patient record
            cursor.execute("""
                INSERT INTO web_patient (
                    patient_id, first_name, last_name, email, phone, date_of_birth,
                    gender, address, city, state, zip_code, country,
                    emergency_contact, emergency_phone, emergency_relation,
                    blood_group, allergies, medical_history,
                    insurance_provider, insurance_number, insurance_expiry,
                    id_proof_type, id_proof_number, marital_status, occupation,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                patient['patient_id'],
                patient['first_name'],
                patient['last_name'],
                patient['email'],
                patient['phone'],
                patient['date_of_birth'],
                patient['gender'],
                patient['address'],
                patient['city'],
                patient['state'],
                patient['zip_code'],
                patient['country'],
                patient['emergency_contact'],
                patient['emergency_phone'],
                patient['emergency_relation'],
                patient['blood_group'],
                patient['allergies'],
                patient['medical_history'],
                patient['insurance_provider'],
                patient['insurance_number'],
                patient['insurance_expiry'],
                patient['id_proof_type'],
                patient['id_proof_number'],
                patient['marital_status'],
                patient['occupation'],
                datetime.utcnow(),
                datetime.utcnow()
            ))
            
            print(f"  Created patient record for {patient['first_name']} {patient['last_name']} ({patient['patient_id']})")
            created_count += 1
        
        # Commit changes
        conn.commit()
        
        print(f"\nPatient record creation summary:")
        print(f"  Created: {created_count} patient records")
        print(f"  Skipped: {skipped_count} patient records (already exist)")
        
        # Show all patient records
        cursor.execute("SELECT patient_id, first_name, last_name, email, phone FROM web_patient ORDER BY patient_id")
        all_patients = cursor.fetchall()
        
        print(f"\nAll patient records ({len(all_patients)} total):")
        for patient_id, first_name, last_name, email, phone in all_patients:
            print(f"  {patient_id}: {first_name} {last_name} - {email} - {phone}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        if 'conn' in locals():
            conn.rollback()

if __name__ == "__main__":
    create_patient_records()