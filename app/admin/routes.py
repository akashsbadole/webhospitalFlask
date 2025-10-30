"""
Admin routes for Hospital Management System
"""

from flask import render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json

from app import db
from app.models.user import WebUser
from app.models.patient import WebPatient
from app.models.admin import HospitalBranch, Bed, Ward
from app.utils.language import get_text, get_language
from app.utils.decorators import role_required

# Import blueprint from __init__.py
from app.admin import bp

# =============== ADMIN DASHBOARD ===============
@bp.route('/')
@login_required
@role_required('admin')
def admin_dashboard():
    """Admin dashboard with system overview"""
    
    # Get statistics
    total_users = WebUser.query.count()
    total_patients = WebPatient.query.count()
    total_branches = HospitalBranch.query.count()
    
    # User statistics by role
    admin_count = WebUser.query.filter_by(role='admin').count()
    doctor_count = WebUser.query.filter_by(role='doctor').count()
    nurse_count = WebUser.query.filter_by(role='nurse').count()
    receptionist_count = WebUser.query.filter_by(role='receptionist').count()
    pharmacist_count = WebUser.query.filter_by(role='pharmacist').count()
    
    # Recent users
    recent_users = WebUser.query.order_by(WebUser.created_at.desc()).limit(5).all()
    
    return render_template('admin_dashboard.html',
                         total_users=total_users,
                         total_patients=total_patients,
                         total_branches=total_branches,
                         admin_count=admin_count,
                         doctor_count=doctor_count,
                         nurse_count=nurse_count,
                         receptionist_count=receptionist_count,
                         pharmacist_count=pharmacist_count,
                         recent_users=recent_users)

# =============== USER MANAGEMENT ===============
@bp.route('/users')
@bp.route('/staff-management')
@login_required
@role_required('admin')
def staff_management():
    """Display all users"""
    
    role_filter = request.args.get('role', '')
    status_filter = request.args.get('status', '')
    
    query = WebUser.query
    
    if role_filter:
        query = query.filter_by(role=role_filter)
    
    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'inactive':
        query = query.filter_by(is_active=False)
    
    users = query.order_by(WebUser.created_at.desc()).all()
    
    return render_template('users.html', users=users, role_filter=role_filter, status_filter=status_filter)

@bp.route('/add-user', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_user():
    """Add a new user"""
    
    if request.method == 'POST':
        try:
            user = WebUser(
                username=request.form.get('username'),
                email=request.form.get('email'),
                full_name=request.form.get('full_name'),
                phone=request.form.get('phone'),
                role=request.form.get('role'),
                is_active=True
            )
            
            # Set password
            password = request.form.get('password')
            if password:
                user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            flash('User added successfully!', 'success')
            return redirect(url_for('admin.users'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding user: {str(e)}', 'error')
    
    return render_template('add_user.html')

@bp.route('/edit-user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_user(user_id):
    """Edit user"""
    
    user = WebUser.query.get_or_404(user_id)
    
    if request.method == 'POST':
        try:
            user.username = request.form.get('username', user.username)
            user.email = request.form.get('email', user.email)
            user.full_name = request.form.get('full_name', user.full_name)
            user.phone = request.form.get('phone', user.phone)
            user.role = request.form.get('role', user.role)
            user.is_active = 'is_active' in request.form
            
            # Update password if provided
            if request.form.get('password'):
                user.set_password(request.form.get('password'))
            
            db.session.commit()
            
            flash('User updated successfully!', 'success')
            return redirect(url_for('admin.users'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'error')
    
    return render_template('edit_user.html', user=user)

# =============== HOSPITAL BRANCHES ===============
@bp.route('/branches')
@login_required
@role_required('admin')
def branches():
    """Display all hospital branches"""
    
    branches = HospitalBranch.query.all()
    
    return render_template('branches.html', branches=branches)

@bp.route('/add-branch', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_branch():
    """Add a new hospital branch"""
    
    if request.method == 'POST':
        try:
            branch = HospitalBranch(
                name=request.form.get('name'),
                code=request.form.get('code'),
                address=request.form.get('address'),
                city=request.form.get('city'),
                state=request.form.get('state'),
                postal_code=request.form.get('postal_code'),
                country=request.form.get('country'),
                phone=request.form.get('phone'),
                email=request.form.get('email'),
                is_active=True
            )
            
            db.session.add(branch)
            db.session.commit()
            
            flash('Branch added successfully!', 'success')
            return redirect(url_for('admin.branches'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding branch: {str(e)}', 'error')
    
    return render_template('add_branch.html')

@bp.route('/edit-branch/<int:branch_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_branch(branch_id):
    """Edit hospital branch"""
    
    branch = HospitalBranch.query.get_or_404(branch_id)
    
    if request.method == 'POST':
        try:
            branch.name = request.form.get('name', branch.name)
            branch.code = request.form.get('code', branch.code)
            branch.address = request.form.get('address', branch.address)
            branch.city = request.form.get('city', branch.city)
            branch.state = request.form.get('state', branch.state)
            branch.postal_code = request.form.get('postal_code', branch.postal_code)
            branch.country = request.form.get('country', branch.country)
            branch.phone = request.form.get('phone', branch.phone)
            branch.email = request.form.get('email', branch.email)
            branch.is_active = 'is_active' in request.form
            
            db.session.commit()
            
            flash('Branch updated successfully!', 'success')
            return redirect(url_for('admin.branches'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating branch: {str(e)}', 'error')
    
    return render_template('edit_branch.html', branch=branch)

# =============== WARD MANAGEMENT ===============
@bp.route('/wards')
@bp.route('/manage-wards')
@login_required
@role_required('admin')
def manage_wards():
    """Display all wards"""
    
    wards = Ward.query.all()
    
    return render_template('wards.html', wards=wards)

@bp.route('/add-ward', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_ward():
    """Add a new ward"""
    
    if request.method == 'POST':
        try:
            ward = Ward(
                name=request.form.get('name'),
                ward_type=request.form.get('ward_type'),
                floor=request.form.get('floor'),
                capacity=int(request.form.get('capacity')),
                charges_per_day=float(request.form.get('charges_per_day')),
                is_active=True
            )
            
            db.session.add(ward)
            db.session.commit()
            
            flash('Ward added successfully!', 'success')
            return redirect(url_for('admin.wards'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding ward: {str(e)}', 'error')
    
    return render_template('add_ward.html')

# =============== BED MANAGEMENT ===============
@bp.route('/beds')
@login_required
@role_required('admin')
def beds():
    """Display all beds"""
    
    ward_filter = request.args.get('ward', '')
    status_filter = request.args.get('status', '')
    
    query = db.session.query(Bed, Ward).join(Ward, Bed.ward_id == Ward.id)
    
    if ward_filter:
        query = query.filter(Bed.ward_id == ward_filter)
    
    if status_filter == 'available':
        query = query.filter(Bed.is_occupied == False)
    elif status_filter == 'occupied':
        query = query.filter(Bed.is_occupied == True)
    
    beds = query.all()
    wards = Ward.query.all()
    
    return render_template('beds.html', beds=beds, wards=wards, ward_filter=ward_filter, status_filter=status_filter)

@bp.route('/add-bed', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_bed():
    """Add a new bed"""
    
    wards = Ward.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        try:
            bed = Bed(
                ward_id=request.form.get('ward_id'),
                bed_number=request.form.get('bed_number'),
                bed_type=request.form.get('bed_type'),
                charges_per_day=float(request.form.get('charges_per_day')),
                is_active=True,
                is_occupied=False
            )
            
            db.session.add(bed)
            db.session.commit()
            
            flash('Bed added successfully!', 'success')
            return redirect(url_for('admin.beds'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding bed: {str(e)}', 'error')
    
    return render_template('add_bed.html', wards=wards)

# =============== SYSTEM SETTINGS ===============
@bp.route('/settings')
@login_required
@role_required('admin')
def settings():
    """Display system settings"""
    
    # This would typically load settings from a database or config file
    settings = {
        'hospital_name': 'Hospital Management System',
        'hospital_address': '123 Hospital Street, City, State',
        'hospital_phone': '(123) 456-7890',
        'hospital_email': 'info@hospital.com',
        'currency': 'USD',
        'timezone': 'UTC',
        'date_format': 'YYYY-MM-DD',
        'time_format': '24-hour',
        'language': 'English',
        'backup_frequency': 'Daily',
        'auto_logout_time': '30 minutes'
    }
    
    return render_template('settings.html', settings=settings)

# =============== ATTENDANCE MANAGEMENT ===============
@bp.route('/attendance')
@login_required
@role_required('admin')
def attendance():
    """Attendance management"""
    from app.models.attendance import WebAttendance
    attendance_records = WebAttendance.query.order_by(WebAttendance.date.desc()).limit(50).all()
    return render_template('attendance.html', attendance_records=attendance_records)

# =============== DEPARTMENTS MANAGEMENT ===============
@bp.route('/departments')
@bp.route('/manage-departments')
@login_required
@role_required('admin')
def manage_departments():
    """Manage departments"""
    from app.models.admin import Department
    departments = Department.query.all()
    return render_template('departments.html', departments=departments)

# =============== REPORTS ===============
@bp.route('/reports')
@login_required
@role_required('admin')
def reports():
    """Admin reports"""
    return render_template('reports.html')

@bp.route('/settings', methods=['POST'])
@login_required
@role_required('admin')
def update_settings():
    """Update system settings"""
    
    try:
        # This would typically update settings in a database or config file
        # For now, we'll just show a success message
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('admin.settings'))
        
    except Exception as e:
        flash(f'Error updating settings: {str(e)}', 'error')
        return redirect(url_for('admin.settings'))

# =============== API ENDPOINTS ===============
@bp.route('/api/user-stats')
@login_required
@role_required('admin')
def get_user_stats():
    """API endpoint to get user statistics"""
    
    total_users = WebUser.query.count()
    active_users = WebUser.query.filter_by(is_active=True).count()
    
    # Users by role
    roles = db.session.query(WebUser.role, db.func.count(WebUser.id)).group_by(WebUser.role).all()
    role_stats = {role: count for role, count in roles}
    
    return jsonify({
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': total_users - active_users,
        'role_stats': role_stats
    })

@bp.route('/api/branch-stats')
@login_required
@role_required('admin')
def get_branch_stats():
    """API endpoint to get branch statistics"""
    
    total_branches = HospitalBranch.query.count()
    active_branches = HospitalBranch.query.filter_by(is_active=True).count()
    
    return jsonify({
        'total_branches': total_branches,
        'active_branches': active_branches,
        'inactive_branches': total_branches - active_branches
    })