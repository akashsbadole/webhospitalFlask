"""
Tenant Management Routes
Handles tenant registration, subscription management, and super admin functions
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random
import string
import logging

logger = logging.getLogger(__name__)

def generate_tenant_code():
    """Generate unique tenant code"""
    from web_app import Tenant, db
    
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if not Tenant.query.filter_by(tenant_code=code).first():
            return code

def generate_patient_id_for_tenant(tenant_id):
    """Generate unique patient ID for a tenant"""
    from web_app import WebPatient, db
    
    # Get count of patients for this tenant
    count = WebPatient.query.filter_by(tenant_id=tenant_id).count()
    return f'P{count + 1:06d}'

def init_tenant_routes(app, db):
    """Initialize tenant-related routes"""
    from subscription_plans import SUBSCRIPTION_PLANS, get_plan_details
    from tenant_context import tenant_context
    
    # =============== TENANT REGISTRATION ===============
    @app.route('/register-hospital', methods=['GET', 'POST'])
    def register_hospital():
        """Register a new hospital tenant"""
        from web_app import Tenant, WebUser, Department, Ward, Bed
        
        if request.method == 'POST':
            try:
                # Validate subdomain availability
                subdomain = request.form.get('subdomain', '').lower().strip()
                
                if not subdomain:
                    flash('Subdomain is required', 'danger')
                    return redirect(url_for('register_hospital'))
                
                if Tenant.query.filter_by(subdomain=subdomain).first():
                    flash('Subdomain already taken. Please choose another.', 'danger')
                    return redirect(url_for('register_hospital'))
                
                # Create tenant
                tenant = Tenant(
                    tenant_code=generate_tenant_code(),
                    name=request.form.get('hospital_name'),
                    subdomain=subdomain,
                    admin_name=request.form.get('admin_name'),
                    admin_email=request.form.get('admin_email'),
                    admin_phone=request.form.get('phone'),
                    city=request.form.get('city'),
                    country=request.form.get('country'),
                    subscription_plan=request.form.get('plan', 'basic'),
                    subscription_status='trial',
                    trial_ends_at=datetime.utcnow() + timedelta(days=14),
                    max_users=10,
                    max_patients=100,
                    max_storage_gb=1
                )
                
                db.session.add(tenant)
                db.session.flush()  # Get tenant ID
                
                logger.info(f"Creating tenant: {tenant.name} (ID: {tenant.id})")
                
                # Create admin user for tenant
                admin_user = WebUser(
                    tenant_id=tenant.id,
                    username=request.form.get('admin_email'),
                    email=request.form.get('admin_email'),
                    password_hash=generate_password_hash(request.form.get('password')),
                    full_name=request.form.get('admin_name'),
                    role='admin',
                    employee_id=f'ADMIN-{tenant.tenant_code}',
                    is_active=True
                )
                
                db.session.add(admin_user)
                logger.info(f"Created admin user for tenant {tenant.id}")
                
                # Create default departments
                default_departments = [
                    {'name': 'Cardiology', 'code': 'CARD'},
                    {'name': 'Neurology', 'code': 'NEUR'},
                    {'name': 'Orthopedics', 'code': 'ORTH'},
                    {'name': 'Pediatrics', 'code': 'PEDI'},
                    {'name': 'General Medicine', 'code': 'GENM'}
                ]
                
                for dept_data in default_departments:
                    dept = Department(
                        tenant_id=tenant.id,
                        name=dept_data['name'],
                        code=dept_data['code'],
                        is_active=True
                    )
                    db.session.add(dept)
                
                logger.info(f"Created {len(default_departments)} departments for tenant {tenant.id}")
                
                # Create default wards
                default_wards = [
                    {'name': 'General Ward', 'type': 'general', 'beds': 20, 'charge': 100},
                    {'name': 'ICU', 'type': 'icu', 'beds': 10, 'charge': 500},
                    {'name': 'Emergency', 'type': 'emergency', 'beds': 15, 'charge': 200}
                ]
                
                for ward_data in default_wards:
                    ward = Ward(
                        tenant_id=tenant.id,
                        name=ward_data['name'],
                        ward_type=ward_data['type'],
                        total_beds=ward_data['beds'],
                        available_beds=ward_data['beds'],
                        charge_per_day=ward_data['charge'],
                        is_active=True
                    )
                    db.session.add(ward)
                    db.session.flush()
                    
                    # Create beds
                    for i in range(1, ward_data['beds'] + 1):
                        bed = Bed(
                            tenant_id=tenant.id,
                            bed_number=f"{ward_data['type'].upper()}-{i:03d}",
                            ward_id=ward.id,
                            bed_type=ward_data['type'],
                            is_occupied=False,
                            is_active=True
                        )
                        db.session.add(bed)
                
                logger.info(f"Created wards and beds for tenant {tenant.id}")
                
                db.session.commit()
                
                flash(f'Hospital registered successfully! Your 14-day trial has started.', 'success')
                flash(f'Login at: http://{subdomain}.yourdomain.com/login', 'info')
                
                # Redirect to login page with subdomain
                return redirect(url_for('login'))
                
            except Exception as e:
                db.session.rollback()
                logger.error(f'Error registering hospital: {str(e)}', exc_info=True)
                flash(f'Error registering hospital: {str(e)}', 'danger')
                return redirect(url_for('register_hospital'))
        
        # GET request - show registration form
        return render_template('register_hospital.html', plans=SUBSCRIPTION_PLANS)
    
    # =============== TENANT SELECTION (for testing) ===============
    @app.route('/select-tenant')
    def select_tenant():
        """Select tenant for testing (development only)"""
        from web_app import Tenant
        
        tenants = Tenant.query.filter_by(is_active=True).all()
        return render_template('select_tenant.html', tenants=tenants)
    
    @app.route('/set-tenant/<int:tenant_id>')
    def set_tenant(tenant_id):
        """Set tenant in session (development only)"""
        from web_app import Tenant
        
        tenant = Tenant.query.get_or_404(tenant_id)
        tenant_context.set_current_tenant(tenant)
        flash(f'Switched to tenant: {tenant.name}', 'success')
        return redirect(url_for('dashboard'))
    
    # =============== SUBSCRIPTION MANAGEMENT ===============
    @app.route('/subscription')
    @login_required
    def subscription():
        """View current subscription"""
        tenant = tenant_context.get_current_tenant()
        if not tenant:
            flash('No tenant context', 'danger')
            return redirect(url_for('dashboard'))
        
        current_plan = get_plan_details(tenant.subscription_plan)
        
        return render_template('subscription.html', 
                             tenant=tenant,
                             current_plan=current_plan,
                             plans=SUBSCRIPTION_PLANS)
    
    @app.route('/subscription/upgrade', methods=['POST'])
    @login_required
    def upgrade_subscription():
        """Upgrade subscription plan"""
        from web_app import Tenant
        
        tenant = tenant_context.get_current_tenant()
        if not tenant:
            return jsonify({'success': False, 'message': 'No tenant context'})
        
        plan = request.form.get('plan')
        billing_cycle = request.form.get('billing_cycle', 'monthly')
        
        if plan not in SUBSCRIPTION_PLANS:
            return jsonify({'success': False, 'message': 'Invalid plan'})
        
        plan_details = SUBSCRIPTION_PLANS[plan]
        
        # Update tenant
        tenant.subscription_plan = plan
        tenant.max_users = plan_details['max_users']
        tenant.max_patients = plan_details['max_patients']
        tenant.max_storage_gb = plan_details['max_storage_gb']
        tenant.subscription_status = 'active'
        tenant.subscription_starts_at = datetime.utcnow()
        
        if billing_cycle == 'monthly':
            tenant.subscription_ends_at = datetime.utcnow() + timedelta(days=30)
        else:
            tenant.subscription_ends_at = datetime.utcnow() + timedelta(days=365)
        
        db.session.commit()
        
        flash(f'Successfully upgraded to {plan_details["name"]} plan!', 'success')
        return jsonify({'success': True, 'message': 'Subscription upgraded successfully'})
    
    # =============== SUPER ADMIN ROUTES ===============
    @app.route('/superadmin')
    @login_required
    def superadmin_dashboard():
        """Super admin dashboard"""
        from web_app import Tenant, WebUser, WebPatient
        
        # Check if user is superadmin (tenant_id is NULL)
        if current_user.tenant_id is not None:
            flash('Access denied. Super admin only.', 'danger')
            return redirect(url_for('dashboard'))
        
        tenants = Tenant.query.all()
        
        stats = {
            'total_tenants': len(tenants),
            'active_tenants': len([t for t in tenants if t.subscription_status == 'active']),
            'trial_tenants': len([t for t in tenants if t.subscription_status == 'trial']),
            'total_users': WebUser.query.count(),
            'total_patients': WebPatient.query.count()
        }
        
        return render_template('superadmin_dashboard.html', 
                             tenants=tenants,
                             stats=stats)
    
    @app.route('/superadmin/tenant/<int:tenant_id>')
    @login_required
    def superadmin_tenant_details(tenant_id):
        """View tenant details"""
        from web_app import Tenant, WebUser, WebPatient, WebAppointment, Payment
        
        if current_user.tenant_id is not None:
            flash('Access denied. Super admin only.', 'danger')
            return redirect(url_for('dashboard'))
        
        tenant = Tenant.query.get_or_404(tenant_id)
        
        # Get tenant statistics
        tenant_stats = {
            'users': WebUser.query.filter_by(tenant_id=tenant.id).count(),
            'patients': WebPatient.query.filter_by(tenant_id=tenant.id).count(),
            'appointments': WebAppointment.query.filter_by(tenant_id=tenant.id).count() if hasattr(WebAppointment, 'tenant_id') else 0,
            'revenue': db.session.query(db.func.sum(Payment.amount)).filter_by(tenant_id=tenant.id).scalar() or 0 if hasattr(Payment, 'tenant_id') else 0
        }
        
        return render_template('superadmin_tenant_details.html',
                             tenant=tenant,
                             stats=tenant_stats,
                             plan=get_plan_details(tenant.subscription_plan))
    
    @app.route('/superadmin/tenant/<int:tenant_id>/suspend', methods=['POST'])
    @login_required
    def suspend_tenant(tenant_id):
        """Suspend a tenant"""
        from web_app import Tenant
        
        if current_user.tenant_id is not None:
            return jsonify({'success': False, 'message': 'Access denied'})
        
        tenant = Tenant.query.get_or_404(tenant_id)
        tenant.subscription_status = 'suspended'
        tenant.is_active = False
        db.session.commit()
        
        flash(f'Tenant {tenant.name} suspended successfully', 'success')
        return redirect(url_for('superadmin_tenant_details', tenant_id=tenant_id))
    
    @app.route('/superadmin/tenant/<int:tenant_id>/activate', methods=['POST'])
    @login_required
    def activate_tenant(tenant_id):
        """Activate a suspended tenant"""
        from web_app import Tenant
        
        if current_user.tenant_id is not None:
            return jsonify({'success': False, 'message': 'Access denied'})
        
        tenant = Tenant.query.get_or_404(tenant_id)
        tenant.subscription_status = 'active'
        tenant.is_active = True
        db.session.commit()
        
        flash(f'Tenant {tenant.name} activated successfully', 'success')
        return redirect(url_for('superadmin_tenant_details', tenant_id=tenant_id))
    
    logger.info("Tenant routes initialized")
