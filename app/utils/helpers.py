"""
Helper functions for Hospital Management System
"""

import os
from datetime import datetime
from werkzeug.utils import secure_filename
from app import db
from app.models.admin import HospitalSetting

def get_all_settings():
    """Get all settings from database as a dictionary"""
    settings = {}
    try:
        for setting in HospitalSetting.query.all():
            # Convert setting value based on type
            if setting.setting_type == 'number':
                try:
                    settings[setting.setting_key] = float(setting.setting_value)
                except (ValueError, TypeError):
                    settings[setting.setting_key] = 0.0
            elif setting.setting_type == 'boolean':
                settings[setting.setting_key] = setting.setting_value.lower() in ('true', '1', 'yes')
            else:
                settings[setting.setting_key] = setting.setting_value
    except Exception as e:
        # If table doesn't exist or query fails, return default settings
        print(f"Warning: Could not load settings from database: {e}")
        settings = {
            'hospital_name': 'MediCare Pro',
            'hospital_tagline': 'Your Health, Our Priority',
            'primary_color': '#0d6efd',
            'secondary_color': '#6c757d',
            'currency': 'USD',
            'password_min_length': 8,
            'password_expiry_days': 90,
            'default_language': 'en',
            'enable_multilingual': False,
        }
    
    # Ensure we always have default values for required settings
    default_values = {
        'hospital_name': 'MediCare Pro',
        'hospital_tagline': 'Your Health, Our Priority',
        'primary_color': '#0d6efd',
        'secondary_color': '#6c757d',
        'currency': 'USD',
        'password_min_length': 8,
        'password_expiry_days': 90,
        'default_language': 'en',
        'enable_multilingual': False,
    }
    
    for key, default_value in default_values.items():
        if key not in settings:
            settings[key] = default_value
    
    return settings

def update_setting(key, value, setting_type='string', category='general', description=''):
    """Update or create a setting"""
    setting = HospitalSetting.query.filter_by(setting_key=key).first()
    if setting:
        setting.setting_value = str(value)
        setting.setting_type = setting_type
        setting.category = category
        setting.description = description
        setting.updated_at = datetime.utcnow()
    else:
        setting = HospitalSetting(
            setting_key=key,
            setting_value=str(value),
            setting_type=setting_type,
            category=category,
            description=description
        )
        db.session.add(setting)
    return setting

def save_uploaded_file(file, upload_dir):
    """Save uploaded file and return the path"""
    if file and file.filename:
        filename = secure_filename(file.filename)
        # Create unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{filename}"
        
        # Ensure upload directory exists
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        return file_path
    return None

def generate_patient_id():
    """Generate unique patient ID"""
    from app.models.patient import WebPatient
    count = WebPatient.query.count()
    return f'P{count + 1:06d}'
