#!/usr/bin/env python3
"""
Script to update database schema with missing columns
"""

import sqlite3
import os

def update_database_schema():
    """Update database schema with missing columns"""
    db_path = os.path.join('instance', 'hospital_web.db')
    
    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table info
        cursor.execute("PRAGMA table_info(web_appointment)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Check and add missing columns for web_appointment table
        missing_columns = []
        if 'check_in_time' not in columns:
            missing_columns.append('check_in_time DATETIME')
        if 'consultation_start' not in columns:
            missing_columns.append('consultation_start DATETIME')
        if 'consultation_end' not in columns:
            missing_columns.append('consultation_end DATETIME')
        if 'meeting_link' not in columns:
            missing_columns.append('meeting_link VARCHAR(500)')
        
        if missing_columns:
            print("Adding missing columns to web_appointment table...")
            for column in missing_columns:
                try:
                    cursor.execute(f"ALTER TABLE web_appointment ADD COLUMN {column}")
                    print(f"Added column: {column}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print(f"Column already exists: {column}")
                    else:
                        print(f"Error adding column {column}: {e}")
        else:
            print("All web_appointment columns are present")
        
        # Check bill table for missing columns
        cursor.execute("PRAGMA table_info(bill)")
        bill_columns = [row[1] for row in cursor.fetchall()]
        
        missing_bill_columns = []
        if 'prescription_id' not in bill_columns:
            missing_bill_columns.append('prescription_id INTEGER')
        if 'bill_type' not in bill_columns:
            missing_bill_columns.append('bill_type VARCHAR(20)')
        if 'subtotal' not in bill_columns:
            missing_bill_columns.append('subtotal FLOAT')
        if 'discount_amount' not in bill_columns:
            missing_bill_columns.append('discount_amount FLOAT')
        if 'tax_amount' not in bill_columns:
            missing_bill_columns.append('tax_amount FLOAT')
        if 'total_amount' not in bill_columns:
            missing_bill_columns.append('total_amount FLOAT')
        if 'final_amount' not in bill_columns:
            missing_bill_columns.append('final_amount FLOAT')
        if 'paid_amount' not in bill_columns:
            missing_bill_columns.append('paid_amount FLOAT')
        if 'balance_amount' not in bill_columns:
            missing_bill_columns.append('balance_amount FLOAT')
        if 'payment_status' not in bill_columns:
            missing_bill_columns.append('payment_status VARCHAR(20)')
        if 'insurance_claim_amount' not in bill_columns:
            missing_bill_columns.append('insurance_claim_amount FLOAT')
        if 'created_by' not in bill_columns:
            missing_bill_columns.append('created_by INTEGER')
        
        if missing_bill_columns:
            print("\nAdding missing columns to bill table...")
            for column in missing_bill_columns:
                try:
                    cursor.execute(f"ALTER TABLE bill ADD COLUMN {column}")
                    print(f"Added column: {column}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print(f"Column already exists: {column}")
                    else:
                        print(f"Error adding column {column}: {e}")
        else:
            print("\nAll bill columns are present")
        
        # Check medicine table for missing columns
        cursor.execute("PRAGMA table_info(medicine)")
        medicine_columns = [row[1] for row in cursor.fetchall()]
        
        missing_medicine_columns = []
        if 'min_stock_level' not in medicine_columns:
            missing_medicine_columns.append('min_stock_level INTEGER DEFAULT 10')
        if 'reorder_level' not in medicine_columns:
            missing_medicine_columns.append('reorder_level INTEGER DEFAULT 10')
        
        if missing_medicine_columns:
            print("\nAdding missing columns to medicine table...")
            for column in missing_medicine_columns:
                try:
                    cursor.execute(f"ALTER TABLE medicine ADD COLUMN {column}")
                    print(f"Added column: {column}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print(f"Column already exists: {column}")
                    else:
                        print(f"Error adding column {column}: {e}")
        else:
            print("\nAll medicine columns are present")
        
        # Check other tables if needed
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Check if other tables need updates
        print(f"\nFound tables: {', '.join(tables)}")
        
        conn.commit()
        conn.close()
        print("Database schema updated successfully!")
        
    except Exception as e:
        print(f"Error updating database: {e}")
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    update_database_schema()