#!/usr/bin/env python3
"""
Hospital Management System Configuration
Centralized configuration for all system components
"""

import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///instance/hospital_web.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security Configuration
    SESSION_TIMEOUT = timedelta(hours=8)
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_SPECIAL = True
    PASSWORD_REQUIRE_NUMBERS = True
    PASSWORD_REQUIRE_UPPERCASE = True
    
    # Backup Configuration
    BACKUP_CONFIG = {
        'retention_days': int(os.environ.get('BACKUP_RETENTION_DAYS', 30)),
        'max_backups': int(os.environ.get('BACKUP_MAX_COUNT', 50)),
        'compression': os.environ.get('BACKUP_COMPRESSION', 'true').lower() == 'true',
        'email_notifications': os.environ.get('BACKUP_EMAIL_NOTIFICATIONS', 'true').lower() == 'true',
        'schedule_enabled': os.environ.get('BACKUP_SCHEDULE_ENABLED', 'true').lower() == 'true'
    }
    
    # Email Configuration
    EMAIL_CONFIG = {
        'enabled': os.environ.get('EMAIL_ENABLED', 'true').lower() == 'true',
        'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
        'smtp_port': int(os.environ.get('SMTP_PORT', 587)),
        'username': os.environ.get('SMTP_USERNAME', ''),
        'password': os.environ.get('SMTP_PASSWORD', ''),
        'from_name': os.environ.get('EMAIL_FROM_NAME', 'Hospital Management System'),
        'use_tls': os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'
    }
    
    # SMS Configuration (Twilio)
    SMS_CONFIG = {
        'enabled': os.environ.get('SMS_ENABLED', 'false').lower() == 'true',
        'twilio_account_sid': os.environ.get('TWILIO_ACCOUNT_SID', ''),
        'twilio_auth_token': os.environ.get('TWILIO_AUTH_TOKEN', ''),
        'twilio_phone_number': os.environ.get('TWILIO_PHONE_NUMBER', '')
    }
    
    # WhatsApp Configuration (Twilio)
    WHATSAPP_CONFIG = {
        'enabled': os.environ.get('WHATSAPP_ENABLED', 'false').lower() == 'true',
        'twilio_account_sid': os.environ.get('TWILIO_ACCOUNT_SID', ''),
        'twilio_auth_token': os.environ.get('TWILIO_AUTH_TOKEN', ''),
        'whatsapp_number': os.environ.get('WHATSAPP_NUMBER', '')  # Format: whatsapp:+1234567890
    }
    
    # Push Notification Configuration
    PUSH_CONFIG = {
        'enabled': os.environ.get('PUSH_ENABLED', 'false').lower() == 'true',
        'firebase_server_key': os.environ.get('FIREBASE_SERVER_KEY', ''),
        'firebase_sender_id': os.environ.get('FIREBASE_SENDER_ID', '')
    }
    
    # Two-Factor Authentication Configuration
    TWO_FA_CONFIG = {
        'issuer_name': os.environ.get('TWO_FA_ISSUER', 'Hospital Management System'),
        'backup_codes_count': int(os.environ.get('TWO_FA_BACKUP_CODES', 10)),
        'token_validity_minutes': int(os.environ.get('TWO_FA_TOKEN_VALIDITY', 5))
    }
    
    # Audit Configuration
    AUDIT_CONFIG = {
        'log_retention_days': int(os.environ.get('AUDIT_RETENTION_DAYS', 365)),
        'log_file_rotation': os.environ.get('AUDIT_LOG_ROTATION', 'daily'),
        'sensitive_data_masking': os.environ.get('AUDIT_MASK_SENSITIVE', 'true').lower() == 'true',
        'real_time_alerts': os.environ.get('AUDIT_REAL_TIME_ALERTS', 'true').lower() == 'true'
    }
    
    # Notification Configuration
    NOTIFICATION_CONFIG = {
        'appointment_reminder_hours': [24, 2],  # Hours before appointment
        'medication_reminder_enabled': os.environ.get('MEDICATION_REMINDERS', 'true').lower() == 'true',
        'lab_result_notification': os.environ.get('LAB_RESULT_NOTIFICATIONS', 'true').lower() == 'true',
        'bill_reminder_days': [7, 3, 1],  # Days before due date
        'emergency_notification_enabled': os.environ.get('EMERGENCY_NOTIFICATIONS', 'true').lower() == 'true'
    }
    
    # Export/Import Configuration
    EXPORT_CONFIG = {
        'max_export_records': int(os.environ.get('MAX_EXPORT_RECORDS', 10000)),
        'export_retention_days': int(os.environ.get('EXPORT_RETENTION_DAYS', 7)),
        'allow_sensitive_export': os.environ.get('ALLOW_SENSITIVE_EXPORT', 'false').lower() == 'true',
        'fhir_version': os.environ.get('FHIR_VERSION', 'R4')
    }
    
    # Security Configuration
    SECURITY_CONFIG = {
        'max_login_attempts': int(os.environ.get('MAX_LOGIN_ATTEMPTS', 5)),
        'lockout_duration_minutes': int(os.environ.get('LOCKOUT_DURATION', 30)),
        'session_timeout_minutes': int(os.environ.get('SESSION_TIMEOUT', 480)),  # 8 hours
        'password_expiry_days': int(os.environ.get('PASSWORD_EXPIRY_DAYS', 90)),
        'ip_whitelist_enabled': os.environ.get('IP_WHITELIST_ENABLED', 'false').lower() == 'true',
        'ip_whitelist': os.environ.get('IP_WHITELIST', '').split(',') if os.environ.get('IP_WHITELIST') else []
    }
    
    # Hospital Information
    HOSPITAL_INFO = {
        'name': os.environ.get('HOSPITAL_NAME', 'MediCare Pro Hospital'),
        'address': os.environ.get('HOSPITAL_ADDRESS', '123 Healthcare Ave, Medical City, MC 12345'),
        'phone': os.environ.get('HOSPITAL_PHONE', '+1-234-567-8900'),
        'email': os.environ.get('HOSPITAL_EMAIL', 'info@medicareprohospital.com'),
        'website': os.environ.get('HOSPITAL_WEBSITE', 'https://medicareprohospital.com'),
        'emergency_phone': os.environ.get('HOSPITAL_EMERGENCY_PHONE', '+1-234-567-8911'),
        'billing_phone': os.environ.get('HOSPITAL_BILLING_PHONE', '+1-234-567-8901'),
        'license_number': os.environ.get('HOSPITAL_LICENSE', 'HL-2024-001'),
        'tax_id': os.environ.get('HOSPITAL_TAX_ID', '12-3456789')
    }
    
    # Integration Configuration
    INTEGRATION_CONFIG = {
        'hl7_enabled': os.environ.get('HL7_ENABLED', 'false').lower() == 'true',
        'fhir_enabled': os.environ.get('FHIR_ENABLED', 'true').lower() == 'true',
        'payment_gateway': os.environ.get('PAYMENT_GATEWAY', 'stripe'),  # stripe, razorpay, paypal
        'lab_integration': os.environ.get('LAB_INTEGRATION', 'false').lower() == 'true',
        'imaging_integration': os.environ.get('IMAGING_INTEGRATION', 'false').lower() == 'true'
    }
    
    # Payment Gateway Configuration
    PAYMENT_CONFIG = {
        'stripe': {
            'publishable_key': os.environ.get('STRIPE_PUBLISHABLE_KEY', ''),
            'secret_key': os.environ.get('STRIPE_SECRET_KEY', ''),
            'webhook_secret': os.environ.get('STRIPE_WEBHOOK_SECRET', '')
        },
        'razorpay': {
            'key_id': os.environ.get('RAZORPAY_KEY_ID', ''),
            'key_secret': os.environ.get('RAZORPAY_KEY_SECRET', '')
        },
        'paypal': {
            'client_id': os.environ.get('PAYPAL_CLIENT_ID', ''),
            'client_secret': os.environ.get('PAYPAL_CLIENT_SECRET', ''),
            'mode': os.environ.get('PAYPAL_MODE', 'sandbox')  # sandbox or live
        }
    }
    
    # File Upload Configuration
    UPLOAD_CONFIG = {
        'max_file_size': int(os.environ.get('MAX_FILE_SIZE', 16 * 1024 * 1024)),  # 16MB
        'allowed_extensions': os.environ.get('ALLOWED_EXTENSIONS', 'pdf,jpg,jpeg,png,doc,docx').split(','),
        'upload_folder': os.environ.get('UPLOAD_FOLDER', 'uploads'),
        'virus_scan_enabled': os.environ.get('VIRUS_SCAN_ENABLED', 'false').lower() == 'true'
    }
    
    # Logging Configuration
    LOGGING_CONFIG = {
        'level': os.environ.get('LOG_LEVEL', 'INFO'),
        'file_logging': os.environ.get('FILE_LOGGING', 'true').lower() == 'true',
        'log_file': os.environ.get('LOG_FILE', 'hospital_management.log'),
        'max_log_size': int(os.environ.get('MAX_LOG_SIZE', 10 * 1024 * 1024)),  # 10MB
        'backup_count': int(os.environ.get('LOG_BACKUP_COUNT', 5))
    }

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    
    # Override for development
    BACKUP_CONFIG = Config.BACKUP_CONFIG.copy()
    BACKUP_CONFIG['schedule_enabled'] = False  # Disable scheduled backups in dev
    
    SECURITY_CONFIG = Config.SECURITY_CONFIG.copy()
    SECURITY_CONFIG['max_login_attempts'] = 10  # More lenient in dev
    SECURITY_CONFIG['lockout_duration_minutes'] = 5

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Stricter security in production
    SECURITY_CONFIG = Config.SECURITY_CONFIG.copy()
    SECURITY_CONFIG['max_login_attempts'] = 3
    SECURITY_CONFIG['lockout_duration_minutes'] = 60
    
    # Enable all security features
    AUDIT_CONFIG = Config.AUDIT_CONFIG.copy()
    AUDIT_CONFIG['real_time_alerts'] = True

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable external services in testing
    EMAIL_CONFIG = Config.EMAIL_CONFIG.copy()
    EMAIL_CONFIG['enabled'] = False
    
    SMS_CONFIG = Config.SMS_CONFIG.copy()
    SMS_CONFIG['enabled'] = False
    
    BACKUP_CONFIG = Config.BACKUP_CONFIG.copy()
    BACKUP_CONFIG['schedule_enabled'] = False

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])

# Environment-specific settings loader
def load_config_from_file(config_file='config.json'):
    """Load configuration from JSON file if it exists"""
    import json
    from pathlib import Path
    
    config_path = Path(config_file)
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
            
            # Update environment variables with file config
            for key, value in file_config.items():
                if key not in os.environ:
                    os.environ[key] = str(value)
                    
        except Exception as e:
            print(f"Warning: Could not load config file {config_file}: {e}")

# Load configuration from file on import
load_config_from_file()

# Validation functions
def validate_config():
    """Validate critical configuration settings"""
    errors = []
    
    # Check required email settings if email is enabled
    if Config.EMAIL_CONFIG['enabled']:
        if not Config.EMAIL_CONFIG['username']:
            errors.append("SMTP_USERNAME is required when email is enabled")
        if not Config.EMAIL_CONFIG['password']:
            errors.append("SMTP_PASSWORD is required when email is enabled")
    
    # Check SMS settings if SMS is enabled
    if Config.SMS_CONFIG['enabled']:
        if not Config.SMS_CONFIG['twilio_account_sid']:
            errors.append("TWILIO_ACCOUNT_SID is required when SMS is enabled")
        if not Config.SMS_CONFIG['twilio_auth_token']:
            errors.append("TWILIO_AUTH_TOKEN is required when SMS is enabled")
    
    # Check database URL
    if not Config.SQLALCHEMY_DATABASE_URI:
        errors.append("DATABASE_URL is required")
    
    # Check secret key in production
    env = os.environ.get('FLASK_ENV', 'development')
    if env == 'production' and Config.SECRET_KEY == 'your-secret-key-change-in-production':
        errors.append("SECRET_KEY must be changed in production")
    
    return errors

if __name__ == '__main__':
    # Validate configuration when run directly
    errors = validate_config()
    if errors:
        print("Configuration Errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("Configuration validation passed!")
    
    # Print current configuration (non-sensitive values only)
    print("\nCurrent Configuration:")
    print(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    print(f"Database: {Config.SQLALCHEMY_DATABASE_URI}")
    print(f"Email Enabled: {Config.EMAIL_CONFIG['enabled']}")
    print(f"SMS Enabled: {Config.SMS_CONFIG['enabled']}")
    print(f"2FA Enabled: {Config.TWO_FA_CONFIG['issuer_name']}")
    print(f"Backup Retention: {Config.BACKUP_CONFIG['retention_days']} days")