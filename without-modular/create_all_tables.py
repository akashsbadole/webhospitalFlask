#!/usr/bin/env python3
"""
Script to create all missing database tables by importing the web_app models
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_all_tables():
    """Create all missing database tables"""
    try:
        # Import Flask app and database
        from web_app import app, db
        
        with app.app_context():
            print("Creating all database tables...")
            
            # Create all tables defined in models
            db.create_all()
            
            print("✓ All database tables created successfully")
            
            # Check if HospitalSetting table has data
            from web_app import HospitalSetting
            
            settings_count = HospitalSetting.query.count()
            print(f"Current settings count: {settings_count}")
            
            if settings_count == 0:
                print("Adding default settings...")
                
                # Add default settings
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
                print("✓ Default settings added")
            
            # Verify settings
            final_count = HospitalSetting.query.count()
            print(f"✓ Total settings in database: {final_count}")
            
            return True
            
    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_all_tables()
    if success:
        print("\n✓ Database initialization completed successfully!")
        print("You can now access the settings page without the 'settings' undefined error.")
    else:
        print("\n✗ Database initialization failed!")
        sys.exit(1)