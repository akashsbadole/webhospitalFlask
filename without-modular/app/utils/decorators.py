"""
Decorators for Hospital Management System
"""

from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def role_required(*roles):
    """Decorator to require specific user roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role not in roles:
                flash('Access denied! You do not have permission to access this page.', 'error')
                return redirect(url_for('main.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
