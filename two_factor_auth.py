#!/usr/bin/env python3
"""
Two-Factor Authentication (2FA) System
Implements TOTP-based 2FA, backup codes, and SMS verification
"""

import pyotp
import qrcode
import io
import base64
from datetime import datetime, timedelta
import secrets
import string
from flask import session, request
from flask_login import current_user
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from twilio.rest import Client
import json
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TwoFactorAuth:
    def __init__(self, db, app):
        self.db = db
        self.app = app
        self.setup_2fa_tables()
        
        # Configuration
        self.config = {
            'issuer_name': 'Hospital Management System',
            'backup_codes_count': 10,
            'sms_enabled': False,  # Configure in production
            'email_enabled': True,
            'twilio_account_sid': '',  # Configure in production
            'twilio_auth_token': '',  # Configure in production
            'twilio_phone_number': '',  # Configure in production
            'email_config': {
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'username': '',  # Configure in production
                'password': ''   # Configure in production
            }
        }
    
    def setup_2fa_tables(self):
        """Create 2FA related tables"""
        
        class UserTwoFactor(self.db.Model):
            __tablename__ = 'user_two_factor'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            user_id = self.db.Column(self.db.Integer, nullable=False, unique=True)
            secret_key = self.db.Column(self.db.String(32), nullable=False)
            is_enabled = self.db.Column(self.db.Boolean, default=False)
            backup_codes = self.db.Column(self.db.Text)  # JSON array of backup codes
            phone_number = self.db.Column(self.db.String(20))  # For SMS 2FA
            email_2fa_enabled = self.db.Column(self.db.Boolean, default=False)
            sms_2fa_enabled = self.db.Column(self.db.Boolean, default=False)
            app_2fa_enabled = self.db.Column(self.db.Boolean, default=False)
            created_at = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            last_used = self.db.Column(self.db.DateTime)
        
        class TwoFactorAttempt(self.db.Model):
            __tablename__ = 'two_factor_attempts'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            user_id = self.db.Column(self.db.Integer, nullable=False)
            attempt_type = self.db.Column(self.db.String(20), nullable=False)  # totp, sms, email, backup
            success = self.db.Column(self.db.Boolean, nullable=False)
            ip_address = self.db.Column(self.db.String(45))
            user_agent = self.db.Column(self.db.Text)
            timestamp = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            failure_reason = self.db.Column(self.db.String(100))
        
        class TwoFactorToken(self.db.Model):
            __tablename__ = 'two_factor_tokens'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            user_id = self.db.Column(self.db.Integer, nullable=False)
            token = self.db.Column(self.db.String(10), nullable=False)
            token_type = self.db.Column(self.db.String(20), nullable=False)  # sms, email
            expires_at = self.db.Column(self.db.DateTime, nullable=False)
            used = self.db.Column(self.db.Boolean, default=False)
            created_at = self.db.Column(self.db.DateTime, default=datetime.utcnow)
        
        # Store model classes
        self.UserTwoFactor = UserTwoFactor
        self.TwoFactorAttempt = TwoFactorAttempt
        self.TwoFactorToken = TwoFactorToken
        
        # Create tables
        self.db.create_all()
    
    def setup_2fa_for_user(self, user_id):
        """Initialize 2FA setup for a user"""
        try:
            # Check if 2FA already exists
            existing_2fa = self.UserTwoFactor.query.filter_by(user_id=user_id).first()
            if existing_2fa:
                return existing_2fa
            
            # Generate secret key
            secret = pyotp.random_base32()
            
            # Generate backup codes
            backup_codes = self._generate_backup_codes()
            
            # Create 2FA record
            user_2fa = self.UserTwoFactor(
                user_id=user_id,
                secret_key=secret,
                backup_codes=json.dumps(backup_codes)
            )
            
            self.db.session.add(user_2fa)
            self.db.session.commit()
            
            logger.info(f"2FA setup initialized for user {user_id}")
            return user_2fa
            
        except Exception as e:
            logger.error(f"Failed to setup 2FA for user {user_id}: {str(e)}")
            raise
    
    def generate_qr_code(self, user_id, username):
        """Generate QR code for TOTP setup"""
        try:
            user_2fa = self.UserTwoFactor.query.filter_by(user_id=user_id).first()
            if not user_2fa:
                user_2fa = self.setup_2fa_for_user(user_id)
            
            # Create TOTP URI
            totp = pyotp.TOTP(user_2fa.secret_key)
            provisioning_uri = totp.provisioning_uri(
                name=username,
                issuer_name=self.config['issuer_name']
            )
            
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            
            # Create QR code image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64 for web display
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            qr_code_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            
            return {
                'qr_code': qr_code_base64,
                'secret_key': user_2fa.secret_key,
                'backup_codes': json.loads(user_2fa.backup_codes)
            }
            
        except Exception as e:
            logger.error(f"Failed to generate QR code for user {user_id}: {str(e)}")
            raise
    
    def verify_totp_code(self, user_id, code):
        """Verify TOTP code"""
        try:
            user_2fa = self.UserTwoFactor.query.filter_by(user_id=user_id).first()
            if not user_2fa or not user_2fa.app_2fa_enabled:
                return False
            
            totp = pyotp.TOTP(user_2fa.secret_key)
            is_valid = totp.verify(code, valid_window=1)  # Allow 30 seconds window
            
            # Log attempt
            self._log_2fa_attempt(user_id, 'totp', is_valid, 
                                'Invalid code' if not is_valid else None)
            
            if is_valid:
                user_2fa.last_used = datetime.utcnow()
                self.db.session.commit()
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Failed to verify TOTP for user {user_id}: {str(e)}")
            self._log_2fa_attempt(user_id, 'totp', False, str(e))
            return False
    
    def verify_backup_code(self, user_id, code):
        """Verify backup code"""
        try:
            user_2fa = self.UserTwoFactor.query.filter_by(user_id=user_id).first()
            if not user_2fa:
                return False
            
            backup_codes = json.loads(user_2fa.backup_codes)
            
            if code in backup_codes:
                # Remove used backup code
                backup_codes.remove(code)
                user_2fa.backup_codes = json.dumps(backup_codes)
                user_2fa.last_used = datetime.utcnow()
                self.db.session.commit()
                
                self._log_2fa_attempt(user_id, 'backup', True)
                logger.info(f"Backup code used for user {user_id}")
                return True
            else:
                self._log_2fa_attempt(user_id, 'backup', False, 'Invalid backup code')
                return False
                
        except Exception as e:
            logger.error(f"Failed to verify backup code for user {user_id}: {str(e)}")
            self._log_2fa_attempt(user_id, 'backup', False, str(e))
            return False
    
    def send_sms_code(self, user_id, phone_number):
        """Send SMS verification code"""
        try:
            if not self.config['sms_enabled']:
                raise ValueError("SMS 2FA is not enabled")
            
            # Generate 6-digit code
            code = ''.join(secrets.choice(string.digits) for _ in range(6))
            
            # Store token
            token = self.TwoFactorToken(
                user_id=user_id,
                token=code,
                token_type='sms',
                expires_at=datetime.utcnow() + timedelta(minutes=5)
            )
            self.db.session.add(token)
            self.db.session.commit()
            
            # Send SMS using Twilio
            client = Client(
                self.config['twilio_account_sid'],
                self.config['twilio_auth_token']
            )
            
            message = client.messages.create(
                body=f"Your {self.config['issuer_name']} verification code is: {code}",
                from_=self.config['twilio_phone_number'],
                to=phone_number
            )
            
            logger.info(f"SMS code sent to user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send SMS code to user {user_id}: {str(e)}")
            return False
    
    def send_email_code(self, user_id, email):
        """Send email verification code"""
        try:
            if not self.config['email_enabled']:
                raise ValueError("Email 2FA is not enabled")
            
            # Generate 6-digit code
            code = ''.join(secrets.choice(string.digits) for _ in range(6))
            
            # Store token
            token = self.TwoFactorToken(
                user_id=user_id,
                token=code,
                token_type='email',
                expires_at=datetime.utcnow() + timedelta(minutes=10)
            )
            self.db.session.add(token)
            self.db.session.commit()
            
            # Send email
            subject = f"{self.config['issuer_name']} - Verification Code"
            body = f"""
            Your verification code is: {code}
            
            This code will expire in 10 minutes.
            
            If you didn't request this code, please contact your administrator immediately.
            """
            
            self._send_email(email, subject, body)
            
            logger.info(f"Email code sent to user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email code to user {user_id}: {str(e)}")
            return False
    
    def verify_sms_code(self, user_id, code):
        """Verify SMS code"""
        return self._verify_token_code(user_id, code, 'sms')
    
    def verify_email_code(self, user_id, code):
        """Verify email code"""
        return self._verify_token_code(user_id, code, 'email')
    
    def _verify_token_code(self, user_id, code, token_type):
        """Verify token-based code (SMS/Email)"""
        try:
            token = self.TwoFactorToken.query.filter_by(
                user_id=user_id,
                token=code,
                token_type=token_type,
                used=False
            ).first()
            
            if not token:
                self._log_2fa_attempt(user_id, token_type, False, 'Invalid code')
                return False
            
            if token.expires_at < datetime.utcnow():
                self._log_2fa_attempt(user_id, token_type, False, 'Expired code')
                return False
            
            # Mark token as used
            token.used = True
            self.db.session.commit()
            
            self._log_2fa_attempt(user_id, token_type, True)
            return True
            
        except Exception as e:
            logger.error(f"Failed to verify {token_type} code for user {user_id}: {str(e)}")
            self._log_2fa_attempt(user_id, token_type, False, str(e))
            return False
    
    def enable_2fa(self, user_id, method='app', verification_code=None, phone_number=None):
        """Enable 2FA for a user"""
        try:
            user_2fa = self.UserTwoFactor.query.filter_by(user_id=user_id).first()
            if not user_2fa:
                user_2fa = self.setup_2fa_for_user(user_id)
            
            # Verify the setup with a code
            if method == 'app' and verification_code:
                if not self.verify_totp_code(user_id, verification_code):
                    return False, "Invalid verification code"
                user_2fa.app_2fa_enabled = True
            
            elif method == 'sms' and phone_number:
                user_2fa.phone_number = phone_number
                user_2fa.sms_2fa_enabled = True
            
            elif method == 'email':
                user_2fa.email_2fa_enabled = True
            
            user_2fa.is_enabled = True
            self.db.session.commit()
            
            logger.info(f"2FA enabled for user {user_id} using method: {method}")
            return True, "2FA enabled successfully"
            
        except Exception as e:
            logger.error(f"Failed to enable 2FA for user {user_id}: {str(e)}")
            return False, str(e)
    
    def disable_2fa(self, user_id):
        """Disable 2FA for a user"""
        try:
            user_2fa = self.UserTwoFactor.query.filter_by(user_id=user_id).first()
            if user_2fa:
                user_2fa.is_enabled = False
                user_2fa.app_2fa_enabled = False
                user_2fa.sms_2fa_enabled = False
                user_2fa.email_2fa_enabled = False
                self.db.session.commit()
                
                logger.info(f"2FA disabled for user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to disable 2FA for user {user_id}: {str(e)}")
            return False
    
    def is_2fa_enabled(self, user_id):
        """Check if 2FA is enabled for a user"""
        user_2fa = self.UserTwoFactor.query.filter_by(user_id=user_id).first()
        return user_2fa and user_2fa.is_enabled
    
    def get_2fa_methods(self, user_id):
        """Get enabled 2FA methods for a user"""
        user_2fa = self.UserTwoFactor.query.filter_by(user_id=user_id).first()
        if not user_2fa or not user_2fa.is_enabled:
            return []
        
        methods = []
        if user_2fa.app_2fa_enabled:
            methods.append('app')
        if user_2fa.sms_2fa_enabled:
            methods.append('sms')
        if user_2fa.email_2fa_enabled:
            methods.append('email')
        
        return methods
    
    def regenerate_backup_codes(self, user_id):
        """Regenerate backup codes for a user"""
        try:
            user_2fa = self.UserTwoFactor.query.filter_by(user_id=user_id).first()
            if not user_2fa:
                return None
            
            backup_codes = self._generate_backup_codes()
            user_2fa.backup_codes = json.dumps(backup_codes)
            self.db.session.commit()
            
            logger.info(f"Backup codes regenerated for user {user_id}")
            return backup_codes
            
        except Exception as e:
            logger.error(f"Failed to regenerate backup codes for user {user_id}: {str(e)}")
            return None
    
    def _generate_backup_codes(self):
        """Generate backup codes"""
        codes = []
        for _ in range(self.config['backup_codes_count']):
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) 
                          for _ in range(8))
            # Format as XXXX-XXXX
            formatted_code = f"{code[:4]}-{code[4:]}"
            codes.append(formatted_code)
        return codes
    
    def _log_2fa_attempt(self, user_id, attempt_type, success, failure_reason=None):
        """Log 2FA attempt"""
        try:
            attempt = self.TwoFactorAttempt(
                user_id=user_id,
                attempt_type=attempt_type,
                success=success,
                ip_address=self._get_client_ip(),
                user_agent=request.headers.get('User-Agent', '') if request else '',
                failure_reason=failure_reason
            )
            
            self.db.session.add(attempt)
            self.db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to log 2FA attempt: {str(e)}")
    
    def _get_client_ip(self):
        """Get client IP address"""
        if not request:
            return 'unknown'
        
        if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
            return request.environ.get('REMOTE_ADDR', 'unknown')
        else:
            return request.environ['HTTP_X_FORWARDED_FOR']
    
    def _send_email(self, to_email, subject, body):
        """Send email notification"""
        try:
            config = self.config['email_config']
            
            if not config['username']:
                raise ValueError("Email configuration not set")
            
            msg = MimeMultipart()
            msg['From'] = config['username']
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
            server.starttls()
            server.login(config['username'], config['password'])
            
            text = msg.as_string()
            server.sendmail(config['username'], to_email, text)
            server.quit()
            
            logger.info(f"Email sent successfully to {to_email}")
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            raise
    
    def get_2fa_statistics(self, user_id=None, days=30):
        """Get 2FA usage statistics"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            query = self.TwoFactorAttempt.query.filter(
                self.TwoFactorAttempt.timestamp >= start_date
            )
            
            if user_id:
                query = query.filter(self.TwoFactorAttempt.user_id == user_id)
            
            attempts = query.all()
            
            stats = {
                'total_attempts': len(attempts),
                'successful_attempts': len([a for a in attempts if a.success]),
                'failed_attempts': len([a for a in attempts if not a.success]),
                'method_breakdown': {},
                'success_rate': 0
            }
            
            # Method breakdown
            for attempt in attempts:
                method = attempt.attempt_type
                if method not in stats['method_breakdown']:
                    stats['method_breakdown'][method] = {'total': 0, 'successful': 0}
                
                stats['method_breakdown'][method]['total'] += 1
                if attempt.success:
                    stats['method_breakdown'][method]['successful'] += 1
            
            # Calculate success rate
            if stats['total_attempts'] > 0:
                stats['success_rate'] = (stats['successful_attempts'] / stats['total_attempts']) * 100
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get 2FA statistics: {str(e)}")
            return None
    
    def cleanup_expired_tokens(self):
        """Clean up expired tokens"""
        try:
            expired_tokens = self.TwoFactorToken.query.filter(
                self.TwoFactorToken.expires_at < datetime.utcnow()
            ).all()
            
            for token in expired_tokens:
                self.db.session.delete(token)
            
            self.db.session.commit()
            
            logger.info(f"Cleaned up {len(expired_tokens)} expired 2FA tokens")
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired tokens: {str(e)}")

# Flask decorators and helpers
def require_2fa(f):
    """Decorator to require 2FA verification"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        
        # Check if 2FA is required and verified
        if hasattr(current_user, 'requires_2fa') and current_user.requires_2fa:
            if not session.get('2fa_verified'):
                return redirect(url_for('verify_2fa'))
        
        return f(*args, **kwargs)
    
    return decorated_function

def init_2fa(app, db):
    """Initialize 2FA system with Flask app"""
    two_factor_auth = TwoFactorAuth(db, app)
    
    # Add 2FA instance to app
    app.two_factor_auth = two_factor_auth
    
    # Schedule cleanup task
    def setup_2fa_cleanup():
        import threading
        import time
        
        def cleanup_task():
            while True:
                try:
                    with app.app_context():
                        two_factor_auth.cleanup_expired_tokens()
                    time.sleep(3600)  # Run every hour
                except Exception as e:
                    logger.error(f"2FA cleanup task failed: {str(e)}")
                    time.sleep(3600)
        
        cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
        cleanup_thread.start()
    
    # Start cleanup task
    setup_2fa_cleanup()
    
    return two_factor_auth