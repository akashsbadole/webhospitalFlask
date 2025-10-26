#!/usr/bin/env python3
"""
Advanced Security System
Implements IP whitelisting, session management, password policies, rate limiting, and CAPTCHA
"""

import hashlib
import secrets
import string
import ipaddress
from datetime import datetime, timedelta
import json
import logging
from flask import request, session, current_app, jsonify, abort
from flask_login import current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
from functools import wraps
import re
import base64
from PIL import Image, ImageDraw, ImageFont
import io
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedSecurity:
    def __init__(self, db, app):
        self.db = db
        self.app = app
        self.setup_security_tables()
        
        # Initialize Redis for rate limiting and session management
        try:
            self.redis_client = redis.Redis(
                host=app.config.get('REDIS_HOST', 'localhost'),
                port=app.config.get('REDIS_PORT', 6379),
                db=app.config.get('REDIS_DB', 0),
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
            self.redis_available = True
        except:
            self.redis_available = False
            logger.warning("Redis not available, using in-memory storage")
        
        # Initialize rate limiter
        self.limiter = Limiter(
            key_func=get_remote_address,
            default_limits=["1000 per hour"],
            storage_uri=f"redis://localhost:6379" if self.redis_available else "memory://"
        )
        self.limiter.init_app(app)
        
        # Security configuration
        self.config = {
            'password_policy': {
                'min_length': 8,
                'require_uppercase': True,
                'require_lowercase': True,
                'require_numbers': True,
                'require_special': True,
                'special_chars': '!@#$%^&*()_+-=[]{}|;:,.<>?',
                'max_age_days': 90,
                'history_count': 5,  # Remember last 5 passwords
                'lockout_attempts': 5,
                'lockout_duration_minutes': 30
            },
            'session_policy': {
                'timeout_minutes': 480,  # 8 hours
                'concurrent_sessions': 3,
                'secure_cookies': True,
                'httponly_cookies': True
            },
            'ip_security': {
                'whitelist_enabled': False,
                'whitelist_ips': [],
                'blacklist_enabled': True,
                'auto_blacklist_attempts': 10,
                'auto_blacklist_duration_hours': 24
            },
            'rate_limiting': {
                'login_attempts': "5 per minute",
                'api_calls': "100 per minute",
                'password_reset': "3 per hour"
            },
            'captcha': {
                'enabled': True,
                'length': 5,
                'width': 200,
                'height': 80,
                'font_size': 36
            }
        }
    
    def setup_security_tables(self):
        """Create security-related tables"""
        
        class PasswordHistory(self.db.Model):
            __tablename__ = 'password_history'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            user_id = self.db.Column(self.db.Integer, nullable=False)
            password_hash = self.db.Column(self.db.String(128), nullable=False)
            created_at = self.db.Column(self.db.DateTime, default=datetime.utcnow)
        
        class UserSession(self.db.Model):
            __tablename__ = 'user_sessions'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            user_id = self.db.Column(self.db.Integer, nullable=False)
            session_id = self.db.Column(self.db.String(128), unique=True, nullable=False)
            ip_address = self.db.Column(self.db.String(45))
            user_agent = self.db.Column(self.db.Text)
            created_at = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            last_activity = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            is_active = self.db.Column(self.db.Boolean, default=True)
            expires_at = self.db.Column(self.db.DateTime)
        
        class IPWhitelist(self.db.Model):
            __tablename__ = 'ip_whitelist'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            ip_address = self.db.Column(self.db.String(45), nullable=False)
            ip_range = self.db.Column(self.db.String(50))  # CIDR notation
            description = self.db.Column(self.db.String(200))
            created_by = self.db.Column(self.db.Integer)
            created_at = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            is_active = self.db.Column(self.db.Boolean, default=True)
        
        class IPBlacklist(self.db.Model):
            __tablename__ = 'ip_blacklist'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            ip_address = self.db.Column(self.db.String(45), nullable=False)
            reason = self.db.Column(self.db.String(200))
            blocked_at = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            blocked_until = self.db.Column(self.db.DateTime)
            is_permanent = self.db.Column(self.db.Boolean, default=False)
            created_by = self.db.Column(self.db.Integer)
        
        class SecurityEvent(self.db.Model):
            __tablename__ = 'security_events_advanced'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            event_type = self.db.Column(self.db.String(50), nullable=False)
            severity = self.db.Column(self.db.String(20), nullable=False)
            user_id = self.db.Column(self.db.Integer)
            ip_address = self.db.Column(self.db.String(45))
            user_agent = self.db.Column(self.db.Text)
            description = self.db.Column(self.db.Text)
            details = self.db.Column(self.db.Text)  # JSON
            timestamp = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            resolved = self.db.Column(self.db.Boolean, default=False)
        
        class CaptchaChallenge(self.db.Model):
            __tablename__ = 'captcha_challenges'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            challenge_id = self.db.Column(self.db.String(64), unique=True, nullable=False)
            solution = self.db.Column(self.db.String(10), nullable=False)
            ip_address = self.db.Column(self.db.String(45))
            created_at = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            expires_at = self.db.Column(self.db.DateTime)
            solved = self.db.Column(self.db.Boolean, default=False)
        
        # Store model classes
        self.PasswordHistory = PasswordHistory
        self.UserSession = UserSession
        self.IPWhitelist = IPWhitelist
        self.IPBlacklist = IPBlacklist
        self.SecurityEvent = SecurityEvent
        self.CaptchaChallenge = CaptchaChallenge
        
        # Create tables
        self.db.create_all()
    
    # ==================== PASSWORD POLICY ====================
    
    def validate_password(self, password, user_id=None):
        """Validate password against security policy"""
        errors = []
        policy = self.config['password_policy']
        
        # Length check
        if len(password) < policy['min_length']:
            errors.append(f"Password must be at least {policy['min_length']} characters long")
        
        # Character requirements
        if policy['require_uppercase'] and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if policy['require_lowercase'] and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if policy['require_numbers'] and not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        if policy['require_special']:
            special_chars = policy['special_chars']
            if not re.search(f'[{re.escape(special_chars)}]', password):
                errors.append(f"Password must contain at least one special character: {special_chars}")
        
        # Check against password history
        if user_id:
            if self._is_password_in_history(user_id, password):
                errors.append(f"Password cannot be one of your last {policy['history_count']} passwords")
        
        return len(errors) == 0, errors
    
    def _is_password_in_history(self, user_id, password):
        """Check if password was used recently"""
        from werkzeug.security import check_password_hash
        
        history_count = self.config['password_policy']['history_count']
        recent_passwords = self.PasswordHistory.query.filter_by(
            user_id=user_id
        ).order_by(self.PasswordHistory.created_at.desc()).limit(history_count).all()
        
        for hist_password in recent_passwords:
            if check_password_hash(hist_password.password_hash, password):
                return True
        
        return False
    
    def add_password_to_history(self, user_id, password_hash):
        """Add password to history"""
        try:
            # Add new password to history
            password_history = self.PasswordHistory(
                user_id=user_id,
                password_hash=password_hash
            )
            self.db.session.add(password_history)
            
            # Clean up old history entries
            history_count = self.config['password_policy']['history_count']
            old_entries = self.PasswordHistory.query.filter_by(
                user_id=user_id
            ).order_by(self.PasswordHistory.created_at.desc()).offset(history_count).all()
            
            for entry in old_entries:
                self.db.session.delete(entry)
            
            self.db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to add password to history: {str(e)}")
            self.db.session.rollback()
    
    def check_password_expiry(self, user_id, last_password_change):
        """Check if password has expired"""
        if not last_password_change:
            return True  # Force password change if no date recorded
        
        max_age = timedelta(days=self.config['password_policy']['max_age_days'])
        return datetime.utcnow() - last_password_change > max_age
    
    # ==================== SESSION MANAGEMENT ====================
    
    def create_user_session(self, user_id):
        """Create new user session"""
        try:
            # Generate session ID
            session_id = secrets.token_urlsafe(32)
            
            # Calculate expiry
            timeout_minutes = self.config['session_policy']['timeout_minutes']
            expires_at = datetime.utcnow() + timedelta(minutes=timeout_minutes)
            
            # Check concurrent session limit
            max_sessions = self.config['session_policy']['concurrent_sessions']
            active_sessions = self.UserSession.query.filter_by(
                user_id=user_id,
                is_active=True
            ).count()
            
            if active_sessions >= max_sessions:
                # Deactivate oldest session
                oldest_session = self.UserSession.query.filter_by(
                    user_id=user_id,
                    is_active=True
                ).order_by(self.UserSession.created_at.asc()).first()
                
                if oldest_session:
                    oldest_session.is_active = False
            
            # Create new session
            user_session = self.UserSession(
                user_id=user_id,
                session_id=session_id,
                ip_address=self._get_client_ip(),
                user_agent=request.headers.get('User-Agent', '') if request else '',
                expires_at=expires_at
            )
            
            self.db.session.add(user_session)
            self.db.session.commit()
            
            # Store in Flask session
            session['security_session_id'] = session_id
            session.permanent = True
            
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create user session: {str(e)}")
            return None
    
    def validate_session(self, session_id):
        """Validate user session"""
        try:
            user_session = self.UserSession.query.filter_by(
                session_id=session_id,
                is_active=True
            ).first()
            
            if not user_session:
                return False
            
            # Check expiry
            if user_session.expires_at < datetime.utcnow():
                user_session.is_active = False
                self.db.session.commit()
                return False
            
            # Update last activity
            user_session.last_activity = datetime.utcnow()
            self.db.session.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate session: {str(e)}")
            return False
    
    def terminate_session(self, session_id):
        """Terminate user session"""
        try:
            user_session = self.UserSession.query.filter_by(session_id=session_id).first()
            if user_session:
                user_session.is_active = False
                self.db.session.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to terminate session: {str(e)}")
            return False
    
    def terminate_all_user_sessions(self, user_id, except_current=True):
        """Terminate all sessions for a user"""
        try:
            query = self.UserSession.query.filter_by(user_id=user_id, is_active=True)
            
            if except_current:
                current_session_id = session.get('security_session_id')
                if current_session_id:
                    query = query.filter(self.UserSession.session_id != current_session_id)
            
            sessions = query.all()
            for user_session in sessions:
                user_session.is_active = False
            
            self.db.session.commit()
            
            return len(sessions)
            
        except Exception as e:
            logger.error(f"Failed to terminate user sessions: {str(e)}")
            return 0
    
    # ==================== IP SECURITY ====================
    
    def is_ip_whitelisted(self, ip_address):
        """Check if IP is whitelisted"""
        if not self.config['ip_security']['whitelist_enabled']:
            return True  # Whitelist disabled, allow all
        
        try:
            # Check exact IP match
            whitelist_entry = self.IPWhitelist.query.filter_by(
                ip_address=ip_address,
                is_active=True
            ).first()
            
            if whitelist_entry:
                return True
            
            # Check IP ranges
            ip_obj = ipaddress.ip_address(ip_address)
            range_entries = self.IPWhitelist.query.filter(
                self.IPWhitelist.ip_range.isnot(None),
                self.IPWhitelist.is_active == True
            ).all()
            
            for entry in range_entries:
                try:
                    network = ipaddress.ip_network(entry.ip_range, strict=False)
                    if ip_obj in network:
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check IP whitelist: {str(e)}")
            return True  # Allow on error
    
    def is_ip_blacklisted(self, ip_address):
        """Check if IP is blacklisted"""
        try:
            blacklist_entry = self.IPBlacklist.query.filter_by(ip_address=ip_address).first()
            
            if not blacklist_entry:
                return False
            
            # Check if temporary blacklist has expired
            if not blacklist_entry.is_permanent and blacklist_entry.blocked_until:
                if datetime.utcnow() > blacklist_entry.blocked_until:
                    self.db.session.delete(blacklist_entry)
                    self.db.session.commit()
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to check IP blacklist: {str(e)}")
            return False
    
    def add_ip_to_blacklist(self, ip_address, reason, duration_hours=None, permanent=False):
        """Add IP to blacklist"""
        try:
            blocked_until = None
            if not permanent and duration_hours:
                blocked_until = datetime.utcnow() + timedelta(hours=duration_hours)
            
            blacklist_entry = self.IPBlacklist(
                ip_address=ip_address,
                reason=reason,
                blocked_until=blocked_until,
                is_permanent=permanent,
                created_by=current_user.id if current_user.is_authenticated else None
            )
            
            self.db.session.add(blacklist_entry)
            self.db.session.commit()
            
            logger.info(f"IP {ip_address} added to blacklist: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add IP to blacklist: {str(e)}")
            return False
    
    def check_and_auto_blacklist(self, ip_address):
        """Check failed attempts and auto-blacklist if threshold exceeded"""
        try:
            # Count recent failed attempts from this IP
            recent_time = datetime.utcnow() - timedelta(hours=1)
            
            # This would integrate with your audit logging system
            # For now, we'll use a simple Redis counter
            if self.redis_available:
                key = f"failed_attempts:{ip_address}"
                attempts = self.redis_client.get(key) or 0
                attempts = int(attempts)
                
                if attempts >= self.config['ip_security']['auto_blacklist_attempts']:
                    duration = self.config['ip_security']['auto_blacklist_duration_hours']
                    self.add_ip_to_blacklist(
                        ip_address,
                        f"Auto-blacklisted after {attempts} failed attempts",
                        duration_hours=duration
                    )
                    
                    # Clear counter
                    self.redis_client.delete(key)
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check auto-blacklist: {str(e)}")
            return False
    
    def record_failed_attempt(self, ip_address):
        """Record failed login attempt"""
        if self.redis_available:
            key = f"failed_attempts:{ip_address}"
            self.redis_client.incr(key)
            self.redis_client.expire(key, 3600)  # Expire after 1 hour
    
    # ==================== CAPTCHA SYSTEM ====================
    
    def generate_captcha(self):
        """Generate CAPTCHA challenge"""
        try:
            # Generate random text
            length = self.config['captcha']['length']
            characters = string.ascii_uppercase + string.digits
            captcha_text = ''.join(random.choices(characters, k=length))
            
            # Create image
            width = self.config['captcha']['width']
            height = self.config['captcha']['height']
            font_size = self.config['captcha']['font_size']
            
            image = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(image)
            
            # Try to load a font, fallback to default
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
            
            # Add noise
            for _ in range(100):
                x = random.randint(0, width)
                y = random.randint(0, height)
                draw.point((x, y), fill='gray')
            
            # Draw text with slight variations
            text_width = draw.textlength(captcha_text, font=font)
            x = (width - text_width) // 2
            y = (height - font_size) // 2
            
            for i, char in enumerate(captcha_text):
                char_x = x + i * (text_width // length)
                char_y = y + random.randint(-5, 5)
                draw.text((char_x, char_y), char, fill='black', font=font)
            
            # Add lines
            for _ in range(3):
                x1 = random.randint(0, width)
                y1 = random.randint(0, height)
                x2 = random.randint(0, width)
                y2 = random.randint(0, height)
                draw.line([(x1, y1), (x2, y2)], fill='gray', width=2)
            
            # Convert to base64
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            
            # Generate challenge ID
            challenge_id = secrets.token_urlsafe(32)
            
            # Store challenge
            expires_at = datetime.utcnow() + timedelta(minutes=10)
            captcha_challenge = self.CaptchaChallenge(
                challenge_id=challenge_id,
                solution=captcha_text,
                ip_address=self._get_client_ip(),
                expires_at=expires_at
            )
            
            self.db.session.add(captcha_challenge)
            self.db.session.commit()
            
            return {
                'challenge_id': challenge_id,
                'image': f"data:image/png;base64,{img_base64}"
            }
            
        except Exception as e:
            logger.error(f"Failed to generate CAPTCHA: {str(e)}")
            return None
    
    def verify_captcha(self, challenge_id, solution):
        """Verify CAPTCHA solution"""
        try:
            challenge = self.CaptchaChallenge.query.filter_by(
                challenge_id=challenge_id,
                solved=False
            ).first()
            
            if not challenge:
                return False
            
            # Check expiry
            if challenge.expires_at < datetime.utcnow():
                return False
            
            # Check solution (case-insensitive)
            if challenge.solution.upper() == solution.upper():
                challenge.solved = True
                self.db.session.commit()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to verify CAPTCHA: {str(e)}")
            return False
    
    # ==================== DECORATORS ====================
    
    def require_ip_whitelist(self, f):
        """Decorator to require IP whitelisting"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = self._get_client_ip()
            
            if not self.is_ip_whitelisted(client_ip):
                self.log_security_event(
                    'ip_not_whitelisted',
                    'medium',
                    f"Access denied for non-whitelisted IP: {client_ip}"
                )
                abort(403)
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    def check_ip_blacklist(self, f):
        """Decorator to check IP blacklist"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = self._get_client_ip()
            
            if self.is_ip_blacklisted(client_ip):
                self.log_security_event(
                    'blacklisted_ip_access',
                    'high',
                    f"Access attempt from blacklisted IP: {client_ip}"
                )
                abort(403)
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    def require_valid_session(self, f):
        """Decorator to require valid session"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            session_id = session.get('security_session_id')
            
            if not session_id or not self.validate_session(session_id):
                self.log_security_event(
                    'invalid_session',
                    'medium',
                    "Access attempt with invalid session"
                )
                abort(401)
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    # ==================== UTILITY METHODS ====================
    
    def log_security_event(self, event_type, severity, description, details=None):
        """Log security event"""
        try:
            security_event = self.SecurityEvent(
                event_type=event_type,
                severity=severity,
                user_id=current_user.id if current_user.is_authenticated else None,
                ip_address=self._get_client_ip(),
                user_agent=request.headers.get('User-Agent', '') if request else '',
                description=description,
                details=json.dumps(details) if details else None
            )
            
            self.db.session.add(security_event)
            self.db.session.commit()
            
            logger.warning(f"Security Event: {event_type} - {severity} - {description}")
            
        except Exception as e:
            logger.error(f"Failed to log security event: {str(e)}")
    
    def _get_client_ip(self):
        """Get client IP address"""
        if not request:
            return 'unknown'
        
        if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
            return request.environ.get('REMOTE_ADDR', 'unknown')
        else:
            return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
    
    def get_security_dashboard_data(self):
        """Get data for security dashboard"""
        try:
            # Recent security events
            recent_events = self.SecurityEvent.query.filter(
                self.SecurityEvent.timestamp >= datetime.utcnow() - timedelta(days=7)
            ).order_by(self.SecurityEvent.timestamp.desc()).limit(50).all()
            
            # Active sessions
            active_sessions = self.UserSession.query.filter_by(is_active=True).count()
            
            # Blacklisted IPs
            blacklisted_ips = self.IPBlacklist.query.count()
            
            # Failed attempts in last hour
            failed_attempts = 0
            if self.redis_available:
                keys = self.redis_client.keys("failed_attempts:*")
                for key in keys:
                    failed_attempts += int(self.redis_client.get(key) or 0)
            
            return {
                'recent_events': [
                    {
                        'type': event.event_type,
                        'severity': event.severity,
                        'description': event.description,
                        'timestamp': event.timestamp.isoformat(),
                        'ip_address': event.ip_address
                    }
                    for event in recent_events
                ],
                'active_sessions': active_sessions,
                'blacklisted_ips': blacklisted_ips,
                'failed_attempts_last_hour': failed_attempts
            }
            
        except Exception as e:
            logger.error(f"Failed to get security dashboard data: {str(e)}")
            return {}

def init_advanced_security(app, db):
    """Initialize advanced security system"""
    return AdvancedSecurity(db, app)