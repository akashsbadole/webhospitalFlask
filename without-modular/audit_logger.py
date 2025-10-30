#!/usr/bin/env python3
"""
Audit Logging & Compliance System
Comprehensive audit trail for all CRUD operations, user activities, and compliance reporting
"""

from flask import request, session, g
from flask_login import current_user
from datetime import datetime, timedelta
import json
import hashlib
import ipaddress
from functools import wraps
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session
import logging
import os
from pathlib import Path

# Configure audit logging
audit_log_dir = Path('audit_logs')
audit_log_dir.mkdir(exist_ok=True)

audit_logger = logging.getLogger('audit')
audit_logger.setLevel(logging.INFO)

# Create file handler with rotation
audit_handler = logging.FileHandler(audit_log_dir / 'audit.log')
audit_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))
audit_logger.addHandler(audit_handler)

class AuditLogger:
    def __init__(self, db):
        self.db = db
        self.setup_audit_tables()
        self.setup_database_listeners()
    
    def setup_audit_tables(self):
        """Create audit tables if they don't exist"""
        
        # User Activity Audit
        class UserActivityAudit(self.db.Model):
            __tablename__ = 'user_activity_audit'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            user_id = self.db.Column(self.db.Integer, nullable=True)  # Can be null for anonymous actions
            username = self.db.Column(self.db.String(80))
            session_id = self.db.Column(self.db.String(100))
            ip_address = self.db.Column(self.db.String(45))  # IPv6 compatible
            user_agent = self.db.Column(self.db.Text)
            action = self.db.Column(self.db.String(50), nullable=False)  # login, logout, view, create, update, delete
            resource_type = self.db.Column(self.db.String(50))  # patient, appointment, etc.
            resource_id = self.db.Column(self.db.String(50))
            details = self.db.Column(self.db.Text)  # JSON string with additional details
            timestamp = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            risk_level = self.db.Column(self.db.String(20), default='low')  # low, medium, high, critical
            
        # Data Modification Audit
        class DataAudit(self.db.Model):
            __tablename__ = 'data_audit'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            user_id = self.db.Column(self.db.Integer, nullable=False)
            username = self.db.Column(self.db.String(80))
            table_name = self.db.Column(self.db.String(50), nullable=False)
            record_id = self.db.Column(self.db.String(50), nullable=False)
            operation = self.db.Column(self.db.String(10), nullable=False)  # INSERT, UPDATE, DELETE
            old_values = self.db.Column(self.db.Text)  # JSON string
            new_values = self.db.Column(self.db.Text)  # JSON string
            changed_fields = self.db.Column(self.db.Text)  # JSON array of changed field names
            timestamp = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            ip_address = self.db.Column(self.db.String(45))
            session_id = self.db.Column(self.db.String(100))
            
        # Login Audit
        class LoginAudit(self.db.Model):
            __tablename__ = 'login_audit'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            username = self.db.Column(self.db.String(80))
            user_id = self.db.Column(self.db.Integer)
            ip_address = self.db.Column(self.db.String(45))
            user_agent = self.db.Column(self.db.Text)
            login_time = self.db.Column(self.db.DateTime)
            logout_time = self.db.Column(self.db.DateTime)
            session_duration = self.db.Column(self.db.Integer)  # in seconds
            login_status = self.db.Column(self.db.String(20))  # success, failed, locked
            failure_reason = self.db.Column(self.db.String(100))
            session_id = self.db.Column(self.db.String(100))
            
        # Failed Login Attempts
        class FailedLoginAttempt(self.db.Model):
            __tablename__ = 'failed_login_attempts'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            username = self.db.Column(self.db.String(80))
            ip_address = self.db.Column(self.db.String(45))
            user_agent = self.db.Column(self.db.Text)
            attempt_time = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            failure_reason = self.db.Column(self.db.String(100))
            
        # Security Events
        class SecurityEvent(self.db.Model):
            __tablename__ = 'security_events'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            event_type = self.db.Column(self.db.String(50), nullable=False)  # suspicious_activity, data_breach, etc.
            severity = self.db.Column(self.db.String(20), nullable=False)  # low, medium, high, critical
            user_id = self.db.Column(self.db.Integer)
            ip_address = self.db.Column(self.db.String(45))
            description = self.db.Column(self.db.Text)
            details = self.db.Column(self.db.Text)  # JSON string
            timestamp = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            resolved = self.db.Column(self.db.Boolean, default=False)
            resolved_by = self.db.Column(self.db.Integer)
            resolved_at = self.db.Column(self.db.DateTime)
            
        # Store model classes for later use
        self.UserActivityAudit = UserActivityAudit
        self.DataAudit = DataAudit
        self.LoginAudit = LoginAudit
        self.FailedLoginAttempt = FailedLoginAttempt
        self.SecurityEvent = SecurityEvent
        
        # Create tables
        self.db.create_all()
    
    def setup_database_listeners(self):
        """Setup SQLAlchemy event listeners for automatic audit logging"""
        
        @event.listens_for(Session, 'before_flush')
        def before_flush(session, flush_context, instances):
            """Capture changes before they're committed"""
            if not hasattr(g, 'audit_changes'):
                g.audit_changes = []
            
            # Track new objects
            for obj in session.new:
                if self._should_audit_table(obj.__tablename__):
                    change = {
                        'operation': 'INSERT',
                        'table_name': obj.__tablename__,
                        'record_id': None,  # Will be set after flush
                        'old_values': None,
                        'new_values': self._serialize_object(obj),
                        'changed_fields': list(self._serialize_object(obj).keys()),
                        'object': obj
                    }
                    g.audit_changes.append(change)
            
            # Track modified objects
            for obj in session.dirty:
                if self._should_audit_table(obj.__tablename__):
                    old_values = {}
                    new_values = {}
                    changed_fields = []
                    
                    # Get the object's state
                    state = inspect(obj)
                    
                    for attr in state.attrs:
                        if attr.history.has_changes():
                            field_name = attr.key
                            changed_fields.append(field_name)
                            
                            # Get old value
                            if attr.history.deleted:
                                old_values[field_name] = attr.history.deleted[0]
                            
                            # Get new value
                            new_values[field_name] = getattr(obj, field_name)
                    
                    if changed_fields:  # Only log if there are actual changes
                        change = {
                            'operation': 'UPDATE',
                            'table_name': obj.__tablename__,
                            'record_id': str(getattr(obj, 'id', 'unknown')),
                            'old_values': old_values,
                            'new_values': new_values,
                            'changed_fields': changed_fields,
                            'object': obj
                        }
                        g.audit_changes.append(change)
            
            # Track deleted objects
            for obj in session.deleted:
                if self._should_audit_table(obj.__tablename__):
                    change = {
                        'operation': 'DELETE',
                        'table_name': obj.__tablename__,
                        'record_id': str(getattr(obj, 'id', 'unknown')),
                        'old_values': self._serialize_object(obj),
                        'new_values': None,
                        'changed_fields': list(self._serialize_object(obj).keys()),
                        'object': obj
                    }
                    g.audit_changes.append(change)
        
        @event.listens_for(Session, 'after_flush')
        def after_flush(session, flush_context):
            """Update record IDs for new objects after flush"""
            if hasattr(g, 'audit_changes'):
                for change in g.audit_changes:
                    if change['operation'] == 'INSERT' and change['record_id'] is None:
                        obj = change['object']
                        change['record_id'] = str(getattr(obj, 'id', 'unknown'))
        
        @event.listens_for(Session, 'after_commit')
        def after_commit(session):
            """Log audit entries after successful commit"""
            if hasattr(g, 'audit_changes'):
                for change in g.audit_changes:
                    self._log_data_change(change)
                g.audit_changes = []
    
    def _should_audit_table(self, table_name):
        """Determine if a table should be audited"""
        # Don't audit the audit tables themselves
        audit_tables = {
            'user_activity_audit', 'data_audit', 'login_audit', 
            'failed_login_attempts', 'security_events'
        }
        return table_name not in audit_tables
    
    def _serialize_object(self, obj):
        """Serialize SQLAlchemy object to dictionary"""
        result = {}
        for column in obj.__table__.columns:
            value = getattr(obj, column.name)
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            elif value is not None:
                result[column.name] = str(value)
            else:
                result[column.name] = None
        return result
    
    def _log_data_change(self, change):
        """Log data change to audit table"""
        try:
            try:
                user_id = current_user.id if current_user and current_user.is_authenticated else None
                username = current_user.username if current_user and current_user.is_authenticated else 'anonymous'
            except:
                user_id = None
                username = 'anonymous'
                
            audit_entry = self.DataAudit(
                user_id=user_id,
                username=username,
                table_name=change['table_name'],
                record_id=change['record_id'],
                operation=change['operation'],
                old_values=json.dumps(change['old_values']) if change['old_values'] else None,
                new_values=json.dumps(change['new_values']) if change['new_values'] else None,
                changed_fields=json.dumps(change['changed_fields']),
                ip_address=self._get_client_ip(),
                session_id=session.get('session_id', '')
            )
            
            self.db.session.add(audit_entry)
            self.db.session.commit()
            
            # Also log to file
            audit_logger.info(f"DATA_CHANGE: {change['operation']} on {change['table_name']} "
                            f"record {change['record_id']} by user {audit_entry.username}")
            
        except Exception as e:
            audit_logger.error(f"Failed to log data change: {str(e)}")
    
    def log_user_activity(self, action, resource_type=None, resource_id=None, 
                         details=None, risk_level='low'):
        """Log user activity"""
        try:
            try:
                user_id = current_user.id if current_user and current_user.is_authenticated else None
                username = current_user.username if current_user and current_user.is_authenticated else 'anonymous'
            except:
                user_id = None
                username = 'anonymous'
                
            activity = self.UserActivityAudit(
                user_id=user_id,
                username=username,
                session_id=session.get('session_id', ''),
                ip_address=self._get_client_ip(),
                user_agent=request.headers.get('User-Agent', ''),
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
                details=json.dumps(details) if details else None,
                risk_level=risk_level
            )
            
            self.db.session.add(activity)
            self.db.session.commit()
            
            # Log to file
            audit_logger.info(f"USER_ACTIVITY: {action} by {activity.username} "
                            f"on {resource_type} {resource_id} from {activity.ip_address}")
            
        except Exception as e:
            audit_logger.error(f"Failed to log user activity: {str(e)}")
    
    def log_login_attempt(self, username, success=True, failure_reason=None):
        """Log login attempt"""
        try:
            if success:
                # Log successful login
                try:
                    user_id = current_user.id if current_user and current_user.is_authenticated else None
                except:
                    user_id = None
                    
                login_entry = self.LoginAudit(
                    username=username,
                    user_id=user_id,
                    ip_address=self._get_client_ip(),
                    user_agent=request.headers.get('User-Agent', ''),
                    login_time=datetime.utcnow(),
                    login_status='success',
                    session_id=session.get('session_id', '')
                )
                
                self.db.session.add(login_entry)
                audit_logger.info(f"LOGIN_SUCCESS: {username} from {login_entry.ip_address}")
                
            else:
                # Log failed login
                failed_attempt = self.FailedLoginAttempt(
                    username=username,
                    ip_address=self._get_client_ip(),
                    user_agent=request.headers.get('User-Agent', ''),
                    failure_reason=failure_reason
                )
                
                self.db.session.add(failed_attempt)
                audit_logger.warning(f"LOGIN_FAILED: {username} from {failed_attempt.ip_address} - {failure_reason}")
                
                # Check for suspicious activity
                self._check_suspicious_login_activity(username, failed_attempt.ip_address)
            
            self.db.session.commit()
            
        except Exception as e:
            audit_logger.error(f"Failed to log login attempt: {str(e)}")
    
    def log_logout(self, username, session_id):
        """Log user logout"""
        try:
            # Update login audit record with logout time
            login_record = self.LoginAudit.query.filter_by(
                username=username,
                session_id=session_id,
                logout_time=None
            ).first()
            
            if login_record:
                login_record.logout_time = datetime.utcnow()
                if login_record.login_time:
                    duration = (login_record.logout_time - login_record.login_time).total_seconds()
                    login_record.session_duration = int(duration)
                
                self.db.session.commit()
                audit_logger.info(f"LOGOUT: {username} session duration: {login_record.session_duration}s")
            
        except Exception as e:
            audit_logger.error(f"Failed to log logout: {str(e)}")
    
    def log_security_event(self, event_type, severity, description, details=None):
        """Log security event"""
        try:
            try:
                user_id = current_user.id if current_user and current_user.is_authenticated else None
            except:
                user_id = None
                
            security_event = self.SecurityEvent(
                event_type=event_type,
                severity=severity,
                user_id=user_id,
                ip_address=self._get_client_ip(),
                description=description,
                details=json.dumps(details) if details else None
            )
            
            self.db.session.add(security_event)
            self.db.session.commit()
            
            audit_logger.warning(f"SECURITY_EVENT: {event_type} - {severity} - {description}")
            
        except Exception as e:
            audit_logger.error(f"Failed to log security event: {str(e)}")
    
    def _check_suspicious_login_activity(self, username, ip_address):
        """Check for suspicious login patterns"""
        try:
            # Check for multiple failed attempts in short time
            recent_failures = self.FailedLoginAttempt.query.filter(
                self.FailedLoginAttempt.username == username,
                self.FailedLoginAttempt.attempt_time > datetime.utcnow() - timedelta(minutes=15)
            ).count()
            
            if recent_failures >= 5:
                self.log_security_event(
                    'multiple_failed_logins',
                    'high',
                    f'Multiple failed login attempts for user {username}',
                    {'username': username, 'ip_address': ip_address, 'attempt_count': recent_failures}
                )
            
            # Check for login attempts from multiple IPs
            recent_ips = self.FailedLoginAttempt.query.filter(
                self.FailedLoginAttempt.username == username,
                self.FailedLoginAttempt.attempt_time > datetime.utcnow() - timedelta(hours=1)
            ).distinct(self.FailedLoginAttempt.ip_address).count()
            
            if recent_ips >= 3:
                self.log_security_event(
                    'multiple_ip_login_attempts',
                    'medium',
                    f'Login attempts from multiple IPs for user {username}',
                    {'username': username, 'ip_count': recent_ips}
                )
                
        except Exception as e:
            audit_logger.error(f"Failed to check suspicious activity: {str(e)}")
    
    def _get_client_ip(self):
        """Get client IP address"""
        if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
            return request.environ['REMOTE_ADDR']
        else:
            return request.environ['HTTP_X_FORWARDED_FOR']
    
    def generate_compliance_report(self, start_date, end_date, report_type='full'):
        """Generate compliance report for audit purposes"""
        try:
            report = {
                'report_type': report_type,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'generated_at': datetime.utcnow().isoformat(),
                'generated_by': current_user.username if current_user.is_authenticated else 'system'
            }
            
            # User activity summary
            user_activities = self.UserActivityAudit.query.filter(
                self.UserActivityAudit.timestamp.between(start_date, end_date)
            ).all()
            
            report['user_activity_summary'] = {
                'total_activities': len(user_activities),
                'unique_users': len(set(a.username for a in user_activities if a.username)),
                'actions_breakdown': {}
            }
            
            # Count actions
            for activity in user_activities:
                action = activity.action
                if action not in report['user_activity_summary']['actions_breakdown']:
                    report['user_activity_summary']['actions_breakdown'][action] = 0
                report['user_activity_summary']['actions_breakdown'][action] += 1
            
            # Data modifications summary
            data_changes = self.DataAudit.query.filter(
                self.DataAudit.timestamp.between(start_date, end_date)
            ).all()
            
            report['data_modifications'] = {
                'total_changes': len(data_changes),
                'operations_breakdown': {},
                'tables_affected': {}
            }
            
            for change in data_changes:
                # Count operations
                op = change.operation
                if op not in report['data_modifications']['operations_breakdown']:
                    report['data_modifications']['operations_breakdown'][op] = 0
                report['data_modifications']['operations_breakdown'][op] += 1
                
                # Count table changes
                table = change.table_name
                if table not in report['data_modifications']['tables_affected']:
                    report['data_modifications']['tables_affected'][table] = 0
                report['data_modifications']['tables_affected'][table] += 1
            
            # Login activity summary
            login_attempts = self.LoginAudit.query.filter(
                self.LoginAudit.login_time.between(start_date, end_date)
            ).all()
            
            failed_attempts = self.FailedLoginAttempt.query.filter(
                self.FailedLoginAttempt.attempt_time.between(start_date, end_date)
            ).all()
            
            report['login_activity'] = {
                'successful_logins': len(login_attempts),
                'failed_attempts': len(failed_attempts),
                'unique_users_logged_in': len(set(l.username for l in login_attempts if l.username)),
                'average_session_duration': 0
            }
            
            # Calculate average session duration
            valid_sessions = [l for l in login_attempts if l.session_duration]
            if valid_sessions:
                avg_duration = sum(l.session_duration for l in valid_sessions) / len(valid_sessions)
                report['login_activity']['average_session_duration'] = round(avg_duration, 2)
            
            # Security events summary
            security_events = self.SecurityEvent.query.filter(
                self.SecurityEvent.timestamp.between(start_date, end_date)
            ).all()
            
            report['security_events'] = {
                'total_events': len(security_events),
                'severity_breakdown': {},
                'event_types': {}
            }
            
            for event in security_events:
                # Count by severity
                severity = event.severity
                if severity not in report['security_events']['severity_breakdown']:
                    report['security_events']['severity_breakdown'][severity] = 0
                report['security_events']['severity_breakdown'][severity] += 1
                
                # Count by type
                event_type = event.event_type
                if event_type not in report['security_events']['event_types']:
                    report['security_events']['event_types'][event_type] = 0
                report['security_events']['event_types'][event_type] += 1
            
            return report
            
        except Exception as e:
            audit_logger.error(f"Failed to generate compliance report: {str(e)}")
            raise

# Decorator for auditing function calls
def audit_action(action, resource_type=None, risk_level='low'):
    """Decorator to automatically audit function calls"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract resource_id from kwargs or args if available
            resource_id = kwargs.get('id') or (args[0] if args else None)
            
            # Log the action
            if hasattr(g, 'audit_logger'):
                g.audit_logger.log_user_activity(
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    risk_level=risk_level
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Initialize audit logger instance
def init_audit_logger(app, db):
    """Initialize audit logger with Flask app"""
    audit_logger_instance = AuditLogger(db)
    
    @app.before_request
    def before_request():
        g.audit_logger = audit_logger_instance
        
        # Generate session ID if not exists
        if 'session_id' not in session:
            session['session_id'] = hashlib.md5(
                f"{datetime.utcnow().isoformat()}{request.remote_addr}".encode()
            ).hexdigest()
    
    return audit_logger_instance