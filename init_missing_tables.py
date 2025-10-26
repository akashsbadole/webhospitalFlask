#!/usr/bin/env python3
"""
Script to create missing database tables
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Create a minimal Flask app for database operations
app = Flask(__name__)
app.config['SECRET_KEY'] = 'temp-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/hospital_web.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Import the models we need
class HospitalSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=True)
    setting_key = db.Column(db.String(100), nullable=False)
    setting_value = db.Column(db.Text)
    setting_type = db.Column(db.String(20), default='string')
    category = db.Column(db.String(50), default='general')
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp())

def create_missing_tables():
    """Create missing database tables"""
    with app.app_context():
        try:
            # Create the hospital_setting table
            db.create_all()
            print("✓ Created missing database tables")
            
            # Add some default settings
            default_settings = [
                ('hospital_name', 'MediCare Pro', 'string', 'organization', 'Hospital name'),
                ('hospital_tagline', 'Your Health, Our Priority', 'string', 'organization', 'Hospital tagline'),
                ('primary_color', '#0d6efd', 'string', 'organization', 'Primary theme color'),
                ('secondary_color', '#6c757d', 'string', 'organization', 'Secondary theme color'),
                ('currency', 'USD', 'string', 'billing', 'Default currency'),
                ('password_min_length', '8', 'number', 'security', 'Minimum password length'),
                ('password_expiry_days', '90', 'number', 'security', 'Password expiry in days'),
                ('default_language', 'en', 'string', 'organization', 'Default language'),
                ('enable_multilingual', 'false', 'boolean', 'organization', 'Enable multilingual support'),
            ]
            
            for key, value, setting_type, category, description in default_settings:
                existing = HospitalSetting.query.filter_by(setting_key=key).first()
                if not existing:
                    setting = HospitalSetting(
                        setting_key=key,
                        setting_value=value,
                        setting_type=setting_type,
                        category=category,
                        description=description
                    )
                    db.session.add(setting)
            
            db.session.commit()
            print("✓ Added default settings")
            
            # Verify the table was created
            from sqlalchemy import text
            result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='hospital_setting';")).fetchone()
            if result:
                count = db.session.execute(text("SELECT COUNT(*) FROM hospital_setting;")).fetchone()[0]
                print(f"✓ HospitalSetting table created successfully with {count} settings")
            else:
                print("✗ Failed to create HospitalSetting table")
                
        except Exception as e:
            print(f"✗ Error creating tables: {e}")
            db.session.rollback()

if __name__ == "__main__":
    create_missing_tables()