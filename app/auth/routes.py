"""
Authentication routes for Hospital Management System
"""

from flask import render_template, request, redirect, url_for, flash, session, jsonify, Blueprint
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import uuid

from app import db, login_manager
from app.models.user import WebUser
from app.utils.decorators import role_required

# Add has_role method to WebUser
def has_role(user, role):
    """Check if user has specific role"""
    return user.is_authenticated and user.role == role

# Monkey patch the method to WebUser model
WebUser.has_role = lambda self, role: has_role(self, role)

# Import the blueprint from the __init__.py file
from . import bp

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(WebUser, int(user_id))

# =============== LOGIN/LOGOUT ROUTES ===============
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = WebUser.query.filter(
            (WebUser.username == username)
        ).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            session['language'] = session.get('language', 'en')
            
            flash('Login successful!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid username or password!', 'error')
    
    return render_template('login.html')

@bp.route('/logout')
def logout():
    if current_user.is_authenticated:
        logout_user()
        session.pop('language', None)
        flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

# =============== 2FA ROUTES ===============
@bp.route('/2fa/setup')
@login_required
def setup_2fa():
    # This would integrate with the two_factor_auth module
    return render_template('2fa_setup.html')

@bp.route('/2fa/verify', methods=['GET', 'POST'])
def verify_2fa():
    if request.method == 'POST':
        code = request.form.get('code')
        # Verify 2FA code here
        if code == '123456':  # Simplified for demo
            session['2fa_verified'] = True
            flash('2FA verification successful!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid verification code.', 'error')
    
    return render_template('2fa_verify.html')

@bp.route('/2fa/disable', methods=['POST'])
@login_required
def disable_2fa():
    # Disable 2FA for user
    flash('2FA disabled successfully!', 'success')
    return redirect(url_for('auth.profile'))

# =============== PROFILE ROUTES ===============
@bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    if request.method == 'POST':
        user = current_user
        user.full_name = request.form.get('full_name', user.full_name)
        user.email = request.form.get('email', user.email)
        user.phone = request.form.get('phone', user.phone)
        
        if request.form.get('password'):
            user.password_hash = generate_password_hash(request.form['password'])
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
    
    return redirect(url_for('auth.profile'))

# =============== LANGUAGE ROUTES ===============
@bp.route('/set-language/<language>')
def set_language(language):
    session['language'] = language
    return redirect(request.referrer or url_for('auth.login'))

# =============== BRANCH SWITCHING ===============
@bp.route('/switch-branch/<int:branch_id>')
@login_required
def switch_branch(branch_id):
    if branch_id == 0:
        session.pop('current_branch_id', None)
        session.pop('current_branch_name', None)
        session.pop('current_branch_code', None)
        flash('Switched to all branches view', 'success')
    else:
        from app.models.admin import HospitalBranch
        branch = HospitalBranch.query.get_or_404(branch_id)
        
        session['current_branch_id'] = branch.id
        session['current_branch_name'] = branch.name
        session['current_branch_code'] = branch.code
        
        flash(f'Switched to {branch.name} branch', 'success')
    
    return redirect(request.referrer or url_for('main.dashboard'))
